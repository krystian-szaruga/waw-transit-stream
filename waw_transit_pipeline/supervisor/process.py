import logging
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("warsaw_transit_stream_supervisor")


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    arguments: tuple[str, ...]


class ManagedProcess:
    def __init__(
        self,
        spec: ServiceSpec,
        working_directory: Path,
        backoff_cap: float,
    ) -> None:
        self._spec = spec
        self._working_directory = working_directory
        self._backoff_cap = backoff_cap
        self._process: subprocess.Popen[str] | None = None
        self._restart_at = 0.0

    @property
    def name(self) -> str:
        return self._spec.name

    def start(self) -> None:
        command = [sys.executable, *self._spec.arguments]
        logger.info("Starting %s", " ".join(self._spec.arguments))
        self._process = subprocess.Popen(
            command,
            cwd=self._working_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        threading.Thread(target=self._pump_output, daemon=True).start()

    def _pump_output(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            print(f"[{self._spec.name}] {line.rstrip()}", flush=True)

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def exit_code(self) -> int | None:
        return None if self._process is None else self._process.returncode

    def ready(self) -> bool:
        return time.monotonic() >= self._restart_at

    def schedule_restart(self, attempt: int) -> None:
        delay = min(self._backoff_cap, 2.0 ** (attempt - 1))
        self._restart_at = time.monotonic() + delay
        logger.warning("%s restarting in %.0fs", self._spec.name, delay)

    def wait(self) -> int:
        if self._process is None:
            return 1
        return self._process.wait()

    def terminate(self, timeout: float) -> None:
        process = self._process
        if process is None or process.poll() is not None:
            return
        self._signal_group(process, signal.SIGTERM)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning("%s did not stop in %.0fs; killing", self._spec.name, timeout)
            self._signal_group(process, signal.SIGKILL)
            process.wait()

    @staticmethod
    def _signal_group(process: subprocess.Popen[str], sig: int) -> None:
        try:
            os.killpg(os.getpgid(process.pid), sig)
        except ProcessLookupError:
            pass
