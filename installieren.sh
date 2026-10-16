#!/bin/sh
# Stellwerk installieren oder aktualisieren, für den angemeldeten Benutzer. Aufruf aus dem Projektordner:
#
#   ./installieren.sh
#
# Legt den Ordner ~/Stellwerk an (oder STELLWERK_ORDNER), installiert das Programm in ein eigenes venv,
# baut die Oberfläche (wenn Node vorhanden ist) und richtet es als Dienst ein, der Neustarts übersteht:
# macOS launchd (startet mit der Anmeldung), Linux systemd im Benutzerkontext. Gibt es einen Maschinenraum, trägt
# sich das Stellwerk dort unter betrieb/ ein: sein Menüleistensymbol ist das zentrale Steuerwerk (Stellwerk starten,
# anhalten, öffnen, Webapps schalten). App-Dateien, Einstellungen und Sollzustand bleiben bei einer Aktualisierung.
set -eu

HIER="$(cd "$(dirname "$0")" && pwd)"
ORDNER="${STELLWERK_ORDNER:-$HOME/Stellwerk}"
PYTHON="${PYTHON:-python3}"
KENNUNG="stellwerk"

meldung() { printf '%s\n' "$*"; }
abbruch() { printf 'Abbruch: %s\n' "$*" >&2; exit 1; }

command -v "$PYTHON" >/dev/null || abbruch "$PYTHON fehlt (Python 3.11 oder neuer)"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || abbruch "Python 3.11 oder neuer nötig ($PYTHON)"

mkdir -p "$ORDNER/apps" "$ORDNER/protokolle"
chmod 700 "$ORDNER"

# ── Oberfläche bauen und Programm installieren ───────────────────────────
if command -v npm >/dev/null; then
  ( cd "$HIER/frontend" && npm ci --no-audit --no-fund --silent && npm run build --silent )
elif [ ! -f "$HIER/stellwerk/oberflaeche/index.html" ]; then
  meldung "Hinweis: ohne Node keine Oberfläche; die Schnittstelle läuft trotzdem."
fi
"$PYTHON" -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "$HIER/version.json" > "$HIER/stellwerk/VERSION"
[ -d "$ORDNER/.venv" ] || "$PYTHON" -m venv "$ORDNER/.venv"
"$ORDNER/.venv/bin/pip" install --quiet --upgrade pip
"$ORDNER/.venv/bin/pip" install --quiet --upgrade --force-reinstall --no-deps "$HIER"
"$ORDNER/.venv/bin/pip" install --quiet "$HIER"
rm -f "$HIER/stellwerk/VERSION"
PY="$ORDNER/.venv/bin/python"
PORT="$("$PY" -c "from stellwerk.konfig import Ordner; from pathlib import Path; print(Ordner(Path('$ORDNER')).einstellungen().oberflaeche.port)")"

# ── Als Dienst einrichten ────────────────────────────────────────────────
launchd_laden() {   # Abmelden läuft im Hintergrund weiter; erst neu laden, wenn der alte Dienst weg ist
  launchctl bootout "gui/$(id -u)/$1" 2>/dev/null || true
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    launchctl print "gui/$(id -u)/$1" >/dev/null 2>&1 || break
    sleep 0.5
  done
  launchctl bootstrap "gui/$(id -u)" "$2"
}

case "$(uname -s)" in
  Darwin)
    mkdir -p "$HOME/Library/LaunchAgents"
    PLIST="$HOME/Library/LaunchAgents/$KENNUNG.plist"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$KENNUNG</string>
  <key>ProgramArguments</key>
  <array><string>$PY</string><string>-m</string><string>stellwerk</string><string>$ORDNER</string></array>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string><key>LANG</key><string>de_DE.UTF-8</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>ProcessType</key><string>Interactive</string>
  <key>StandardOutPath</key><string>$ORDNER/protokolle/start.log</string>
  <key>StandardErrorPath</key><string>$ORDNER/protokolle/start.log</string>
</dict>
</plist>
EOF
    launchd_laden "$KENNUNG" "$PLIST"
    meldung "Stellwerk läuft als launchd-Dienst $KENNUNG (startet mit der Anmeldung)."
    # Früheres eigenes Menüleistensymbol: ersetzt durch das des Maschinenraums
    if [ -f "$HOME/Library/LaunchAgents/$KENNUNG.menueleiste.plist" ]; then
      launchctl bootout "gui/$(id -u)/$KENNUNG.menueleiste" 2>/dev/null || true
      rm -f "$HOME/Library/LaunchAgents/$KENNUNG.menueleiste.plist"
      rm -rf "$HOME/Applications/Stellwerk.app"
      meldung "Eigenes Menüleistensymbol entfernt; das Stellwerk steht jetzt im Symbol des Maschinenraums."
    fi
    STARTEN="[\"launchctl\", \"bootstrap\", \"gui/$(id -u)\", \"$PLIST\"]"
    ANHALTEN="[\"launchctl\", \"bootout\", \"gui/$(id -u)/$KENNUNG\"]"
    ;;
  Linux)
    UNIT="$HOME/.config/systemd/user/$KENNUNG.service"
    mkdir -p "$(dirname "$UNIT")"
    cat > "$UNIT" <<EOF
[Unit]
Description=Stellwerk
After=network-online.target

[Service]
ExecStart=$PY -m stellwerk $ORDNER
Restart=always
RestartSec=10
KillMode=process
StandardOutput=append:$ORDNER/protokolle/start.log
StandardError=append:$ORDNER/protokolle/start.log

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable --now "$KENNUNG.service"
    systemctl --user restart "$KENNUNG.service"
    meldung "Stellwerk läuft als systemd-Dienst im Benutzerkontext."
    STARTEN="[\"systemctl\", \"--user\", \"start\", \"$KENNUNG.service\"]"
    ANHALTEN="[\"systemctl\", \"--user\", \"stop\", \"$KENNUNG.service\"]"
    if [ "$(loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null || echo no)" != "yes" ]; then
      meldung "Damit er ohne Anmeldung startet, einmal mit Verwalterrechten: sudo loginctl enable-linger $(id -un)"
    fi
    ;;
  *) abbruch "unbekanntes Betriebssystem $(uname -s)" ;;
esac

# ── Im Maschinenraum eintragen (zentrales Steuerwerk), wenn es einen gibt ──
MASCHINENRAUM="${MASCHINENRAUM_ORDNER:-$HOME/Maschinenraum}"
if [ -d "$MASCHINENRAUM" ]; then
  mkdir -p "$MASCHINENRAUM/betrieb"
  cat > "$MASCHINENRAUM/betrieb/$KENNUNG.toml" <<EINTRAG_ENDE
# Vom Installationsskript des Stellwerks geschrieben; wird bei jeder Installation erneuert.
name = "Stellwerk"
beschreibung = "Startet Anwendungen: die eigenen Webapps dieses Rechners, nativ oder mit Docker"
ordner = "~"
steuerung = "befehle"
befehl = $STARTEN
anhaltebefehl = $ANHALTEN
port = $PORT
oberflaeche = "http://127.0.0.1:$PORT"
prozessmuster = "-m stellwerk( |$)"
speicher_gb = 0.2
startzeit_s = 60
anhaltezeit_s = 60
neustart = false
EINTRAG_ENDE
  meldung "Im Maschinenraum unter Betrieb eingetragen ($MASCHINENRAUM/betrieb/$KENNUNG.toml)."
fi

meldung "Oberfläche: http://127.0.0.1:$PORT/"
meldung "Ordner: $ORDNER (Webapps unter apps/, Ausgaben unter protokolle/)"
