import os
import tempfile
import json
from unittest.mock import patch
from PIL import Image
from awtrix_display.client import resolve_sprite_path, process_gif_for_awtrix, AwtrixClient

def test_resolve_sprite_path():
    with tempfile.TemporaryDirectory() as temp_dir:
        sprites_json = [
            {"name": "Cecil (Paladin)", "game": "FFIV", "path": "sprites/cecil.gif"},
            {"game": "Missing Name", "path": "sprites/missing_name.gif"},
            {"name": "Missing Path", "game": "FFVI"},
            "not a dictionary",
            {"name": "Terra", "game": "FFVI", "path": "sprites/terra.gif"}
        ]
        with open(os.path.join(temp_dir, "sprites.json"), "w") as f:
            json.dump(sprites_json, f)
            
        os.makedirs(os.path.join(temp_dir, "sprites"), exist_ok=True)
        
        cecil_path = os.path.join(temp_dir, "sprites/cecil.gif")
        terra_path = os.path.join(temp_dir, "sprites/terra.gif")
        open(cecil_path, "w").close()
        open(terra_path, "w").close()
        
        assert resolve_sprite_path("cecil", temp_dir) == cecil_path
        assert resolve_sprite_path("cecil_paladin", temp_dir) == cecil_path
        assert resolve_sprite_path("Terra", temp_dir) == terra_path
        assert resolve_sprite_path("Missing Name", temp_dir) is None
        assert resolve_sprite_path("Missing Path", temp_dir) is None
        assert resolve_sprite_path("nonexistent", temp_dir) is None

def test_process_gif_for_awtrix():
    img1 = Image.new("RGBA", (16, 24), (255, 0, 0, 255))
    img2 = Image.new("RGBA", (16, 24), (0, 255, 0, 255))
    
    img1.putpixel((5, 5), (0, 0, 255, 255))
    img2.putpixel((5, 5), (0, 0, 255, 255))
    
    temp_gif = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
            img1.save(f, save_all=True, append_images=[img2], duration=100, loop=0)
            temp_gif = f.name
        
        frames, durations = process_gif_for_awtrix(temp_gif)
        
        assert len(frames) == 2
        assert len(durations) == 2
        assert durations == [100, 100]
        # Check active pixels in frames
        assert len(frames[0]) > 0
    finally:
        if temp_gif:
            try:
                os.remove(temp_gif)
            except Exception:
                pass

def test_awtrix_client_input_coercion():
    client = AwtrixClient()
    with patch("urllib.request.urlopen") as mock_urlopen:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        
        assert client.set_power("localhost", "off") is True
        args, _ = mock_urlopen.call_args
        req = args[0]
        data = json.loads(req.data.decode("utf-8"))
        assert data["power"] is False
        
        assert client.set_power("localhost", "on") is True
        args, _ = mock_urlopen.call_args
        req = args[0]
        data = json.loads(req.data.decode("utf-8"))
        assert data["power"] is True
        
        assert client.set_power("localhost", False) is True
        args, _ = mock_urlopen.call_args
        req = args[0]
        data = json.loads(req.data.decode("utf-8"))
        assert data["power"] is False

def test_awtrix_client_url_encoding():
    client = AwtrixClient()
    with patch("urllib.request.urlopen") as mock_urlopen:
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        
        assert client.send_payload("localhost", "my custom app", {"test": 123}) is True
        args, _ = mock_urlopen.call_args
        req = args[0]
        assert "name=my%20custom%20app" in req.full_url
