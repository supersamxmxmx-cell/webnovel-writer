#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

import data_modules.doctor as doctor_module
import data_modules.project_status as project_status_module
import data_modules.projections as projections_module
import data_modules.run_logger as run_logger_module
from data_modules.project_phase import ProjectPhaseSnapshot
from data_modules.write_gates import format_gate_report, gate_report, issue, run_write_gate

from .test_project_phase import _make_init_ready


def _snapshot(phase: str, *, target: int = 4, latest: int = 3) -> ProjectPhaseSnapshot:
    return ProjectPhaseSnapshot(
        project_root="/tmp/book",
        phase=phase,
        target_chapter=target,
        latest_accepted_chapter=latest,
    )


def test_projection_commit_reader_handles_invalid_payloads(tmp_path: Path) -> None:
    path = tmp_path / "commit.json"
    path.write_text("{broken", encoding="utf-8")
    payload, error = projections_module._read_commit(path)
    assert payload == {}
    assert error.startswith("invalid_json:")

    path.write_text("[]", encoding="utf-8")
    assert projections_module._read_commit(path) == ({}, "commit_not_object")

    path.write_text('{"projection_status": "broken"}', encoding="utf-8")
    assert projections_module._read_commit(path) == ({}, "projection_status_not_object")


def test_projection_status_and_replay_validation(tmp_path: Path) -> None:
    assert projections_module._projection_failed({"projection_status": "bad"}) is True
    assert projections_module._projection_failed({"projection_status": {"state": "pending"}}) is True
    assert projections_module._projection_failed({"projection_status": {"state": "failed:boom"}}) is True
    assert projections_module._projection_failed({"projection_status": {"state": "done"}}) is False

    report = projections_module.replay_projections(tmp_path, start_chapter=3, end_chapter=2)
    assert report["ok"] is False
    assert report["error"] == "invalid_chapter_range"


def test_projection_reports_have_human_readable_text() -> None:
    retry = {
        "action": "retry",
        "ok": False,
        "chapter": 2,
        "commit_path": "/book/chapter_002.commit.json",
        "projection_status": {"state": "pending"},
        "error": "pending",
    }
    replay = {
        "action": "replay",
        "ok": True,
        "start_chapter": 1,
        "end_chapter": 2,
        "error": "",
        "results": [
            {"chapter": 1, "ok": True, "projection_status": {"state": "done"}},
            {"chapter": 2, "ok": False, "error": "missing_commit"},
        ],
    }
    assert "ERROR projections retry" in projections_module.format_projection_report(retry, "text")
    text = projections_module.format_projection_report(replay, "text")
    assert "OK projections replay" in text
    assert "chapter 2: ERROR missing_commit" in text
    assert json.loads(projections_module.format_projection_report(replay, "json"))["action"] == "replay"


@pytest.mark.parametrize(
    ("argv", "expected_action"),
    [
        (["projections", "--project-root", "/book", "retry", "--chapter", "9", "--format", "text"], "retry"),
        (
            [
                "projections",
                "--project-root",
                "/book",
                "replay",
                "--from-chapter",
                "1",
                "--to-chapter",
                "2",
            ],
            "replay",
        ),
    ],
)
def test_projections_main_routes_actions(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    expected_action: str,
) -> None:
    monkeypatch.setattr(sys, "argv", argv)
    if expected_action == "retry":
        monkeypatch.setattr(
            projections_module,
            "retry_projection",
            lambda *_args, **_kwargs: {
                "action": "retry",
                "ok": False,
                "chapter": 9,
                "commit_path": "missing",
                "projection_status": {},
                "error": "missing_commit",
            },
        )
    else:
        monkeypatch.setattr(
            projections_module,
            "replay_projections",
            lambda *_args, **_kwargs: {
                "action": "replay",
                "ok": True,
                "start_chapter": 1,
                "end_chapter": 2,
                "error": "",
                "results": [],
            },
        )

    with pytest.raises(SystemExit) as raised:
        projections_module.main()
    assert raised.value.code == (1 if expected_action == "retry" else 0)
    assert expected_action in capsys.readouterr().out


@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        ("no_project", "/webnovel-init"),
        ("init_scaffolded", "doctor"),
        ("init_ready", "/webnovel-plan"),
        ("plan_in_progress", "chapter 4"),
        ("chapter_contract_ready", "/webnovel-write 4"),
        ("draft_in_progress", "review/data"),
        ("ready_to_commit", "chapter-commit"),
        ("chapter_committed", "chapter 4"),
        ("projection_failed", "projection_log"),
        ("unknown", "doctor"),
    ],
)
def test_project_status_recommends_every_phase(phase: str, expected: str) -> None:
    assert expected in project_status_module.next_action_for_phase(_snapshot(phase))


def test_project_status_title_and_diagnostics_format(tmp_path: Path) -> None:
    state = tmp_path / ".webnovel" / "state.json"
    state.parent.mkdir(parents=True)
    state.write_text("[]", encoding="utf-8")
    assert project_status_module._project_title(tmp_path) == ""
    state.write_text('{"project": {"title": "  备用标题  "}}', encoding="utf-8")
    assert project_status_module._project_title(tmp_path) == "备用标题"

    report = {
        "project": "",
        "project_root": "",
        "phase": "draft_in_progress",
        "latest_accepted_chapter": 1,
        "target_chapter": 2,
        "next_action": "review",
        "blocking": ["缺少审查"],
        "warnings": ["索引较旧"],
    }
    text = project_status_module.format_project_status(report)
    assert "project: (未命名项目)" in text
    assert "blocking:\n- 缺少审查" in text
    assert "warnings:\n- 索引较旧" in text


def test_project_status_main_prints_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["project-status", "--format", "json"])
    monkeypatch.setattr(
        project_status_module,
        "build_project_status",
        lambda *_args, **_kwargs: {"schema_version": "test", "phase": "no_project"},
    )
    with pytest.raises(SystemExit) as raised:
        project_status_module.main()
    assert raised.value.code == 0
    assert json.loads(capsys.readouterr().out)["phase"] == "no_project"


def test_run_logger_handles_lists_scalars_and_append(tmp_path: Path) -> None:
    redacted = run_logger_module.redact_payload(
        [{"token": "secret"}, "password=hunter2", 7, None]
    )
    assert redacted == [{"token": "<redacted>"}, "password=<redacted>", 7, None]

    run_logger_module.write_run_log(tmp_path, event="first")
    result = run_logger_module.write_run_log(tmp_path, event="second", append=True)
    lines = Path(result["path"]).read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["event"] for line in lines] == ["first", "second"]


@pytest.mark.parametrize(
    ("payload", "message"),
    [("{broken", "不是合法 JSON"), ("[]", "必须是 JSON object")],
)
def test_run_logger_main_rejects_invalid_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: str,
    message: str,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["run-logger", "--project-root", str(tmp_path), "--event", "test", "--payload-json", payload],
    )
    with pytest.raises(SystemExit, match=message):
        run_logger_module.main()


@pytest.mark.parametrize("output_format", ["json", "text"])
def test_run_logger_main_writes_supported_formats(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    output_format: str,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run-logger",
            "--project-root",
            str(tmp_path),
            "--event",
            "test",
            "--payload-json",
            '{"token": "hidden"}',
            "--format",
            output_format,
        ],
    )
    run_logger_module.main()
    output = capsys.readouterr().out
    assert "hidden" not in output
    assert str(run_logger_module.log_path(tmp_path)) in output


def test_doctor_helpers_cover_corrupt_and_optional_inputs(tmp_path: Path) -> None:
    missing, error = doctor_module._read_json(tmp_path / "missing.json")
    assert missing == {}
    assert error == "missing"

    broken = tmp_path / "broken.json"
    broken.write_text("{broken", encoding="utf-8")
    assert doctor_module._read_json(broken)[1].startswith("invalid json:")
    broken.write_text("[]", encoding="utf-8")
    assert doctor_module._read_json(broken) == ({}, "json root is not object")

    checks = doctor_module._preflight_checks(
        {
            "checks": [
                "ignored",
                {"name": "project_root", "ok": True, "path": "/book"},
                {"name": "state", "ok": False, "error": "missing"},
            ]
        }
    )
    assert [item["status"] for item in checks] == ["ok", "error"]
    assert checks[1]["severity"] == "blocker"


def test_doctor_sqlite_checks_cover_valid_missing_table_and_corruption(tmp_path: Path) -> None:
    valid = tmp_path / "valid.db"
    with sqlite3.connect(valid) as conn:
        conn.execute("CREATE TABLE chapters (id INTEGER)")
        conn.execute("INSERT INTO chapters VALUES (1)")
    assert doctor_module._sqlite_table_count(valid, "chapters") == (True, 1, "")
    assert doctor_module._sqlite_table_count(valid, "vectors") == (False, 0, "table_missing")

    corrupt = tmp_path / "corrupt.db"
    corrupt.write_text("not sqlite", encoding="utf-8")
    ok, count, error = doctor_module._sqlite_table_count(corrupt, "chapters")
    assert ok is False
    assert count == 0
    assert error


def test_doctor_dashboard_and_text_report_include_repairs(tmp_path: Path) -> None:
    dashboard = tmp_path / "dashboard"
    (dashboard / "frontend" / "dist").mkdir(parents=True)
    (dashboard / "frontend" / "package.json").write_text("{}", encoding="utf-8")
    checks = doctor_module._dashboard_checks(tmp_path)
    assert {item["id"]: item["status"] for item in checks} == {
        "dashboard.root": "ok",
        "dashboard.frontend.dist": "ok",
        "dashboard.frontend.package_json": "ok",
        "dashboard.requirements": "warning",
    }

    report = {
        "ok": False,
        "project_root": "/book",
        "phase": "init_scaffolded",
        "blocking_count": 1,
        "warning_count": 1,
        "checks": [
            {"status": "ok", "id": "ignored"},
            {
                "status": "error",
                "id": "file.required",
                "message": "missing",
                "path": "/book/file",
                "actual": "missing",
                "impact": "blocked",
                "repair": "restore it",
            },
        ],
        "recommended_actions": ["restore it"],
    }
    text = doctor_module.format_doctor_report(report)
    assert "ERROR webnovel-doctor" in text
    assert "path: /book/file" in text
    assert "repair: restore it" in text
    assert json.loads(doctor_module.format_doctor_report(report, "json"))["ok"] is False


def test_doctor_report_survives_runtime_health_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_init_ready(tmp_path)
    monkeypatch.setattr(doctor_module, "_python_checks", lambda: [])
    monkeypatch.setattr(
        doctor_module,
        "build_story_runtime_health",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("health unavailable")),
    )
    report = doctor_module.build_doctor_report(
        tmp_path,
        deep=True,
        preflight_report={"checks": [{"name": "root", "ok": True}]},
    )
    assert any(item["id"] == "story_runtime.health" for item in report["checks"])
    assert report["mode"] == "deep"


def test_doctor_main_returns_status_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["doctor", "--format", "json"])
    monkeypatch.setattr(
        doctor_module,
        "build_doctor_report",
        lambda *_args, **_kwargs: {"ok": True, "phase": "init_ready"},
    )
    with pytest.raises(SystemExit) as raised:
        doctor_module.main()
    assert raised.value.code == 0
    assert json.loads(capsys.readouterr().out)["phase"] == "init_ready"


def test_write_gate_text_format_and_unknown_stage(tmp_path: Path) -> None:
    error = issue(
        "missing_contract",
        message="合同缺失",
        path="/book/contract.json",
        impact="不能开写",
        repair="重新生成合同",
    )
    warning = issue("stale_index", message="索引较旧", severity="warning")
    report = gate_report(
        stage="prewrite",
        project_root=tmp_path,
        chapter=3,
        phase="chapter_contract_ready",
        errors=[error],
        warnings=[warning],
    )
    text = format_gate_report(report, "text")
    assert "ERROR write-gate prewrite" in text
    assert "path: /book/contract.json" in text
    assert "impact: 不能开写" in text
    assert "repair: 重新生成合同" in text
    assert "WARNING stale_index" in text
    assert json.loads(format_gate_report(report, "json"))["ok"] is False
    with pytest.raises(ValueError, match="unknown write-gate stage"):
        run_write_gate(tmp_path, chapter=3, stage="invalid")
