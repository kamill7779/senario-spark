from pipelines.highlight_extraction.agent import RuleBasedHighlightExtractor
from pipelines.highlight_extraction.tools import HighlightToolbox
from pipelines.script_generation.generator import build_fallback_observed_script
from pipelines.video_analysis.media import plan_audio_chunks, plan_video_segments
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
