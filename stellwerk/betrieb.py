"""Betrieb der Webapps auf dem Dienstkern: aus jeder App-Datei werden ihre Teile (und bei Bedarf die Docker-Laufzeit)
zu Diensten des Kerns; geschaltet wird je Webapp, in der Reihenfolge ihrer Abhängigkeiten.

Starten, Anhalten, Neustarts nach Absturz, Sollzustand und Messung je Teil kommen aus dem Dienstkern (gemeinsam mit dem
Maschinenraum). Docker wird gestartet, sobald ein Docker-Teil startet, und nur von Hand angehalten, wenn kein
Docker-Teil mehr läuft. Je Takt hält der Verwalter zusätzlich fest, welche Prozesse er für jeden Teil führt und seit
wann sie laufen (prozesse.py).
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum

from dienstkern.dienst import Dienst
from dienstkern.verwalter import Ergebnis, Neustartregeln
from dienstkern.verwalter import Verwalter as Kernverwalter
from dienstkern.vorlage import Ladefehler, Vorlage, lesbar
from dienstkern.zustand import Soll, Zustand
from pydantic import ValidationError

from .konfig import DOCKER, App, Art, Einstellungen, Ordner, Teil, docker_vorlage, teil_vorlage
from .prozesse import Fuehrung, Prozesse, erfassen

log = logging.getLogger("stellwerk")


class AppZustand(str, Enum):
    AUS = "aus"
    STARTET = "startet"
    LAEUFT = "laeuft"
    TEILWEISE = "teilweise"    # manche Teile laufen, andere nicht
    STOPPT = "stoppt"
    GESTOERT = "gestoert"


class Schaltung(str, Enum):
    STARTEN = "starten"           # mit allem, was gebraucht wird, zuerst
    ANHALTEN = "anhalten"
    NEUSTARTEN = "neustarten"


def app_zustand(zustaende: list[Zustand]) -> AppZustand:
    if Zustand.GESTOERT in zustaende:
        return AppZustand.GESTOERT
    if Zustand.STARTET in zustaende:
        return AppZustand.STARTET
    if Zustand.STOPPT in zustaende:
        return AppZustand.STOPPT
    if all(z == Zustand.LAEUFT for z in zustaende):
        return AppZustand.LAEUFT
    if all(z == Zustand.AUS for z in zustaende):
        return AppZustand.AUS
    return AppZustand.TEILWEISE


class Verwalter(Kernverwalter):
    """Alle Webapps des Ordners. Läuft unabhängig von der Oberfläche."""

    def __init__(self, ordner: Ordner, einstellungen: Einstellungen) -> None:
        self.ordner = ordner
        self.einstellungen = einstellungen
        self.apps: dict[str, App] = {}
        self.prozesse: dict[str, Prozesse] = {}         # je Teil (Kennung des Dienstes), Stand des letzten Takts
        super().__init__(self._lesen, ordner.protokolle, ordner.zustand_datei, herkunft="vom Stellwerk")

    @property
    def regeln(self) -> Neustartregeln:
        return self.einstellungen.neustart

    @property
    def takt_s(self) -> float:
        return self.einstellungen.messung.takt_s

    def _lesen(self) -> tuple[list[Vorlage], list[Ladefehler]]:
        apps, fehler = self.ordner.apps()
        vorlagen: list[Vorlage] = []
        gelesen: dict[str, App] = {}
        for app in apps:
            try:
                vorlagen += [teil_vorlage(app, t) for t in app.teile]
                gelesen[app.kennung] = app
            except ValidationError as e:
                fehler.append(Ladefehler(datei=f"{app.kennung}.toml", meldung=lesbar(e)))
        if any(t.art == Art.DOCKER for a in gelesen.values() for t in a.teile):
            vorlagen.append(docker_vorlage(self.einstellungen.docker))
        self.apps = gelesen
        return vorlagen, fehler

    # ── Teile einer Webapp ───────────────────────────────────────────────
    def teile(self, app: App) -> list[Dienst]:
        return [self.dienste[k] for k in (app.teilkennung(t.kennung) for t in app.teile) if k in self.dienste]

    def zustand(self, app: App) -> AppZustand:
        return app_zustand([d.zustand for d in self.teile(app)])

    def docker_apps(self) -> list[App]:
        return [a for a in self.apps.values() if Art.DOCKER in a.arten]

    def folge(self, app: App) -> list[Teil]:
        """Startreihenfolge der Teile: wer gebraucht wird, zuerst (Reihenfolge des Dienstkerns). Anhalten umgekehrt."""
        nach_kennung = {app.teilkennung(t.kennung): t for t in app.teile}
        return [nach_kennung[k] for k in self.reihenfolge(list(nach_kennung))]

    async def runde(self) -> None:
        """Takt des Dienstkerns, danach die Prozesse je Teil (eigene Tabelle, im eigenen Faden)."""
        await super().runde()
        fuehrung = {k: Fuehrung(gruppe=d.stand.gruppe, fremd_pid=d.fremd_pid) for k, d in self.dienste.items()}
        self.prozesse = await asyncio.to_thread(erfassen, fuehrung)

    # ── Schalten ─────────────────────────────────────────────────────────
    async def app_schalten(self, kennung: str, schaltung: Schaltung) -> Ergebnis:
        if schaltung == Schaltung.STARTEN:
            return await self.app_starten(kennung)
        if schaltung == Schaltung.ANHALTEN:
            return await self.app_anhalten(kennung)
        return await self.app_neu_starten(kennung)

    async def teil_schalten(self, kennung: str, teil: str, schaltung: Schaltung) -> Ergebnis:
        """Ein einzelner Teil: Starten bringt erst, was er braucht (auch Docker); Anhalten trifft nur ihn, Teile, die
        ihn brauchen, laufen weiter."""
        app = self.apps.get(kennung)
        if app is None or not any(t.kennung == teil for t in app.teile):
            return Ergebnis(ziel=f"{kennung}.{teil}", erfolg=False, meldung=f"unbekannter Teil {kennung}.{teil}")
        k = app.teilkennung(teil)
        if schaltung == Schaltung.STARTEN:
            return await self.starten(k)
        if schaltung == Schaltung.ANHALTEN:
            return await self.anhalten(k)
        return await self.neu_starten(k)

    async def app_starten(self, kennung: str) -> Ergebnis:
        """Alle Teile, wer gebraucht wird zuerst; scheitert ein Teil, bleibt es dabei (die übrigen laufen weiter)."""
        app = self.apps.get(kennung)
        if app is None:
            return Ergebnis(ziel=kennung, erfolg=False, meldung=f"unbekannte Webapp {kennung}")
        for t in self.folge(app):
            k = app.teilkennung(t.kennung)
            e = await self.starten(k)
            if not e.erfolg:
                return Ergebnis(ziel=kennung, erfolg=False, meldung=f"{self.dienste[k].vorlage.name}: {e.meldung}")
        return Ergebnis(ziel=kennung, erfolg=True, meldung="läuft")

    async def app_anhalten(self, kennung: str) -> Ergebnis:
        """Alle Teile in umgekehrter Folge: wer andere braucht, zuerst. Docker bleibt an (nur von Hand)."""
        app = self.apps.get(kennung)
        if app is None:
            return Ergebnis(ziel=kennung, erfolg=False, meldung=f"unbekannte Webapp {kennung}")
        fehler = []
        for t in reversed(self.folge(app)):
            k = app.teilkennung(t.kennung)
            e = await self.anhalten(k)
            if not e.erfolg:
                fehler.append(f"{self.dienste[k].vorlage.name}: {e.meldung}")
        return Ergebnis(ziel=kennung, erfolg=not fehler, meldung="; ".join(fehler) or "aus")

    async def app_neu_starten(self, kennung: str) -> Ergebnis:
        aus = await self.app_anhalten(kennung)
        if not aus.erfolg:
            return aus
        return await self.app_starten(kennung)

    async def docker_starten(self) -> Ergebnis:
        if DOCKER not in self.dienste:
            return Ergebnis(ziel=DOCKER, erfolg=False, meldung="keine Webapp mit Docker-Teilen")
        return await self.starten(DOCKER)

    async def docker_anhalten(self) -> Ergebnis:
        """Nur wenn kein Docker-Teil mehr läuft; sonst stünden laufende Webapps ohne ihre Container da."""
        if DOCKER not in self.dienste:
            return Ergebnis(ziel=DOCKER, erfolg=False, meldung="keine Webapp mit Docker-Teilen")
        laufend = sorted({a.name for a in self.docker_apps() for t in a.teile
                          if t.art == Art.DOCKER and self.dienste.get(a.teilkennung(t.kennung)) is not None
                          and self.dienste[a.teilkennung(t.kennung)].zustand != Zustand.AUS})
        if laufend:
            return Ergebnis(ziel=DOCKER, erfolg=False, meldung=f"Docker-Teile laufen noch ({', '.join(laufend)}); erst diese Webapps anhalten")
        return await self.anhalten(DOCKER)

    def soll(self, app: App) -> Soll | None:
        """Soll laufen, wenn ein Teil laufen soll; aus, wenn das für alle entschieden ist; sonst nie entschieden."""
        werte = {d.stand.soll for d in self.teile(app)}
        if Soll.LAEUFT in werte:
            return Soll.LAEUFT
        return Soll.AUS if werte == {Soll.AUS} else None
