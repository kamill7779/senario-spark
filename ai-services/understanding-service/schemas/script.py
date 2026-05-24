from pydantic import BaseModel, Field


class ScriptCharacter(BaseModel):
    character_id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""


class ScriptBeat(BaseModel):
    beat_id: str
    type: str
    speaker: str | None = None
    content: str
    character_emotion: str | None = None
    source_segment_ids: list[str] = Field(default_factory=list)


class ScriptScene(BaseModel):
    scene_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    location: str
    summary: str
    characters: list[str] = Field(default_factory=list)
    source_segment_ids: list[str] = Field(default_factory=list)
    beats: list[ScriptBeat] = Field(default_factory=list)


class ObservedScript(BaseModel):
    script_id: str
    episode_id: str
    title: str
    summary: str
    characters: list[ScriptCharacter] = Field(default_factory=list)
    scenes: list[ScriptScene] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"episode_id: {self.episode_id}",
            "",
            "## Summary",
            "",
            self.summary,
            "",
            "## Scenes",
        ]
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
                lines.append(f"- {beat.type}: {speaker}{beat.content}")
        lines.append("")
        return "\n".join(lines)
