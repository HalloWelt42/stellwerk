# Stellwerk

Ein Ort für die eigenen Webapps eines Rechners: Backend, Oberfläche, Datenbank und was eine Webapp sonst zum Laufen
braucht. Je Webapp eine Datei mit ihren Teilen, nativ als eigener Prozess oder als Container mit Docker. Ein Schalter
startet die ganze Webapp in der Reihenfolge ihrer Abhängigkeiten und hält sie in umgekehrter Folge wieder an. Statt dass
Projekte irgendwo im Hintergrund laufen, steht hier, was läuft, was es belegt und was es ausgibt.

- **Oberfläche im Browser** unter `http://127.0.0.1:8550/`, nur auf diesem Rechner erreichbar. Die Webapps als
  ausführliche Liste oder als Karten zum Überblick (Wahl je Gerät); ein Klick führt zur Detailansicht
  `/apps/<kennung>` mit allen Teilen, Starten und Anhalten je Teil, Protokollen und den Abhängigkeiten der Webapp.
- **Jede Webapp sagt, wofür sie da ist:** ein kurzer Zweck neben dem Namen (etwa "Wissensspeicher"), damit sich
  ähnliche Programme nicht verwechseln lassen. Das Stellwerk selbst heißt in Kopf und Titel "Stellwerk · App-Steuerung".
- **Im zentralen Steuerwerk:** Das Stellwerk trägt sich bei der Installation im [Maschinenraum](https://github.com/HalloWelt42/maschinenraum)
  ein. Dessen Menüleistensymbol startet, hält an und öffnet das Stellwerk und schaltet die Webapps.
- **Übersteht Neustarts:** läuft als launchd- oder systemd-Dienst; was laufen soll, startet wieder.
- **Abstürze** einzelner Teile werden mit Pausen neu gestartet; stürzt ein Teil zu oft ab, bleibt er aus.
- **Docker bei Bedarf:** startet ein Docker-Teil, startet das Stellwerk vorher Docker; angehalten wird Docker nur von
  Hand und nur, wenn kein Docker-Teil mehr läuft.

## Zusammenspiel

Das Stellwerk gehört zu [Leitstelle](https://github.com/HalloWelt42/leitstelle),
[Maschinenraum](https://github.com/HalloWelt42/maschinenraum) und [Klangwerk](https://github.com/HalloWelt42/klangwerk).
Die Webapps im Stellwerk halten selbst keine Modelle: Was sie an KI brauchen, holen sie über die Leitstelle. Die
KI-Dienste stehen im Maschinenraum, die Sprachmodelle im Modell-Läufer.

```
Webapps (Stellwerk)  ->  Leitstelle  ->  Modell-Läufer      (Sprachmodelle)
                                     ->  Maschinenraum      (übrige KI-Dienste, etwa das Klangwerk)
```

Starten, Anhalten, Abhängigkeiten, Neustarts, Sollzustand und Prozessmessung teilen sich Stellwerk und Maschinenraum
über den [Dienstkern](https://github.com/HalloWelt42/dienstkern). Das Stellwerk hat keine Verbindung zur Leitstelle;
es schaltet nur Webapps. Was eine Webapp außerhalb ihrer Teile braucht (Leitstelle, Kellerwolke, Fundus auf dem Pi,
Dienste des Maschinenraums), nennt ihre Datei unter `nutzt`: das Stellwerk zeigt, ob es gerade erreichbar ist, startet
es aber nie. Der Maschinenraum liest aus `GET /api/stand` je Teil die Prozesse (`pids`) und ordnet sie so den Webapps zu.

## Installieren

Python 3.11 oder neuer; für die Oberfläche Node.

```bash
git clone https://github.com/HalloWelt42/stellwerk.git && cd stellwerk && ./installieren.sh
```

Das Skript legt den Ordner `~/Stellwerk` an, installiert das Programm in ein eigenes venv und richtet es als Dienst
ein. Derselbe Befehl aktualisiert; App-Dateien, Einstellungen und Sollzustand bleiben. Gibt es einen Maschinenraum
(`~/Maschinenraum`), schreibt das Skript dort `betrieb/stellwerk.toml`: so lässt sich das Stellwerk aus dem Maschinenraum
und seinem Menüleistensymbol starten, anhalten und öffnen.

## Der Ordner

| Pfad | Inhalt |
|---|---|
| `einstellungen.toml` | Port der Oberfläche, Messtakt, Neustartregeln, Docker, Prüfung äußerer Abhängigkeiten |
| `apps/<kennung>.toml` | je Webapp eine Datei mit ihren Teilen; der Dateiname ist die Kennung |
| `protokolle/stellwerk.log` | Ausgabe des Stellwerks |
| `protokolle/<webapp>.<teil>.log` | Ausgabe eines Teils; `docker.log` die der Docker-Befehle |
| `zustand.json` | Sollzustand je Teil und gemessene Höchstwerte |

Neue oder geänderte App-Dateien liest das Stellwerk im nächsten Takt. Stand ohne Oberfläche:

```bash
~/Stellwerk/.venv/bin/stellwerk --liste
```

## App-Datei

Beispiel: [beispiele/notizbuch.toml](beispiele/notizbuch.toml). Unbekannte Felder sind ein Fehler; die Datei wird
dann mit einer lesbaren Meldung übergangen. Eine Datei mit `faehigkeiten` gehört in den Maschinenraum.

| Feld | Vorgabe | Bedeutung |
|---|---|---|
| `name` | Pflicht | Anzeigename der Webapp |
| `zweck` | Pflicht für neue Einträge | wofür die Webapp da ist, ein Begriff oder wenige Wörter, höchstens 40 Zeichen (etwa "Wissensspeicher", "Bewerbungen", "Textprüfung"); steht in Liste, Karte und Detailansicht neben dem Namen. Fehlt er in einer älteren Datei, läuft die Webapp trotzdem und die Oberfläche zeigt "Zweck fehlt: in der App-Datei eintragen" |
| `beschreibung` | leer | längere Erklärung in ganzen Sätzen, nur in der Detailansicht |
| `oberflaeche` | keine | Adresse der Webapp im Browser; Karte und Menüleiste des Maschinenraums bekommen einen Knopf zum Öffnen |
| `[[teile]]` | mindestens einer | die Teile der Webapp, siehe unten |
| `[[nutzt]]` | keine | äußere Abhängigkeiten, siehe unten |

Je Teil:

| Feld | Vorgabe | Bedeutung |
|---|---|---|
| `kennung` | Pflicht | Kleinbuchstaben, Ziffern, `-` und `_`; eindeutig in der Webapp |
| `name` | Pflicht | Anzeigename, etwa Backend oder Oberfläche |
| `zweck` | keiner | wofür der Teil da ist, wie beim Zweck der Webapp kurz (etwa "Bedeutungssuche"); steht in der Detailansicht |
| `art` | nativ | `nativ`: eigener Prozess. `docker`: Container aus der Compose-Datei des Projekts |
| `ordner` | Pflicht | Arbeitsordner; `~` und `$VAR` werden aufgelöst |
| `befehl` | Pflicht bei nativ | Programm und Argumente; ein relativer Programmpfad gilt ab `ordner`; `$NAME` aus der Umgebung des Teils |
| `vorher` | leer | nativ: Befehl, der vor jedem Start einmal läuft |
| `compose` | leer | docker: Optionen vor dem Unterbefehl, genau wie das Projekt sie nutzt (`--env-file`, `-f`) |
| `container` | Pflicht bei docker | Name des Dienstes in der Compose-Datei |
| `port` | keiner | erreichbar heißt: der Port nimmt Verbindungen an; bei docker Pflicht, wenn keine `pruefadresse` |
| `pruefadresse` | keine | strenger: eine Antwort unter 500 von dieser Adresse |
| `braucht` | leer | Teile derselben Webapp, die vorher laufen müssen |
| `speicher_gb` | 0,5 | Schätzung, bis der Teil gemessen ist |
| `startzeit_s` | 60 | so lange darf der Start bis zur Erreichbarkeit dauern |
| `anhaltezeit_s` | 20 | so lange darf das Beenden dauern, danach hart |
| `umgebung` | leer | zusätzliche Umgebungsvariablen |
| `umgebung_datei` | keine | Datei mit Zeilen `NAME=WERT`, zum Beispiel die `.env` eines Projekts |
| `pfad` | übliche Systempfade | Suchpfad für Programme |
| `neustart` | ja | nach einem Absturz neu starten, solange der Teil laufen soll |
| `aktiv_ab_prozent` | 5 | ab dieser Prozessorlast (Prozent eines Kerns) gilt er als arbeitend |

Docker-Teile starten mit `docker compose <compose> up -d <container>` und halten mit `docker compose <compose> stop
<container>` an, nie per Signal. Wichtig ist derselbe Aufruf wie im Projekt (Umgebungsdatei, Compose-Datei): sonst
entstünde ein zweites Compose-Projekt mit leerem Datenbestand.

### Äußere Abhängigkeiten (`nutzt`)

Was die Webapp außerhalb ihrer Teile braucht: die Leitstelle für KI-Aufträge, die Kellerwolke für die Anmeldung, Fundus
auf dem Pi, Dienste des Maschinenraums. Das Stellwerk startet nichts davon; es prüft im Hintergrund, ob es erreichbar ist,
und zeigt das in Karte und Detailansicht. Geprüft wird gepuffert, nie beim Seitenaufruf: jedes Ziel höchstens alle
`nutzt.abstand_s` Sekunden mit der Frist `nutzt.frist_s` (Einstellungen); nutzen mehrere Webapps dasselbe Ziel, wird
es nur einmal geprüft.

| Feld | Vorgabe | Bedeutung |
|---|---|---|
| `name` | Pflicht | Anzeigename, eindeutig in der Webapp |
| `zweck` | Pflicht | wofür die Webapp ihn braucht, kurz wie oben (etwa "KI-Aufträge") |
| `pruefadresse` | | `http://` oder `https://`; erreichbar heißt: Antwort unter 500. Zertifikate werden dabei nicht geprüft, gesendet wird nur eine leere Anfrage |
| `port` | | statt `pruefadresse`: erreichbar heißt, der Port nimmt Verbindungen an |
| `rechner` | dieser Rechner | mit `port`: Name oder Adresse des Rechners |

Genau eins von `pruefadresse` und `port`:

```toml
[[nutzt]]
name = "Leitstelle"
zweck = "KI-Aufträge"
pruefadresse = "http://pi.local:8530/"

[[nutzt]]
name = "Kellerwolke"
zweck = "Anmeldung und Dateien"
rechner = "pi.local"
port = 39277
```

## Abgrenzung je Teil

Jeder native Teil läuft in eigener Sitzung und Prozessgruppe, im eigenen Arbeitsordner, mit eigener Umgebung (nur
Suchpfad, Heimordner, Sprache und was die Datei nennt) und schreibt in eine eigene Protokolldatei. Anhalten trifft
genau seine Prozessgruppe: erst freundlich, nach `anhaltezeit_s` hart. Läuft ein Teil schon, ohne vom Stellwerk
gestartet zu sein (sein Port antwortet), übernimmt das Stellwerk ihn: es misst ihn und kann ihn anhalten, startet ihn
aber nicht doppelt.

## Einstellungen

`einstellungen.toml`, Abschnitte und Vorgaben:

| Abschnitt | Feld | Vorgabe | Bedeutung |
|---|---|---|---|
| | `name` | Rechnername | Anzeigename |
| `oberflaeche` | `adresse`, `port` | 127.0.0.1, 8550 | wo die Oberfläche lauscht; nur 127.0.0.1 ist vor dem Netz geschützt |
| `messung` | `takt_s` | 5 | Abstand der Prüfung und Messung der Teile |
| `neustart` | `pausen_s` | 5, 30, 120 | Pausen vor dem ersten, zweiten, dritten Neustart nach Absturz |
| `neustart` | `fenster_s`, `im_fenster` | 600, 3 | mehr Abstürze im Zeitraum: der Teil bleibt aus |
| `docker` | `befehl`, `pruefbefehl`, `anhaltebefehl` | `docker desktop start`, `docker info`, `docker desktop stop` | wie Docker gestartet, geprüft und angehalten wird |
| `docker` | `prozessmuster`, `speicher_gb` | virtuelle Maschine, 8 | wessen Speicher als Docker zählt |
| `docker` | `startzeit_s`, `anhaltezeit_s` | 240, 180 | Grenzen für Start und Anhalten |
| `nutzt` | `abstand_s` | 30 | so oft wird jede äußere Abhängigkeit geprüft |
| `nutzt` | `frist_s` | 2 | so lange darf ihre Antwort dauern |

## Schnittstelle

| Aufruf | Wirkung |
|---|---|
| `GET /api/stand` | alle Webapps mit Zweck, Teilen (in Startreihenfolge unter `folge`) und äußeren Abhängigkeiten samt letzter Prüfung, Docker, fehlerhafte Dateien |
| `GET /api/version` | Fassung des laufenden Programms; weicht sie von der eingebauten ab, lädt die Oberfläche von selbst neu |
| `POST /api/apps/<kennung>/starten`, `/anhalten`, `/neustarten` | ganze Webapp schalten; Antwort mit Erfolg und Meldung |
| `POST /api/apps/<kennung>/teile/<teil>/starten`, `/anhalten`, `/neustarten` | einen Teil schalten: Starten bringt erst, was er braucht (auch Docker), Anhalten trifft nur ihn |
| `GET /api/apps/<kennung>/teile/<teil>/protokoll?zeilen=200` | Ende der Protokolldatei eines Teils |
| `POST /api/docker/starten`, `/anhalten` | Docker schalten; anhalten nur, wenn kein Docker-Teil läuft |
| `GET /api/docker/protokoll`, `GET /api/protokoll` | Ausgabe der Docker-Befehle, Ausgabe des Stellwerks |

Je Teil liefert `GET /api/stand` neben Zustand, Port, Messwerten und Meldung:

| Feld | Bedeutung |
|---|---|
| `pids` | die Prozesse, die das Stellwerk für den Teil führt: bei einem selbst gestarteten Teil die lebenden Prozesse seiner Prozessgruppe, bei einem übernommenen der lauschende Prozess mit seinen Nachfahren; bei Docker-Teilen und solange er nicht läuft leer. Stand des letzten Messtakts |
| `laeuft_seit` | Start seines ältesten Prozesses (Sekunden seit 1970), daraus die Laufzeit |
| `braucht`, `zweck` | wie in der App-Datei |

Schreibende Aufrufe brauchen den Kopf `X-Stellwerk: 1`, und es gelten nur die Rechnernamen dieses Rechners. So kann
keine fremde Webseite im selben Browser Webapps schalten.

## Entwickeln

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[test]" && .venv/bin/python -m pytest
```

```bash
cd frontend && npm install && npm run pruefen && npm run build
```

Oberfläche mit Neuladen: `cd frontend && npm run dev` (Port 5550, Schnittstelle vom laufenden Stellwerk). Nach
Änderungen an den Pydantic-Modellen `npm run typen`. Name und Kurzzweck des Stellwerks stehen nur in
`frontend/src/lib/marke.ts`; Seitentitel und Manifest entstehen beim Bauen daraus (Farben und Symbole des Manifests in
`frontend/manifest.json`). Die Tests laufen gegen echte kleine Prozesse; Docker spielt
dabei ein Schein-Programm, das Container als HTTP-Server startet.

---

## Lizenz

**Nicht-kommerzielle Nutzung** - Siehe [LICENSE](LICENSE)

Erlaubt: Private Nutzung, Installation, persönliche Anpassungen, Teilen mit Quellenangabe

Verboten: Kommerzielle Nutzung, Verkauf, Einbindung in kommerzielle Produkte

---

## Unterstützen

Stellwerk ist ein privates Hobby-Projekt. Kein Tracking, keine Werbung, keine Kompromisse.

Wenn dir das Projekt gefällt, kannst du ihm einen Stern geben - oder direkt hier:

[![Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/HalloWelt42)

**Crypto:**

| Coin | Adresse |
|------|---------|
| BTC | `bc1qnd599khdkv3v3npmj9ufxzf6h4fzanny2acwqr` |
| DOGE | `DL7tuiYCqm3xQjMDXChdxeQxqUGMACn1ZV` |
| ETH | `0x8A28fc47bFFFA03C8f685fa0836E2dBe1CA14F27` |

Copyright (c) 2026 HalloWelt42
