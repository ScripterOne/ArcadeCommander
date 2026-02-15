# Arcade Commander 2.0 User Manual

## 1. What This Release Includes

Arcade Commander 2.0 ships as a 3-component Windows suite:

- `ArcadeCommanderV2.exe`: main operator UI (Commander, Emulator, Game Manager, FX Editor, Controller Config).
- `ACLighter.exe`: local background lighting service and tray app.
- `ACDispatch.exe`: CLI dispatcher for frontend/game-launch event automation.

All three are intended to work together and share the same runtime data structure.

## 2. System Requirements

- Windows 10/11 (64-bit recommended).
- USB-connected LED hardware/controller stack configured for your cabinet.
- Local loopback networking enabled (`127.0.0.1`).
- If running from source instead of `.exe`, Python + project dependencies are required.

## 3. Package Contents (Release)

Expected release build outputs:

- `dist/ArcadeCommanderV2/ArcadeCommanderV2.exe`
- `dist/ACLighter.exe`
- `dist/ACDispatch.exe`

Also included in repository release:

- `README.md`
- `RELEASE_2.0.md`
- `README_EFFECTS.md`
- `docs/USER_MANUAL_V2.md` (this file)

## 4. Startup Order (Recommended)

1. Start `ACLighter.exe`.
2. Start `ArcadeCommanderV2.exe`.
3. Use `ACDispatch.exe` only for automation/testing from scripts or frontend launch hooks.

Why this order: Commander/Dispatch send runtime packets to ACLighter on `127.0.0.1:6006`.

## 5. Runtime Data Layout

V2 stores runtime files under `data/`:

- `data/config/ac_settings.json`
- `data/config/controller_config.json`
- `data/config/last_profile.cfg`
- `data/games/AC_GameData.json`
- `data/library/AC_FXLibrary.json`
- `data/library/AC_AnimationLibrary.json`
- `data/profiles/*.json`
- `data/keymaps/*.json`

Legacy root-level files are auto-migrated to this layout at startup.

## 6. Core Workflow (Operator)

1. Configure deck/controller details in `CONTROLLER CONFIG`.
2. Set base colors/live checks in `ARCADE COMMANDER`.
3. Use `FX EDITOR` to author or adjust effects/animations.
4. Map game/event behavior in `GAME MANAGER`.
5. Validate in `EMULATOR`.
6. Save profile/map data, then verify with `ACDispatch` event simulation if needed.

## 7. Tab Guide

### 7.1 ARCADE COMMANDER Tab

Primary live-control workspace.

Common actions:

- Load a game profile.
- Apply effect/animation selection to active preview/hardware path.
- Per-player and system color assignment.
- Use bottom utility bar for test/maintenance operations.

Bottom utility bar controls include:

- `APPLY`
- `ALL OFF`
- `BTN TEST`
- `SWAP FIGHT`
- `SWAP START`
- `LED TEST`
- `CYCLE`
- `DEMO`
- `PORT`
- `ABOUT`
- `HELP`
- `QUIT`

### 7.2 EMULATOR Tab

Visual validation layer for game cards, effects, and animation behavior.

Use it to:

- Confirm button/color mapping.
- Validate selected effect/animation behavior before hardware verification.
- Check behavior parity with Commander load/apply actions.

### 7.3 GAME MANAGER Tab

Per-game assignment and persistence:

- Create/select game entries.
- Assign control maps.
- Assign FX and event mappings.
- Import/export game data as needed.

Runtime source of truth for game records: `data/games/AC_GameData.json`.

### 7.4 FX EDITOR Tab

Authoring and preview environment for effects and animations.

Use this tab to:

- Build effect definitions and modulation settings.
- Save reusable entries to shared effect/animation libraries.
- Load saved entries for edits.
- Validate preview behavior before assigning to games/events.

Important:

- `ALL OFF` is available on FX Editor controls for immediate blackout/reset.
- Shared library behavior means saved entries should be visible across Commander, Emulator, and FX Editor selectors.

### 7.5 CONTROLLER CONFIG Tab

Hardware profile and system behavior settings.

Includes:

- Controller deck settings (style, players, buttons/sticks/triggers, extras).
- Summary panel.
- App settings (startup/FX defaults).
- `FUTURE ENHANCEMENTS` card (release planning display list).

## 8. Effects, Presets, and Shared Catalog Behavior

V2 uses shared runtime library files:

- Effects: `data/library/AC_FXLibrary.json`
- Animations: `data/library/AC_AnimationLibrary.json`

Effects engine presets currently include:

- `showroom_default`
- `classic_static`
- `neon_minimal`
- `party_mode`
- `tease`

The `tease` preset is a slow pulsing multi-phase cycle and is expected to be available anywhere shared effect loading is used.

## 9. ACLighter Operations

`ACLighter.exe` runs local service logic and tray controls.

Default listener:

- Host: `127.0.0.1`
- Port: `6006`

Tray menu includes:

- `STRESS: Plasma`
- `STRESS: Hyper Strobe`
- `Test: Rainbow`
- `Reset (Off)`
- `Exit`

## 10. ACDispatch Automation

`ACDispatch.exe` can send runtime commands/events to ACLighter.

Usage patterns:

- Idle reset (no args):
  - `ACDispatch.exe`
- Trigger specific animation:
  - `ACDispatch.exe --anim RAINBOW`
- Trigger specific event:
  - `ACDispatch.exe --event GAME_START <rom_name>`
- Game launch profile load:
  - `ACDispatch.exe <rom_name>`

Accepted event family includes:

- `FE_START`
- `FE_QUIT`
- `SCREENSAVER_START`
- `SCREENSAVER_STOP`
- `LIST_CHANGE`
- `GAME_START`
- `GAME_QUIT`
- `GAME_PAUSE`
- `AUDIO_ANIMATION`
- `SPEAK_CONTROLS`
- `DEFAULT`

## 11. Save/Backup Strategy

Before major edits or release upgrades, back up:

- `data/games/AC_GameData.json`
- `data/library/AC_FXLibrary.json`
- `data/library/AC_AnimationLibrary.json`
- `data/profiles/`
- `data/keymaps/`
- `data/config/`

For release snapshots, archive the full `data/` folder with build/version label.

## 12. Troubleshooting

### 12.1 No Lighting Response

- Confirm `ACLighter.exe` is running.
- Confirm local port `6006` is not blocked.
- Verify Commander selected correct `PORT`.
- Use `ALL OFF` then `APPLY` to force state refresh.

### 12.2 Effect Exists in FX Editor but Not in Commander/Emulator

- Verify save wrote to shared library file under `data/library/`.
- Reload app/tab and re-open selector.
- Confirm item is saved under shared catalog format expected by loader.

### 12.3 Preview Works but Hardware Does Not

- Confirm ACLighter socket listener is active.
- Validate hardware transport path/cable and controller state.
- Use `LED TEST` and `BTN TEST` from utility bar for hardware-side checks.

### 12.4 Automation Not Triggering

- Confirm calling syntax for `ACDispatch.exe`.
- Confirm ROM key exists in `AC_GameData.json`.
- Confirm event mapping has animation and/or button map assignment.

## 13. Release Readiness Checklist

- All three executables built:
  - `ArcadeCommanderV2.exe`
  - `ACLighter.exe`
  - `ACDispatch.exe`
- Core tabs open and render correctly.
- `ALL OFF` verified in Commander and FX Editor.
- Effect load list consistent in Commander, Emulator, and FX Editor.
- `tease` preset present in shared preset-enabled locations.
- Game mapping save/load verified.
- ACLighter tray commands verified.
- ACDispatch event simulation verified.
- README + Release notes + manual included in package.

## 14. Support Files

- Release summary: `RELEASE_2.0.md`
- Effects engine details: `README_EFFECTS.md`
- This operator manual: `docs/USER_MANUAL_V2.md`
