"""Webapps mit ihren Teilen: lesen, prüfen, schalten in der Reihenfolge der Abhängigkeiten, Docker bei Bedarf."""

from __future__ import annotations

from pathlib import Path

from dienstkern.zustand import Soll, Zustand

from stellwerk.betrieb import AppZustand
from stellwerk.konfig import DOCKER, Art

from hilfen import freier_port, offen, schein_docker, server, stellwerk, verwalter


def zweiteilig(tmp: Path, port_b: int, port_o: int) -> str:
    return (f'name = "Probe"\noberflaeche = "http://localhost:{port_o}"\n'
            f'[[teile]]\nkennung = "oberflaeche"\nname = "Oberfläche"\nordner = "{tmp}"\nbefehl = {server(port_o)}\nport = {port_o}\nbraucht = ["backend"]\n'
            f'startzeit_s = 15\nanhaltezeit_s = 5\n'
            f'[[teile]]\nkennung = "backend"\nname = "Backend"\nordner = "{tmp}"\nbefehl = {server(port_b)}\nport = {port_b}\nstartzeit_s = 15\nanhaltezeit_s = 5\n')


async def test_webapp_startet_in_reihenfolge_und_haelt_umgekehrt_an(tmp_path: Path):
    port_b, port_o = freier_port(), freier_port()
    v = verwalter(stellwerk(tmp_path, {"probe": zweiteilig(tmp_path, port_b, port_o)}))
    await v.runde()
    app = v.apps["probe"]
    assert app.arten == [Art.NATIV] and v.zustand(app) == AppZustand.AUS and v.soll(app) is None
    assert sorted(v.dienste) == ["probe.backend", "probe.oberflaeche"]          # ohne Docker-Teile keine Laufzeit
    e = await v.app_starten("probe")
    assert e.erfolg, e.meldung
    assert offen(port_b) and offen(port_o)
    await v.runde()
    assert v.zustand(app) == AppZustand.LAEUFT and v.soll(app) == Soll.LAEUFT
    start_b = (tmp_path / "protokolle" / "probe.backend.log").stat().st_mtime_ns
    start_o = (tmp_path / "protokolle" / "probe.oberflaeche.log").stat().st_mtime_ns
    assert start_b <= start_o                                                   # Backend zuerst
    assert (await v.anhalten("probe.oberflaeche")).erfolg
    await v.runde()
    assert v.zustand(app) == AppZustand.TEILWEISE
    e = await v.app_anhalten("probe")
    assert e.erfolg and not offen(port_b) and not offen(port_o)
    await v.runde()
    assert v.zustand(app) == AppZustand.AUS and v.soll(app) == Soll.AUS


async def test_docker_startet_bei_bedarf_und_bleibt_bis_von_hand(tmp_path: Path):
    pfad = schein_docker(tmp_path)
    port_d, port_b = freier_port(), freier_port()
    text = (f'name = "Mit Datenbank"\n'
            f'[[teile]]\nkennung = "datenbank"\nname = "Datenbank"\nart = "docker"\nordner = "{tmp_path}"\ncompose = ["-f", "compose.yml"]\n'
            f'container = "web{port_d}"\nport = {port_d}\npfad = "{pfad}"\nstartzeit_s = 15\nanhaltezeit_s = 10\n'
            f'[[teile]]\nkennung = "backend"\nname = "Backend"\nordner = "{tmp_path}"\nbefehl = {server(port_b)}\nport = {port_b}\nbraucht = ["datenbank"]\n'
            f'startzeit_s = 15\nanhaltezeit_s = 5\n')
    v = verwalter(stellwerk(tmp_path, {"mitdb": text}, docker_pfad=pfad))
    await v.runde()
    assert DOCKER in v.dienste and v.dienste[DOCKER].zustand == Zustand.AUS
    e = await v.app_starten("mitdb")
    assert e.erfolg, e.meldung
    assert (tmp_path / "schein" / "laeuft").exists() and offen(port_d) and offen(port_b)
    await v.runde()
    assert v.zustand(v.apps["mitdb"]) == AppZustand.LAEUFT and v.dienste[DOCKER].zustand == Zustand.LAEUFT
    e = await v.docker_anhalten()
    assert not e.erfolg and "Mit Datenbank" in e.meldung                      # nicht, solange Docker-Teile laufen
    assert (await v.app_anhalten("mitdb")).erfolg
    assert not offen(port_d) and not offen(port_b)
    assert (tmp_path / "schein" / "laeuft").exists()                            # Docker bleibt an
    await v.runde()
    e = await v.docker_anhalten()
    assert e.erfolg, e.meldung
    assert not (tmp_path / "schein" / "laeuft").exists()


async def test_scheiternder_teil_wird_gemeldet(tmp_path: Path):
    port_b, port_o = freier_port(), freier_port()
    text = zweiteilig(tmp_path, port_b, port_o).replace(server(port_b), '["/gibt/es/nicht"]')
    v = verwalter(stellwerk(tmp_path, {"probe": text}))
    await v.runde()
    e = await v.app_starten("probe")
    assert not e.erfolg and e.meldung.startswith("Probe Backend:") and not offen(port_o)
    await v.runde()
    assert v.zustand(v.apps["probe"]) == AppZustand.GESTOERT


def _fehler(tmp: Path, text: str) -> str:
    o = stellwerk(tmp, {"x": text})
    apps, fehler = o.apps()
    assert not apps and len(fehler) == 1
    return fehler[0].meldung


def test_dateien_werden_streng_geprueft(tmp_path: Path):
    teil = f'[[teile]]\nkennung = "a"\nname = "A"\nordner = "{tmp_path}"\n'
    assert "Maschinenraum" in _fehler(tmp_path, f'name = "X"\nfaehigkeiten = ["stimme"]\n{teil}befehl = ["true"]\n')
    assert "braucht einen befehl" in _fehler(tmp_path, f'name = "X"\n{teil}')
    assert "container" in _fehler(tmp_path, f'name = "X"\n{teil}art = "docker"\nport = 1\n')
    assert "port oder pruefadresse" in _fehler(tmp_path, f'name = "X"\n{teil}art = "docker"\ncontainer = "c"\n')
    assert "ohne befehl" in _fehler(tmp_path, f'name = "X"\n{teil}art = "docker"\ncontainer = "c"\nport = 1\nbefehl = ["x"]\n')
    assert "es in dieser Webapp nicht gibt" in _fehler(tmp_path, f'name = "X"\n{teil}befehl = ["true"]\nbraucht = ["b"]\n')
    assert "doppelt" in _fehler(tmp_path, f'name = "X"\n{teil}befehl = ["true"]\n{teil}befehl = ["true"]\n')
    assert "unbekanntes Feld" in _fehler(tmp_path, f'name = "X"\n{teil}befehl = ["true"]\nstartzeitt_s = 1\n')
    assert "teile" in _fehler(tmp_path, 'name = "X"\n')
