import os
import json

def load_config():
    """
    Loads Awtrix display configuration from environment variables or local JSON config file.
    No secrets, paths, or IPs are hardcoded in the codebase.
    """
    config = {
        "devices": {},
        "sprites_dir": None,
        "default_text_color": "#00BCFF"
    }

    # 1. Try to read from JSON config file
    config_path = os.environ.get("AWTRIX_CONFIG_PATH")
    if not config_path:
        config_path = os.path.expanduser("~/.config/awtrix/config.json")
    else:
        config_path = os.path.expanduser(config_path)

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                file_config = json.load(f)
                if isinstance(file_config, dict):
                    if "devices" in file_config and isinstance(file_config["devices"], dict):
                        config["devices"].update(file_config["devices"])
                    if "sprites_dir" in file_config:
                        config["sprites_dir"] = file_config["sprites_dir"]
                    if "default_text_color" in file_config:
                        config["default_text_color"] = file_config["default_text_color"]
        except Exception:
            pass

    # 2. Environment variables override
    # AWTRIX_DEVICES can be "kitchen=awtrix-kitchen.local,office=awtrix-office.local"
    env_devices = os.environ.get("AWTRIX_DEVICES")
    if env_devices:
        parts = env_devices.split(",")
        for part in parts:
            if "=" in part:
                alias, endpoint = part.split("=", 1)
                config["devices"][alias.strip()] = endpoint.strip()
            else:
                config["devices"][part.strip()] = part.strip()

    env_sprites_dir = os.environ.get("AWTRIX_SPRITES_DIR")
    if env_sprites_dir:
        config["sprites_dir"] = env_sprites_dir

    return config

def resolve_device(device_name, config):
    """
    Resolves a device name (alias or FQDN/IP) using the config.
    Returns the resolved hostname/IP (e.g. 'awtrix-kitchen.local').
    """
    if device_name in config["devices"]:
        return config["devices"][device_name]
    return device_name
