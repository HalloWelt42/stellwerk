"""Schnittstelle: Stand, Schalten je Webapp, Protokolle, Schutz, Fassung und Auslieferung der Oberfläche."""

from __future__ import annotations

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
