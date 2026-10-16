// Menüleistensymbol des Stellwerks: Schnellzugriff auf die eigenen Webapps dieses Rechners.
// Holt den Stand von der lokalen Schnittstelle (Port aus Info.plist), schaltet Webapps und öffnet sie.
// Es verwaltet selbst nichts; die Wahrheit liegt im Stellwerk.

import AppKit
import SwiftUI

struct Teil: Decodable { let zustand: String }

struct Webapp: Decodable, Identifiable {
    let kennung: String
    let name: String
    let zustand: String
    let oberflaeche: String?
    let gb_jetzt: Double?
    let teile: [Teil]
    var id: String { kennung }
    var an: Bool { zustand != "aus" && zustand != "gestoert" }
}

struct Docker: Decodable { let zustand: String; let gb_jetzt: Double? }

struct Stand: Decodable {
    let rechner: String
    let apps: [Webapp]
    let docker: Docker?
}

@MainActor
final class Modell: ObservableObject {
    @Published var stand: Stand?
    @Published var erreichbar = true
    @Published var arbeitet: Set<String> = []
    let basis: URL
    private var zeitgeber: Timer?

    init() {
        let port = Bundle.main.object(forInfoDictionaryKey: "StellwerkPort") as? Int ?? 8550
        basis = URL(string: "http://127.0.0.1:\(port)")!
        zeitgeber = Timer.scheduledTimer(withTimeInterval: 3, repeats: true) { [weak self] _ in
            Task { @MainActor in await self?.holen() }
        }
        Task { await holen() }
    }

    func holen() async {
        do {
            let (daten, _) = try await URLSession.shared.data(from: basis.appendingPathComponent("api/stand"))
            stand = try JSONDecoder().decode(Stand.self, from: daten)
            erreichbar = true
        } catch {
            erreichbar = false
        }
    }

    func schalten(_ a: Webapp) async {
        arbeitet.insert(a.kennung)
        var anfrage = URLRequest(url: basis.appendingPathComponent("api/apps/\(a.kennung)/\(a.an ? "anhalten" : "starten")"))
        anfrage.httpMethod = "POST"
        anfrage.setValue("1", forHTTPHeaderField: "X-Stellwerk")
        _ = try? await URLSession.shared.data(for: anfrage)
        arbeitet.remove(a.kennung)
        await holen()
    }

    func oeffnen(_ adresse: String? = nil) {
        if let a = adresse, let url = URL(string: a) { NSWorkspace.shared.open(url) } else { NSWorkspace.shared.open(basis) }
    }
}

func gb(_ wert: Double) -> String {
    wert < 1 ? "\(Int((wert * 1024).rounded())) MB" : String(format: "%.1f GB", wert).replacingOccurrences(of: ".", with: ",")
}

func farbe(_ zustand: String) -> Color {
    switch zustand {
    case "gestoert": return .red
    case "laeuft": return .green
    case "aus": return .gray.opacity(0.5)
    default: return .orange
    }
}

struct Ansicht: View {
    @ObservedObject var modell: Modell

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Stellwerk").font(.headline)
                Spacer()
                if let s = modell.stand { Text(s.rechner).foregroundStyle(.secondary) }
            }
            if !modell.erreichbar {
                Label("Das Stellwerk antwortet nicht.", systemImage: "exclamationmark.triangle").foregroundStyle(.orange)
            }
            Divider()
            if let apps = modell.stand?.apps, !apps.isEmpty {
                ForEach(apps) { a in
                    HStack(spacing: 8) {
                        Circle().fill(farbe(a.zustand)).frame(width: 9, height: 9)
                        Text(a.name).lineLimit(1)
                        Spacer()
                        if let jetzt = a.gb_jetzt { Text(gb(jetzt)).monospacedDigit().foregroundStyle(.secondary) }
                        if let adresse = a.oberflaeche, a.zustand == "laeuft" {
                            Button { modell.oeffnen(adresse) } label: { Image(systemName: "arrow.up.right.square") }
                                .buttonStyle(.borderless).help("Im Browser öffnen")
                        }
                        if modell.arbeitet.contains(a.kennung) {
                            ProgressView().controlSize(.small)
                        } else {
                            Toggle("", isOn: Binding(get: { a.an }, set: { _ in Task { await modell.schalten(a) } }))
                                .toggleStyle(.switch).labelsHidden().controlSize(.small)
                        }
                    }
                }
            } else {
                Text("Keine Webapps eingetragen.").foregroundStyle(.secondary)
            }
            if let d = modell.stand?.docker {
                Divider()
                HStack(spacing: 8) {
                    Circle().fill(farbe(d.zustand)).frame(width: 9, height: 9)
                    Text("Docker").foregroundStyle(.secondary)
                    Spacer()
                    if let jetzt = d.gb_jetzt { Text(gb(jetzt)).monospacedDigit().foregroundStyle(.secondary) }
                }.help("Startet von selbst mit einer Docker-Webapp; anhalten in der Oberfläche")
            }
            Divider()
            HStack {
                Button("Oberfläche öffnen") { modell.oeffnen() }
                Spacer()
                Button("Symbol beenden") { NSApplication.shared.terminate(nil) }
                    .help("Beendet nur dieses Symbol; das Stellwerk und seine Webapps laufen weiter")
            }
        }
        .padding(14)
        .frame(width: 340)
    }
}

@main
struct StellwerkMenue: App {
    @StateObject private var modell = Modell()

    var body: some Scene {
        MenuBarExtra {
            Ansicht(modell: modell)
        } label: {
            let laufen = modell.stand?.apps.filter { $0.an }.count ?? 0
            Image(systemName: modell.erreichbar ? "switch.2" : "exclamationmark.triangle")
            if laufen > 0 { Text("\(laufen)") }
        }
        .menuBarExtraStyle(.window)
    }
}
