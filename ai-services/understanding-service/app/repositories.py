from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from schemas.highlight import HighlightCandidate, HighlightEvent
from schemas.script import ObservedScript
from schemas.video import (
    AudioAsset,
    Keyframe,
    SegmentUnderstanding,
    TranscriptChunk,
    UnderstandingPackage,
    VideoAsset,
    VideoSegment,
)


SCHEMA_DDL = [
    """
    CREATE TABLE IF NOT EXISTS `analysis_jobs` (
      `job_id` VARCHAR(128) PRIMARY KEY,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `video_id` VARCHAR(128) NOT NULL,
      `status` VARCHAR(32) NOT NULL,
      `pipeline_version` VARCHAR(64) NOT NULL,
      `taxonomy_version` VARCHAR(64) NOT NULL,
      `video_source` TEXT,
      `input_payload` JSON,
      `output_dir` TEXT,
      `error` TEXT,
      `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
      `completed_at` DATETIME(6) NULL,
      INDEX `idx_analysis_jobs_series_episode` (`series_id`, `episode_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `analysis_step_runs` (
      `step_run_id` VARCHAR(160) PRIMARY KEY,
      `job_id` VARCHAR(128) NOT NULL,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `step_name` VARCHAR(128) NOT NULL,
      `status` VARCHAR(32) NOT NULL,
      `input_artifact_ids` JSON,
      `output_artifact_ids` JSON,
      `model_provider` VARCHAR(64),
      `model_name` VARCHAR(128),
      `prompt_version` VARCHAR(64),
      `schema_version` VARCHAR(64),
      `taxonomy_version` VARCHAR(64),
      `tool_call_count` INT NOT NULL DEFAULT 0,
      `latency_ms` INT NOT NULL DEFAULT 0,
      `error` TEXT,
      `started_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
      `completed_at` DATETIME(6) NULL,
      INDEX `idx_step_runs_job_step` (`job_id`, `step_name`),
      INDEX `idx_step_runs_series_episode_step` (`series_id`, `episode_id`, `step_name`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `video_assets` (
      `video_id` VARCHAR(128) PRIMARY KEY,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `source_url` TEXT NOT NULL,
      `storage_uri` TEXT NOT NULL,
      `duration_ms` INT NOT NULL,
      `width` INT NULL,
      `height` INT NULL,
      `fps` DOUBLE NULL,
      `codec` VARCHAR(64),
      `checksum` VARCHAR(128),
      `status` VARCHAR(32) NOT NULL,
      INDEX `idx_video_assets_series_episode` (`series_id`, `episode_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `audio_assets` (
      `audio_id` VARCHAR(128) PRIMARY KEY,
      `video_id` VARCHAR(128) NOT NULL,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `storage_uri` TEXT NOT NULL,
      `sample_rate` INT NOT NULL,
      `channels` INT NOT NULL,
      `duration_ms` INT NOT NULL,
      INDEX `idx_audio_assets_series_episode` (`series_id`, `episode_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `transcript_chunks` (
      `chunk_id` VARCHAR(128) PRIMARY KEY,
      `audio_id` VARCHAR(128) NOT NULL,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `start_ms` INT NOT NULL,
      `end_ms` INT NOT NULL,
      `text` TEXT NOT NULL,
      `provider` VARCHAR(64) NOT NULL,
      `model` VARCHAR(128) NOT NULL,
      `asr_segments` JSON NOT NULL,
      INDEX `idx_transcript_series_episode_time` (`series_id`, `episode_id`, `start_ms`, `end_ms`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `video_segments` (
      `segment_id` VARCHAR(128) PRIMARY KEY,
      `video_id` VARCHAR(128) NOT NULL,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `start_ms` INT NOT NULL,
      `end_ms` INT NOT NULL,
      `keyframe_ids` JSON NOT NULL,
      INDEX `idx_video_segments_series_episode_time` (`series_id`, `episode_id`, `start_ms`, `end_ms`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `keyframes` (
      `keyframe_id` VARCHAR(160) PRIMARY KEY,
      `segment_id` VARCHAR(128) NOT NULL,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `timestamp_ms` INT NOT NULL,
      `image_uri` TEXT NOT NULL,
      INDEX `idx_keyframes_segment` (`segment_id`),
      INDEX `idx_keyframes_series_episode_segment` (`series_id`, `episode_id`, `segment_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `segment_understandings` (
      `segment_understanding_id` VARCHAR(160) PRIMARY KEY,
      `segment_id` VARCHAR(128) NOT NULL,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `start_ms` INT NOT NULL,
      `end_ms` INT NOT NULL,
      `keyframe_ids` JSON NOT NULL,
      `transcript_refs` JSON NOT NULL,
      `dialogue_raw` TEXT,
      `visual_summary` TEXT,
      `scene` TEXT,
      `main_actions` TEXT,
      `emotion_hint` TEXT,
      `conflict_level` INT NOT NULL,
      `visible_characters` JSON NOT NULL,
      `character_actions` JSON NOT NULL,
      `facial_expressions` TEXT,
      `shot_cues` TEXT,
      `sound_cues` TEXT,
      `power_dynamic` TEXT,
      INDEX `idx_segment_understandings_series_episode` (`series_id`, `episode_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `understanding_packages` (
      `package_id` VARCHAR(160) PRIMARY KEY,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `video_id` VARCHAR(128) NOT NULL,
      `pipeline_version` VARCHAR(64) NOT NULL,
      `video_asset_id` VARCHAR(128) NOT NULL,
      `audio_asset_id` VARCHAR(128) NOT NULL,
      `transcript_chunk_ids` JSON NOT NULL,
      `video_segment_ids` JSON NOT NULL,
      `segment_understanding_ids` JSON NOT NULL,
      INDEX `idx_understanding_packages_series_episode` (`series_id`, `episode_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `observed_scripts` (
      `script_id` VARCHAR(160) PRIMARY KEY,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `title` TEXT NOT NULL,
      `summary` TEXT NOT NULL,
      `content_json` JSON NOT NULL,
      `content_markdown` MEDIUMTEXT NOT NULL,
      INDEX `idx_observed_scripts_series_episode` (`series_id`, `episode_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `highlight_candidates` (
      `candidate_id` VARCHAR(160) PRIMARY KEY,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `taxonomy_version` VARCHAR(64) NOT NULL,
      `source_scene_id` VARCHAR(128) NOT NULL,
      `source_segment_ids` JSON NOT NULL,
      `highlight_type` VARCHAR(64) NOT NULL,
      `secondary_highlight_types` JSON NOT NULL,
      `summary` TEXT NOT NULL,
      `trigger_text_clean` TEXT NOT NULL,
      `primary_audience_emotion` VARCHAR(64) NOT NULL,
      `audience_emotions` JSON NOT NULL,
      `interaction_intent` VARCHAR(64) NOT NULL,
      `sentiment_polarity` VARCHAR(32) NOT NULL,
      `intensity` DOUBLE NOT NULL,
      `confidence` DOUBLE NOT NULL,
      `raw_json` JSON NOT NULL,
      INDEX `idx_highlight_candidates_series_episode` (`series_id`, `episode_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `highlight_events` (
      `highlight_id` VARCHAR(160) PRIMARY KEY,
      `candidate_id` VARCHAR(160),
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `taxonomy_version` VARCHAR(64) NOT NULL,
      `highlight_type` VARCHAR(64) NOT NULL,
      `secondary_highlight_types` JSON NOT NULL,
      `summary` TEXT NOT NULL,
      `trigger_text_clean` TEXT NOT NULL,
      `trigger_text_raw` TEXT NOT NULL,
      `primary_audience_emotion` VARCHAR(64) NOT NULL,
      `audience_emotions` JSON NOT NULL,
      `interaction_intent` VARCHAR(64) NOT NULL,
      `sentiment_polarity` VARCHAR(32) NOT NULL,
      `intensity` DOUBLE NOT NULL,
      `confidence` DOUBLE NOT NULL,
      `start_ms` INT NOT NULL,
      `peak_ms` INT NOT NULL,
      `end_ms` INT NOT NULL,
      `source_scene_id` VARCHAR(128) NOT NULL,
      `source_segment_ids` JSON NOT NULL,
      `evidence` JSON NOT NULL,
      `review_status` VARCHAR(32) NOT NULL,
      `enabled` BOOLEAN NOT NULL DEFAULT FALSE,
      `raw_json` JSON NOT NULL,
      INDEX `idx_highlight_events_series_episode_time` (`series_id`, `episode_id`, `start_ms`, `end_ms`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS `highlight_event_evidence` (
      `evidence_id` VARCHAR(192) PRIMARY KEY,
      `highlight_id` VARCHAR(160) NOT NULL,
      `series_id` VARCHAR(128) NOT NULL,
      `episode_id` VARCHAR(128) NOT NULL,
      `evidence_index` INT NOT NULL,
      `type` VARCHAR(32) NOT NULL,
      `segment_id` VARCHAR(128),
      `transcript_chunk_id` VARCHAR(128),
      `asr_id` VARCHAR(64),
      `keyframe_id` VARCHAR(160),
      `text` TEXT,
      `description` TEXT,
      `start_ms` INT NULL,
      `end_ms` INT NULL,
      `raw_json` JSON NOT NULL,
      INDEX `idx_highlight_evidence_highlight` (`highlight_id`, `evidence_index`),
      INDEX `idx_highlight_evidence_series_episode` (`series_id`, `episode_id`, `highlight_id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


SERIES_COLUMN_MIGRATIONS = [
    ("analysis_jobs", "job_id"),
    ("analysis_step_runs", "job_id"),
    ("video_assets", "video_id"),
    ("audio_assets", "video_id"),
    ("transcript_chunks", "audio_id"),
    ("video_segments", "video_id"),
    ("keyframes", "segment_id"),
    ("segment_understandings", "segment_id"),
    ("understanding_packages", "package_id"),
    ("observed_scripts", "script_id"),
    ("highlight_candidates", "candidate_id"),
    ("highlight_events", "candidate_id"),
    ("highlight_event_evidence", "highlight_id"),
]


SERIES_INDEX_MIGRATIONS = [
    ("analysis_jobs", "idx_analysis_jobs_series_episode", ("series_id", "episode_id")),
    (
        "analysis_step_runs",
        "idx_step_runs_series_episode_step",
        ("series_id", "episode_id", "step_name"),
    ),
    ("video_assets", "idx_video_assets_series_episode", ("series_id", "episode_id")),
    ("audio_assets", "idx_audio_assets_series_episode", ("series_id", "episode_id")),
    (
        "transcript_chunks",
        "idx_transcript_series_episode_time",
        ("series_id", "episode_id", "start_ms", "end_ms"),
    ),
    (
        "video_segments",
        "idx_video_segments_series_episode_time",
        ("series_id", "episode_id", "start_ms", "end_ms"),
    ),
    (
        "keyframes",
        "idx_keyframes_series_episode_segment",
        ("series_id", "episode_id", "segment_id"),
    ),
    (
        "segment_understandings",
        "idx_segment_understandings_series_episode",
        ("series_id", "episode_id"),
    ),
    (
        "understanding_packages",
        "idx_understanding_packages_series_episode",
        ("series_id", "episode_id"),
    ),
    ("observed_scripts", "idx_observed_scripts_series_episode", ("series_id", "episode_id")),
    (
        "highlight_candidates",
        "idx_highlight_candidates_series_episode",
        ("series_id", "episode_id"),
    ),
    (
        "highlight_events",
        "idx_highlight_events_series_episode_time",
        ("series_id", "episode_id", "start_ms", "end_ms"),
    ),
    (
        "highlight_event_evidence",
        "idx_highlight_evidence_series_episode",
        ("series_id", "episode_id", "highlight_id"),
    ),
]


SEGMENT_UNDERSTANDING_COLUMN_MIGRATIONS = [
    ("visible_characters", "JSON NULL", "conflict_level"),
    ("character_actions", "JSON NULL", "visible_characters"),
    ("facial_expressions", "TEXT", "character_actions"),
    ("shot_cues", "TEXT", "facial_expressions"),
    ("sound_cues", "TEXT", "shot_cues"),
    ("power_dynamic", "TEXT", "sound_cues"),
]


JSON_COLUMNS = {
    "input_payload",
    "input_artifact_ids",
    "output_artifact_ids",
    "asr_segments",
    "keyframe_ids",
    "transcript_refs",
    "visible_characters",
    "character_actions",
    "transcript_chunk_ids",
    "video_segment_ids",
    "segment_understanding_ids",
    "content_json",
    "source_segment_ids",
    "secondary_highlight_types",
    "audience_emotions",
    "evidence",
    "raw_json",
}


class MySQLRepository:
    def __init__(self, connection):
        self.connection = connection

    def init_schema(self) -> None:
        with self.connection.cursor() as cursor:
            for statement in SCHEMA_DDL:
                cursor.execute(statement)
            self._ensure_series_id_columns(cursor)
            self._ensure_segment_understanding_columns(cursor)
            self._ensure_series_id_indexes(cursor)
        self.connection.commit()

    def _ensure_series_id_columns(self, cursor) -> None:
        for table, after_column in SERIES_COLUMN_MIGRATIONS:
            cursor.execute(
                """
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = %s
                  AND column_name = 'series_id'
                """,
                (table,),
            )
            row = cursor.fetchone() or {}
            if int(row.get("column_count", 0)) > 0:
                continue
            cursor.execute(
                f"""
                ALTER TABLE `{table}`
                ADD COLUMN `series_id` VARCHAR(128) NOT NULL DEFAULT 'default_series'
                AFTER `{after_column}`
                """
            )

    def _ensure_segment_understanding_columns(self, cursor) -> None:
        for column_name, column_type, after_column in SEGMENT_UNDERSTANDING_COLUMN_MIGRATIONS:
            cursor.execute(
                """
                SELECT COUNT(*) AS column_count
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = 'segment_understandings'
                  AND column_name = %s
                """,
                (column_name,),
            )
            row = cursor.fetchone() or {}
            if int(row.get("column_count", 0)) > 0:
                continue
            cursor.execute(
                f"""
                ALTER TABLE `segment_understandings`
                ADD COLUMN `{column_name}` {column_type}
                AFTER `{after_column}`
                """
            )

    def _ensure_series_id_indexes(self, cursor) -> None:
        for table, index_name, columns in SERIES_INDEX_MIGRATIONS:
            cursor.execute(
                """
                SELECT COUNT(*) AS index_count
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = %s
                  AND index_name = %s
                """,
                (table, index_name),
            )
            row = cursor.fetchone() or {}
            if int(row.get("index_count", 0)) > 0:
                continue
            quoted_columns = ", ".join(f"`{column}`" for column in columns)
            cursor.execute(f"CREATE INDEX `{index_name}` ON `{table}` ({quoted_columns})")

    def save_analysis_job(self, job: dict[str, Any]) -> None:
        self._upsert("analysis_jobs", job, "job_id")

    def update_analysis_job_status(
        self, job_id: str, status: str, error: str | None = None, completed: bool = False
    ) -> None:
        row = self.get_analysis_job(job_id) or {"job_id": job_id}
        row["status"] = status
        row["error"] = error
        if completed:
            row["completed_at"] = _now_iso()
        self.save_analysis_job(row)

    def get_analysis_job(self, job_id: str) -> dict[str, Any] | None:
        return self._fetch_one("analysis_jobs", "job_id", job_id)

    def save_step_run(self, step_run: dict[str, Any]) -> None:
        self._upsert("analysis_step_runs", step_run, "step_run_id")

    def save_video_asset(self, asset: VideoAsset) -> None:
        self._upsert("video_assets", asset, "video_id")

    def get_video_asset(self, video_id: str) -> dict[str, Any] | None:
        return self._fetch_one("video_assets", "video_id", video_id)

    def save_audio_asset(self, asset: AudioAsset) -> None:
        self._upsert("audio_assets", asset, "audio_id")

    def get_audio_asset(self, audio_id: str) -> dict[str, Any] | None:
        return self._fetch_one("audio_assets", "audio_id", audio_id)

    def save_transcript_chunk(self, chunk: TranscriptChunk) -> None:
        self._upsert("transcript_chunks", chunk, "chunk_id")

    def get_transcript_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        return self._fetch_one("transcript_chunks", "chunk_id", chunk_id)

    def list_transcript_chunks(
        self,
        series_id: str,
        episode_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if episode_id is None:
            return self._fetch_many("transcript_chunks", "episode_id", series_id)
        return self._fetch_many_by_columns(
            "transcript_chunks",
            {"series_id": series_id, "episode_id": episode_id},
        )

    def save_video_segment(self, segment: VideoSegment) -> None:
        self._upsert("video_segments", segment, "segment_id")

    def list_video_segments(
        self,
        series_id: str,
        episode_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if episode_id is None:
            return self._fetch_many("video_segments", "episode_id", series_id)
        return self._fetch_many_by_columns(
            "video_segments",
            {"series_id": series_id, "episode_id": episode_id},
        )

    def save_keyframe(self, keyframe: Keyframe) -> None:
        self._upsert("keyframes", keyframe, "keyframe_id")

    def list_keyframes(
        self,
        series_id: str,
        episode_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if episode_id is None:
            return self._fetch_many("keyframes", "episode_id", series_id)
        return self._fetch_many_by_columns(
            "keyframes",
            {"series_id": series_id, "episode_id": episode_id},
        )

    def save_segment_understanding(self, understanding: SegmentUnderstanding) -> None:
        self._upsert(
            "segment_understandings",
            understanding,
            "segment_understanding_id",
        )

    def list_segment_understandings(
        self,
        series_id: str,
        episode_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if episode_id is None:
            return self._fetch_many("segment_understandings", "episode_id", series_id)
        return self._fetch_many_by_columns(
            "segment_understandings",
            {"series_id": series_id, "episode_id": episode_id},
        )

    def save_understanding_package(self, package: UnderstandingPackage) -> None:
        self._upsert("understanding_packages", package, "package_id")

    def get_understanding_package(self, package_id: str) -> dict[str, Any] | None:
        return self._fetch_one("understanding_packages", "package_id", package_id)

    def save_observed_script(self, script: ObservedScript, markdown: str) -> None:
        self._upsert(
            "observed_scripts",
            {
                "script_id": script.script_id,
                "series_id": script.series_id,
                "episode_id": script.episode_id,
                "title": script.title,
                "summary": script.summary,
                "content_json": script.model_dump(mode="json"),
                "content_markdown": markdown,
            },
            "script_id",
        )

    def get_observed_script(self, script_id: str) -> dict[str, Any] | None:
        return self._fetch_one("observed_scripts", "script_id", script_id)

    def save_highlight_candidate(self, candidate: HighlightCandidate) -> None:
        row = candidate.model_dump(mode="json")
        row["raw_json"] = candidate.model_dump(mode="json")
        self._upsert("highlight_candidates", row, "candidate_id")

    def save_highlight_event(self, event: HighlightEvent) -> None:
        row = event.model_dump(mode="json")
        row.pop("timing", None)
        row.update(
            {
                "start_ms": event.timing.start_ms,
                "peak_ms": event.timing.peak_ms,
                "end_ms": event.timing.end_ms,
                "raw_json": event.model_dump(mode="json"),
            }
        )
        self._upsert("highlight_events", row, "highlight_id")

    def get_highlight_event(self, highlight_id: str) -> dict[str, Any] | None:
        row = self._fetch_one("highlight_events", "highlight_id", highlight_id)
        if row and "timing" not in row:
            row["timing"] = {
                "start_ms": row.get("start_ms"),
                "peak_ms": row.get("peak_ms"),
                "end_ms": row.get("end_ms"),
            }
        return row

    def list_highlight_events(self, series_id: str, episode_id: str) -> list[dict[str, Any]]:
        rows = self._fetch_many_by_columns(
            "highlight_events",
            {"series_id": series_id, "episode_id": episode_id},
        )
        for row in rows:
            if "timing" not in row:
                row["timing"] = {
                    "start_ms": row.get("start_ms"),
                    "peak_ms": row.get("peak_ms"),
                    "end_ms": row.get("end_ms"),
                }
        return rows

    def save_highlight_event_evidence(self, event: HighlightEvent) -> None:
        for index, evidence in enumerate(event.evidence):
            evidence_json = evidence.model_dump(mode="json")
            self._upsert(
                "highlight_event_evidence",
                {
                    "evidence_id": f"{event.highlight_id}:{index:03d}",
                    "highlight_id": event.highlight_id,
                    "series_id": event.series_id,
                    "episode_id": event.episode_id,
                    "evidence_index": index,
                    **evidence_json,
                    "raw_json": evidence_json,
                },
                "evidence_id",
            )

    def list_highlight_event_evidence(self, highlight_id: str) -> list[dict[str, Any]]:
        return self._fetch_many("highlight_event_evidence", "highlight_id", highlight_id)

    def _upsert(self, table: str, data: BaseModel | dict[str, Any], primary_key: str) -> None:
        row = _as_dict(data)
        row = {key: _encode_value(key, value) for key, value in row.items()}
        columns = list(row)
        placeholders = ", ".join(["%s"] * len(columns))
        quoted_columns = ", ".join(f"`{column}`" for column in columns)
        updates = ", ".join(
            f"`{column}` = VALUES(`{column}`)" for column in columns if column != primary_key
        )
        sql = (
            f"INSERT INTO `{table}` ({quoted_columns}) VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {updates}"
        )
        with self.connection.cursor() as cursor:
            cursor.execute(sql, tuple(row[column] for column in columns))
        self.connection.commit()

    def _fetch_one(self, table: str, column: str, value: Any) -> dict[str, Any] | None:
        sql = f"SELECT * FROM `{table}` WHERE `{column}` = %s"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, (value,))
            row = cursor.fetchone()
        return _decode_row(row) if row else None

    def _fetch_many(self, table: str, column: str, value: Any) -> list[dict[str, Any]]:
        order_clause = _order_clause(table)
        sql = f"SELECT * FROM `{table}` WHERE `{column}` = %s{order_clause}"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, (value,))
            rows = cursor.fetchall()
        return [_decode_row(row) for row in rows]

    def _fetch_many_by_columns(self, table: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        where_clause = " AND ".join(f"`{column}` = %s" for column in filters)
        sql = f"SELECT * FROM `{table}` WHERE {where_clause}{_order_clause(table)}"
        with self.connection.cursor() as cursor:
            cursor.execute(sql, tuple(filters.values()))
            rows = cursor.fetchall()
        return [_decode_row(row) for row in rows]


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")


def _as_dict(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return dict(value)


def _encode_value(key: str, value: Any) -> Any:
    if key in JSON_COLUMNS:
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
    decoded = dict(row)
    for key, value in list(decoded.items()):
        if key in {"visible_characters", "character_actions"} and value is None:
            decoded[key] = []
            continue
        if key in {"facial_expressions", "shot_cues", "sound_cues", "power_dynamic"} and value is None:
            decoded[key] = ""
            continue
        if key in JSON_COLUMNS and isinstance(value, str):
            decoded[key] = json.loads(value)
    if "enabled" in decoded:
        decoded["enabled"] = bool(decoded["enabled"])
    return decoded


def _order_clause(table: str) -> str:
    if table == "highlight_event_evidence":
        return " ORDER BY `evidence_index` ASC"
    if table in {"transcript_chunks", "video_segments", "highlight_events"}:
        return " ORDER BY `start_ms` ASC"
    if table == "keyframes":
        return " ORDER BY `timestamp_ms` ASC"
    if table == "segment_understandings":
        return " ORDER BY `start_ms` ASC"
    return ""
