import os
import tempfile
import json
from contextlib import contextmanager
from awtrix_display.config import load_config, resolve_device

@contextmanager
def patch_env(new_env):
    """Temporarily modifies environment variables and restores them afterwards."""
    orig_env = {}
    for k in new_env:
        orig_env[k] = os.environ.get(k)
        
    for k, v in new_env.items():
        if v is None:
            if k in os.environ:
                del os.environ[k]
        else:
            os.environ[k] = v
    try:
        yield
    finally:
        for k, v in orig_env.items():
            if v is None:
                if k in os.environ:
                    del os.environ[k]
            else:
                os.environ[k] = v

def test_load_config_defaults():
    with patch_env({
        "AWTRIX_CONFIG_PATH": None,
        "AWTRIX_DEVICES": None,
        "AWTRIX_SPRITES_DIR": None,
    }):
        config = load_config()
        assert isinstance(config, dict)
        assert "devices" in config
        assert "default_text_color" in config

def test_load_config_from_file_and_env():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({
            "devices": {"testdev": "testval.local"},
            "sprites_dir": "/tmp/sprites",
            "default_text_color": "#FF0000"
        }, f)
        temp_name = f.name
        
    try:
        with patch_env({
            "AWTRIX_CONFIG_PATH": temp_name,
            "AWTRIX_DEVICES": "envdev=envval.local",
            "AWTRIX_SPRITES_DIR": "/tmp/env_sprites",
        }):
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

def test_load_config_malformed_and_edge_cases():
    # 1. Malformed JSON
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{invalid-json}")
        temp_name = f.name
    try:
        with patch_env({
            "AWTRIX_CONFIG_PATH": temp_name,
            "AWTRIX_DEVICES": None,
            "AWTRIX_SPRITES_DIR": None,
        }):
            config = load_config()
            assert isinstance(config, dict)
            assert "devices" in config
    finally:
        try:
            os.remove(temp_name)
        except Exception:
            pass

    # 2. Blank and edge-case env variable entries
    with patch_env({
        "AWTRIX_CONFIG_PATH": None,
        "AWTRIX_DEVICES": ",,kitchen=192.168.1.100,,office=192.168.1.101,,",
        "AWTRIX_SPRITES_DIR": None,
    }):
        config = load_config()
        assert "kitchen" in config["devices"]
        assert "office" in config["devices"]
        assert "" not in config["devices"]
        assert None not in config["devices"]
        assert len(config["devices"]) == 2
