"""Lightweight startup timing based only on the standard library."""

from __future__ import annotations

from time import perf_counter


class StartupProfiler:
    def __init__(self):
        self.started_at = perf_counter()
        self.milestones = []
        self.mark("Python-/App-Einstieg")

    def mark(self, label):
        elapsed = perf_counter() - self.started_at
        self.milestones.append((str(label), elapsed))
        return elapsed

    def log_summary(self):
        from loguru import logger
        for label, elapsed in self.milestones:
            logger.info("Startprofil: {:<32} {:>8.3f} s", label, elapsed)
