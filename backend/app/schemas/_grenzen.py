"""Ganzzahl-Grenzen aus dem Spaltentyp (#117).

Postgres `integer` ist 32 Bit. Ein Wert darüber scheitert erst in der
Datenbank (500), statt als ungültige Eingabe abgelehnt zu werden (422) —
gefunden vom API-Fuzzing im Wochen-Scan. Die Grenze kommt aus dem Spaltentyp,
nicht aus einer geschätzten Fachobergrenze (lehren.md: Integer-Grenzen nur auf
PG messen).
"""

from typing import Annotated

from pydantic import Field

PG_INTEGER_MAX = 2**31 - 1

# Geldfelder: Numeric(8,2) → max. 999.999,99; ohne Grenze → Postgres-
# Overflow/500. Negative Beträge würden die Statistik still verfälschen → ge=0.
# (Zuerst für Sealed eingeführt, seit #117 hier zentral, auch für Karten.)
MONEY_FIELD = Field(default=None, ge=0, max_digits=8, decimal_places=2)

# Für Spalten vom Typ integer, die nie negativ sind (IDs, Slot-Indizes,
# Positionen, Binder-Größe).
PgNichtNegativ = Annotated[int, Field(ge=0, le=PG_INTEGER_MAX)]
