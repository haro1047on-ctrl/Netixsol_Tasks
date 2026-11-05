"""
deploy_live.py
==============
Master Multi-Project Deployment & Live Link Manager
for Netixsol Weeks 7, 8, 9, and 10 Projects.

This script launches all 4 projects simultaneously on isolated ports and
optionally initializes secure public HTTPS tunnels (via Pinggy / SSH or Localtunnel)
so that live public URLs are immediately generated for submission.

Ports Allocation:
- Week 7 (Real Estate AI Agent & Portal):       Port 8000 (FastAPI + Static Web App)
- Week 8 (AI Property Valuation & Lead Scoring): Port 8501 (Streamlit Intelligence Hub)
- Week 9 (City Care Clinics Healthcare AI):     Port 8502 (Streamlit Patient Portal)
- Week 10 (Zarya Digital Bank UrduLish Platform):Port 8503 (Streamlit Banking Portal)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from typing import Dict, List

# Set UTF-8 encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

PROJECTS = [
    {
        "week": "Week 7",
        "name": "Real Estate Hub — AI Voice & Chat Consultant",
        "type": "FastAPI + Web App",
        "port": 8000,
        "cwd": os.path.join(REPO_ROOT, "week7-RE_Agent", "day5-langgraph-agent"),
        "command": [
            sys.executable,
            "-m",
            "uvicorn",
            "vapi_server:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        "local_url": "http://localhost:8000",
        "cloud_alternative": "https://haro1047on-ctrl.github.io/Netixsol_Tasks/week7-RE_Agent/day5-langgraph-agent/website/",
    },
    {
        "week": "Week 8",
        "name": "AI Property Valuation & Lead Scoring Platform",
        "type": "Streamlit Intelligence Hub",
        "port": 8501,
        "cwd": REPO_ROOT,
        "command": [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            os.path.join("week8", "Day4", "app_dashboard.py"),
            "--server.port",
            "8501",
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
        ],
        "local_url": "http://localhost:8501",
        "cloud_file_path": "week8/Day4/app_dashboard.py",
    },
    {
        "week": "Week 9",
        "name": "City Care Clinics — Multi-Agent Healthcare Assistant",
        "type": "Streamlit Patient Intake Portal",
        "port": 8502,
        "cwd": REPO_ROOT,
        "command": [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            os.path.join("week9", "Day5", "src", "patient_web_app.py"),
            "--server.port",
            "8502",
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
        ],
        "local_url": "http://localhost:8502",
        "cloud_file_path": "week9/Day5/src/patient_web_app.py",
    },
    {
        "week": "Week 10",
        "name": "Zarya Digital Bank — Sovereign UrduLish Banking AI Platform",
        "type": "Streamlit Banking Concierge & Operations Hub",
        "port": 8503,
        "cwd": REPO_ROOT,
        "command": [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            os.path.join("src", "ui", "app.py"),
            "--server.port",
            "8503",
            "--server.address",
            "0.0.0.0",
            "--server.headless",
            "true",
        ],
        "local_url": "http://localhost:8503",
        "cloud_file_path": "src/ui/app.py",
    },
]


def check_ssh_available() -> bool:
    return shutil.which("ssh") is not None


def start_tunnel(port: int) -> subprocess.Popen | None:
    """Start an SSH reverse tunnel to Pinggy or Localhost.run for public HTTPS."""
    if not check_ssh_available():
        return None
    try:
        # Pinggy gives instant https url without account setup
        proc = subprocess.Popen(
            [
                "ssh",
                "-p",
                "443",
                "-R0:localhost:" + str(port),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "ServerAliveInterval=30",
                "qr@a.pinggy.io",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        return proc
    except Exception as e:
        print(f"Tunnel launch error on port {port}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Deploy Netixsol Week 7-10 Projects")
    parser.add_argument("--tunnel", action="store_true", help="Launch public HTTPS tunnels for all ports")
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 NETIXSOL MULTI-WEEK DEPLOYMENT MANAGER (WEEKS 7, 8, 9, 10)")
    print("=" * 80)
    print(f"Working Directory: {REPO_ROOT}")
    print(f"Python Executable: {sys.executable}")
    print(f"Public Tunnels Enabled: {args.tunnel}")
    print("-" * 80)

    processes: List[subprocess.Popen] = []
    tunnel_procs: Dict[int, subprocess.Popen] = {}

    try:
        for p in PROJECTS:
            print(f"[*] Starting {p['week']}: {p['name']} on port {p['port']}...")
            env = os.environ.copy()
            env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")

            proc = subprocess.Popen(
                p["command"],
                cwd=p["cwd"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            processes.append(proc)
            time.sleep(1.5)

            if args.tunnel:
                print(f"[*] Initiating public HTTPS tunnel for port {p['port']}...")
                t_proc = start_tunnel(p["port"])
                if t_proc:
                    tunnel_procs[p["port"]] = t_proc

        print("\n" + "=" * 80)
        print("✅ ALL 4 PROJECTS ARE ACTIVELY RUNNING")
        print("=" * 80)
        for p in PROJECTS:
            print(f"• {p['week']} [{p['type']}]:")
            print(f"  Local Access:  {p['local_url']}")
            if p.get("cloud_file_path"):
                print(f"  Streamlit Cloud Entrypoint: {p['cloud_file_path']}")
            elif p.get("cloud_alternative"):
                print(f"  Web Link / Pages: {p['cloud_alternative']}")

        if args.tunnel:
            print("\n" + "-" * 80)
            print("🌐 PUBLIC HTTPS LIVE TUNNEL OUTPUT:")
            print("-" * 80)
            print("Listening for public URLs from tunnel provider (press Ctrl+C to terminate)...")
            time.sleep(2)
            for port, tp in tunnel_procs.items():
                try:
                    for _ in range(10):
                        line = tp.stdout.readline()
                        if line and ("http://" in line or "https://" in line):
                            print(f"[Port {port}] Live Link: {line.strip()}")
                            break
                except Exception:
                    pass

        print("\nPress Ctrl+C anytime to cleanly stop all servers.")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[!] Shutting down all deployed servers and tunnels...")
        for p in processes:
            p.terminate()
        for tp in tunnel_procs.values():
            tp.terminate()
        print("[✓] All servers terminated successfully.")


if __name__ == "__main__":
    main()

