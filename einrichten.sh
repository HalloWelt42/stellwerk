#!/usr/bin/env bash
# Einrichten des Stellwerks. Schritte und Proben der Neueinrichtung stehen in docs/handbuch.md.
#
#   ./einrichten.sh                                       wie ./installieren.sh: Ordner ~/Stellwerk, Programm in eigenem
#                                                         venv, Oberfläche, Dienst (launchd), Eintrag im Maschinenraum
#   ./einrichten.sh --probe --ziel DIR --port-versatz N   Probelauf des Handbuchs: Programm und Oberfläche in DIR, ein
#                                                         eigener Ordner DIR/ordner ohne Webapps, Docker wird weder
#                                                         gestartet noch angehalten, Oberfläche nur an 127.0.0.1 und um
#                                                         N verschoben, gestartet als Prozess (kein launchd, kein Eintrag
#                                                         im Maschinenraum, nichts in ~/Library/LaunchAgents)
#   ./einrichten.sh --probe --ziel DIR --abbauen          beendet den Prozess
set -euo pipefail
HIER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
WARTEN_S=60

probe_aufbauen() {
  local ziel="$1" versatz="$2" ordner="$1/ordner" py port
  cd "$ziel"
  ( cd frontend && npm ci --no-audit --no-fund --silent && npm run build --silent )
  "$PYTHON" -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" version.json > stellwerk/VERSION
  mkdir -p "$ordner/apps"
  "$PYTHON" -m venv "$ziel/.venv"
  "$ziel/.venv/bin/pip" install --quiet --upgrade pip
  "$ziel/.venv/bin/pip" install --quiet "$ziel"
  py="$ziel/.venv/bin/python"
  # Port aus der Vorgabe des Programms (stellwerk/konfig.py), verschoben um den Versatz
  port=$(( $("$py" -c "from stellwerk.konfig import Einstellungen; print(Einstellungen().oberflaeche.port)") + versatz ))
  cat > "$ordner/einstellungen.toml" <<EOF
# Probelauf des Handbuchs: keine Webapps, Docker wird nie gestartet oder angehalten, nur an diesem Rechner
name = "Probelauf"

[oberflaeche]
adresse = "127.0.0.1"
port = $port

[docker]
befehl = ["true"]
anhaltebefehl = ["true"]
EOF
  nohup "$py" -m stellwerk "$ordner" > "$ziel/stellwerk.log" 2>&1 &
  echo $! > "$ziel/stellwerk.pid"
  local ende=$(( $(date +%s) + WARTEN_S ))
  while [ "$(date +%s)" -lt "$ende" ]; do
    if curl -sf "http://127.0.0.1:$port/api/version" >/dev/null && curl -sf -o /dev/null "http://127.0.0.1:$port/"; then
      echo "ANTWORTET http://127.0.0.1:$port/api/version"
      return 0
    fi
    sleep 1
  done
  echo "Das Stellwerk antwortet nach $WARTEN_S s nicht" >&2
  tail -n 40 "$ziel/stellwerk.log" >&2 || true
  return 1
}

probe_abbauen() {
  local pid
  if [ -f "$1/stellwerk.pid" ]; then
    pid="$(cat "$1/stellwerk.pid")"
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$1/stellwerk.pid"
  fi
}

probe=0; abbauen=0; ziel=""; versatz=""
while [ $# -gt 0 ]; do
  case "$1" in
    --probe) probe=1 ;;
    --abbauen) abbauen=1 ;;
    --ziel) ziel="${2:?--ziel braucht einen Ordner}"; shift ;;
    --port-versatz) versatz="${2:?--port-versatz braucht eine Zahl}"; shift ;;
    *) echo "unbekannte Angabe: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ "$probe" = 0 ]; then
  exec "$HIER/installieren.sh"
elif [ -z "$ziel" ] || [ ! -d "$ziel" ]; then
  echo "--probe braucht --ziel mit einem vorhandenen Ordner" >&2; exit 2
elif [ "$abbauen" = 1 ]; then
  probe_abbauen "$(cd "$ziel" && pwd)"
else
  probe_aufbauen "$(cd "$ziel" && pwd)" "${versatz:?--port-versatz fehlt}"
fi
