ANIMATIONS = {
    # Core animation identifiers (shared)
    "RAINBOW": {
        "label": "Rainbow",
        "scopes": ["aclighter", "commander_preview"],
        "aliases": ["RAINBOW"],
    },
    "PULSE_RED": {
        "label": "Pulse Red",
        "scopes": ["aclighter", "commander_preview"],
        "aliases": ["PULSE_RED", "BREATH"],
    },
    "PULSE_BLUE": {
        "label": "Pulse Blue",
        "scopes": ["aclighter", "commander_preview"],
        "aliases": ["PULSE_BLUE", "FADE"],
    },
    "PULSE_GREEN": {
        "label": "Pulse Green",
        "scopes": ["aclighter", "commander_preview"],
        "aliases": ["PULSE_GREEN"],
    },
    "HYPER_STROBE": {
        "label": "Hyper Strobe",
        "scopes": ["aclighter", "commander_preview"],
        "aliases": ["HYPER_STROBE", "STROBE"],
    },
    "TEASE": {
        "label": "Tease",
        "scopes": ["commander_preview"],
        "aliases": ["TEASE"],
    },
    "ALL_OFF": {
        "label": "All Off",
        "scopes": ["commander_preview"],
        "aliases": ["ALL_OFF", "ALL OFF", "OFF"],
    },
    "PLASMA": {
        "label": "Plasma",
        "scopes": ["aclighter"],
        "aliases": ["PLASMA"],
    },
    # Commander-only previews (custom)
    "DEMOMODE": {
        "label": "DemoMode",
        "scopes": ["commander_preview"],
        "aliases": ["DEMOMODE", "DEMO_MODE"],
    },
    "BAZERK": {
        "label": "Bazerk",
        "scopes": ["commander_preview"],
        "aliases": ["BAZERK"],
    },
    # ALU emulator events
    "LAUNCH": {
        "label": "Launch",
        "scopes": ["alu_emulator"],
        "aliases": ["LAUNCH", "START"],
    },
    "PAUSE": {
        "label": "Pause",
        "scopes": ["alu_emulator"],
        "aliases": ["PAUSE"],
    },
    "STOP": {
        "label": "Stop",
        "scopes": ["alu_emulator"],
        "aliases": ["STOP", "GAME_OVER"],
    },
    "IDLE": {
        "label": "Idle",
        "scopes": ["alu_emulator"],
        "aliases": ["IDLE", "ATTRACT"],
    },
}


def resolve_animation(name):
    if not name:
        return None
    n = str(name).strip().upper()
    for key, data in ANIMATIONS.items():
        if n == key:
            return key
        for alias in data.get("aliases", []):
            if n == str(alias).strip().upper():
                return key
    return None


def list_supported(scope=None):
    if not scope:
        return list(ANIMATIONS.keys())
    return [k for k, v in ANIMATIONS.items() if scope in v.get("scopes", [])]


def list_aliases(key):
    data = ANIMATIONS.get(key, {})
    return list(data.get("aliases", []))
