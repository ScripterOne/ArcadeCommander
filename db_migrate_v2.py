import argparse
import csv
import datetime
import json
import os
import re
import shutil
import sys
from app_paths import game_db_file, migrate_legacy_runtime_files


ARCADE_TOKENS = ("arcade", "mame")
XBOX_TOKENS = ("xbox", "xinput")
GAMEPAD_TOKENS = (
    "playstation",
    "ps1",
    "ps2",
    "ps3",
    "ps4",
    "ps5",
    "switch",
    "nintendo",
    "pc",
    "steam",
    "windows",
    "linux",
    "mac",
)


def normalize_title(value):
    if not value:
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv_index(path):
    rows = []
    title_index = {}
    if not path:
        return rows, title_index
    if not os.path.exists(path):
        print(f"[warn] CSV not found: {path}")
        return rows, title_index

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
                title = (
                    row.get("Game Name")
                    or row.get("Title")
                    or row.get("Game")
                    or row.get("Name")
                    or ""
                )
                norm = normalize_title(title)
                if norm and norm not in title_index:
                    title_index[norm] = row
    except Exception as exc:
        print(f"[warn] Failed to read CSV '{path}': {exc}")
    return rows, title_index


def infer_mode_from_csv_row(row):
    if not isinstance(row, dict):
        return None
    text = " ".join(
        [
            str(row.get("Recommended Platform") or ""),
            str(row.get("Platforms") or ""),
            str(row.get("Platform") or ""),
            str(row.get("Emulator") or ""),
        ]
    ).lower()

    if any(tok in text for tok in ARCADE_TOKENS):
        return "ARCADE_PANEL"
    if any(tok in text for tok in XBOX_TOKENS):
        return "XINPUT_XBOX"
    if any(tok in text for tok in GAMEPAD_TOKENS):
        return "GAMEPAD_GENERIC"
    return None


def find_csv_match(entry_key, entry_value, title_index):
    if not title_index:
        return None

    candidates = []
    if isinstance(entry_value, dict):
        candidates.extend(
            [
                entry_value.get("game_name"),
                entry_value.get("full_name"),
                entry_value.get("title"),
                entry_value.get("name"),
            ]
        )
    candidates.append(entry_key)

    for candidate in candidates:
        norm = normalize_title(candidate)
        if norm and norm in title_index:
            return title_index[norm]
    return None


def migrate_db(db, defaults, csv_title_index):
    if not isinstance(db, dict):
        raise ValueError("Top-level JSON must be an object/dict of game entries.")

    stats = {
        "total_entries": 0,
        "profiles_added": 0,
        "controller_mode_inferred": 0,
        "controller_mode_defaulted": 0,
        "already_compliant": 0,
    }

    migrated = {}

    for key, value in db.items():
        stats["total_entries"] += 1
        modified = False

        if not isinstance(value, dict):
            value = {"legacy_value": value}
            modified = True

        profile = value.get("profile")
        if not isinstance(profile, dict):
            profile = {}
            value["profile"] = profile
            stats["profiles_added"] += 1
            modified = True

        if "controller_mode" not in profile:
            inferred = None
            row = find_csv_match(key, value, csv_title_index)
            if row is not None:
                inferred = infer_mode_from_csv_row(row)
            if inferred:
                profile["controller_mode"] = inferred
                stats["controller_mode_inferred"] += 1
            else:
                profile["controller_mode"] = defaults["controller_mode"]
                stats["controller_mode_defaulted"] += 1
            modified = True

        if "lighting_policy" not in profile:
            profile["lighting_policy"] = defaults["lighting_policy"]
            modified = True

        if "default_fx" not in profile:
            profile["default_fx"] = defaults["default_fx"]
            modified = True

        if not modified:
            stats["already_compliant"] += 1

        migrated[key] = value

    return migrated, stats


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def maybe_backup_inplace(path):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.bak_{stamp}"
    shutil.copy2(path, backup_path)
    return backup_path


def parse_args():
    migrate_legacy_runtime_files()
    parser = argparse.ArgumentParser(description="Migrate AC_GameData.json to V2 profile schema.")
    parser.add_argument("--in", dest="in_path", default=game_db_file(), help="Input DB path")
    parser.add_argument("--out", dest="out_path", default=None, help="Output DB path")
    parser.add_argument("--write", action="store_true", help="Write in-place to --in when --out is not provided")
    parser.add_argument("--csv", dest="csv_path", default=None, help="Optional Top100_Games.csv path")
    parser.add_argument("--default-mode", dest="default_mode", default="ARCADE_PANEL", help="Default controller_mode")
    parser.add_argument("--default-policy", dest="default_policy", default="AUTO", help="Default lighting_policy")
    parser.add_argument("--default-fx", dest="default_fx", default="", help="Default default_fx")
    return parser.parse_args()


def main():
    args = parse_args()

    if not os.path.exists(args.in_path):
        print(f"[error] Input DB not found: {args.in_path}")
        return 1

    try:
        db = load_json(args.in_path)
    except Exception as exc:
        print(f"[error] Failed to read DB '{args.in_path}': {exc}")
        return 1

    _, csv_title_index = load_csv_index(args.csv_path)

    defaults = {
        "controller_mode": args.default_mode,
        "lighting_policy": args.default_policy,
        "default_fx": args.default_fx,
    }

    try:
        migrated, stats = migrate_db(db, defaults, csv_title_index)
    except Exception as exc:
        print(f"[error] Migration failed: {exc}")
        return 1

    dry_run = not args.out_path and not args.write

    print("Migration Summary")
    print(f"  total entries: {stats['total_entries']}")
    print(f"  profiles added: {stats['profiles_added']}")
    print(f"  controller_mode inferred: {stats['controller_mode_inferred']}")
    print(f"  already compliant: {stats['already_compliant']}")

    if dry_run:
        print("  mode: dry-run (no file written)")
        return 0

    out_path = args.out_path if args.out_path else args.in_path

    if not args.out_path and args.write:
        try:
            backup_path = maybe_backup_inplace(args.in_path)
            print(f"  backup created: {backup_path}")
        except Exception as exc:
            print(f"[error] Failed to create backup: {exc}")
            return 1

    try:
        write_json(out_path, migrated)
        print(f"  wrote: {out_path}")
    except Exception as exc:
        print(f"[error] Failed to write output '{out_path}': {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
