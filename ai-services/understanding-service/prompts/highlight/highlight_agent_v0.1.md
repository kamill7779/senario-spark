# highlight_agent_prompt_v0.1

Extract short-drama highlight candidates using only the injected taxonomy. Do not invent
`highlight_type`, `audience_emotion`, or `interaction_intent` values. Each candidate must
reference existing scene and segment IDs so the controlled agent can call evidence tools and
submit validated `highlight_event` records.
