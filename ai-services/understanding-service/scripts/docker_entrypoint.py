from __future__ import annotations

import os
import sys
import time

from app.config import Settings
from app.database import connect_mysql, mysql_config_from_env
from app.repositories import MySQLRepository
from app.workflow import AnalysisWorkflow


def main() -> int:
    episode_id = os.environ.get("EPISODE_ID")
    video_input = os.environ.get("VIDEO_INPUT") or os.environ.get("VIDEO_PATH") or os.environ.get("VIDEO_URL")
    if not episode_id or not video_input:
        print("EPISODE_ID and VIDEO_INPUT are required.", file=sys.stderr)
        print(
            'Example: docker run --env-file .env -v "%cd%/input:/input:ro" '
            'senariospark/understanding-service:local',
            file=sys.stderr,
        )
        return 2

    if os.environ.get("WAIT_FOR_MYSQL", "1") != "0":
        wait_for_mysql()

    settings = Settings.from_env()
    connection = connect_mysql()
    try:
        repository = MySQLRepository(connection)
        if os.environ.get("SKIP_INIT_DB", "0") != "1":
            repository.init_schema()
        context = AnalysisWorkflow(repository, settings).run(
            episode_id=episode_id,
            video_input=video_input,
            resume_from=os.environ.get("RESUME_FROM") or None,
        )
    finally:
        connection.close()
    print(f"analysis_job={context.job_id}")
    print(f"output_dir={context.output_dir}")
    print(f"highlight_events={len(context.highlight_events)}")
    return 0


def wait_for_mysql() -> None:
    config = mysql_config_from_env()
    timeout_seconds = int(os.environ.get("MYSQL_WAIT_TIMEOUT_SECONDS", "90"))
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            connection = connect_mysql(config)
            connection.close()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"MySQL did not become ready within {timeout_seconds}s: {last_error}")


if __name__ == "__main__":
    raise SystemExit(main())
