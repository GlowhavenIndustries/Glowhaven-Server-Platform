from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import psutil

STATE_PATH = Path(os.getenv("HELIX_AGENT_STATE", "agent.json"))


def request(controller: str, path: str, method: str, payload: dict, agent_key: str | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(controller.rstrip("/") + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if agent_key:
        req.add_header("X-Helix-Agent-Key", agent_key)
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def inventory() -> dict:
    disk = shutil.disk_usage(Path.cwd())
    return {
        "cpu_count": psutil.cpu_count(logical=True) or 1,
        "memory_bytes": psutil.virtual_memory().total,
        "disk_bytes": disk.total,
        "python": platform.python_version(),
        "kernel": platform.release(),
    }


def service_action(action: str, service: str) -> dict:
    if platform.system().lower() == "windows":
        command = {"service_start": "start", "service_stop": "stop", "service_restart": "restart"}[action]
        if command == "restart":
            first = subprocess.run(["sc.exe", "stop", service], capture_output=True, text=True, timeout=20)
            second = subprocess.run(["sc.exe", "start", service], capture_output=True, text=True, timeout=20)
            return {"returncode": max(first.returncode, second.returncode), "stdout": (first.stdout + second.stdout)[-4000:], "stderr": (first.stderr + second.stderr)[-4000:]}
        result = subprocess.run(["sc.exe", command, service], capture_output=True, text=True, timeout=20)
    else:
        command = {"service_start": "start", "service_stop": "stop", "service_restart": "restart"}[action]
        result = subprocess.run(["systemctl", command, service], capture_output=True, text=True, timeout=20)
    return {"returncode": result.returncode, "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]}


def execute(job: dict) -> tuple[str, dict]:
    action = job["action"]
    params = job.get("params", {})
    if action.startswith("service_"):
        result = service_action(action, params["service"])
        return ("succeeded" if result["returncode"] == 0 else "failed", result)
    if action == "refresh_inventory":
        return "succeeded", {"inventory": inventory()}
    if action == "collect_diagnostics":
        vm = psutil.virtual_memory()
        result = {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "cpu_percent": psutil.cpu_percent(interval=0.4),
            "memory_percent": vm.percent,
            "load": getattr(os, "getloadavg", lambda: ())(),
            "uptime_seconds": max(0, int(time.time() - psutil.boot_time())),
            "process_count": len(psutil.pids()),
        }
        return "succeeded", result
    if action == "reboot":
        if platform.system().lower() == "windows":
            subprocess.Popen(["shutdown", "/r", "/t", "0"])
        else:
            subprocess.Popen(["systemctl", "reboot"])
        return "succeeded", {"message": "reboot requested"}
    if action == "shutdown":
        if platform.system().lower() == "windows":
            subprocess.Popen(["shutdown", "/s", "/t", "0"])
        else:
            subprocess.Popen(["systemctl", "poweroff"])
        return "succeeded", {"message": "shutdown requested"}
    return "failed", {"message": "unsupported action"}


def register(controller: str, enrollment_token: str, name: str) -> dict:
    payload = {"enrollment_token": enrollment_token, "name": name, "hostname": socket.gethostname(), "platform": platform.system(), "arch": platform.machine(), "os_version": platform.version()}
    response = request(controller, "/api/agent/register", "POST", payload)
    STATE_PATH.write_text(json.dumps(response, indent=2), encoding="utf-8")
    try:
        STATE_PATH.chmod(0o600)
    except OSError:
        pass
    return response


def run(controller: str, state: dict) -> None:
    agent_key = state["agent_key"]
    interval = int(state.get("heartbeat_interval_seconds", 15))
    while True:
        heartbeat = {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "arch": platform.machine(),
            "os_version": platform.version(),
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage(Path.cwd()).percent,
            "uptime_seconds": max(0, int(time.time() - psutil.boot_time())),
            "inventory": inventory(),
            "labels": {},
        }
        try:
            request(controller, "/api/agent/heartbeat", "POST", heartbeat, agent_key)
            polled = request(controller, "/api/agent/jobs/poll", "POST", {}, agent_key)
            if polled.get("job"):
                job = polled["job"]
                try:
                    status, result = execute(job)
                except Exception as exc:
                    status, result = "failed", {"error": str(exc)}
                request(controller, f"/api/agent/jobs/{job['id']}/report", "POST", {"status": status, "result": result}, agent_key)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"Helix agent communication error: {exc}")
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Glowhaven Helix server agent")
    parser.add_argument("--controller", required=True)
    parser.add_argument("--enrollment-token")
    parser.add_argument("--name", default=socket.gethostname())
    args = parser.parse_args()
    if args.enrollment_token:
        state = register(args.controller, args.enrollment_token, args.name)
    elif STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    else:
        raise SystemExit("Provide --enrollment-token for first registration.")
    run(args.controller, state)


if __name__ == "__main__":
    main()
