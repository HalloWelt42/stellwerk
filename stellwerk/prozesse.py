"""Welche Prozesse das Stellwerk für einen Teil führt, welches Programm das ist, seit wann es läuft und wie viel
eingeblendete Dateien es im Arbeitsspeicher hält.

Geführt werden bei einem selbst gestarteten Teil die lebenden Prozesse seiner Prozessgruppe, bei einem übernommenen
Teil (lief schon, sein Port antwortete) der lauschende Prozess mit seinen Nachfahren: genau die Prozesse, die das
Stellwerk misst und beim Anhalten beendet (Dienstkern). Docker-Teile führen keine Prozesse auf diesem Rechner, ihre
Container leben in der virtuellen Maschine der Laufzeit.

Die Liste geht über `GET /api/stand` (Feld `pids` je Teil) an den Maschinenraum, der damit Prozesse den Webapps
zuordnet. Die Laufzeit eines Teils zählt ab dem Start seines ältesten Prozesses.

Das Programm ist der lesbare Name (Regel des Dienstkerns, `programmname`) des Hauptprozesses: des übernommenen oder des
Gruppenführers; ist der nur eine Hülle (eine Shell, env), der nächste Prozess, der keine ist. Der feste Speicher kommt
wie bisher aus dem Bericht des Dienstkerns; hier nur der eingeblendete Anteil (`prozess_speicher`, derselbe Aufruf).
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Iterable
from pathlib import Path

from dienstkern.messen import GIB, MAC, Prozesstabelle, befehl, programmname, prozess_speicher, rechenzeit
from pydantic import BaseModel


class Fuehrung(BaseModel):
    """Was der Dienstkern über einen Teil weiß: seine eigene Prozessgruppe oder den übernommenen Prozess."""

    gruppe: int | None = None
    fremd_pid: int | None = None


HUELLEN = {"sh", "bash", "zsh", "dash", "fish", "env", "nohup"}     # starten nur ein anderes Programm


class Prozesse(BaseModel):
    pids: list[int] = []
    seit: float | None = None               # Start des ältesten Prozesses, Sekunden seit 1970
    programm: str | None = None             # lesbarer Name des Hauptprozesses, etwa qdrant, caddy, rechtschreibung.pruefserver
    eingeblendet_gb: float | None = None    # eingeblendete Dateien im Arbeitsspeicher (GiB); None: nicht getrennt messbar


def gefuehrt(f: Fuehrung, tabelle: Prozesstabelle) -> list[int]:
    if f.gruppe is not None:
        return sorted(tabelle.in_gruppe(f.gruppe))
    if f.fremd_pid is not None:
        return sorted(p for p in tabelle.mit_nachfahren(f.fremd_pid) if p in tabelle.eltern)
    return []


def programm(f: Fuehrung, pids: list[int], tabelle: Prozesstabelle) -> str | None:
    """Name des Hauptprozesses; ist er eine Hülle, der des nächsten Prozesses, der keine ist."""
    haupt = f.fremd_pid if f.fremd_pid is not None else f.gruppe
    namen = [programmname(tabelle.befehlszeile.get(p, "")) for p in sorted(pids, key=lambda p: (p != haupt, p))]
    namen = [n for n in namen if n]
    return next((n for n in namen if n not in HUELLEN), namen[0] if namen else None)


def eingeblendet_gb(pids: list[int]) -> float | None:
    if not pids:
        return None
    teile = [prozess_speicher(p).eingeblendet for p in pids]
    return None if any(t is None for t in teile) else sum(teile) / GIB


def startzeiten(pids: Iterable[int]) -> dict[int, float]:
    """Startzeitpunkt je Prozess in Sekunden seit 1970; wer nicht (mehr) lesbar ist, fehlt."""
    gesucht = set(pids)
    if not gesucht:
        return {}
    return _startzeiten_mac(gesucht) if MAC else _startzeiten_linux(gesucht)


def _startzeiten_mac(gesucht: set[int]) -> dict[int, float]:
    """`ps -o etime`: vergangene Zeit seit dem Start, [[TT-]SS:]MM:SS."""
    try:
        ausgabe = befehl("ps", "-A", "-o", "pid=,etime=")
    except (OSError, subprocess.SubprocessError):
        return {}
    jetzt, zeiten = time.time(), {}
    for zeile in ausgabe.splitlines():
        teile = zeile.split()
        if len(teile) == 2 and teile[0].isdigit() and int(teile[0]) in gesucht:
            try:
                zeiten[int(teile[0])] = round(jetzt - rechenzeit(teile[1]), 1)
            except ValueError:
                continue
    return zeiten


def _startzeiten_linux(gesucht: set[int]) -> dict[int, float]:
    """/proc/<pid>/stat Feld 22: Start in Taktschritten nach dem Systemstart (btime aus /proc/stat)."""
    try:
        start = next(int(z.split()[1]) for z in Path("/proc/stat").read_text().splitlines() if z.startswith("btime "))
    except (OSError, StopIteration, ValueError):
        return {}
    takt, zeiten = os.sysconf("SC_CLK_TCK"), {}
    for pid in gesucht:
        try:
            rest = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            zeiten[pid] = round(start + int(rest[19]) / takt, 1)
        except (OSError, IndexError, ValueError):
            continue
    return zeiten


def erfassen(fuehrung: dict[str, Fuehrung]) -> dict[str, Prozesse]:
    """Für alle Teile auf einmal (eine Prozesstabelle, eine Abfrage der Startzeiten); blockiert."""
    tabelle = Prozesstabelle()
    pids = {k: gefuehrt(f, tabelle) for k, f in fuehrung.items()}
    zeiten = startzeiten(p for liste in pids.values() for p in liste)
    return {k: Prozesse(pids=liste, seit=min((zeiten[p] for p in liste if p in zeiten), default=None),
                        programm=programm(fuehrung[k], liste, tabelle), eingeblendet_gb=eingeblendet_gb(liste))
            for k, liste in pids.items()}
