from __future__ import annotations

import base64
from pathlib import Path

from app.config import Settings
from app.model_clients import ModelClientError, ZhipuChatClient
from schemas.video import Keyframe, SegmentUnderstanding, TranscriptChunk, VideoSegment


VLM_PROMPT = """Return one JSON object matching this schema:
{
  "visual_summary": string,
  "scene": string,
  "main_actions": string,
  "emotion_hint": string,
  "conflict_level": integer from 0 to 5,
  "visible_characters": [string],
  "character_actions": [string],
  "facial_expressions": string,
  "shot_cues": string,
  "sound_cues": string,
  "power_dynamic": string
}
除 schema key 外，所有字段值必须使用简体中文输出。
不要输出英文角色泛称；无法确认姓名时使用中文描述，例如“白衣男子”“年长妇人”。
Use the keyframe and nearby ASR text as evidence. Preserve character continuity when the same
person appears in adjacent segments. Separate visible evidence from inferred relationships.
Do not invent IDs or unsupported plot facts. 若 ASR 破碎，应结合画面和相邻台词还原角色动作、
情绪、权力关系，但不得把无证据的剧情当作确定事实。"""


def build_segment_understandings(
    settings: Settings,
    segments: list[VideoSegment],
    transcript_chunks: list[TranscriptChunk],
    keyframes: list[Keyframe],
) -> list[SegmentUnderstanding]:
    client = (
        ZhipuChatClient(settings.zhipuai_api_key, settings.zhipuai_vlm_model)
        if settings.zhipuai_api_key
        else None
    )
    keyframes_by_segment = {item.segment_id: item for item in keyframes}
    results: list[SegmentUnderstanding] = []
    for segment in segments:
        keyframe = keyframes_by_segment.get(segment.segment_id)
        dialogue, transcript_refs = _dialogue_for_segment(segment, transcript_chunks)
        if client is None:
            if not settings.allow_model_fallback:
                raise ModelClientError("ZHIPUAI_API_KEY is required for VLM segment understanding")
            payload = _fallback_understanding_payload(dialogue)
        else:
            if keyframe is None:
                raise ModelClientError(f"missing keyframe for segment {segment.segment_id}")
            try:
                payload = client.complete_json_with_image(
                    prompt=VLM_PROMPT,
                    image_data_url=_image_data_url(
                        _resolve_keyframe_path(keyframe.image_uri, settings.output_root)
                    ),
                    extra_payload={
                        "segment_id": segment.segment_id,
                        "time_range": {"start_ms": segment.start_ms, "end_ms": segment.end_ms},
                        "dialogue_raw": dialogue,
                    },
                )
            except ModelClientError as exc:
                if not settings.allow_model_fallback:
                    raise
                payload = _fallback_understanding_payload(dialogue)
        results.append(
            SegmentUnderstanding.model_validate(
                {
                    "segment_understanding_id": f"su_{segment.segment_id}",
                    "segment_id": segment.segment_id,
                    "series_id": segment.series_id,
                    "episode_id": segment.episode_id,
                    "start_ms": segment.start_ms,
                    "end_ms": segment.end_ms,
                    "keyframe_ids": segment.keyframe_ids,
                    "transcript_refs": transcript_refs,
                    "dialogue_raw": dialogue,
                    **payload,
                }
            )
        )
    return results


def _dialogue_for_segment(
    segment: VideoSegment, transcript_chunks: list[TranscriptChunk]
) -> tuple[str, list[str]]:
    pieces = []
    refs = []
    for chunk in transcript_chunks:
        for asr in chunk.asr_segments:
            if segment.start_ms <= asr.start_ms and asr.end_ms <= segment.end_ms:
                pieces.append(asr.text)
                refs.append(f"{chunk.chunk_id}:{asr.asr_id}")
    return " ".join(pieces).strip(), refs


def _fallback_understanding_payload(dialogue: str) -> dict:
    conflict_markers = ("凭什么", "为什么", "滚", "住手", "不可能", "背叛")
    conflict_level = 4 if any(marker in dialogue for marker in conflict_markers) else 1
    summary_text = dialogue.strip() or "该片段暂无可用台词。"
    return {
        "visual_summary": f"本地 ASR 降级理解：{summary_text}",
        "scene": "未知场景",
        "main_actions": "根据 ASR 文本进行降级理解。",
        "emotion_hint": "冲突" if conflict_level >= 3 else "中性",
        "conflict_level": conflict_level,
        "visible_characters": [],
        "character_actions": [],
        "facial_expressions": "",
        "shot_cues": "",
        "sound_cues": "",
        "power_dynamic": "",
    }


def _image_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _resolve_keyframe_path(image_uri: str, output_root: Path) -> Path:
    path = Path(image_uri)
    if path.exists():
        return path
    normalized = image_uri.replace("\\", "/")
    marker = "/outputs/"
    if marker in normalized:
        relative_output_path = normalized.split(marker, 1)[1]
        for root in (output_root, Path("outputs")):
            candidate = root.joinpath(*relative_output_path.split("/"))
            if candidate.exists():
                return candidate.resolve()
        return output_root.joinpath(*relative_output_path.split("/"))
    return path
