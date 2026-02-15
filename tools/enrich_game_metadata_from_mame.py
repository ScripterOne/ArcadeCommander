#!/usr/bin/env python3
import argparse
import json
import pathlib
import urllib.request
import xml.etree.ElementTree as ET


MAME2003_PLUS_XML_URL = (
    "https://raw.githubusercontent.com/libretro/mame2003-plus-libretro/master/metadata/mame2003-plus.xml"
)
FBNEO_XML_URL = (
    "https://raw.githubusercontent.com/libretro/FBNeo/master/dats/FinalBurn%20Neo%20%28ClrMame%20Pro%20XML%2C%20Arcade%20only%29.dat"
)


def load_json(path: pathlib.Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: pathlib.Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def fetch_xml(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def build_index(xml_text: str, source_name: str) -> dict:
    root = ET.fromstring(xml_text)
    index = {}
    for game in root.findall("game"):
        rom = game.attrib.get("name", "").strip().lower()
        if not rom:
            continue
        desc = (game.findtext("description") or "").strip()
        year = (game.findtext("year") or "").strip()
        manufacturer = (game.findtext("manufacturer") or "").strip()
        input_node = game.find("input")
        players = ""
        input_buttons = ""
        input_control = ""
        input_ways = ""
        if input_node is not None:
            players = (input_node.attrib.get("players") or "").strip()
            input_buttons = (input_node.attrib.get("buttons") or "").strip()
            input_control = (input_node.attrib.get("control") or "").strip()
            input_ways = (input_node.attrib.get("ways") or "").strip()
        index[rom] = {
            "title": desc,
            "year": year,
            "manufacturer": manufacturer,
            "players": players,
            "input_buttons": input_buttons,
            "input_control": input_control,
            "input_ways": input_ways,
            "source": source_name,
        }
    return index


def _pick_genre(entry: dict) -> str:
    if not isinstance(entry, dict):
        return ""
    for container_key in ("catalog_override", "catalog_base", "catalog"):
        container = entry.get(container_key)
        if isinstance(container, dict):
            genre = str(container.get("genre", "")).strip()
            if genre:
                return genre
    return ""


def _build_short_description(title: str, year: str, manufacturer: str) -> str:
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
    parser = argparse.ArgumentParser(description="Enrich AC_GameData.json with ROM metadata from MAME2003+ XML.")
    parser.add_argument(
        "--db",
        default="data/games/AC_GameData.json",
        help="Path to AC game database JSON.",
    )
    parser.add_argument(
        "--xml-url",
        default=MAME2003_PLUS_XML_URL,
        help="Primary metadata XML URL.",
    )
    parser.add_argument(
        "--fallback-xml-url",
        default=FBNEO_XML_URL,
        help="Fallback metadata XML URL.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite non-empty metadata fields if already present.",
    )
    args = parser.parse_args()

    db_path = pathlib.Path(args.db)
    db = load_json(db_path)
    primary_xml = fetch_xml(args.xml_url)
    fallback_xml = fetch_xml(args.fallback_xml_url)
    index_primary = build_index(primary_xml, "libretro_mame2003plus")
    index_fallback = build_index(fallback_xml, "libretro_fbneo")

    scanned = 0
    matched = 0
    updated_entries = 0

    for rom_key, entry in db.items():
        if not isinstance(entry, dict):
            continue
        scanned += 1
        rom = str(rom_key).strip().lower()
        meta_src = index_primary.get(rom) or index_fallback.get(rom)
        if meta_src:
            matched += 1
        metadata = entry.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        before = dict(metadata)
        if meta_src:
            for field in (
                "title",
                "year",
                "manufacturer",
                "players",
                "input_buttons",
                "input_control",
                "input_ways",
                "source",
            ):
                incoming = str(meta_src.get(field, "")).strip()
                existing = str(metadata.get(field, "")).strip()
                if not incoming:
                    continue
                if args.overwrite or not existing:
                    metadata[field] = incoming

        genre_incoming = _pick_genre(entry)
        if genre_incoming:
            genre_existing = str(metadata.get("genre", "")).strip()
            if args.overwrite or not genre_existing:
                metadata["genre"] = genre_incoming

        # Always attempt to add a short summary if missing (or overwrite requested).
        desc_existing = str(metadata.get("description", "")).strip()
        desc_incoming = _build_short_description(
            metadata.get("title", ""),
            metadata.get("year", ""),
            metadata.get("manufacturer", ""),
        )
        if desc_incoming and (args.overwrite or not desc_existing):
            metadata["description"] = desc_incoming

        if metadata != before:
            updated_entries += 1
            entry["metadata"] = metadata
            db[rom_key] = entry

    save_json(db_path, db)
    print(f"Scanned: {scanned}")
    print(f"Matched ROMs: {matched}")
    print(f"Entries updated: {updated_entries}")
    print(f"DB: {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
