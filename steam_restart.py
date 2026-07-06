"""Restart Steam so it picks up new/changed non-Steam shortcuts.

Kill/wait/relaunch pattern (kill, then poll for actual exit instead of
guessing a fixed delay, then launch) matches
github.com/SteamGridDB/steam-rom-manager's stop-start-steam.ts, which
the user specifically pointed to as feeling seamless. Flatpak-vs-native
detection uses steam_paths' filesystem checks instead of asking the
`flatpak` CLI (which SRM does) -- confirmed that CLI's view of
installed refs can be isolated from the host's actual installs (e.g.
from inside a distrobox/toolbox container), even though the
filesystem paths themselves are shared and visible.
"""
import os
import shutil
import subprocess
import time

import steam_paths

POLL_INTERVAL = 0.5
POLL_TIMEOUT = 60


def _steam_pid_running():
    return subprocess.run(["pidof", "steam"], capture_output=True).returncode == 0


def restart_steam():
    pids = _steam_pids()
    if pids:
        subprocess.run(["kill", "-15", *pids], capture_output=True)

    waited = 0.0
    while _steam_pid_running() and waited < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL

    try:
        root = steam_paths.find_steam_root()
    except steam_paths.SteamNotFoundError:
        return

    if root == os.path.expanduser(steam_paths.FLATPAK_ROOT):
        flatpak = shutil.which("flatpak")
        if flatpak:
            _launch_and_wait([flatpak, "run", "com.valvesoftware.Steam"])
        return

    # Prefer the launcher script at its known absolute path within the
    # detected root over a PATH-based `steam` lookup: the script lives on
    # the shared host filesystem either way, but the launcher binary
    # normally installed to /usr/bin isn't visible from inside a
    # distrobox/toolbox container (separate root filesystem, only home
    # is shared) -- confirmed this is exactly why shutil.which("steam")
    # found nothing there even though native Steam is genuinely installed.
    launcher = os.path.join(root, "steam.sh")
    if os.path.exists(launcher):
        _launch_and_wait([launcher, "-silent"])
    elif shutil.which("steam"):
        _launch_and_wait(["steam", "-silent"])


def _steam_pids():
    result = subprocess.run(["pidof", "steam"], capture_output=True, text=True)
    return result.stdout.split()


def _launch_and_wait(argv):
    subprocess.Popen(argv, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    waited = 0.0
    while not _steam_pid_running() and waited < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL
