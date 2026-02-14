import os
import shutil
import sys


def app_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


APP_ROOT = app_root()
DATA_DIR = os.path.join(APP_ROOT, "data")
CONFIG_DIR = os.path.join(DATA_DIR, "config")
GAMES_DIR = os.path.join(DATA_DIR, "games")
LIBRARY_DIR = os.path.join(DATA_DIR, "library")
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")
KEYMAP_DIR = os.path.join(DATA_DIR, "keymaps")


def settings_file() -> str:
    return os.path.join(CONFIG_DIR, "ac_settings.json")


def controller_config_file() -> str:
    return os.path.join(CONFIG_DIR, "controller_config.json")


def last_profile_file() -> str:
    return os.path.join(CONFIG_DIR, "last_profile.cfg")


def game_db_file() -> str:
    return os.path.join(GAMES_DIR, "AC_GameData.json")


def fx_library_file() -> str:
    return os.path.join(LIBRARY_DIR, "AC_FXLibrary.json")


def animation_library_file() -> str:
    return os.path.join(LIBRARY_DIR, "AC_AnimationLibrary.json")


def profile_file(name: str) -> str:
    return os.path.join(PROFILES_DIR, name)


def keymap_dir() -> str:
    return KEYMAP_DIR


def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, CONFIG_DIR, GAMES_DIR, LIBRARY_DIR, PROFILES_DIR, KEYMAP_DIR):
        os.makedirs(path, exist_ok=True)


def _move_if_needed(src: str, dst: str) -> None:
    if not os.path.exists(src):
        return
    if os.path.exists(dst):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)


def _merge_keymaps_legacy(legacy_dir: str, new_dir: str) -> None:
    if not os.path.isdir(legacy_dir):
        return
    os.makedirs(new_dir, exist_ok=True)
    for name in os.listdir(legacy_dir):
        src = os.path.join(legacy_dir, name)
        dst = os.path.join(new_dir, name)
        if os.path.isdir(src):
            continue
        if os.path.exists(dst):
            continue
        shutil.move(src, dst)
    try:
        if not os.listdir(legacy_dir):
            os.rmdir(legacy_dir)
    except Exception:
        pass


def migrate_legacy_runtime_files() -> None:
    ensure_runtime_dirs()
    legacy = {
        os.path.join(APP_ROOT, "ac_settings.json"): settings_file(),
        os.path.join(APP_ROOT, "controller_config.json"): controller_config_file(),
        os.path.join(APP_ROOT, "last_profile.cfg"): last_profile_file(),
        os.path.join(APP_ROOT, "AC_GameData.json"): game_db_file(),
        os.path.join(APP_ROOT, "AC_FXLibrary.json"): fx_library_file(),
        os.path.join(APP_ROOT, "AC_AnimationLibrary.json"): animation_library_file(),
        os.path.join(APP_ROOT, "default.json"): profile_file("default.json"),
        os.path.join(APP_ROOT, "Default.json"): profile_file("Default.json"),
    }
    for src, dst in legacy.items():
        _move_if_needed(src, dst)
    _merge_keymaps_legacy(os.path.join(APP_ROOT, "keymaps"), keymap_dir())
