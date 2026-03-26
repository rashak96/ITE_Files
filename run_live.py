"""
One-command live session: build data (optional filters), start server, public HTTPS URL — no GitHub, no Render.

With **cloudflared** installed, this prints a **https://….trycloudflare.com** link anyone on the internet can use
for presenter + /vote + /present. No accounts, no deploy step. This PC must stay on while you teach.

Install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/

Usage:
  python run_live.py
  Double-click START_ITE.bat  →  same as: python run_live.py --simple
  python run_live.py --topic Cardiology --limit 10
  python run_live.py --port 8800 --lan-only
  python run_live.py --skip-build --lan-only   # fastest local start (no rebuild, no tunnel)
  python run_live.py --simple                  # open /present (simple flow) instead of slide deck
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1.2)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _can_bind_port(port: int, host: str = "0.0.0.0") -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _choose_listen_port(preferred: int, *, user_fixed: bool) -> int:
    if user_fixed:
        if _can_bind_port(preferred):
            return preferred
        print(
            f"ERROR: Port {preferred} is already in use (e.g. another run_live.py).",
            file=sys.stderr,
        )
        print("  Close that process, or pick another port:", file=sys.stderr)
        print(f"  python run_live.py --port {preferred + 1}", file=sys.stderr)
        sys.exit(1)
    p = preferred
    for _ in range(50):
        if _can_bind_port(p):
            if p != preferred:
                print(
                    f"Note: port {preferred} is busy — using {p} instead "
                    f"(or stop the process holding {preferred})."
                )
            return p
        p += 1
    print("ERROR: Could not find a free TCP port in range.", file=sys.stderr)
    sys.exit(1)


def _wait_for_server(port: int, timeout_s: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.4):
                return True
        except OSError:
            time.sleep(0.12)
    return False


def _cloudflared_exe() -> str | None:
    """
    Resolve cloudflared without requiring PATH:

    - Env ``CLOUDFLARED`` = full path to cloudflared.exe
    - ``cloudflared`` / ``cloudflared.exe`` on PATH
    - ``cloudflared.exe`` or ``cloudflared-windows-amd64.exe`` in ITE_Files folder (portable)
    """
    env = (os.environ.get("CLOUDFLARED") or "").strip().strip('"')
    if env:
        p = Path(env)
        if p.is_file():
            return str(p)
    for name in ("cloudflared", "cloudflared.exe"):
        w = shutil.which(name)
        if w:
            return w
    for cand in (
        ROOT / "cloudflared.exe",
        ROOT / "cloudflared-windows-amd64.exe",
        Path(r"C:\Program Files\cloudflared\cloudflared.exe"),
        Path(r"C:\Program Files (x86)\cloudflared\cloudflared.exe"),
    ):
        if cand.is_file():
            return str(cand)
    return None


def _cloudflared_windows_help() -> str:
    d = ROOT
    return (
        "\nCould not find **cloudflared** (separate from Cloudflare WARP / 1.1.1.1 / the website).\n\n"
        "Pick ONE:\n"
        "  A) Open PowerShell as Administrator and run:\n"
        "       winget install Cloudflare.cloudflared\n"
        "     Close PowerShell, open a new one, then:  cloudflared --version\n\n"
        "  B) Portable (no installer): download this file in your browser:\n"
        "       https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe\n"
        "     Save it as:\n"
        f"       {d / 'cloudflared.exe'}\n"
        "     (same folder as run_live.py). Run:  python run_live.py\n\n"
        "  C) Put the .exe anywhere and set environment variable, then restart terminal:\n"
        "       CLOUDFLARED=C:\\\\full\\\\path\\\\to\\\\cloudflared.exe\n"
    )


def _try_cloudflared(port: int) -> tuple[str | None, subprocess.Popen | None]:
    exe = _cloudflared_exe()
    if not exe:
        return None, None
    popen_kw: dict = dict(
        args=[exe, "tunnel", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
    )
    if sys.platform == "win32":
        popen_kw["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    try:
        p = subprocess.Popen(**popen_kw)
    except OSError:
        return None, None
    url = None
    if p.stdout:
        for _ in range(120):
            line = p.stdout.readline()
            if not line and p.poll() is not None:
                break
            if line:
                m = re.search(r"(https://[a-z0-9.-]+\.trycloudflare\.com/?)", line, re.I)
                if m:
                    url = m.group(1).rstrip("/")
                    break
            time.sleep(0.05)
    return url, p


def main() -> None:
    ap = argparse.ArgumentParser(description="ITE live QR + voting session")
    ap.add_argument("--topic", help="Filter build_live by topic substring")
    ap.add_argument("--year", type=int, help="Filter by exam year")
    ap.add_argument("--limit", type=int, help="Max questions")
    ap.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="N",
        help="Listen port (default: 8765; if that is taken, next free is used automatically)",
    )
    ap.add_argument(
        "--lan-only",
        action="store_true",
        help="Do not start cloudflared; join URL is your LAN IP (same Wi‑Fi only)",
    )
    ap.add_argument("--no-browser", action="store_true", help="Do not open presenter URL")
    ap.add_argument(
        "--open-local",
        action="store_true",
        help="With a tunnel, still open 127.0.0.1 in the browser on this PC (audience can use the public URL)",
    )
    ap.add_argument(
        "--rebuild",
        action="store_true",
        help="Always run build_live.py (default skips if data.json is newer than ite_data.json and no filters)",
    )
    ap.add_argument(
        "--skip-build",
        action="store_true",
        help="Never run build_live.py (use existing live_ite/static/data.json)",
    )
    ap.add_argument(
        "--simple",
        action="store_true",
        help="Open /present (button-driven presenter) in browser instead of the slide deck",
    )
    args = ap.parse_args()

    data_json = ROOT / "live_ite" / "static" / "data.json"
    ite_json = ROOT / "ite_data.json"
    has_filters = bool(args.topic or args.year is not None or args.limit is not None)

    if args.skip_build:
        if not data_json.is_file():
            print("ERROR: --skip-build but data.json missing. Run: python build_live.py", file=sys.stderr)
            sys.exit(1)
        print("Skipping build (--skip-build).")
    else:
        stale = (
            ite_json.is_file()
            and data_json.is_file()
            and data_json.stat().st_mtime < ite_json.stat().st_mtime
        )
        run_build = args.rebuild or has_filters or not data_json.is_file() or stale
        if run_build:
            build_cmd = [sys.executable, str(ROOT / "build_live.py")]
            if args.topic:
                build_cmd.extend(["--topic", args.topic])
            if args.year is not None:
                build_cmd.extend(["--year", str(args.year)])
            if args.limit is not None:
                build_cmd.extend(["--limit", str(args.limit)])
            print("Running build_live.py…")
            r = subprocess.run(build_cmd, cwd=str(ROOT))
            if r.returncode != 0:
                sys.exit(r.returncode)
        else:
            print("Skipping build_live.py (data.json is up to date). Use --rebuild to force.")

    preferred = 8765 if args.port is None else args.port
    user_fixed = args.port is not None
    port = _choose_listen_port(preferred, user_fixed=user_fixed)

    lan = _lan_ip()
    public = f"http://{lan}:{port}"
    os.environ["PUBLIC_BASE_URL"] = public

    import uvicorn
    from live_ite.app import app

    def serve() -> None:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

    th = threading.Thread(target=serve, daemon=True)
    th.start()
    if not _wait_for_server(port):
        print(
            f"ERROR: Server did not start listening on port {port}.",
            file=sys.stderr,
        )
        sys.exit(1)

    tunnel_proc: subprocess.Popen | None = None
    tunnel_base: str | None = None
    if not args.lan_only:
        print(
            "Starting cloudflared for a public URL… "
            "(first URL can take 15–40s; use --lan-only to skip and start faster on Wi‑Fi only)"
        )
        turl, tunnel_proc = _try_cloudflared(port)
        if turl:
            tunnel_base = turl.rstrip("/")
            os.environ["PUBLIC_BASE_URL"] = tunnel_base
        else:
            if _cloudflared_exe() is None:
                print(_cloudflared_windows_help())
            else:
                print(
                    "cloudflared started but no tunnel URL was detected "
                    "(wait longer or check firewall). Falling back to LAN only.",
                    file=sys.stderr,
                )
            print("Falling back to LAN only.")
            if tunnel_proc:
                tunnel_proc.terminate()
                tunnel_proc = None
    else:
        print("LAN-only mode (no internet-wide URL).")

    base = os.environ.get("PUBLIC_BASE_URL", public).rstrip("/")
    deck_url = base + "/"
    simple_url = base + "/present"
    vote_url = base + "/vote"
    local_deck = f"http://127.0.0.1:{port}/"
    local_simple = f"http://127.0.0.1:{port}/present"

    print()
    if tunnel_base is not None:
        print("  " + "=" * 62)
        print("  PUBLIC HTTPS (no GitHub, no Render, no signup): use these links")
        print("  " + "=" * 62)
    print()
    print("  Presenter — slide deck:")
    print("  ", deck_url)
    print("  Presenter — simple controls:")
    print("  ", simple_url)
    print()
    print("  Audience phones (/vote):")
    print("  ", vote_url)
    print()
    if tunnel_base is None:
        print("  Wi‑Fi / LAN only right now. For a public https URL from this folder only:")
        print("  → Install cloudflared (see docstring link), then run again WITHOUT --lan-only.")
    else:
        print("  Keep THIS window open while presenting. URL changes next time you restart")
        print("  (copy the new https://….trycloudflare.com link from the console).")
    print()
    print("  Same-machine: deck", local_deck, "| simple", local_simple)
    print("Stop: Ctrl+C")

    if not args.no_browser:
        open_local = local_simple if args.simple else local_deck
        open_remote = simple_url if args.simple else deck_url
        if args.open_local and tunnel_base is not None:
            webbrowser.open(open_local)
        elif tunnel_base is not None:
            webbrowser.open(open_remote)
        else:
            webbrowser.open(open_local)

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\nStopping…")
        if tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()


if __name__ == "__main__":
    main()
