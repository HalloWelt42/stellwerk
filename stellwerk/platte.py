"""Plattenbelegung je Teil: was ein Teil auf der Platte hält.

Gezählt wird, was die App-Datei unter `daten` nennt (Ordner oder Dateien, gemessen mit `du`), bei Docker-Teilen dazu
die benannten Volumes ihres Dienstes in der Compose-Datei (Größen aus `docker system df -v`, eine Abfrage für alle).
Welche Volumes und welches Abbild ein Docker-Teil hat, sagt `docker compose <compose> config`, mit genau den Optionen
des Teils; das braucht die Laufzeit nicht.

Gemessen wird selten und gepuffert, nie beim Seitenaufruf: im Messtakt jeder Teil, der noch nie oder vor mehr als
`platte.abstand_s` Sekunden gemessen wurde, nacheinander in einem eigenen Faden (die Platte wird nicht mit vielen
gleichzeitigen Läufen belastet). Docker-Teile nur, solange Docker läuft; das Stellwerk startet Docker dafür nie. Die
Schnittstelle liest nur den Puffer.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from dienstkern.messen import GIB
from pydantic import BaseModel

from .konfig import Art, Plattenmessung, Teil

log = logging.getLogger("stellwerk")

EINHEIT = {"B": 1, "kB": 1e3, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12, "PB": 1e15}     # Docker zählt dezimal
GROESSE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([kKMGTP]?B)\s*$")


class Belegung(BaseModel):
    gb: float | None            # GiB auf drei Stellen (etwa 1 MB); None: nichts davon messbar (die Meldung sagt, warum)
    geprueft: float             # Zeitpunkt der Messung, Sekunden seit 1970
    meldung: str = ""           # was fehlte oder scheiterte; leer, wenn alles gemessen ist


class ComposeDienst(BaseModel):
    """Was die Compose-Datei über den Dienst eines Docker-Teils sagt."""

    abbild: str | None          # Name des Abbilds; selbst gebaut: Projekt-Dienst, wie Compose es benennt
    volumes: list[str]          # volle Namen der benannten Volumes


class _Fehler(Exception):
    """Messung gescheitert, mit kurzem Grund für die Oberfläche."""


def _ausfuehren(args: list[str], frist_s: float, ordner: Path | None = None, pfad: str | None = None,
                umgebung: dict[str, str] | None = None) -> str:
    env = {**os.environ, "LC_ALL": "C", **(umgebung or {}), **({"PATH": pfad} if pfad else {})}
    try:
        r = subprocess.run(args, cwd=ordner, env=env, capture_output=True, text=True, timeout=frist_s, check=False)
    except subprocess.TimeoutExpired:
        raise _Fehler(f"{args[0]} {args[1]}: keine Antwort binnen {frist_s:g} s") from None
    except OSError as f:
        raise _Fehler(f"{args[0]}: {f.strerror or f}") from None
    if r.returncode != 0:
        zeile = (r.stderr.strip().splitlines() or [f"Rückgabe {r.returncode}"])[-1]
        raise _Fehler(f"{args[0]} {args[1]}: {zeile[:160]}")
    return r.stdout


def pfad_bytes(p: Path, frist_s: float) -> int:
    """Belegte Größe eines Ordners oder einer Datei (Blöcke wie `du`, harte Verweise einmal)."""
    if not p.exists():
        raise _Fehler(f"fehlt: {p}")
    ausgabe = _ausfuehren(["du", "-s", "-k", "-H", str(p)], frist_s)
    try:
        return int(ausgabe.split()[0]) * 1024
    except (IndexError, ValueError):
        raise _Fehler(f"du: unlesbare Ausgabe für {p}") from None


def docker_groesse(text: str) -> int:
    """Größe aus der Ausgabe von Docker, etwa 1.249GB, 5.689MB, 264B."""
    m = GROESSE.match(text)
    if not m:
        raise ValueError(f"unbekannte Größe {text!r}")
    return int(float(m.group(1)) * EINHEIT[m.group(2)])


def compose_lesen(t: Teil, frist_s: float) -> ComposeDienst:
    """Abbild und benannte Volumes des Dienstes, aus `docker compose <compose> config` im Ordner des Teils."""
    ausgabe = _ausfuehren(["docker", "compose", *t.compose, "config", "--format", "json"], frist_s, ordner=t.ordner, pfad=t.pfad,
                          umgebung=t.umgebung)
    try:
        d = json.loads(ausgabe)
        dienst = d["services"][t.container]
    except (ValueError, KeyError, TypeError):
        raise _Fehler(f"docker compose config: kein Dienst {t.container}") from None
    projekt = d.get("name") or ""
    benannt = d.get("volumes") or {}
    volumes = []
    for v in dienst.get("volumes") or []:
        if isinstance(v, dict) and v.get("type") == "volume" and v.get("source"):
            volumes.append((benannt.get(v["source"]) or {}).get("name") or f"{projekt}_{v['source']}")
    abbild = dienst.get("image") or (f"{projekt}-{t.container}" if projekt else None)
    return ComposeDienst(abbild=abbild, volumes=volumes)


def volume_groessen(pfad: str, frist_s: float) -> dict[str, int]:
    """Alle Volumes der Laufzeit mit ihrer Größe in Byte; eine Abfrage, dauert einige Sekunden."""
    ausgabe = _ausfuehren(["docker", "system", "df", "-v", "--format", "json"], frist_s, pfad=pfad)
    try:
        eintraege = json.loads(ausgabe).get("Volumes") or []
    except (ValueError, AttributeError):
        raise _Fehler("docker system df: unlesbare Ausgabe") from None
    groessen = {}
    for v in eintraege:
        try:
            groessen[v["Name"]] = docker_groesse(v["Size"])
        except (KeyError, TypeError, ValueError):
            continue
    return groessen


def messen(t: Teil, compose: ComposeDienst | None, volumes: dict[str, int] | Exception | None, frist_s: float) -> Belegung | None:
    """Belegung eines Teils; None, wenn es nichts zu messen gibt (keine Datenorte, keine Volumes). Was fehlt, steht in
    der Meldung; gezählt wird, was messbar war."""
    summe, gemessen, fehler = 0, 0, []
    for p in t.daten:
        try:
            summe += pfad_bytes(p, frist_s)
            gemessen += 1
        except _Fehler as f:
            fehler.append(str(f))
    for name in compose.volumes if compose else []:
        if isinstance(volumes, Exception):
            fehler.append(str(volumes))
            break
        if volumes is not None and name in volumes:
            summe += volumes[name]
            gemessen += 1
        else:
            fehler.append(f"Volume {name} nicht gefunden")
    if not gemessen and not fehler:
        return None
    return Belegung(gb=round(summe / GIB, 3) if gemessen else None, geprueft=time.time(), meldung="; ".join(fehler))


class Plattenpuffer:
    """Puffer der Belegung je Teil (Kennung des Dienstes, `<app>.<teil>`) und des Compose-Stands der Docker-Teile."""

    def __init__(self, einstellungen: Plattenmessung, docker_pfad: str) -> None:
        self.einstellungen = einstellungen
        self.docker_pfad = docker_pfad
        self.belegung: dict[str, Belegung] = {}
        self.compose: dict[str, ComposeDienst] = {}
        self.compose_fehler: dict[str, str] = {}
        self._versucht: dict[str, tuple[float, tuple]] = {}     # letzte Messung je Teil (auch ohne Ergebnis) mit ihrer Grundlage

    def stand(self, kennung: str) -> Belegung | None:
        return self.belegung.get(kennung)

    def abbild(self, kennung: str) -> str | None:
        c = self.compose.get(kennung)
        return c.abbild if c else None

    @staticmethod
    def _grundlage(t: Teil) -> tuple:
        """Was die Messung bestimmt; ändert es sich in der App-Datei, wird der Teil gleich neu gemessen."""
        return (tuple(t.daten), t.art, tuple(t.compose), t.container, t.ordner)

    def _faellig(self, teile: dict[str, Teil], docker_laeuft: bool) -> list[str]:
        jetzt = time.time()
        faellig = []
        for k, t in teile.items():
            if not (t.daten or t.art == Art.DOCKER) or (t.art == Art.DOCKER and not docker_laeuft):
                continue
            zeit, grundlage = self._versucht.get(k, (0.0, ()))
            if grundlage != self._grundlage(t) or jetzt - zeit >= self.einstellungen.abstand_s:
                faellig.append(k)
        return faellig

    def _runde_blockierend(self, teile: dict[str, Teil], faellig: list[str]) -> None:
        frist = self.einstellungen.frist_s
        for k, t in teile.items():
            if t.art == Art.DOCKER and (k in faellig or (k not in self.compose and k not in self.compose_fehler)):
                try:
                    self.compose[k] = compose_lesen(t, frist)
                    self.compose_fehler.pop(k, None)
                except _Fehler as f:
                    if self.compose_fehler.get(k) != str(f):
                        log.warning("Compose-Stand von %s nicht lesbar: %s", k, f)
                    self.compose_fehler[k] = str(f)
        volumes: dict[str, int] | Exception | None = None
        if any(self.compose.get(k) and self.compose[k].volumes for k in faellig):
            try:
                volumes = volume_groessen(self.docker_pfad, frist)
            except _Fehler as f:
                volumes = f
        for k in faellig:
            t = teile[k]
            b = messen(t, self.compose.get(k), volumes, frist)
            if b is not None and t.art == Art.DOCKER and k in self.compose_fehler:
                b.meldung = "; ".join(x for x in (self.compose_fehler[k], b.meldung) if x)
            if b is None and k in self.compose_fehler:
                b = Belegung(gb=None, geprueft=time.time(), meldung=self.compose_fehler[k])
            if b is None:
                self.belegung.pop(k, None)
            else:
                self.belegung[k] = b
            self._versucht[k] = (time.time(), self._grundlage(t))

    async def runde(self, teile: dict[str, Teil], docker_laeuft: bool) -> None:
        for k in [k for k in self.belegung if k not in teile]:      # was es nicht mehr gibt
            self.belegung.pop(k, None)
        for d in (self.compose, self.compose_fehler, self._versucht):
            for k in [k for k in d if k not in teile]:
                d.pop(k, None)
        for k, t in teile.items():                                 # Teil ohne Datenorte mehr: alte Messung gilt nicht
            if not (t.daten or t.art == Art.DOCKER):
                self.belegung.pop(k, None)
        faellig = self._faellig(teile, docker_laeuft)
        neu_compose = [k for k, t in teile.items() if t.art == Art.DOCKER and k not in self.compose and k not in self.compose_fehler]
        if faellig or neu_compose:
            await asyncio.to_thread(self._runde_blockierend, teile, faellig)

    async def schleife(self, quelle: Callable[[], dict[str, Teil]], docker_laeuft: Callable[[], bool], takt_s: Callable[[], float]) -> None:
        """Läuft neben der Prüfung der Teile; `quelle` liefert alle Teile aller Webapps nach Kennung des Dienstes."""
        while True:
            try:
                await self.runde(quelle(), docker_laeuft())
            except Exception:                                   # die Schleife darf nie sterben
                log.exception("Fehler in der Messung der Plattenbelegung")
            await asyncio.sleep(takt_s())
