#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

try:
    from chapter_paths import volume_num_for_chapter
except ImportError:  # pragma: no cover
    from scripts.chapter_paths import volume_num_for_chapter


_CHAPTER_RANGE_RE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")
_VOLUME_OUTLINE_FILENAME_RE = re.compile(
    r"^第\s*0*(?P<volume>\d+)\s*卷\s*(?:[-—_ ]\s*)?详细大纲\.md$",
    re.IGNORECASE,
)
_VOLUME_HEADING_RE = re.compile(
    r"^#{1,6}\s*第\s*(?P<volume>\d+)\s*卷\s*[\uff1a:]?\s*(?P<title>.*?)\s*$",
    re.MULTILINE,
)
_STAGE_HEADING_RE = re.compile(
    r"^#{1,6}\s*阶段\s*(?P<index>[0-9零〇一二两三四五六七八九十]+)"
    r"\s*[·・\.\-—]?\s*(?P<label>[^\uff08(\n]*?)\s*"
    r"[（(]\s*第\s*(?P<start>\d+)\s*[-—–~至]\s*(?P<end>\d+)\s*章"
    r"(?:\s*[,\uff0c\uff5c|]\s*(?P<period>[^\uff09)\n]+))?\s*[）)]\s*$",
    re.MULTILINE,
)


def _parse_chapters_range(value: object) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    match = _CHAPTER_RANGE_RE.match(value)
    if not match:
        return None
    try:
        start = int(match.group(1))
        end = int(match.group(2))
    except ValueError:
        return None
    if start <= 0 or end <= 0 or start > end:
        return None
    return start, end


def volume_num_for_chapter_from_state(project_root: Path, chapter_num: int) -> int | None:
    state_path = project_root / ".webnovel" / "state.json"
    if not state_path.exists():
        return None

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(state, dict):
        return None

    progress = state.get("progress")
    if not isinstance(progress, dict):
        return None

    volumes_planned = progress.get("volumes_planned")
    if not isinstance(volumes_planned, list):
        return None

    best: tuple[int, int] | None = None
    for item in volumes_planned:
        if not isinstance(item, dict):
            continue
        volume = item.get("volume")
        if not isinstance(volume, int) or volume <= 0:
            continue
        parsed = _parse_chapters_range(item.get("chapters_range"))
        if not parsed:
            continue
        start, end = parsed
        if start <= chapter_num <= end:
            candidate = (start, volume)
            if best is None or candidate[0] > best[0] or (candidate[0] == best[0] and candidate[1] < best[1]):
                best = candidate

    return best[1] if best else None


def _find_split_outline_file(outline_dir: Path, chapter_num: int) -> Path | None:
    patterns = [
        f"第{chapter_num}章*.md",
        f"第{chapter_num:02d}章*.md",
        f"第{chapter_num:03d}章*.md",
        f"第{chapter_num:04d}章*.md",
    ]
    for pattern in patterns:
        matches = sorted(outline_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def _find_volume_outline_file_by_volume(project_root: Path, volume_num: int) -> Path | None:
    outline_dir = project_root / "大纲"
    candidates = [
        outline_dir / f"第{volume_num}卷-详细大纲.md",
        outline_dir / f"第{volume_num}卷 - 详细大纲.md",
        outline_dir / f"第{volume_num}卷 详细大纲.md",
    ]
    return next((path for path in candidates if path.exists()), None)


def _find_volume_outline_file(project_root: Path, chapter_num: int) -> Path | None:
    volume_num = volume_num_for_chapter_from_state(project_root, chapter_num) or volume_num_for_chapter(chapter_num)
    return _find_volume_outline_file_by_volume(project_root, volume_num)


def _extract_outline_section(content: str, chapter_num: int) -> str | None:
    patterns = [
        rf"###\s*第\s*{chapter_num}\s*章[：:]\s*(.+?)(?=###\s*第\s*\d+\s*章|##\s|$)",
        rf"###\s*第{chapter_num}章[：:]\s*(.+?)(?=###\s*第\d+章|##\s|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(0).strip()
    return None


def _parse_chinese_chapter_num(value: str) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if text in _CHINESE_NUMERAL_DIGITS:
        return _CHINESE_NUMERAL_DIGITS[text]
    if text == "十":
        return 10
    if "十" in text:
        left, _, right = text.partition("十")
        tens = _CHINESE_NUMERAL_DIGITS.get(left, 1 if not left else 0)
        ones = _CHINESE_NUMERAL_DIGITS.get(right, 0) if right else 0
        parsed = tens * 10 + ones
        return parsed or None
    parsed = 0
    for char in text:
        digit = _CHINESE_NUMERAL_DIGITS.get(char)
        if digit is None:
            return None
        parsed = parsed * 10 + digit
    return parsed or None


def _extract_directive_section(content: str, chapter_num: int) -> str | None:
    matches = list(_CHAPTER_HEADING_RE.finditer(content))
    for index, match in enumerate(matches):
        parsed = _parse_chinese_chapter_num(match.group(2))
        if parsed != chapter_num:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        return content[match.start():end].strip()
    return _extract_outline_section(content, chapter_num)


def load_chapter_outline(project_root: Path, chapter_num: int, max_chars: int | None = 1500) -> str:
    outline_dir = project_root / "大纲"

    split_outline = _find_split_outline_file(outline_dir, chapter_num)
    if split_outline is not None:
        return split_outline.read_text(encoding="utf-8")

    volume_outline = _find_volume_outline_file(project_root, chapter_num)
    if volume_outline is None:
        return f"⚠️ 大纲文件不存在：第 {chapter_num} 章"

    outline = _extract_outline_section(volume_outline.read_text(encoding="utf-8"), chapter_num)
    if outline is None:
        return f"⚠️ 未找到第 {chapter_num} 章的大纲"

    if max_chars and len(outline) > max_chars:
        return outline[:max_chars] + "\n...(已截断)"
    return outline

_PLOT_SECTION_FIELD_MAP = {
    "cbn": "cbn",
    "cpns": "cpns",
    "cen": "cen",
    "必须覆盖节点": "mandatory_nodes",
    "本章禁区": "prohibitions",
}

_CHAPTER_HEADING_RE = re.compile(
    r"^(#{1,6})\s*第\s*([0-9零〇一二两三四五六七八九十]+)\s*章\b.*$",
    re.MULTILINE,
)

_CHINESE_NUMERAL_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

_DIRECTIVE_FIELD_MAP = {
    "目标": "goal",
    "本章目标": "goal",
    "章目标": "goal",
    "阻力": "obstacles",
    "障碍": "obstacles",
    "代价": "cost",
    "时间锚点": "time_anchor",
    "时间": "time_anchor",
    "章内跨度": "chapter_span",
    "章节跨度": "chapter_span",
    "与上章": "previous_chapter_link",
    "倒计时状态": "countdown",
    "倒计时": "countdown",
    "cbn": "cbn",
    "cpns": "cpns",
    "cen": "cen",
    "必须覆盖节点": "must_cover_nodes",
    "本章禁区": "forbidden_zones",
    "章末未闭合问题": "chapter_end_open_question",
    "章末问题": "chapter_end_open_question",
    "钩子类型": "hook_type",
    "钩子强度": "hook_strength",
    "关键实体": "key_entities",
    "涉及实体": "key_entities",
    "strand": "strand",
    "反派层级": "antagonist_tier",
    "核心冲突": "core_conflict",
    "爽点": "payoff",
    "视角/主角": "viewpoint",
    "本章变化": "planned_changes",
    "未闭合问题": "chapter_end_open_question",
    "钩子": "hook",
}

_DIRECTIVE_LIST_FIELDS = {"cpns", "must_cover_nodes", "forbidden_zones", "key_entities"}


def _clean_plot_line(line: str) -> str:
    text = str(line or "").strip()
    text = re.sub(r"^[\-\*•]+\s*", "", text)
    text = re.sub(r"^\d+[\.、]\s*", "", text)
    text = text.replace("**", "").replace("__", "")
    return text.strip()


def _append_plot_value(target: Dict[str, Any], field: str, value: str) -> None:
    value = _clean_plot_line(value)
    if not value:
        return

    if field in {"cpns", "mandatory_nodes", "prohibitions"}:
        target.setdefault(field, [])
        candidates = [value]
        if field in {"mandatory_nodes", "prohibitions"}:
            split_values = [part.strip() for part in re.split(r"[、,，；;|]+", value) if part.strip()]
            if split_values:
                candidates = split_values
        for item in candidates:
            if item not in target[field]:
                target[field].append(item)
        return

    if field not in target:
        target[field] = value


def _split_directive_values(value: str) -> list[str]:
    text = _clean_plot_line(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"[、,，；;|]+", text) if part.strip()]


def _append_directive_value(target: Dict[str, Any], field: str, value: str) -> None:
    value = _clean_plot_line(value)
    if not value:
        return
    if field in _DIRECTIVE_LIST_FIELDS:
        target.setdefault(field, [])
        for item in _split_directive_values(value) or [value]:
            if item not in target[field]:
                target[field].append(item)
        return
    if field not in target:
        target[field] = value


def parse_chapter_plot_structure(outline_text: str) -> Dict[str, Any]:
    text = str(outline_text or "")
    if not text or text.startswith("⚠️"):
        return {}

    structure: Dict[str, Any] = {}
    current_field = ""

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            current_field = ""
            continue
        if re.match(r"^#{1,6}\s*第\s*\d+\s*章", stripped):
            current_field = ""
            continue

        cleaned = _clean_plot_line(stripped)
        matched_field = ""
        matched_value = ""
        for label, field in _PLOT_SECTION_FIELD_MAP.items():
            match = re.match(rf"^{re.escape(label)}\s*[：:]\s*(.*)$", cleaned, re.IGNORECASE)
            if match:
                matched_field = field
                matched_value = match.group(1).strip()
                break

        if matched_field:
            current_field = matched_field
            _append_plot_value(structure, matched_field, matched_value)
            continue

        if current_field:
            _append_plot_value(structure, current_field, cleaned)

    cpns = structure.get("cpns") or []
    mandatory_nodes = structure.get("mandatory_nodes") or []
    prohibitions = structure.get("prohibitions") or []
    if not any([structure.get("cbn"), cpns, structure.get("cen"), mandatory_nodes, prohibitions]):
        return {}

    return {
        "cbn": str(structure.get("cbn") or "").strip(),
        "cpns": cpns,
        "cen": str(structure.get("cen") or "").strip(),
        "mandatory_nodes": mandatory_nodes,
        "prohibitions": prohibitions,
        "source": "chapter_outline",
    }


def load_chapter_plot_structure(project_root: Path, chapter_num: int) -> Dict[str, Any]:
    outline = load_chapter_outline(project_root, chapter_num, max_chars=None)
    return parse_chapter_plot_structure(outline)


def parse_chapter_execution_directive(outline_text: str) -> Dict[str, Any]:
    text = str(outline_text or "")
    if not text or text.startswith("⚠️"):
        return {}

    directive: Dict[str, Any] = {}
    current_field = ""
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            current_field = ""
            continue
        if _CHAPTER_HEADING_RE.match(stripped):
            current_field = ""
            continue

        for segment in stripped.split("｜"):
            cleaned = _clean_plot_line(segment)
            if not cleaned:
                continue
            matched_field = ""
            matched_value = ""
            for label, field in _DIRECTIVE_FIELD_MAP.items():
                match = re.match(rf"^{re.escape(label)}\s*[：:]\s*(.*)$", cleaned, re.IGNORECASE)
                if match:
                    matched_field = field
                    matched_value = match.group(1).strip()
                    break

            if matched_field:
                current_field = matched_field
                _append_directive_value(directive, matched_field, matched_value)
                continue
            if current_field:
                _append_directive_value(directive, current_field, cleaned)

    plot_structure = parse_chapter_plot_structure(text)
    for source_key, target_key in (
        ("cbn", "cbn"),
        ("cpns", "cpns"),
        ("cen", "cen"),
        ("mandatory_nodes", "must_cover_nodes"),
        ("prohibitions", "forbidden_zones"),
    ):
        if plot_structure.get(source_key) and not directive.get(target_key):
            directive[target_key] = plot_structure[source_key]

    if directive:
        directive["source"] = "chapter_outline"
    return directive


def load_chapter_execution_directive(project_root: Path, chapter_num: int) -> Dict[str, Any]:
    outline_dir = project_root / "大纲"
    split_outline = _find_split_outline_file(outline_dir, chapter_num)
    if split_outline is not None:
        return parse_chapter_execution_directive(split_outline.read_text(encoding="utf-8"))

    volume_outline = _find_volume_outline_file(project_root, chapter_num)
    if volume_outline is None:
        return {}
    section = _extract_directive_section(volume_outline.read_text(encoding="utf-8"), chapter_num)
    if section is None:
        return {}
    return parse_chapter_execution_directive(section)


def _volume_title_from_content(content: str, volume_num: int) -> str:
    for match in _VOLUME_HEADING_RE.finditer(content):
        try:
            matched_volume = int(match.group("volume"))
        except (TypeError, ValueError):
            continue
        if matched_volume != volume_num:
            continue
        title = str(match.group("title") or "").strip()
        title = re.sub(r"\s*[-—]\s*详细大纲\s*$", "", title).strip()
        if title == "详细大纲":
            return ""
        return title
    return ""


def _chapter_title_from_heading(heading: str) -> str:
    match = re.match(
        r"^#{1,6}\s*第\s*[0-9零〇一二两三四五六七八九十]+\s*章\s*[\uff1a:]?\s*(.*?)\s*$",
        str(heading or ""),
    )
    return str(match.group(1) or "").strip() if match else ""


def load_volume_outline_plan(project_root: Path, volume_num: int) -> Dict[str, Any]:
    """读取一份详细卷纲，返回看板可直接使用的阶段与章节计划。"""
    if volume_num <= 0:
        return {}
    outline_path = _find_volume_outline_file_by_volume(project_root, volume_num)
    if outline_path is None:
        return {}
    try:
        content = outline_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    stage_matches = list(_STAGE_HEADING_RE.finditer(content))
    stages: list[Dict[str, Any]] = []
    for order, match in enumerate(stage_matches, start=1):
        try:
            start = int(match.group("start"))
            end = int(match.group("end"))
        except (TypeError, ValueError):
            continue
        if start <= 0 or end < start:
            continue
        index_label = str(match.group("index") or order).strip()
        name = str(match.group("label") or "").strip()
        stages.append(
            {
                "id": f"outline-stage-{order}",
                "label": f"阶段{index_label}" + (f" · {name}" if name else ""),
                "name": name,
                "start_chapter": start,
                "end_chapter": end,
                "period": str(match.group("period") or "").strip(),
                "source": "volume_outline",
            }
        )

    chapter_matches = list(_CHAPTER_HEADING_RE.finditer(content))
    chapters: list[Dict[str, Any]] = []
    for index, match in enumerate(chapter_matches):
        chapter_num = _parse_chinese_chapter_num(match.group(2))
        if not chapter_num or chapter_num <= 0:
            continue
        end = chapter_matches[index + 1].start() if index + 1 < len(chapter_matches) else len(content)
        next_stage = next((item.start() for item in stage_matches if match.end() < item.start() < end), None)
        if next_stage is not None:
            end = next_stage
        section = content[match.start():end].strip()
        directive = parse_chapter_execution_directive(section)
        chapters.append(
            {
                "chapter": chapter_num,
                "title": _chapter_title_from_heading(match.group(0)),
                "status": "planned",
                "is_recorded": False,
                "word_count": 0,
                "location": "",
                "summary": str(directive.get("goal") or "").strip(),
                "entities": [],
                "new_entities": [],
                "changes": [],
                "planned_entities": directive.get("key_entities") or [],
                "outline": directive,
                "outline_source": str(outline_path.relative_to(project_root)),
            }
        )

    chapter_numbers = [item["chapter"] for item in chapters]
    range_candidates = [(item["start_chapter"], item["end_chapter"]) for item in stages]
    if chapter_numbers:
        range_candidates.append((min(chapter_numbers), max(chapter_numbers)))
    start_chapter = min((item[0] for item in range_candidates), default=0)
    end_chapter = max((item[1] for item in range_candidates), default=0)
    title = _volume_title_from_content(content, volume_num)
    return {
        "volume": volume_num,
        "title": title,
        "label": f"第 {volume_num} 卷" + (f" · {title}" if title else ""),
        "start_chapter": start_chapter,
        "end_chapter": end_chapter,
        "stages": stages,
        "chapters": sorted(chapters, key=lambda item: item["chapter"]),
        "source_file": str(outline_path.relative_to(project_root)),
    }


def load_all_volume_outline_plans(project_root: Path) -> list[Dict[str, Any]]:
    """扫描大纲目录中的详细卷纲；一卷最多返回一份计划。"""
    outline_dir = project_root / "大纲"
    if not outline_dir.is_dir():
        return []
    volume_numbers: set[int] = set()
    for path in outline_dir.glob("*.md"):
        match = _VOLUME_OUTLINE_FILENAME_RE.match(path.name)
        if not match:
            continue
        try:
            volume_numbers.add(int(match.group("volume")))
        except (TypeError, ValueError):
            continue
    return [
        plan
        for volume_num in sorted(volume_numbers)
        if (plan := load_volume_outline_plan(project_root, volume_num))
    ]
