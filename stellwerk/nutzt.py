"""Äußere Abhängigkeiten der Webapps (Feld `nutzt` der App-Dateien): ist erreichbar, was eine Webapp außerhalb ihrer
Teile braucht?

Geprüft wird gepuffert, nie beim Seitenaufruf: im Messtakt des Stellwerks jedes Ziel, das noch nie oder vor mehr als
`abstand_s` Sekunden geprüft wurde, mit kurzer Frist und alle fälligen nebeneinander. Gleiche Ziele mehrerer Webapps
(etwa die Leitstelle) werden nur einmal geprüft. Die Schnittstelle liest nur den Puffer.

Erreichbar heißt: eine Adresse antwortet unter 500, oder ein Port nimmt Verbindungen an. Zertifikate werden dabei nicht
geprüft (die eigenen Dienste im Heimnetz tragen selbst ausgestellte); gesendet wird nur eine leere Anfrage.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable

from pydantic import BaseModel

from .konfig import Nutzung, NutztPruefung

log = logging.getLogger("stellwerk")


class Erreichbarkeit(BaseModel):
    erreichbar: bool
    geprueft: float             # Zeitpunkt der Prüfung, Sekunden seit 1970
    meldung: str = ""           # Grund, wenn nicht erreichbar


class _Nicht(Exception):
    """Nicht erreichbar, mit kurzem Grund für die Oberfläche."""


def _grund(f: BaseException, frist_s: float) -> str:
    if isinstance(f, urllib.error.URLError) and isinstance(f.reason, BaseException):
        f = f.reason
    if isinstance(f, (TimeoutError, socket.timeout)):
        return f"keine Antwort binnen {frist_s:g} s"
    if isinstance(f, ConnectionRefusedError):
        return "Verbindung abgelehnt"
    if isinstance(f, socket.gaierror):
        return "Rechner unbekannt"
    return str(f)[:160] or f.__class__.__name__


def _ohne_zertifikat() -> ssl.SSLContext:
    kontext = ssl.create_default_context()
    kontext.check_hostname = False
    kontext.verify_mode = ssl.CERT_NONE
    return kontext


def _adresse(adresse: str, frist_s: float) -> None:
    anfrage = urllib.request.Request(adresse, headers={"User-Agent": "Stellwerk"})
    try:
        with urllib.request.urlopen(anfrage, timeout=frist_s, context=_ohne_zertifikat()) as antwort:
            code = antwort.status
    except urllib.error.HTTPError as f:
        code = f.code
    if code >= 500:
        raise _Nicht(f"antwortet mit {code}")


def _port(rechner: str, port: int, frist_s: float) -> None:
    with socket.create_connection((rechner, port), timeout=frist_s):
        pass


def pruefen(n: Nutzung, frist_s: float) -> Erreichbarkeit:
    """Eine Prüfung, höchstens etwa `frist_s` lang; blockiert (im eigenen Faden aufrufen)."""
    jetzt = time.time()
    try:
        if n.pruefadresse:
            _adresse(n.pruefadresse, frist_s)
        else:
            _port(n.rechner or "localhost", n.port or 0, frist_s)
    except _Nicht as f:
        return Erreichbarkeit(erreichbar=False, geprueft=jetzt, meldung=str(f))
    except (OSError, ValueError, urllib.error.URLError) as f:
        return Erreichbarkeit(erreichbar=False, geprueft=jetzt, meldung=_grund(f, frist_s))
    return Erreichbarkeit(erreichbar=True, geprueft=jetzt)


class Erreichbarkeiten:
    """Puffer der Prüfungen je Ziel (`Nutzung.ziel`)."""

    def __init__(self, einstellungen: NutztPruefung) -> None:
        self.einstellungen = einstellungen
        self.ergebnisse: dict[str, Erreichbarkeit] = {}

    def stand(self, n: Nutzung) -> Erreichbarkeit | None:
        """Letzte Prüfung des Ziels; None, solange es noch nicht geprüft ist."""
        return self.ergebnisse.get(n.ziel)

    async def runde(self, nutzungen: Iterable[Nutzung]) -> None:
        ziele = {n.ziel: n for n in nutzungen}
        self.ergebnisse = {k: e for k, e in self.ergebnisse.items() if k in ziele}     # was keine Webapp mehr nutzt
        jetzt = time.time()
        faellig = [n for k, n in ziele.items()
                   if k not in self.ergebnisse or jetzt - self.ergebnisse[k].geprueft >= self.einstellungen.abstand_s]
        frist = self.einstellungen.frist_s
        neu = await asyncio.gather(*(asyncio.to_thread(pruefen, n, frist) for n in faellig))
        for n, e in zip(faellig, neu):
            vorher = self.ergebnisse.get(n.ziel)
            if vorher is not None and vorher.erreichbar != e.erreichbar:
                log.info("%s (%s) %s", n.name, n.ziel, "wieder erreichbar" if e.erreichbar else f"nicht erreichbar: {e.meldung}")
            self.ergebnisse[n.ziel] = e

    async def schleife(self, quelle: Callable[[], list[Nutzung]], takt_s: Callable[[], float]) -> None:
        """Läuft neben der Prüfung der Teile; `quelle` liefert die äußeren Abhängigkeiten aller Webapps."""
        while True:
            try:
                await self.runde(quelle())
            except Exception:                                   # die Schleife darf nie sterben
                log.exception("Fehler in der Prüfung der äußeren Abhängigkeiten")
            await asyncio.sleep(takt_s())
