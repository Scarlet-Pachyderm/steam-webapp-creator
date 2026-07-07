"""Detect an installed Microsoft Edge, native or Flatpak.

Edge is the only Chromium-based browser with Dolby Digital Plus/Atmos audio
decoding built in on every platform it ships, including Linux -- Google
never licensed Dolby codecs into open-source Chromium, so no other
Chromium derivative (including a bundled Electron) can play that audio.
Rather than bundling a browser ourselves, we shell out to Edge if it's
already installed, and ask the user to install it otherwise.
"""
import os
import shutil
import subprocess

NATIVE_BINARY_NAMES = ["microsoft-edge-stable", "microsoft-edge", "microsoft-edge-beta", "microsoft-edge-dev"]
FLATPAK_APP_ID = "com.microsoft.Edge"

# Chromium/Edge only shows its first-run wizard (instead of the kiosk
# --app= page) when this sentinel file is missing from the profile dir.
# Pre-creating it (empty) lets a shortcut work correctly on its very
# first launch. Confirmed path on the Flatpak build; native installs
# manage their own profile/first-run outside our scope.
FLATPAK_FIRST_RUN_PATH = os.path.expanduser(
    "~/.var/app/com.microsoft.Edge/config/microsoft-edge/First Run"
)

INSTALL_INSTRUCTIONS = (
    "Microsoft Edge wasn't found. Install it from Flathub "
    "(flatpak install flathub com.microsoft.Edge) or from "
    "https://www.microsoft.com/en-us/edge/download?platform=linux "
    "(official .deb/.rpm), then try again."
)


class EdgeNotFoundError(RuntimeError):
    pass


def _flatpak_edge_installed():
    flatpak = shutil.which("flatpak")
    if not flatpak:
        return False
    result = subprocess.run(
        [flatpak, "info", FLATPAK_APP_ID],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def find_edge():
    """Returns (exe, prefix_args) for the installed Edge. prefix_args is
    empty for a native binary, or ["run", FLATPAK_APP_ID] when only the
    Flatpak is installed, so callers can just do
    [exe, *prefix_args, "--app=<url>", ...].

    No "--" separator before the app's own args: flatpak run doesn't
    need one here (no ambiguity, our args come after the app id), and
    Chromium/Edge treats a literal "--" in its own argv as "stop parsing
    flags, treat everything after as URLs" -- flatpak forwards it
    straight through, so adding one here silently breaks every flag
    after it (confirmed on real hardware: --app/--start-fullscreen/etc.
    all opened as literal tabs instead of being parsed)."""
    for name in NATIVE_BINARY_NAMES:
        path = shutil.which(name)
        if path:
            return path, []

    if _flatpak_edge_installed():
        suppress_first_run()
        return shutil.which("flatpak"), ["run", FLATPAK_APP_ID]

    raise EdgeNotFoundError(INSTALL_INSTRUCTIONS)


def suppress_first_run():
    """Pre-seed the Flatpak Edge profile's first-run sentinel so a kiosk
    shortcut isn't hijacked by the first-run wizard. Safe to call
    whenever we know the Flatpak Edge is installed; a no-op if the
    profile already has one (e.g. the user already ran Edge directly)."""
    if os.path.exists(FLATPAK_FIRST_RUN_PATH):
        return
    os.makedirs(os.path.dirname(FLATPAK_FIRST_RUN_PATH), exist_ok=True)
    open(FLATPAK_FIRST_RUN_PATH, "a").close()
