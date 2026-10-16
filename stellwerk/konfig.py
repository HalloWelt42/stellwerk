"""Der Ordner des Stellwerks: ein Ort je Rechner für die eigenen Webapps.

    <ordner>/einstellungen.toml   Oberfläche, Messtakt, Neustartregeln, Docker
    <ordner>/apps/<kennung>.toml  je Webapp eine Datei mit ihren Teilen; der Dateiname ist die Kennung
    <ordner>/protokolle/          Ausgabe des Stellwerks und je Teil eine Datei
    <ordner>/zustand.json         Sollzustand je Teil (übersteht Neustarts) und gemessene Höchstwerte

Hier stehen nur Webapps und was sie zum Laufen brauchen (Backend, Oberfläche, Datenbank, Abholer). KI-Dienste mit
Fähigkeiten gehören in den Maschinenraum; die Webapps erreichen sie über die Leitstelle.
"""

from __future__ import annotations

import tomllib
from enum import Enum
from pathlib import Path
from typing import Any

from dienstkern.verwalter import Neustartregeln
from dienstkern.vorlage import STANDARD_PFAD, Ladefehler, Steuerung, Vorlage, dateien_lesen, pfad
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

STANDARD_ORDNER = "~/Stellwerk"
DOCKER = "docker"                       # Kennung der Container-Laufzeit unter den Teilen; Teile heißen <app>.<teil>
TEILKENNUNG = r"^[a-z0-9][a-z0-9_-]{0,63}$"


# ── Einstellungen ────────────────────────────────────────────────────────
class Oberflaeche(BaseModel):
    adresse: str = Field(default="127.0.0.1", description="nur dieser Rechner; 0.0.0.0 öffnet die Oberfläche fürs Netz")
    port: int = Field(default=8550, ge=1, le=65535)


class Messung(BaseModel):
    takt_s: float = Field(default=5.0, ge=1, le=300, description="Abstand der Prüfung und Messung der Teile")


class DockerLaufzeit(BaseModel):
    """Die Container-Laufzeit. Keine Webapp, sondern was Docker-Teile brauchen: das Stellwerk startet sie, wenn ein
    Docker-Teil startet, und hält sie nur von Hand an, wenn kein Docker-Teil mehr läuft."""

    befehl: list[str] = Field(default=["docker", "desktop", "start"], min_length=1)
    pruefbefehl: list[str] = Field(default=["docker", "info", "--format", "{{.ServerVersion}}"], min_length=1)
    anhaltebefehl: list[str] = Field(default=["docker", "desktop", "stop"], min_length=1)
    prozessmuster: str | None = Field(default=r"com\.apple\.Virtualization\.VirtualMachine", description="Prozesse, deren Speicher zählt (die virtuelle Maschine)")
    speicher_gb: float = Field(default=8.0, ge=0)
    startzeit_s: float = Field(default=240, gt=0)
    anhaltezeit_s: float = Field(default=180, gt=0)
    pfad: str = STANDARD_PFAD


class Einstellungen(BaseModel):
    name: str | None = Field(default=None, description="Anzeigename des Rechners; sonst der Rechnername")
    oberflaeche: Oberflaeche = Field(default_factory=Oberflaeche)
    messung: Messung = Field(default_factory=Messung)
    neustart: Neustartregeln = Field(default_factory=Neustartregeln)
    docker: DockerLaufzeit = Field(default_factory=DockerLaufzeit)


# ── Webapps ──────────────────────────────────────────────────────────────
class Art(str, Enum):
    NATIV = "nativ"     # ein eigener Prozess, der läuft, bis er angehalten wird
    DOCKER = "docker"   # ein Container aus der Compose-Datei des Projekts


class Teil(BaseModel):
    """Ein Teil einer Webapp: Backend, Oberfläche, Datenbank, Abholer."""

    model_config = ConfigDict(extra="forbid")

    kennung: str = Field(pattern=TEILKENNUNG)
    name: str
    art: Art = Art.NATIV
    ordner: Path
    befehl: list[str] = Field(default_factory=list, description="nativ: Programm und Argumente; ein relativer Programmpfad gilt ab ordner")
    vorher: list[str] = Field(default_factory=list, description="nativ: Befehl, der vor jedem Start einmal läuft")
    compose: list[str] = Field(default_factory=list, description="docker: Optionen vor dem Unterbefehl, genau wie das Projekt sie nutzt (Umgebungsdatei, Compose-Datei)")
    container: str | None = Field(default=None, description="docker: Name des Dienstes in der Compose-Datei")
    port: int | None = Field(default=None, ge=1, le=65535)
    pruefadresse: str | None = None
    speicher_gb: float = Field(default=0.5, ge=0, description="Schätzung bis zur ersten Messung")
    startzeit_s: float = Field(default=60, gt=0)
    anhaltezeit_s: float = Field(default=20, gt=0)
    umgebung: dict[str, str] = Field(default_factory=dict)
    umgebung_datei: Path | None = None
    pfad: str = STANDARD_PFAD
    neustart: bool = True
    braucht: list[str] = Field(default_factory=list, description="Teile derselben Webapp, die vorher laufen müssen")
    aktiv_ab_prozent: float = Field(default=5.0, ge=0)

    @field_validator("ordner", "umgebung_datei", mode="before")
    @classmethod
    def _aufloesen(cls, wert: object) -> object:
        return pfad(wert) if isinstance(wert, str) else wert

    @model_validator(mode="after")
    def _art_vollstaendig(self) -> Teil:
        if self.art == Art.NATIV:
            if not self.befehl:
                raise ValueError(f"Teil {self.kennung}: art = nativ braucht einen befehl")
            if self.compose or self.container:
                raise ValueError(f"Teil {self.kennung}: compose und container gelten nur für art = docker")
        else:
            if not self.container:
                raise ValueError(f"Teil {self.kennung}: art = docker braucht container (den Dienst in der Compose-Datei)")
            if self.befehl or self.vorher:
                raise ValueError(f"Teil {self.kennung}: art = docker startet über compose, ohne befehl und vorher")
            if not (self.port or self.pruefadresse):
                raise ValueError(f"Teil {self.kennung}: art = docker braucht port oder pruefadresse, um zu sehen, ob er läuft")
        return self


class App(BaseModel):
    """Eine Datei unter apps/: eine Webapp mit ihren Teilen."""

    model_config = ConfigDict(extra="forbid")

    kennung: str = Field(pattern=TEILKENNUNG)
    name: str
    beschreibung: str = ""
    oberflaeche: str | None = Field(default=None, description="Adresse der Webapp im Browser, zum Öffnen aus dem Stellwerk")
    teile: list[Teil] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _keine_ki_dienste(cls, daten: Any) -> Any:
        if isinstance(daten, dict) and "faehigkeiten" in daten:
            raise ValueError("faehigkeiten gibt es hier nicht: KI-Dienste gehören in den Maschinenraum, Webapps erreichen sie über die Leitstelle")
        return daten

    @model_validator(mode="after")
    def _teile_stimmig(self) -> App:
        kennungen = [t.kennung for t in self.teile]
        doppelt = sorted({k for k in kennungen if kennungen.count(k) > 1})
        if doppelt:
            raise ValueError(f"Teile doppelt: {', '.join(doppelt)}")
        for t in self.teile:
            fremd = [b for b in t.braucht if b not in kennungen or b == t.kennung]
            if fremd:
                raise ValueError(f"Teil {t.kennung} braucht {', '.join(fremd)}, das es in dieser Webapp nicht gibt")
        return self

    @property
    def arten(self) -> list[Art]:
        return [a for a in Art if any(t.art == a for t in self.teile)]

    def teilkennung(self, teil: str) -> str:
        return f"{self.kennung}.{teil}"


def teil_vorlage(app: App, t: Teil) -> Vorlage:
    """Ein Teil als Vorlage des Dienstkerns: nativ als Prozess, Docker als Befehlsdienst über compose, der die
    Laufzeit braucht."""
    gemeinsam: dict[str, Any] = dict(kennung=app.teilkennung(t.kennung), name=f"{app.name} {t.name}", ordner=t.ordner, port=t.port,
                                     pruefadresse=t.pruefadresse, speicher_gb=t.speicher_gb, startzeit_s=t.startzeit_s,
                                     anhaltezeit_s=t.anhaltezeit_s, umgebung=t.umgebung, umgebung_datei=t.umgebung_datei, pfad=t.pfad,
                                     neustart=t.neustart, aktiv_ab_prozent=t.aktiv_ab_prozent, braucht=[app.teilkennung(b) for b in t.braucht])
    if t.art == Art.NATIV:
        return Vorlage(**gemeinsam, befehl=t.befehl, vorher=t.vorher)
    compose = ["docker", "compose", *t.compose]
    return Vorlage(**{**gemeinsam, "braucht": [DOCKER, *gemeinsam["braucht"]]}, steuerung=Steuerung.BEFEHLE,
                   befehl=[*compose, "up", "-d", t.container], anhaltebefehl=[*compose, "stop", t.container])


def docker_vorlage(d: DockerLaufzeit) -> Vorlage:
    return Vorlage(kennung=DOCKER, name="Docker", ordner=Path.home(), steuerung=Steuerung.BEFEHLE, befehl=d.befehl, pruefbefehl=d.pruefbefehl,
                   anhaltebefehl=d.anhaltebefehl, prozessmuster=d.prozessmuster, speicher_gb=d.speicher_gb, startzeit_s=d.startzeit_s,
                   anhaltezeit_s=d.anhaltezeit_s, pfad=d.pfad, neustart=False,
                   beschreibung="Container-Laufzeit; der Speicher ist der der virtuellen Maschine mit allen Containern")


# ── Ordner ───────────────────────────────────────────────────────────────
def _toml_wert(w: object) -> str:
    if isinstance(w, bool):
        return "true" if w else "false"
    if isinstance(w, (int, float)):
        return repr(w)
    if isinstance(w, list):
        return "[" + ", ".join(_toml_wert(x) for x in w) + "]"
    return '"' + str(w).replace("\\", "\\\\").replace('"', '\\"') + '"'


def toml_schreiben(e: Einstellungen) -> str:
    """Einstellungen als TOML; leere Werte entfallen (gelten dann als Vorgabe)."""
    zeilen = ["# Einstellungen des Stellwerks. Webapps stehen im Ordner apps/.", ""]
    daten = e.model_dump(mode="json", exclude_none=True)
    for k, w in daten.items():
        if not isinstance(w, dict):
            zeilen.append(f"{k} = {_toml_wert(w)}")
    for k, w in daten.items():
        if isinstance(w, dict):
            zeilen += ["", f"[{k}]"] + [f"{n} = {_toml_wert(x)}" for n, x in w.items()]
    return "\n".join(zeilen) + "\n"


class Ordner:
    def __init__(self, wurzel: Path) -> None:
        self.wurzel = wurzel.expanduser().resolve()

    @property
    def apps_ordner(self) -> Path:
        return self.wurzel / "apps"

    @property
    def protokolle(self) -> Path:
        return self.wurzel / "protokolle"

    @property
    def zustand_datei(self) -> Path:
        return self.wurzel / "zustand.json"

    @property
    def einstellungsdatei(self) -> Path:
        return self.wurzel / "einstellungen.toml"

    def anlegen(self) -> None:
        for o in (self.wurzel, self.apps_ordner, self.protokolle):
            o.mkdir(parents=True, exist_ok=True)
        self.wurzel.chmod(0o700)
        if not self.einstellungsdatei.exists():
            neu = self.einstellungsdatei.with_suffix(".toml.neu")
            neu.write_text(toml_schreiben(Einstellungen()), encoding="utf-8")
            neu.replace(self.einstellungsdatei)

    def einstellungen(self) -> Einstellungen:
        try:
            with open(self.einstellungsdatei, "rb") as f:
                return Einstellungen.model_validate(tomllib.load(f))
        except FileNotFoundError:
            return Einstellungen()

    def apps(self) -> tuple[list[App], list[Ladefehler]]:
        """Alle Webapps; fehlerhafte Dateien werden gemeldet und ausgelassen, nie geraten."""
        return dateien_lesen(self.apps_ordner, App)


__all__ = ["App", "Art", "DOCKER", "DockerLaufzeit", "Einstellungen", "Ladefehler", "Ordner", "STANDARD_ORDNER", "Teil",
           "docker_vorlage", "teil_vorlage"]
