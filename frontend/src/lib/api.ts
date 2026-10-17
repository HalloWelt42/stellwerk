// Zugriff auf die lokale Schnittstelle /api/*. Schreibende Aufrufe tragen den Kopf X-Stellwerk,
// den fremde Webseiten nicht setzen dürfen, und zählen als laufende Arbeit, solange ihre Antwort aussteht.
import { arbeit } from './arbeit.svelte';
import type { Ergebnis, Fassung, Protokollauszug, Stand } from './typen.gen';

export class ApiFehler extends Error {
  constructor(public grund: string, public begruendung: string, public status: number) {
    super(begruendung);
  }
}

function rufen<T>(pfad: string, methode = 'GET'): Promise<T> {
  return methode === 'GET' ? senden<T>(pfad, methode) : arbeit.rahmen(() => senden<T>(pfad, methode));
}

async function senden<T>(pfad: string, methode: string): Promise<T> {
  const kopf: Record<string, string> = methode === 'GET' ? {} : { 'X-Stellwerk': '1' };
  const antwort = await fetch(`/api${pfad}`, { method: methode, headers: kopf });
  const text = await antwort.text();
  const inhalt = text ? JSON.parse(text) : null;
  if (!antwort.ok) {
    const satz = inhalt?.meldung ?? (typeof inhalt?.detail === 'string' ? inhalt.detail : `Das Stellwerk antwortet mit ${antwort.status}.`);
    throw new ApiFehler(inhalt?.grund ?? 'fehler', satz, antwort.status);
  }
  return inhalt as T;
}

export type Schaltung = 'starten' | 'anhalten' | 'neustarten';

/** Wessen Protokoll: das Stellwerk selbst, die Docker-Laufzeit oder ein Teil einer Webapp */
export type Protokollziel = { art: 'stellwerk' } | { art: 'docker' } | { art: 'teil'; app: string; teil: string };

export const api = {
  version: () => rufen<Fassung>('/version'),
  stand: () => rufen<Stand>('/stand'),
  app: (k: string, s: Schaltung) => rufen<Ergebnis>(`/apps/${encodeURIComponent(k)}/${s}`, 'POST'),
  docker: (s: 'starten' | 'anhalten') => rufen<Ergebnis>(`/docker/${s}`, 'POST'),
  protokoll: (z: Protokollziel, zeilen = 300) =>
    rufen<Protokollauszug>(z.art === 'stellwerk' ? `/protokoll?zeilen=${zeilen}` : z.art === 'docker' ? `/docker/protokoll?zeilen=${zeilen}`
      : `/apps/${encodeURIComponent(z.app)}/teile/${encodeURIComponent(z.teil)}/protokoll?zeilen=${zeilen}`),
};
