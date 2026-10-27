"""Startpunkt: `stellwerk [ordner]` (Vorgabe ~/Stellwerk) startet Verwaltung und Oberfläche der Webapps. `--liste`
zeigt nur den Stand.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

import uvicorn
from dienstkern.web import protokoll_einrichten

from .betrieb import Verwalter
from .konfig import STANDARD_ORDNER, Ordner
from .prozesse import Prozesse


def laufen(ordner: Ordner) -> None:
    from .api import erstellen
    ordner.anlegen()
    protokoll_einrichten(ordner.protokolle / "stellwerk.log")
    e = ordner.einstellungen()
    uvicorn.run(erstellen(ordner), host=e.oberflaeche.adresse, port=e.oberflaeche.port, log_level="warning", access_log=False)


async def liste(ordner: Ordner) -> None:
    v = Verwalter(ordner, ordner.einstellungen())
    await v.runde()
    for f in v.ladefehler:
        print(f"FEHLER  {f.datei}: {f.meldung}")
    for a in v.apps.values():
        print(f"{v.zustand(a).value:10} {a.kennung:20} {a.name} ({a.zweck or 'Zweck fehlt'})")
        for d in v.teile(a):
            b = d.bericht()
            jetzt = f"{b.gb_jetzt:5.1f} GB" if b.gb_jetzt is not None else "      -"
            pids = ",".join(str(p) for p in v.prozesse.get(d.kennung, Prozesse()).pids) or "-"
            print(f"  {b.zustand.value:9} {b.kennung:28} {jetzt}  Port {b.port or '-':>5}  Prozesse {pids}  {b.meldung}")


def main() -> None:
    p = argparse.ArgumentParser(prog="stellwerk", description="Stellwerk: startet und stoppt die eigenen Webapps dieses Rechners")
    p.add_argument("ordner", nargs="?", default=STANDARD_ORDNER, help="Ordner mit einstellungen.toml und apps/")
    p.add_argument("--liste", action="store_true", help="nur den Stand der Webapps zeigen")
    a = p.parse_args()
    ordner = Ordner(Path(a.ordner))
    if a.liste:
        logging.basicConfig(level=logging.WARNING)
        asyncio.run(liste(ordner))
    else:
        laufen(ordner)


if __name__ == "__main__":
    main()
