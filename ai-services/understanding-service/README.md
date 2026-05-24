# Understanding Service

Python microservice for video understanding.

Expected outputs:

- transcript chunks
- visual observations
- fused segments
- cleaned observed script
- highlight events with source evidence

## MVP run

Install local dependencies:

```powershell
python -m pip install -r requirements.txt
```

Configure MySQL through either `MYSQL_DSN` or `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER`
/ `MYSQL_PASSWORD` / `MYSQL_DATABASE`. Model keys are read from `ZHIPUAI_API_KEY` and
`DEEPSEEK_API_KEY`; when keys are absent the local fallback path can be disabled with
`ALLOW_MODEL_FALLBACK=0`.

Initialize tables:

```powershell
python -m scripts.init_db
```

Run the full chain:

```powershell
python -m scripts.run_analysis --episode-id ep_003 --video "C:\Users\23999\Downloads\第3集.mp4"
```

Resume from a failed step:

```powershell
python -m scripts.run_analysis --episode-id ep_003 --video "C:\Users\23999\Downloads\第3集.mp4" --resume-from highlight_extraction_agent
```

Outputs are written under `outputs/<episode_id>/`, including `audio.wav`, `audio_chunks/`,
`keyframes/`, `observed_script.json`, `observed_script.md`, and `highlight_events.json`.

