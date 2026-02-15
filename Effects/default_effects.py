from __future__ import annotations

import math
from dataclasses import dataclass

from .effects_engine import ColorRGB, Effect, EffectContext, FrameContribution, InputState


def _clamp01(value: float) -> float:
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


def _hsv_to_rgb(h: float, s: float, v: float) -> ColorRGB:
    h = h % 1.0
    s = _clamp01(s)
    v = _clamp01(v)
    i = int(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return int(r * 255.0), int(g * 255.0), int(b * 255.0)


def _scale_color(color: ColorRGB, brightness: float) -> ColorRGB:
    b = _clamp01(brightness)
    return int(color[0] * b), int(color[1] * b), int(color[2] * b)


def _role_color(button_name: str) -> ColorRGB:
    n = (button_name or "").upper()
    if n.endswith("_A"):
        return 255, 128, 0
    if n.endswith("_B"):
        return 255, 210, 0
    if n.endswith("_C"):
        return 255, 0, 170
    if n.endswith("_X"):
        return 0, 230, 120
    if n.endswith("_Y"):
        return 0, 220, 255
    if n.endswith("_Z"):
        return 40, 130, 255
    if "START" in n:
        return 255, 255, 255
    if "REWIND" in n:
        return 180, 0, 255
    if "MENU" in n:
        return 0, 170, 255
    return 200, 200, 200


class IdleSoftGlowEffect(Effect):
    def __init__(
        self,
        color: ColorRGB = (190, 215, 255),
        min_brightness: float = 0.10,
        max_brightness: float = 0.18,
        period_ms: float = 4500.0,
        suspend_in_attract: bool = True,
        attract_timeout_ms: float = 45000.0,
    ) -> None:
        self.color = color
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.period_ms = max(250.0, float(period_ms))
        self.suspend_in_attract = suspend_in_attract
        self.attract_timeout_ms = max(0.0, float(attract_timeout_ms))
        self.ctx: EffectContext | None = None
        self._colors: list[ColorRGB] = []

    def initialize(self, context: EffectContext) -> None:
        self.ctx = context
        self._colors = [(0, 0, 0)] * context.button_count

    def update(self, delta_time_ms: float, input_state: InputState) -> FrameContribution | None:
        if not self.ctx:
            return None
        if self.suspend_in_attract and input_state.idle_ms >= self.attract_timeout_ms:
            for i in range(len(self._colors)):
                self._colors[i] = (0, 0, 0)
            return FrameContribution(colors=self._colors, layer="base")

        wave = 0.5 + 0.5 * math.sin((input_state.now_ms / self.period_ms) * math.tau)
        b = self.min_brightness + (self.max_brightness - self.min_brightness) * wave
        c = _scale_color(self.color, b)
        for i in range(len(self._colors)):
            self._colors[i] = c
        return FrameContribution(colors=self._colors, layer="base")

    def priority(self) -> int:
        return 10


class TeasePulseCycleEffect(Effect):
    def __init__(
        self,
        min_hz: float = 0.5,
        max_hz: float = 2.0,
        sweep_period_ms: float = 16000.0,
        min_brightness: float = 0.08,
        max_brightness: float = 1.0,
        hue_speed_hz: float = 0.03,
        saturation: float = 1.0,
    ) -> None:
        self.min_hz = max(0.05, float(min_hz))
        self.max_hz = max(self.min_hz, float(max_hz))
        self.sweep_period_ms = max(1000.0, float(sweep_period_ms))
        self.min_brightness = _clamp01(min_brightness)
        self.max_brightness = _clamp01(max_brightness)
        self.hue_speed_hz = max(0.001, float(hue_speed_hz))
        self.saturation = _clamp01(saturation)
        self.ctx: EffectContext | None = None
        self._colors: list[ColorRGB] = []
        self._pulse_offsets: list[float] = []
        self._hue_offsets: list[float] = []
        self._pulse_phase: float = 0.0

    def initialize(self, context: EffectContext) -> None:
        self.ctx = context
        self._colors = [(0, 0, 0)] * context.button_count
        self._pulse_phase = 0.0
        self._pulse_offsets = [((i * 0.61803398875) % 1.0) * math.tau for i in range(context.button_count)]
        self._hue_offsets = [((i * 0.38196601125) % 1.0) for i in range(context.button_count)]

    def update(self, delta_time_ms: float, input_state: InputState) -> FrameContribution | None:
        if not self.ctx:
            return None
        if not self._colors:
            return FrameContribution(colors=self._colors, layer="base")

        now_ms = float(input_state.now_ms)
        sweep = (now_ms % self.sweep_period_ms) / self.sweep_period_ms
        # Triangle wave sweep: slow -> fast -> slow.
        sweep_mix = 1.0 - abs((2.0 * sweep) - 1.0)
        current_hz = self.min_hz + ((self.max_hz - self.min_hz) * sweep_mix)
        self._pulse_phase += math.tau * current_hz * (max(0.0, float(delta_time_ms)) / 1000.0)

        hue_base = (now_ms / 1000.0) * self.hue_speed_hz
        span = max(0.0, self.max_brightness - self.min_brightness)
        for i in range(len(self._colors)):
            pulse = 0.5 + (0.5 * math.sin(self._pulse_phase + self._pulse_offsets[i]))
            bright = self.min_brightness + (span * pulse)
            hue = (hue_base + self._hue_offsets[i]) % 1.0
            base_color = _hsv_to_rgb(hue, self.saturation, 1.0)
            self._colors[i] = _scale_color(base_color, bright)
        return FrameContribution(colors=self._colors, layer="base")

    def priority(self) -> int:
        return 15


class TeaseIndependentColorCycleEffect(Effect):
    def __init__(
        self,
        min_hz: float = 0.5,
        max_hz: float = 2.0,
        sweep_period_ms: float = 16000.0,
        min_brightness: float = 0.08,
        max_brightness: float = 1.0,
        hue_speed_hz: float = 0.03,
        saturation: float = 1.0,
    ) -> None:
        self.min_hz = max(0.05, float(min_hz))
        self.max_hz = max(self.min_hz, float(max_hz))
        self.sweep_period_ms = max(1000.0, float(sweep_period_ms))
        self.min_brightness = _clamp01(min_brightness)
        self.max_brightness = _clamp01(max_brightness)
        self.hue_speed_hz = max(0.001, float(hue_speed_hz))
        self.saturation = _clamp01(saturation)
        self.ctx: EffectContext | None = None
        self._colors: list[ColorRGB] = []
        self._pulse_offsets: list[float] = []
        self._sweep_offsets_ms: list[float] = []
        self._hue_offsets: list[float] = []
        self._hue_speeds: list[float] = []

    def initialize(self, context: EffectContext) -> None:
        self.ctx = context
        self._colors = [(0, 0, 0)] * context.button_count
        # Deterministic per-button offsets/speeds so every button feels independently timed.
        self._pulse_offsets = [((i * 0.61803398875) % 1.0) * math.tau for i in range(context.button_count)]
        self._sweep_offsets_ms = [((i * 0.41421356237) % 1.0) * self.sweep_period_ms for i in range(context.button_count)]
        self._hue_offsets = [((i * 0.38196601125) % 1.0) for i in range(context.button_count)]
        self._hue_speeds = [
            self.hue_speed_hz * (0.75 + (((i * 0.27182818284) % 1.0) * 0.90))
            for i in range(context.button_count)
        ]

    def update(self, delta_time_ms: float, input_state: InputState) -> FrameContribution | None:
        if not self.ctx:
            return None
        if not self._colors:
            return FrameContribution(colors=self._colors, layer="base")

        now_ms = float(input_state.now_ms)
        now_s = now_ms / 1000.0
        span = max(0.0, self.max_brightness - self.min_brightness)
        hz_span = max(0.0, self.max_hz - self.min_hz)

        for i in range(len(self._colors)):
            sweep = ((now_ms + self._sweep_offsets_ms[i]) % self.sweep_period_ms) / self.sweep_period_ms
            # Triangle wave sweep: slow -> fast -> slow, independently phased per button.
            sweep_mix = 1.0 - abs((2.0 * sweep) - 1.0)
            current_hz = self.min_hz + (hz_span * sweep_mix)
            pulse_phase = (now_s * current_hz * math.tau) + self._pulse_offsets[i]
            pulse = 0.5 + (0.5 * math.sin(pulse_phase))
            bright = self.min_brightness + (span * pulse)
            hue = ((now_s * self._hue_speeds[i]) + self._hue_offsets[i]) % 1.0
            base_color = _hsv_to_rgb(hue, self.saturation, 1.0)
            self._colors[i] = _scale_color(base_color, bright)
        return FrameContribution(colors=self._colors, layer="base")

    def priority(self) -> int:
        return 15


class PlayerIdentitySplitEffect(Effect):
    def __init__(self, enabled: bool = False, strength: float = 0.25) -> None:
        self.enabled = enabled
        self.strength = _clamp01(strength)
        self.ctx: EffectContext | None = None
        self._colors: list[ColorRGB] = []
        self._p1_set: set[str] = set()
        self._p2_set: set[str] = set()
        self.p1_tint: ColorRGB = (255, 120, 40)
        self.p2_tint: ColorRGB = (0, 180, 255)

    def initialize(self, context: EffectContext) -> None:
        self.ctx = context
        self._colors = [(0, 0, 0)] * context.button_count
        groups = context.config.get("layout_groups", {}) if isinstance(context.config, dict) else {}
        p1 = list(groups.get("P1_Action", [])) + list(groups.get("P1_Shoulder", [])) + list(groups.get("P1_System", []))
        p2 = list(groups.get("P2_Action", [])) + list(groups.get("P2_Shoulder", [])) + list(groups.get("P2_System", []))
        self._p1_set = set(p1)
        self._p2_set = set(p2)

    def update(self, delta_time_ms: float, input_state: InputState) -> FrameContribution | None:
        if not self.ctx or not self.enabled:
            return None
        for i, name in enumerate(self.ctx.button_names):
            if name in self._p1_set:
                self._colors[i] = _scale_color(self.p1_tint, self.strength)
            elif name in self._p2_set:
                self._colors[i] = _scale_color(self.p2_tint, self.strength)
            else:
                self._colors[i] = (0, 0, 0)
        return FrameContribution(colors=self._colors, layer="base")

    def priority(self) -> int:
        return 20


class AttractChaseRainbowEffect(Effect):
    def __init__(self, idle_timeout_ms: float = 45000.0, step_ms: float = 700.0, hue_speed_hz: float = 0.06) -> None:
        self.idle_timeout_ms = max(0.0, idle_timeout_ms)
        self.step_ms = max(50.0, step_ms)
        self.hue_speed_hz = max(0.001, hue_speed_hz)
        self.ctx: EffectContext | None = None
        self._colors: list[ColorRGB] = []
        self._groups: list[list[int]] = []

    def initialize(self, context: EffectContext) -> None:
        self.ctx = context
        self._colors = [(0, 0, 0)] * context.button_count
        groups_cfg = context.config.get("layout_groups", {}) if isinstance(context.config, dict) else {}
        ordered = [
            "P1_Action",
            "P1_Shoulder",
            "P1_System",
            "P2_Action",
            "P2_Shoulder",
            "P2_System",
        ]
        self._groups = []
        for key in ordered:
            names = [n for n in groups_cfg.get(key, []) if n in context.button_index]
            if names:
                self._groups.append([context.button_index[n] for n in names])
        if not self._groups:
            self._groups = [[i] for i in range(context.button_count)]

    def is_active(self) -> bool:
        return True

    def update(self, delta_time_ms: float, input_state: InputState) -> FrameContribution | None:
        if not self.ctx:
            return None
        if input_state.pressed_buttons:
            for i in range(len(self._colors)):
                self._colors[i] = (0, 0, 0)
            return FrameContribution(colors=self._colors, layer="attract")
        if input_state.idle_ms < self.idle_timeout_ms:
            for i in range(len(self._colors)):
                self._colors[i] = (0, 0, 0)
            return FrameContribution(colors=self._colors, layer="attract")

        gcount = max(1, len(self._groups))
        active = (input_state.now_ms / self.step_ms) % float(gcount)
        hue_base = (input_state.now_ms / 1000.0) * self.hue_speed_hz
        for i in range(len(self._colors)):
            self._colors[i] = (0, 0, 0)
        for gi, group in enumerate(self._groups):
            dist = abs(float(gi) - active)
            dist = min(dist, float(gcount) - dist)
            if dist >= 1.0:
                intensity = 0.0
            else:
                intensity = 1.0 - dist
            if intensity <= 0.0:
                continue
            hue = (hue_base + float(gi) / float(gcount)) % 1.0
            rgb = _scale_color(_hsv_to_rgb(hue, 1.0, 1.0), intensity)
            for idx in group:
                self._colors[idx] = rgb
        return FrameContribution(colors=self._colors, layer="attract")

    def priority(self) -> int:
        return 40


@dataclass(slots=True)
class _Ripple:
    origin: str
    start_ms: float
    color: ColorRGB


class PressRippleEffect(Effect):
    def __init__(
        self,
        peak_brightness: float = 1.0,
        ring1_delay_ms: float = 60.0,
        ring2_delay_ms: float = 120.0,
        decay_ms: float = 210.0,
        color_mode: str = "role",
        player_color_p1: ColorRGB = (255, 160, 30),
        player_color_p2: ColorRGB = (0, 180, 255),
    ) -> None:
        self.peak_brightness = _clamp01(peak_brightness)
        self.ring1_delay_ms = ring1_delay_ms
        self.ring2_delay_ms = ring2_delay_ms
        self.decay_ms = max(30.0, decay_ms)
        self.color_mode = color_mode
        self.player_color_p1 = player_color_p1
        self.player_color_p2 = player_color_p2
        self.ctx: EffectContext | None = None
        self._colors: list[ColorRGB] = []
        self._adj: dict[str, list[str]] = {}
        self._rings: dict[str, tuple[list[str], list[str], list[str]]] = {}
        self._ripples: list[_Ripple] = []
        self._max_active = 64
        self._p1_set: set[str] = set()

    def initialize(self, context: EffectContext) -> None:
        self.ctx = context
        self._colors = [(0, 0, 0)] * context.button_count
        self._adj = context.config.get("layout_adjacency", {}) if isinstance(context.config, dict) else {}
        groups = context.config.get("layout_groups", {}) if isinstance(context.config, dict) else {}
        self._p1_set = set(groups.get("P1_Action", []) + groups.get("P1_Shoulder", []) + groups.get("P1_System", []))
        self._rings = {}
        for name in context.button_names:
            ring0 = [name]
            ring1 = list(self._adj.get(name, []))
            ring2: set[str] = set()
            for n1 in ring1:
                for n2 in self._adj.get(n1, []):
                    if n2 != name and n2 not in ring1:
                        ring2.add(n2)
            self._rings[name] = (ring0, ring1, sorted(ring2))

    def update(self, delta_time_ms: float, input_state: InputState) -> FrameContribution | None:
        if not self.ctx:
            return None
        now = input_state.now_ms
        for btn in input_state.pressed_buttons:
            if btn not in self.ctx.button_index:
                continue
            self._ripples.append(_Ripple(origin=btn, start_ms=now, color=self._pick_color(btn)))
        if len(self._ripples) > self._max_active:
            self._ripples = self._ripples[-self._max_active :]

        for i in range(len(self._colors)):
            self._colors[i] = (0, 0, 0)
        next_ripples: list[_Ripple] = []
        intensities = [0.0] * len(self._colors)
        for ripple in self._ripples:
            age = now - ripple.start_ms
            if age > self.ring2_delay_ms + self.decay_ms:
                continue
            next_ripples.append(ripple)
            self._apply_ring(intensities, ripple, age, 0.0, 0)
            self._apply_ring(intensities, ripple, age, self.ring1_delay_ms, 1)
            self._apply_ring(intensities, ripple, age, self.ring2_delay_ms, 2)
        self._ripples = next_ripples

        for i, strength in enumerate(intensities):
            if strength <= 0.0:
                continue
            color = self._colors[i]
            if color == (0, 0, 0):
                continue
            self._colors[i] = _scale_color(color, strength * self.peak_brightness)
        return FrameContribution(colors=self._colors, layer="overlay")

    def _apply_ring(self, intensities: list[float], ripple: _Ripple, age: float, delay_ms: float, ring_idx: int) -> None:
        local = age - delay_ms
        if local < 0.0 or local > self.decay_ms:
            return
        envelope = 1.0 - (local / self.decay_ms)
        ring = self._rings.get(ripple.origin, ([], [], []))[ring_idx]
        for name in ring:
            idx = self.ctx.button_index.get(name) if self.ctx else None
            if idx is None:
                continue
            if envelope > intensities[idx]:
                intensities[idx] = envelope
                self._colors[idx] = ripple.color

    def _pick_color(self, button_name: str) -> ColorRGB:
        if self.color_mode == "player":
            return self.player_color_p1 if button_name in self._p1_set else self.player_color_p2
        return _role_color(button_name)

    def priority(self) -> int:
        return 80


class ComboExplosionEffect(Effect):
    def __init__(
        self,
        combo_press_count: int = 5,
        combo_window_ms: float = 1000.0,
        hold_ms: float = 110.0,
        fade_ms: float = 420.0,
        cooldown_ms: float = 1200.0,
        color: ColorRGB = (255, 255, 255),
    ) -> None:
        self.combo_press_count = max(2, int(combo_press_count))
        self.combo_window_ms = max(50.0, combo_window_ms)
        self.hold_ms = max(10.0, hold_ms)
        self.fade_ms = max(50.0, fade_ms)
        self.cooldown_ms = max(0.0, cooldown_ms)
        self.color = color
        self.ctx: EffectContext | None = None
        self._colors: list[ColorRGB] = []
        self._press_times: list[float] = []
        self._burst_start_ms: float = -1.0
        self._last_trigger_ms: float = -1.0

    def initialize(self, context: EffectContext) -> None:
        self.ctx = context
        self._colors = [(0, 0, 0)] * context.button_count

    def update(self, delta_time_ms: float, input_state: InputState) -> FrameContribution | None:
        if not self.ctx:
            return None
        now = input_state.now_ms
        press_count = len(input_state.pressed_buttons)
        if press_count > 0:
            for _ in range(press_count):
                self._press_times.append(now)
        if self._press_times:
            cutoff = now - self.combo_window_ms
            self._press_times = [t for t in self._press_times if t >= cutoff]
        if len(self._press_times) >= self.combo_press_count and (now - self._last_trigger_ms) >= self.cooldown_ms:
            self._burst_start_ms = now
            self._last_trigger_ms = now
            self._press_times.clear()

        amp = 0.0
        if self._burst_start_ms >= 0.0:
            age = now - self._burst_start_ms
            if age <= self.hold_ms:
                amp = 1.0
            else:
                fade_age = age - self.hold_ms
                if fade_age <= self.fade_ms:
                    amp = 1.0 - (fade_age / self.fade_ms)
                else:
                    self._burst_start_ms = -1.0
                    amp = 0.0
        if amp <= 0.0:
            for i in range(len(self._colors)):
                self._colors[i] = (0, 0, 0)
            return FrameContribution(colors=self._colors, layer="overlay")
        c = _scale_color(self.color, amp)
        for i in range(len(self._colors)):
            self._colors[i] = c
        return FrameContribution(colors=self._colors, layer="overlay")

    def priority(self) -> int:
        return 90


class InsertCoinBlinkEffect(Effect):
    def __init__(
        self,
        blink_button: str = "P1_START",
        cadence_ms: float = 600.0,
        color: ColorRGB = (255, 220, 40),
        brightness: float = 1.0,
        only_no_credits: bool = True,
    ) -> None:
        self.blink_button = blink_button
        self.cadence_ms = max(120.0, cadence_ms)
        self.color = color
        self.brightness = _clamp01(brightness)
        self.only_no_credits = only_no_credits
        self.ctx: EffectContext | None = None
        self._colors: list[ColorRGB] = []
        self._idx: int | None = None

    def initialize(self, context: EffectContext) -> None:
        self.ctx = context
        self._colors = [(0, 0, 0)] * context.button_count
        self._idx = context.button_index.get(self.blink_button)
        if self._idx is None and "P1_START" in context.button_index:
            self._idx = context.button_index["P1_START"]

    def update(self, delta_time_ms: float, input_state: InputState) -> FrameContribution | None:
        if not self.ctx or self._idx is None:
            return None
        menu_gate = bool(input_state.in_menu or not input_state.in_game)
        credit_gate = (not input_state.has_credits) if self.only_no_credits else True
        if not (menu_gate and credit_gate):
            for i in range(len(self._colors)):
                self._colors[i] = (0, 0, 0)
            return FrameContribution(colors=self._colors, layer="overlay")
        for i in range(len(self._colors)):
            self._colors[i] = (0, 0, 0)
        on = int(input_state.now_ms // self.cadence_ms) % 2 == 0
        self._colors[self._idx] = _scale_color(self.color, self.brightness if on else 0.0)
        return FrameContribution(colors=self._colors, layer="overlay")

    def priority(self) -> int:
        return 70
