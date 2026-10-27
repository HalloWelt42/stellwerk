"""Äußere Abhängigkeiten: geprüft gepuffert (fällig nur nach dem Abstand), gleiche Ziele einmal, mit kurzem Grund."""

from __future__ import annotations

import socket

from stellwerk.konfig import Nutzung, NutztPruefung
from stellwerk.nutzt import Erreichbarkeiten, pruefen

from hilfen import freier_port


def test_port_und_adresse():
    with socket.socket() as lauscher:
        lauscher.bind(("127.0.0.1", 0))
        lauscher.listen()
        port = lauscher.getsockname()[1]
        assert pruefen(Nutzung(name="A", zweck="Probe", rechner="127.0.0.1", port=port), 1).erreichbar
    zu = pruefen(Nutzung(name="B", zweck="Probe", rechner="127.0.0.1", port=freier_port()), 1)
    assert not zu.erreichbar and zu.meldung == "Verbindung abgelehnt"
    adresse = pruefen(Nutzung(name="C", zweck="Probe", pruefadresse=f"http://127.0.0.1:{freier_port()}/"), 1)
    assert not adresse.erreichbar and adresse.meldung == "Verbindung abgelehnt"


async def test_gepuffert_und_gemeinsam():
    e = Erreichbarkeiten(NutztPruefung(abstand_s=60, frist_s=1))
    port = freier_port()
    leitstelle = Nutzung(name="Leitstelle", zweck="KI-Aufträge", rechner="127.0.0.1", port=port)
    gleiche = Nutzung(name="Leitstelle (andere Webapp)", zweck="KI", rechner="127.0.0.1", port=port)
    assert e.stand(leitstelle) is None                                          # noch nicht geprüft
    await e.runde([leitstelle, gleiche])
    erste = e.stand(leitstelle)
    assert erste is not None and not erste.erreichbar and e.stand(gleiche) is erste and len(e.ergebnisse) == 1
    await e.runde([leitstelle])
    assert e.stand(leitstelle) is erste                                         # vor Ablauf des Abstands nicht neu geprüft
    e.einstellungen = NutztPruefung(abstand_s=1, frist_s=1)
    erste.geprueft -= 2
    await e.runde([leitstelle])
    assert e.stand(leitstelle) is not erste                                     # fällig: neu geprüft
    await e.runde([])
    assert e.ergebnisse == {}                                                   # nutzt keiner mehr: vergessen
