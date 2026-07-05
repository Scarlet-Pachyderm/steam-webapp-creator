const { app, components, BrowserWindow } = require("electron");

// Chromium's process-level sandbox needs Linux user-namespace permissions
// that aren't reliably available when launched from Steam's Gamescope
// Game Mode session (as opposed to a normal desktop session).
app.commandLine.appendSwitch("no-sandbox");

function targetUrl() {
  const arg = process.argv.slice(1).find((a) => /^https?:\/\//.test(a));
  if (!arg) {
    console.error("Usage: kiosk-launcher <url>");
    process.exit(1);
  }
  return arg;
}

const HIDE_SCROLLBAR_CSS = "::-webkit-scrollbar { width: 0 !important; height: 0 !important; }";

function createWindow(url) {
  const win = new BrowserWindow({
    fullscreen: true,
    frame: false,
    autoHideMenuBar: true,
    webPreferences: {
      sandbox: false,
    },
  });
  win.webContents.on("did-finish-load", () => {
    win.webContents.insertCSS(HIDE_SCROLLBAR_CSS);
  });
  if (process.env.KIOSK_DEVTOOLS) {
    win.webContents.openDevTools({ mode: "detach" });
  }
  win.loadURL(url);
}

app.whenReady().then(async () => {
  await components.whenReady();
  createWindow(targetUrl());
});

app.on("window-all-closed", () => app.quit());
