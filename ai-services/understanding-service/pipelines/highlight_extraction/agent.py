from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import Settings
from app.model_clients import DeepSeekJSONClient, ModelClientError
from schemas.highlight import HighlightCandidate, HighlightEvent
from schemas.taxonomy import TAXONOMY

from .tools import HighlightToolbox


HIGHLIGHT_PROMPT = """You are the controlled SenarioSpark Highlight Extraction Agent.
Input includes observed_script, evidence package summaries, and a fixed taxonomy.
Return only JSON:
{
  "candidates": [
    {
      "candidate_id": string,
      "series_id": string,
      "episode_id": string,
      "taxonomy_version": string,
      "source_scene_id": string,
      "source_segment_ids": [string],
      "highlight_type": one taxonomy highlight_type,
      "secondary_highlight_types": [taxonomy highlight_type],
      "summary": string,
      "trigger_text_clean": string,
      "primary_audience_emotion": one taxonomy audience_emotion,
      "audience_emotions": [taxonomy audience_emotion],
      "interaction_intent": one taxonomy interaction_intent,
      "sentiment_polarity": "positive" | "negative" | "mixed" | "neutral",
      "intensity": number from 0 to 1,
      "confidence": number from 0 to 1
    }
  ]
}
Do not invent taxonomy values. Use only source_scene_id and source_segment_ids that exist in observed_script.
Use restored plot_facts, canonical character aliases, beat clean_text, and uncertainty notes to
understand why a short-drama moment is emotionally interactive. Still anchor timing and trigger
text through ASR, segment, and keyframe evidence tools; never rely on summary-only timing."""


class HighlightCandidateBatch(BaseModel):
    candidates: list[HighlightCandidate] = Field(default_factory=list)


def extract_highlights(
    settings: Settings, toolbox: HighlightToolbox
) -> tuple[list[HighlightCandidate], list[HighlightEvent]]:
    if not settings.deepseek_api_key:
        if not settings.allow_model_fallback:
            raise ModelClientError("DEEPSEEK_API_KEY is required for highlight extraction")
        return RuleBasedHighlightExtractor().extract(toolbox)
    return DeepSeekHighlightExtractor(settings.deepseek_api_key, settings.deepseek_model).extract(toolbox)


class DeepSeekHighlightExtractor:
    def __init__(self, api_key: str, model: str):
        self.client = DeepSeekJSONClient(api_key, model)

    def extract(self, toolbox: HighlightToolbox) -> tuple[list[HighlightCandidate], list[HighlightEvent]]:
        payload = self.client.complete_json(
            HIGHLIGHT_PROMPT,
            {
                "observed_script": toolbox.observed_script.model_dump(mode="json"),
                "segment_understandings": [
                    item.model_dump(mode="json") for item in toolbox.segment_understandings
                ],
                "taxonomy": toolbox.taxonomy.as_prompt_payload(),
            },
        )
        candidate_payloads = payload.get("candidates", [])
        for candidate_payload in candidate_payloads:
            candidate_payload.setdefault("series_id", toolbox.observed_script.series_id)
            candidate_payload.setdefault("episode_id", toolbox.observed_script.episode_id)
        batch = HighlightCandidateBatch.model_validate({"candidates": candidate_payloads})
        resolver = RuleBasedHighlightExtractor()
        candidates = batch.candidates
        event_payloads = [resolver._resolve_candidate(toolbox, candidate) for candidate in candidates]
        events = toolbox.submit_highlight_events(event_payloads)
        return candidates, events


class RuleBasedHighlightExtractor:
    def extract(self, toolbox: HighlightToolbox) -> tuple[list[HighlightCandidate], list[HighlightEvent]]:
        candidate_payloads = self._candidate_payloads(toolbox)
        candidates = [HighlightCandidate.model_validate(item) for item in candidate_payloads]
        event_payloads = [self._resolve_candidate(toolbox, candidate) for candidate in candidates]
        events = toolbox.submit_highlight_events(event_payloads)
        return candidates, events

    def _candidate_payloads(self, toolbox: HighlightToolbox) -> list[dict]:
        candidates: list[dict] = []
        id_prefix = f"{_safe_id_part(toolbox.observed_script.series_id)}_{_safe_id_part(toolbox.observed_script.episode_id)}"
        for index, scene in enumerate(toolbox.observed_script.scenes):
            segment_ids = scene.source_segment_ids
            if not segment_ids:
                continue
            conflict_level = _max_conflict_level(toolbox, segment_ids)
            dialogue = _scene_dialogue(toolbox, segment_ids)
            if conflict_level == 0 and _looks_conflict_dialogue(dialogue):
                conflict_level = 4
            if conflict_level < 3 and not dialogue:
                continue
            highlight_type = "conflict" if conflict_level >= 3 else "cliffhanger"
            candidates.append(
                {
                    "candidate_id": f"hc_{id_prefix}_{index:03d}",
                    "series_id": toolbox.observed_script.series_id,
                    "episode_id": toolbox.observed_script.episode_id,
                    "taxonomy_version": toolbox.taxonomy.taxonomy_version,
                    "source_scene_id": scene.scene_id,
                    "source_segment_ids": segment_ids,
                    "highlight_type": highlight_type,
                    "secondary_highlight_types": [],
                    "summary": scene.summary,
                    "trigger_text_clean": dialogue or scene.summary,
                    "primary_audience_emotion": "anger" if highlight_type == "conflict" else "curiosity",
                    "audience_emotions": ["anger"] if highlight_type == "conflict" else ["curiosity"],
                    "interaction_intent": "vent" if highlight_type == "conflict" else "predict",
                    "sentiment_polarity": "negative" if highlight_type == "conflict" else "mixed",
                    "intensity": min(1.0, max(0.55, conflict_level / 5)),
                    "confidence": 0.62,
                }
            )
        if not candidates and toolbox.observed_script.scenes:
            scene = toolbox.observed_script.scenes[0]
            candidates.append(
                {
                    "candidate_id": f"hc_{id_prefix}_000",
                    "series_id": toolbox.observed_script.series_id,
                    "episode_id": toolbox.observed_script.episode_id,
                    "taxonomy_version": TAXONOMY.taxonomy_version,
                    "source_scene_id": scene.scene_id,
                    "source_segment_ids": scene.source_segment_ids,
                    "highlight_type": "cliffhanger",
                    "secondary_highlight_types": [],
                    "summary": scene.summary,
                    "trigger_text_clean": scene.summary,
                    "primary_audience_emotion": "curiosity",
                    "audience_emotions": ["curiosity"],
                    "interaction_intent": "predict",
                    "sentiment_polarity": "mixed",
                    "intensity": 0.5,
                    "confidence": 0.5,
                }
            )
        return candidates[:5]

    def _resolve_candidate(
        self, toolbox: HighlightToolbox, candidate: HighlightCandidate
    ) -> dict:
        scene = toolbox.get_scene(candidate.source_scene_id)
        asr_evidence = []
        keyframe_evidence = []
        for segment_id in candidate.source_segment_ids:
            for asr in toolbox.get_asr_segments(segment_id=segment_id):
                asr_evidence.append(
                    {
                        "type": "asr",
                        "segment_id": asr["segment_id"] or segment_id,
                        "transcript_chunk_id": asr["transcript_chunk_id"],
                        "asr_id": asr["asr_id"],
                        "text": asr["text"],
                        "start_ms": asr["start_ms"],
                        "end_ms": asr["end_ms"],
                    }
                )
            for keyframe in toolbox.get_keyframes(segment_id):
                keyframe_evidence.append(
                    {
                        "type": "visual",
                        "segment_id": segment_id,
                        "keyframe_id": keyframe["keyframe_id"],
                        "description": f"Keyframe evidence at {keyframe['timestamp_ms']}ms.",
                    }
                )
        evidence = asr_evidence[:3] + keyframe_evidence[:1]
        if not evidence:
            evidence.append(
                {
                    "type": "context",
                    "segment_id": candidate.source_segment_ids[0],
                    "description": scene["summary"],
                }
            )
        timed = [item for item in evidence if item.get("start_ms") is not None]
        if timed:
            start_ms = min(item["start_ms"] for item in timed)
            end_ms = max(item["end_ms"] for item in timed)
            peak_ms = start_ms + (end_ms - start_ms) // 2
            trigger_text_raw = " ".join(item.get("text", "") for item in timed).strip()
        else:
            start_ms = scene["start_ms"]
            end_ms = scene["end_ms"]
            peak_ms = start_ms + (end_ms - start_ms) // 2
            trigger_text_raw = candidate.trigger_text_clean
        return {
            **candidate.model_dump(mode="json"),
            "highlight_id": candidate.candidate_id.replace("hc_", "hl_", 1),
            "trigger_text_raw": trigger_text_raw or candidate.trigger_text_clean,
            "timing": {
                "start_ms": start_ms,
                "peak_ms": peak_ms,
                "end_ms": end_ms,
            },
            "evidence": evidence,
            "review_status": "pending",
            "enabled": False,
        }


def _max_conflict_level(toolbox: HighlightToolbox, segment_ids: list[str]) -> int:
    levels = [
        item.conflict_level
        for item in toolbox.segment_understandings
        if item.segment_id in set(segment_ids)
    ]
    return max(levels) if levels else 0


def _scene_dialogue(toolbox: HighlightToolbox, segment_ids: list[str]) -> str:
    pieces: list[str] = []
    for segment_id in segment_ids:
        pieces.extend(item["text"] for item in toolbox.get_asr_segments(segment_id=segment_id))
    return " ".join(pieces).strip()


def _looks_conflict_dialogue(dialogue: str) -> bool:
    markers = ("凭什么", "为什么", "你敢", "不可能", "滚", "住手", "背叛")
    return any(marker in dialogue for marker in markers)


def _safe_id_part(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").strip()
