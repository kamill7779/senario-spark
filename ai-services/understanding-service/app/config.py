from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from schemas.taxonomy import TAXONOMY


@dataclass(frozen=True)
class Settings:
    pipeline_version: str
    taxonomy_version: str
    output_root: Path
    audio_chunk_ms: int
    video_segment_ms: int
    zhipuai_api_key: str | None
    deepseek_api_key: str | None
    zhipuai_asr_model: str
    zhipuai_vlm_model: str
    deepseek_model: str
    allow_model_fallback: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            pipeline_version=os.environ.get("ANALYSIS_PIPELINE_VERSION", "analysis_pipeline_v0.1"),
            taxonomy_version=TAXONOMY.taxonomy_version,
            output_root=Path(os.environ.get("OUTPUT_ROOT", "outputs")),
            audio_chunk_ms=int(os.environ.get("AUDIO_CHUNK_MS", "20000")),
            video_segment_ms=int(os.environ.get("VIDEO_SEGMENT_MS", "8000")),
            zhipuai_api_key=os.environ.get("ZHIPUAI_API_KEY"),
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY"),
            zhipuai_asr_model=os.environ.get("ZHIPUAI_ASR_MODEL", "glm-asr-2512"),
            zhipuai_vlm_model=os.environ.get("ZHIPUAI_VLM_MODEL", "glm-4v-flash"),
            deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            allow_model_fallback=os.environ.get("ALLOW_MODEL_FALLBACK", "1") != "0",
        )
