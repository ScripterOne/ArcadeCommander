from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Iterable, Literal, Optional

LayerName = Literal["base", "overlay", "attract"]
BlendMode = Literal["additive", "max", "screen"]
ColorRGB = tuple[int, int, int]


def _clamp_u8(value: float) -> int:
    if value <= 0.0:
        return 0
    if value >= 255.0:
        return 255
    return int(value)


@dataclass(slots=True)
class InputState:
    pressed_buttons: set[str] = field(default_factory=set)
    released_buttons: set[str] = field(default_factory=set)
    held_buttons: set[str] = field(default_factory=set)
    now_ms: float = 0.0
    idle_ms: float = 0.0
    in_game: bool = False
    in_menu: bool = True
    has_credits: bool = False


@dataclass(slots=True)
class FrameContribution:
    """
    Contribution produced by one effect update.

    Notes:
    - colors is expected to be the same length as button_count.
    - brightness is optional; if provided, each color is scaled by brightness[i].
    - layer controls where the contribution is routed in the mixer.
    """

    colors: list[ColorRGB]
    brightness: Optional[list[float]] = None
    layer: LayerName = "base"


@dataclass(slots=True)
class EffectContext:
    button_names: list[str]
    button_index: dict[str, int]
    seed: int = 1337
    clock: Callable[[], float] = time.monotonic
    config: dict = field(default_factory=dict)
    rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    @property
    def button_count(self) -> int:
        return len(self.button_names)


class Effect(ABC):
    """
    Minimal composable effect interface.
    """

    @abstractmethod
    def initialize(self, context: EffectContext) -> None:
        pass

    @abstractmethod
    def update(self, delta_time_ms: float, input_state: InputState) -> Optional[FrameContribution]:
        pass

    def is_active(self) -> bool:
        return True

    def priority(self) -> int:
        return 0


class Mixer:
    """
    Layered deterministic mixer.

    Blending policy:
    - base layer: max (default) or additive
    - overlay layer: screen (default), max, or additive
    - attract layer: screen (default), max, or additive
    """

    def __init__(
        self,
        button_count: int,
        base_blend: BlendMode = "max",
        overlay_blend: BlendMode = "screen",
        attract_blend: BlendMode = "screen",
    ) -> None:
        self.button_count = int(button_count)
        self.base_blend = base_blend
        self.overlay_blend = overlay_blend
        self.attract_blend = attract_blend

        # Pre-allocated layer buffers, reused every tick.
        self._base_r = [0.0] * self.button_count
        self._base_g = [0.0] * self.button_count
        self._base_b = [0.0] * self.button_count
        self._overlay_r = [0.0] * self.button_count
        self._overlay_g = [0.0] * self.button_count
        self._overlay_b = [0.0] * self.button_count
        self._attract_r = [0.0] * self.button_count
        self._attract_g = [0.0] * self.button_count
        self._attract_b = [0.0] * self.button_count
        self._out: list[ColorRGB] = [(0, 0, 0)] * self.button_count

    def clear(self) -> None:
        for i in range(self.button_count):
            self._base_r[i] = 0.0
            self._base_g[i] = 0.0
            self._base_b[i] = 0.0
            self._overlay_r[i] = 0.0
            self._overlay_g[i] = 0.0
            self._overlay_b[i] = 0.0
            self._attract_r[i] = 0.0
            self._attract_g[i] = 0.0
            self._attract_b[i] = 0.0

    def add(self, contribution: FrameContribution) -> None:
        if not contribution:
            return
        if contribution.layer == "base":
            tr, tg, tb, mode = self._base_r, self._base_g, self._base_b, self.base_blend
        elif contribution.layer == "overlay":
            tr, tg, tb, mode = self._overlay_r, self._overlay_g, self._overlay_b, self.overlay_blend
        else:
            tr, tg, tb, mode = self._attract_r, self._attract_g, self._attract_b, self.attract_blend

        colors = contribution.colors
        brightness = contribution.brightness
        n = min(self.button_count, len(colors))
        if brightness is None:
            for i in range(n):
                r, g, b = colors[i]
                self._blend_channel(tr, i, float(r), mode)
                self._blend_channel(tg, i, float(g), mode)
                self._blend_channel(tb, i, float(b), mode)
        else:
            bn = len(brightness)
            for i in range(min(n, bn)):
                br = max(0.0, min(1.0, float(brightness[i])))
                r, g, b = colors[i]
                self._blend_channel(tr, i, float(r) * br, mode)
                self._blend_channel(tg, i, float(g) * br, mode)
                self._blend_channel(tb, i, float(b) * br, mode)

    def compose(self, attract_active: bool = False) -> list[ColorRGB]:
        for i in range(self.button_count):
            r = self._base_r[i]
            g = self._base_g[i]
            b = self._base_b[i]

            # Overlay is always above base.
            r = self._screen(r, self._overlay_r[i])
            g = self._screen(g, self._overlay_g[i])
            b = self._screen(b, self._overlay_b[i])

            # Attract layer only participates when attract mode is active.
            if attract_active:
                r = self._screen(r, self._attract_r[i])
                g = self._screen(g, self._attract_g[i])
                b = self._screen(b, self._attract_b[i])

            self._out[i] = (_clamp_u8(r), _clamp_u8(g), _clamp_u8(b))
        return self._out

    def _blend_channel(self, target: list[float], idx: int, value: float, mode: BlendMode) -> None:
        if mode == "additive":
            target[idx] = min(255.0, target[idx] + value)
        elif mode == "max":
            if value > target[idx]:
                target[idx] = value
        else:  # screen
            target[idx] = self._screen(target[idx], value)

    @staticmethod
    def _screen(a: float, b: float) -> float:
        # Screen blend in 0..255 space.
        if a <= 0.0:
            return min(255.0, b)
        if b <= 0.0:
            return min(255.0, a)
        na = a / 255.0
        nb = b / 255.0
        return 255.0 * (1.0 - (1.0 - na) * (1.0 - nb))


class EffectEngine:
    """
    Deterministic, time-based effect runner.
    """

    def __init__(
        self,
        context: EffectContext,
        mixer: Mixer,
        effects: Optional[Iterable[Effect]] = None,
    ) -> None:
        self.context = context
        self.mixer = mixer
        self.effects: list[Effect] = []
        self._last_tick_ms: Optional[float] = None
        if effects:
            for effect in effects:
                self.add_effect(effect)

    def add_effect(self, effect: Effect) -> None:
        effect.initialize(self.context)
        self.effects.append(effect)
        # Stable deterministic ordering for same priority.
        self.effects.sort(key=lambda e: e.priority())

    def reset_clock(self) -> None:
        self._last_tick_ms = None

    def tick(self, input_state: Optional[InputState] = None, now_ms: Optional[float] = None, attract_active: bool = False) -> list[ColorRGB]:
        if now_ms is None:
            now_ms = self.context.clock() * 1000.0
        if input_state is None:
            input_state = InputState()
        input_state.now_ms = float(now_ms)

        if self._last_tick_ms is None:
            delta_ms = 0.0
        else:
            delta_ms = max(0.0, float(now_ms) - self._last_tick_ms)
        self._last_tick_ms = float(now_ms)

        self.mixer.clear()
        for effect in self.effects:
            if not effect.is_active():
                continue
            contribution = effect.update(delta_ms, input_state)
            if contribution:
                self.mixer.add(contribution)
        return self.mixer.compose(attract_active=attract_active)
