from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import requests

from app.config import Settings
from app.repositories import MySQLRepository
from pipelines.highlight_extraction.agent import extract_highlights
from pipelines.highlight_extraction.tools import HighlightToolbox
from pipelines.script_generation.generator import generate_observed_script
from pipelines.video_analysis.asr import transcribe_audio_chunks
from pipelines.video_analysis.media import (
    extract_audio,
    extract_keyframes,
    plan_audio_chunks,
    plan_video_segments,
    probe_video,
    split_audio_file,
)
from pipelines.video_analysis.understanding import build_segment_understandings
from schemas.highlight import HighlightCandidate, HighlightEvent
from schemas.script import ObservedScript
from schemas.taxonomy import TAXONOMY
from schemas.video import (
    AudioAsset,
    Keyframe,
    SegmentUnderstanding,
    TranscriptChunk,
    UnderstandingPackage,
    VideoAsset,
    VideoSegment,
)


STEP_NAMES = [
    "create_analysis_job",
    "read_video_metadata",
    "extract_audio",
    "split_audio",
    "asr_transcription",
    "create_video_segments",
    "extract_keyframes",
    "segment_understanding",
    "build_understanding_package",
    "generate_observed_script",
    "highlight_extraction_agent",
]


@dataclass
class StepOutput:
    artifact_ids: list[str] = field(default_factory=list)
    tool_call_count: int = 0


@dataclass
class AnalysisContext:
    series_id: str
    episode_id: str
    video_input: str
    settings: Settings
    job_id: str = ""
    video_id: str = ""
    audio_id: str = ""
    package_id: str = ""
    script_id: str = ""
    output_dir: Path | None = None
    video_path: Path | None = None
    audio_path: Path | None = None
    audio_chunk_ranges: list[tuple[int, int]] = field(default_factory=list)
    audio_chunk_paths: list[Path] = field(default_factory=list)
    video_asset: VideoAsset | None = None
    audio_asset: AudioAsset | None = None
    transcript_chunks: list[TranscriptChunk] = field(default_factory=list)
    video_segments: list[VideoSegment] = field(default_factory=list)
    keyframes: list[Keyframe] = field(default_factory=list)
    segment_understandings: list[SegmentUnderstanding] = field(default_factory=list)
    understanding_package: UnderstandingPackage | None = None
    observed_script: ObservedScript | None = None
    highlight_candidates: list[HighlightCandidate] = field(default_factory=list)
    highlight_events: list[HighlightEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        safe_series = _safe_path_part(self.series_id)
        safe_episode = _safe_path_part(self.episode_id)
        id_prefix = f"{safe_series}_{safe_episode}"
        self.job_id = f"job_{id_prefix}_analysis_v0_1"
        self.video_id = f"vid_{id_prefix}"
        self.audio_id = f"audio_{id_prefix}"
        self.package_id = f"upkg_{id_prefix}_v1"
        self.script_id = f"script_{id_prefix}_v1"
        self.output_dir = self.settings.output_root / safe_series / safe_episode
        self.video_path = self._initial_video_path()
        self.audio_path = self.output_dir / "audio.wav"

    def _initial_video_path(self) -> Path:
        if self.video_input.startswith(("http://", "https://")):
            suffix = Path(self.video_input.split("?")[0]).suffix or ".mp4"
            assert self.output_dir is not None
            return self.output_dir / f"input{suffix}"
        return Path(self.video_input)


class AnalysisWorkflow:
    def __init__(self, repository: MySQLRepository, settings: Settings | None = None):
        self.repository = repository
        self.settings = settings or Settings.from_env()

    def run(
        self,
        series_id: str,
        episode_id: str,
        video_input: str,
        resume_from: str | None = None,
    ) -> AnalysisContext:
        if resume_from and resume_from not in STEP_NAMES:
            raise ValueError(f"unknown resume step {resume_from}; valid steps: {', '.join(STEP_NAMES)}")
        context = AnalysisContext(
            series_id=series_id,
            episode_id=episode_id,
            video_input=video_input,
            settings=self.settings,
        )
        context.output_dir.mkdir(parents=True, exist_ok=True)
        if resume_from:
            self._load_existing_context(context)

        started = resume_from is None
        for step_name, func, metadata in self._steps():
            if not started:
                started = step_name == resume_from
            if not started:
                continue
            self._run_step(context, step_name, func, **metadata)
        self.repository.update_analysis_job_status(context.job_id, "completed", completed=True)
        return context

    def _steps(self) -> list[tuple[str, Callable[[AnalysisContext], StepOutput], dict]]:
        return [
            ("create_analysis_job", self._step_create_analysis_job, {}),
            ("read_video_metadata", self._step_read_video_metadata, {}),
            ("extract_audio", self._step_extract_audio, {}),
            ("split_audio", self._step_split_audio, {}),
            (
                "asr_transcription",
                self._step_asr_transcription,
                {"model_provider": "zhipuai", "model_name": self.settings.zhipuai_asr_model},
            ),
            ("create_video_segments", self._step_create_video_segments, {}),
            ("extract_keyframes", self._step_extract_keyframes, {}),
            (
                "segment_understanding",
                self._step_segment_understanding,
                {"model_provider": "zhipuai", "model_name": self.settings.zhipuai_vlm_model},
            ),
            ("build_understanding_package", self._step_build_understanding_package, {}),
            (
                "generate_observed_script",
                self._step_generate_observed_script,
                {
                    "model_provider": "deepseek",
                    "model_name": self.settings.deepseek_model,
                    "prompt_version": "script_generation_prompt_v0.1",
                    "schema_version": "observed_script_schema_v0.1",
                },
            ),
            (
                "highlight_extraction_agent",
                self._step_highlight_extraction,
                {
                    "model_provider": "deepseek",
                    "model_name": self.settings.deepseek_model,
                    "prompt_version": "highlight_agent_prompt_v0.1",
                    "schema_version": "highlight_event_schema_v0.1",
                },
            ),
        ]

    def _run_step(
        self,
        context: AnalysisContext,
        step_name: str,
        func: Callable[[AnalysisContext], StepOutput],
        model_provider: str | None = None,
        model_name: str | None = None,
        prompt_version: str | None = None,
        schema_version: str | None = None,
    ) -> None:
        step_run_id = f"step_{context.job_id}_{step_name}"
        start = time.monotonic()
        self.repository.save_step_run(
            {
                "step_run_id": step_run_id,
                "job_id": context.job_id,
                "series_id": context.series_id,
                "episode_id": context.episode_id,
                "step_name": step_name,
                "status": "processing",
                "input_artifact_ids": self._step_input_ids(context, step_name),
                "output_artifact_ids": [],
                "model_provider": model_provider,
                "model_name": model_name,
                "prompt_version": prompt_version,
                "schema_version": schema_version,
                "taxonomy_version": self.settings.taxonomy_version,
                "tool_call_count": 0,
                "latency_ms": 0,
                "error": None,
            }
        )
        try:
            output = func(context)
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            error = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.repository.save_step_run(
                {
                    "step_run_id": step_run_id,
                    "job_id": context.job_id,
                    "series_id": context.series_id,
                    "episode_id": context.episode_id,
                    "step_name": step_name,
                    "status": "failed",
                    "input_artifact_ids": self._step_input_ids(context, step_name),
                    "output_artifact_ids": [],
                    "model_provider": model_provider,
                    "model_name": model_name,
                    "prompt_version": prompt_version,
                    "schema_version": schema_version,
                    "taxonomy_version": self.settings.taxonomy_version,
                    "tool_call_count": 0,
                    "latency_ms": latency_ms,
                    "error": error,
                    "completed_at": _mysql_datetime(),
                }
            )
            self.repository.update_analysis_job_status(context.job_id, "failed", error=error)
            raise
        latency_ms = int((time.monotonic() - start) * 1000)
        self.repository.save_step_run(
            {
                "step_run_id": step_run_id,
                "job_id": context.job_id,
                "series_id": context.series_id,
                "episode_id": context.episode_id,
                "step_name": step_name,
                "status": "completed",
                "input_artifact_ids": self._step_input_ids(context, step_name),
                "output_artifact_ids": output.artifact_ids,
                "model_provider": model_provider,
                "model_name": model_name,
                "prompt_version": prompt_version,
                "schema_version": schema_version,
                "taxonomy_version": self.settings.taxonomy_version,
                "tool_call_count": output.tool_call_count,
                "latency_ms": latency_ms,
                "error": None,
                "completed_at": _mysql_datetime(),
            }
        )

    def _step_create_analysis_job(self, context: AnalysisContext) -> StepOutput:
        self.repository.save_analysis_job(
            {
                "job_id": context.job_id,
                "series_id": context.series_id,
                "episode_id": context.episode_id,
                "video_id": context.video_id,
                "status": "processing",
                "pipeline_version": self.settings.pipeline_version,
                "taxonomy_version": self.settings.taxonomy_version,
                "video_source": context.video_input,
                "input_payload": {
                    "series_id": context.series_id,
                    "episode_id": context.episode_id,
                    "video": context.video_input,
                },
                "output_dir": str(context.output_dir),
                "error": None,
            }
        )
        return StepOutput([context.job_id])

    def _step_read_video_metadata(self, context: AnalysisContext) -> StepOutput:
        if context.video_input.startswith(("http://", "https://")):
            _download_video(context.video_input, context.video_path)
        assert context.video_path is not None
        context.video_asset = probe_video(
            context.video_path,
            context.series_id,
            context.episode_id,
            context.video_id,
        )
        self.repository.save_video_asset(context.video_asset)
        return StepOutput([context.video_asset.video_id])

    def _step_extract_audio(self, context: AnalysisContext) -> StepOutput:
        self._ensure_video_asset(context)
        assert context.video_path is not None and context.audio_path is not None
        extract_audio(context.video_path, context.audio_path)
        context.audio_asset = AudioAsset(
            audio_id=context.audio_id,
            video_id=context.video_id,
            series_id=context.series_id,
            episode_id=context.episode_id,
            storage_uri=str(context.audio_path),
            sample_rate=16000,
            channels=1,
            duration_ms=context.video_asset.duration_ms,
        )
        self.repository.save_audio_asset(context.audio_asset)
        return StepOutput([context.audio_asset.audio_id])

    def _step_split_audio(self, context: AnalysisContext) -> StepOutput:
        self._ensure_audio_asset(context)
        assert context.audio_path is not None
        context.audio_chunk_ranges = plan_audio_chunks(
            context.audio_asset.duration_ms,
            self.settings.audio_chunk_ms,
        )
        context.audio_chunk_paths = split_audio_file(
            context.audio_path,
            context.audio_chunk_ranges,
            context.output_dir / "audio_chunks",
        )
        return StepOutput([str(path) for path in context.audio_chunk_paths])

    def _step_asr_transcription(self, context: AnalysisContext) -> StepOutput:
        self._ensure_audio_asset(context)
        if not context.audio_chunk_ranges:
            context.audio_chunk_ranges = plan_audio_chunks(
                context.audio_asset.duration_ms,
                self.settings.audio_chunk_ms,
            )
        if not context.audio_chunk_paths:
            context.audio_chunk_paths = [
                context.output_dir / "audio_chunks" / f"chunk_{idx:03d}_{start}_{end}.wav"
                for idx, (start, end) in enumerate(context.audio_chunk_ranges)
            ]
        context.transcript_chunks = transcribe_audio_chunks(
            self.settings,
            context.series_id,
            context.episode_id,
            context.audio_id,
            context.audio_chunk_paths,
            context.audio_chunk_ranges,
        )
        for chunk in context.transcript_chunks:
            self.repository.save_transcript_chunk(chunk)
        return StepOutput([chunk.chunk_id for chunk in context.transcript_chunks])

    def _step_create_video_segments(self, context: AnalysisContext) -> StepOutput:
        self._ensure_video_asset(context)
        context.video_segments = plan_video_segments(
            context.video_id,
            context.series_id,
            context.episode_id,
            context.video_asset.duration_ms,
            self.settings.video_segment_ms,
        )
        for segment in context.video_segments:
            self.repository.save_video_segment(segment)
        return StepOutput([segment.segment_id for segment in context.video_segments])

    def _step_extract_keyframes(self, context: AnalysisContext) -> StepOutput:
        self._ensure_video_segments(context)
        assert context.video_path is not None
        context.keyframes = extract_keyframes(
            context.video_path,
            context.video_segments,
            context.output_dir / "keyframes",
        )
        for keyframe in context.keyframes:
            self.repository.save_keyframe(keyframe)
        return StepOutput([keyframe.keyframe_id for keyframe in context.keyframes])

    def _step_segment_understanding(self, context: AnalysisContext) -> StepOutput:
        self._ensure_video_segments(context)
        self._ensure_transcript_chunks(context)
        self._ensure_keyframes(context)
        context.segment_understandings = build_segment_understandings(
            self.settings,
            context.video_segments,
            context.transcript_chunks,
            context.keyframes,
        )
        for understanding in context.segment_understandings:
            self.repository.save_segment_understanding(understanding)
        return StepOutput(
            [understanding.segment_understanding_id for understanding in context.segment_understandings]
        )

    def _step_build_understanding_package(self, context: AnalysisContext) -> StepOutput:
        self._ensure_video_asset(context)
        self._ensure_audio_asset(context)
        self._ensure_transcript_chunks(context)
        self._ensure_video_segments(context)
        self._ensure_segment_understandings(context)
        context.understanding_package = UnderstandingPackage(
            package_id=context.package_id,
            series_id=context.series_id,
            episode_id=context.episode_id,
            video_id=context.video_id,
            pipeline_version=self.settings.pipeline_version,
            video_asset_id=context.video_id,
            audio_asset_id=context.audio_id,
            transcript_chunk_ids=[chunk.chunk_id for chunk in context.transcript_chunks],
            video_segment_ids=[segment.segment_id for segment in context.video_segments],
            segment_understanding_ids=[
                understanding.segment_understanding_id
                for understanding in context.segment_understandings
            ],
        )
        self.repository.save_understanding_package(context.understanding_package)
        return StepOutput([context.understanding_package.package_id])

    def _step_generate_observed_script(self, context: AnalysisContext) -> StepOutput:
        self._ensure_video_segments(context)
        self._ensure_transcript_chunks(context)
        self._ensure_segment_understandings(context)
        context.observed_script = generate_observed_script(
            self.settings,
            context.series_id,
            context.episode_id,
            context.video_segments,
            context.transcript_chunks,
            context.segment_understandings,
        )
        markdown = context.observed_script.to_markdown()
        _write_json(context.output_dir / "observed_script.json", context.observed_script.model_dump(mode="json"))
        (context.output_dir / "observed_script.md").write_text(markdown, encoding="utf-8")
        self.repository.save_observed_script(context.observed_script, markdown)
        return StepOutput([context.observed_script.script_id])

    def _step_highlight_extraction(self, context: AnalysisContext) -> StepOutput:
        self._ensure_observed_script(context)
        self._ensure_video_segments(context)
        self._ensure_transcript_chunks(context)
        self._ensure_keyframes(context)
        self._ensure_segment_understandings(context)
        toolbox = HighlightToolbox(
            observed_script=context.observed_script,
            segments=context.video_segments,
            transcript_chunks=context.transcript_chunks,
            keyframes=context.keyframes,
            segment_understandings=context.segment_understandings,
            taxonomy=TAXONOMY,
        )
        context.highlight_candidates, context.highlight_events = extract_highlights(
            self.settings,
            toolbox,
        )
        for candidate in context.highlight_candidates:
            self.repository.save_highlight_candidate(candidate)
        for event in context.highlight_events:
            self.repository.save_highlight_event(event)
            self.repository.save_highlight_event_evidence(event)
        _write_json(
            context.output_dir / "highlight_events.json",
            [event.model_dump(mode="json") for event in context.highlight_events],
        )
        return StepOutput(
            [event.highlight_id for event in context.highlight_events],
            tool_call_count=toolbox.tool_call_count,
        )

    def _load_existing_context(self, context: AnalysisContext) -> None:
        video_asset = self.repository.get_video_asset(context.video_id)
        if video_asset:
            context.video_asset = VideoAsset.model_validate(video_asset)
        audio_asset = self.repository.get_audio_asset(context.audio_id)
        if audio_asset:
            context.audio_asset = AudioAsset.model_validate(audio_asset)
        context.transcript_chunks = [
            TranscriptChunk.model_validate(row)
            for row in self.repository.list_transcript_chunks(context.series_id, context.episode_id)
        ]
        context.video_segments = [
            VideoSegment.model_validate(row)
            for row in self.repository.list_video_segments(context.series_id, context.episode_id)
        ]
        context.keyframes = [
            Keyframe.model_validate(row)
            for row in self.repository.list_keyframes(context.series_id, context.episode_id)
        ]
        context.segment_understandings = [
            SegmentUnderstanding.model_validate(row)
            for row in self.repository.list_segment_understandings(
                context.series_id,
                context.episode_id,
            )
        ]
        package = self.repository.get_understanding_package(context.package_id)
        if package:
            context.understanding_package = UnderstandingPackage.model_validate(package)
        script = self.repository.get_observed_script(context.script_id)
        if script:
            context.observed_script = ObservedScript.model_validate(script["content_json"])

    def _ensure_video_asset(self, context: AnalysisContext) -> None:
        if context.video_asset is None:
            row = self.repository.get_video_asset(context.video_id)
            if not row:
                raise RuntimeError("video_asset is not available; rerun read_video_metadata")
            context.video_asset = VideoAsset.model_validate(row)

    def _ensure_audio_asset(self, context: AnalysisContext) -> None:
        if context.audio_asset is None:
            row = self.repository.get_audio_asset(context.audio_id)
            if not row:
                raise RuntimeError("audio_asset is not available; rerun extract_audio")
            context.audio_asset = AudioAsset.model_validate(row)

    def _ensure_transcript_chunks(self, context: AnalysisContext) -> None:
        if not context.transcript_chunks:
            context.transcript_chunks = [
                TranscriptChunk.model_validate(row)
                for row in self.repository.list_transcript_chunks(context.series_id, context.episode_id)
            ]
        if not context.transcript_chunks:
            raise RuntimeError("transcript_chunks are not available; rerun asr_transcription")

    def _ensure_video_segments(self, context: AnalysisContext) -> None:
        if not context.video_segments:
            context.video_segments = [
                VideoSegment.model_validate(row)
                for row in self.repository.list_video_segments(context.series_id, context.episode_id)
            ]
        if not context.video_segments:
            raise RuntimeError("video_segments are not available; rerun create_video_segments")

    def _ensure_keyframes(self, context: AnalysisContext) -> None:
        if not context.keyframes:
            context.keyframes = [
                Keyframe.model_validate(row)
                for row in self.repository.list_keyframes(context.series_id, context.episode_id)
            ]
        if not context.keyframes:
            raise RuntimeError("keyframes are not available; rerun extract_keyframes")

    def _ensure_segment_understandings(self, context: AnalysisContext) -> None:
        if not context.segment_understandings:
            context.segment_understandings = [
                SegmentUnderstanding.model_validate(row)
                for row in self.repository.list_segment_understandings(
                    context.series_id,
                    context.episode_id,
                )
            ]
        if not context.segment_understandings:
            raise RuntimeError("segment_understandings are not available; rerun segment_understanding")

    def _ensure_observed_script(self, context: AnalysisContext) -> None:
        if context.observed_script is None:
            row = self.repository.get_observed_script(context.script_id)
            if not row:
                raise RuntimeError("observed_script is not available; rerun generate_observed_script")
            context.observed_script = ObservedScript.model_validate(row["content_json"])

    def _step_input_ids(self, context: AnalysisContext, step_name: str) -> list[str]:
        mapping = {
            "create_analysis_job": [context.video_input],
            "read_video_metadata": [context.video_input],
            "extract_audio": [context.video_id],
            "split_audio": [context.audio_id],
            "asr_transcription": [context.audio_id],
            "create_video_segments": [context.video_id],
            "extract_keyframes": [segment.segment_id for segment in context.video_segments],
            "segment_understanding": [
                *[segment.segment_id for segment in context.video_segments],
                *[chunk.chunk_id for chunk in context.transcript_chunks],
            ],
            "build_understanding_package": [
                context.video_id,
                context.audio_id,
                *[chunk.chunk_id for chunk in context.transcript_chunks],
                *[segment.segment_id for segment in context.video_segments],
            ],
            "generate_observed_script": [context.package_id],
            "highlight_extraction_agent": [context.script_id, context.package_id],
        }
        return mapping.get(step_name, [])


def _download_video(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _mysql_datetime() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _safe_path_part(value: str) -> str:
    safe = value.replace("/", "_").replace("\\", "_").strip()
    if not safe:
        raise ValueError("series_id and episode_id cannot be empty")
    return safe
