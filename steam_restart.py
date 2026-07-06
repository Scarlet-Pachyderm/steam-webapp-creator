"""Restart Steam so it picks up new/changed non-Steam shortcuts."""
import shutil
import subprocess
import time


def restart_steam():
    """Kill Steam and relaunch it (Flatpak or native, whichever is
    present). Fire-and-forget -- Steam takes a while to fully start on
    its own regardless of how it's launched."""
    subprocess.run(["killall", "steam"], capture_output=True)
    time.sleep(1)

    flatpak = shutil.which("flatpak")
    if flatpak and subprocess.run(
        [flatpak, "info", "com.valvesoftware.Steam"], capture_output=True
    ).returncode == 0:
        subprocess.Popen([flatpak, "run", "com.valvesoftware.Steam"])
    elif shutil.which("steam"):
        subprocess.Popen(["steam", "-silent"])
