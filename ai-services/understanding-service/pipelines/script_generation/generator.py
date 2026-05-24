from __future__ import annotations

from app.config import Settings
from app.model_clients import DeepSeekJSONClient, ModelClientError
from schemas.script import ObservedScript
from schemas.video import SegmentUnderstanding, TranscriptChunk, VideoSegment


SCRIPT_PROMPT = """You generate an observed script from short-drama evidence.
Return only JSON matching ObservedScript:
{
  "script_id": string,
  "series_id": string,
  "episode_id": string,
  "title": string,
  "summary": string,
  "characters": [{"character_id": string, "name": string, "aliases": [string], "description": string}],
  "scenes": [{
    "scene_id": string,
    "start_ms": integer,
    "end_ms": integer,
    "location": string,
    "summary": string,
    "characters": [string],
    "source_segment_ids": [string],
    "beats": [{
      "beat_id": string,
      "type": "dialogue" | "action",
      "speaker": string | null,
      "content": string,
      "character_emotion": string | null,
      "source_segment_ids": [string]
    }]
  }]
}
Every scene and beat must keep source_segment_ids from the input evidence."""


def generate_observed_script(
    settings: Settings,
    series_id: str,
    episode_id: str,
    segments: list[VideoSegment],
    transcript_chunks: list[TranscriptChunk],
    understandings: list[SegmentUnderstanding],
) -> ObservedScript:
    if not settings.deepseek_api_key:
        if not settings.allow_model_fallback:
            raise ModelClientError("DEEPSEEK_API_KEY is required for script generation")
        return build_fallback_observed_script(
            series_id,
            episode_id,
            segments,
            transcript_chunks,
            understandings,
        )
    client = DeepSeekJSONClient(settings.deepseek_api_key, settings.deepseek_model)
    payload = client.complete_json(
        SCRIPT_PROMPT,
        {
            "series_id": series_id,
            "episode_id": episode_id,
            "segments": [segment.model_dump(mode="json") for segment in segments],
            "transcript_chunks": [chunk.model_dump(mode="json") for chunk in transcript_chunks],
            "segment_understandings": [
                understanding.model_dump(mode="json") for understanding in understandings
            ],
        },
    )
    script_payload = payload.get("observed_script", payload)
    script_payload.setdefault("script_id", f"script_{_safe_id_part(series_id)}_{_safe_id_part(episode_id)}_v1")
    script_payload.setdefault("series_id", series_id)
    script_payload.setdefault("episode_id", episode_id)
    return ObservedScript.model_validate(script_payload)


def build_fallback_observed_script(
    series_id: str,
    episode_id: str,
    segments: list[VideoSegment],
    transcript_chunks: list[TranscriptChunk],
    understandings: list[SegmentUnderstanding],
) -> ObservedScript:
    understanding_by_segment = {item.segment_id: item for item in understandings}
    scenes = []
    for index, segment in enumerate(segments):
        understanding = understanding_by_segment.get(segment.segment_id)
        dialogue = _dialogue_for_segment(segment, transcript_chunks)
        summary = (
            understanding.visual_summary
            if understanding
            else dialogue or f"Segment {segment.segment_id} observation."
        )
        scenes.append(
            {
                "scene_id": f"scene_{index:03d}",
                "start_ms": segment.start_ms,
                "end_ms": segment.end_ms,
                "location": understanding.scene if understanding else "unknown",
                "summary": summary,
                "characters": [],
                "source_segment_ids": [segment.segment_id],
                "beats": [
                    {
                        "beat_id": f"beat_scene_{index:03d}_001",
                        "type": "dialogue" if dialogue else "action",
                        "speaker": None,
                        "content": dialogue or summary,
                        "character_emotion": understanding.emotion_hint if understanding else None,
                        "source_segment_ids": [segment.segment_id],
                    }
                ],
            }
        )
    transcript_summary = " ".join(chunk.text for chunk in transcript_chunks if chunk.text).strip()
    return ObservedScript.model_validate(
        {
            "script_id": f"script_{_safe_id_part(series_id)}_{_safe_id_part(episode_id)}_v1",
            "series_id": series_id,
            "episode_id": episode_id,
            "title": f"Observed Script {episode_id}",
            "summary": transcript_summary or "Video observations generated from local segment evidence.",
            "characters": [],
            "scenes": scenes,
        }
    )


def _dialogue_for_segment(segment: VideoSegment, transcript_chunks: list[TranscriptChunk]) -> str:
    pieces: list[str] = []
    for chunk in transcript_chunks:
        for asr in chunk.asr_segments:
            if segment.start_ms <= asr.start_ms and asr.end_ms <= segment.end_ms:
                pieces.append(asr.text)
    return " ".join(pieces).strip()


def _safe_id_part(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").strip()
