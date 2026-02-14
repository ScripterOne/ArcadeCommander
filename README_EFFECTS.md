# ArcadeCommander Effects Engine

## Architecture

- Core engine: `Effects/effects_engine.py`
- Layout/groups/adjacency: `Effects/layout.py`
- Editable layout config: `Effects/layout_config.json`
- Default effect modules: `Effects/default_effects.py`
- Preset definitions: `Effects/presets.py`
- Runtime wiring: `ArcadeCommanderV2.py`

Effects are layered and mixed deterministically:

- Base layer blend: `max`
- Overlay layer blend: `screen`
- Attract layer blend: `screen`

Runtime flow:

1. `ArcadeCommanderV2` builds `EffectContext` with button map + layout config.
2. A preset loads effect instances into `EffectEngine`.
3. Existing pulse loop calls `_tick_effects_engine()` when legacy pulse output is idle.
4. Final frame is sent to hardware through existing `cab.set(...)` / `cab.show()` path.

## Defaults And First Run

Default settings are persisted in `ac_settings.json`:

- `effects_enabled: true`
- `effects_seed: 1337`
- `effects_preset_id: "showroom_default"`

This is initialized in `ArcadeCommanderV2.py` during app startup.

## Presets

Defined in `Effects/presets.py`:

- `showroom_default`
- `classic_static`
- `neon_minimal`
- `party_mode`

UI selector is in **Controller Config -> App Settings**.
Selecting a preset applies immediately and persists to settings.

## Add A New Effect

1. Create a class in `Effects/default_effects.py` (or a new module) implementing `Effect`:
   - `initialize(context)`
   - `update(delta_time_ms, input_state) -> FrameContribution | None`
2. Use `context.config["layout_groups"]` and `context.config["layout_adjacency"]` if needed.
3. Return a `FrameContribution` with layer set to `base`, `overlay`, or `attract`.
4. Register your effect in one or more preset builders in `Effects/presets.py`.

## Adjacency Configuration

Edit `Effects/layout_config.json`:

- `groups`: named button sets (`P1_Action`, `P1_Shoulder`, `P1_System`, etc.)
- `adjacency`: node neighbors used by ripple-style effects

All adjacency editing is centralized there so effect code does not need changes.

## Debug / Preview

Run dry-run tests without hardware:

```powershell
python -m Effects.effects_dry_run
```

This validates:

- Attract mode enter/exit behavior
- Ripple adjacency ring propagation
- Combo threshold triggering
