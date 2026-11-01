import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "decompyler"
CONFIG_FILE = CONFIG_DIR / "settings.toml"

DEFAULT_SETTINGS = {
    "theme": "monokai",
    "font_family": "Monospace",
    "font_size": 15
}

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
            for k, v in settings.items():
                if isinstance(v, str):
                    f.write(f'{k} = "{v}"\n')
                else:
                    f.write(f"{k} = {v}\n")
    except Exception as e:
        if sys.stderr is not None:
            print(f"Error saving config: {e}", file=sys.stderr)
