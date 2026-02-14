from __future__ import annotations

import json
import os
from dataclasses import dataclass


DEFAULT_LAYOUT_FILE = os.path.join(os.path.dirname(__file__), "layout_config.json")


@dataclass(slots=True)
class ButtonLayout:
    button_names: list[str]
    groups: dict[str, list[str]]
    adjacency: dict[str, list[str]]


def load_layout_config(path: str = DEFAULT_LAYOUT_FILE) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def build_button_layout(button_names: list[str], config_path: str = DEFAULT_LAYOUT_FILE) -> ButtonLayout:
    present = set(button_names)
    cfg = load_layout_config(config_path)
    groups_cfg = cfg.get("groups", {}) if isinstance(cfg, dict) else {}
    adjacency_cfg = cfg.get("adjacency", {}) if isinstance(cfg, dict) else {}

    groups = {
        "P1_Action": _resolve_group(
            groups_cfg.get("P1_Action"),
            present,
            ["P1_A", "P1_B", "P1_X", "P1_Y", "P1_C", "P1_Z"],
            limit=4,
        ),
        "P1_Shoulder": _resolve_group(
            groups_cfg.get("P1_Shoulder"),
            present,
            ["P1_L1", "P1_R1", "P1_L2", "P1_R2", "P1_C", "P1_Z"],
            limit=4,
        ),
        "P1_System": _resolve_group(
            groups_cfg.get("P1_System"),
            present,
            ["P1_START", "MENU", "REWIND"],
            limit=None,
        ),
        "P2_Action": _resolve_group(
            groups_cfg.get("P2_Action"),
            present,
            ["P2_A", "P2_B", "P2_X", "P2_Y", "P2_C", "P2_Z"],
            limit=4,
        ),
        "P2_Shoulder": _resolve_group(
            groups_cfg.get("P2_Shoulder"),
            present,
            ["P2_L1", "P2_R1", "P2_L2", "P2_R2", "P2_C", "P2_Z"],
            limit=4,
        ),
        "P2_System": _resolve_group(
            groups_cfg.get("P2_System"),
            present,
            ["P2_START", "MENU", "REWIND", "TRACKBALL"],
            limit=None,
        ),
    }

    adjacency = _build_default_adjacency(groups)
    _apply_adjacency_config(adjacency, adjacency_cfg, present)
    _ensure_undirected(adjacency)
    for name in button_names:
        adjacency.setdefault(name, [])
    return ButtonLayout(button_names=list(button_names), groups=groups, adjacency=adjacency)


def _resolve_group(config_values, present: set[str], defaults: list[str], limit: int | None) -> list[str]:
    chosen: list[str] = []
    if isinstance(config_values, list):
        for item in config_values:
            if isinstance(item, str) and item in present and item not in chosen:
                chosen.append(item)
    if not chosen:
        for name in defaults:
            if name in present and name not in chosen:
                chosen.append(name)
    if limit is not None:
        return chosen[:limit]
    return chosen


def _build_default_adjacency(groups: dict[str, list[str]]) -> dict[str, list[str]]:
    adjacency: dict[str, set[str]] = {}
    for names in groups.values():
        for name in names:
            adjacency.setdefault(name, set())

    for g in ("P1_Action", "P2_Action"):
        _add_action_connections(adjacency, groups.get(g, []))
    for g in ("P1_Shoulder", "P2_Shoulder"):
        _add_chain_connections(adjacency, groups.get(g, []))
    for g in ("P1_System", "P2_System"):
        _add_chain_connections(adjacency, groups.get(g, []))

    _connect_first(adjacency, groups.get("P1_System", []), groups.get("P1_Action", []))
    _connect_first(adjacency, groups.get("P1_System", []), groups.get("P1_Shoulder", []))
    _connect_first(adjacency, groups.get("P2_System", []), groups.get("P2_Action", []))
    _connect_first(adjacency, groups.get("P2_System", []), groups.get("P2_Shoulder", []))
    _connect_cross_systems(adjacency, groups.get("P1_System", []), groups.get("P2_System", []))

    return {k: sorted(v) for k, v in adjacency.items()}


def _add_action_connections(adjacency: dict[str, set[str]], names: list[str]) -> None:
    if len(names) < 2:
        return
    if len(names) >= 4:
        a, b, x, y = names[0], names[1], names[2], names[3]
        for u, v in ((a, b), (a, x), (b, y), (x, y), (a, y), (b, x)):
            _link(adjacency, u, v)
        for i in range(4, len(names)):
            _link(adjacency, names[i - 1], names[i])
        return
    _add_chain_connections(adjacency, names)


def _add_chain_connections(adjacency: dict[str, set[str]], names: list[str]) -> None:
    for i in range(len(names) - 1):
        _link(adjacency, names[i], names[i + 1])


def _connect_first(adjacency: dict[str, set[str]], left: list[str], right: list[str]) -> None:
    if left and right:
        _link(adjacency, left[0], right[0])


def _connect_cross_systems(adjacency: dict[str, set[str]], left: list[str], right: list[str]) -> None:
    if left and right:
        _link(adjacency, left[0], right[0])


def _link(adjacency: dict[str, set[str]], a: str, b: str) -> None:
    if a == b:
        return
    adjacency.setdefault(a, set()).add(b)
    adjacency.setdefault(b, set()).add(a)


def _apply_adjacency_config(adjacency: dict[str, list[str]], cfg: dict, present: set[str]) -> None:
    if not isinstance(cfg, dict):
        return
    for src, dsts in cfg.items():
        if not isinstance(src, str) or src not in present:
            continue
        merged = set(adjacency.get(src, []))
        if isinstance(dsts, list):
            for dst in dsts:
                if isinstance(dst, str) and dst in present and dst != src:
                    merged.add(dst)
        adjacency[src] = sorted(merged)


def _ensure_undirected(adjacency: dict[str, list[str]]) -> None:
    for src, dsts in list(adjacency.items()):
        for dst in dsts:
            if dst not in adjacency:
                adjacency[dst] = []
            if src not in adjacency[dst]:
                adjacency[dst].append(src)
    for src in adjacency:
        adjacency[src] = sorted(set(adjacency[src]))
