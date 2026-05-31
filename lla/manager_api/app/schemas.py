from pydantic import BaseModel


class StatusResponse(BaseModel):
    ok: bool
    project_root: str
    bot_python_dir: str
    configured_admin_token: bool
    allowed_bot_id: str | None = None


class CommandInfo(BaseModel):
    name: str
    type: str
    description: str = ""
    extension: str


class ExtensionInfo(BaseModel):
    name: str
    loaded_by_entrypoint: bool
    enabled: bool
    path: str


class ToggleResponse(BaseModel):
    name: str
    enabled: bool
