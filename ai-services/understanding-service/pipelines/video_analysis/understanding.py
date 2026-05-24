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
  "conflict_level": integer from 0 to 5
}
Use the keyframe and nearby ASR text as evidence. Do not invent IDs."""


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
            payload = client.complete_json_with_image(
                prompt=VLM_PROMPT,
                image_data_url=_image_data_url(Path(keyframe.image_uri)),
                extra_payload={
                    "segment_id": segment.segment_id,
                    "time_range": {"start_ms": segment.start_ms, "end_ms": segment.end_ms},
                    "dialogue_raw": dialogue,
                },
            )
        results.append(
            SegmentUnderstanding.model_validate(
                {
                    "segment_understanding_id": f"su_{segment.segment_id}",
                    "segment_id": segment.segment_id,
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
    return {
        "visual_summary": "Local fallback visual observation; VLM was not configured.",
        "scene": "unknown",
        "main_actions": "No VLM model output available.",
        "emotion_hint": "conflict" if conflict_level >= 3 else "neutral",
        "conflict_level": conflict_level,
    }


def _image_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
