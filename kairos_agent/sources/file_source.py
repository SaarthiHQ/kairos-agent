"""File-based log source — reads local log files via glob patterns."""

from __future__ import annotations

import glob as glob_mod
import logging
import time
from datetime import datetime
from pathlib import Path

from kairos_agent.sources import FetchedLines

logger = logging.getLogger("kairos_agent")


class FileSource:
    """Read log lines from local files matching a glob pattern."""

    def __init__(self, path: str) -> None:
        self._path = path

    @property
    def name(self) -> str:
        return f"file:{self._path}"

    def fetch(
        self,
        service_name: str,
        start: datetime,
        end: datetime,
    ) -> FetchedLines:
        t0 = time.monotonic()
        all_lines: list[str] = []
        matched_paths = sorted(glob_mod.glob(self._path))

        if not matched_paths:
            elapsed = (time.monotonic() - t0) * 1000
            logger.warning("No files matched pattern: %s", self._path)
            return FetchedLines(
                lines=[],
                source_name=self.name,
                line_count=0,
                fetch_duration_ms=elapsed,
                error=f"No files matched pattern: {self._path}",
            )

        for file_path in matched_paths:
            path = Path(file_path)
            if not path.is_file():
                continue
            try:
                lines = path.read_text(errors="replace").splitlines()
                all_lines.extend(f"[{path.name}] {line}" for line in lines)
            except OSError as e:
                logger.warning("Could not read %s: %s", file_path, e)

        elapsed = (time.monotonic() - t0) * 1000
        return FetchedLines(
            lines=all_lines,
            source_name=self.name,
            line_count=len(all_lines),
            fetch_duration_ms=elapsed,
        )
