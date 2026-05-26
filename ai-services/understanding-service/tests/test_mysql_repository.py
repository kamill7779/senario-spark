import re

from app.repositories import MySQLRepository
from schemas.highlight import HighlightEvent
from schemas.script import ObservedScript
from schemas.taxonomy import TAXONOMY
from schemas.video import TranscriptChunk


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        params = params or ()
        compact = " ".join(sql.split())
        if compact.startswith("INSERT INTO"):
            self._insert(compact, params)
            self.result = None
            return 1
        if compact.startswith("SELECT"):
            self.result = self._select(compact, params)
            return len(self.result) if isinstance(self.result, list) else int(self.result is not None)
        if compact.startswith("DELETE FROM"):
            return self._delete(compact, params)
        raise AssertionError(f"unexpected SQL: {compact}")

    def fetchone(self):
        if isinstance(self.result, list):
            return self.result[0] if self.result else None
        return self.result

    def fetchall(self):
        if self.result is None:
            return []
        if isinstance(self.result, list):
            return self.result
        return [self.result]

    def _insert(self, sql, params):
        match = re.search(r"INSERT INTO `(?P<table>\w+)` \((?P<columns>.+?)\) VALUES", sql)
        assert match, sql
        table = match.group("table")
        columns = [column.strip(" `") for column in match.group("columns").split(",")]
        row = dict(zip(columns, params[: len(columns)], strict=True))
        primary_key = self.connection.primary_keys[table]
        self.connection.tables.setdefault(table, {})[row[primary_key]] = row

    def _select(self, sql, params):
        match = re.search(r"FROM `(?P<table>\w+)` WHERE (?P<where>.+?)(?: ORDER BY|$)", sql)
        assert match, sql
        table = match.group("table")
        columns = re.findall(r"`(?P<column>\w+)` = %s", match.group("where"))
        assert columns, sql
        rows = [
            row
            for row in self.connection.tables.get(table, {}).values()
            if all(row.get(column) == value for column, value in zip(columns, params, strict=True))
        ]
        if "`evidence_index`" in sql:
            return sorted(rows, key=lambda row: row.get("evidence_index", 0))
        if "`start_ms`" in sql:
            return sorted(rows, key=lambda row: row.get("start_ms", 0))
        if "`timestamp_ms`" in sql:
            return sorted(rows, key=lambda row: row.get("timestamp_ms", 0))
        return rows[0] if rows else None

    def _delete(self, sql, params):
        match = re.search(r"DELETE FROM `(?P<table>\w+)` WHERE (?P<where>.+)$", sql)
        assert match, sql
        table = match.group("table")
        columns = re.findall(r"`(?P<column>\w+)` = %s", match.group("where"))
        assert columns, sql
        rows = self.connection.tables.get(table, {})
        deleted = 0
        for primary_key, row in list(rows.items()):
            if all(row.get(column) == value for column, value in zip(columns, params, strict=True)):
                del rows[primary_key]
                deleted += 1
        return deleted


class FakeConnection:
    primary_keys = {
        "analysis_jobs": "job_id",
        "transcript_chunks": "chunk_id",
        "observed_scripts": "script_id",
        "highlight_candidates": "candidate_id",
        "highlight_events": "highlight_id",
        "highlight_event_evidence": "evidence_id",
    }

    def __init__(self):
        self.tables = {}
        self.commits = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


def _highlight_event() -> HighlightEvent:
    return HighlightEvent.model_validate(
        {
            "highlight_id": "hl_repo_001",
            "candidate_id": "hc_repo_001",
            "series_id": "series_repo",
            "episode_id": "ep_repo",
            "taxonomy_version": TAXONOMY.taxonomy_version,
            "highlight_type": "conflict",
            "secondary_highlight_types": [],
            "summary": "两名角色爆发正面冲突。",
            "trigger_text_clean": "你凭什么这样做？",
            "trigger_text_raw": "你凭什么这样做",
            "primary_audience_emotion": "anger",
            "audience_emotions": ["anger"],
            "interaction_intent": "vent",
            "sentiment_polarity": "negative",
            "intensity": 0.7,
            "confidence": 0.8,
            "timing": {"start_ms": 1000, "peak_ms": 1500, "end_ms": 2000},
            "source_scene_id": "scene_repo_001",
            "source_segment_ids": ["seg_repo_001"],
            "evidence": [
                {
                    "type": "asr",
                    "segment_id": "seg_repo_001",
                    "transcript_chunk_id": "aud_repo_001",
                    "asr_id": "1",
                    "text": "你凭什么这样做",
                    "start_ms": 1000,
                    "end_ms": 1800,
                }
            ],
            "review_status": "pending",
            "enabled": False,
        }
    )


def test_mysql_repository_writes_and_reads_core_records():
    repo = MySQLRepository(FakeConnection())

    repo.save_analysis_job(
        {
            "job_id": "job_repo_001",
            "series_id": "series_repo",
            "episode_id": "ep_repo",
            "video_id": "vid_repo",
            "status": "pending",
            "pipeline_version": "analysis_pipeline_v0.1",
            "taxonomy_version": TAXONOMY.taxonomy_version,
            "video_source": "file:///repo.mp4",
            "input_payload": {"video": "repo.mp4"},
            "output_dir": "outputs/series_repo/ep_repo",
            "error": None,
        }
    )
    repo.save_transcript_chunk(
        TranscriptChunk(
            chunk_id="aud_repo_001",
            audio_id="audio_repo",
            series_id="series_repo",
            episode_id="ep_repo",
            start_ms=1000,
            end_ms=2000,
            text="你凭什么这样做",
            provider="test",
            model="fixture",
            asr_segments=[
                {"asr_id": "1", "start_ms": 1000, "end_ms": 1800, "text": "你凭什么这样做"}
            ],
        )
    )
    event = _highlight_event()
    repo.save_highlight_event(event)
    repo.save_highlight_event_evidence(event)

    assert repo.get_analysis_job("job_repo_001")["episode_id"] == "ep_repo"
    assert repo.get_transcript_chunk("aud_repo_001")["asr_segments"][0]["text"] == "你凭什么这样做"
    assert repo.get_highlight_event("hl_repo_001")["timing"]["peak_ms"] == 1500
    assert repo.list_highlight_events("series_repo", "ep_repo")[0]["highlight_id"] == "hl_repo_001"
    assert repo.list_highlight_event_evidence("hl_repo_001")[0]["type"] == "asr"


def test_repository_clears_episode_script_and_highlight_outputs_before_rerun():
    connection = FakeConnection()
    repo = MySQLRepository(connection)
    script = ObservedScript.model_validate(
        {
            "script_id": "script_repo_001",
            "series_id": "series_repo",
            "episode_id": "ep_repo",
            "title": "旧剧本",
            "summary": "旧摘要",
            "characters": [],
            "scenes": [],
            "plot_facts": [],
            "uncertainties": [],
        }
    )
    repo.save_observed_script(script, script.to_markdown())
    event = _highlight_event()
    repo.save_highlight_candidate(event)
    repo.save_highlight_event(event)
    repo.save_highlight_event_evidence(event)

    repo.delete_observed_scripts_for_episode("series_repo", "ep_repo")
    repo.delete_highlight_outputs_for_episode("series_repo", "ep_repo")

    assert connection.tables["observed_scripts"] == {}
    assert connection.tables["highlight_candidates"] == {}
    assert connection.tables["highlight_events"] == {}
    assert connection.tables["highlight_event_evidence"] == {}
