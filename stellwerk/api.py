"""Lokale Schnittstelle und Oberfläche des Stellwerks.

Standardmäßig nur auf diesem Rechner erreichbar (127.0.0.1). Schutz gegen fremde Webseiten im selben Browser (aus dem
Dienstkern): nur bekannte Rechnernamen im Host-Kopf und schreibende Aufrufe nur mit dem Kopf `X-Stellwerk: 1`.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dienstkern.dienst import Dienst
from dienstkern.verwalter import Ergebnis
from dienstkern.vorlage import Ladefehler
from dienstkern.web import Protokollauszug, oberflaeche_ausliefern, protokoll_ende, schutz_einrichten
from dienstkern.zustand import Soll, Zustand
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import __version__
from .betrieb import AppZustand, Verwalter
from .konfig import DOCKER, App, Art, Einstellungen, Ordner, Teil

log = logging.getLogger("stellwerk")
OBERFLAECHE = Path(__file__).resolve().parent / "oberflaeche"


class TeilAnsicht(BaseModel):
    kennung: str
    name: str
    art: Art
    port: int | None
    zustand: Zustand
    fremd: bool
    gb_jetzt: float | None          # gemessen, solange er läuft (Docker-Teile: im Speicher der Laufzeit, hier nicht einzeln)
    spitze_gb: float | None
    schaetzung_gb: float
    cpu_prozent: float | None
    aktiv: bool
    soll: Soll | None
    meldung: str
    ordner: str
    protokolldatei: str


class AppAnsicht(BaseModel):
    kennung: str
    name: str
    beschreibung: str
    oberflaeche: str | None
    arten: list[Art]
    zustand: AppZustand
    soll: Soll | None
    gb_jetzt: float | None          # Summe der gemessenen Teile
    teile: list[TeilAnsicht]
    datei: str


class DockerAnsicht(BaseModel):
    zustand: Zustand
    gb_jetzt: float | None
    soll: Soll | None
    meldung: str
    apps: list[str]                 # Namen der Webapps mit Docker-Teilen
    protokolldatei: str


class Stand(BaseModel):
    version: str
    rechner: str
    zeit: float
    ordner: str
    einstellungen: Einstellungen
    apps: list[AppAnsicht]
    docker: DockerAnsicht | None    # nur, wenn eine Webapp Docker-Teile hat
    ladefehler: list[Ladefehler]


def _teil(t: Teil, d: Dienst) -> TeilAnsicht:
    b = d.bericht()
    return TeilAnsicht(kennung=t.kennung, name=t.name, art=t.art, port=b.port, zustand=b.zustand, fremd=b.fremd, gb_jetzt=b.gb_jetzt,
                       spitze_gb=b.spitze_gb, schaetzung_gb=t.speicher_gb, cpu_prozent=b.cpu_prozent, aktiv=b.aktiv, soll=b.soll,
                       meldung=b.meldung, ordner=str(t.ordner), protokolldatei=str(d.protokolldatei()))


class Laufzeit:
    """Alles, was während des Betriebs lebt; einmal je Anwendung."""

    def __init__(self, ordner: Ordner) -> None:
        self.ordner = ordner
        self.verwalter = Verwalter(ordner, ordner.einstellungen())
        self.aufgaben: list[asyncio.Task] = []

    async def starten(self) -> None:
        self.aufgaben = [asyncio.create_task(self.verwalter.schleife(), name="apps")]

    async def beenden(self) -> None:
        for t in self.aufgaben:
            t.cancel()
        await asyncio.gather(*self.aufgaben, return_exceptions=True)
        await self.verwalter.beenden()

    def app(self, a: App) -> AppAnsicht:
        v = self.verwalter
        teile = [_teil(t, v.dienste[a.teilkennung(t.kennung)]) for t in a.teile if a.teilkennung(t.kennung) in v.dienste]
        gemessen = [t.gb_jetzt for t in teile if t.gb_jetzt is not None]
        return AppAnsicht(kennung=a.kennung, name=a.name, beschreibung=a.beschreibung, oberflaeche=a.oberflaeche, arten=a.arten,
                          zustand=v.zustand(a), soll=v.soll(a), gb_jetzt=round(sum(gemessen), 2) if gemessen else None, teile=teile,
                          datei=str(self.ordner.apps_ordner / f"{a.kennung}.toml"))

    def docker(self) -> DockerAnsicht | None:
        d = self.verwalter.dienste.get(DOCKER)
        if d is None:
            return None
        b = d.bericht()
        return DockerAnsicht(zustand=b.zustand, gb_jetzt=b.gb_jetzt, soll=b.soll, meldung=b.meldung,
                             apps=[a.name for a in self.verwalter.docker_apps()], protokolldatei=str(d.protokolldatei()))

    def stand(self) -> Stand:
        e = self.verwalter.einstellungen
        return Stand(version=__version__, rechner=e.name or socket.gethostname().removesuffix(".local"), zeit=time.time(),
                     ordner=str(self.ordner.wurzel), einstellungen=self.ordner.einstellungen(),
                     apps=[self.app(a) for a in self.verwalter.apps.values()], docker=self.docker(), ladefehler=self.verwalter.ladefehler)


def erstellen(ordner: Ordner) -> FastAPI:
    ordner.anlegen()
    lz = Laufzeit(ordner)

    @asynccontextmanager
    async def lebenslauf(app: FastAPI):
        await lz.starten()
        log.info("Stellwerk %s, Ordner %s", __version__, ordner.wurzel)
        try:
            yield
        finally:
            await lz.beenden()

    app = FastAPI(title="Stellwerk", version=__version__, lifespan=lebenslauf)
    app.state.laufzeit = lz
    schutz_einrichten(app, lambda: lz.verwalter.einstellungen.oberflaeche.adresse, "X-Stellwerk")

    def webapp(kennung: str) -> App:
        a = lz.verwalter.apps.get(kennung)
        if a is None:
            raise HTTPException(404, "Diese Webapp gibt es nicht.")
        return a

    async def auszug(datei: Path, zeilen: int) -> Protokollauszug:
        return Protokollauszug(datei=str(datei), zeilen=await asyncio.to_thread(protokoll_ende, datei, zeilen))

    @app.get("/api/stand")
    async def stand() -> Stand:
        return lz.stand()

    @app.post("/api/apps/{kennung}/starten")
    async def starten(kennung: str) -> Ergebnis:
        return await lz.verwalter.app_starten(webapp(kennung).kennung)

    @app.post("/api/apps/{kennung}/anhalten")
    async def anhalten(kennung: str) -> Ergebnis:
        return await lz.verwalter.app_anhalten(webapp(kennung).kennung)

    @app.post("/api/apps/{kennung}/neustarten")
    async def neustarten(kennung: str) -> Ergebnis:
        return await lz.verwalter.app_neu_starten(webapp(kennung).kennung)

    @app.get("/api/apps/{kennung}/teile/{teil}/protokoll")
    async def teilprotokoll(kennung: str, teil: str, zeilen: int = 200) -> Protokollauszug:
        d = lz.verwalter.dienste.get(webapp(kennung).teilkennung(teil))
        if d is None:
            raise HTTPException(404, "Diesen Teil gibt es nicht.")
        return await auszug(d.protokolldatei(), zeilen)

    @app.post("/api/docker/starten")
    async def docker_starten() -> Ergebnis:
        return await lz.verwalter.docker_starten()

    @app.post("/api/docker/anhalten")
    async def docker_anhalten() -> Ergebnis:
        return await lz.verwalter.docker_anhalten()

    @app.get("/api/docker/protokoll")
    async def dockerprotokoll(zeilen: int = 200) -> Protokollauszug:
        d = lz.verwalter.dienste.get(DOCKER)
        if d is None:
            raise HTTPException(404, "Keine Webapp mit Docker-Teilen.")
        return await auszug(d.protokolldatei(), zeilen)

    @app.get("/api/protokoll")
    async def eigenes_protokoll(zeilen: int = 200) -> Protokollauszug:
        return await auszug(ordner.protokolle / "stellwerk.log", zeilen)

    oberflaeche_ausliefern(app, OBERFLAECHE)
    return app
