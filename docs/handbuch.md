---
zweck: "Startet und stoppt die eigenen Webapps eines Rechners, nativ oder mit Docker, je Webapp mit ihren Teilen in der richtigen Reihenfolge, und zeigt ihren Zustand."
geraet: [mac]
abhaengigkeiten: [maschinenraum]
daten:
  - "Mac: `~/Stellwerk` mit `apps/` (eine Datei je Webapp mit ihren Teilen), `einstellungen.toml`, `zustand.json` (Sollzustand), `protokolle/` (je Teil ein Protokoll)"
  - "Mac: `~/Maschinenraum/betrieb/stellwerk.toml`, der Eintrag des Stellwerks im Maschinenraum (von der Installation geschrieben)"
sicherung:
  - "kein eigenes Werkzeug (Stand 24.10.2026); `~/Stellwerk/apps` gehört zur Sicherung des Macs (siehe Grundlage Mac). Die Einträge der Webapps liegen als `stellwerk.toml` in ihren Repos und lassen sich von dort neu kopieren"
schluessel_orte: []
einrichten: einrichten.sh
stand: ab6ea50
---

# Stellwerk

## Zweck

Das Stellwerk ist nur dafür da, die eigenen Webapps eines Rechners zu starten und zu stoppen, mit Docker oder ohne,
je nach Art. Jede Webapp hat eine Datei in `~/Stellwerk/apps/` mit ihren Teilen (etwa Datenbank, Backend,
Oberfläche); das Stellwerk startet sie in der Reihenfolge ihrer Abhängigkeiten, prüft, ob sie antworten, startet sie
nach einem Absturz begrenzt neu und schreibt je Teil ein Protokoll. Docker Desktop startet es bei Bedarf; angehalten
wird Docker nur von Hand und nur, wenn kein Docker-Teil mehr läuft.

Am Mac laufen darüber unter anderem der Vektorspeicher von [[Fundus]] und die Datenbank und der Browser von
[[Zusage]]. KI-Dienste gehören nicht hierher, sie laufen im [[Maschinenraum]]; Webapps nutzen KI nur über die
[[Leitstelle]].

Es läuft als launchd-Dienst `stellwerk` mit Oberfläche im Browser (nur dieser Rechner, Port {{port:stellwerk}}) und
steht im Symbol des Maschinenraums in der Menüleiste unter Betrieb.

## Was sie braucht

- Mac nach [[Grundlage Mac]]: Python ab 3.11, Node.js für die Oberfläche, Docker Desktop für die Docker-Teile.
- [[Maschinenraum]]: die Installation trägt das Stellwerk dort unter `betrieb/` ein; so steht es in dessen
  Menüleistensymbol und kann von dort gestartet und angehalten werden.

## Neu einrichten

Zwei Wege. Aus der Sicherung: `~/Stellwerk` vor der Installation zurückspielen (Webapps, Einstellungen,
Sollzustand); die Installation lässt den Ordner stehen. Frisch: die Installation legt ihn leer an, dann kommen die
Webapps einzeln hinzu, jede mit dem `stellwerk.toml` aus ihrem Repo.

### 1. Klon und Installation

```
git clone {{repo}} {{ordner}}
cd {{ordner}} && ./einrichten.sh
```

`./einrichten.sh` ruft `./installieren.sh`: Ordner `~/Stellwerk` (Modus 700), Programm in eigenem venv
(`~/Stellwerk/.venv`), Oberfläche bauen, launchd-Dienst `stellwerk` (startet mit der Anmeldung) und der Eintrag
`~/Maschinenraum/betrieb/stellwerk.toml`.

Probe: `curl -s http://127.0.0.1:{{port:stellwerk}}/api/version` meldet `{"version":"{{fassung}}"}`, und im Symbol des
Maschinenraums steht das Stellwerk unter Betrieb.

### 2. Webapps eintragen

Aus der Sicherung liegen sie schon in `~/Stellwerk/apps/`. Frisch je Webapp ihr Eintrag aus dem Repo:
`cp <repo>/stellwerk.toml ~/Stellwerk/apps/<kennung>.toml` (die Seite jeder App sagt, ob sie einen hat; manche
Einträge, etwa der Betrieb von Zusage, liegen nur hier). Das Stellwerk liest neue und geänderte Dateien von selbst; eine
fehlerhafte Datei hält ihre Webapp nicht an, der Fehler steht unter Ladefehler.

Probe: die Oberfläche zeigt unter Webapps jede eingetragene App mit ihren Teilen; ein Start über die Oberfläche bringt
alle Teile auf "läuft".

## Sicherung und Rückspielen

Ein eigenes Sicherungswerkzeug gibt es nicht (Stand 24.10.2026), das Werkzeug Sicherungen holt nichts vom Stellwerk.
Wichtig ist `~/Stellwerk/apps`; es gehört zur Sicherung des Macs (siehe [[Grundlage Mac]]). Die meisten Einträge lassen
sich aus den Repos der Apps neu kopieren. Zurückspielen: Ordner an seinen Ort legen (Modus 700), dann Schritt 1.

## Wenn etwas klemmt

- Ein Teil startet nicht: unter Webapps das Protokoll des Teils ansehen (`~/Stellwerk/protokolle/<app>.<teil>.log`).
- Docker-Teile hängen: Docker Desktop startet noch (bis zu vier Minuten) oder läuft nicht; das Stellwerk wartet darauf.
- Nach einer Installation reagiert nichts: `launchctl print gui/$(id -u)/stellwerk` und `~/Stellwerk/protokolle/start.log`.
- Eine Webapp läuft doppelt: sie wurde von Hand neben dem Stellwerk gestartet; das Stellwerk übernimmt Teile, die schon
  auf ihrem Port lauschen, und hält beim Anhalten nur den lauschenden Prozess an.
