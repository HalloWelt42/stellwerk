"""Webapps mit ihren Teilen: lesen, prüfen, schalten in der Reihenfolge der Abhängigkeiten, Docker bei Bedarf."""

from __future__ import annotations

import subprocess
import sys
import time
import tomllib
from pathlib import Path

from dienstkern.zustand import Soll, Zustand

from stellwerk.betrieb import AppZustand, Schaltung
from stellwerk.konfig import DOCKER, App, Art

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


async def test_folge_und_einzelner_teil(tmp_path: Path):
    """Startreihenfolge kommt aus dem Dienstkern; ein Teil startet mit dem, was er braucht, und hält allein an."""
    port_b, port_o = freier_port(), freier_port()
    v = verwalter(stellwerk(tmp_path, {"probe": zweiteilig(tmp_path, port_b, port_o)}))
    await v.runde()
    app = v.apps["probe"]
    assert [t.kennung for t in v.folge(app)] == ["backend", "oberflaeche"]      # Datei nennt die Oberfläche zuerst
    e = await v.teil_schalten("probe", "oberflaeche", Schaltung.STARTEN)
    assert e.erfolg, e.meldung
    assert offen(port_b) and offen(port_o)                                      # das Backend kam zuerst mit
    assert (await v.teil_schalten("probe", "oberflaeche", Schaltung.ANHALTEN)).erfolg
    assert offen(port_b) and not offen(port_o)                                  # nur die Oberfläche hält an
    assert not (await v.teil_schalten("probe", "gibtsnicht", Schaltung.STARTEN)).erfolg
    assert (await v.app_schalten("probe", Schaltung.ANHALTEN)).erfolg
    assert not offen(port_b)


async def test_prozesse_je_teil(tmp_path: Path):
    """Eigener Teil: seine Prozessgruppe; übernommener Teil: der lauschende Prozess; Laufzeit ab dem ältesten Prozess."""
    port_e, port_f = freier_port(), freier_port()
    fremd = subprocess.Popen([sys.executable, "-m", "http.server", str(port_f), "--bind", "127.0.0.1"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        for _ in range(50):
            if offen(port_f):
                break
            time.sleep(0.1)
        teil = f'[[teile]]\nkennung = "backend"\nname = "Backend"\nordner = "{tmp_path}"\nstartzeit_s = 15\nanhaltezeit_s = 5\n'
        v = verwalter(stellwerk(tmp_path, {"eigen": f'name = "Eigen"\n{teil}befehl = {server(port_e)}\nport = {port_e}\n',
                                           "fremd": f'name = "Fremd"\n{teil}befehl = {server(port_f)}\nport = {port_f}\n'}))
        await v.runde()
        assert v.prozesse["eigen.backend"].pids == [] and v.prozesse["eigen.backend"].seit is None
        assert fremd.pid in v.prozesse["fremd.backend"].pids and v.dienste["fremd.backend"].fremd_pid == fremd.pid
        assert (await v.app_starten("eigen")).erfolg
        await v.runde()
        p = v.prozesse["eigen.backend"]
        gruppe = v.dienste["eigen.backend"].stand.gruppe
        assert gruppe in p.pids and p.seit is not None and time.time() - 60 < p.seit <= time.time() + 1
        assert (await v.app_anhalten("eigen")).erfolg
        await v.runde()
        assert v.prozesse["eigen.backend"].pids == []
    finally:
        fremd.terminate()
        fremd.wait(5)


def test_zweck_und_nutzt_werden_geprueft(tmp_path: Path):
    teil = f'[[teile]]\nkennung = "a"\nname = "A"\nordner = "{tmp_path}"\nbefehl = ["true"]\n'
    assert "höchstens 40" in _fehler(tmp_path, f'name = "X"\nzweck = "{"Wissen " * 8}"\n{teil}')
    assert "teile.0.zweck" in _fehler(tmp_path, f'name = "X"\n{teil}zweck = "{"x" * 41}"\n')
    assert "leer" in _fehler(tmp_path, f'name = "X"\nzweck = "  "\n{teil}')
    nutzt = '[[nutzt]]\nname = "Leitstelle"\nzweck = "KI-Aufträge"\n'
    assert "entweder pruefadresse oder port" in _fehler(tmp_path, f'name = "X"\n{teil}{nutzt}')
    assert "entweder pruefadresse oder port" in _fehler(tmp_path, f'name = "X"\n{teil}{nutzt}pruefadresse = "http://a"\nport = 1\n')
    assert "rechner gilt nur mit port" in _fehler(tmp_path, f'name = "X"\n{teil}{nutzt}pruefadresse = "http://a"\nrechner = "pi"\n')
    assert "http://" in _fehler(tmp_path, f'name = "X"\n{teil}{nutzt}pruefadresse = "pi:8530"\n')
    assert "zweck" in _fehler(tmp_path, f'name = "X"\n{teil}[[nutzt]]\nname = "Leitstelle"\nport = 8530\n')
    assert "nutzt doppelt: Leitstelle" in _fehler(tmp_path, f'name = "X"\n{teil}{nutzt}port = 1\n{nutzt}port = 2\n')
    # ohne Zweck lädt die Datei (alte Einträge laufen weiter, die Oberfläche zeigt einen Hinweis); Leerraum wird geglättet
    o = stellwerk(tmp_path / "gut", {"alt": f'name = "Alt"\n{teil}', "neu": f'name = "Neu"\nzweck = "  Wissens   speicher "\n{teil}zweck = "Suche"\n'
                                                                    f'{nutzt}rechner = "pi"\nport = 8530\n'})
    apps, fehler = o.apps()
    assert not fehler and [a.zweck for a in apps] == [None, "Wissens speicher"]
    assert apps[1].teile[0].zweck == "Suche" and apps[1].nutzt[0].ziel == "pi:8530"


def test_beispiel_ist_gueltig():
    """Das Beispiel im Repo besteht die Prüfung der App-Datei (Zweck, Teile, nutzt)."""
    datei = Path(__file__).resolve().parent.parent / "beispiele" / "notizbuch.toml"
    app = App.model_validate({**tomllib.loads(datei.read_text(encoding="utf-8")), "kennung": datei.stem})
    assert app.zweck and all(t.zweck for t in app.teile) and [n.name for n in app.nutzt] == ["Leitstelle", "Kellerwolke", "Fundus", "Vektorspeicher"]
