import logging
import signal
import threading
import time
from collections import deque
from pathlib import Path

from waw_transit_pipeline.supervisor.process import ManagedProcess, ServiceSpec

logger = logging.getLogger("warsaw_transit_stream_supervisor")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Supervisor:
    _POLL_SEC = 0.5
    _BACKOFF_CAP_SEC = 30.0
    _RESTART_LIMIT = 5
    _RESTART_WINDOW_SEC = 60.0
    _SHUTDOWN_TIMEOUT_SEC = 30.0
    _BOOTSTRAP = ServiceSpec("gtfs-once", ("-m", "waw_transit_pipeline.gtfs.main"))
    _SERVICES = (
        ServiceSpec("ingest", ("-m", "waw_transit_pipeline.ingest.main")),
        ServiceSpec("gtfs-watch", ("-m", "waw_transit_pipeline.gtfs.main", "--watch")),
        ServiceSpec("processing", ("-m", "waw_transit_pipeline.processing.main")),
    )

    def __init__(self) -> None:
        self._stop = threading.Event()

    def run(self) -> None:
        self._register_system_signals()
        if not self._run_bootstrap():
            raise SystemExit(1)
        processes = [self._spawn(spec) for spec in self._SERVICES]
        for process in processes:
            process.start()
        self._supervise(processes)
        self._shutdown(processes)

    def _spawn(self, spec: ServiceSpec) -> ManagedProcess:
        return ManagedProcess(spec, _PROJECT_ROOT, self._BACKOFF_CAP_SEC)

    def _register_system_signals(self) -> None:
        signal.signal(signal.SIGINT, lambda *_: self._stop.set())
        signal.signal(signal.SIGTERM, lambda *_: self._stop.set())

    def _run_bootstrap(self) -> bool:
        process = self._spawn(self._BOOTSTRAP)
        process.start()
        code = process.wait()
        if code != 0:
            logger.critical("%s exited with code %d", process.name, code)
            return False
        return True

    def _supervise(self, processes: list[ManagedProcess]) -> None:
        failures: dict[str, deque[float]] = {process.name: deque() for process in processes}
        while not self._stop.is_set():
            now = time.monotonic()
            for process in processes:
                if process.is_running() or not process.ready():
                    continue
                attempts = failures[process.name]
                while attempts and now - attempts[0] > self._RESTART_WINDOW_SEC:
                    attempts.popleft()
                if len(attempts) >= self._RESTART_LIMIT:
                    logger.critical("%s keeps failing; stopping everything", process.name)
                    return
                attempts.append(now)
                logger.warning("%s exited with code %s", process.name, process.exit_code())
                process.schedule_restart(len(attempts))
                process.start()
            time.sleep(self._POLL_SEC)

    def _shutdown(self, processes: list[ManagedProcess]) -> None:
        logger.info("Stopping supervised services")
        for process in processes:
            process.terminate(self._SHUTDOWN_TIMEOUT_SEC)
        logger.info("All supervised services stopped")
