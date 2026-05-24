from pipelines.highlight_extraction.tools import HighlightToolbox
from schemas.highlight import HighlightEvent
from schemas.script import ObservedScript
from schemas.taxonomy import TAXONOMY
from schemas.video import Keyframe, SegmentUnderstanding, TranscriptChunk, VideoSegment


def _toolbox() -> HighlightToolbox:
    script = ObservedScript.model_validate(
        {
            "script_id": "script_ep_003_v1",
            "episode_id": "ep_003",
            "title": "镇北侯府·孽障",
            "summary": "雨儿揭穿沈慧珍的伪装。",
            "characters": [],
            "scenes": [
                {
                    "scene_id": "scene_05",
                    "start_ms": 96000,
                    "end_ms": 112000,
                    "location": "古代庭院",
                    "summary": "雨儿冷漠讽刺母亲沈慧珍演了十五年的慈母。",
                    "characters": ["雨儿", "沈慧珍"],
                    "source_segment_ids": ["seg_012", "seg_013"],
                    "beats": [],
                }
            ],
        }
    )
    segments = [
        VideoSegment(
            segment_id="seg_012",
            video_id="vid_003",
            episode_id="ep_003",
            start_ms=96000,
            end_ms=104000,
            keyframe_ids=["kf_seg_012_100000"],
        ),
        VideoSegment(
            segment_id="seg_013",
            video_id="vid_003",
            episode_id="ep_003",
            start_ms=104000,
            end_ms=112000,
            keyframe_ids=["kf_seg_013_108000"],
        ),
    ]
    keyframes = [
        Keyframe(
            keyframe_id="kf_seg_013_108000",
            segment_id="seg_013",
            episode_id="ep_003",
            timestamp_ms=108000,
            image_uri="outputs/ep_003/keyframes/seg_013_108000.jpg",
        )
    ]
    transcript_chunks = [
        TranscriptChunk(
            chunk_id="aud_005",
            audio_id="audio_ep_003",
            episode_id="ep_003",
            start_ms=100000,
            end_ms=120000,
            text="沈慧珍 演了十五年的刺，也真是难为你们了。",
            provider="test",
            model="fixture",
            asr_segments=[
                {
                    "asr_id": "1",
                    "start_ms": 103200,
                    "end_ms": 104400,
                    "text": "爹娘慢走",
                },
                {
                    "asr_id": "2",
                    "start_ms": 106800,
                    "end_ms": 107600,
                    "text": "沈慧珍",
                },
                {
                    "asr_id": "3",
                    "start_ms": 107800,
                    "end_ms": 110900,
                    "text": "演了十五年的刺，也真是难为你们了。",
                },
            ],
        )
    ]
    understandings = [
        SegmentUnderstanding(
            segment_understanding_id="su_seg_013",
            segment_id="seg_013",
            episode_id="ep_003",
            start_ms=104000,
            end_ms=112000,
            keyframe_ids=["kf_seg_013_108000"],
            transcript_refs=["aud_005:2", "aud_005:3"],
            dialogue_raw="沈慧珍 演了十五年的刺，也真是难为你们了。",
            visual_summary="年轻男子侧目凝视，神情隐忍讽刺。",
            scene="室外庭院",
            main_actions="男子侧身站立，目光斜视。",
            emotion_hint="冷漠、讽刺",
            conflict_level=4,
        )
    ]
    return HighlightToolbox(
        observed_script=script,
        segments=segments,
        transcript_chunks=transcript_chunks,
        keyframes=keyframes,
        segment_understandings=understandings,
        taxonomy=TAXONOMY,
    )


def test_toolbox_get_scene_and_segment_include_source_fields():
    toolbox = _toolbox()

    scene = toolbox.get_scene("scene_05")
    segment = toolbox.get_segment("seg_013")

    assert scene["source_id"] == "scene_05"
    assert scene["source_segment_ids"] == ["seg_012", "seg_013"]
    assert segment["source_id"] == "seg_013"
    assert segment["start_ms"] == 104000


def test_toolbox_get_asr_segments_by_segment_and_time_range():
    toolbox = _toolbox()

    by_segment = toolbox.get_asr_segments(segment_id="seg_013")
    by_range = toolbox.get_asr_segments(time_range={"start_ms": 106000, "end_ms": 108000})

    assert [item["asr_id"] for item in by_segment] == ["2", "3"]
    assert [item["asr_id"] for item in by_range] == ["2"]


def test_toolbox_get_neighbor_segments_and_keyframes():
    toolbox = _toolbox()

    neighbors = toolbox.get_neighbor_segments("seg_013", before=1, after=0)
    keyframes = toolbox.get_keyframes("seg_013")

    assert [item["segment_id"] for item in neighbors] == ["seg_012", "seg_013"]
    assert neighbors[0]["source_id"] == "seg_012"
    assert keyframes[0]["source_id"] == "kf_seg_013_108000"


def test_toolbox_submit_highlight_events_validates_schema():
    toolbox = _toolbox()
    event = {
        "highlight_id": "hl_ep_003_001",
        "candidate_id": "hc_ep_003_001",
        "episode_id": "ep_003",
        "taxonomy_version": TAXONOMY.taxonomy_version,
        "highlight_type": "reversal",
        "secondary_highlight_types": ["face_slap"],
        "summary": "雨儿讽刺沈慧珍演了十五年的慈母。",
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
        "source_segment_ids": ["seg_013"],
        "evidence": [
            {
                "type": "asr",
                "segment_id": "seg_013",
                "transcript_chunk_id": "aud_005",
                "asr_id": "2",
                "text": "沈慧珍",
                "start_ms": 106800,
                "end_ms": 107600,
            }
        ],
        "review_status": "pending",
        "enabled": False,
    }

    submitted = toolbox.submit_highlight_events([event])

    assert submitted == [HighlightEvent.model_validate(event)]
    assert toolbox.submitted_events[0].enabled is False
