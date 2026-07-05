const { app, components, BrowserWindow } = require("electron");

function targetUrl() {
  const arg = process.argv.slice(1).find((a) => /^https?:\/\//.test(a));
  if (!arg) {
    console.error("Usage: kiosk-launcher <url>");
    process.exit(1);
  }
  return arg;
}

const HIDE_SCROLLBAR_CSS = "::-webkit-scrollbar { width: 0 !important; height: 0 !important; }";

// Disney+ (and some other services) block DRM playback on a Linux user
// agent even with a real, valid Widevine CDM -- spoofing Windows is a
// well-known workaround that real Linux browser users also rely on.
const WINDOWS_UA = `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${process.versions.chrome} Safari/537.36`;

function createWindow(url) {
  const win = new BrowserWindow({
    fullscreen: true,
    frame: false,
    autoHideMenuBar: true,
  });
  win.webContents.setUserAgent(WINDOWS_UA);
  win.webContents.on("did-finish-load", () => {
    win.webContents.insertCSS(HIDE_SCROLLBAR_CSS);
  });
  win.loadURL(url);
}

app.whenReady().then(async () => {
  await components.whenReady();
  createWindow(targetUrl());
});

app.on("window-all-closed", () => app.quit());
