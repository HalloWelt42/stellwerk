"""Gemeinsame Hilfen: freie Ports, ein Stellwerk-Ordner mit Webapps und eine Schein-Laufzeit für Docker.

Die Schein-Laufzeit ist ein Programm `docker` in einem eigenen Ordner, der im Suchpfad der Teile steht: `desktop
start/stop` und `info` spielen die Laufzeit, `compose ... up -d webNNNN` startet einen HTTP-Server auf Port NNNN als
Container, `compose ... stop webNNNN` beendet ihn. `compose ... config` nennt die Dienste aus der Datei `dienste` mit dem
Abbild probe:1 und dem Volume probe_daten, `system df -v` gibt diesem Volume 1.5GB (beides als JSON wie die echte
Laufzeit)."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

from stellwerk.betrieb import Verwalter
from stellwerk.konfig import Ordner

SCHEIN_DOCKER = f'''#!{sys.executable}
import os, pathlib, signal, subprocess, sys
hier = pathlib.Path(__file__).resolve().parent
a = sys.argv[1:]
laeuft = hier / "laeuft"
if a[:2] == ["desktop", "start"]:
    laeuft.touch()
elif a[:2] == ["desktop", "stop"]:
    laeuft.unlink(missing_ok=True)
elif a[:1] == ["info"]:
    sys.exit(0 if laeuft.exists() else 1)
elif a[:1] == ["compose"] and "config" in a:
    import json
    dienste = {{n: {{"image": "probe:1", "volumes": [{{"type": "volume", "source": "daten", "target": "/daten"}}]}}
               for n in (hier / "dienste").read_text().split()}}
    print(json.dumps({{"name": "probe", "services": dienste, "volumes": {{"daten": {{"name": "probe_daten"}}}}}}))
elif a[:2] == ["system", "df"]:
    if not laeuft.exists():
        sys.exit("Docker läuft nicht")
    import json
    print(json.dumps({{"Volumes": [{{"Name": "probe_daten", "Size": "1.5GB"}}, {{"Name": "anderes", "Size": "264B"}}]}}))
elif a[:1] == ["compose"]:
    if not laeuft.exists():
        sys.exit("Docker läuft nicht")
    name = a[-1]
    if "up" in a:
        p = subprocess.Popen([sys.executable, "-m", "http.server", name[3:], "--bind", "127.0.0.1"], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (hier / name).write_text(str(p.pid))
    elif "stop" in a:
        os.kill(int((hier / name).read_text()), signal.SIGTERM)
'''


def freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def offen(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def server(port: int) -> str:
    return f'["{sys.executable}", "-m", "http.server", "{port}", "--bind", "127.0.0.1"]'


def schein_docker(tmp: Path, dienste: tuple[str, ...] = ()) -> str:
    """Legt die Schein-Laufzeit an; Rückgabe: Suchpfad mit ihr vorne."""
    ordner = tmp / "schein"
    ordner.mkdir(exist_ok=True)
    (ordner / "dienste").write_text(" ".join(dienste))
    (ordner / "docker").write_text(SCHEIN_DOCKER)
    (ordner / "docker").chmod(0o755)
    return f"{ordner}:/usr/bin:/bin"


def stellwerk(tmp: Path, apps: dict[str, str], docker_pfad: str | None = None) -> Ordner:
    (tmp / "apps").mkdir(parents=True, exist_ok=True)
    einstellungen = '[messung]\ntakt_s = 1\n[neustart]\npausen_s = [0.2]\n[nutzt]\nabstand_s = 1\nfrist_s = 1\n'
    if docker_pfad:
        einstellungen += f'[docker]\npfad = "{docker_pfad}"\nstartzeit_s = 15\nanhaltezeit_s = 10\nprozessmuster = "keiner-passt"\n'
    (tmp / "einstellungen.toml").write_text(einstellungen)
    for kennung, text in apps.items():
        (tmp / "apps" / f"{kennung}.toml").write_text(text)
    return Ordner(tmp)


def verwalter(o: Ordner) -> Verwalter:
    return Verwalter(o, o.einstellungen())
