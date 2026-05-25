from typing import Literal

from pydantic import BaseModel, Field, model_validator


Certainty = Literal["observed", "inferred", "uncertain"]


class ScriptEvidenceRef(BaseModel):
    type: Literal["asr", "visual", "context", "segment", "keyframe", "scene"]
    source_id: str | None = None
    segment_id: str | None = None
    transcript_chunk_id: str | None = None
    asr_id: str | None = None
    keyframe_id: str | None = None
    text: str | None = None
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)


class ScriptRelationship(BaseModel):
    target_character_id: str
    relation: str
    certainty: Certainty = "observed"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_refs: list[ScriptEvidenceRef] = Field(default_factory=list)


class ScriptCharacter(BaseModel):
    character_id: str
    name: str
    canonical_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    role: str = ""
    description: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    relationships: list[ScriptRelationship] = Field(default_factory=list)
    evidence_refs: list[ScriptEvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def default_canonical_name(self) -> "ScriptCharacter":
        if self.canonical_name is None:
            self.canonical_name = self.name
        return self


class ScriptBeat(BaseModel):
    beat_id: str
    type: str
    speaker: str | None = None
    content: str
    raw_text: str = ""
    clean_text: str = ""
    character_emotion: str | None = None
    source_segment_ids: list[str] = Field(default_factory=list)
    source_asr_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[ScriptEvidenceRef] = Field(default_factory=list)
    certainty: Certainty = "observed"

    @model_validator(mode="after")
    def default_text_tracks(self) -> "ScriptBeat":
        if not self.raw_text:
            self.raw_text = self.content
        if not self.clean_text:
            self.clean_text = self.content
        return self


class ScriptScene(BaseModel):
    scene_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    location: str
    summary: str
    characters: list[str] = Field(default_factory=list)
    source_segment_ids: list[str] = Field(default_factory=list)
    beats: list[ScriptBeat] = Field(default_factory=list)


class PlotFact(BaseModel):
    fact_id: str
    type: str
    statement: str
    certainty: Certainty = "observed"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_scene_ids: list[str] = Field(default_factory=list)
    source_segment_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[ScriptEvidenceRef] = Field(default_factory=list)


class ScriptUncertainty(BaseModel):
    uncertainty_id: str
    field: str
    description: str
    candidates: list[str] = Field(default_factory=list)
    chosen: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_segment_ids: list[str] = Field(default_factory=list)


class ObservedScript(BaseModel):
    script_id: str
    series_id: str
    episode_id: str
    title: str
    summary: str
    characters: list[ScriptCharacter] = Field(default_factory=list)
    scenes: list[ScriptScene] = Field(default_factory=list)
    plot_facts: list[PlotFact] = Field(default_factory=list)
    uncertainties: list[ScriptUncertainty] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"series_id: {self.series_id}",
            "",
            f"episode_id: {self.episode_id}",
            "",
            "## Summary",
            "",
            self.summary,
        ]
        if self.characters:
            lines.extend(["", "## Characters"])
            for character in self.characters:
                alias_text = f" ({', '.join(character.aliases)})" if character.aliases else ""
                role_text = f" - {character.role}" if character.role else ""
                lines.append(f"- {character.canonical_name}{alias_text}{role_text}")
        if self.plot_facts:
            lines.extend(["", "## Plot Facts"])
            for fact in self.plot_facts:
                source_segments = ", ".join(fact.source_segment_ids)
                lines.append(
                    f"- [{fact.certainty}] {fact.statement} "
                    f"(confidence: {fact.confidence:.2f}; segments: {source_segments})"
                )
        if self.uncertainties:
            lines.extend(["", "## Uncertainties"])
            for uncertainty in self.uncertainties:
                candidates = " / ".join(uncertainty.candidates)
                chosen = f"; chosen: {uncertainty.chosen}" if uncertainty.chosen else ""
                lines.append(f"- {uncertainty.field}: {candidates}{chosen}. {uncertainty.description}")
        lines.extend(["", "## Scenes"])
        for scene in self.scenes:
            lines.extend(
                [
                    "",
                    f"### {scene.scene_id} ({scene.start_ms}-{scene.end_ms}ms)",
                    "",
                    f"- Location: {scene.location}",
                    f"- Source segments: {', '.join(scene.source_segment_ids)}",
                    f"- Summary: {scene.summary}",
                ]
            )
            for beat in scene.beats:
                speaker = f"{beat.speaker}: " if beat.speaker else ""
                lines.append(f"- {beat.type}: {speaker}{beat.clean_text or beat.content}")
        lines.append("")
        return "\n".join(lines)
