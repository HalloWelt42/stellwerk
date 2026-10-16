// Erzeugt aus den Pydantic-Modellen des Stellwerks (npm run typen). Nicht von Hand ändern.

/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Art".
 */
export type Art = 'nativ' | 'docker';
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "AppZustand".
 */
export type AppZustand = 'aus' | 'startet' | 'laeuft' | 'teilweise' | 'stoppt' | 'gestoert';
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Soll".
 */
export type Soll = 'laeuft' | 'aus';
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Zustand".
 */
export type Zustand = 'aus' | 'startet' | 'laeuft' | 'stoppt' | 'gestoert';

export interface Stellwerk {
  Stand?: Stand;
  Ergebnis?: Ergebnis;
  Protokollauszug?: Protokollauszug;
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Stand".
 */
export interface Stand {
  version: string;
  rechner: string;
  zeit: number;
  ordner: string;
  einstellungen: Einstellungen;
  apps: AppAnsicht[];
  docker: DockerAnsicht | null;
  ladefehler: Ladefehler[];
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Einstellungen".
 */
export interface Einstellungen {
  /**
   * Anzeigename des Rechners; sonst der Rechnername
   */
  name: string | null;
  oberflaeche: Oberflaeche;
  messung: Messung;
  neustart: Neustartregeln;
  docker: DockerLaufzeit;
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Oberflaeche".
 */
export interface Oberflaeche {
  /**
   * nur dieser Rechner; 0.0.0.0 öffnet die Oberfläche fürs Netz
   */
  adresse: string;
  port: number;
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Messung".
 */
export interface Messung {
  /**
   * Abstand der Prüfung und Messung der Teile
   */
  takt_s: number;
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Neustartregeln".
 */
export interface Neustartregeln {
  /**
   * Pausen vor dem 1., 2., 3. Neustart nach einem Absturz
   *
   * @minItems 1
   */
  pausen_s: [number, ...number[]];
  /**
   * Zeitraum, in dem Abstürze gezählt werden
   */
  fenster_s: number;
  /**
   * mehr Abstürze im Zeitraum: der Dienst bleibt aus
   */
  im_fenster: number;
}
/**
 * Die Container-Laufzeit. Keine Webapp, sondern was Docker-Teile brauchen: das Stellwerk startet sie, wenn ein
 * Docker-Teil startet, und hält sie nur von Hand an, wenn kein Docker-Teil mehr läuft.
 *
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "DockerLaufzeit".
 */
export interface DockerLaufzeit {
  /**
   * @minItems 1
   */
  befehl: [string, ...string[]];
  /**
   * @minItems 1
   */
  pruefbefehl: [string, ...string[]];
  /**
   * @minItems 1
   */
  anhaltebefehl: [string, ...string[]];
  /**
   * Prozesse, deren Speicher zählt (die virtuelle Maschine)
   */
  prozessmuster: string | null;
  speicher_gb: number;
  startzeit_s: number;
  anhaltezeit_s: number;
  pfad: string;
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "AppAnsicht".
 */
export interface AppAnsicht {
  kennung: string;
  name: string;
  beschreibung: string;
  oberflaeche: string | null;
  arten: Art[];
  zustand: AppZustand;
  soll: Soll | null;
  gb_jetzt: number | null;
  teile: TeilAnsicht[];
  datei: string;
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "TeilAnsicht".
 */
export interface TeilAnsicht {
  kennung: string;
  name: string;
  art: Art;
  port: number | null;
  zustand: Zustand;
  fremd: boolean;
  gb_jetzt: number | null;
  spitze_gb: number | null;
  schaetzung_gb: number;
  cpu_prozent: number | null;
  aktiv: boolean;
  soll: Soll | null;
  meldung: string;
  ordner: string;
  protokolldatei: string;
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "DockerAnsicht".
 */
export interface DockerAnsicht {
  zustand: Zustand;
  gb_jetzt: number | null;
  soll: Soll | null;
  meldung: string;
  apps: string[];
  protokolldatei: string;
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Ladefehler".
 */
export interface Ladefehler {
  datei: string;
  meldung: string;
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Ergebnis".
 */
export interface Ergebnis {
  ziel: string;
  erfolg: boolean;
  meldung: string;
}
/**
 * This interface was referenced by `Stellwerk`'s JSON-Schema
 * via the `definition` "Protokollauszug".
 */
export interface Protokollauszug {
  datei: string;
  zeilen: string[];
}
