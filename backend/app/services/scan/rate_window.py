"""
Live-Nutzungsfenster für Gemini (Issue #22).

In-Memory-Sliding-Window der letzten 60 Sekunden je Prozess für Requests (RPM)
und Tokens (TPM). Bewusst flüchtig — kein DB-Schema; ein Reset bei Neustart ist
in Ordnung ("live"-Anzeige, kein Abrechnungsbeleg).

Pure, testbare Struktur mit injizierbarer Zeit (Parameter `now`), damit Tests
ohne echtes Warten laufen. Produktiv wird `time.monotonic()` genutzt (immun
gegen Wanduhr-Sprünge durch NTP/Sommerzeit — korrekt für "letzte 60 s").
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

_FENSTER_SEKUNDEN = 60.0


def _jetzt() -> float:
    return time.monotonic()


@dataclass
class SlidingWindow:
    """Zeitfenster-Zähler: bucht (Requests, Tokens) mit Zeitstempel und summiert
    nur die Einträge, deren Alter kleiner als `fenster` Sekunden ist."""

    fenster: float = _FENSTER_SEKUNDEN
    _events: "deque[tuple[float, int, int]]" = field(default_factory=deque, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, *, requests: int = 1, tokens: int = 0, now: Optional[float] = None) -> None:
        """Bucht Requests/Tokens mit Zeitstempel und verwirft Altes (>= Fenster)."""
        t = _jetzt() if now is None else now
        with self._lock:
            self._events.append((t, int(requests), int(tokens)))
            self._prune(t)

    def snapshot(self, now: Optional[float] = None) -> tuple[int, int]:
        """Aktueller Verbrauch (Requests, Tokens) im Fenster [now-fenster, now]."""
        t = _jetzt() if now is None else now
        with self._lock:
            self._prune(t)
            req = sum(e[1] for e in self._events)
            tok = sum(e[2] for e in self._events)
        return req, tok

    def _prune(self, now: float) -> None:
        # Einträge, deren Alter >= fenster ist, fallen raus (linkes Ende zuerst,
        # deque ist chronologisch).
        grenze = now - self.fenster
        ev = self._events
        while ev and ev[0][0] <= grenze:
            ev.popleft()


# Prozess-globaler Tracker (ein Nutzer, ein Prozess – LAN-App).
gemini_rate = SlidingWindow()
