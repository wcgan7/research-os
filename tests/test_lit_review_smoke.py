import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from research_os.agent.tools import batch_triage
from research_os.api import routes
from research_os import launcher
from research_os.store.db import get_connection, init_schema
from research_os.store.models import Assessment, LiteratureReview, Paper
from research_os.store.store import Store


class LitReviewSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tempdir.name) / "test.sqlite3"
        conn = get_connection(db_path)
        init_schema(conn)
        self.store = Store(conn)

    def tearDown(self) -> None:
        self.store.conn.close()
        self.tempdir.cleanup()

    def test_batch_triage_only_creates_canonical_assessments(self) -> None:
        review = LiteratureReview(topic="topic", objective="objective")
        self.store.save(review)

        relevant = Paper(review_id=review.id, title="Relevant paper")
        uncertain = Paper(review_id=review.id, title="Uncertain paper")
        deferred = Paper(review_id=review.id, title="Deferred paper")
        self.store.save(relevant)
        self.store.save(uncertain)
        self.store.save(deferred)

        result = batch_triage(
            {"store": self.store, "review_id": review.id, "sources": {}},
            [
                {"paper_id": relevant.id, "relevance": "relevant", "reason": "core paper"},
                {"paper_id": uncertain.id, "relevance": "uncertain", "reason": "needs more reading"},
                {"paper_id": deferred.id, "relevance": "deferred", "reason": "save for later"},
            ],
        )

        self.assertTrue(result.ok)
        self.assertEqual(
            [p.status for p in self.store.query(Paper, review_id=review.id)],
            ["deferred", "uncertain", "relevant"],
        )

        assessments = self.store.query(Assessment, review_id=review.id)
        self.assertEqual(len(assessments), 1)
        self.assertEqual(assessments[0].paper_id, relevant.id)
        self.assertEqual(assessments[0].relevance, "relevant")

    def test_stop_review_marks_review_paused(self) -> None:
        review = LiteratureReview(topic="topic", objective="objective", status="active")
        self.store.save(review)

        run_dir = Path(self.tempdir.name) / "run"
        run_dir.mkdir()
        meta_path = run_dir / "meta.json"
        meta_path.write_text(json.dumps({"pid": 12345, "started_at": "2026-04-13T00:00:00+00:00"}))

        with (
            mock.patch.object(routes, "_get_store", return_value=self.store),
            mock.patch.object(routes, "_find_active_run_dir", return_value=run_dir),
            mock.patch.object(routes.os, "kill"),
            mock.patch.object(routes, "_pid_is_running", return_value=False),
        ):
            result = routes.stop_review(review.id)

        self.assertEqual(result["status"], "stopped")
        refreshed = self.store.get(LiteratureReview, review.id)
        self.assertIsNotNone(refreshed)
        self.assertEqual(refreshed.status, "paused")

        meta = json.loads(meta_path.read_text())
        self.assertEqual(meta["stopped_by"], "user")
        self.assertEqual(meta["exit_code"], -15)
        self.assertIn("completed_at", meta)

    def test_get_review_reports_not_running_when_pid_is_dead(self) -> None:
        review = LiteratureReview(topic="topic", objective="objective", status="active")
        self.store.save(review)
        self.store.save(Paper(review_id=review.id, title="Paper"))

        log_root = Path(self.tempdir.name) / ".research-os" / "logs" / review.id[:8]
        run_dir = log_root / "20260413_000000"
        run_dir.mkdir(parents=True)
        (run_dir / "meta.json").write_text(json.dumps({
            "pid": 54321,
            "started_at": "2026-04-13T00:00:00+00:00",
        }))

        with (
            mock.patch.object(routes, "_get_store", return_value=self.store),
            mock.patch.object(routes.Path, "home", return_value=Path(self.tempdir.name)),
            mock.patch.object(routes, "_pid_is_running", return_value=False),
        ):
            result = routes.get_review(review.id)

        self.assertFalse(result["is_running"])

    def test_get_steering_clears_pending_for_dead_run(self) -> None:
        review = LiteratureReview(topic="topic", objective="objective", status="active")
        self.store.save(review)

        log_root = Path(self.tempdir.name) / ".research-os" / "logs" / review.id[:8]
        run_dir = log_root / "20260413_000000"
        run_dir.mkdir(parents=True)
        (run_dir / "meta.json").write_text(json.dumps({
            "pid": 54321,
            "started_at": "2026-04-13T00:00:00+00:00",
        }))
        (run_dir / "steering.md").write_text("focus on benchmarks\n")

        with (
            mock.patch.object(routes.Path, "home", return_value=Path(self.tempdir.name)),
            mock.patch.object(routes, "_pid_is_running", return_value=False),
        ):
            result = routes.get_steering(review.id)

        self.assertEqual(result, {"pending": None})

    def test_launch_review_finalizes_metadata_when_subprocess_errors_after_exit(self) -> None:
        db_path = Path(self.tempdir.name) / "launcher.sqlite3"
        cache_dir = Path(self.tempdir.name) / "cache"
        log_dir = Path(self.tempdir.name) / "logs" / "run"
        log_dir.mkdir(parents=True)

        class FakeProc:
            def __init__(self) -> None:
                self.pid = 12345
                self.returncode = 7

            def communicate(self, input: str | None = None) -> None:
                raise RuntimeError("launcher interrupted")

            def poll(self) -> int:
                return self.returncode

        with (
            mock.patch.dict(os.environ, {
                "RESEARCH_OS_DB": str(db_path),
                "RESEARCH_OS_CACHE": str(cache_dir),
            }, clear=False),
            mock.patch.object(launcher, "_make_log_dir", return_value=log_dir),
            mock.patch.object(launcher.subprocess, "Popen", return_value=FakeProc()),
            mock.patch.object(launcher.Path, "home", return_value=Path(self.tempdir.name)),
        ):
            with self.assertRaisesRegex(RuntimeError, "launcher interrupted"):
                launcher.launch_review(topic="topic", objective="objective")

        conn = get_connection(db_path)
        init_schema(conn)
        store = Store(conn)
        try:
            reviews = store.query(LiteratureReview)
            self.assertEqual(len(reviews), 1)
            self.assertEqual(reviews[0].status, "paused")
        finally:
            conn.close()

        meta = json.loads((log_dir / "meta.json").read_text())
        self.assertEqual(meta["pid"], 12345)
        self.assertEqual(meta["exit_code"], 7)
        self.assertIn("completed_at", meta)


if __name__ == "__main__":
    unittest.main()
