import json
import os
import uuid
from dataclasses import dataclass, asdict
from app_paths import fx_library_file, migrate_legacy_runtime_files


@dataclass
class FXEffect:
    fx_id: str
    name: str
    entrance: dict
    main: dict
    exit: dict
    audio_path: str = ""
    applied_to: list = None
    meta: dict = None

    def to_dict(self):
        data = asdict(self)
        if data.get("applied_to") is None:
            data["applied_to"] = []
        if data.get("meta") is None:
            data["meta"] = {}
        return data


class FXLibrary:
    """
    Simple JSON-backed FX library.
    Stores multi-state animation profiles with optional audio references.
    """

    def __init__(self, path=None):
        migrate_legacy_runtime_files()
        self.path = path or fx_library_file()
        self._db = {"fx": {}}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._db = json.load(f)
            except Exception:
                self._db = {"fx": {}}
        if "fx" not in self._db:
            self._db["fx"] = {}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._db, f, indent=2)

    def save_fx(self, effect):
        if isinstance(effect, FXEffect):
            data = effect.to_dict()
        else:
            data = dict(effect)
        fx_id = data.get("fx_id") or str(uuid.uuid4())
        data["fx_id"] = fx_id
        self._db["fx"][fx_id] = data
        self._save()
        return fx_id

    def get_fx_by_name(self, name):
        for fx in self._db["fx"].values():
            if fx.get("name", "").lower() == name.lower():
                return fx
        return None

    def get_fx_by_id(self, fx_id):
        return self._db["fx"].get(fx_id)

    def clone_fx(self, fx_id, new_name):
        src = self.get_fx_by_id(fx_id)
        if not src:
            return None
        cloned = dict(src)
        cloned["fx_id"] = str(uuid.uuid4())
        cloned["name"] = new_name
        self._db["fx"][cloned["fx_id"]] = cloned
        self._save()
        return cloned["fx_id"]
