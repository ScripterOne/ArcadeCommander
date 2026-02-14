from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .default_effects import (
    AttractChaseRainbowEffect,
    ComboExplosionEffect,
    IdleSoftGlowEffect,
    InsertCoinBlinkEffect,
    PlayerIdentitySplitEffect,
    PressRippleEffect,
    TeasePulseCycleEffect,
)
from .effects_engine import Effect


@dataclass(slots=True)
class EffectPreset:
    preset_id: str
    name: str
    description: str
    build_effects: Callable[[], list[Effect]]


def showroom_default() -> list[Effect]:
    return [
        IdleSoftGlowEffect(color=(190, 215, 255), min_brightness=0.10, max_brightness=0.18, period_ms=4500.0),
        PlayerIdentitySplitEffect(enabled=True, strength=0.16),
        InsertCoinBlinkEffect(blink_button="P1_START", cadence_ms=600.0, only_no_credits=True),
        PressRippleEffect(
            peak_brightness=1.0,
            ring1_delay_ms=60.0,
            ring2_delay_ms=120.0,
            decay_ms=210.0,
            color_mode="role",
        ),
        ComboExplosionEffect(combo_press_count=5, combo_window_ms=1000.0, hold_ms=100.0, fade_ms=450.0, cooldown_ms=1100.0),
        AttractChaseRainbowEffect(idle_timeout_ms=45000.0, step_ms=700.0, hue_speed_hz=0.06),
    ]


def classic_static() -> list[Effect]:
    return [
        IdleSoftGlowEffect(color=(240, 240, 240), min_brightness=0.14, max_brightness=0.14, period_ms=20000.0),
    ]


def neon_minimal() -> list[Effect]:
    return [
        IdleSoftGlowEffect(color=(170, 220, 255), min_brightness=0.11, max_brightness=0.17, period_ms=5000.0),
        PressRippleEffect(
            peak_brightness=0.95,
            ring1_delay_ms=50.0,
            ring2_delay_ms=95.0,
            decay_ms=180.0,
            color_mode="player",
        ),
    ]


def party_mode() -> list[Effect]:
    return [
        IdleSoftGlowEffect(color=(190, 220, 255), min_brightness=0.10, max_brightness=0.16, period_ms=3600.0),
        PressRippleEffect(
            peak_brightness=1.0,
            ring1_delay_ms=45.0,
            ring2_delay_ms=90.0,
            decay_ms=190.0,
            color_mode="role",
        ),
        ComboExplosionEffect(combo_press_count=4, combo_window_ms=900.0, hold_ms=110.0, fade_ms=420.0, cooldown_ms=900.0),
        AttractChaseRainbowEffect(idle_timeout_ms=30000.0, step_ms=580.0, hue_speed_hz=0.10),
    ]


def tease() -> list[Effect]:
    return [
        TeasePulseCycleEffect(
            min_hz=0.5,
            max_hz=2.0,
            sweep_period_ms=16000.0,
            min_brightness=0.08,
            max_brightness=1.0,
            hue_speed_hz=0.03,
            saturation=1.0,
        ),
    ]


PRESETS: list[EffectPreset] = [
    EffectPreset(
        preset_id="showroom_default",
        name="Showroom Default",
        description="Idle glow, attract chase rainbow, ripple press response, combo flash, and start-button blink.",
        build_effects=showroom_default,
    ),
    EffectPreset(
        preset_id="classic_static",
        name="Classic Static",
        description="Role-color style static baseline without animated overlays.",
        build_effects=classic_static,
    ),
    EffectPreset(
        preset_id="neon_minimal",
        name="Neon Minimal",
        description="Subtle idle glow with responsive press ripple only.",
        build_effects=neon_minimal,
    ),
    EffectPreset(
        preset_id="party_mode",
        name="Party Mode",
        description="Faster attract/ripple/combo behavior, ready for music-reactive expansion.",
        build_effects=party_mode,
    ),
    EffectPreset(
        preset_id="tease",
        name="Tease",
        description="Staggered per-button pulse color cycle with speed sweep between 2.0 and 0.5 pulses per second.",
        build_effects=tease,
    ),
]


def get_preset_map() -> dict[str, EffectPreset]:
    return {preset.preset_id: preset for preset in PRESETS}
