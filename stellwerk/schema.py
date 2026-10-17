"""JSON-Schema aller Daten, die die Oberfläche sieht. Eine Wahrheit: die Pydantic-Modelle.

`python -m stellwerk.schema` schreibt ein Schema mit allen Modellen unter `$defs`; die Oberfläche erzeugt daraus ihre
Typen (frontend/werkzeuge/typen.mjs).
"""

from __future__ import annotations

import json
import sys

from dienstkern.verwalter import Ergebnis
from dienstkern.web import Protokollauszug
from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from .api import Fassung, Stand

# Antworten: jedes Feld wird immer mitgeschickt, auch mit Vorgabewert (auch in eingebetteten Modellen)
AUSGABE: list[type[BaseModel]] = [Stand, Fassung, Ergebnis, Protokollauszug]


def schema() -> dict:
    _, defs = models_json_schema([(m, "serialization") for m in AUSGABE], title="Stellwerk")
    for d in defs.get("$defs", {}).values():
        if "properties" in d:
            d["required"] = list(d["properties"])
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Stellwerk", "type": "object",
            "properties": {m.__name__: {"$ref": f"#/$defs/{m.__name__}"} for m in AUSGABE}, **defs}


if __name__ == "__main__":
    json.dump(schema(), sys.stdout, ensure_ascii=False, indent=1)
