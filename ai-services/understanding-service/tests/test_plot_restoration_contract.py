from app.config import Settings
from pipelines.script_generation.generator import build_fallback_observed_script
from pipelines.script_generation import generator
from pipelines.highlight_extraction.agent import HIGHLIGHT_PROMPT
from pipelines.video_analysis.understanding import VLM_PROMPT
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
    assert "ASR 引用: aud_series_001_ep_003_001:1" in script.to_markdown()
    assert "原始 ASR:" in script.to_markdown()
    assert script.characters[0].canonical_name == "吕贞"
    assert script.plot_facts[0].certainty == "inferred"
    assert script.plot_facts[0].source_segment_ids == ["seg_series_001_ep_003_001"]


def test_model_prompts_require_simplified_chinese_output():
    assert "简体中文" in generator.SCRIPT_PROMPT
    assert "简体中文" in HIGHLIGHT_PROMPT
    assert "简体中文" in VLM_PROMPT


def test_fallback_script_uses_chinese_default_copy_when_text_is_missing():
    segment = VideoSegment(
        segment_id="seg_series_001_ep_003_001",
        video_id="vid_series_001_ep_003",
        series_id="series_001",
        episode_id="ep_003",
        start_ms=0,
        end_ms=8000,
        keyframe_ids=[],
    )

    script = build_fallback_observed_script("series_001", "ep_003", [segment], [], [])
    markdown = script.to_markdown()

    assert script.title == "观测剧本 ep_003"
    assert script.summary == "本集暂无可用台词，剧本由本地片段证据生成。"
    assert "Observed Script" not in markdown
    assert "Video observations" not in markdown
    assert "Segment " not in markdown


def test_generate_observed_script_falls_back_when_model_returns_invalid_json(monkeypatch):
    class BrokenDeepSeekClient:
        def __init__(self, api_key: str, model: str):
            pass

        def complete_json(self, system_prompt: str, user_payload: dict) -> dict:
            raise ValueError("invalid model json")

    monkeypatch.setattr(generator, "DeepSeekJSONClient", BrokenDeepSeekClient)
    settings = Settings(
        pipeline_version="analysis_pipeline_v0.1",
        taxonomy_version="highlight_taxonomy_v0.1",
        output_root=__import__("pathlib").Path("outputs"),
        audio_chunk_ms=20000,
        video_segment_ms=8000,
        zhipuai_api_key=None,
        deepseek_api_key="configured",
        zhipuai_asr_model="glm-asr-2512",
        zhipuai_vlm_model="glm-4v-flash",
        deepseek_model="deepseek-chat",
        allow_model_fallback=True,
    )
    segments = [
        VideoSegment(
            segment_id="seg_series_001_ep_003_001",
            video_id="vid_series_001_ep_003",
            series_id="series_001",
            episode_id="ep_003",
            start_ms=0,
            end_ms=8000,
            keyframe_ids=[],
        )
    ]

    script = generator.generate_observed_script(
        settings,
        "series_001",
        "ep_003",
        segments,
        [],
        [],
    )

    assert script.script_id == "script_series_001_ep_003_v1"
    assert script.uncertainties[0].field == "model_output"
    assert script.uncertainties[0].description == "脚本模型返回的 JSON 未通过解析，已使用本地证据降级生成剧本。"


def test_generate_observed_script_normalizes_model_evidence_refs(monkeypatch):
    class SegmentOnlyEvidenceClient:
        def __init__(self, api_key: str, model: str):
            pass

        def complete_json(self, system_prompt: str, user_payload: dict) -> dict:
            return {
                "script_id": "script_series_001_ep_003_v1",
                "series_id": "series_001",
                "episode_id": "ep_003",
                "title": "镇北侯府风波",
                "summary": "吕贞揭露阴谋。",
                "characters": [
                    {
                        "character_id": "char_lu_zhen",
                        "name": "吕贞",
                        "canonical_name": "吕贞",
                        "aliases": ["吕珍"],
                        "role": "继母",
                        "description": "掌握真相的人。",
                        "confidence": 0.8,
                        "relationships": [
                            {
                                "target_character_id": "char_sun_yu",
                                "relation": "继母",
                                "certainty": "inferred",
                                "confidence": 0.8,
                                "evidence_refs": [{"segment_id": "seg_001"}],
                            }
                        ],
                        "evidence_refs": [{"segment_id": "seg_001"}],
                    }
                ],
                "plot_facts": [
                    {
                        "fact_id": "fact_001",
                        "type": "reveal",
                        "statement": "吕贞承认故意养废孙瑜。",
                        "certainty": "inferred",
                        "confidence": 0.9,
                        "source_scene_ids": ["scene_001"],
                        "source_segment_ids": ["seg_001"],
                        "evidence_refs": [{"segment_id": "seg_001"}],
                    }
                ],
                "uncertainties": [],
                "scenes": [],
            }

    monkeypatch.setattr(generator, "DeepSeekJSONClient", SegmentOnlyEvidenceClient)
    settings = Settings(
        pipeline_version="analysis_pipeline_v0.1",
        taxonomy_version="highlight_taxonomy_v0.1",
        output_root=__import__("pathlib").Path("outputs"),
        audio_chunk_ms=20000,
        video_segment_ms=8000,
        zhipuai_api_key=None,
        deepseek_api_key="configured",
        zhipuai_asr_model="glm-asr-2512",
        zhipuai_vlm_model="glm-4v-flash",
        deepseek_model="deepseek-chat",
        allow_model_fallback=False,
    )

    script = generator.generate_observed_script(
        settings,
        "series_001",
        "ep_003",
        [],
        [],
        [],
    )

    assert script.characters[0].evidence_refs[0].type == "segment"
    assert script.characters[0].evidence_refs[0].source_id == "seg_001"
    assert script.characters[0].relationships[0].evidence_refs[0].type == "segment"
    assert script.plot_facts[0].evidence_refs[0].type == "segment"
