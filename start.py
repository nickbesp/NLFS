"""Start the NLFS backend and frontend together in this terminal.

Usage:
    python start.py               # start both, open the browser when ready
    python start.py --no-browser  # start both, don't open the browser

Press Ctrl+C to stop both servers.
Only uses the standard library, so any Python 3.10+ can run it.
"""

import argparse
import os
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
IS_WINDOWS = os.name == "nt"
VENV_PYTHON = BACKEND / ".venv" / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
NPM = "npm.cmd" if IS_WINDOWS else "npm"

BACKEND_URL = "http://127.0.0.1:8000/api/stats"
FRONTEND_URL = "http://localhost:3000"
READY_TIMEOUT = 120  # seconds


def log(msg: str) -> None:
    print(f"[start] {msg}", flush=True)


def run_setup_step(cmd: list[str], cwd: Path) -> None:
    log(f"$ {' '.join(map(str, cmd))}")
    subprocess.run(cmd, cwd=cwd, check=True)


def ensure_setup() -> None:
    """Create the venv / install npm packages on first run."""
    if not VENV_PYTHON.exists():
        log("Backend venv missing, creating it...")
        run_setup_step([sys.executable, "-m", "venv", ".venv"], BACKEND)
        run_setup_step([str(VENV_PYTHON), "-m", "pip", "install", "-r", "requirements.txt"], BACKEND)
    if not (FRONTEND / "node_modules").exists():
        log("Frontend packages missing, running npm install...")
        run_setup_step([NPM, "install"], FRONTEND)


def start(name: str, cmd: list[str], cwd: Path) -> subprocess.Popen:
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "FORCE_COLOR": "1"}
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
    )
    threading.Thread(target=pipe_output, args=(name, proc), daemon=True).start()
    log(f"{name} started (pid {proc.pid}): {' '.join(map(str, cmd))}")
    return proc


def pipe_output(name: str, proc: subprocess.Popen) -> None:
    """Print a child's output line by line with a [name] prefix."""
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.decode("utf-8", errors="replace").rstrip()
        if line:
            print(f"[{name}] {line}", flush=True)


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if IS_WINDOWS:
        # npm and uvicorn --reload spawn child processes; /T kills the whole tree.
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def is_up(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2):
            return True
    except Exception:
        return False


def wait_until_ready(procs: dict[str, subprocess.Popen]) -> bool:
    deadline = time.time() + READY_TIMEOUT
    pending = {"backend": BACKEND_URL, "frontend": FRONTEND_URL}
    while pending and time.time() < deadline:
        for name in list(pending):
            if procs[name].poll() is not None:
                log(f"{name} exited early (code {procs[name].returncode}).")
                return False
            if is_up(pending[name]):
                log(f"{name} is ready.")
                del pending[name]
        time.sleep(1)
    if pending:
        log(f"Timed out waiting for: {', '.join(pending)}")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-browser", action="store_true", help="don't open the browser")
    args = parser.parse_args()

    # Server output contains symbols (▲, ✓, Cyrillic paths) that legacy Windows code pages
    # can't encode; replace them instead of crashing the output threads.
    sys.stdout.reconfigure(errors="replace")

    if is_up(BACKEND_URL) or is_up(FRONTEND_URL):
        log("Port 8000 or 3000 is already in use - is NLFS already running? Stop it first.")
        return 1

    try:
        ensure_setup()
    except subprocess.CalledProcessError as e:
        log(f"Setup failed: {e}")
        return 1

    procs = {
        "backend": start("backend", [str(VENV_PYTHON), "run.py"], BACKEND),
        "frontend": start("frontend", [NPM, "run", "dev"], FRONTEND),
    }

    try:
        if not wait_until_ready(procs):
            return 1
        log(f"NLFS is running at {FRONTEND_URL}  (Ctrl+C to stop)")
        if not args.no_browser:
            webbrowser.open(FRONTEND_URL)

        # Keep running until a server dies or the user presses Ctrl+C.
        while all(p.poll() is None for p in procs.values()):
            time.sleep(1)
        dead = [n for n, p in procs.items() if p.poll() is not None]
        log(f"{', '.join(dead)} stopped unexpectedly - shutting down.")
        return 1
    except KeyboardInterrupt:
        log("Ctrl+C received - stopping...")
        return 0
    finally:
        for p in procs.values():
            stop(p)
        log("All servers stopped.")


if __name__ == "__main__":
    sys.exit(main())
