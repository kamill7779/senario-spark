from pydantic import BaseModel, Field


class VideoAsset(BaseModel):
    video_id: str
    episode_id: str
    source_url: str
    storage_uri: str
    duration_ms: int = Field(ge=0)
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)
    fps: float | None = Field(default=None, ge=0)
    codec: str | None = None
    checksum: str | None = None
    status: str = "ready"


class AudioAsset(BaseModel):
    audio_id: str
    video_id: str
    episode_id: str
    storage_uri: str
    sample_rate: int = 16000
    channels: int = 1
    duration_ms: int = Field(ge=0)


class AsrSegment(BaseModel):
    asr_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str


class TranscriptChunk(BaseModel):
    chunk_id: str
    audio_id: str
    episode_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str
    provider: str
    model: str
    asr_segments: list[AsrSegment] = Field(default_factory=list)


class VideoSegment(BaseModel):
    segment_id: str
    video_id: str
    episode_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    keyframe_ids: list[str] = Field(default_factory=list)


class Keyframe(BaseModel):
    keyframe_id: str
    segment_id: str
    episode_id: str
    timestamp_ms: int = Field(ge=0)
    image_uri: str


class SegmentUnderstanding(BaseModel):
    segment_understanding_id: str
    segment_id: str
    episode_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    keyframe_ids: list[str] = Field(default_factory=list)
    transcript_refs: list[str] = Field(default_factory=list)
    dialogue_raw: str
    visual_summary: str
    scene: str
    main_actions: str
    emotion_hint: str
    conflict_level: int = Field(ge=0, le=5)


class UnderstandingPackage(BaseModel):
    package_id: str
    episode_id: str
    video_id: str
    pipeline_version: str
    video_asset_id: str
    audio_asset_id: str
    transcript_chunk_ids: list[str]
    video_segment_ids: list[str]
    segment_understanding_ids: list[str]
