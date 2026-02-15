# Arcade Commander 2.0 User Manual

Version: 2.0
Release Channel: ALPHA (Pre-Release)
Primary Application: `ArcadeCommanderV2.exe`
Companion Services: `ACLighter.exe`, `ACDispatch.exe`

## 0. How to Use This Manual

This manual is written for cabinet builders, operators, and integrators who need full control of Arcade Commander 2.0.

Read order recommendation:

1. Section 1 (`Suite and Architecture`) for system model.
2. Section 2 (`Installation and Startup`) for clean setup.
3. Section 3 (`Operator Quick Start`) to verify end-to-end flow.
4. Section 4 through Section 8 for deep operations by tab/component.
5. Section 11 (`Troubleshooting`) when behavior is unexpected.

If you are integrating with a frontend launcher, read Section 8 (`ACDispatch Automation`) before production use.

[GRAPHIC PLACEHOLDER G-00: Manual Navigation Map]
- Purpose: Show readers where each part of the workflow lives in this document.
- Required image: One-page flow map with blocks for Setup, Authoring, Mapping, Validation, Automation.
- Annotation notes: Label each block with the matching section number.
- Suggested output: `docs/images/G-00-manual-navigation-map.png`.

## 1. Suite and Architecture

Arcade Commander 2.0 is a 3-component Windows suite:

- `ArcadeCommanderV2.exe`: operator UI and workflow host.
- `ACLighter.exe`: local runtime lighting service/tray app.
- `ACDispatch.exe`: command/event dispatcher used by scripts and frontend hooks.

All components share runtime data under `data/` and communicate locally over loopback networking.

### 1.1 Component Responsibilities

`ArcadeCommanderV2.exe`:

- User-facing control plane.
- Owns Commander, Emulator, Game Manager, FX Editor, and Controller Config tabs.
- Loads and saves profiles, game records, and shared FX/animation libraries.

`ACLighter.exe`:

- Runtime apply engine for live lighting behavior.
- Exposes local listener endpoint used by Commander and Dispatch.
- Provides tray-level stress/test/reset actions.

`ACDispatch.exe`:

- External trigger path for game events and automation.
- Supports idle reset, event signaling, animation forcing, and ROM-driven mapping loads.

### 1.2 Runtime Communication Model

Default local endpoint:

- Host: `127.0.0.1`
- Port: `6006`

Expected flow:

1. Operator configures behavior in Commander UI.
2. UI writes/reads runtime JSON data under `data/`.
3. UI and ACDispatch send runtime packets to ACLighter.
4. ACLighter applies effect and animation output to configured hardware path.

### 1.3 Shared Catalog Model

Effects and animations are designed as shared catalogs.
A saved entry in FX Editor should be available from Commander and Emulator selectors.

Shared files:

- Effects: `data/library/AC_FXLibrary.json`
- Animations: `data/library/AC_AnimationLibrary.json`

[GRAPHIC PLACEHOLDER G-01: Suite Architecture Diagram]
- Purpose: Explain data/control boundaries between the three executables.
- Required image: Diagram with 3 app boxes, loopback socket, and `data/` folder.
- Must show labels: Commander UI, ACLighter Service, ACDispatch CLI, `127.0.0.1:6006`.
- Annotation notes: Arrow direction for command flow and data persistence flow.
- Suggested output: `docs/images/G-01-suite-architecture.png`.

## 2. Installation and Startup

### 2.1 System Requirements

- Windows 10 or Windows 11 (64-bit recommended).
- Cabinet LED/controller hardware connected and recognized by system.
- Loopback networking enabled (`127.0.0.1`).
- If running from source: Python runtime and project dependencies installed.

### 2.2 Release Package Contents

Expected packaged outputs:

- `dist/ArcadeCommanderV2/ArcadeCommanderV2.exe`
- `dist/ACLighter.exe`
- `dist/ACDispatch.exe`

Documentation files expected in release bundle:

- `README.md`
- `RELEASE_2.0.md`
- `README_EFFECTS.md`
- `docs/USER_MANUAL_V2.md`

### 2.3 First-Run Startup Order (Recommended)

1. Start `ACLighter.exe` first.
2. Start `ArcadeCommanderV2.exe` second.
3. Use `ACDispatch.exe` for automation checks after both are up.

Why this order matters:

- Commander and Dispatch depend on ACLighter listener availability.
- Starting service first avoids connection timing issues during initial apply/load actions.

### 2.4 Shutdown Order

1. Stop external automation scripts (if active).
2. Close `ArcadeCommanderV2.exe`.
3. Exit `ACLighter.exe` from tray menu.

[GRAPHIC PLACEHOLDER G-02: Startup Order Visual]
- Purpose: Show exact launch/shutdown sequence.
- Required image: Numbered sequence graphic with start and stop order.
- Must show executable names exactly as shipped.
- Annotation notes: Add "required" marker on ACLighter-first startup.
- Suggested output: `docs/images/G-02-startup-sequence.png`.

## 3. Operator Quick Start (5-10 Minutes)

Use this sequence for first functional validation.

1. Launch `ACLighter.exe`.
2. Launch `ArcadeCommanderV2.exe`.
3. Open `CONTROLLER CONFIG` and confirm controller profile.
4. Open `ARCADE COMMANDER` and set visible test colors/effect.
5. Press `APPLY`.
6. Run `LED TEST` and `BTN TEST`.
7. Open `EMULATOR` and confirm visual parity.
8. Optional dispatch test:
   - `ACDispatch.exe --anim RAINBOW`

Expected result:

- Hardware responds to apply/test commands.
- Emulator behavior matches expected active effect routing.

If not, go to Section 11 (`Troubleshooting`).

[GRAPHIC PLACEHOLDER G-03: First Successful Apply]
- Purpose: Show user what a "good" first-run state looks like.
- Required image: Commander tab with color/effect chosen and apply confirmation context.
- Must show: Utility bar, current profile/game area, active selection state.
- Annotation notes: Circle `APPLY`, `LED TEST`, and `ALL OFF`.
- Suggested output: `docs/images/G-03-first-apply.png`.

## 4. Runtime Data Layout and File Behavior

V2 runtime files are centralized under `data/`.

### 4.1 Key Paths

- `data/config/ac_settings.json`
- `data/config/controller_config.json`
- `data/config/last_profile.cfg`
- `data/games/AC_GameData.json`
- `data/library/AC_FXLibrary.json`
- `data/library/AC_AnimationLibrary.json`
- `data/profiles/*.json`
- `data/keymaps/*.json`

### 4.2 File Role Reference

`ac_settings.json`:

- App-level preferences and startup behavior.

`controller_config.json`:

- Cabinet control deck and hardware profile definition.

`last_profile.cfg`:

- Pointer to most recently loaded profile/context.

`AC_GameData.json`:

- Game-centric mapping, profile, and FX/event behavior assignments.

`AC_FXLibrary.json` and `AC_AnimationLibrary.json`:

- Shared catalog entries used across tabs.

`profiles/*.json` and `keymaps/*.json`:

- Reusable profile and control mapping data artifacts.

### 4.3 Migration Behavior

V2 includes legacy migration logic that can move root-level runtime files into the `data/` structure at startup.

Operational recommendation:

- Before first V2 run on an upgraded environment, back up old runtime files.
- Verify migrated data in each `data/` subfolder before editing further.

[GRAPHIC PLACEHOLDER G-04: Runtime Folder Tree]
- Purpose: Make runtime storage expectations explicit.
- Required image: Windows Explorer tree expanded to all `data/` subfolders.
- Must show complete path and all key files from Section 4.1.
- Annotation notes: Highlight `games`, `library`, and `config` folders.
- Suggested output: `docs/images/G-04-runtime-tree.png`.

## 5. Detailed Tab Guide

## 5.1 ARCADE COMMANDER Tab

Role:

- Primary live-control workspace.

Common operator actions:

- Load a profile or game context.
- Set player/system colors.
- Select effect/animation behavior.
- Apply changes to active runtime path.

Bottom utility bar controls:

- `APPLY`: Push current selections to runtime output path.
- `ALL OFF`: Immediate blackout/reset state.
- `BTN TEST`: Verify button mapping and response.
- `SWAP FIGHT`: Swap fight button mapping orientation.
- `SWAP START`: Swap start/select orientation as configured.
- `LED TEST`: Validate output channels and color path.
- `CYCLE`: Iterate through test modes/colors.
- `DEMO`: Trigger a demonstration sequence.
- `PORT`: Change/select output port path.
- `ABOUT`: Build/version/license info dialog.
- `HELP`: Open help/manual resources.
- `QUIT`: Close application.

Safe operating notes:

- Use `ALL OFF` before profile switching if prior state persists unexpectedly.
- Use `APPLY` after meaningful edits; do not assume auto-apply.

[GRAPHIC PLACEHOLDER G-05: Commander Tab Annotated]
- Purpose: Identify all live controls used in normal operation.
- Required image: Full Commander tab at normal desktop scaling.
- Must show: main selection widgets and complete bottom utility bar.
- Annotation notes: Number every utility control left-to-right.
- Suggested output: `docs/images/G-05-commander-annotated.png`.

### 5.2 EMULATOR Tab

Role:

- Visual validation of layout, mappings, and selected effects/animations.

Use cases:

- Validate mapping before hardware confirmation.
- Compare behavior changes after effect edits.
- Reproduce non-hardware issues for debugging.

Validation workflow:

1. Load or assign target game/profile.
2. Apply effect from Commander or FX path.
3. Confirm emulator state reflects current selection.
4. Cross-check with hardware output when needed.

[GRAPHIC PLACEHOLDER G-06: Emulator Validation View]
- Purpose: Show where to check parity between assigned behavior and preview.
- Required image: Emulator tab with active game/effect loaded.
- Must show: visible controls plus current preview state.
- Annotation notes: Call out the values that must match Commander state.
- Suggested output: `docs/images/G-06-emulator-validation.png`.

### 5.3 GAME MANAGER Tab

Role:

- Per-game assignment and persistence management.

Typical tasks:

- Create or select game entries.
- Attach keymaps and profile behavior.
- Assign FX and event mappings.
- Save/import/export game data.

Source-of-truth file:

- `data/games/AC_GameData.json`

Data handling recommendations:

- Keep consistent ROM naming in records and dispatch calls.
- After bulk edits, restart selector views to verify loaded state.
- Validate one known game end-to-end before mass assignment.

[GRAPHIC PLACEHOLDER G-07: Game Manager Record Editing]
- Purpose: Show all fields required to make a valid game assignment.
- Required image: Game Manager with one selected record and assigned map/FX.
- Must show: game ID/name field, mapping selectors, save action area.
- Annotation notes: Highlight minimum required fields for successful dispatch mapping.
- Suggested output: `docs/images/G-07-game-manager-record.png`.

### 5.4 FX EDITOR Tab

Role:

- Authoring and preview environment for effects and animations.

Core workflow:

1. Create or load effect definition.
2. Adjust modulation/timing/color parameters.
3. Preview locally.
4. Save to shared libraries.
5. Verify visibility from Commander and Emulator selectors.

Critical control:

- `ALL OFF` provides immediate blackout/reset inside FX workflow.

Shared-catalog expectation:

- A saved entry should propagate to all tabs that consume shared catalogs.

[GRAPHIC PLACEHOLDER G-08: FX Editor Authoring Flow]
- Purpose: Show the exact edit-preview-save sequence.
- Required image: FX Editor with parameter controls and preview pane visible.
- Must show: load/save controls and live preview area at the same time.
- Annotation notes: Mark the "save to shared library" action point.
- Suggested output: `docs/images/G-08-fx-editor-flow.png`.

### 5.5 CONTROLLER CONFIG Tab

Role:

- Hardware/deck profile and app behavior configuration.

Expected configuration areas:

- Deck style and player count.
- Button/stick/trigger/extras definitions.
- App startup/default behavior values.
- Summary panel and planned feature card.

Operational recommendation:

- Complete Controller Config before deep game/effect assignment work.

[GRAPHIC PLACEHOLDER G-09: Controller Config Fields]
- Purpose: Document every field that affects runtime mapping.
- Required image: Controller Config tab with all major groups expanded/visible.
- Must show: deck options, player count, and app setting values.
- Annotation notes: Tag fields that require restart/reload after change.
- Suggested output: `docs/images/G-09-controller-config.png`.

## 6. Effects, Presets, and Shared Catalog Behavior

### 6.1 Shared Libraries

- Effects: `data/library/AC_FXLibrary.json`
- Animations: `data/library/AC_AnimationLibrary.json`

These files are shared across Commander, Emulator, and FX Editor.

### 6.2 Included Preset Set

Current preset family includes:

- `showroom_default`
- `classic_static`
- `neon_minimal`
- `party_mode`
- `tease`

Preset note:

- `tease` is a slow pulsing multi-phase cycle and should be visible where shared preset loading is supported.

### 6.3 Catalog Consistency Checks

After creating or editing entries:

1. Save in FX Editor.
2. Re-open selection list in Commander.
3. Re-open selection list in Emulator.
4. Confirm same entry appears in all selectors.

If not consistent, inspect Section 11.2.

[GRAPHIC PLACEHOLDER G-10: Shared Catalog Cross-Tab Verification]
- Purpose: Prove shared library synchronization behavior.
- Required image: Three cropped callouts from Commander, Emulator, FX Editor showing same entry.
- Must show identical effect/animation name in all three views.
- Annotation notes: Include one red marker where mismatch would appear.
- Suggested output: `docs/images/G-10-shared-catalog-parity.png`.

## 7. ACLighter Service Operations

### 7.1 Service Role

`ACLighter.exe` hosts runtime apply logic and listens for local commands.

Default listener:

- Host: `127.0.0.1`
- Port: `6006`

### 7.2 Tray Menu Reference

- `STRESS: Plasma`
- `STRESS: Hyper Strobe`
- `Test: Rainbow`
- `Reset (Off)`
- `Exit`

### 7.3 Service Verification Routine

1. Start ACLighter.
2. Confirm tray icon is active.
3. Use `Test: Rainbow`.
4. Trigger apply from Commander.
5. Send one dispatch event.

Expected result:

- All three control paths (tray, UI, dispatch) produce response.

[GRAPHIC PLACEHOLDER G-11: ACLighter Tray Operations]
- Purpose: Show operators the exact tray actions and expected order.
- Required image: Open tray menu with all commands visible.
- Must show: menu text exactly as released.
- Annotation notes: Add arrows for safe test order (`Rainbow` then `Reset (Off)`).
- Suggested output: `docs/images/G-11-aclighter-tray.png`.

## 8. ACDispatch Automation

### 8.1 Command Patterns

Idle reset:

- `ACDispatch.exe`

Trigger animation:

- `ACDispatch.exe --anim RAINBOW`

Trigger event mapping:

- `ACDispatch.exe --event GAME_START <rom_name>`

Load game profile behavior:

- `ACDispatch.exe <rom_name>`

### 8.2 Supported Event Family

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

### 8.3 Frontend Integration Guidance

Use dispatch calls from frontend hooks to keep lighting state synchronized with UX state transitions.

Typical mapping strategy:

1. Send `FE_START` when frontend launches.
2. Send `LIST_CHANGE` during browsing transitions.
3. Send `GAME_START <rom_name>` at launch.
4. Send `GAME_QUIT <rom_name>` when title exits.
5. Send `FE_QUIT` during frontend shutdown.

Validation rule:

- Every frontend event path should be tested with at least one known ROM mapping before production rollout.

[GRAPHIC PLACEHOLDER G-12: Dispatch CLI Examples]
- Purpose: Provide exact terminal syntax examples for integrators.
- Required image: Terminal window with successful command examples and outputs.
- Must show at least one `--anim`, one `--event`, and one ROM-name invocation.
- Annotation notes: Highlight argument positions and required token case.
- Suggested output: `docs/images/G-12-acdispatch-cli.png`.

## 9. Backup, Restore, and Change Management

### 9.1 Backup Scope (Before Major Changes)

Back up these paths together:

- `data/games/AC_GameData.json`
- `data/library/AC_FXLibrary.json`
- `data/library/AC_AnimationLibrary.json`
- `data/profiles/`
- `data/keymaps/`
- `data/config/`

### 9.2 Snapshot Strategy

Recommended snapshot label format:

- `AC2_<YYYY-MM-DD>_<environment>_<note>`

Examples:

- `AC2_2026-02-15_ArcadeCab_A_PreUpdate`
- `AC2_2026-02-15_ArcadeCab_A_PostTune`

### 9.3 Restore Procedure (High Level)

1. Stop Commander and ACLighter.
2. Replace `data/` contents from snapshot.
3. Restart ACLighter, then Commander.
4. Validate one known game and one known effect.

[GRAPHIC PLACEHOLDER G-13: Backup Folder Example]
- Purpose: Standardize backup packaging so restores are repeatable.
- Required image: Explorer view of timestamped backup folder structure.
- Must show all required files/folders from Section 9.1.
- Annotation notes: Mark required vs optional archive content.
- Suggested output: `docs/images/G-13-backup-structure.png`.

## 10. Validation and Release Readiness Checklist

Use this checklist before shipping or cabinet handoff.

Build/runtime checks:

- `ArcadeCommanderV2.exe` build present.
- `ACLighter.exe` build present.
- `ACDispatch.exe` build present.

Functional checks:

- All tabs open and render correctly.
- `ALL OFF` verified in Commander and FX Editor.
- Shared catalog entries visible in Commander, Emulator, and FX Editor.
- `tease` preset visible where shared preset loading applies.
- Game map save/load verified.
- ACLighter tray commands verified.
- ACDispatch event simulation verified.

Package checks:

- README and release notes included.
- Manual included and current.
- Runtime `data/` schema verified for expected files.

[GRAPHIC PLACEHOLDER G-14: Release Checklist Completion Sheet]
- Purpose: Provide signoff artifact for deployment.
- Required image: Completed checklist template with initials/date.
- Must show pass/fail status for each major subsystem.
- Annotation notes: Include escalation owner field for failed checks.
- Suggested output: `docs/images/G-14-release-checklist.png`.

## 11. Troubleshooting Guide

### 11.1 No Lighting Response

Symptoms:

- No visible LED output after apply or tests.

Likely causes:

- ACLighter not running.
- Port/path mismatch.
- Hardware path disconnected.

Actions:

1. Confirm ACLighter tray icon exists.
2. Verify listener path and selected port.
3. Run `ALL OFF` then `APPLY`.
4. Run `LED TEST` and `BTN TEST`.

### 11.2 Effect Exists in FX Editor but Missing Elsewhere

Symptoms:

- Effect appears in FX Editor but not Commander/Emulator selectors.

Likely causes:

- Save did not persist to shared library.
- Selector cache not refreshed.
- Entry format inconsistent.

Actions:

1. Verify entry exists in `data/library/AC_FXLibrary.json` or animation file.
2. Reload selectors or restart app.
3. Re-save using shared library path.

### 11.3 Preview Works but Hardware Does Not

Symptoms:

- Emulator/preview updates but cabinet LEDs do not.

Likely causes:

- ACLighter listener path unavailable.
- Hardware transport failure.
- Port selection mismatch.

Actions:

1. Confirm ACLighter active state.
2. Validate physical connections.
3. Run hardware-side diagnostics via `LED TEST`.

### 11.4 Automation Events Not Triggering

Symptoms:

- ACDispatch command executes but expected behavior is missing.

Likely causes:

- Wrong event name or argument format.
- ROM name mismatch with `AC_GameData.json` record.
- Missing event assignment in game map.

Actions:

1. Re-run command with known-good syntax.
2. Confirm ROM key in game DB.
3. Confirm event mapping exists and references valid effect/animation.

### 11.5 Escalation Capture Pack

When escalating, capture and attach:

- Exact command used.
- Screenshot of UI state.
- Relevant JSON snippet from `data/games` or `data/library`.
- Build versions and environment notes.

[GRAPHIC PLACEHOLDER G-15: Troubleshooting Decision Tree]
- Purpose: Speed root-cause isolation for field issues.
- Required image: Decision tree from symptom to corrective action.
- Must include branches for service, data, mapping, and hardware.
- Annotation notes: Add priority marker on fastest high-confidence checks.
- Suggested output: `docs/images/G-15-troubleshooting-tree.png`.

## 12. Graphics Production Shot List (All Placeholders)

Use this section as the master specification for documentation screenshots/graphics.

### 12.1 Capture Standards

- Format: PNG for screenshots/diagrams.
- Recommended width: 1920 px (or 1600 px minimum).
- Scale: 100% UI scale whenever possible.
- Theme: Keep visual theme consistent across all captures.
- Annotation style: Use numbered callouts with short labels.
- File naming: `G-XX-short-description.png`.

### 12.2 Placeholder Index

`G-00`:

- Title: Manual Navigation Map.
- Required content: End-to-end workflow map aligned to section numbers.

`G-01`:

- Title: Suite Architecture Diagram.
- Required content: Commander, ACLighter, ACDispatch, `data/`, and socket link.

`G-02`:

- Title: Startup Order Visual.
- Required content: Launch and shutdown order with dependency markers.

`G-03`:

- Title: First Successful Apply.
- Required content: Commander with active selection and utility controls visible.

`G-04`:

- Title: Runtime Folder Tree.
- Required content: Explorer view with `data` subfolders and key JSON files.

`G-05`:

- Title: Commander Tab Annotated.
- Required content: Full Commander screen with numbered utility controls.

`G-06`:

- Title: Emulator Validation View.
- Required content: Emulator screen showing loaded state to compare with Commander.

`G-07`:

- Title: Game Manager Record Editing.
- Required content: Game record fields plus mapping/FX assignments.

`G-08`:

- Title: FX Editor Authoring Flow.
- Required content: Parameter controls, preview area, and save action.

`G-09`:

- Title: Controller Config Fields.
- Required content: Deck profile settings and app settings in one capture.

`G-10`:

- Title: Shared Catalog Cross-Tab Verification.
- Required content: Same effect visible across Commander, Emulator, and FX Editor.

`G-11`:

- Title: ACLighter Tray Operations.
- Required content: Full tray menu with stress/test/reset options.

`G-12`:

- Title: Dispatch CLI Examples.
- Required content: Valid command invocations with visible outputs.

`G-13`:

- Title: Backup Folder Example.
- Required content: Snapshot folder layout with dated naming convention.

`G-14`:

- Title: Release Checklist Completion Sheet.
- Required content: Completed checklist with signoff status.

`G-15`:

- Title: Troubleshooting Decision Tree.
- Required content: Symptom-driven diagnosis flow.

`G-16`:

- Title: "Known Good" End State Panel.
- Required content: Combined collage of service running, profile loaded, and dispatch success.

[GRAPHIC PLACEHOLDER G-16: Known Good End State]
- Purpose: Define the final target state for acceptance testing.
- Required image: 3-panel collage (Commander, ACLighter tray, CLI test success).
- Must show: consistent profile/effect naming across all panels.
- Annotation notes: Include date/time/build labels on each panel.
- Suggested output: `docs/images/G-16-known-good-state.png`.

## 13. Support References

- Release summary: `RELEASE_2.0.md`
- Effects engine notes: `README_EFFECTS.md`
- Primary repository notes: `README.md`
- This manual: `docs/USER_MANUAL_V2.md`

## 14. Document Maintenance Notes

When updating this manual:

1. Keep command syntax examples in sync with executable behavior.
2. Keep event family list synchronized with ACDispatch.
3. Keep runtime file path references synchronized with `app_paths.py` behavior.
4. Update placeholder descriptions if UI labels/layout change.
5. Date-stamp major manual edits in release notes.
