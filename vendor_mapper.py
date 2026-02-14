import argparse
import csv
import json
import os
import re
from app_paths import game_db_file, migrate_legacy_runtime_files

_TITLE_INDEX = {}
_CONFLICT_COUNT = 0

def normalize_title(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def build_title_index(csv_rows):
    index = {}
    for row in csv_rows:
        title = row.get("Game Name") or row.get("Game") or ""
        vendor = row.get("Developer") or row.get("Vendor") or row.get("Manufacturer")
        key = normalize_title(title)
        if not key or not vendor:
            continue
        if key in index and index[key] != vendor:
            print(f"[vendor_mapper] Warning: conflicting vendors for '{title}': '{index[key]}' vs '{vendor}'. Keeping first.")
            continue
        index[key] = vendor
    return index

def _best_effort_match(norm_title):
    global _CONFLICT_COUNT
    best_vendor = None
    best_score = None
    conflict = False
    for title_key, vendor in _TITLE_INDEX.items():
        if not title_key:
            continue
        if title_key == norm_title:
            return vendor
        if title_key in norm_title or norm_title in title_key:
            score = abs(len(title_key) - len(norm_title))
            if best_score is None or score < best_score:
                best_score = score
                best_vendor = vendor
                conflict = False
            elif score == best_score and vendor != best_vendor:
                conflict = True
    if conflict:
        _CONFLICT_COUNT += 1
        print(f"[vendor_mapper] Warning: multiple close matches for '{norm_title}'. Using '{best_vendor}'.")
    return best_vendor

def guess_vendor_for_rom(rom_key, rom_to_title_hint=None):
    if not _TITLE_INDEX:
        return None
    hint = rom_to_title_hint or rom_key
    norm = normalize_title(hint)
    if not norm:
        return None
    return _best_effort_match(norm)

def apply_vendors_to_db(db):
    global _CONFLICT_COUNT
    _CONFLICT_COUNT = 0
    updated = 0
    skipped = 0

    for rom, data in db.items():
        if not isinstance(data, dict):
            skipped += 1
            continue
        if data.get("vendor"):
            skipped += 1
            continue
        hint = data.get("full_name", rom)
        vendor = guess_vendor_for_rom(rom, hint)
        if vendor:
            data["vendor"] = vendor
            updated += 1
        else:
            skipped += 1

    stats = {"set": updated, "skipped": skipped, "conflicts": _CONFLICT_COUNT}
    return db, stats

def _load_csv_rows(path):
    rows = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"[vendor_mapper] Error reading CSV '{path}': {e}")
    return rows

def _load_db(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        print(f"[vendor_mapper] Error reading DB '{path}': {e}")
    return {}

def _write_db(path, db):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4)
        return True
    except Exception as e:
        print(f"[vendor_mapper] Error writing DB '{path}': {e}")
        return False

def main():
    migrate_legacy_runtime_files()
    parser = argparse.ArgumentParser(description="Vendor Mapper")
    parser.add_argument("--db", default=game_db_file(), help="Path to AC_GameData.json")
    parser.add_argument("--csv", default="Top100_Games.csv", help="Path to Top100_Games.csv")
    parser.add_argument("--write", action="store_true", help="Write updates to DB")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"[vendor_mapper] CSV not found: {args.csv}")
        return
    if not os.path.exists(args.db):
        print(f"[vendor_mapper] DB not found: {args.db}")
        return

    rows = _load_csv_rows(args.csv)
    if not rows:
        print("[vendor_mapper] No rows loaded from CSV.")
        return

    global _TITLE_INDEX
    _TITLE_INDEX = build_title_index(rows)
    if not _TITLE_INDEX:
        print("[vendor_mapper] No titles indexed from CSV.")
        return

    db = _load_db(args.db)
    if not db:
        print("[vendor_mapper] DB is empty or invalid.")
        return

    db, stats = apply_vendors_to_db(db)
    print(f"[vendor_mapper] Vendors set: {stats['set']}, skipped: {stats['skipped']}, conflicts: {stats['conflicts']}")

    if args.write:
        if _write_db(args.db, db):
            print("[vendor_mapper] DB updated.")

if __name__ == "__main__":
    main()
