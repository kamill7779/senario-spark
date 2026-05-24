import copy

import pytest
from pydantic import ValidationError

from schemas.highlight import HighlightEvent
from schemas.taxonomy import TAXONOMY


def valid_highlight_event_payload() -> dict:
    return {
        "highlight_id": "hl_ep_003_001",
        "candidate_id": "hc_ep_003_001",
        "series_id": "series_001",
        "episode_id": "ep_003",
        "taxonomy_version": TAXONOMY.taxonomy_version,
        "highlight_type": "reversal",
        "secondary_highlight_types": ["face_slap"],
        "summary": "雨儿讽刺沈慧珍演了十五年的慈母，揭开表面温情后的反转。",
        "trigger_text_clean": "沈慧珍，演了十五年的慈母，也真是难为你们了。",
        "trigger_text_raw": "沈慧珍 演了十五年的刺，也真是难为你们了。",
        "primary_audience_emotion": "shock",
        "audience_emotions": ["shock", "satisfaction"],
        "interaction_intent": "tease",
        "sentiment_polarity": "mixed",
        "intensity": 0.9,
        "confidence": 0.82,
        "timing": {
            "start_ms": 106800,
            "peak_ms": 108350,
            "end_ms": 110900,
        },
        "source_scene_id": "scene_05",
        "source_segment_ids": ["seg_012", "seg_013"],
        "evidence": [
            {
                "type": "asr",
                "segment_id": "seg_013",
                "transcript_chunk_id": "aud_005",
                "asr_id": "2",
                "text": "沈慧珍",
                "start_ms": 106800,
                "end_ms": 107600,
            },
            {
                "type": "visual",
                "segment_id": "seg_013",
                "keyframe_id": "kf_seg_013_108000",
                "description": "年轻男子侧目凝视，神情隐忍讽刺。",
            },
        ],
        "review_status": "pending",
        "enabled": False,
    }


def test_taxonomy_v01_contains_required_enums():
    assert TAXONOMY.taxonomy_version == "highlight_taxonomy_v0.1"
    assert "conflict" in TAXONOMY.highlight_type_enum
    assert "cliffhanger" in TAXONOMY.highlight_type_enum
    assert "shock" in TAXONOMY.audience_emotion_enum
    assert "predict" in TAXONOMY.interaction_intent_enum


def test_highlight_event_accepts_contract_payload():
    event = HighlightEvent.model_validate(valid_highlight_event_payload())

    assert event.highlight_type == "reversal"
    assert event.review_status == "pending"
    assert event.enabled is False
    assert event.timing.start_ms == 106800
    assert event.evidence[0].type == "asr"


def test_highlight_event_rejects_illegal_highlight_type():
    payload = valid_highlight_event_payload()
    payload["highlight_type"] = "invented_type"

    with pytest.raises(ValidationError):
        HighlightEvent.model_validate(payload)


def test_highlight_event_rejects_illegal_secondary_type():
    payload = valid_highlight_event_payload()
    payload["secondary_highlight_types"] = ["face_slap", "made_up"]

    with pytest.raises(ValidationError):
        HighlightEvent.model_validate(payload)


def test_highlight_event_rejects_invalid_timing_order():
    payload = copy.deepcopy(valid_highlight_event_payload())
    payload["timing"]["peak_ms"] = 111000

    with pytest.raises(ValidationError):
        HighlightEvent.model_validate(payload)
