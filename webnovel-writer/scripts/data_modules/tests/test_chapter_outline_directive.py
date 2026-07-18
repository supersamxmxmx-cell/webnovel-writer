#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from chapter_outline_loader import (
    load_chapter_execution_directive,
    load_volume_outline_plan,
)


def test_load_chapter_execution_directive_from_volume_outline(tmp_path):
    outline_dir = tmp_path / "大纲"
    outline_dir.mkdir()
    (tmp_path / ".webnovel").mkdir()
    (tmp_path / ".webnovel" / "state.json").write_text(
        json.dumps({"progress": {"volumes_planned": [{"volume": 1, "chapters_range": "1-50"}]}}),
        encoding="utf-8",
    )
    (outline_dir / "第1卷-详细大纲.md").write_text(
        "\n".join(
            [
                "### 第一章：债从天降",
                "- 目标：搞清楚借据条款的荒谬",
                "- 阻力：杂役不能随意离开宗门",
                "- 代价：暴露自己懂账",
                "- 时间锚点：D-Day 清晨",
                "- 章内跨度：一炷香",
                "- 倒计时状态：三日内还债",
                "- Strand：债务调查",
                "- 反派层级：小反派",
                "- 关键实体：陆鸣、借据、利息",
                "- CBN：醒来发现债务",
                "- CPNs：检查借据；发现复利陷阱",
                "- CEN：决定去井边打听",
                "- 必须覆盖节点：借据金额；复利算法",
                "- 本章禁区：不得离开宗门；不得提前摊牌",
                "- 章末未闭合问题：谁改了借据？",
                "- 钩子类型：信息钩",
                "- 钩子强度：中",
                "",
                "### 第二章：井边口风",
                "- 目标：打听债主来历",
            ]
        ),
        encoding="utf-8",
    )

    directive = load_chapter_execution_directive(tmp_path, 1)

    assert directive["goal"] == "搞清楚借据条款的荒谬"
    assert directive["time_anchor"] == "D-Day 清晨"
    assert directive["chapter_span"] == "一炷香"
    assert directive["countdown"] == "三日内还债"
    assert directive["cpns"] == ["检查借据", "发现复利陷阱"]
    assert "不得离开宗门" in directive["forbidden_zones"]
    assert "借据" in directive["key_entities"]
    assert directive["chapter_end_open_question"] == "谁改了借据？"


def test_load_volume_outline_plan_returns_real_stages_and_all_planned_chapters(tmp_path):
    outline_dir = tmp_path / "大纲"
    outline_dir.mkdir()
    (outline_dir / "第1卷-详细大纲.md").write_text(
        "\n".join(
            [
                "# 第 1 卷：风起青云 - 详细大纲",
                "",
                "## 阶段一·入局（第1-2章，第1天）",
                "",
                "### 第1章：借据从天而降",
                "- 目标：搞清借据条款",
                "- 时间锚点：第1天清晨 ｜ 章内跨度：一炷香 ｜ 与上章：— ｜ 倒计时：三日内还债",
                "- 关键实体：陆鸣、借据",
                "- 本章变化：陆鸣确认欠债",
                "- 钩子：借据上的签名会发光",
                "",
                "### 第2章：井边口风",
                "- 目标：打听债主来历",
                "- 阻力：同门不肯开口",
                "",
                "## 阶段二·破局（第3-3章，第2天）",
                "",
                "### 第3章：当面对账",
                "**目标**：找债主对质",
                "**核心冲突**：还债 vs 揭穿假账",
            ]
        ),
        encoding="utf-8",
    )

    plan = load_volume_outline_plan(tmp_path, 1)

    assert plan["label"] == "第 1 卷 · 风起青云"
    assert plan["start_chapter"] == 1
    assert plan["end_chapter"] == 3
    assert [stage["label"] for stage in plan["stages"]] == ["阶段一 · 入局", "阶段二 · 破局"]
    assert [chapter["chapter"] for chapter in plan["chapters"]] == [1, 2, 3]
    assert plan["chapters"][0]["planned_entities"] == ["陆鸣", "借据"]
    assert plan["chapters"][0]["outline"]["chapter_span"] == "一炷香"
    assert plan["chapters"][0]["outline"]["countdown"] == "三日内还债"
    assert plan["chapters"][2]["outline"]["core_conflict"] == "还债 vs 揭穿假账"
