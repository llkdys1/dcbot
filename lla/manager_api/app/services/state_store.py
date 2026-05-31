import json
from pathlib import Path


class StateStore:
    def __init__(self, state_path: Path):
        self.state_path = state_path

    def load(self):
        if not self.state_path.exists():
            return {"extensions": {}}

        try:
            with self.state_path.open("r", encoding="utf-8") as state_file:
                data = json.load(state_file)
        except (json.JSONDecodeError, OSError):
            return {"extensions": {}}

        if not isinstance(data, dict):
            return {"extensions": {}}

        data.setdefault("extensions", {})
        return data

    def save(self, data):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as state_file:
            json.dump(data, state_file, ensure_ascii=False, indent=2)
            state_file.write("\n")

    def extension_enabled(self, name):
        data = self.load()
        extension = data.get("extensions", {}).get(name, {})
        return bool(extension.get("enabled", True))

    def set_extension_enabled(self, name, enabled):
        data = self.load()
        extensions = data.setdefault("extensions", {})
        extension = extensions.setdefault(name, {})
        extension["enabled"] = bool(enabled)
        self.save(data)
        return extension["enabled"]
