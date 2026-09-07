"""
run_all.py
----------
Single-command launcher for Medical Risk & XAI platform.

Order of Execution:
1. Verifies/trains ML model (src/build_training_data.py -> src/preprocessing.py -> src/train.py).
2. Checks and seeds database if empty (scripts/seed_demo_data.py).
3. Spawns FastAPI backend subprocess (port 8000).
4. Spawns Vite frontend dev server subprocess.
5. Prints quick access URLs and credentials.
6. Streams logs and shuts down cleanly on Ctrl+C.

Usage:
    python run_all.py
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_FILE = MODELS_DIR / "best_model.joblib"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

venv_win = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
venv_nix = PROJECT_ROOT / ".venv" / "bin" / "python"
if venv_win.exists():
    PYTHON_EXEC = str(venv_win)
elif venv_nix.exists():
    PYTHON_EXEC = str(venv_nix)
else:
    PYTHON_EXEC = sys.executable



def log_step(title: str) -> None:
    print("\n" + "=" * 80)
    print(f"[*] {title}")
    print("=" * 80)


def run_command(cmd: list[str], cwd: Path | None = None) -> None:
    cwd_str = str(cwd) if cwd else str(PROJECT_ROOT)
    cmd_str = " ".join(cmd)
    print(f" -> Running: {cmd_str}")
    res = subprocess.run(cmd, cwd=cwd_str, check=False)
    if res.returncode != 0:
        print(f"[!] Command failed with exit code {res.returncode}: {cmd_str}")
        sys.exit(res.returncode)


def check_and_train_model() -> None:
    """Step 1: Check if models/best_model.joblib exists; train pipeline if missing."""
    if not MODEL_FILE.exists():
        log_step("Model not found. Running complete training pipeline...")
        run_command([PYTHON_EXEC, "src/build_training_data.py"])
        run_command([PYTHON_EXEC, "src/preprocessing.py"])
        run_command([PYTHON_EXEC, "src/train.py"])
        print(" -> Model pipeline trained and saved successfully.")
    else:
        print(f"[*] Found existing trained model at: {MODEL_FILE.relative_to(PROJECT_ROOT)}")


def check_and_seed_database() -> None:
    """Step 2: Seed database with demo data if it's empty."""
    log_step("Checking database and seeding demo records if needed...")
    run_command([PYTHON_EXEC, "scripts/seed_demo_data.py"])


def stream_logs(pipe, prefix: str) -> None:
    """Reads lines from a subprocess pipe and outputs them with a labeled prefix."""
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            line_str = line.strip()
            if line_str:
                print(f"{prefix} {line_str}")
    except Exception:
        pass
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def find_available_port(host: str = "127.0.0.1", start_port: int = 5173) -> int:
    """Return the first available local TCP port at or after ``start_port``."""
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
        return port
    raise RuntimeError(f"Could not find an available port starting at {start_port}.")


def wait_for_service(url: str, process: subprocess.Popen, name: str, timeout: float = 20.0) -> None:
    """Fail fast if a service cannot start, rather than launching a disconnected UI."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{name} exited during startup (code {process.returncode}).")
        try:
            with urlopen(url, timeout=1) as response:
                if 200 <= response.status < 300:
                    print(f"[*] {name} is ready: {url}")
                    return
        except (URLError, TimeoutError):
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {name} at {url}.")


def main() -> None:
    # 1. Check ML Model
    check_and_train_model()

    # 2. Check Database
    check_and_seed_database()

    log_step("Starting Medical Risk XAI Services")

    # 3. Start FastAPI backend
    env_unbuffered = dict(os.environ)
    env_unbuffered["PYTHONUNBUFFERED"] = "1"
    backend_cmd = [PYTHON_EXEC, "-u", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--reload", "--port", "8000"]
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env_unbuffered,
    )
    wait_for_service("http://127.0.0.1:8000/health", backend_proc, "Backend API")


    # 4. Start React/Vite Frontend
    is_windows = sys.platform.startswith("win")
    npm_cmd = "npm.cmd" if is_windows else "npm"
    frontend_port = find_available_port()
    frontend_url = f"http://127.0.0.1:{frontend_port}"
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(frontend_port), "--strictPort"],
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=is_windows,
    )
    t_frontend = threading.Thread(
        target=stream_logs,
        args=(frontend_proc.stdout, "[UI] "),
        daemon=True,
    )
    t_frontend.start()
    try:
        wait_for_service(frontend_url, frontend_proc, "Frontend")
    except Exception:
        # Startup occurs before the main cleanup handler is active.
        # Stop the backend too, so a failed UI launch does not leave it running.
        if frontend_proc.poll() is None:
            if is_windows:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend_proc.pid)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                frontend_proc.terminate()
        if backend_proc.poll() is None:
            backend_proc.terminate()
        raise

    # 5. Print Summary Banner
    print("\n" + "=" * 80)
    print(" MEDICAL RISK & XAI PLATFORM READY")
    print("=" * 80)
    print(f"  * Frontend UI : {frontend_url}")
    print("  * Backend API : http://127.0.0.1:8000")
    print("  * Swagger Docs: http://127.0.0.1:8000/docs")
    print("-" * 80)
    print("  * Demo Admin  : admin@hospital.com  / Demo@123")
    print("  * Demo Doctor : dr.sharma@hospital.com / Demo@123")
    print("  * Demo Patient: patient.arjun@hospital.com / Demo@123")
    print("=" * 80)
    print("Streaming service logs below (Press Ctrl+C to shut down cleanly)...\n")

    # 6. Stream outputs in background threads
    t_backend = threading.Thread(
        target=stream_logs,
        args=(backend_proc.stdout, "[API]"),
        daemon=True,
    )
    t_backend.start()

    def cleanup():
        print("\n[*] Shutting down backend and frontend services...")
        try:
            if backend_proc.poll() is None:
                backend_proc.terminate()
                backend_proc.wait(timeout=3)
        except Exception:
            backend_proc.kill()

        try:
            if frontend_proc.poll() is None:
                if is_windows:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(frontend_proc.pid)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    frontend_proc.terminate()
                    frontend_proc.wait(timeout=3)
        except Exception:
            frontend_proc.kill()

        print("[*] All services stopped cleanly.")

    try:
        while True:
            if backend_proc.poll() is not None:
                print(f"[!] Backend process exited with code {backend_proc.returncode}")
                break
            if frontend_proc.poll() is not None:
                print(f"[!] Frontend process exited with code {frontend_proc.returncode}")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()
