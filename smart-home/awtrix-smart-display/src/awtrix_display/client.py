import os
import json
import urllib.request
import urllib.parse
import io
from PIL import Image, ImageSequence

class AwtrixClient:
    def __init__(self, default_color="#00BCFF"):
        self.default_color = default_color

    def send_payload(self, target, app_name, payload):
        """Sends payload to Awtrix custom app API."""
        if not target.startswith("http"):
            url = f"http://{target}"
        else:
            url = target

        endpoint = f"{url}/api/custom?name={urllib.parse.quote(app_name, safe='')}"
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as response:
                return response.status == 200
        except Exception:
            return False

    def delete_app(self, target, app_name):
        """Deletes a custom app scene by sending empty JSON."""
        return self.send_payload(target, app_name, {})

    def send_text(self, target, text, color=None, app_name="notify"):
        """Sends a simple text update to Awtrix."""
        payload = {
            "text": text,
            "color": color or self.default_color
        }
        return self.send_payload(target, app_name, payload)

    def set_power(self, target, state):
        """Toggles the matrix power (state is True/on or False/off)."""
        if not target.startswith("http"):
            url = f"http://{target}"
        else:
            url = target

        if isinstance(state, str):
            is_on = state.lower() not in ("off", "false", "0")
        else:
            is_on = bool(state)

        endpoint = f"{url}/api/power"
        payload = {"power": is_on}
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as response:
                return response.status == 200
        except Exception:
            return False


def resolve_sprite_path(source, sprites_dir):
    """
    Resolves a sprite name (e.g. 'cecil' or 'rydia_child') or direct path.
    Looks up in sprites.json if sprites_dir is provided.
    """
    if not sprites_dir or not os.path.exists(sprites_dir):
        if os.path.exists(source):
            return source
        return None

    # Try loading sprites.json catalog
    sprites_json_path = os.path.join(sprites_dir, "sprites.json")
    if os.path.exists(sprites_json_path):
        try:
            with open(sprites_json_path, "r") as f:
                catalog = json.load(f)
                search_name = source.lower().replace(" ", "_").replace("(", "").replace(")", "")
                for char in catalog:
                    if not isinstance(char, dict):
                        continue
                    name = char.get("name")
                    path = char.get("path")
                    if not name or not path:
                        continue
                    char_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "")
                    if (char_name == search_name or 
                        path.lower().endswith(f"/{search_name}.gif") or 
                        path.lower() == f"sprites/{search_name}.gif"):
                        full_path = os.path.join(sprites_dir, path)
                        if os.path.exists(full_path):
                            return full_path
        except Exception:
            pass

    # Fallbacks
    direct_join = os.path.join(sprites_dir, source)
    if os.path.exists(direct_join):
        return direct_join
    if os.path.exists(source):
        return source
    return None


def process_gif_for_awtrix(gif_path):
    """
    Processes a character walking GIF using the pixel-perfect integer-scale padding algorithm.
    Returns: (scaled_frames, durations)
    """
    try:
        with open(gif_path, "rb") as f:
            gif_data = f.read()
        gif_img = Image.open(io.BytesIO(gif_data))
    except Exception as e:
        raise ValueError(f"Failed to read/parse GIF at {gif_path}: {e}")

    # 1. Compute union bounding box across all frames
    union_bbox = None
    for frame in ImageSequence.Iterator(gif_img):
        frame_rgba = frame.convert("RGBA")
        width, height = frame_rgba.size
        rgba_data = list(frame_rgba.getdata())
        mask_data = []
        for p in rgba_data:
            r, g, b, a = p
            mask_data.append(255 if a > 50 else 0)
        
        mask = Image.new("L", (width, height))
        mask.putdata(mask_data)
        bbox = mask.getbbox()
        if bbox:
            if union_bbox is None:
                union_bbox = list(bbox)
            else:
                union_bbox[0] = min(union_bbox[0], bbox[0])
                union_bbox[1] = min(union_bbox[1], bbox[1])
                union_bbox[2] = max(union_bbox[2], bbox[2])
                union_bbox[3] = max(union_bbox[3], bbox[3])

    scaled_frames = []
    durations = []

    for frame in ImageSequence.Iterator(gif_img):
        dur = frame.info.get('duration', 100)
        if dur <= 0:
            dur = 100
        durations.append(dur)

        frame_rgba = frame.convert("RGBA")
        if union_bbox:
            frame_cropped = frame_rgba.crop(union_bbox)
        else:
            frame_cropped = frame_rgba

        crop_w, crop_h = frame_cropped.size
        if crop_h > 0 and crop_w > 0:
            N = max(1, (crop_h + 7) // 8)
            padded_h = N * 8
            padded_w = ((crop_w + N - 1) // N) * N
            
            padded_img = Image.new("RGBA", (padded_w, padded_h), (0, 0, 0, 0))
            y_offset = padded_h - crop_h
            x_offset = (padded_w - crop_w) // 2
            
            padded_img.paste(frame_cropped, (x_offset, y_offset))
            
            fw = padded_w // N
            fh = 8
            img_processed = padded_img.resize((fw, fh), Image.Resampling.NEAREST)
        else:
            fw, fh = 8, 8
            img_processed = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))

        # Convert to list of active pixels (x, y, color)
        active_pixels = []
        cur_w, cur_h = img_processed.size
        for y in range(cur_h):
            for x in range(cur_w):
                r, g, b, a = img_processed.getpixel((x, y))
                if a > 50:
                    hex_color = f"#{r:02X}{g:02X}{b:02X}"
                    active_pixels.append((x, y, hex_color))
        scaled_frames.append(active_pixels)

    return scaled_frames, durations
