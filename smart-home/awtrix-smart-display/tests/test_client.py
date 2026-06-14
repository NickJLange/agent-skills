import os
import tempfile
import json
from PIL import Image
from awtrix_display.client import resolve_sprite_path, process_gif_for_awtrix

def test_resolve_sprite_path():
    with tempfile.TemporaryDirectory() as temp_dir:
        sprites_json = [
            {"name": "Cecil (Paladin)", "game": "FFIV", "path": "sprites/cecil.gif"},
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
        assert resolve_sprite_path("nonexistent", temp_dir) is None

def test_process_gif_for_awtrix():
    img1 = Image.new("RGBA", (16, 24), (255, 0, 0, 255))
    img2 = Image.new("RGBA", (16, 24), (0, 255, 0, 255))
    
    img1.putpixel((5, 5), (0, 0, 255, 255))
    img2.putpixel((5, 5), (0, 0, 255, 255))
    
    with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
        img1.save(f, save_all=True, append_images=[img2], duration=100, loop=0)
        temp_gif = f.name
        
    try:
        frames, durations = process_gif_for_awtrix(temp_gif)
        
        assert len(frames) == 2
        assert len(durations) == 2
        assert durations == [100, 100]
        # Check active pixels in frames
        assert len(frames[0]) > 0
    finally:
        try:
            os.remove(temp_gif)
        except Exception:
            pass
