from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from schemas.highlight import HighlightEvent
from schemas.script import ObservedScript
from schemas.taxonomy import HighlightTaxonomy
from schemas.video import Keyframe, SegmentUnderstanding, TranscriptChunk, VideoSegment


class HighlightToolbox:
    def __init__(
        self,
        observed_script: ObservedScript,
        segments: Iterable[VideoSegment],
        transcript_chunks: Iterable[TranscriptChunk],
        keyframes: Iterable[Keyframe],
        segment_understandings: Iterable[SegmentUnderstanding],
        taxonomy: HighlightTaxonomy,
    ):
        self.observed_script = observed_script
        self.segments = sorted(list(segments), key=lambda item: item.start_ms)
        self.transcript_chunks = list(transcript_chunks)
        self.keyframes = list(keyframes)
        self.segment_understandings = list(segment_understandings)
        self.taxonomy = taxonomy
        self.submitted_events: list[HighlightEvent] = []
        self.tool_call_count = 0

    def get_scene(self, scene_id: str) -> dict[str, Any]:
        self.tool_call_count += 1
        for scene in self.observed_script.scenes:
            if scene.scene_id == scene_id:
                payload = scene.model_dump(mode="json")
                payload["source_id"] = scene.scene_id
                return payload
        raise KeyError(f"scene not found: {scene_id}")

    def get_segment(self, segment_id: str) -> dict[str, Any]:
        self.tool_call_count += 1
        segment = self._segment(segment_id)
        payload = segment.model_dump(mode="json")
        payload["source_id"] = segment.segment_id
        payload["understanding"] = [
            item.model_dump(mode="json")
            for item in self.segment_understandings
            if item.segment_id == segment_id
        ]
        return payload

    def get_asr_segments(
        self,
        segment_id: str | None = None,
        time_range: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        self.tool_call_count += 1
        if segment_id is None and time_range is None:
            raise ValueError("segment_id or time_range is required")
        if segment_id is not None:
            segment = self._segment(segment_id)
            start_ms, end_ms = segment.start_ms, segment.end_ms
        else:
            assert time_range is not None
            start_ms, end_ms = time_range["start_ms"], time_range["end_ms"]

        results: list[dict[str, Any]] = []
        for chunk in self.transcript_chunks:
            for asr in chunk.asr_segments:
                if _within(asr.start_ms, asr.end_ms, start_ms, end_ms):
                    results.append(
                        {
                            "source_id": f"{chunk.chunk_id}:{asr.asr_id}",
                            "transcript_chunk_id": chunk.chunk_id,
                            "asr_id": asr.asr_id,
                            "segment_id": self._segment_id_for_time(asr.start_ms, asr.end_ms),
                            "start_ms": asr.start_ms,
                            "end_ms": asr.end_ms,
                            "text": asr.text,
                        }
                    )
        return sorted(results, key=lambda item: (item["start_ms"], item["end_ms"]))

    def get_neighbor_segments(
        self, segment_id: str, before: int = 1, after: int = 1
    ) -> list[dict[str, Any]]:
        self.tool_call_count += 1
        index = next(
            (idx for idx, segment in enumerate(self.segments) if segment.segment_id == segment_id),
            None,
        )
        if index is None:
            raise KeyError(f"segment not found: {segment_id}")
        start = max(0, index - before)
        end = min(len(self.segments), index + after + 1)
        return [
            {**segment.model_dump(mode="json"), "source_id": segment.segment_id}
            for segment in self.segments[start:end]
        ]

    def get_keyframes(self, segment_id: str) -> list[dict[str, Any]]:
        self.tool_call_count += 1
        return [
            {**keyframe.model_dump(mode="json"), "source_id": keyframe.keyframe_id}
            for keyframe in self.keyframes
            if keyframe.segment_id == segment_id
        ]

    def submit_highlight_events(self, events: list[dict[str, Any]]) -> list[HighlightEvent]:
        self.tool_call_count += 1
        validated = [HighlightEvent.model_validate(event) for event in events]
        self.submitted_events.extend(validated)
        return validated

    def _segment(self, segment_id: str) -> VideoSegment:
        for segment in self.segments:
            if segment.segment_id == segment_id:
                return segment
        raise KeyError(f"segment not found: {segment_id}")

    def _segment_id_for_time(self, start_ms: int, end_ms: int) -> str | None:
        for segment in self.segments:
            if _overlaps(start_ms, end_ms, segment.start_ms, segment.end_ms):
                return segment.segment_id
        return None


def _overlaps(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_a < end_b and start_b < end_a


def _within(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    return start_b <= start_a and end_a <= end_b
