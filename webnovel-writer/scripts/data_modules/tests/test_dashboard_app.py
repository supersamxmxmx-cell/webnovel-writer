#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import importlib
import json
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from data_modules.config import DataModulesConfig
from data_modules.index_manager import (
    ChapterMeta,
    ChapterReadingPowerMeta,
    IndexManager,
    ReviewMetrics,
)


def _create_dashboard_client(monkeypatch, project_root: Path) -> TestClient:
    plugin_root = Path(__file__).resolve().parents[3]
    scripts_dir = plugin_root / "scripts"

    clean_path = []
    scripts_resolved = scripts_dir.resolve()
    for entry in sys.path:
        try:
            if Path(entry).resolve() == scripts_resolved:
                continue
        except Exception:
            pass
        clean_path.append(entry)

    if str(plugin_root) not in clean_path:
        clean_path.insert(0, str(plugin_root))

    monkeypatch.setattr(sys, "path", clean_path)
    for name in list(sys.modules):
        if name == "dashboard.app" or name == "data_modules" or name.startswith("data_modules."):
            sys.modules.pop(name, None)

    module = importlib.import_module("dashboard.app")
    app = module.create_app(project_root)
    return TestClient(app)


def _write_state(project_root: Path) -> None:
    state = {
        "project_info": {
            "title": "像素写手测试书",
            "genre": "玄幻",
            "target_words": 1000000,
            "target_chapters": 300,
        },
        "progress": {
            "current_chapter": 3,
            "current_volume": 2,
            "total_words": 9300,
            "volumes_planned": [
                {"volume": 1, "chapters_range": "1-2"},
                {"volume": 2, "chapters_range": "3-10"},
            ],
        },
        "protagonist_state": {
            "name": "林长青",
            "power": {"realm": "筑基"},
            "location": {"current": "青元宗"},
        },
        "strand_tracker": {
            "current_dominant": "constellation",
            "history": [
                {"chapter": 1, "strand": "quest"},
                {"chapter": 2, "strand": "fire"},
                {"chapter": 3, "strand": "constellation"},
            ],
        },
        "plot_threads": {
            "foreshadowing": [
                {
                    "content": "青元秘境钥匙碎片",
                    "status": "未回收",
                    "tier": "核心",
                    "planted_chapter": 1,
                    "target_chapter": 2,
                },
                {
                    "content": "凤灵儿真实身份",
                    "status": "未回收",
                    "tier": "支线",
                    "planted_chapter": 2,
                    "target_chapter": 6,
                },
                {
                    "content": "第一卷残图",
                    "status": "已回收",
                    "tier": "装饰",
                    "planted_chapter": 1,
                    "target_chapter": 3,
                    "resolved_chapter": 3,
                },
            ]
        },
        "chapter_meta": {
            "0001": {"summary": "第一章概要"},
            "0002": {"summary": "第二章概要"},
            "0003": {"summary": "第三章概要"},
        },
    }
    webnovel_dir = project_root / ".webnovel"
    webnovel_dir.mkdir(parents=True, exist_ok=True)
    (webnovel_dir / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_project_data(project_root: Path) -> None:
    cfg = DataModulesConfig.from_project_root(project_root)
    cfg.ensure_dirs()
    _write_state(project_root)

    index = IndexManager(cfg)
    index.add_chapter(
        ChapterMeta(
            chapter=1,
            title="初入山门",
            location="青元宗",
            word_count=3000,
            characters=["lintian"],
            summary="第一章概要",
        )
    )
    index.add_chapter(
        ChapterMeta(
            chapter=2,
            title="秘境异动",
            location="青元秘境",
            word_count=3100,
            characters=["lintian", "fenglinger"],
            summary="第二章概要",
        )
    )
    index.add_chapter(
        ChapterMeta(
            chapter=3,
            title="夜探黑市",
            location="黑市",
            word_count=3200,
            characters=["lintian", "heishifanzi"],
            summary="第三章概要",
        )
    )

    index.save_chapter_reading_power(
        ChapterReadingPowerMeta(
            chapter=1,
            hook_type="悬念钩",
            hook_strength="weak",
            coolpoint_patterns=["身份伏笔"],
        )
    )
    index.save_chapter_reading_power(
        ChapterReadingPowerMeta(
            chapter=2,
            hook_type="反转钩",
            hook_strength="medium",
            coolpoint_patterns=["秘境反转"],
        )
    )
    index.save_chapter_reading_power(
        ChapterReadingPowerMeta(
            chapter=3,
            hook_type="追杀钩",
            hook_strength="strong",
            coolpoint_patterns=["黑市追杀"],
        )
    )

    index.save_review_metrics(
        ReviewMetrics(
            start_chapter=1,
            end_chapter=1,
            overall_score=71,
            severity_counts={"high": 1},
        )
    )
    index.save_review_metrics(
        ReviewMetrics(
            start_chapter=2,
            end_chapter=2,
            overall_score=83,
            severity_counts={"medium": 1},
        )
    )
    index.save_review_metrics(
        ReviewMetrics(
            start_chapter=3,
            end_chapter=3,
            overall_score=88,
            severity_counts={"low": 1},
        )
    )

    story_root = project_root / ".story-system"
    (story_root / "chapters").mkdir(parents=True, exist_ok=True)
    (story_root / "volumes").mkdir(parents=True, exist_ok=True)
    (story_root / "reviews").mkdir(parents=True, exist_ok=True)
    (story_root / "commits").mkdir(parents=True, exist_ok=True)
    (story_root / "MASTER_SETTING.json").write_text(
        json.dumps(
            {
                "meta": {"schema_version": "story-system/v1", "contract_type": "MASTER_SETTING"},
                "route": {"primary_genre": "玄幻升级流"},
                "master_constraints": {"core_tone": "先压后爆"},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (story_root / "volumes" / "volume_001.json").write_text(
        json.dumps({"meta": {"contract_type": "VOLUME_BRIEF", "volume": 1}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (story_root / "volumes" / "volume_002.json").write_text(
        json.dumps({"meta": {"contract_type": "VOLUME_BRIEF", "volume": 2}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (story_root / "chapters" / "chapter_003.json").write_text(
        json.dumps(
            {"meta": {"contract_type": "CHAPTER_BRIEF", "chapter": 3}, "override_allowed": {"chapter_focus": "夜探黑市"}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (story_root / "reviews" / "chapter_003.review.json").write_text(
        json.dumps(
            {"meta": {"contract_type": "REVIEW_CONTRACT", "chapter": 3}, "must_check": ["黑市冲突"]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (story_root / "commits" / "chapter_002.commit.json").write_text(
        json.dumps(
            {
                "meta": {"schema_version": "story-system/v1", "chapter": 2, "status": "accepted"},
                "provenance": {"write_fact_role": "chapter_commit"},
                "projection_status": {
                    "state": "done",
                    "index": "done",
                    "summary": "done",
                    "memory": "done",
                    "vector": "done",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (story_root / "commits" / "chapter_003.commit.json").write_text(
        json.dumps(
            {
                "meta": {"schema_version": "story-system/v1", "chapter": 3, "status": "rejected"},
                "provenance": {"write_fact_role": "chapter_commit"},
                "projection_status": {
                    "state": "skipped",
                    "index": "skipped",
                    "summary": "skipped",
                    "memory": "skipped",
                    "vector": "skipped",
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    vector_db = cfg.vector_db
    with sqlite3.connect(vector_db) as conn:
        conn.execute(
            """
            CREATE TABLE vectors (
                chunk_id TEXT PRIMARY KEY,
                chapter INTEGER,
                scene_index INTEGER,
                content TEXT,
                embedding BLOB,
                parent_chunk_id TEXT,
                chunk_type TEXT,
                source_file TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO vectors (chunk_id, chapter, scene_index, content, embedding, parent_chunk_id, chunk_type, source_file)
            VALUES ('ch0003_s1', 3, 1, '黑市线索', X'00', NULL, 'scene', '正文/第0003章.md')
            """
        )
        conn.commit()

    (project_root / ".env").write_text(
        "\n".join(
            [
                "EMBED_BASE_URL=https://embed.example.com/v1",
                "EMBED_MODEL=test-embed",
                "EMBED_API_KEY=embed-key",
                "RERANK_BASE_URL=https://rerank.example.com/v1",
                "RERANK_MODEL=test-rerank",
                "RERANK_API_KEY=rerank-key",
            ]
        ),
        encoding="utf-8",
    )


def test_dashboard_app_imports_without_scripts_path(monkeypatch, tmp_path):
    plugin_root = Path(__file__).resolve().parents[3]
    scripts_dir = plugin_root / "scripts"

    project_root = tmp_path / "book"
    (project_root / ".webnovel").mkdir(parents=True, exist_ok=True)
    (project_root / ".webnovel" / "state.json").write_text("{}", encoding="utf-8")

    clean_path = []
    scripts_resolved = scripts_dir.resolve()
    for entry in sys.path:
        try:
            if Path(entry).resolve() == scripts_resolved:
                continue
        except Exception:
            pass
        clean_path.append(entry)

    if str(plugin_root) not in clean_path:
        clean_path.insert(0, str(plugin_root))

    monkeypatch.setattr(sys, "path", clean_path)
    for name in list(sys.modules):
        if name == "dashboard.app" or name == "data_modules" or name.startswith("data_modules."):
            sys.modules.pop(name, None)

    module = importlib.import_module("dashboard.app")
    app = module.create_app(project_root)
    client = TestClient(app)

    response = client.get("/api/story-runtime/health")
    assert response.status_code == 200

    milestones_response = client.get("/api/milestones")
    assert milestones_response.status_code == 200
    assert milestones_response.json()["volumes"] == []


def test_dashboard_chapter_trend_endpoint_returns_recent_window(monkeypatch, tmp_path):
    project_root = tmp_path / "book"
    _build_project_data(project_root)
    client = _create_dashboard_client(monkeypatch, project_root)

    response = client.get("/api/stats/chapter-trend", params={"limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["latest_chapter"] == 3
    assert [item["chapter"] for item in payload["items"]] == [2, 3]
    assert payload["items"][0]["review_score"] == 83
    assert payload["items"][0]["hook_strength"] == "medium"
    assert payload["items"][0]["hook_strength_value"] == 3
    assert payload["items"][0]["strand"] == "fire"
    assert payload["items"][0]["volume"] == 1
    assert payload["items"][1]["volume"] == 2


def test_dashboard_milestones_groups_volumes_stages_chapters_and_entities(monkeypatch, tmp_path):
    project_root = tmp_path / "book"
    _build_project_data(project_root)
    db_path = project_root / ".webnovel" / "index.db"
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO entities (
                id, type, canonical_name, tier, desc, current_json,
                first_appearance, last_appearance, is_protagonist, is_archived
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "lintian",
                    "角色",
                    "林长青",
                    "核心",
                    "主角",
                    json.dumps({"境界": "筑基"}, ensure_ascii=False),
                    1,
                    3,
                    1,
                    0,
                ),
                (
                    "secret-key",
                    "物品",
                    "秘境钥匙",
                    "重要",
                    "开启秘境",
                    "{}",
                    2,
                    3,
                    0,
                    0,
                ),
                (
                    "star-fire",
                    "招式",
                    "星火诀",
                    "重要",
                    "攻击能力",
                    json.dumps({"层级": 1}, ensure_ascii=False),
                    3,
                    3,
                    0,
                    0,
                ),
                ("archived", "角色", "已归档角色", "装饰", "", "{}", 1, 1, 0, 1),
            ],
        )
        conn.execute(
            """
            INSERT INTO state_changes (entity_id, field, old_value, new_value, reason, chapter)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("lintian", "境界", "练气", "筑基", "突破成功", 3),
        )
        conn.commit()

    client = _create_dashboard_client(monkeypatch, project_root)
    response = client.get("/api/milestones")

    assert response.status_code == 200
    payload = response.json()
    assert payload["current_chapter"] == 3
    assert payload["current_volume"] == 2
    assert payload["recorded_chapters"] == 3
    assert payload["planned_chapters"] == 10
    assert payload["entity_total"] == 3
    assert payload["entity_counts"] == {"角色": 1, "物品": 1, "招式": 1}

    first_volume, second_volume = payload["volumes"]
    assert first_volume["range_id"] == "1-1-2"
    assert first_volume["recorded_chapters"] == 2
    assert first_volume["completion_percent"] == 100.0
    assert [stage["label"] for stage in first_volume["stages"]] == ["开篇", "收束"]
    assert [stage["chapters"][0]["chapter"] for stage in first_volume["stages"]] == [1, 2]
    assert first_volume["stages"][1]["chapters"][0]["status"] == "accepted"
    assert first_volume["stages"][1]["chapters"][0]["new_entities"][0]["type"] == "物品"

    assert second_volume["is_current"] is True
    assert [stage["label"] for stage in second_volume["stages"]] == ["开篇", "发展", "转折", "收束"]
    current_chapter = second_volume["stages"][0]["chapters"][0]
    assert current_chapter["chapter"] == 3
    assert current_chapter["status"] == "rejected"
    assert {entity["type"] for entity in current_chapter["entities"]} == {"角色", "招式"}
    assert current_chapter["changes"][0]["entity_name"] == "林长青"
    assert current_chapter["changes"][0]["reason"] == "突破成功"


def test_dashboard_milestones_merges_detailed_outline_with_recorded_chapters(monkeypatch, tmp_path):
    project_root = tmp_path / "book"
    _build_project_data(project_root)
    outline_dir = project_root / "大纲"
    outline_dir.mkdir()
    (outline_dir / "第2卷-详细大纲.md").write_text(
        "\n".join(
            [
                "# 第 2 卷：秘境暗潮 - 详细大纲",
                "",
                "## 阶段一·追索（第3-5章，当日夜间）",
                "",
                "### 第3章：夜探黑市",
                "- 目标：确认秘境钥匙来路",
                "- 关键实体：林长青、秘境钥匙",
                "",
                "### 第4章：暗门之后",
                "- 目标：跟踪黑市贩子",
                "- 阻力：暗门内有伏兵",
                "",
                "### 第5章：钥匙易主",
                "- 目标：抢在敌人之前拿到钥匙",
                "- 钩子：钥匙上出现了主角的名字",
            ]
        ),
        encoding="utf-8",
    )

    client = _create_dashboard_client(monkeypatch, project_root)
    response = client.get("/api/milestones")

    assert response.status_code == 200
    payload = response.json()
    assert payload["outlined_chapters"] == 3
    second_volume = payload["volumes"][1]
    assert second_volume["label"] == "第 2 卷 · 秘境暗潮"
    assert second_volume["outlined_chapters"] == 3
    assert second_volume["outline_source"] == "大纲/第2卷-详细大纲.md"
    assert [stage["label"] for stage in second_volume["stages"]] == ["阶段一 · 追索"]
    chapters = second_volume["stages"][0]["chapters"]
    assert [item["chapter"] for item in chapters] == [3, 4, 5]
    assert chapters[0]["is_recorded"] is True
    assert chapters[0]["status"] == "rejected"
    assert chapters[0]["outline"]["goal"] == "确认秘境钥匙来路"
    assert chapters[1]["is_recorded"] is False
    assert chapters[1]["status"] == "planned"
    assert chapters[1]["title"] == "暗门之后"


def test_dashboard_commits_and_contract_summary_endpoints(monkeypatch, tmp_path):
    project_root = tmp_path / "book"
    _build_project_data(project_root)
    from data_modules.projection_log import append_projection_run

    commit_path = project_root / ".story-system" / "commits" / "chapter_002.commit.json"
    logged_payload = json.loads(commit_path.read_text(encoding="utf-8"))
    logged_payload["projection_status"] = dict(logged_payload["projection_status"])
    logged_payload["projection_status"]["vector"] = "failed:timeout"
    append_projection_run(
        project_root,
        logged_payload,
        {"vector": {"status": "failed:timeout", "error": "timeout"}},
        commit_path=commit_path,
    )
    client = _create_dashboard_client(monkeypatch, project_root)

    commits_response = client.get("/api/commits", params={"limit": 2})
    assert commits_response.status_code == 200
    commits_payload = commits_response.json()
    assert [item["chapter"] for item in commits_payload["items"]] == [3, 2]
    assert commits_payload["items"][0]["status"] == "rejected"
    assert commits_payload["items"][0]["projection_source"] == "commit"
    assert commits_payload["items"][1]["projection_source"] == "projection_log"
    assert commits_payload["items"][1]["projection_status"]["vector"] == "failed:timeout"
    assert commits_payload["items"][1]["projection_run"]["run_id"]

    contracts_response = client.get("/api/contracts/summary")
    assert contracts_response.status_code == 200
    contracts_payload = contracts_response.json()
    assert contracts_payload["chapter"] == 3
    assert contracts_payload["current_volume"] == 2
    assert contracts_payload["master"]["primary_genre"] == "玄幻升级流"
    assert contracts_payload["master"]["core_tone"] == "先压后爆"
    assert contracts_payload["counts"]["volumes"] == 2
    assert contracts_payload["counts"]["chapters"] == 1
    assert contracts_payload["counts"]["reviews"] == 1
    assert contracts_payload["counts"]["commits"] == 2
    assert contracts_payload["current_contracts"]["chapter"] is True
    assert contracts_payload["current_contracts"]["review"] is True
    assert contracts_payload["current_contracts"]["commit"] is True


def test_dashboard_env_status_endpoints_report_local_rag_state(monkeypatch, tmp_path):
    project_root = tmp_path / "book"
    _build_project_data(project_root)
    client = _create_dashboard_client(monkeypatch, project_root)

    status_response = client.get("/api/env-status")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["embed"]["api_key_present"] is True
    assert status_payload["rerank"]["api_key_present"] is True
    assert status_payload["vector_db"]["exists"] is True
    assert status_payload["vector_db"]["record_count"] == 1
    assert status_payload["rag_mode"] == "full"

    probe_response = client.get("/api/env-status/probe")
    assert probe_response.status_code == 200
    probe_payload = probe_response.json()
    assert probe_payload["ok"] is True
    check_names = [item["name"] for item in probe_payload["checks"]]
    assert "embed_api_key" in check_names
    assert "rerank_api_key" in check_names
    assert "vector_db" in check_names
