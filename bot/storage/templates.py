"""Template storage (JSON on disk, atomic writes)."""
import json
import os
import re
from pathlib import Path
from typing import Optional

TEMPLATE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _\-]{0,39}$")


class TemplateStore:
    """Saves templates to a JSON file. Writes are atomic."""

    def __init__(self, path: Path):
        self.path = path
        self.templates: dict[str, dict] = {}   # key = lowercase name
        self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                self.templates = json.load(f)
        except FileNotFoundError:
            return
        except (json.JSONDecodeError, OSError) as e:
            # Don't silently overwrite a damaged file: keep a copy and start fresh.
            print(f"TemplateStore: could not read {self.path}: {e!r}")
            try:
                os.replace(self.path, self.path.with_suffix(".json.bak"))
            except OSError:
                pass

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.templates, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def get(self, name: str) -> Optional[dict]:
        return self.templates.get(name.strip().lower())

    def save(self, name: str, data: dict):
        self.templates[name.strip().lower()] = {"name": name.strip(), **data}
        self._save()

    def delete(self, name: str) -> bool:
        if self.templates.pop(name.strip().lower(), None) is None:
            return False
        self._save()
        return True


class TemplateStores:
    """One TemplateStore per server: data/<guild_id>/templates.json. Created on first use."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._stores: dict[int, TemplateStore] = {}

    def get(self, guild_id: int) -> TemplateStore:
        if guild_id not in self._stores:
            self._stores[guild_id] = TemplateStore(self.base_dir / str(guild_id) / "templates.json")
        return self._stores[guild_id]
