import tkinter as tk
from collections import OrderedDict


COLORS = {
    "BG": "#121212",
    "SURFACE": "#1E1E1E",
    "SURFACE_LIGHT": "#2C2C2C",
    "TEXT": "#FFFFFF",
    "TEXT_DIM": "#888888",
    "P1": "#00E5FF",
    "P2": "#FF0055",
    "SYS": "#FFD700",
}


class ArcadeCommanderHelp:
    def __init__(self, root):
        self.root = root
        self.root.title("ARCADE COMMANDER HELP")
        self.root.geometry("1240x880")
        self.root.minsize(980, 700)
        self.root.configure(bg=COLORS["BG"])
        self.current_topic = None
        self.visible_topics = []
        self.help_data = self._build_help_data()
        self._build_ui()
        self.update_index()
        first = next(iter(self.help_data.keys()), None)
        if first:
            self.display_topic(first)

    def _build_help_data(self):
        return OrderedDict(
            [
                (
                    "1) Quick Start",
                    """## What Arcade Commander Controls
- Physical control deck LEDs
- Emulator visualized LEDs
- Per-game profile/event behavior
- FX and animation authoring libraries

## First-Time Setup (10 Minutes)
1. Open ARCADE COMMANDER tab.
2. Verify hardware/service connection.
3. Set button color slots for P1, P2, and SYSTEM.
4. Save a baseline map/profile.
5. Open FX EDITOR and test preview.
6. Save effect to FX Library.
7. Assign effect to a game.
8. Set Start/End FX in game profile.
9. Verify behavior in EMULATOR and on hardware.

## Core Terms
- Effect: One behavior pattern (cycle, pulse, audio driven, etc.).
- Animation: Timeline/sequence of effects and durations.
- Assigned Colors: Per-button slot palette (slot1-slot4).
- Profile/Map: Saved deck colors/behavior state.
- Preview: Temporary test run.
""",
                ),
                (
                    "2) Tab Guide",
                    """## Tab Roles
- ARCADE COMMANDER: Button colors, group controls, map save/load, quick utilities.
- EMULATOR: Visualizer + effect/animation trigger testing.
- GAME MANAGER: Per-game metadata, overrides, event-to-FX mapping.
- FX EDITOR: Effects/animations build, audio tools, assignment, save to library.
- CONTROLLER CONFIG: Controller capabilities and saved controller configuration.

## Recommended Working Order
1. Set button palettes in ARCADE COMMANDER.
2. Build/test effects in FX EDITOR.
3. Bind game events in GAME MANAGER.
4. Validate in EMULATOR and on physical deck.

## Quick Control Index By Tab
- ARCADE COMMANDER: APPLY, ALL OFF, BTN TEST, SWAP FIGHT, SWAP START, LED TEST, CYCLE, DEMO, PORT, ABOUT, HELP, QUIT.
- EMULATOR: VIEW selector, SWITCH, CATCHLIGHT toggle, LOAD/REFRESH/APPLY game, APPLY FX, APPLY ANIM, Event selector.
- GAME MANAGER: Search, NEW GAME, LOAD DB, SAVE DB, SAVE CHANGES, DELETE OVERRIDE, EVENT ASSIGNMENT controls.
- FX EDITOR: PREVIEW, ALL OFF, Color Mode, LOAD WAV, BUILD SEQ, SAVE TO LIB, trim controls, wave controls, ASSIGN/PREVIEW, library/game apply controls.
- CONTROLLER CONFIG: controller type/style/count combos, extras toggles, app settings toggles, default preset selector, notes.
""",
                ),
                (
                    "3) Button Color Assignment",
                    """## Why This Is Critical
Assigned Cycle/Pulse/Random rely on each button's slot colors.
If slots are empty or all black, cycle modes appear broken.

## Where To Assign
- ARCADE COMMANDER tab button context menus/palette.
- Group color tools for fast bulk assignment.

## Slot Strategy
- Slot 1: Primary identity color.
- Slot 2: Contrast color.
- Slot 3: Accent color.
- Slot 4: Highlight or white.

## Assignment Checklist
1. Set at least 2 non-black slots per button.
2. Keep P1 and P2 palettes intentionally different.
3. Save map after major palette changes.
4. In FX EDITOR use Color Mode = Assigned Cycle and preview.
""",
                ),
                (
                    "4) ARCADE COMMANDER Tab",
                    """## Main Use
Live deck configuration and baseline color management.

## Features
- Per-button slot color editing.
- Group controls for player/system sections.
- Utility actions (all off, swaps, tests, help).
- Save/load map profiles.

## Controls Explained
- Button widgets (A/B/C/X/Y/Z/START/MENU/REWIND/TRACKBALL):
- Left-click: edit/select color slot quickly.
- Right-click: full context menu (slot color copy/paste/clear and slot FX assignment).
- Group THEME control:
- Applies color slot palettes to the full group.
- Group mode controls (primary/secondary/theme/fx mode where available):
- Changes how that group renders/animates by default.
- PULSE toggle + speed scale:
- Enables pulse interpolation through group color slots and sets pulse speed.

## Bottom Utility Bar Controls
- APPLY: Pushes current LED state to hardware immediately.
- ALL OFF: Clears all button colors and disables active animation.
- BTN TEST: Opens input test window.
- SWAP FIGHT: Swaps P1/P2 fight button mapping.
- SWAP START: Swaps P1_START and P2_START mapping.
- LED TEST: Opens tester menu (sanity/pin finder/attract test).
- CYCLE: Starts legacy color cycle animation.
- DEMO: Starts demo animation mode.
- PORT: Port/service selection dialog.
- ABOUT: Version/about dialog.
- HELP: Opens this help window.
- QUIT: Exit app.

## Typical Tasks
## Build Baseline Palette
1. Set P1 button colors.
2. Set P2 button colors.
3. Set system/admin colors.
4. Save map.

## Maintain Consistency
- Use this tab as source of truth for assigned color effects.
""",
                ),
                (
                    "5) EMULATOR Tab",
                    """## Main Use
Visual validation of button mapping and behavior.

## Sections
- Game loader/list for profile context.
- Effects list for quick effect trigger.
- Animation list for saved sequence trigger.
- Catchlight toggle for visual style.

## Top Controls
- VIEW dropdown (EMULATOR/DESIGNER):
- Switches between emulator view and layout designer view.
- SWITCH button:
- Applies selected view mode.
- CATCHLIGHT ON/OFF button:
- Toggles button reflection highlight.
- QUIT:
- Closes application.

## Load Game Card Controls
- Catchlight checkbox:
- Alternate catchlight toggle in card context.
- Search box:
- Filters games in list.
- REFRESH:
- Reloads game list from current data source.
- LOAD:
- Loads selected game context in emulator controls.
- APPLY:
- Applies selected game profile to runtime state.
- Game list:
- Select game context for preview and apply.

## Effects and Animations Card Controls
- EFFECTS list:
- Built-in effect list for quick trigger.
- APPLY FX:
- Runs selected effect preview.
- ANIMATIONS list:
- Custom animation library entries.
- Event combobox:
- Chooses event channel used when applying selected animation.
- APPLY ANIM:
- Runs selected animation event sequence.

## Validation Flow
1. Load a game context.
2. Trigger effect/animation.
3. Compare emulator output with physical deck.
4. Fix mapping or assignment if mismatch appears.
""",
                ),
                (
                    "6) GAME MANAGER Tab",
                    """## Main Use
Per-game data and event rules in AC_GameData.json.

## Key Fields
- Controller mode and policy.
- Default FX.
- FX on Start.
- FX on End.
- Event assignments/overrides.

## Workflow
1. Select game.
2. Edit profile fields and event mappings.
3. Save.
4. Test with game start/end events.

## Controls Explained
- GAME LIBRARY search:
- Filters game rows.
- NEW GAME:
- Creates a new game override entry.
- Game list:
- Selects active game for editor panel.

## Editor Fields
- Title/Developer/Year/Genre/Platform/Recommended/Rank:
- Game metadata used in catalog and UI.
- ROM Key (readonly):
- Internal identity key for game mapping.

## Profile Controls
- Vendor:
- Optional vendor override text.
- Controller dropdown:
- Controller profile mode for this game.
- Policy dropdown:
- Lighting policy (AUTO/ARCADE_ONLY/FX_ONLY/OFF).
- Events summary/details:
- Shows currently configured event mappings.

## Event Assignment Panel
- BUTTON MAP list + search:
- Choose button map source.
- ANIMATION list + search:
- Choose animation/effect target.
- EVENT list + search:
- Choose event trigger.
- ASSIGN:
- Writes selected mapping to event table.

## Footer Controls
- Enable Override:
- Enables/disables profile override for selected game.
- LOAD DB / SAVE DB:
- Reloads/saves game database file.
- SAVE CHANGES:
- Saves editor values to selected game.
- DELETE OVERRIDE:
- Removes override for selected game.
""",
                ),
                (
                    "7) FX EDITOR Overview",
                    """## Main Use
Authoring and previewing effects and animations.

## Main Panels
- Modulation panel: timeline, preview, waveform, trims, wave types, controls.
- Assignments panel: FX Library, Game Library, target button grid.
- Animation panel: animation catalog, event sequence, save controls.

## Build Modes
- Non-audio effects (assigned colors + modulation).
- Audio-reactive effects (WAV analysis + assignments).
- Animation sequences (timed effect chains).

## Modulation Panel Controls
- Timeline canvas + scrubber:
- Visual phase/section preview marker.
- Play WAV on Preview:
- Enables WAV playback during preview.
- PREVIEW:
- Starts/stops local FX preview tick.
- ALL OFF:
- Clears local preview canvas state.
- Color Mode combobox:
- Audio / Assigned Cycle / Assigned Pulse / Assigned Random / Primary Only.
- LOAD WAV:
- Loads WAV (or converted audio source).
- BUILD SEQ:
- Builds analysis sequence from current trim bounds.
- SAVE TO LIB:
- Saves current editor effect state to FX library.
- Waveform display:
- Shows current audio waveform/analysis visualization.
- Trim Start / Trim End sliders:
- Sets trimmed section for sequence build and audio preview.
- Wave selectors:
- FX WAVE and ANIMATION WAVE choice and descriptors.
- EFFECTS controls:
- Preset, Apply, Rate, Intensity, Stagger, Width, Bias, Lock Width/Bias, Curve.
- ANIMATION controls:
- Rate, Intensity, Stagger, Width, Bias, Lock Width/Bias, Curve.

## Assignments Panel Controls
- LIBRARY tabs:
- Effects and Animations views.
- Effects library controls:
- Search, filter, REFRESH, IMPORT, EXPORT, DELETE, LOAD, PREVIEW.
- GAME LIBRARY controls:
- Search, APPLY FX, LOAD FX, FX Start, FX End, SAVE START/END.
- Assign row:
- Assign To, Group, ASSIGN, PREVIEW.
- Grid buttons:
- Select target buttons for assignment; right-click opens color/slot menu.
- FX QUICK TEST canvas:
- Local visualization of preview output against logical button layout.

## Animation Catalog Controls
- Built-in animation catalog list.
- User library list.
- APPLY ANIM button.
- Event selector.
- Anim selector and duration input.
- ADD TO ANM for sequence building.
- TRIGGER for event preview.
- SAVE ANM for persistent animation save.
""",
                ),
                (
                    "8) Effects Building (Non-Audio)",
                    """## Goal
Create an effect that uses assigned button colors and modulation controls.

## Step-by-Step
1. Open FX EDITOR.
2. Set Color Mode to Assigned Cycle.
3. In Assign row set:
- Assign To = Full Range (recommended default)
- Group = All (or your target group)
- Click ASSIGN
4. Select FX Wave (start with Sine).
5. Tune controls:
- Rate: 0.6 to 1.2
- Intensity: 0.8 to 1.2
- Stagger: 0.00 to 0.20
- Width: 0.50 to 0.75
- Bias: 0.10 to 0.30
- Curve: Linear
6. Click PREVIEW and refine.
7. Click SAVE TO LIB and name effect.

## If It Looks Static
- Confirm multiple non-black color slots exist.
- Confirm Color Mode is Assigned Cycle (not Audio).
""",
                ),
                (
                    "9) Using Audio (WAV) to Build Effects",
                    """## Goal
Drive effect output from a selected WAV section.

## Step-by-Step
1. Click LOAD WAV.
2. Verify waveform appears.
3. Set Trim Start and Trim End.
4. Click BUILD SEQ.
5. Set Color Mode = Audio.
6. Assign targets:
- Bass for low-end emphasis
- Mid for body/instrument response
- Treble for transients/highs
- Full Range for balanced response
- Sine for synthetic modulation behavior
7. Optional: enable Play WAV on Preview.
8. Click PREVIEW.
9. Save effect to library.

## Important Notes
- Rebuild sequence after changing trim.
- If too dim, increase Intensity, Width, and Bias.
- If too chaotic, lower Rate and reduce Treble-heavy mapping.
""",
                ),
                (
                    "10) FX Editor Controls Reference",
                    """## Color Mode
- Audio
- Assigned Cycle
- Assigned Pulse
- Assigned Random
- Primary Only

## Modulation Controls
- Rate: speed.
- Intensity: brightness influence.
- Stagger: per-button phase delay.
- Width: duty cycle (longer active windows).
- Bias: brightness floor.
- Curve: Linear, Ease-In, Bounce.
- Wave Type: Sine, Square, Sawtooth, Triangle, Noise.

## Assignment Controls
- Assign To: Bass/Mid/Treble/Sine/Full Range.
- Group: Selected/P1/P2/Admin/All.
- ASSIGN writes mapping.
- PREVIEW (next to ASSIGN) tests assignment behavior.
""",
                ),
                (
                    "11) Animation Building (Step-by-Step)",
                    """## Goal
Create a timeline of effect events and durations.

## Build Sequence
1. Choose event type (for example GAME_START).
2. Choose animation/effect from catalog.
3. Set duration.
4. Click ADD TO ANM.
5. Repeat to chain multiple steps.
6. Enter animation name.
7. Click SAVE ANM.

## Practical Pattern
1. Start with RAINBOW (2-3s).
2. Add intermediate animations.
3. End with RAINBOW or ALL_OFF depending on intent.

## Event Design Guidance
- GAME_START: short intro impact.
- GAME_ST: stable gameplay loop.
- GAME_QUIT/END: clear outro.
""",
                ),
                (
                    "12) Apply Effects to Games",
                    """## Apply FX to a Game
1. In FX EDITOR select a saved effect from FX Library.
2. In Game Library select target game.
3. Click APPLY FX.
4. Optionally click LOAD FX to verify assignment.

## Set Start/End Events
1. Set FX Start.
2. Set FX End.
3. Click SAVE START/END.

## Validate
- Trigger start/end and confirm both hardware and emulator.
""",
                ),
                (
                    "13) FX Library and Animation Library",
                    """## FX Library
- Save, load, refresh.
- Import/export JSON.
- Delete and maintain clean set.

## Animation Library
- Stores named animation sequences.
- Supports event-based playback design.
- Save frequently after edits.

## Sharing Tips
- Use clear names and versions.
- Export stable builds only.
""",
                ),
                (
                    "14) CONTROLLER CONFIG Tab",
                    """## Purpose
Save controller capability configuration.

## Configure
- Controller type and style.
- Players and control counts.
- Extras and LED enable flags.

## Output
- Summary panel and persisted controller_config.json.

## Controls Explained
- Controller dropdown:
- Selects base hardware family.
- Style dropdown:
- Chooses control layout style.
- Players / Max Players:
- Defines present and supported player counts.
- Buttons/Player, Sticks/Player, Triggers/Player, D-Pad/Player:
- Defines per-player input topology.
- Include START / Include COIN:
- Enables/disables those button classes in profile description.
- Extras toggles:
- Trackball, Spinner, L/R Flipper, L/R Nudge.
- Buttons are LED enabled:
- Marks LED capability for runtime assumptions.
- Notes text:
- Freeform operator notes saved with config.

## App Settings Controls (same tab)
- Skip splash screen.
- Skip startup WAV.
- FX tab intro video/audio toggles.
- Enable default effects engine.
- Default effects preset selector.

## Save Behavior
- App settings controls save immediately when toggled/changed.
- Controller configuration save button persists full controller config.
""",
                ),
                (
                    "15) Data and Persistence",
                    """## Main Files
- AC_GameData.json
- AC_FXLibrary.json
- AC_AnimationLibrary.json
- controller_config.json
- ac_settings.json
- last_profile.cfg and profile json files

## Backup Guidance
- Export FX library regularly.
- Back up game db before bulk edits.
- Keep a known-good baseline profile.
""",
                ),
                (
                    "16) Troubleshooting: FX and Audio",
                    """## No Light Response
- Verify hardware connection first.
- Confirm service path is active.
- Run quick hardware tests.

## Audio Preview Problems
- Confirm WAV loaded.
- Confirm sequence built after trim update.
- Confirm Play WAV on Preview when expecting sound.
- Check status text in FX EDITOR.

## Trim Feels Wrong
- Rebuild sequence after trim changes.
- Ensure trim start is less than trim end.
""",
                ),
                (
                    "17) Troubleshooting: Color Cycle",
                    """## Assigned Cycle Not Cycling
1. Color Mode must be Assigned Cycle.
2. Buttons need multiple non-black slots.
3. Correct group must be assigned.
4. Preview must be active.

## Looks Like One Color Only
- Slot palette likely duplicates same color.
- Set distinct slot colors on ARCADE COMMANDER tab.

## FX Editor vs Emulator Differences
- FX Editor preview is local simulation.
- Emulator/deck behavior follows shared runtime sync path.
""",
                ),
                (
                    "18) ACDispatch and Automation",
                    """## Purpose
External trigger utility for front-ends and scripts.

## Common Uses
- Trigger game profile load by ROM key.
- Trigger named animation/effect.
- Force idle/off transitions.

## Integration Rules
- Keep ROM keys consistent with game db.
- Keep event names normalized.
""",
                ),
                (
                    "19) Operator Playbooks",
                    """## Playbook A: Build New Effect
1. Set button slot colors.
2. Build in FX EDITOR.
3. Save to FX Library.
4. Apply to game.
5. Set start/end.
6. Validate.

## Playbook B: Build Audio Effect
1. Load WAV.
2. Trim and Build Seq.
3. Assign bands.
4. Preview/tune.
5. Save and apply.

## Playbook C: Build Animation
1. Chain timed steps.
2. Save animation.
3. Bind to game events.
4. Validate transitions.
""",
                ),
                (
                    "20) Best Practices",
                    """## Design
- Keep P1/P2 palettes distinguishable.
- Avoid max intensity always-on loops.
- Use strobe effects sparingly.

## Workflow
- Build from stable baseline.
- Change one variable at a time.
- Validate in emulator and hardware.

## Release Readiness Checklist
- Core effects saved and named.
- Start/end mappings done for priority games.
- Emulator and hardware behavior aligned.
- Backups completed.
""",
                ),
                (
                    "21) Control Reference: ARCADE COMMANDER",
                    """## Player Cards (PLAYER 1 / PLAYER 2)
- Button widgets (A/B/C/X/Y/Z/START):
- Left-click: open slot color flow/select behavior.
- Right-click: advanced context actions (copy/paste/clear slot, slot FX assignment).
- Group THEME row:
- Applies group-wide slot colors.
- PULSE checkbox:
- Enables pulse mode for group.
- Speed slider:
- Sets pulse speed for that group.
- MODE label:
- Shows detected/active mode state.

## System Card
- TRACKBALL button:
- Trackball LED color/slot control.
- REWIND and MENU buttons:
- Admin/system LED controls.
- SAVE MAP:
- Writes current led_state to profile JSON.
- LOAD MAP:
- Loads profile JSON into runtime state.

## Bottom Utility Bar
- APPLY: push current state to hardware/emulator sync path.
- ALL OFF: clear colors and stop active animations.
- BTN TEST: input/button tester window.
- SWAP FIGHT: swap P1/P2 fight button mappings.
- SWAP START: swap P1_START and P2_START.
- LED TEST: external tester menu (sanity, pin finder, attract).
- CYCLE: start cycle-mode preview loop.
- DEMO: start demo-mode preview loop.
- PORT: change/check port or service connection target.
- ABOUT: opens About dialog.
- HELP: opens Help window.
- QUIT: exits app.
""",
                ),
                (
                    "22) Control Reference: EMULATOR",
                    """## Top Toolbar
- VIEW dropdown:
- Selects EMULATOR or DESIGNER host view.
- SWITCH:
- Applies selected view mode.
- CATCHLIGHT ON/OFF:
- Toggles lens reflection style.
- QUIT:
- Closes app.

## LOAD GAME Card
- Catchlight checkbox:
- Same behavior as top catchlight toggle in local card context.
- Search field:
- Filters game list.
- REFRESH:
- Reload list from database/catalog source.
- LOAD:
- Loads selected game row context.
- APPLY:
- Applies selected game profile to runtime.
- Game list:
- Select row for load/apply actions.

## EFFECTS & ANIMATIONS Card
- EFFECTS list:
- Built-in effects.
- APPLY FX:
- Runs selected built-in effect.
- ANIMATIONS list:
- Saved animation library entries.
- Event combobox:
- Selects event channel for animation trigger.
- APPLY ANIM:
- Runs selected animation for chosen event.
- Status text:
- Displays last action/result hints.
""",
                ),
                (
                    "23) Control Reference: GAME MANAGER",
                    """## Left Panel (GAME LIBRARY)
- Search field:
- Filters game list.
- NEW GAME:
- Creates a new override entry.
- Game list:
- Selects active game row.

## Right Panel (EDITOR + PROFILE)
- Title, Vendor/Dev, Year, Genre, Platform, Recommended, Rank:
- Metadata override fields.
- ROM Key:
- Read-only internal key.
- Vendor (profile section):
- Optional profile vendor text.
- Controller dropdown:
- ARCADE_PANEL / GAMEPAD_GENERIC / XINPUT_XBOX / LIGHTGUN / UNKNOWN.
- Policy dropdown:
- AUTO / ARCADE_ONLY / FX_ONLY / OFF.
- Events summary/details:
- Current assigned event mapping display.

## EVENT ASSIGNMENT Panel
- BUTTON MAP search + list:
- Source map selection.
- ANIMATION search + list:
- Animation target selection.
- EVENT search + list:
- Event trigger selection.
- ASSIGN:
- Commits selected map/animation/event assignment.

## Bottom Actions
- Enable Override checkbox:
- Toggles whether profile override is active.
- LOAD DB:
- Reload database from disk.
- SAVE DB:
- Save database to disk.
- SAVE CHANGES:
- Save current editor values to selected game.
- DELETE OVERRIDE:
- Remove selected game's override.
""",
                ),
                (
                    "24) Control Reference: FX EDITOR",
                    """## MODULATION Panel
- Timeline canvas:
- Shows animation phases and preview scrub position.
- Play WAV on Preview:
- Toggles WAV playback in preview flow.
- PREVIEW:
- Starts/stops modulation preview.
- ALL OFF:
- Clears local preview canvas.
- Color Mode combobox:
- Audio / Assigned Cycle / Assigned Pulse / Assigned Random / Primary Only.
- LOAD WAV:
- Loads WAV/audio source.
- BUILD SEQ:
- Builds sequence from current trim/audio analysis.
- SAVE TO LIB:
- Saves current FX editor state to library.
- Waveform canvas:
- Displays loaded waveform/analysis.
- Trim Start / Trim End sliders:
- Defines active audio segment.
- FX WAVE / ANIMATION WAVE comboboxes:
- Sets waveforms and descriptors.
- EFFECTS column:
- Preset + APPLY, Rate dial, Intensity dial, Stagger slider, Width slider, Bias slider, Lock Width/Bias, Curve combobox.
- ANIMATION column:
- Rate dial, Intensity dial, Stagger slider, Width slider, Bias slider, Lock Width/Bias, Curve combobox.

## ASSIGNMENTS Panel
- LIBRARY tabs:
- Effects tab and Animations tab.
- Effects tab controls:
- Search, Filter, REFRESH, IMPORT, EXPORT, DELETE, LOAD, PREVIEW.
- GAME LIBRARY controls:
- Search, APPLY FX, LOAD FX, FX Start combobox, FX End combobox, SAVE START/END.
- Assign row controls:
- Assign To combobox, Group combobox, ASSIGN, PREVIEW.
- Grid buttons:
- Target button selection for assignment.
- FX QUICK TEST:
- Local visual preview surface.

## Animation Catalog Controls
- Built-in animation catalog list + scrollbar.
- User library list + scrollbar.
- APPLY ANIM:
- Applies selected built-in animation preview.
- Event selector:
- Chooses event timeline bucket.
- Anim selector + Dur(s):
- Step content and duration.
- ADD TO ANM:
- Adds step to current animation.
- TRIGGER:
- Runs event preview.
- BAKE AUDIO:
- Writes audio sequence into animation structure.
- SAVE ANM:
- Saves named animation.
""",
                ),
                (
                    "25) Control Reference: CONTROLLER CONFIG",
                    """## CONFIGURATION Panel
- Controller dropdown:
- Select controller family.
- Style dropdown:
- Choose panel style.
- Players dropdown:
- Active player count.
- Max Players dropdown:
- Supported maximum players.
- Buttons/Player dropdown:
- Button count per player.
- Sticks/Player dropdown:
- Stick count per player.
- Triggers/Player dropdown:
- Trigger count per player.
- D-Pad/Player dropdown:
- D-pad count per player.
- Include START checkbox:
- Include start buttons in capability profile.
- Include COIN checkbox:
- Include coin buttons in capability profile.
- EXTRAS checkboxes:
- Trackball, Spinner, L Flipper, L Nudge, R Flipper, R Nudge.
- Buttons are LED enabled checkbox:
- LED capability flag.
- Notes text area:
- Freeform operator notes.

## SUMMARY Panel
- Read-only computed summary of selected controller configuration.

## APP SETTINGS Panel
- Skip splash screen.
- Skip startup WAV.
- FX tab intro video toggle.
- FX tab intro audio toggle.
- Enable default effects engine toggle.
- Default effects preset dropdown.
- Preset description label.

## Save Behavior
- App settings persist immediately when changed.
- Controller configuration save action persists controller config.
""",
                ),
            ]
        )

    def _build_ui(self):
        top = tk.Frame(self.root, bg=COLORS["SURFACE"], pady=10)
        top.pack(fill="x")
        tk.Label(
            top,
            text="HELP SEARCH",
            bg=COLORS["SURFACE"],
            fg=COLORS["TEXT_DIM"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(16, 8))
        self.search_entry = tk.Entry(
            top,
            bg=COLORS["SURFACE_LIGHT"],
            fg=COLORS["TEXT"],
            borderwidth=0,
            insertbackground=COLORS["TEXT"],
            font=("Consolas", 11),
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda _e: self.update_index())
        self.search_entry.bind("<Return>", lambda _e: self._open_first_result())
        tk.Button(
            top,
            text="CLEAR",
            bg=COLORS["SURFACE_LIGHT"],
            fg=COLORS["TEXT"],
            relief="flat",
            activebackground=COLORS["SURFACE_LIGHT"],
            command=self._clear_search,
            font=("Segoe UI", 9, "bold"),
            padx=10,
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            top,
            text="COPY TOPIC",
            bg=COLORS["SURFACE_LIGHT"],
            fg=COLORS["TEXT"],
            relief="flat",
            activebackground=COLORS["SURFACE_LIGHT"],
            command=self.copy_current_topic,
            font=("Segoe UI", 9, "bold"),
            padx=10,
        ).pack(side="left", padx=(0, 16))

        body = tk.Frame(self.root, bg=COLORS["BG"])
        body.pack(fill="both", expand=True, padx=14, pady=(10, 8))

        left = tk.Frame(body, bg=COLORS["SURFACE"], width=330)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        tk.Label(
            left,
            text="TOPICS",
            bg=COLORS["SURFACE"],
            fg=COLORS["P1"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 6))
        idx_wrap = tk.Frame(left, bg=COLORS["SURFACE"])
        idx_wrap.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.idx_list = tk.Listbox(
            idx_wrap,
            bg=COLORS["SURFACE"],
            fg=COLORS["TEXT"],
            selectbackground=COLORS["P1"],
            selectforeground="black",
            borderwidth=0,
            highlightthickness=0,
            font=("Segoe UI", 10),
            activestyle="none",
        )
        self.idx_list.pack(side="left", fill="both", expand=True)
        idx_scroll = tk.Scrollbar(idx_wrap, orient="vertical", command=self.idx_list.yview)
        idx_scroll.pack(side="right", fill="y")
        self.idx_list.configure(yscrollcommand=idx_scroll.set)
        self.idx_list.bind("<<ListboxSelect>>", self.on_select)

        right = tk.Frame(body, bg=COLORS["SURFACE_LIGHT"])
        right.pack(side="left", fill="both", expand=True)
        text_wrap = tk.Frame(right, bg=COLORS["SURFACE_LIGHT"])
        text_wrap.pack(fill="both", expand=True, padx=1, pady=1)
        self.viewer = tk.Text(
            text_wrap,
            wrap="word",
            bg=COLORS["SURFACE_LIGHT"],
            fg=COLORS["TEXT"],
            borderwidth=0,
            highlightthickness=0,
            padx=20,
            pady=16,
            font=("Segoe UI", 11),
            insertbackground=COLORS["TEXT"],
        )
        self.viewer.pack(side="left", fill="both", expand=True)
        text_scroll = tk.Scrollbar(text_wrap, orient="vertical", command=self.viewer.yview)
        text_scroll.pack(side="right", fill="y")
        self.viewer.configure(yscrollcommand=text_scroll.set)
        self.viewer.tag_configure("header", font=("Segoe UI", 17, "bold"), foreground=COLORS["P1"])
        self.viewer.tag_configure("subheader", font=("Segoe UI", 12, "bold"), foreground=COLORS["SYS"])
        self.viewer.tag_configure("bullet", lmargin1=18, lmargin2=34)

        footer = tk.Frame(self.root, bg=COLORS["BG"])
        footer.pack(fill="x", padx=16, pady=(0, 10))
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(
            footer,
            textvariable=self.status_var,
            bg=COLORS["BG"],
            fg=COLORS["TEXT_DIM"],
            font=("Segoe UI", 9),
        ).pack(side="left")
        tk.Label(
            footer,
            text="Tip: Ctrl+F focuses search",
            bg=COLORS["BG"],
            fg=COLORS["TEXT_DIM"],
            font=("Segoe UI", 9),
        ).pack(side="right")
        self.root.bind("<Control-f>", lambda _e: self._focus_search())

    def _focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, tk.END)

    def _clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.update_index()
        self.status_var.set("Search cleared.")

    def _open_first_result(self):
        if not self.visible_topics:
            return
        self.display_topic(self.visible_topics[0])
        self.idx_list.selection_clear(0, tk.END)
        self.idx_list.selection_set(0)
        self.idx_list.activate(0)

    def update_index(self):
        query = self.search_entry.get().strip().lower()
        self.idx_list.delete(0, tk.END)
        self.visible_topics = []
        for topic, body in self.help_data.items():
            if not query or query in topic.lower() or query in body.lower():
                self.visible_topics.append(topic)
                self.idx_list.insert(tk.END, topic)
        if self.visible_topics:
            self.status_var.set(f"{len(self.visible_topics)} topic(s) found.")
        else:
            self.status_var.set("No matching topics.")

    def on_select(self, _evt=None):
        sel = self.idx_list.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(self.visible_topics):
            return
        self.display_topic(self.visible_topics[idx])

    def copy_current_topic(self):
        if not self.current_topic or self.current_topic not in self.help_data:
            self.status_var.set("No topic selected.")
            return
        payload = f"{self.current_topic}\n\n{self.help_data[self.current_topic]}"
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(payload)
            self.status_var.set(f"Copied: {self.current_topic}")
        except Exception:
            self.status_var.set("Clipboard copy failed.")

    def display_topic(self, topic):
        if topic not in self.help_data:
            return
        self.current_topic = topic
        body = self.help_data[topic]
        self.viewer.config(state="normal")
        self.viewer.delete("1.0", tk.END)
        self.viewer.insert("1.0", f"{topic}\n\n", "header")
        for raw_line in body.splitlines():
            line = raw_line.rstrip()
            if line.startswith("## "):
                self.viewer.insert(tk.END, line[3:] + "\n", "subheader")
            elif line.startswith("- "):
                self.viewer.insert(tk.END, line + "\n", "bullet")
            else:
                self.viewer.insert(tk.END, line + "\n")
        self.viewer.config(state="disabled")
        self.viewer.see("1.0")
        self.status_var.set(f"Viewing: {topic}")


if __name__ == "__main__":
    root = tk.Tk()
    ArcadeCommanderHelp(root)
    root.mainloop()
