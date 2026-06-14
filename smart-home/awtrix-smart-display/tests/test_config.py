import os
import tempfile
import json
from awtrix_display.config import load_config, resolve_device

def test_load_config_defaults():
    old_path = os.environ.get("AWTRIX_CONFIG_PATH")
    old_devices = os.environ.get("AWTRIX_DEVICES")
    old_sprites = os.environ.get("AWTRIX_SPRITES_DIR")
    
    if "AWTRIX_CONFIG_PATH" in os.environ: del os.environ["AWTRIX_CONFIG_PATH"]
    if "AWTRIX_DEVICES" in os.environ: del os.environ["AWTRIX_DEVICES"]
    if "AWTRIX_SPRITES_DIR" in os.environ: del os.environ["AWTRIX_SPRITES_DIR"]
    
    try:
        config = load_config()
        assert isinstance(config, dict)
        assert "devices" in config
        assert "default_text_color" in config
    finally:
        if old_path: os.environ["AWTRIX_CONFIG_PATH"] = old_path
        if old_devices: os.environ["AWTRIX_DEVICES"] = old_devices
        if old_sprites: os.environ["AWTRIX_SPRITES_DIR"] = old_sprites

def test_load_config_from_file_and_env():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "devices": {"testdev": "testval.local"},
            "sprites_dir": "/tmp/sprites",
            "default_text_color": "#FF0000"
        }, f)
        temp_name = f.name
        
    try:
        os.environ["AWTRIX_CONFIG_PATH"] = temp_name
        os.environ["AWTRIX_DEVICES"] = "envdev=envval.local"
        os.environ["AWTRIX_SPRITES_DIR"] = "/tmp/env_sprites"
        
        config = load_config()
        assert config["devices"]["testdev"] == "testval.local"
        assert config["devices"]["envdev"] == "envval.local"
        assert config["sprites_dir"] == "/tmp/env_sprites"
        assert config["default_text_color"] == "#FF0000"
        
        assert resolve_device("testdev", config) == "testval.local"
        assert resolve_device("envdev", config) == "envval.local"
        assert resolve_device("nonexistent", config) == "nonexistent"
    finally:
        try:
            os.remove(temp_name)
        except Exception:
            pass
        if "AWTRIX_CONFIG_PATH" in os.environ: del os.environ["AWTRIX_CONFIG_PATH"]
        if "AWTRIX_DEVICES" in os.environ: del os.environ["AWTRIX_DEVICES"]
        if "AWTRIX_SPRITES_DIR" in os.environ: del os.environ["AWTRIX_SPRITES_DIR"]
