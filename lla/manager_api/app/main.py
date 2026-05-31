from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import CommandInfo, ExtensionInfo, StatusResponse, ToggleResponse
from app.security import require_admin_token
from app.services.project_scanner import ProjectScanner
from app.services.state_store import StateStore
from app.settings import settings


app = FastAPI(
    title="DCBOT Manager API",
    version="0.1.0",
    description="HTTP management API scaffold for DCBOT.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

scanner = ProjectScanner(settings.bot_python_dir)
state_store = StateStore(settings.state_path)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get(
    "/api/status",
    response_model=StatusResponse,
    dependencies=[Depends(require_admin_token)],
)
async def status():
    return StatusResponse(
        ok=True,
        project_root=str(settings.project_root),
        bot_python_dir=str(settings.bot_python_dir),
        configured_admin_token=bool(settings.admin_token),
        allowed_bot_id=settings.allowed_bot_id or None,
    )


@app.get(
    "/api/commands",
    response_model=list[CommandInfo],
    dependencies=[Depends(require_admin_token)],
)
async def commands():
    return scanner.list_commands()


@app.get(
    "/api/extensions",
    response_model=list[ExtensionInfo],
    dependencies=[Depends(require_admin_token)],
)
async def extensions():
    return scanner.list_extensions(state_store)


@app.post(
    "/api/extensions/{name}/enable",
    response_model=ToggleResponse,
    dependencies=[Depends(require_admin_token)],
)
async def enable_extension(name: str):
    enabled = state_store.set_extension_enabled(name, True)
    return ToggleResponse(name=name, enabled=enabled)


@app.post(
    "/api/extensions/{name}/disable",
    response_model=ToggleResponse,
    dependencies=[Depends(require_admin_token)],
)
async def disable_extension(name: str):
    enabled = state_store.set_extension_enabled(name, False)
    return ToggleResponse(name=name, enabled=enabled)
