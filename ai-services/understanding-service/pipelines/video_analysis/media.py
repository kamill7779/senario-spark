from __future__ import annotations

import hashlib
import math
import re
import shutil
import subprocess
from pathlib import Path

from schemas.video import Keyframe, VideoAsset, VideoSegment


def ffmpeg_executable() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        path = shutil.which("ffmpeg")
        if path:
            return path
    raise RuntimeError("ffmpeg is required. Install imageio-ffmpeg or provide ffmpeg on PATH.")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def probe_video(video_path: Path, episode_id: str, video_id: str) -> VideoAsset:
    ffmpeg = ffmpeg_executable()
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(video_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    metadata = result.stderr or result.stdout
    duration_ms = _parse_duration_ms(metadata)
    width, height = _parse_dimensions(metadata)
    return VideoAsset(
        video_id=video_id,
        episode_id=episode_id,
        source_url=video_path.resolve().as_uri(),
        storage_uri=video_path.resolve().as_uri(),
        duration_ms=duration_ms,
        width=width,
        height=height,
        fps=_parse_fps(metadata),
        codec=_parse_codec(metadata),
        checksum=file_sha256(video_path),
        status="ready",
    )


def extract_audio(video_path: Path, audio_path: Path) -> None:
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg_executable(),
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def split_audio_file(audio_path: Path, chunk_ranges: list[tuple[int, int]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, (start_ms, end_ms) in enumerate(chunk_ranges):
        chunk_path = output_dir / f"chunk_{index:03d}_{start_ms}_{end_ms}.wav"
        duration_seconds = (end_ms - start_ms) / 1000
        subprocess.run(
            [
                ffmpeg_executable(),
                "-y",
                "-ss",
                f"{start_ms / 1000:.3f}",
                "-t",
                f"{duration_seconds:.3f}",
                "-i",
                str(audio_path),
                str(chunk_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        paths.append(chunk_path)
    return paths


def plan_audio_chunks(duration_ms: int, chunk_ms: int = 20_000) -> list[tuple[int, int]]:
    return _plan_ranges(duration_ms, chunk_ms)


def plan_video_segments(
    video_id: str,
    episode_id: str,
    duration_ms: int,
    segment_ms: int = 8_000,
) -> list[VideoSegment]:
    segments: list[VideoSegment] = []
    for index, (start_ms, end_ms) in enumerate(_plan_ranges(duration_ms, segment_ms)):
        midpoint = start_ms + max(0, math.floor((end_ms - start_ms) / 2))
        segment_id = f"seg_{index:03d}"
        segments.append(
            VideoSegment(
                segment_id=segment_id,
                video_id=video_id,
                episode_id=episode_id,
                start_ms=start_ms,
                end_ms=end_ms,
                keyframe_ids=[f"kf_{segment_id}_{midpoint}"],
            )
        )
    return segments


def extract_keyframes(video_path: Path, segments: list[VideoSegment], output_dir: Path) -> list[Keyframe]:
    output_dir.mkdir(parents=True, exist_ok=True)
    keyframes: list[Keyframe] = []
    for segment in segments:
        timestamp_ms = segment.start_ms + max(0, math.floor((segment.end_ms - segment.start_ms) / 2))
        keyframe_id = segment.keyframe_ids[0]
        image_path = output_dir / f"{keyframe_id}.jpg"
        subprocess.run(
            [
                ffmpeg_executable(),
                "-y",
                "-ss",
                f"{timestamp_ms / 1000:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(image_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        keyframes.append(
            Keyframe(
                keyframe_id=keyframe_id,
                segment_id=segment.segment_id,
                episode_id=segment.episode_id,
                timestamp_ms=timestamp_ms,
                image_uri=str(image_path),
            )
        )
    return keyframes


def _plan_ranges(duration_ms: int, window_ms: int) -> list[tuple[int, int]]:
    if duration_ms <= 0:
        return []
    ranges = []
    start_ms = 0
    while start_ms < duration_ms:
        end_ms = min(duration_ms, start_ms + window_ms)
        ranges.append((start_ms, end_ms))
        start_ms = end_ms
    return ranges


def _parse_duration_ms(metadata: str) -> int:
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", metadata)
    if not match:
        raise RuntimeError("could not parse video duration from ffmpeg output")
    hours, minutes, seconds = match.groups()
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return int(total_seconds * 1000)


def _parse_dimensions(metadata: str) -> tuple[int | None, int | None]:
    match = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", metadata)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _parse_fps(metadata: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*fps", metadata)
    return float(match.group(1)) if match else None


def _parse_codec(metadata: str) -> str | None:
    match = re.search(r"Video:\s*([^,\s]+)", metadata)
    return match.group(1) if match else None
