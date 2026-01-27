#!/usr/bin/env python3
"""
Supervisor process that watches for config changes and manages bot processes.
Polls Secrets Manager periodically and starts/stops bots as needed.
Monitors bot output for errors and handles restarts with backoff.
"""
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))  # seconds
MAX_RESTART_ATTEMPTS = int(os.environ.get("MAX_RESTART_ATTEMPTS", "5"))
RESTART_BACKOFF_BASE = int(os.environ.get("RESTART_BACKOFF_BASE", "5"))  # seconds
SCRIPT_DIR = Path(__file__).parent


def load_config():
    """Load config from AWS Secrets Manager or local bots.json"""
    secret_name = os.environ.get("AWS_SECRET_NAME")

    if secret_name:
        import boto3
        client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])

    config_path = os.environ.get("CONFIG_FILE", SCRIPT_DIR / "bots.json")
    with open(config_path) as f:
        return json.load(f)


@dataclass
class BotState:
    process: subprocess.Popen | None = None
    restart_count: int = 0
    last_restart: float = 0
    last_error: str | None = None
    healthy: bool = True


class BotSupervisor:
    def __init__(self):
        self.bots: dict[str, BotState] = {}
        self.shutdown_event = asyncio.Event()
        self.config_hash: str | None = None
        self.output_tasks: dict[str, asyncio.Task] = {}

    def _config_hash(self, config: dict) -> str:
        """Hash config to detect changes"""
        return json.dumps(config, sort_keys=True)

    async def _monitor_output(self, name: str, stream, is_stderr: bool):
        """Monitor bot output stream for errors"""
        prefix = f"[{name}]"
        error_keywords = ["error", "exception", "traceback", "failed", "critical"]

        while True:
            line = await asyncio.get_event_loop().run_in_executor(
                None, stream.readline
            )
            if not line:
                break

            text = line.decode("utf-8", errors="replace").rstrip()

            # Check for errors
            text_lower = text.lower()
            is_error = is_stderr or any(kw in text_lower for kw in error_keywords)

            if is_error:
                print(f"{prefix} ERROR: {text}", file=sys.stderr)
                if name in self.bots:
                    self.bots[name].last_error = text
                    self.bots[name].healthy = False
            else:
                print(f"{prefix} {text}")

    def _start_bot(self, name: str) -> BotState:
        """Start a bot process"""
        state = self.bots.get(name, BotState())

        # Check restart backoff
        if state.restart_count > 0:
            backoff = RESTART_BACKOFF_BASE * (2 ** min(state.restart_count - 1, 5))
            elapsed = time.time() - state.last_restart
            if elapsed < backoff:
                print(f"[supervisor] Bot {name} in backoff ({backoff - elapsed:.0f}s remaining)")
                return state

        # Check max restarts
        if state.restart_count >= MAX_RESTART_ATTEMPTS:
            print(f"[supervisor] Bot {name} exceeded max restarts ({MAX_RESTART_ATTEMPTS}), giving up")
            print(f"[supervisor] Last error: {state.last_error}")
            return state

        print(f"[supervisor] Starting bot: {name}" + (f" (attempt {state.restart_count + 1})" if state.restart_count > 0 else ""))

        proc = subprocess.Popen(
            [sys.executable, SCRIPT_DIR / "discord_bot.py", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        state.process = proc
        state.last_restart = time.time()
        state.healthy = True
        self.bots[name] = state

        # Start output monitors
        loop = asyncio.get_event_loop()
        self.output_tasks[f"{name}_stdout"] = loop.create_task(
            self._monitor_output(name, proc.stdout, is_stderr=False)
        )
        self.output_tasks[f"{name}_stderr"] = loop.create_task(
            self._monitor_output(name, proc.stderr, is_stderr=True)
        )

        return state

    def _stop_bot(self, name: str):
        """Stop a bot process gracefully"""
        if name not in self.bots or not self.bots[name].process:
            return

        print(f"[supervisor] Stopping bot: {name}")
        state = self.bots.pop(name)
        proc = state.process

        # Cancel output monitors
        for key in [f"{name}_stdout", f"{name}_stderr"]:
            if key in self.output_tasks:
                self.output_tasks.pop(key).cancel()

        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print(f"[supervisor] Force killing bot: {name}")
            proc.kill()

    def _check_health(self):
        """Check health of all bots, restart crashed ones"""
        for name, state in list(self.bots.items()):
            if not state.process:
                continue

            exit_code = state.process.poll()
            if exit_code is not None:
                # Process exited
                if exit_code == 0:
                    print(f"[supervisor] Bot {name} exited cleanly (locked?), not restarting")
                    self.bots.pop(name, None)
                else:
                    print(f"[supervisor] Bot {name} crashed (exit code {exit_code})")
                    if state.last_error:
                        print(f"[supervisor] Last error: {state.last_error}")
                    state.process = None
                    state.restart_count += 1
                    self._start_bot(name)

    async def sync_bots(self):
        """Sync running bots with config"""
        try:
            config = load_config()
        except Exception as e:
            print(f"[supervisor] Failed to load config: {e}", file=sys.stderr)
            return

        new_hash = self._config_hash(config)
        if new_hash != self.config_hash:
            print(f"[supervisor] Config changed, syncing bots...")
            self.config_hash = new_hash

        desired_bots = set(config.get("bots", {}).keys())
        running_bots = set(self.bots.keys())

        # Start new bots
        for name in desired_bots - running_bots:
            self._start_bot(name)

        # Stop removed bots
        for name in running_bots - desired_bots:
            self._stop_bot(name)

        # Check health and restart crashed bots
        self._check_health()

        # Reset restart count for healthy bots (running > 5 min)
        for name, state in self.bots.items():
            if state.process and state.healthy and state.restart_count > 0:
                if time.time() - state.last_restart > 300:
                    print(f"[supervisor] Bot {name} stable, resetting restart count")
                    state.restart_count = 0

    def _print_status(self):
        """Print current bot status"""
        print(f"[supervisor] Status: {len(self.bots)} bots")
        for name, state in self.bots.items():
            status = "running" if state.process and state.process.poll() is None else "stopped"
            health = "healthy" if state.healthy else "unhealthy"
            restarts = f"restarts={state.restart_count}" if state.restart_count > 0 else ""
            print(f"  {name}: {status} ({health}) {restarts}")

    async def run(self):
        """Main supervisor loop"""
        print(f"[supervisor] Starting (poll interval: {POLL_INTERVAL}s, max restarts: {MAX_RESTART_ATTEMPTS})")

        # Initial sync
        await self.sync_bots()
        self._print_status()

        while not self.shutdown_event.is_set():
            try:
                await asyncio.wait_for(
                    self.shutdown_event.wait(),
                    timeout=POLL_INTERVAL
                )
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue loop

            if not self.shutdown_event.is_set():
                await self.sync_bots()

        # Shutdown all bots
        print(f"[supervisor] Shutting down {len(self.bots)} bots...")
        for name in list(self.bots.keys()):
            self._stop_bot(name)
        print("[supervisor] Shutdown complete")

    def shutdown(self):
        """Signal shutdown"""
        print("[supervisor] Shutdown requested")
        self.shutdown_event.set()


def main():
    supervisor = BotSupervisor()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Handle signals
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, supervisor.shutdown)

    try:
        loop.run_until_complete(supervisor.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
