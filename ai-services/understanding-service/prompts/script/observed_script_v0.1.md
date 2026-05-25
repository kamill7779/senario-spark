# observed_script_prompt_v0.1

Generate an observed script from structured ASR, keyframe, and segment-understanding evidence.
Return only JSON that matches the `ObservedScript` Pydantic schema, including the injected
`series_id` and `episode_id`. Keep `source_segment_ids` on every scene and beat so downstream
highlight extraction can trace back to video evidence.

Treat this as evidence-constrained plot restoration, not transcript cleanup. Repair fragmented ASR
into clean beat text while preserving raw text and ASR refs. Normalize repeated character aliases
into canonical characters, infer relationships only when supported by adjacent scenes or visual
evidence, and record plot facts with `observed`, `inferred`, or `uncertain` certainty. Do not
invent unsupported identities, relationships, motives, or off-screen events.
