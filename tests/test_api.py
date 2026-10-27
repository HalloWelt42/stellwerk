"""Schnittstelle: Stand, Schalten je Webapp, Protokolle, Schutz, Fassung und Auslieferung der Oberfläche."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stellwerk import __version__, api
from stellwerk.api import erstellen

from hilfen import freier_port, offen, server, stellwerk

SCHREIBEN = {"X-Stellwerk": "1"}


def test_stand_schalten_und_protokoll(tmp_path: Path):
    port = freier_port()
    o = stellwerk(tmp_path, {"probe": f'name = "Probe"\nbeschreibung = "Zum Testen"\n[[teile]]\nkennung = "backend"\nname = "Backend"\n'
                                       f'ordner = "{tmp_path}"\nbefehl = {server(port)}\nport = {port}\nstartzeit_s = 15\nanhaltezeit_s = 5\n'})
    with TestClient(erstellen(o), base_url="http://127.0.0.1") as c:
        s = c.get("/api/stand").json()
        a = s["apps"][0]
        assert a["kennung"] == "probe" and a["zustand"] == "aus" and a["arten"] == ["nativ"] and s["docker"] is None
        assert a["teile"][0]["kennung"] == "backend" and a["teile"][0]["schaetzung_gb"] == 0.5
        assert c.post("/api/apps/probe/starten").status_code == 403                          # ohne Kopf
        r = c.post("/api/apps/probe/starten", headers=SCHREIBEN).json()
        assert r["erfolg"], r
        assert offen(port)
        r = c.post("/api/apps/probe/neustarten", headers=SCHREIBEN).json()
        assert r["erfolg"] and offen(port)
        zeilen = c.get("/api/apps/probe/teile/backend/protokoll?zeilen=50").json()["zeilen"]
        assert sum("gestartet vom Stellwerk" in z for z in zeilen) == 2
        assert c.get("/api/apps/probe/teile/gibtsnicht/protokoll").status_code == 404
        assert c.post("/api/apps/gibtsnicht/starten", headers=SCHREIBEN).status_code == 404
        assert not c.post("/api/docker/starten", headers=SCHREIBEN).json()["erfolg"]
        r = c.post("/api/apps/probe/anhalten", headers=SCHREIBEN).json()
        assert r["erfolg"] and not offen(port)
        assert c.get("/api/stand", headers={"host": "boese.example"}).status_code == 403


def test_fassung_und_auslieferung_der_oberflaeche(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Die Oberfläche vergleicht ihre Fassung mit /api/version; die Startseite kommt ohne Zwischenspeicher, auch für HEAD."""
    wurzel = (tmp_path / "oberflaeche").resolve()
    (wurzel / "assets").mkdir(parents=True)
    (wurzel / "index.html").write_text("<!doctype html>")
    (wurzel / "assets" / "index-abc123.js").write_text("")
    monkeypatch.setattr(api, "OBERFLAECHE", wurzel)
    with TestClient(erstellen(stellwerk(tmp_path / "ordner", {})), base_url="http://127.0.0.1") as c:
        assert c.get("/api/version").json() == {"version": __version__}
        for methode in ("GET", "HEAD"):
            for pfad in ("/", "/apps/probe"):
                a = c.request(methode, pfad)
                assert a.status_code == 200 and a.headers["cache-control"] == "no-cache", (methode, pfad)
            assert "immutable" in c.request(methode, "/assets/index-abc123.js").headers["cache-control"]


def _warten(c: TestClient, bedingung, sekunden: float = 8) -> dict:
    """Stand abfragen, bis die Bedingung gilt (der Verwalter misst im Takt von 1 s)."""
    ende = time.monotonic() + sekunden
    while True:
        s = c.get("/api/stand").json()
        if bedingung(s) or time.monotonic() > ende:
            return s
        time.sleep(0.2)


def test_teile_einzeln_pids_und_nutzt(tmp_path: Path):
    """Je Teil: Zweck, braucht, Prozesse (pids) und Laufzeit; Startreihenfolge; einzelne Teile schalten; äußere
    Abhängigkeiten mit gepufferter Prüfung."""
    port_b, port_o, zu = freier_port(), freier_port(), freier_port()
    teil = f'ordner = "{tmp_path}"\nstartzeit_s = 15\nanhaltezeit_s = 5\n'
    text = (f'name = "Probe"\nzweck = "Zum Testen"\n'
            f'[[teile]]\nkennung = "oberflaeche"\nname = "Oberfläche"\n{teil}befehl = {server(port_o)}\nport = {port_o}\nbraucht = ["backend"]\n'
            f'[[teile]]\nkennung = "backend"\nname = "Backend"\nzweck = "Schnittstelle"\n{teil}befehl = {server(port_b)}\nport = {port_b}\n'
            f'[[nutzt]]\nname = "Eigenes Backend"\nzweck = "Probe"\npruefadresse = "http://127.0.0.1:{port_b}/"\n'
            f'[[nutzt]]\nname = "Leitstelle"\nzweck = "KI-Aufträge"\nrechner = "127.0.0.1"\nport = {zu}\n')
    with TestClient(erstellen(stellwerk(tmp_path, {"probe": text})), base_url="http://127.0.0.1") as c:
        a = c.get("/api/stand").json()["apps"][0]
        assert a["zweck"] == "Zum Testen" and a["folge"] == ["backend", "oberflaeche"] and a["cpu_prozent"] is None
        o, b = a["teile"]
        assert o["braucht"] == ["backend"] and o["zweck"] is None and b["zweck"] == "Schnittstelle"
        assert o["pids"] == [] and o["laeuft_seit"] is None
        assert [n["name"] for n in a["nutzt"]] == ["Eigenes Backend", "Leitstelle"]
        assert c.post("/api/apps/probe/teile/oberflaeche/starten").status_code == 403              # ohne Kopf
        r = c.post("/api/apps/probe/teile/oberflaeche/starten", headers=SCHREIBEN).json()
        assert r["erfolg"] and offen(port_b) and offen(port_o), r
        s = _warten(c, lambda s: all(t["pids"] for t in s["apps"][0]["teile"]) and s["apps"][0]["nutzt"][0]["erreichbar"])
        a = s["apps"][0]
        for t in a["teile"]:
            assert t["pids"] and t["laeuft_seit"] is not None and s["zeit"] - 60 < t["laeuft_seit"] <= s["zeit"] + 1, t
        eigen, leitstelle = a["nutzt"]
        assert eigen["erreichbar"] and eigen["ziel"] == f"http://127.0.0.1:{port_b}/"
        assert leitstelle["erreichbar"] is False and leitstelle["meldung"] == "Verbindung abgelehnt" and leitstelle["ziel"] == f"127.0.0.1:{zu}"
        r = c.post("/api/apps/probe/teile/oberflaeche/anhalten", headers=SCHREIBEN).json()
        assert r["erfolg"] and offen(port_b) and not offen(port_o)
        o = c.get("/api/stand").json()["apps"][0]["teile"][0]
        assert o["zustand"] == "aus" and o["pids"] == []                                         # nie veraltete pids
        assert c.post("/api/apps/probe/teile/gibtsnicht/starten", headers=SCHREIBEN).status_code == 404
        assert c.post("/api/apps/probe/teile/backend/umfallen", headers=SCHREIBEN).status_code == 422
        assert c.post("/api/apps/probe/anhalten", headers=SCHREIBEN).json()["erfolg"] and not offen(port_b)
