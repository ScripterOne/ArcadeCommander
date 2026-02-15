#!/usr/bin/env python3
import json
import pathlib
import re
import urllib.parse
import urllib.request


DB_PATH = pathlib.Path("data/games/AC_GameData.json")
CATVER_URL = "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main/catver.ini/catver.ini"
ADB_URL_TMPL = "http://adb.arcadeitalia.net/dettaglio_mame.php?game_name={rom}"


def fetch_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=40) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_catver_categories(text: str) -> dict:
    out = {}
    in_cat = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_cat = line.lower() == "[category]"
            continue
        if not in_cat:
            continue
        if "=" not in line:
            continue
        rom, cat = line.split("=", 1)
        rom = rom.strip().lower()
        cat = cat.strip()
        if rom and cat:
            out[rom] = cat
    return out


def parse_adb_fields(html: str) -> dict:
    fields = {}
    m_title = re.search(r"<title>(.*?)\s*-\s*MAME machine</title>", html, flags=re.I | re.S)
    if m_title:
        fields["title"] = re.sub(r"\s+", " ", m_title.group(1)).strip()
    m_year = re.search(
        r"<div class=\"table_caption\">Year:\s*</div>\s*<div class=\"table_value\">\s*<span class=\"dettaglio\">([^<]+)</span>",
        html,
        flags=re.I | re.S,
    )
    if m_year:
        fields["year"] = m_year.group(1).strip()
    m_mfg = re.search(
        r"<div class=\"table_caption\">Manufacturer:\s*</div>\s*<div class=\"table_value\">\s*<span class=\"dettaglio\">([^<]+)</span>",
        html,
        flags=re.I | re.S,
    )
    if m_mfg:
        fields["manufacturer"] = m_mfg.group(1).strip()
    m_players = re.search(
        r"<div class=\"table_caption\">Players:\s*</div>\s*<div class=\"table_value\">\s*<span class=\"dettaglio\">([^<]+)</span>",
        html,
        flags=re.I | re.S,
    )
    if m_players:
        fields["players"] = m_players.group(1).strip()
    return fields


def build_description(title: str, year: str, manufacturer: str) -> str:
    title = str(title or "").strip()
    year = str(year or "").strip()
    manufacturer = str(manufacturer or "").strip()
    if title and year and manufacturer:
        return f"{title} is an arcade title released in {year} by {manufacturer}."
    if title and year:
        return f"{title} is an arcade title released in {year}."
    if title and manufacturer:
        return f"{title} is an arcade title by {manufacturer}."
    if title:
        return f"{title} is an arcade title."
    return ""


def main() -> int:
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    catver_text = fetch_text(CATVER_URL)
    cat_map = parse_catver_categories(catver_text)

    missing_meta = [
        k
        for k, v in db.items()
        if isinstance(v, dict) and not isinstance(v.get("metadata"), dict)
    ]

    filled_meta = 0
    filled_from_adb = 0
    filled_genre = 0

    for rom in missing_meta:
        entry = db.get(rom, {})
        if not isinstance(entry, dict):
            continue
        metadata = {}
        rom_l = str(rom).strip().lower()

        # Try ArcadeItalia per-ROM fallback first.
        try:
            url = ADB_URL_TMPL.format(rom=urllib.parse.quote(rom_l))
            html = fetch_text(url)
            adb_fields = parse_adb_fields(html)
            if adb_fields:
                metadata.update(adb_fields)
                metadata["source"] = "arcadeitalia_http"
                filled_from_adb += 1
        except Exception:
            pass

        # Add category as genre when available.
        cat = cat_map.get(rom_l, "").strip()
        if cat:
            metadata.setdefault("genre", cat)
            filled_genre += 1

        # If still empty, do not create metadata object.
        if not metadata:
            continue

        # Ensure at least a minimal description.
        metadata.setdefault(
            "description",
            build_description(
                metadata.get("title", ""),
                metadata.get("year", ""),
                metadata.get("manufacturer", ""),
            ),
        )
        if not metadata.get("description"):
            title_guess = rom.replace("_", " ").replace("-", " ").strip() or rom
            metadata["title"] = metadata.get("title", title_guess)
            metadata["description"] = f"{metadata['title']} metadata entry."
            metadata.setdefault("source", "fallback_local")

        entry["metadata"] = metadata
        db[rom] = entry
        filled_meta += 1

    # Backfill genre for existing metadata entries.
    backfill_genre = 0
    for rom, entry in db.items():
        if not isinstance(entry, dict):
            continue
        md = entry.get("metadata")
        if not isinstance(md, dict):
            continue
        if str(md.get("genre", "")).strip():
            continue
        cat = cat_map.get(str(rom).strip().lower(), "").strip()
        if cat:
            md["genre"] = cat
            backfill_genre += 1
            entry["metadata"] = md
            db[rom] = entry

    DB_PATH.write_text(json.dumps(db, indent=4) + "\n", encoding="utf-8")
    print(f"Missing metadata before pass: {len(missing_meta)}")
    print(f"Entries filled in this pass: {filled_meta}")
    print(f"Entries with ArcadeItalia fields: {filled_from_adb}")
    print(f"Genre set on new entries: {filled_genre}")
    print(f"Genre backfilled on existing metadata: {backfill_genre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
