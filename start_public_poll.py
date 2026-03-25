"""
One-command public launcher for the HTML poll decks.

Starts:
1) HTML generation (create_ite_html.py)
2) local poll server (poll_server.py)
3) public tunnel via cloudflared

No npx/localtunnel dependency.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

BASE = Path(__file__).parent
PORT = 8765


def _cloudflared_exe() -> str | None:
    for name in ("cloudflared", "cloudflared.exe"):
        w = shutil.which(name)
        if w:
            return w
    for cand in (
        BASE / "cloudflared.exe",
        BASE / "cloudflared-windows-amd64.exe",
        Path(r"C:\Program Files\cloudflared\cloudflared.exe"),
        Path(r"C:\Program Files (x86)\cloudflared\cloudflared.exe"),
    ):
        if cand.is_file():
            return str(cand)
    return None


def _run_cmd(command: list[str], cwd: Path | None = None) -> subprocess.Popen:
    kw: dict = dict(
        args=command,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if sys.platform == "win32":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return subprocess.Popen(**kw)


def main() -> int:
    print("Generating ITE_HTML...")
    gen = subprocess.run([sys.executable, "create_ite_html.py"], cwd=BASE)
    if gen.returncode != 0:
        print("Failed to generate HTML.")
        return gen.returncode

    exe = _cloudflared_exe()
    if not exe:
        print("\ncloudflared not found.")
        print("Install with winget:  winget install Cloudflare.cloudflared")
        print("Or put cloudflared.exe in this folder and run again.")
        return 1

    print("Starting local poll server...")
    server = _run_cmd([sys.executable, "poll_server.py"], cwd=BASE)
    time.sleep(2)
    if server.poll() is not None:
        print("Local poll server failed to start.")
        return 1

    print("Starting public tunnel (5-20 seconds)...")
    tunnel = _run_cmd([exe, "tunnel", "--url", f"http://127.0.0.1:{PORT}"], cwd=BASE)

    public_url = None
    started = time.time()
    while time.time() - started < 50:
        line = tunnel.stdout.readline() if tunnel.stdout else ""
        if not line:
            time.sleep(0.2)
            continue
        m = re.search(r"(https://[a-z0-9.-]+\.trycloudflare\.com/?)(\s|$)", line, re.I)
        if m:
            public_url = m.group(1).rstrip("/")
            break

    if not public_url:
        print("\nCould not read a public URL from cloudflared output.")
        print("Check internet/firewall, then retry.")
        if server.poll() is None:
            server.terminate()
        if tunnel.poll() is None:
            tunnel.terminate()
        return 1

    presenter = public_url + "/"
    print("\nPublic presenter URL (open this on any PC):")
    print(f"  {presenter}")
    print("\nThen choose a topic. Audience joins from the same topic URL + ?audience")
    print("Example:")
    print(f"  {public_url}/Cardiology.html?audience")
    print("\nKeep this process running. Press Ctrl+C to stop.")

    try:
        webbrowser.open(presenter)
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
            if server.poll() is not None:
                print("Server stopped.")
                break
            if tunnel.poll() is not None:
                print("Tunnel stopped.")
                break
    except KeyboardInterrupt:
        pass
    finally:
        for p in (server, tunnel):
            if p.poll() is None:
                p.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
