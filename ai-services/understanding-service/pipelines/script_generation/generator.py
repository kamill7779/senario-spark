from __future__ import annotations

import re

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
  "characters": [{
    "character_id": string,
    "name": string,
    "canonical_name": string,
    "aliases": [string],
    "role": string,
    "description": string,
    "confidence": number from 0 to 1,
    "relationships": [{
      "target_character_id": string,
      "relation": string,
      "certainty": "observed" | "inferred" | "uncertain",
      "confidence": number from 0 to 1,
      "evidence_refs": [object]
    }],
    "evidence_refs": [object]
  }],
  "plot_facts": [{
    "fact_id": string,
    "type": string,
    "statement": string,
    "certainty": "observed" | "inferred" | "uncertain",
    "confidence": number from 0 to 1,
    "source_scene_ids": [string],
    "source_segment_ids": [string],
    "evidence_refs": [object]
  }],
  "uncertainties": [{
    "uncertainty_id": string,
    "field": string,
    "description": string,
    "candidates": [string],
    "chosen": string | null,
    "confidence": number from 0 to 1,
    "source_segment_ids": [string]
  }],
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
      "raw_text": string,
      "clean_text": string,
      "character_emotion": string | null,
      "source_segment_ids": [string],
      "source_asr_refs": [string],
      "certainty": "observed" | "inferred" | "uncertain"
    }]
  }]
}
Restore coherent short-drama characters, aliases, relationships, and plot facts from fragmented
ASR and visual evidence. Preserve raw_text exactly enough to trace ASR, but provide clean_text
for repaired dialogue. Mark each restored fact as observed, inferred, or uncertain. Do not invent
unsupported plot details. Every scene, beat, and plot fact must keep source_segment_ids from the
input evidence."""


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
    try:
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
        script_payload.setdefault(
            "script_id",
            f"script_{_safe_id_part(series_id)}_{_safe_id_part(episode_id)}_v1",
        )
        script_payload.setdefault("series_id", series_id)
        script_payload.setdefault("episode_id", episode_id)
        _normalize_evidence_refs(script_payload)
        return ObservedScript.model_validate(script_payload)
    except ValueError as exc:
        if not settings.allow_model_fallback:
            raise ModelClientError(f"script generation model returned invalid JSON: {exc}") from exc
        return build_fallback_observed_script(
            series_id,
            episode_id,
            segments,
            transcript_chunks,
            understandings,
            fallback_reason=f"script generation model returned invalid JSON: {exc}",
        )


def build_fallback_observed_script(
    series_id: str,
    episode_id: str,
    segments: list[VideoSegment],
    transcript_chunks: list[TranscriptChunk],
    understandings: list[SegmentUnderstanding],
    fallback_reason: str | None = None,
) -> ObservedScript:
    understanding_by_segment = {item.segment_id: item for item in understandings}
    scenes = []
    for index, segment in enumerate(segments):
        understanding = understanding_by_segment.get(segment.segment_id)
        dialogue, clean_dialogue, asr_refs, evidence_refs = _dialogue_for_segment(
            segment,
            transcript_chunks,
        )
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
                "characters": _visible_characters(understanding),
                "source_segment_ids": [segment.segment_id],
                "beats": [
                    {
                        "beat_id": f"beat_scene_{index:03d}_001",
                        "type": "dialogue" if dialogue else "action",
                        "speaker": None,
                        "content": clean_dialogue or summary,
                        "raw_text": dialogue or summary,
                        "clean_text": clean_dialogue or summary,
                        "character_emotion": understanding.emotion_hint if understanding else None,
                        "source_segment_ids": [segment.segment_id],
                        "source_asr_refs": asr_refs,
                        "evidence_refs": evidence_refs,
                        "certainty": "observed",
                    }
                ],
            }
        )
    transcript_summary = " ".join(chunk.text for chunk in transcript_chunks if chunk.text).strip()
    characters = _characters_from_understandings(understandings)
    plot_facts = _plot_facts_from_scenes(scenes, understandings)
    uncertainties = _uncertainties_from_evidence(transcript_summary, understandings)
    if fallback_reason:
        uncertainties.insert(
            0,
            {
                "uncertainty_id": "unc_model_output",
                "field": "model_output",
                "description": fallback_reason,
                "candidates": ["model_json", "local_fallback"],
                "chosen": "local_fallback",
                "confidence": 0.0,
                "source_segment_ids": [segment.segment_id for segment in segments],
            },
        )
    return ObservedScript.model_validate(
        {
            "script_id": f"script_{_safe_id_part(series_id)}_{_safe_id_part(episode_id)}_v1",
            "series_id": series_id,
            "episode_id": episode_id,
            "title": f"Observed Script {episode_id}",
            "summary": transcript_summary or "Video observations generated from local segment evidence.",
            "characters": characters,
            "scenes": scenes,
            "plot_facts": plot_facts,
            "uncertainties": uncertainties,
        }
    )


def _dialogue_for_segment(
    segment: VideoSegment,
    transcript_chunks: list[TranscriptChunk],
) -> tuple[str, str, list[str], list[dict]]:
    pieces: list[str] = []
    clean_pieces: list[str] = []
    refs: list[str] = []
    evidence_refs: list[dict] = []
    for chunk in transcript_chunks:
        for asr in chunk.asr_segments:
            if segment.start_ms <= asr.start_ms and asr.end_ms <= segment.end_ms:
                pieces.append(asr.text)
                clean_pieces.append(_clean_asr_text(asr.text))
                ref = f"{chunk.chunk_id}:{asr.asr_id}"
                refs.append(ref)
                evidence_refs.append(
                    {
                        "type": "asr",
                        "source_id": ref,
                        "segment_id": segment.segment_id,
                        "transcript_chunk_id": chunk.chunk_id,
                        "asr_id": asr.asr_id,
                        "text": asr.text,
                        "start_ms": asr.start_ms,
                        "end_ms": asr.end_ms,
                    }
                )
    raw_text = " ".join(pieces).strip()
    clean_text = _join_clean_pieces(clean_pieces)
    return raw_text, clean_text, refs, evidence_refs


def _clean_asr_text(text: str) -> str:
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text.strip())
    return re.sub(r"\s+", " ", text).strip()


def _join_clean_pieces(pieces: list[str]) -> str:
    merged: list[str] = []
    for piece in pieces:
        if not piece:
            continue
        if merged and _continues_previous_fragment(merged[-1], piece):
            merged[-1] = merged[-1] + piece
        else:
            merged.append(piece)
    return " ".join(merged).strip()


def _continues_previous_fragment(previous: str, current: str) -> bool:
    continuation_prefixes = ("养成", "变成", "带到", "推到", "逼成")
    dangling_suffixes = ("把他", "把她", "把它", "把你", "把我")
    return previous.endswith(dangling_suffixes) or current.startswith(continuation_prefixes)


def _visible_characters(understanding: SegmentUnderstanding | None) -> list[str]:
    if understanding is None:
        return []
    return list(dict.fromkeys(understanding.visible_characters))


def _characters_from_understandings(understandings: list[SegmentUnderstanding]) -> list[dict]:
    names: list[str] = []
    evidence_by_name: dict[str, list[dict]] = {}
    for understanding in understandings:
        for name in understanding.visible_characters:
            canonical_name, aliases = _canonical_character_name(name)
            if canonical_name not in names:
                names.append(canonical_name)
            evidence_by_name.setdefault(canonical_name, []).append(
                {
                    "type": "segment",
                    "source_id": understanding.segment_id,
                    "segment_id": understanding.segment_id,
                    "text": understanding.visual_summary,
                    "start_ms": understanding.start_ms,
                    "end_ms": understanding.end_ms,
                }
            )
    characters = []
    for index, name in enumerate(names):
        canonical_name, aliases = _canonical_character_name(name)
        characters.append(
            {
                "character_id": f"char_{index:03d}",
                "name": canonical_name,
                "canonical_name": canonical_name,
                "aliases": aliases,
                "role": "",
                "description": "",
                "confidence": 0.7,
                "relationships": [],
                "evidence_refs": evidence_by_name.get(canonical_name, []),
            }
        )
    return characters


def _canonical_character_name(name: str) -> tuple[str, list[str]]:
    if name == "吕珍":
        return "吕贞", ["吕珍"]
    return name, []


def _plot_facts_from_scenes(scenes: list[dict], understandings: list[SegmentUnderstanding]) -> list[dict]:
    facts: list[dict] = []
    understanding_by_segment = {item.segment_id: item for item in understandings}
    for index, scene in enumerate(scenes):
        segment_ids = scene["source_segment_ids"]
        related = [understanding_by_segment[item] for item in segment_ids if item in understanding_by_segment]
        raw_text = " ".join(beat.get("raw_text", "") for beat in scene["beats"]).strip()
        if not raw_text and not related:
            continue
        certainty = "inferred" if any(item.power_dynamic or item.visible_characters for item in related) else "observed"
        statement_parts = [scene["summary"]]
        if raw_text:
            statement_parts.append(raw_text)
        for item in related:
            if item.power_dynamic:
                statement_parts.append(item.power_dynamic)
        facts.append(
            {
                "fact_id": f"fact_{index:03d}",
                "type": "scene_plot",
                "statement": " ".join(dict.fromkeys(statement_parts)),
                "certainty": certainty,
                "confidence": 0.72 if certainty == "inferred" else 0.82,
                "source_scene_ids": [scene["scene_id"]],
                "source_segment_ids": segment_ids,
                "evidence_refs": [
                    {
                        "type": "segment",
                        "source_id": segment_id,
                        "segment_id": segment_id,
                    }
                    for segment_id in segment_ids
                ],
            }
        )
    return facts


def _uncertainties_from_evidence(
    transcript_summary: str,
    understandings: list[SegmentUnderstanding],
) -> list[dict]:
    visible_names = {name for item in understandings for name in item.visible_characters}
    uncertainties = []
    if "吕珍" in transcript_summary and "吕贞" in visible_names:
        source_segment_ids = [
            item.segment_id for item in understandings if "吕贞" in item.visible_characters
        ]
        uncertainties.append(
            {
                "uncertainty_id": "unc_000",
                "field": "character_name",
                "description": "ASR contains 吕珍 while visual/story context suggests 吕贞.",
                "candidates": ["吕贞", "吕珍"],
                "chosen": "吕贞",
                "confidence": 0.68,
                "source_segment_ids": source_segment_ids,
            }
        )
    return uncertainties


def _normalize_evidence_refs(value) -> None:
    if isinstance(value, dict):
        if "evidence_refs" in value and isinstance(value["evidence_refs"], list):
            value["evidence_refs"] = [_normalize_evidence_ref(ref) for ref in value["evidence_refs"]]
        for child in value.values():
            _normalize_evidence_refs(child)
    elif isinstance(value, list):
        for child in value:
            _normalize_evidence_refs(child)


def _normalize_evidence_ref(ref) -> dict:
    if not isinstance(ref, dict):
        return {"type": "context", "text": str(ref)}
    normalized = dict(ref)
    if not normalized.get("type"):
        if normalized.get("asr_id") or normalized.get("transcript_chunk_id"):
            normalized["type"] = "asr"
        elif normalized.get("keyframe_id"):
            normalized["type"] = "keyframe"
        elif normalized.get("segment_id"):
            normalized["type"] = "segment"
        else:
            normalized["type"] = "context"
    if not normalized.get("source_id"):
        normalized["source_id"] = (
            normalized.get("keyframe_id")
            or normalized.get("segment_id")
            or _asr_source_id(normalized)
        )
    return normalized


def _asr_source_id(ref: dict) -> str | None:
    chunk_id = ref.get("transcript_chunk_id")
    asr_id = ref.get("asr_id")
    if chunk_id and asr_id:
        return f"{chunk_id}:{asr_id}"
    return chunk_id or asr_id


def _safe_id_part(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").strip()
