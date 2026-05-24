from typing import Literal

from pydantic import BaseModel, Field, model_validator

from schemas.taxonomy import (
    AudienceEmotion,
    HighlightType,
    InteractionIntent,
    SentimentPolarity,
)


class HighlightTiming(BaseModel):
    start_ms: int = Field(ge=0)
    peak_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_order(self) -> "HighlightTiming":
        if not self.start_ms <= self.peak_ms <= self.end_ms:
            raise ValueError("highlight timing must satisfy start_ms <= peak_ms <= end_ms")
        return self


class HighlightEvidence(BaseModel):
    type: Literal["asr", "visual", "context", "segment", "keyframe"]
    segment_id: str | None = None
    transcript_chunk_id: str | None = None
    asr_id: str | None = None
    keyframe_id: str | None = None
    text: str | None = None
    description: str | None = None
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_evidence_reference(self) -> "HighlightEvidence":
        if self.type == "asr":
            if not self.transcript_chunk_id or self.start_ms is None or self.end_ms is None:
                raise ValueError("asr evidence requires transcript_chunk_id, start_ms, and end_ms")
        if self.type in {"visual", "keyframe"} and not self.keyframe_id:
            raise ValueError("visual/keyframe evidence requires keyframe_id")
        if self.start_ms is not None and self.end_ms is not None and self.start_ms > self.end_ms:
            raise ValueError("evidence start_ms cannot be after end_ms")
        return self


class HighlightCandidate(BaseModel):
    candidate_id: str
    episode_id: str
    taxonomy_version: str
    source_scene_id: str
    source_segment_ids: list[str] = Field(min_length=1)
    highlight_type: HighlightType
    secondary_highlight_types: list[HighlightType] = Field(default_factory=list)
    summary: str
    trigger_text_clean: str
    primary_audience_emotion: AudienceEmotion
    audience_emotions: list[AudienceEmotion] = Field(min_length=1)
    interaction_intent: InteractionIntent
    sentiment_polarity: SentimentPolarity
    intensity: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class HighlightEvent(HighlightCandidate):
    highlight_id: str
    trigger_text_raw: str
    timing: HighlightTiming
    evidence: list[HighlightEvidence] = Field(min_length=1)
    review_status: Literal["pending", "approved", "rejected", "needs_edit"] = "pending"
    enabled: bool = False

    @model_validator(mode="after")
    def validate_traceability(self) -> "HighlightEvent":
        evidence_segment_ids = {
            item.segment_id for item in self.evidence if item.segment_id is not None
        }
        if not evidence_segment_ids.intersection(self.source_segment_ids):
            raise ValueError("highlight evidence must reference at least one source segment")
        if not any(item.type == "asr" or item.keyframe_id for item in self.evidence):
            raise ValueError("highlight evidence must include ASR or keyframe evidence")
        return self
