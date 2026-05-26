from app.config import Settings
from app.model_clients import ModelClientError
from pipelines.highlight_extraction.agent import RuleBasedHighlightExtractor
from pipelines.highlight_extraction.tools import HighlightToolbox
from pipelines.script_generation.generator import build_fallback_observed_script
from pipelines.video_analysis.media import plan_audio_chunks, plan_video_segments
from pipelines.video_analysis import understanding
from pipelines.video_analysis.understanding import build_segment_understandings
from pipelines.video_analysis.understanding import _resolve_keyframe_path
from schemas.taxonomy import TAXONOMY
from schemas.video import Keyframe, SegmentUnderstanding, TranscriptChunk, VideoSegment


def test_plan_audio_chunks_covers_duration_with_tail_chunk():
    chunks = plan_audio_chunks(duration_ms=45000, chunk_ms=20000)

    assert chunks == [(0, 20000), (20000, 40000), (40000, 45000)]


def test_plan_video_segments_sets_midpoint_keyframe_id():
    segments = plan_video_segments(
        "vid_series_001_ep_003",
        "series_001",
        "ep_003",
        duration_ms=17000,
        segment_ms=8000,
    )

    assert [segment.segment_id for segment in segments] == [
        "seg_series_001_ep_003_000",
        "seg_series_001_ep_003_001",
        "seg_series_001_ep_003_002",
    ]
    assert segments[-1].start_ms == 16000
    assert segments[-1].end_ms == 17000
    assert segments[0].keyframe_ids == ["kf_seg_series_001_ep_003_000_4000"]


def test_resolve_keyframe_path_maps_container_output_uri_to_local_output_root(tmp_path):
    output_root = tmp_path / "outputs"
    keyframe = output_root / "series_001" / "ep_003" / "keyframes" / "kf_001.jpg"
    keyframe.parent.mkdir(parents=True)
    keyframe.write_bytes(b"jpeg")

    resolved = _resolve_keyframe_path(
        "/app/outputs/series_001/ep_003/keyframes/kf_001.jpg",
        output_root,
    )

    assert resolved == keyframe


def test_resolve_keyframe_path_falls_back_to_cwd_outputs_for_container_output_root(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    keyframe = tmp_path / "outputs" / "series_001" / "ep_003" / "keyframes" / "kf_001.jpg"
    keyframe.parent.mkdir(parents=True)
    keyframe.write_bytes(b"jpeg")

    resolved = _resolve_keyframe_path(
        "/app/outputs/series_001/ep_003/keyframes/kf_001.jpg",
        __import__("pathlib").Path("/app/outputs"),
    )

    assert resolved == keyframe


def test_segment_understanding_falls_back_per_segment_when_vlm_call_fails(tmp_path, monkeypatch):
    class BrokenVlmClient:
        def __init__(self, api_key: str, model: str):
            pass

        def complete_json_with_image(self, **kwargs):
            raise ModelClientError("content filter")

    monkeypatch.setattr(understanding, "ZhipuChatClient", BrokenVlmClient)
    image_path = tmp_path / "outputs" / "series_001" / "ep_003" / "keyframes" / "kf_001.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"jpeg")
    settings = Settings(
        pipeline_version="analysis_pipeline_v0.1",
        taxonomy_version=TAXONOMY.taxonomy_version,
        output_root=tmp_path / "outputs",
        audio_chunk_ms=20000,
        video_segment_ms=8000,
        zhipuai_api_key="configured",
        deepseek_api_key=None,
        zhipuai_asr_model="glm-asr-2512",
        zhipuai_vlm_model="glm-4v-flash",
        deepseek_model="deepseek-chat",
        allow_model_fallback=True,
    )

    results = build_segment_understandings(
        settings,
        [
            VideoSegment(
                segment_id="seg_001",
                video_id="vid_001",
                series_id="series_001",
                episode_id="ep_003",
                start_ms=0,
                end_ms=8000,
                keyframe_ids=["kf_001"],
            )
        ],
        [],
        [
            Keyframe(
                keyframe_id="kf_001",
                segment_id="seg_001",
                series_id="series_001",
                episode_id="ep_003",
                timestamp_ms=4000,
                image_uri=str(image_path),
            )
        ],
    )

    assert results[0].visual_summary == "本地 ASR 降级理解：该片段暂无可用台词。"
    assert results[0].scene == "未知场景"


def test_fallback_script_preserves_segment_sources():
    segments = [
        VideoSegment(
            segment_id="seg_000",
            video_id="vid_003",
            series_id="series_001",
            episode_id="ep_003",
            start_ms=0,
            end_ms=8000,
            keyframe_ids=["kf_seg_000_4000"],
        )
    ]
    transcript_chunks = [
        TranscriptChunk(
            chunk_id="aud_000",
            audio_id="audio_ep_003",
            series_id="series_001",
            episode_id="ep_003",
            start_ms=0,
            end_ms=8000,
            text="你凭什么这样做",
            provider="test",
            model="fixture",
            asr_segments=[
                {"asr_id": "1", "start_ms": 1000, "end_ms": 2000, "text": "你凭什么这样做"}
            ],
        )
    ]
    understandings = [
        SegmentUnderstanding(
            segment_understanding_id="su_seg_000",
            segment_id="seg_000",
            series_id="series_001",
            episode_id="ep_003",
            start_ms=0,
            end_ms=8000,
            keyframe_ids=["kf_seg_000_4000"],
            transcript_refs=["aud_000:1"],
            dialogue_raw="你凭什么这样做",
            visual_summary="两人对峙。",
            scene="室内",
            main_actions="角色争执。",
            emotion_hint="愤怒",
            conflict_level=4,
        )
    ]

    script = build_fallback_observed_script("series_001", "ep_003", segments, transcript_chunks, understandings)

    assert script.scenes[0].source_segment_ids == ["seg_000"]
    assert script.scenes[0].beats[0].source_segment_ids == ["seg_000"]
    assert "你凭什么这样做" in script.to_markdown()


def test_rule_based_highlight_extractor_submits_traceable_event():
    script = build_fallback_observed_script(
        "series_001",
        "ep_003",
        [
            VideoSegment(
                segment_id="seg_000",
                video_id="vid_003",
                series_id="series_001",
                episode_id="ep_003",
                start_ms=0,
                end_ms=8000,
                keyframe_ids=["kf_seg_000_4000"],
            )
        ],
        [
            TranscriptChunk(
                chunk_id="aud_000",
                audio_id="audio_ep_003",
                series_id="series_001",
                episode_id="ep_003",
                start_ms=0,
                end_ms=8000,
                text="你凭什么这样做",
                provider="test",
                model="fixture",
                asr_segments=[
                    {
                        "asr_id": "1",
                        "start_ms": 1000,
                        "end_ms": 2000,
                        "text": "你凭什么这样做",
                    }
                ],
            )
        ],
        [
            SegmentUnderstanding(
                segment_understanding_id="su_seg_000",
                segment_id="seg_000",
                series_id="series_001",
                episode_id="ep_003",
                start_ms=0,
                end_ms=8000,
                keyframe_ids=["kf_seg_000_4000"],
                transcript_refs=["aud_000:1"],
                dialogue_raw="你凭什么这样做",
                visual_summary="两人对峙。",
                scene="室内",
                main_actions="角色争执。",
                emotion_hint="愤怒",
                conflict_level=4,
            )
        ],
    )
    toolbox = HighlightToolbox(
        observed_script=script,
        segments=[
            VideoSegment(
                segment_id="seg_000",
                video_id="vid_003",
                series_id="series_001",
                episode_id="ep_003",
                start_ms=0,
                end_ms=8000,
                keyframe_ids=["kf_seg_000_4000"],
            )
        ],
        transcript_chunks=[
            TranscriptChunk(
                chunk_id="aud_000",
                audio_id="audio_ep_003",
                series_id="series_001",
                episode_id="ep_003",
                start_ms=0,
                end_ms=8000,
                text="你凭什么这样做",
                provider="test",
                model="fixture",
                asr_segments=[
                    {
                        "asr_id": "1",
                        "start_ms": 1000,
                        "end_ms": 2000,
                        "text": "你凭什么这样做",
                    }
                ],
            )
        ],
        keyframes=[
            Keyframe(
                keyframe_id="kf_seg_000_4000",
                segment_id="seg_000",
                series_id="series_001",
                episode_id="ep_003",
                timestamp_ms=4000,
                image_uri="outputs/ep_003/keyframes/kf_seg_000_4000.jpg",
            )
        ],
        segment_understandings=[],
        taxonomy=TAXONOMY,
    )

    candidates, events = RuleBasedHighlightExtractor().extract(toolbox)

    assert candidates[0].highlight_type == "conflict"
    assert events[0].review_status == "pending"
    assert events[0].enabled is False
    assert events[0].evidence[0].transcript_chunk_id == "aud_000"
