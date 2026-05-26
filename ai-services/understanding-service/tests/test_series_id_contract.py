import pytest
from pydantic import ValidationError

from app.config import Settings
from app.workflow import AnalysisContext
from schemas.highlight import HighlightEvent
from schemas.script import ObservedScript
from schemas.taxonomy import TAXONOMY
from schemas.video import UnderstandingPackage


def test_highlight_event_requires_and_preserves_series_id():
    event = HighlightEvent.model_validate(
        {
            "highlight_id": "hl_series_001",
            "candidate_id": "hc_series_001",
            "series_id": "series_001",
            "episode_id": "ep_003",
            "taxonomy_version": TAXONOMY.taxonomy_version,
            "highlight_type": "identity_reveal",
            "secondary_highlight_types": [],
            "summary": "角色揭露隐藏身份。",
            "trigger_text_clean": "原来你就是当年那个人。",
            "trigger_text_raw": "原来你就是当年那个人",
            "primary_audience_emotion": "shock",
            "audience_emotions": ["shock"],
            "interaction_intent": "question",
            "sentiment_polarity": "mixed",
            "intensity": 0.8,
            "confidence": 0.9,
            "timing": {"start_ms": 1000, "peak_ms": 1500, "end_ms": 2000},
            "source_scene_id": "scene_001",
            "source_segment_ids": ["seg_001"],
            "evidence": [
                {
                    "type": "asr",
                    "segment_id": "seg_001",
                    "transcript_chunk_id": "aud_001",
                    "asr_id": "1",
                    "text": "原来你就是当年那个人",
                    "start_ms": 1000,
                    "end_ms": 2000,
                }
            ],
            "review_status": "pending",
            "enabled": False,
        }
    )

    assert event.series_id == "series_001"


def test_highlight_event_rejects_missing_series_id():
    payload = {
        "highlight_id": "hl_series_001",
        "candidate_id": "hc_series_001",
        "episode_id": "ep_003",
        "taxonomy_version": TAXONOMY.taxonomy_version,
        "highlight_type": "identity_reveal",
        "secondary_highlight_types": [],
        "summary": "角色揭露隐藏身份。",
        "trigger_text_clean": "原来你就是当年那个人。",
        "trigger_text_raw": "原来你就是当年那个人",
        "primary_audience_emotion": "shock",
        "audience_emotions": ["shock"],
        "interaction_intent": "question",
        "sentiment_polarity": "mixed",
        "intensity": 0.8,
        "confidence": 0.9,
        "timing": {"start_ms": 1000, "peak_ms": 1500, "end_ms": 2000},
        "source_scene_id": "scene_001",
        "source_segment_ids": ["seg_001"],
        "evidence": [
            {
                "type": "asr",
                "segment_id": "seg_001",
                "transcript_chunk_id": "aud_001",
                "asr_id": "1",
                "text": "原来你就是当年那个人",
                "start_ms": 1000,
                "end_ms": 2000,
            }
        ],
    }

    with pytest.raises(ValidationError):
        HighlightEvent.model_validate(payload)


def test_observed_script_and_understanding_package_carry_series_id():
    script = ObservedScript.model_validate(
        {
            "script_id": "script_series_001_ep_003_v1",
            "series_id": "series_001",
            "episode_id": "ep_003",
            "title": "第三集",
            "summary": "本集摘要。",
            "characters": [],
            "scenes": [],
        }
    )
    package = UnderstandingPackage(
        package_id="upkg_series_001_ep_003_v1",
        series_id="series_001",
        episode_id="ep_003",
        video_id="vid_series_001_ep_003",
        pipeline_version="analysis_pipeline_v0.1",
        video_asset_id="vid_series_001_ep_003",
        audio_asset_id="audio_series_001_ep_003",
        transcript_chunk_ids=[],
        video_segment_ids=[],
        segment_understanding_ids=[],
    )

    assert "series_id: series_001" in script.to_markdown()
    assert package.series_id == "series_001"


def test_analysis_context_uses_series_episode_output_path():
    settings = Settings.from_env()

    context = AnalysisContext(
        series_id="series_001",
        episode_id="ep_003",
        video_input=r"C:\Users\23999\Downloads\第3集.mp4",
        settings=settings,
    )

    assert context.job_id == "job_series_001_ep_003_analysis_v0_1"
    assert context.video_id == "vid_series_001_ep_003"
    assert str(context.output_dir).endswith("outputs\\series_001\\ep_003") or str(
        context.output_dir
    ).endswith("outputs/series_001/ep_003")


def test_deployment_config_exposes_series_id():
    service_root = __import__("pathlib").Path(__file__).resolve().parents[1]
    repo_root = service_root.parents[1]

    env_example = (service_root / ".env.example").read_text(encoding="utf-8")
    compose = (service_root / "docker-compose.yml").read_text(encoding="utf-8")
    k8s = (
        repo_root / "deploy" / "k8s" / "understanding-service" / "analysis-job.yaml"
    ).read_text(encoding="utf-8")

    assert "SERIES_ID=series_001" in env_example
    assert "SERIES_ID:" in compose
    assert "SERIES_ID:" in k8s
