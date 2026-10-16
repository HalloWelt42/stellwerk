"""Stellwerk: startet und stoppt die eigenen Webapps eines Rechners, nativ oder mit Docker, je Webapp mit allen ihren
Teilen. Die Dienststeuerung kommt aus dem Dienstkern; KI nutzen die Webapps nur über die Leitstelle.

Die Fassung steht in `version.json` im Wurzelordner; bei einer Installation legt das Installationsskript sie
als `VERSION` ins Paket.
"""

from __future__ import annotations

from pathlib import Path

from dienstkern import fassung

__version__ = fassung(Path(__file__).resolve().parent)
