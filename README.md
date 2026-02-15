# Arcade Commander 2.0

Arcade Commander 2.0 is a Windows LED control suite for arcade cabinets.  
This release includes three coordinated components:

- `ArcadeCommanderV2` (main UI and profile/effect workflow)
- `ACLighter` (background lighting service/daemon)
- `ACDispatch` (packet/command dispatcher)

## Release Components

### ArcadeCommanderV2
- Primary operator UI
- Shared effect loading across Commander, Emulator, and FX Editor tabs
- Controller configuration and game/profile mapping workflow

### ACLighter
- Runtime lighting service for applying effects and animations
- Works with shared effect/animation catalogs

### ACDispatch
- Dispatch bridge for control/state packets
- Supports local/networked flow used by the V2 stack

## Project Layout

- `ArcadeCommanderV2.py`
- `ACLighter.py`
- `ACDispatch.py`
- `data/config/`
- `data/games/`
- `data/library/`
- `data/profiles/`
- `data/keymaps/`
- `assets/`
- `RELEASE_2.0.md`

## Windows Build Outputs

Expected release artifacts after PyInstaller build:

- `dist/ArcadeCommanderV2/ArcadeCommanderV2.exe`
- `dist/ACLighter.exe`
- `dist/ACDispatch.exe`

## Notes

- Use `RELEASE_2.0.md` for full release notes and change summary.
- Use `docs/USER_MANUAL_V2.md` for the comprehensive operator manual.
- This repository is intended to keep all three components in sync for each tagged release.
