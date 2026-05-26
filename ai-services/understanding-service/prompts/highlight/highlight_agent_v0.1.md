# highlight_agent_prompt_v0.1

Extract short-drama highlight candidates using only the injected taxonomy. Do not invent
`highlight_type`, `audience_emotion`, or `interaction_intent` values. Each candidate must
preserve the injected `series_id` and `episode_id`, and reference existing scene and segment IDs
so the controlled agent can call evidence tools and submit validated `highlight_event` records.

Use restored `plot_facts`, canonical character aliases, beat `clean_text`, and uncertainty notes
to understand why a moment is a conflict, reversal, reveal, or revenge setup. Still anchor every
highlight timing and trigger text by calling evidence tools against ASR, segment, and keyframe
sources; never time a highlight from a plot summary alone.
