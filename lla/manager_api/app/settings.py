import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


MANAGER_ROOT = Path(__file__).resolve().parent.parent
if load_dotenv is not None:
    load_dotenv(MANAGER_ROOT / ".env")


class Settings:
    def __init__(self):
        self.manager_root = MANAGER_ROOT
        self.project_root = self._resolve_project_root()
        self.bot_python_dir = self.project_root / "lla" / "python"
        self.state_path = self.manager_root / "manager_state.json"
        self.admin_token = os.getenv("DCBOT_ADMIN_TOKEN", "")
        self.allowed_bot_id = os.getenv("DCBOT_ALLOWED_BOT_ID", "").strip()

    def _resolve_project_root(self):
        raw_path = os.getenv("DCBOT_PROJECT_ROOT", "..\\..")
        path = Path(raw_path)
        if not path.is_absolute():
            path = MANAGER_ROOT / path

        return path.resolve()


settings = Settings()
