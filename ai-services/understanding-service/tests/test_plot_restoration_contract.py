from pipelines.script_generation.generator import build_fallback_observed_script
from schemas.script import ObservedScript
from schemas.video import SegmentUnderstanding, TranscriptChunk, VideoSegment


def test_observed_script_carries_restored_characters_facts_and_uncertainties():
    script = ObservedScript.model_validate(
        {
            "script_id": "script_series_001_ep_003_v1",
            "series_id": "series_001",
            "episode_id": "ep_003",
            "title": "镇北侯府风波",
            "summary": "吕贞揭露自己故意养废孙瑜。",
            "characters": [
                {
                    "character_id": "char_sun_yu",
                    "name": "孙瑜",
                    "canonical_name": "孙瑜",
                    "aliases": ["鱼儿", "二公子"],
                    "role": "镇北侯二公子",
                    "description": "被继母故意养废的侯府子弟。",
                    "confidence": 0.86,
                    "evidence_refs": [
                        {
                            "type": "asr",
                            "segment_id": "seg_001",
                            "transcript_chunk_id": "aud_001",
                            "asr_id": "1",
                            "text": "鱼儿",
                            "start_ms": 1000,
                            "end_ms": 1500,
                        }
                    ],
                    "relationships": [
                        {
                            "target_character_id": "char_lu_zhen",
                            "relation": "继母",
                            "certainty": "inferred",
                            "confidence": 0.8,
                            "evidence_refs": [],
                        }
                    ],
                }
            ],
            "scenes": [],
            "plot_facts": [
                {
                    "fact_id": "fact_001",
                    "type": "backstory_reveal",
                    "statement": "吕贞曾毒害孙瑜生母，并故意将孙瑜养成废物。",
                    "certainty": "inferred",
                    "confidence": 0.92,
                    "source_scene_ids": ["scene_002"],
                    "source_segment_ids": ["seg_001"],
                    "evidence_refs": [],
                }
            ],
            "uncertainties": [
                {
                    "uncertainty_id": "unc_001",
                    "field": "character_name",
                    "description": "ASR 中吕贞和吕珍不一致。",
                    "candidates": ["吕贞", "吕珍"],
                    "chosen": "吕贞",
                    "confidence": 0.7,
                    "source_segment_ids": ["seg_001"],
                }
            ],
        }
    )

    markdown = script.to_markdown()

    assert script.characters[0].canonical_name == "孙瑜"
    assert script.characters[0].relationships[0].certainty == "inferred"
    assert script.plot_facts[0].source_segment_ids == ["seg_001"]
    assert "## Plot Facts" in markdown
    assert "吕贞曾毒害孙瑜生母" in markdown
    assert "## Uncertainties" in markdown
    assert "吕贞 / 吕珍" in markdown


def test_fallback_script_restores_clean_beats_from_fragmented_asr():
    segments = [
        VideoSegment(
            segment_id="seg_series_001_ep_003_001",
            video_id="vid_series_001_ep_003",
            series_id="series_001",
            episode_id="ep_003",
            start_ms=0,
            end_ms=8000,
            keyframe_ids=["kf_seg_series_001_ep_003_001_4000"],
        )
    ]
    transcript_chunks = [
        TranscriptChunk(
            chunk_id="aud_series_001_ep_003_001",
            audio_id="audio_series_001_ep_003",
            series_id="series_001",
            episode_id="ep_003",
            start_ms=0,
            end_ms=8000,
            text="吕珍 是 当朝丞相之女 娘只有 把他 养成 一个 废物",
            provider="test",
            model="fixture",
            asr_segments=[
                {"asr_id": "1", "start_ms": 1000, "end_ms": 1800, "text": "吕珍 是 当朝丞相之女"},
                {"asr_id": "2", "start_ms": 2000, "end_ms": 3200, "text": "娘只有 把他"},
                {"asr_id": "3", "start_ms": 3300, "end_ms": 4500, "text": "养成 一个 废物"},
            ],
        )
    ]
    understandings = [
        SegmentUnderstanding(
            segment_understanding_id="su_seg_series_001_ep_003_001",
            segment_id="seg_series_001_ep_003_001",
            series_id="series_001",
            episode_id="ep_003",
            start_ms=0,
            end_ms=8000,
            keyframe_ids=["kf_seg_series_001_ep_003_001_4000"],
            transcript_refs=["aud_series_001_ep_003_001:1", "aud_series_001_ep_003_001:2"],
            dialogue_raw="吕珍 是 当朝丞相之女 娘只有 把他 养成 一个 废物",
            visual_summary="两名角色在侯府内室低声密谋。",
            scene="侯府内室",
            main_actions="一名妇人与年轻男子密谈。",
            emotion_hint="阴谋揭露",
            conflict_level=4,
            visible_characters=["吕贞", "孙瑜"],
            character_actions=["妇人低声解释过往阴谋", "年轻男子隐忍倾听"],
            facial_expressions="妇人克制，年轻男子震惊隐忍。",
            shot_cues="室内近景，角色正反打。",
            sound_cues="低声密谈。",
            power_dynamic="继母掌握真相，孙瑜处于被操控位置。",
        )
    ]

    script = build_fallback_observed_script(
        "series_001",
        "ep_003",
        segments,
        transcript_chunks,
        understandings,
    )

    beat = script.scenes[0].beats[0]

    assert beat.raw_text == "吕珍 是 当朝丞相之女 娘只有 把他 养成 一个 废物"
    assert beat.clean_text == "吕珍是当朝丞相之女 娘只有把他养成一个废物"
    assert beat.source_asr_refs == [
        "aud_series_001_ep_003_001:1",
        "aud_series_001_ep_003_001:2",
        "aud_series_001_ep_003_001:3",
    ]
    assert script.characters[0].canonical_name == "吕贞"
    assert script.plot_facts[0].certainty == "inferred"
    assert script.plot_facts[0].source_segment_ids == ["seg_series_001_ep_003_001"]
