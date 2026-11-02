import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "decompyler"
CONFIG_FILE = CONFIG_DIR / "settings.toml"

TOOL_SUFFIX = ".exe" if os.name == "nt" else ""
DEFAULT_BIN_DIR = Path.home() / ".local" / "bin"

DEFAULT_SETTINGS = {
    "theme": "monokai",
    "font_family": "Monospace",
    "font_size": 15,
    "hide_stdlib": True,
    "pycdc_path": str(DEFAULT_BIN_DIR / f"pycdc{TOOL_SUFFIX}"),
    "pycdas_path": str(DEFAULT_BIN_DIR / f"pycdas{TOOL_SUFFIX}"),
}

BOOL_KEYS = {"hide_stdlib"}

def load_settings() -> dict:
    if not CONFIG_FILE.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        settings = DEFAULT_SETTINGS.copy()
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#") and not line.startswith("["):
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k in settings:
                        if k == "font_size":
                            settings[k] = int(v)
                        elif k in BOOL_KEYS:
                            settings[k] = v.lower() in ("1", "true", "yes", "on")
                        else:
                            settings[k] = v
        return settings
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("[appearance]\n")
            for k in ("theme", "font_family", "font_size"):
                v = settings[k]
                if isinstance(v, str):
                    f.write(f'{k} = "{v}"\n')
                else:
                    f.write(f"{k} = {v}\n")
            f.write(f"hide_stdlib = {'true' if settings['hide_stdlib'] else 'false'}\n")
            f.write("\n[paths]\n")
            for k in ("pycdc_path", "pycdas_path"):
                f.write(f'{k} = "{settings[k]}"\n')
    except Exception as e:
        if sys.stderr is not None:
            print(f"Error saving config: {e}", file=sys.stderr)
