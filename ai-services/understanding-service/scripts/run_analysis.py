from __future__ import annotations

import argparse

from app.config import Settings
from app.database import connect_mysql
from app.repositories import MySQLRepository
from app.workflow import AnalysisWorkflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SenarioSpark MVP video analysis.")
    parser.add_argument("--series-id", required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--video", required=True, help="Local video path or http(s) URL.")
    parser.add_argument(
        "--resume-from",
        default=None,
        help="Optional step name to resume from, such as asr_transcription.",
    )
    parser.add_argument(
        "--skip-init-db",
        action="store_true",
        help="Skip the default idempotent MySQL table initialization.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings.from_env()
    connection = connect_mysql()
    try:
        repository = MySQLRepository(connection)
        if not args.skip_init_db:
            repository.init_schema()
        context = AnalysisWorkflow(repository, settings).run(
            series_id=args.series_id,
            episode_id=args.episode_id,
            video_input=args.video,
            resume_from=args.resume_from,
        )
    finally:
        connection.close()
    print(f"series_id={context.series_id}")
    print(f"episode_id={context.episode_id}")
    print(f"analysis_job={context.job_id}")
    print(f"output_dir={context.output_dir}")
    print(f"highlight_events={len(context.highlight_events)}")


if __name__ == "__main__":
    main()
