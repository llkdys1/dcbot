import ast
from pathlib import Path


ENTRYPOINT_NAME = "lla-example"
IGNORED_MODULES = {"test"}


def _literal_string(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    return ""


def _decorator_call_name(decorator):
    if isinstance(decorator, ast.Call):
        decorator = decorator.func

    parts = []
    while isinstance(decorator, ast.Attribute):
        parts.append(decorator.attr)
        decorator = decorator.value

    if isinstance(decorator, ast.Name):
        parts.append(decorator.id)

    return ".".join(reversed(parts))


def _decorator_kwarg_string(decorator, key):
    if not isinstance(decorator, ast.Call):
        return ""

    for keyword in decorator.keywords:
        if keyword.arg == key:
            return _literal_string(keyword.value)

    return ""


def _first_docstring(node):
    docstring = ast.get_docstring(node)
    return docstring or ""


class ProjectScanner:
    def __init__(self, bot_python_dir: Path):
        self.bot_python_dir = bot_python_dir

    def list_extension_files(self):
        if not self.bot_python_dir.exists():
            return []

        return sorted(
            path
            for path in self.bot_python_dir.glob("*.py")
            if path.stem not in IGNORED_MODULES and path.stem != ENTRYPOINT_NAME
        )

    def list_loaded_extensions(self):
        entrypoint = self.bot_python_dir / f"{ENTRYPOINT_NAME}.py"
        if not entrypoint.exists():
            return set()

        tree = ast.parse(entrypoint.read_text(encoding="utf-8"))
        loaded = set()

        for node in ast.walk(tree):
            if not isinstance(node, ast.Await):
                continue

            call = node.value
            if not isinstance(call, ast.Call):
                continue

            if _decorator_call_name(call.func) != "self.load_extension":
                continue

            if call.args:
                extension_name = _literal_string(call.args[0])
                if extension_name:
                    loaded.add(extension_name)

        return loaded

    def list_extensions(self, state_store):
        loaded = self.list_loaded_extensions()
        extensions = []

        for path in self.list_extension_files():
            name = path.stem
            extensions.append(
                {
                    "name": name,
                    "loaded_by_entrypoint": name in loaded,
                    "enabled": state_store.extension_enabled(name),
                    "path": str(path),
                }
            )

        return extensions

    def list_commands(self):
        commands = []

        for path in self.list_extension_files() + [self.bot_python_dir / f"{ENTRYPOINT_NAME}.py"]:
            if not path.exists():
                continue

            tree = ast.parse(path.read_text(encoding="utf-8"))
            extension = path.stem

            for node in ast.walk(tree):
                if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                    continue

                for decorator in node.decorator_list:
                    decorator_name = _decorator_call_name(decorator)
                    command = self._command_from_decorator(
                        node,
                        decorator,
                        decorator_name,
                        extension,
                    )
                    if command is not None:
                        commands.append(command)

        return sorted(commands, key=lambda item: (item["type"], item["name"]))

    def _command_from_decorator(self, node, decorator, decorator_name, extension):
        if decorator_name.endswith("app_commands.command"):
            return {
                "name": _decorator_kwarg_string(decorator, "name") or node.name,
                "type": "slash",
                "description": _decorator_kwarg_string(decorator, "description"),
                "extension": extension,
            }

        if decorator_name.endswith("bot.command"):
            return {
                "name": _decorator_kwarg_string(decorator, "name") or node.name,
                "type": "prefix",
                "description": _first_docstring(node),
                "extension": extension,
            }

        if decorator_name.endswith("bot.hybrid_command"):
            return {
                "name": _decorator_kwarg_string(decorator, "name") or node.name,
                "type": "hybrid",
                "description": _first_docstring(node),
                "extension": extension,
            }

        if decorator_name.endswith("command"):
            return {
                "name": _decorator_kwarg_string(decorator, "name") or node.name,
                "type": "slash",
                "description": _decorator_kwarg_string(decorator, "description"),
                "extension": extension,
            }

        return None
