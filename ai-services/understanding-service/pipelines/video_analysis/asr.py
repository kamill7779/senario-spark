from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from app.config import Settings
from app.model_clients import ModelClientError
from schemas.video import TranscriptChunk


class ZhipuASRClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def transcribe(self, audio_path: Path) -> dict[str, Any]:
        with audio_path.open("rb") as audio_file:
            response = requests.post(
                "https://open.bigmodel.cn/api/paas/v4/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data={"model": self.model, "stream": "false"},
                files={"file": (audio_path.name, audio_file, "audio/wav")},
                timeout=180,
            )
        if response.status_code >= 400:
            raise ModelClientError(f"Zhipu ASR request failed: {response.status_code} {response.text}")
        return response.json()


def transcribe_audio_chunks(
    settings: Settings,
    series_id: str,
    episode_id: str,
    audio_id: str,
    audio_chunk_paths: list[Path],
    chunk_ranges: list[tuple[int, int]],
) -> list[TranscriptChunk]:
    client = (
        ZhipuASRClient(settings.zhipuai_api_key, settings.zhipuai_asr_model)
        if settings.zhipuai_api_key
        else None
    )
    chunks: list[TranscriptChunk] = []
    for index, (path, (start_ms, end_ms)) in enumerate(zip(audio_chunk_paths, chunk_ranges, strict=True)):
        if client is None:
            if not settings.allow_model_fallback:
                raise ModelClientError("ZHIPUAI_API_KEY is required for ASR")
            chunk = _fallback_chunk(index, series_id, episode_id, audio_id, start_ms, end_ms)
        else:
            payload = client.transcribe(path)
            chunk = _chunk_from_asr_payload(
                index=index,
                series_id=series_id,
                episode_id=episode_id,
                audio_id=audio_id,
                start_ms=start_ms,
                end_ms=end_ms,
                payload=payload,
                provider="zhipuai",
                model=settings.zhipuai_asr_model,
            )
        chunks.append(chunk)
    return chunks


def _chunk_from_asr_payload(
    index: int,
    series_id: str,
    episode_id: str,
    audio_id: str,
    start_ms: int,
    end_ms: int,
    payload: dict[str, Any],
    provider: str,
    model: str,
) -> TranscriptChunk:
    id_prefix = f"{_safe_id_part(series_id)}_{_safe_id_part(episode_id)}"
    text = (
        payload.get("text")
        or payload.get("result", {}).get("text")
        or payload.get("data", {}).get("text")
        or _choice_text(payload)
        or ""
    )
    raw_segments = (
        payload.get("segments")
        or payload.get("result", {}).get("segments")
        or payload.get("data", {}).get("segments")
        or []
    )
    asr_segments = []
    for segment_index, segment in enumerate(raw_segments):
        seg_start = _to_ms(segment.get("start_ms", segment.get("start", 0))) + start_ms
        seg_end = _to_ms(segment.get("end_ms", segment.get("end", 0))) + start_ms
        asr_segments.append(
            {
                "asr_id": str(segment.get("id", segment.get("asr_id", segment_index + 1))),
                "start_ms": max(start_ms, seg_start),
                "end_ms": min(end_ms, seg_end if seg_end > seg_start else end_ms),
                "text": segment.get("text", "").strip(),
            }
        )
    if not asr_segments and text:
        asr_segments.append(
            {"asr_id": "1", "start_ms": start_ms, "end_ms": end_ms, "text": text.strip()}
        )
    return TranscriptChunk(
        chunk_id=f"aud_{id_prefix}_{index:03d}",
        audio_id=audio_id,
        series_id=series_id,
        episode_id=episode_id,
        start_ms=start_ms,
        end_ms=end_ms,
        text=text.strip(),
        provider=provider,
        model=model,
        asr_segments=asr_segments,
    )


def _fallback_chunk(
    index: int,
    series_id: str,
    episode_id: str,
    audio_id: str,
    start_ms: int,
    end_ms: int,
) -> TranscriptChunk:
    id_prefix = f"{_safe_id_part(series_id)}_{_safe_id_part(episode_id)}"
    text = f"Local ASR fallback chunk {index + 1}"
    return TranscriptChunk(
        chunk_id=f"aud_{id_prefix}_{index:03d}",
        audio_id=audio_id,
        series_id=series_id,
        episode_id=episode_id,
        start_ms=start_ms,
        end_ms=end_ms,
        text=text,
        provider="local_fallback",
        model="no_asr_model",
        asr_segments=[
            {
                "asr_id": "1",
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": text,
            }
        ],
    )


def _to_ms(value: Any) -> int:
    if isinstance(value, str):
        value = float(value)
    if isinstance(value, float) and value < 100000:
        return int(value * 1000)
    return int(value)


def _choice_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return message.get("content") or choices[0].get("text") or ""


def _safe_id_part(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").strip()
