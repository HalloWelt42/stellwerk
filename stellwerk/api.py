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
from .betrieb import AppZustand, Schaltung, Verwalter
from .konfig import DOCKER, App, Art, Einstellungen, Nutzung, Ordner, Teil
from .nutzt import Erreichbarkeiten
from .platte import Belegung, Plattenpuffer
from .prozesse import Prozesse

log = logging.getLogger("stellwerk")
OBERFLAECHE = Path(__file__).resolve().parent / "oberflaeche"


class TeilAnsicht(BaseModel):
    kennung: str
    name: str
    zweck: str | None
    art: Art
    port: int | None
    braucht: list[str]              # Teile derselben Webapp, die vorher laufen müssen; Docker-Teile brauchen dazu die Laufzeit
    zustand: Zustand
    fremd: bool
    programm: str | None            # nativ: lesbarer Name des Hauptprozesses, solange er läuft (etwa qdrant); docker: Name des Abbilds
    gb_jetzt: float | None          # fest belegter Arbeitsspeicher, gemessen, solange er läuft (Docker-Teile: im Speicher der Laufzeit, hier nicht einzeln)
    eingeblendet_gb: float | None   # dazu eingeblendete Dateien im Arbeitsspeicher, die das System bei Bedarf freigibt; None: nicht gemessen
    spitze_gb: float | None
    schaetzung_gb: float
    cpu_prozent: float | None       # Prozent eines Kerns
    aktiv: bool
    soll: Soll | None
    meldung: str
    ordner: str
    protokolldatei: str
    pids: list[int]                 # Prozesse, die das Stellwerk für ihn führt (Prozessgruppe oder übernommener Prozess mit Nachfahren); Docker leer
    laeuft_seit: float | None       # Start seines ältesten Prozesses, Sekunden seit 1970
    daten: list[str]                # Datenorte aus der App-Datei, deren Größe als Platte zählt
    platte_gb: float | None         # belegte Platte (Datenorte und bei Docker die Volumes); None: nichts zu messen oder noch nicht gemessen
    platte_geprueft: float | None   # Zeitpunkt der letzten Plattenmessung, Sekunden seit 1970
    platte_meldung: str             # was bei der Plattenmessung fehlte oder scheiterte


class NutzungAnsicht(BaseModel):
    """Eine äußere Abhängigkeit mit der letzten gepufferten Prüfung."""

    name: str
    zweck: str
    ziel: str                       # geprüfte Adresse oder Rechner:Port
    erreichbar: bool | None         # None: noch nicht geprüft
    geprueft: float | None          # Zeitpunkt der letzten Prüfung, Sekunden seit 1970
    meldung: str


class AppAnsicht(BaseModel):
    kennung: str
    name: str
    zweck: str | None               # kurz, neben dem Namen; fehlt er, zeigt die Oberfläche einen Hinweis
    beschreibung: str
    oberflaeche: str | None
    arten: list[Art]
    zustand: AppZustand
    soll: Soll | None
    gb_jetzt: float | None          # Summe der gemessenen Teile, fest belegter Arbeitsspeicher
    eingeblendet_gb: float | None   # Summe der eingeblendeten Dateien der gemessenen Teile
    cpu_prozent: float | None       # Summe der gemessenen Teile, Prozent eines Kerns
    platte_gb: float | None         # Summe der gemessenen Plattenbelegung der Teile
    teile: list[TeilAnsicht]
    folge: list[str]                # Kennungen der Teile in Startreihenfolge (Anhalten umgekehrt)
    nutzt: list[NutzungAnsicht]
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


class Fassung(BaseModel):
    """Fassung des laufenden Programms; die Oberfläche vergleicht sie mit ihrer eingebauten und lädt bei Abweichung neu."""

    version: str


LAUFEND = (Zustand.LAEUFT, Zustand.STARTET, Zustand.STOPPT)


def _summe(werte: list[float | None], stellen: int) -> float | None:
    gemessen = [w for w in werte if w is not None]
    return round(sum(gemessen), stellen) if gemessen else None


def _teil(t: Teil, d: Dienst, p: Prozesse | None, platte: Belegung | None, abbild: str | None) -> TeilAnsicht:
    b = d.bericht()
    # Prozesse aus dem letzten Takt, nur solange er läuft (wie die Messwerte); nach dem Anhalten nie veraltete pids
    p = p if p is not None and b.zustand in LAUFEND else Prozesse()
    eingeblendet = round(p.eingeblendet_gb, 2) if p.eingeblendet_gb is not None and b.gb_jetzt is not None else None
    return TeilAnsicht(kennung=t.kennung, name=t.name, zweck=t.zweck, art=t.art, port=b.port, braucht=t.braucht, zustand=b.zustand,
                       fremd=b.fremd, programm=abbild if t.art == Art.DOCKER else p.programm, gb_jetzt=b.gb_jetzt,
                       eingeblendet_gb=eingeblendet, spitze_gb=b.spitze_gb, schaetzung_gb=t.speicher_gb, cpu_prozent=b.cpu_prozent,
                       aktiv=b.aktiv, soll=b.soll, meldung=b.meldung, ordner=str(t.ordner), protokolldatei=str(d.protokolldatei()),
                       pids=p.pids, laeuft_seit=p.seit, daten=[str(x) for x in t.daten], platte_gb=platte.gb if platte else None,
                       platte_geprueft=platte.geprueft if platte else None, platte_meldung=platte.meldung if platte else "")


class Laufzeit:
    """Alles, was während des Betriebs lebt; einmal je Anwendung."""

    def __init__(self, ordner: Ordner) -> None:
        self.ordner = ordner
        self.verwalter = Verwalter(ordner, ordner.einstellungen())
        self.erreichbarkeiten = Erreichbarkeiten(self.verwalter.einstellungen.nutzt)
        e = self.verwalter.einstellungen
        self.platte = Plattenpuffer(e.platte, e.docker.pfad)
        self.aufgaben: list[asyncio.Task] = []

    def nutzungen(self) -> list[Nutzung]:
        return [n for a in self.verwalter.apps.values() for n in a.nutzt]

    def alle_teile(self) -> dict[str, Teil]:
        return {a.teilkennung(t.kennung): t for a in self.verwalter.apps.values() for t in a.teile}

    def takt_s(self) -> float:
        return self.verwalter.takt_s

    def docker_laeuft(self) -> bool:
        d = self.verwalter.dienste.get(DOCKER)
        return d is not None and d.zustand == Zustand.LAEUFT

    async def starten(self) -> None:
        self.aufgaben = [asyncio.create_task(self.verwalter.schleife(), name="apps"),
                         asyncio.create_task(self.erreichbarkeiten.schleife(self.nutzungen, self.takt_s), name="nutzt"),
                         asyncio.create_task(self.platte.schleife(self.alle_teile, self.docker_laeuft, self.takt_s), name="platte")]

    async def beenden(self) -> None:
        for t in self.aufgaben:
            t.cancel()
        await asyncio.gather(*self.aufgaben, return_exceptions=True)
        await self.verwalter.beenden()

    def nutzung(self, n: Nutzung) -> NutzungAnsicht:
        e = self.erreichbarkeiten.stand(n)
        return NutzungAnsicht(name=n.name, zweck=n.zweck, ziel=n.ziel, erreichbar=e.erreichbar if e else None,
                              geprueft=e.geprueft if e else None, meldung=e.meldung if e else "")

    def app(self, a: App) -> AppAnsicht:
        v = self.verwalter
        teile = [_teil(t, v.dienste[k], v.prozesse.get(k), self.platte.stand(k), self.platte.abbild(k))
                 for t in a.teile if (k := a.teilkennung(t.kennung)) in v.dienste]
        return AppAnsicht(kennung=a.kennung, name=a.name, zweck=a.zweck, beschreibung=a.beschreibung, oberflaeche=a.oberflaeche,
                          arten=a.arten, zustand=v.zustand(a), soll=v.soll(a), gb_jetzt=_summe([t.gb_jetzt for t in teile], 2),
                          eingeblendet_gb=_summe([t.eingeblendet_gb for t in teile], 2), cpu_prozent=_summe([t.cpu_prozent for t in teile], 1),
                          platte_gb=_summe([t.platte_gb for t in teile], 3), teile=teile, folge=[t.kennung for t in v.folge(a)],
                          nutzt=[self.nutzung(n) for n in a.nutzt], datei=str(self.ordner.apps_ordner / f"{a.kennung}.toml"))

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

    @app.get("/api/version")
    async def fassung() -> Fassung:
        return Fassung(version=__version__)

    def teil(a: App, kennung: str) -> Dienst:
        d = lz.verwalter.dienste.get(a.teilkennung(kennung))
        if d is None or not any(t.kennung == kennung for t in a.teile):
            raise HTTPException(404, "Diesen Teil gibt es nicht.")
        return d

    @app.post("/api/apps/{kennung}/{schaltung}")
    async def app_schalten(kennung: str, schaltung: Schaltung) -> Ergebnis:
        """Ganze Webapp: starten (wer gebraucht wird, zuerst), anhalten (umgekehrt), neustarten."""
        return await lz.verwalter.app_schalten(webapp(kennung).kennung, schaltung)

    @app.post("/api/apps/{kennung}/teile/{teil_kennung}/{schaltung}")
    async def teil_schalten(kennung: str, teil_kennung: str, schaltung: Schaltung) -> Ergebnis:
        """Ein Teil: starten bringt erst, was er braucht; anhalten trifft nur ihn."""
        a = webapp(kennung)
        teil(a, teil_kennung)
        return await lz.verwalter.teil_schalten(a.kennung, teil_kennung, schaltung)

    @app.get("/api/apps/{kennung}/teile/{teil_kennung}/protokoll")
    async def teilprotokoll(kennung: str, teil_kennung: str, zeilen: int = 200) -> Protokollauszug:
        return await auszug(teil(webapp(kennung), teil_kennung).protokolldatei(), zeilen)

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
