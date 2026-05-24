# observed_script_prompt_v0.1

Generate an observed script from structured ASR, keyframe, and segment-understanding evidence.
Return only JSON that matches the `ObservedScript` Pydantic schema. Keep `source_segment_ids`
on every scene and beat so downstream highight extraction can trace back to video evidence.
