import sys
import os
import argparse
import signal
import time
import subprocess
import json
from awtrix_display.config import load_config, resolve_device
from awtrix_display.client import AwtrixClient, resolve_sprite_path, process_gif_for_awtrix

def check_process_running(pid):
    """Checks if a process with pid is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def handle_stream(args, config):
    action = args.action
    pid_dir = os.path.expanduser("~/.config/awtrix")
    os.makedirs(pid_dir, exist_ok=True)
    pid_path = os.path.join(pid_dir, "streamer.pid")
    log_path = os.path.join(pid_dir, "streamer.log")

    if action == "status":
        if os.path.exists(pid_path):
            try:
                with open(pid_path, "r") as f:
                    pid = int(f.read().strip())
                if check_process_running(pid):
                    print(f"Awtrix background streamer is RUNNING (PID: {pid}).")
                    print(f"Logs: {log_path}")
                    return 0
            except ValueError:
                pass
        print("Awtrix background streamer is STOPPED.")
        return 0

    elif action == "stop":
        if os.path.exists(pid_path):
            try:
                with open(pid_path, "r") as f:
                    pid = int(f.read().strip())
                if check_process_running(pid):
                    print(f"Stopping Awtrix background streamer (PID: {pid})...")
                    os.kill(pid, signal.SIGTERM)
                    # Wait up to 3s for termination
                    for _ in range(30):
                        if not check_process_running(pid):
                            break
                        time.sleep(0.1)
                else:
                    print("Streamer process was already stopped.")
            except Exception as e:
                print(f"Error stopping process: {e}")
            finally:
                if os.path.exists(pid_path):
                    os.remove(pid_path)
        else:
            print("No active streamer PID file found.")

        # Delete edge_scene app on devices
        client = AwtrixClient()
        devices = args.devices or ",".join(config["devices"].values())
        for dev_name in devices.split(","):
            resolved = resolve_device(dev_name.strip(), config)
            if resolved:
                client.delete_app(resolved, "edge_scene")
        print("Streamer stopped and screens cleared.")
        return 0

    elif action == "start":
        if os.path.exists(pid_path):
            try:
                with open(pid_path, "r") as f:
                    pid = int(f.read().strip())
                if check_process_running(pid):
                    print(f"Streamer is already running (PID: {pid}). Stop it first.")
                    return 1
            except ValueError:
                pass

        # Resolve script path
        script_path = os.environ.get("AWTRIX_ANIMATE_SCRIPT")
        if not script_path:
            lookup_paths = [
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../mkulanzi/client/awtrix_animate.py")),
                "/Users/njl/dev/src/mkulanzi/client/awtrix_animate.py"
            ]
            for p in lookup_paths:
                if os.path.exists(p):
                    script_path = p
                    break
        if not script_path or not os.path.exists(script_path):
            print("Error: Could not locate awtrix_animate.py streamer script.")
            print("Please set AWTRIX_ANIMATE_SCRIPT env variable pointing to it.")
            return 1

        # Resolve devices & sprites dir
        devices = args.devices
        if not devices:
            devices = ",".join(config["devices"].values())
        if not devices:
            print("Error: No devices specified and none configured in config.json.")
            return 1

        sprites_dir = args.sprites_dir or config["sprites_dir"]
        if not sprites_dir or not os.path.exists(sprites_dir):
            print(f"Error: Sprites directory '{sprites_dir}' does not exist.")
            return 1

        print(f"Starting Awtrix background streamer...")
        print(f"Devices: {devices}")
        print(f"Sprites: {sprites_dir}")
        print(f"Logs: {log_path}")

        # Run process
        cmd = [sys.executable, script_path, "-d", devices, "--sprites-dir", sprites_dir]
        try:
            with open(log_path, "a") as log_file:
                p = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
            with open(pid_path, "w") as f:
                f.write(str(p.pid))
            print(f"Streamer successfully launched (PID: {p.pid}).")
            return 0
        except Exception as e:
            print(f"Error spawning streamer: {e}")
            return 1

def handle_notify(args, config):
    device = resolve_device(args.device, config)
    text = args.text
    color = args.color or config.get("default_text_color") or "#00BCFF"
    duration = args.duration
    sprite = args.sprite

    client = AwtrixClient()

    if not sprite:
        print(f"Sending text notification to {args.device}...")
        success = client.send_text(device, text, color, app_name="notify")
        if success:
            time.sleep(duration)
            client.delete_app(device, "notify")
        return 0 if success else 1

    sprites_dir = config["sprites_dir"]
    sprite_path = resolve_sprite_path(sprite, sprites_dir)
    if not sprite_path:
        print(f"Error: Sprite '{sprite}' could not be resolved in directory '{sprites_dir}'.")
        return 1

    try:
        scaled_frames, durations = process_gif_for_awtrix(sprite_path)
    except Exception as e:
        print(f"Error processing sprite: {e}")
        return 1

    fw = len(scaled_frames[0]) if scaled_frames else 8
    if scaled_frames and scaled_frames[0]:
        max_x = max(p[0] for p in scaled_frames[0])
        fw = max_x + 1

    print(f"Streaming animated notification to {args.device} for {duration}s...")
    start_time = time.time()
    frame_idx = 0
    success = True

    try:
        while time.time() - start_time < duration:
            frame_start = time.time()
            pixels = scaled_frames[frame_idx]

            draw_list = []
            for px, py, p_color in pixels:
                draw_list.append({"dp": [px, py, p_color]})

            payload = {
                "draw": draw_list,
                "text": text,
                "textX": fw + 2,
                "color": color
            }

            if not client.send_payload(device, "notify", payload):
                success = False
                break

            frame_duration = durations[frame_idx] / 1000.0
            elapsed = time.time() - frame_start
            sleep_time = frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

            frame_idx = (frame_idx + 1) % len(scaled_frames)
    finally:
        client.delete_app(device, "notify")

    return 0 if success else 1

def handle_text(args, config):
    device = resolve_device(args.device, config)
    color = args.color or config.get("default_text_color") or "#00BCFF"
    client = AwtrixClient()
    success = client.send_text(device, args.text, color, app_name=args.name)
    return 0 if success else 1

def handle_custom(args, config):
    device = resolve_device(args.device, config)
    try:
        payload = json.loads(args.json_payload)
    except Exception as e:
        print(f"Error parsing JSON payload: {e}")
        return 1

    client = AwtrixClient()
    success = client.send_payload(device, args.name, payload)
    return 0 if success else 1

def handle_power(args, config):
    device = resolve_device(args.device, config)
    state = args.state.lower() in ("on", "true", "1")
    client = AwtrixClient()
    success = client.set_power(device, state)
    return 0 if success else 1

def main():
    parser = argparse.ArgumentParser(description="Awtrix Smart Display Agent Integration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Stream Command
    stream_parser = subparsers.add_parser("stream", help="Control background rotator animation stream")
    stream_parser.add_argument("action", choices=["start", "stop", "status"])
    stream_parser.add_argument("-d", "--devices", help="Devices override (comma separated aliases/hostnames)")
    stream_parser.add_argument("--sprites-dir", help="Sprites directory override")

    # Notify Command
    notify_parser = subparsers.add_parser("notify", help="Send walking character + text notification")
    notify_parser.add_argument("device", help="Device alias or hostname")
    notify_parser.add_argument("text", help="Text message")
    notify_parser.add_argument("--sprite", help="Final Fantasy character sprite name/path")
    notify_parser.add_argument("--color", help="Text hex color override")
    notify_parser.add_argument("--duration", type=int, default=10, help="Duration to display (seconds)")

    # Text Command
    text_parser = subparsers.add_parser("text", help="Send static custom app text")
    text_parser.add_argument("device", help="Device alias or hostname")
    text_parser.add_argument("text", help="Text message")
    text_parser.add_argument("--color", help="Text hex color override")
    text_parser.add_argument("--name", default="customapp", help="Custom app name")

    # Custom Command
    custom_parser = subparsers.add_parser("custom", help="Send raw drawing JSON payload")
    custom_parser.add_argument("device", help="Device alias or hostname")
    custom_parser.add_argument("json_payload", help="JSON payload string")
    custom_parser.add_argument("--name", default="customapp", help="Custom app name")

    # Power Command
    power_parser = subparsers.add_parser("power", help="Control display power")
    power_parser.add_argument("device", help="Device alias or hostname")
    power_parser.add_argument("state", choices=["on", "off"])

    args = parser.parse_args()
    config = load_config()

    if args.command == "stream":
        sys.exit(handle_stream(args, config))
    elif args.command == "notify":
        sys.exit(handle_notify(args, config))
    elif args.command == "text":
        sys.exit(handle_text(args, config))
    elif args.command == "custom":
        sys.exit(handle_custom(args, config))
    elif args.command == "power":
        sys.exit(handle_power(args, config))

if __name__ == "__main__":
    main()
