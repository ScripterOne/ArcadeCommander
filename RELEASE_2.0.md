# Arcade Commander 2.0 Release

## Overview
Arcade Commander 2.0 is a major platform update with:
- New networked V2 control flow
- Expanded FX Editor and Effects Engine
- Integrated Emulator + Layout tooling improvements
- Controller Config improvements
- Unified effect/animation catalog behavior across tabs

This release also includes coordinated updates for:
- `ACLighter`
- `ACDispatch`

## Major Features
- Commander tab effect loading and shared effect routing
- New `TEASE` animation support in shared registry/preview paths
- Future Enhancements card updates in Controller Config
- Emulator tab bottom tools row parity with Commander tools
- FX Editor global off control and preview/load stability fixes
- Effects preset expansion, including tease preset integration

## Runtime/Data Organization
- Introduced centralized runtime paths in `app_paths.py`
- Migrated runtime files into `data/`:
  - `data/config/`
  - `data/games/`
  - `data/library/`
  - `data/profiles/`
  - `data/keymaps/`
- Added legacy migration support so older root-level files are moved automatically

## Component Release Notes
### ArcadeCommander
- Core V2 app updates in `ArcadeCommanderV2.py`
- New shared effect catalog behavior across Commander/Emulator/FX Editor
- Expanded asset and layout support for multi-deck scenarios

### ACLighter
- Included updated service/daemon support files and spec updates

### ACDispatch
- Included updated dispatcher behavior and packaging spec updates

## Repository/Packaging Notes
- Added `.gitignore` rules for local build output:
  - `/build/`
  - `/dist/`
  - `__pycache__/`
- Added Git LFS tracking for large binary/media assets and installers

## Recommended Tag
- `v2.0.0`
