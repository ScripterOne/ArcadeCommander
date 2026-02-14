from __future__ import annotations

import sys
import time

from .default_effects import AttractChaseRainbowEffect, ComboExplosionEffect, PressRippleEffect
from .effects_engine import EffectContext, EffectEngine, InputState, Mixer
from .layout import build_button_layout


def _sample_buttons() -> list[str]:
    return [
        "P1_A",
        "P1_B",
        "P1_X",
        "P1_Y",
        "P1_C",
        "P1_Z",
        "REWIND",
        "P1_START",
        "MENU",
        "P2_A",
        "P2_B",
        "P2_X",
        "P2_Y",
        "P2_C",
        "P2_Z",
        "P2_START",
        "TRACKBALL",
    ]


def _build_engine(effects):
    names = _sample_buttons()
    layout = build_button_layout(names)
    ctx = EffectContext(
        button_names=names,
        button_index={name: i for i, name in enumerate(names)},
        seed=1337,
        config={
            "layout_groups": layout.groups,
            "layout_adjacency": layout.adjacency,
        },
    )
    engine = EffectEngine(ctx, Mixer(len(names)), effects=effects)
    return engine, ctx, layout


def _non_black(rgb):
    return rgb[0] > 0 or rgb[1] > 0 or rgb[2] > 0


def test_attract_enter_exit():
    engine, ctx, _ = _build_engine([AttractChaseRainbowEffect(idle_timeout_ms=500.0, step_ms=250.0)])
    t0 = time.monotonic() * 1000.0
    f_idle_short = engine.tick(InputState(idle_ms=200.0), now_ms=t0, attract_active=False)
    assert all(not _non_black(c) for c in f_idle_short), "Attract should be off before timeout."

    f_idle_long = engine.tick(InputState(idle_ms=900.0), now_ms=t0 + 600.0, attract_active=True)
    assert any(_non_black(c) for c in f_idle_long), "Attract should render after timeout."

    f_press_exit = engine.tick(
        InputState(idle_ms=900.0, pressed_buttons={"P1_A"}),
        now_ms=t0 + 650.0,
        attract_active=False,
    )
    assert all(not _non_black(c) for c in f_press_exit), "Any press should clear attract output."


def test_press_ripple_adjacency():
    ripple = PressRippleEffect(ring1_delay_ms=60.0, ring2_delay_ms=120.0, decay_ms=240.0)
    engine, ctx, layout = _build_engine([ripple])
    origin = "P1_A"
    ring1 = list(layout.adjacency.get(origin, []))
    assert ring1, "Adjacency map should provide ring1 nodes for ripple."
    t0 = time.monotonic() * 1000.0

    f0 = engine.tick(InputState(pressed_buttons={origin}), now_ms=t0, attract_active=False)
    assert _non_black(f0[ctx.button_index[origin]]), "Origin should flash immediately on press."

    f1 = engine.tick(InputState(), now_ms=t0 + 70.0, attract_active=False)
    assert any(_non_black(f1[ctx.button_index[n]]) for n in ring1 if n in ctx.button_index), "Ring1 should light after delay."


def test_combo_trigger_window():
    combo = ComboExplosionEffect(combo_press_count=5, combo_window_ms=1000.0, hold_ms=100.0, fade_ms=300.0, cooldown_ms=1000.0)
    engine, _, _ = _build_engine([combo])
    t0 = time.monotonic() * 1000.0
    presses = ["P1_A", "P1_B", "P1_X", "P1_Y", "P1_C"]
    frame = None
    for i, key in enumerate(presses):
        frame = engine.tick(InputState(pressed_buttons={key}), now_ms=t0 + (i * 150.0), attract_active=False)
    assert frame is not None
    assert any(_non_black(c) for c in frame), "Combo explosion should trigger on threshold within window."


def main():
    tests = [
        ("attract_enter_exit", test_attract_enter_exit),
        ("press_ripple_adjacency", test_press_ripple_adjacency),
        ("combo_trigger_window", test_combo_trigger_window),
    ]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"[PASS] {name}")
        except Exception as exc:
            failed.append((name, str(exc)))
            print(f"[FAIL] {name}: {exc}")
    if failed:
        print(f"\n{len(failed)} test(s) failed.")
        return 1
    print("\nAll effect dry-run tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
