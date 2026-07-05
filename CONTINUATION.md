# Project recap / handoff

Written for continuing this project with Claude Code on the x86_64 laptop
(this repo was started on an aarch64 machine that can't run Steam).

## Goal

A Flatpak GTK4 app for Steam Deck / Bazzite / CachyOS: user types a URL
(e.g. netflix.com), app searches SteamGridDB for matching artwork, user
confirms the match, and the app creates a non-Steam shortcut so the site
shows up as a native-looking tile in Steam Game Mode — opened in a
borderless/kiosk browser window instead of a normal browser tab.

Stretch goal: bundle a Steam Input controller config so the d-pad acts
like Tab (navigate), A = Enter/Play-Pause, B = Back/Escape.

## Stack decisions (already made, don't re-litigate)

- **GTK4 + libadwaita**, Python via PyGObject. UI should stay minimal,
  styled like [unrud/video-downloader](https://github.com/unrud/video-downloader)
  — single window, no bells and whistles.
- **No third-party Python deps for the SGDB client** — stdlib `urllib`
  only, to keep the Flatpak runtime light. Keep this going unless there's
  a strong reason to add `requests`.
- **Flatpak target: x86_64 only** (changed from an earlier x64+arm64
  plan — see kiosk launcher decision below for why. Tried reverting this
  when the launcher architecture changed again later, but Edge itself
  has no Linux arm64 build either — checked its Flathub manifest,
  `only-arches: [x86_64]` — so this stays x86_64-only regardless).
- Plan: publish to GitHub (done) for issues, then submit to **Flathub**
  for auto-updates.

## Repo

https://github.com/Scarlet-Pachyderm/steam-webapp-creator

(Transferred from a personal account into the `Scarlet-Pachyderm` org.
Repo name `steam-webapp-creator` is a placeholder — renaming later is
fine, GitHub redirects the old URL/remote automatically.)

## Stage 1 — done

`sgdb_client.py` + `create_webapp.py`: CLI that searches SGDB, lets the
user confirm a match, downloads the 5 asset categories, and (since Steam
isn't installed on the dev machine) registers a `.desktop` file in the
local app menu as a stand-in test for "does the icon actually render."
Confirmed working end-to-end for Netflix.

Non-obvious things learned along the way:

- SGDB API requests need a real `User-Agent` header or Cloudflare 403s
  them (error code 1010) — the auth header alone isn't enough.
- The `/icons` endpoint returns both `.ico` and plain `.png` entries for
  the same game. **Prefer `.png`**; `.ico` isn't part of the freedesktop
  icon spec and can render blank in app menus. `sgdb_client.py` already
  filters for `.png` first.
- As a fallback for the rare case where only `.ico` exists,
  `sgdb_client.extract_largest_png_from_ico()` pulls the largest embedded
  PNG frame straight out of the ICO container (modern ICOs embed real
  PNGs for big sizes) — no image library needed.
- Always derive the saved file extension from the actual URL, not a
  hardcoded `.png` — SGDB's "grid" assets are sometimes JPEGs.
- Grid dimensions used: vertical `600x900,342x482,660x930`, horizontal
  `460x215,920x430` (matches what Steam's non-Steam-shortcut grid folder
  expects for portrait/landscape tiles).
- `.env` (gitignored) holds `STEAMGRIDDB_API_KEY` — get a free key at
  steamgriddb.com/profile/preferences/api. Needs to be recreated on each
  machine, it's not in git.
- `assets/` (gitignored) holds test-downloaded images, also not in git.

## Stage 2 — items 1-4 done, confirmed working on real Steam

1. **`shortcuts.vdf` writer** — done, `shortcuts_vdf.py`. Binary VDF
   read/write (type-tagged tree: 0x00 map / 0x01 string / 0x02 int32,
   0x08 closes a map). `load()`/`save()` round-trip preserves existing
   entries and auto-backs up to `.bak` before overwriting.
   `add_shortcut()` updates in place by matching `appname` instead of
   duplicating.
2. **App ID calculation** — done, `shortcuts_vdf.generate_appid(exe,
   appname)`: CRC32 of the **quoted** exe path concatenated with the app
   name, OR'd with `0x80000000`. Same value is used for the vdf's
   `appid` field and every grid asset filename — confirmed they must all
   agree or Steam won't associate the artwork.
3. **Artwork placement** — done, in `create_webapp.py:register_steam_shortcut()`.
   Saves into `<userdata>/<id>/config/grid/` as `<appid>p.ext` (vertical),
   `<appid>.ext` (horizontal), `<appid>_hero.ext`, `<appid>_logo.ext`,
   `<appid>_icon.ext` — extension taken from the real downloaded file,
   not hardcoded.
4. **Steam install path detection** — done, `steam_paths.py`. Checks
   native `~/.local/share/Steam` / `~/.steam/steam` first, then Flatpak
   `~/.var/app/com.valvesoftware.Steam/.local/share/Steam`. Confirmed
   correct on both: picks native on the Steam Deck (SteamOS, `holo`),
   picks Flatpak on the x86_64 dev box. Multiple userdata user IDs
   aren't auto-resolved — raises and expects `--steam-user`.

**Confirmed end-to-end on real Steam for Disney+, on two different
machines:**
- **x86_64 desktop, Steam as Flatpak** — shortcut appeared with full
  artwork after a full Steam restart, and the tile launched the URL via
  `exe=/usr/bin/xdg-open` (a **host** binary path) with no
  `flatpak-spawn --host` wrapper needed — Steam's own Flatpak sandbox
  permissions were broad enough to exec it directly.
- **Steam Deck (SteamOS, native Steam)** — same code, same generated
  appid (`4039713046`, confirming the calc is deterministic across
  machines), shortcut appeared with artwork and launched correctly.
  Reached over SSH (SteamOS ships `sshd` but it's off by default —
  enabled via Desktop Mode: `passwd` then `sudo systemctl enable --now
  sshd`; unit is named `sshd`, not `ssh`). `killall steam` is enough to
  force a restart that picks up new shortcuts; it auto-relaunches.

Not yet tested: Bazzite, CachyOS, a userdata dir with multiple Steam
user IDs.

5. Steam needs a full restart (fully quit, not just close the window)
   to pick up new/changed shortcuts — confirmed, no known way around
   this.

## Later stages (not started)

- **Kiosk-mode browser launch — FINAL decision: shell out to an installed
  Microsoft Edge, don't bundle a browser at all.** This is the second
  reversal on this decision; history kept below for context so it isn't
  re-litigated:
  1. Original plan: shell out to any installed Chromium-based browser
     (Brave/Chrome/Edge) in `--app=<url>` mode.
  2. Revised to bundling a Widevine-enabled Electron fork (castLabs'
     "Electron for Content Security"), fully implemented in a
     `kiosk-launcher/` subproject and **confirmed working end-to-end on
     real hardware** (x86_64 desktop with Steam as Flatpak, and a real
     Steam Deck, including from actual Game Mode) — see git history
     around the `kiosk-launcher/` removal commit for the full trail of
     gotchas that were worked through to get there (Steam overlay
     LD_PRELOAD injection crashing Electron's zygote process regardless
     of `AllowOverlay`, a cookie-consent prompt that must be explicitly
     accepted once per profile, castLabs' Cloudflare/AdGuard interaction
     during Widevine CDM install, etc.) if any of that becomes relevant
     again.
  3. **Reverted again, this time for good:** that castLabs-Electron setup
     could not play Dolby Digital Plus/Atmos audio at all — confirmed via
     `DecoderStatus::Codes::kUnsupportedConfig` errors on any title with a
     Dolby-only audio track (typical for big-budget content; titles
     mastered in plain stereo/AAC, e.g. Golden Girls, played fine).
     Microsoft has a direct Dolby licensing deal baked into Edge's binary
     on every platform it ships, including Linux; Google never licensed
     Dolby codecs into open-source Chromium, so **no other Chromium
     derivative can decode that audio, ever** — not Chrome, not Brave,
     not a bundled Electron, regardless of build config. This is a hard
     licensing wall, not a bug, and the user considers it a deal-breaker.
     Checked whether quark-player (an existing prior-art Electron
     streaming-service player on the same castLabs fork) found a
     workaround — it hasn't; [its Disney+ issue](https://github.com/Alex313031/quark-player/issues/49)
     describes an unrelated black-screen bug, no mention of Dolby at all.
  - **Current implementation:** `edge_launcher.py` detects an installed
    Edge (checks native binary names `microsoft-edge`/
    `microsoft-edge-stable`/etc. first, then falls back to checking for
    the Flatpak `com.microsoft.Edge`, which is a real official Flathub
    package). `create_webapp.py` points the Steam shortcut's `exe` at
    `launch-browser.sh` (a tiny wrapper, kept from the Electron days,
    that does `unset LD_PRELOAD` before `exec "$@"` — still needed since
    Steam sets `LD_PRELOAD` for its overlay in every child process
    regardless of `AllowOverlay`, which would otherwise crash Edge the
    same way it crashed Electron's zygote), with `LaunchOptions` set to
    the Edge binary plus `--app=<url> --start-fullscreen
    --user-data-dir=<per-shortcut profile dir under edge-profiles/,
    gitignored>`.
  - **x86_64 only, still** — tried reviving arm64 now that castLabs
    Electron (the thing that killed it) is gone, but Edge's own Flathub
    manifest is also `only-arches: [x86_64]` (Microsoft doesn't ship an
    Edge Linux arm64 build at all), so this stays x86_64-only regardless
    of which approach is used.
  - **Not yet re-tested on real Steam Deck hardware** — this pivot
    happened after the Electron version was already confirmed working on
    Game Mode; the Edge-based version needs the same real-hardware
    verification pass before it can be considered done. Likely still-true
    carryover concerns from the Electron testing: Edge will probably hit
    the same cookie/privacy-consent-prompt-must-be-accepted-once gotcha
    on a fresh profile, and the `shortcuts_vdf.generate_appid()` derives
    from `exe` + `appname` so changing `exe` again means re-copying grid
    assets under the new appid and deleting the orphaned old ones (same
    as happened during the Electron pivot).
- Steam Input controller config bundling (dpad → Tab/Arrows, A → Enter,
  B → Escape) so sites are navigable without a mouse/keyboard. This is a
  Steam feature (works on any non-Steam shortcut), not something the app
  renders itself — quality depends on how keyboard-navigable the actual
  site is.
- **Wrap the CLI logic in a GTK4/libadwaita UI**, with a first-run
  onboarding flow covering the two one-time setup steps below (the actual
  per-shortcut flow — type URL, confirm SGDB match, create shortcut —
  doesn't need to touch either again afterward):
  1. **Check for Edge, offer to install if missing.**
     `edge_launcher.find_edge()` already does the detection (native
     binary names first, then the Flatpak). If not found, show a button
     that installs the Flathub package via
     `flatpak-spawn --host flatpak install flathub com.microsoft.Edge`
     — confirmed this is a legitimate, established pattern by checking
     two real installed apps that do the same thing (Bazaar, an app
     store; Warehouse, a Flatpak manager): both request
     `--talk-name=org.freedesktop.Flatpak` in their manifest's
     finish-args (shows as `org.freedesktop.Flatpak=talk` under Session
     Bus Policy) to get `flatpak-spawn --host` access. `flatpak install`
     run this way still shows its own confirmation dialog on the host
     side by default, so nothing installs silently. This is one more
     privileged manifest permission on top of the Steam userdata
     filesystem access we already need — Flathub reviewers do scrutinize
     it, though it's an accepted pattern for apps like this.
  2. **SGDB API key input.** A settings field where the user pastes their
     own free key (from steamgriddb.com/profile/preferences/api), stored
     locally in the app's own data dir, never committed or shared.
     SGDB's terms expect per-user keys; a key baked into a distributed
     app would get rate-limited across installs and risks revocation,
     breaking the app for everyone. Checked how
     [Steam ROM Manager](https://github.com/SteamGridDB/steam-rom-manager)
     (an official first-party SteamGridDB tool) handles this for
     comparison: `src/lib/image-providers/api-key.ts` just hardcodes a
     single shared key, with their own `// TODO make the user input this`
     comment admitting it's a stopgap. They can get away with it only
     because they're the platform's own team and control both sides if
     that key ever gets rate-limited/abused — not a position a
     third-party app is in, so this doesn't change our decision, if
     anything it reinforces it. The current `.env` (gitignored, recreated
     per dev machine) is only a stand-in for this until the UI exists.
- Flatpak manifest (x86_64 only), needs broad filesystem permission to
  reach Steam's userdata dir outside the sandbox, plus
  `--talk-name=org.freedesktop.Flatpak` for the Edge-install button
  above.
- Flathub submission.

## Constraints to keep in mind

- Keep it a small utility app: no premature abstractions, no deps beyond
  what's needed, no error handling for cases that can't happen.
- Don't commit `.env` or `assets/` — already gitignored.
