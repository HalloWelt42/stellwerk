"""Plattenbelegung je Teil (Feld daten, Volumes der Docker-Teile), Programm und eingeblendeter Speicher je Teil."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stellwerk.api import erstellen
from stellwerk.konfig import App, Plattenmessung
from stellwerk.platte import ComposeDienst, Plattenpuffer, docker_groesse, messen

from hilfen import freier_port, schein_docker, server, stellwerk

MIB = 1024**2


def _app(tmp: Path, **felder) -> App:
    return App.model_validate({"kennung": "probe", "name": "Probe", "teile": [
        {"kennung": "a", "name": "A", "ordner": str(tmp), "befehl": ["true"], **felder}]})


def test_daten_werden_aufgeloest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PROBE_ORT", str(tmp_path / "woanders"))
    t = _app(tmp_path, daten=["daten", "~/x", "$PROBE_ORT/y", "/abs/z"]).teile[0]
    assert t.daten == [tmp_path / "daten", Path.home() / "x", tmp_path / "woanders" / "y", Path("/abs/z")]
    assert _app(tmp_path).teile[0].daten == []


def test_docker_groessen():
    assert docker_groesse("264B") == 264
    assert docker_groesse("18.65kB") == 18650
    assert docker_groesse("1.249GB") == 1_249_000_000
    with pytest.raises(ValueError):
        docker_groesse("N/A")


def test_messen_zaehlt_was_da_ist_und_nennt_was_fehlt(tmp_path: Path):
    (tmp_path / "daten").mkdir()
    (tmp_path / "daten" / "a.bin").write_bytes(os.urandom(2 * MIB))
    (tmp_path / "einzeln.bin").write_bytes(os.urandom(MIB))
    t = _app(tmp_path, daten=["daten", "einzeln.bin", "fehlt"]).teile[0]
    b = messen(t, None, None, 10)
    assert b is not None and b.gb is not None and 2.9 <= b.gb * 1024 <= 4.1                    # 3 MB, in GiB auf drei Stellen
    assert b.meldung == f"fehlt: {tmp_path / 'fehlt'}"
    nichts = messen(_app(tmp_path, daten=["fehlt"]).teile[0], None, None, 10)
    assert nichts is not None and nichts.gb is None and "fehlt" in nichts.meldung
    assert messen(_app(tmp_path).teile[0], None, None, 10) is None                       # nichts zu messen
    c = ComposeDienst(abbild="x", volumes=["v1", "v2"])
    v = messen(_app(tmp_path).teile[0], c, {"v1": 1024**3}, 10)
    assert v is not None and v.gb == 1.0 and v.meldung == "Volume v2 nicht gefunden"


async def test_puffer_misst_selten_und_neu_bei_geaenderter_datei(tmp_path: Path):
    (tmp_path / "daten").mkdir()
    (tmp_path / "daten" / "a.bin").write_bytes(os.urandom(MIB))
    p = Plattenpuffer(Plattenmessung(abstand_s=3600), "/usr/bin:/bin")
    teil = _app(tmp_path, daten=["daten"]).teile[0]
    await p.runde({"probe.a": teil}, docker_laeuft=False)
    erst = p.stand("probe.a")
    assert erst is not None and erst.gb is not None and not erst.meldung
    (tmp_path / "daten" / "b.bin").write_bytes(os.urandom(4 * MIB))
    await p.runde({"probe.a": teil}, docker_laeuft=False)
    assert p.stand("probe.a") == erst                                       # noch nicht fällig
    anders = _app(tmp_path, daten=["daten", "daten/b.bin"]).teile[0]
    await p.runde({"probe.a": anders}, docker_laeuft=False)
    neu = p.stand("probe.a")
    assert neu is not None and neu.gb > erst.gb and neu.geprueft >= erst.geprueft    # Datei geändert: gleich neu
    await p.runde({"probe.a": _app(tmp_path).teile[0]}, docker_laeuft=False)
    assert p.stand("probe.a") is None                                       # keine Datenorte mehr
    await p.runde({}, docker_laeuft=False)
    assert not p.belegung and not p._versucht                               # Teil entfernt


async def test_docker_teil_abbild_und_volume(tmp_path: Path):
    """Abbild aus compose config auch ohne laufende Laufzeit; Volumes erst, wenn Docker läuft (nie dafür gestartet)."""
    pfad = schein_docker(tmp_path, ("db",))
    teil = App.model_validate({"kennung": "probe", "name": "Probe", "teile": [
        {"kennung": "db", "name": "Datenbank", "art": "docker", "ordner": str(tmp_path), "container": "db", "port": 1, "pfad": pfad}]}).teile[0]
    p = Plattenpuffer(Plattenmessung(), pfad)
    await p.runde({"probe.db": teil}, docker_laeuft=False)
    assert p.abbild("probe.db") == "probe:1" and p.stand("probe.db") is None
    assert not (tmp_path / "schein" / "laeuft").exists()
    (tmp_path / "schein" / "laeuft").touch()
    await p.runde({"probe.db": teil}, docker_laeuft=True)
    b = p.stand("probe.db")
    assert b is not None and b.gb == round(1.5e9 / 1024**3, 3) and not b.meldung


def test_stand_mit_programm_platte_und_eingeblendet(tmp_path: Path):
    port = freier_port()
    (tmp_path / "daten").mkdir()
    (tmp_path / "daten" / "a.bin").write_bytes(os.urandom(MIB))
    o = stellwerk(tmp_path, {"probe": f'name = "Probe"\n[[teile]]\nkennung = "backend"\nname = "Backend"\nordner = "{tmp_path}"\n'
                                       f'befehl = {server(port)}\nport = {port}\nstartzeit_s = 15\nanhaltezeit_s = 5\ndaten = ["daten"]\n'})
    with TestClient(erstellen(o), base_url="http://127.0.0.1") as c:
        assert c.post("/api/apps/probe/starten", headers={"X-Stellwerk": "1"}).json()["erfolg"]
        ende = time.monotonic() + 10
        while True:
            a = c.get("/api/stand").json()["apps"][0]
            t = a["teile"][0]
            if (t["programm"] and t["platte_gb"] is not None and t["gb_jetzt"] is not None) or time.monotonic() > ende:
                break
            time.sleep(0.2)
        assert t["programm"] == "http.server", t
        assert t["daten"] == [str(tmp_path / "daten")] and t["platte_gb"] is not None and t["platte_geprueft"] and not t["platte_meldung"]
        assert a["platte_gb"] == t["platte_gb"]
        if sys.platform == "darwin":
            assert t["eingeblendet_gb"] is not None and a["eingeblendet_gb"] is not None
        assert c.post("/api/apps/probe/anhalten", headers={"X-Stellwerk": "1"}).json()["erfolg"]
        t = c.get("/api/stand").json()["apps"][0]["teile"][0]
        assert t["programm"] is None and t["eingeblendet_gb"] is None and t["platte_gb"] is not None    # Platte bleibt
