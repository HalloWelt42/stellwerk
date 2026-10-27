// Name und Kurzzweck des Stellwerks, an genau dieser Stelle. Daraus kommen der Kopf, der Titel des Reiters und beim
// Bauen der Titel der Startseite und das Manifest (vite.config.ts). Der Kurzzweck unterscheidet es von den Nachbarn im
// Verbund: Maschinenraum (KI-Dienste), Leitstelle (KI-Vermittlung), Fundus (Wissensspeicher).
export const MARKE = { name: 'Stellwerk', zweck: 'App-Steuerung' } as const;

/** Titel des Reiters und Name im Manifest: Name mit Kurzzweck */
export const TITEL = `${MARKE.name} · ${MARKE.zweck}`;
