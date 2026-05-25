# Plot Restoration Enhancement Design

## Goal

Absorb useful patterns from `D:\Project\open-design` into the SenarioSpark understanding service so the pipeline can recover coherent short-drama characters, relationships, plot facts, and high-confidence highlights from fragmented ASR and segment evidence.

## What The Demo Contributes

`open-design` is not a backend analysis demo. Its useful pieces are video prompt templates and transcript guidance:

- Time-coded storyboard prompts split a clip into micro-beats with clear action, emotion, camera, and sound cues.
- Character continuity constraints keep identity, costume, action, and emotional state stable across shots.
- Negative prompts explicitly forbid drift, unsupported details, and artifacts.
- Transcript guidance treats transcription quality as a gate, with cleaning, retry, and import rules before downstream composition.

## Design

Keep the current deterministic Analysis Workflow. Do not turn the whole service into a large agent. Strengthen the model-facing contract in three places:

1. Segment understanding should expose richer visual evidence: visible characters, actions, expressions, shot cues, sound cues, and a compact power dynamic.
2. Observed script generation should become evidence-constrained plot restoration, not a transcript rewrite. It should normalize character aliases, keep raw and clean beat text, record plot facts, and mark uncertain ASR/name/relationship repairs.
3. Highlight extraction should consume restored plot facts and uncertainties, but still call tools to anchor timing and evidence.

All additions must remain Pydantic-validated and evidence-linked through `source_segment_ids`, transcript refs, and keyframe refs.

## Implementation Plan

### Task 1: Contract Tests

Add tests that fail until:

- `ObservedScript` accepts characters with canonical names, aliases, relationships, evidence refs, plot facts, and uncertainties.
- `to_markdown()` displays restored plot facts and uncertainty notes.
- fallback script generation merges fractured ASR into clean beat text while preserving raw text and segment evidence.
- `SegmentUnderstanding` can carry visual evidence dimensions borrowed from storyboard prompts.

### Task 2: Schema Enhancement

Modify:

- `schemas/script.py`
- `schemas/video.py`

Add optional but structured fields with defaults to avoid breaking existing persisted rows.

### Task 3: Prompt Enhancement

Modify:

- `pipelines/script_generation/generator.py`
- `pipelines/video_analysis/understanding.py`
- `pipelines/highlight_extraction/agent.py`
- `prompts/script/observed_script_v0.1.md`
- `prompts/highlight/highlight_agent_v0.1.md`

Prompts must explicitly separate observed, inferred, and uncertain content, and forbid unsupported invention.

### Task 4: Fallback And Normalization

Modify `pipelines/script_generation/generator.py` so local fallback produces the richer structure from existing ASR and segment understanding evidence. This keeps tests deterministic and gives the real model a stable target shape.

### Task 5: Verification

Run:

```powershell
python -m pytest
python -m compileall app pipelines schemas scripts
git diff --check
```

Commit the branch after verification.
