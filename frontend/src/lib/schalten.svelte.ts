// Schalten einer Webapp oder eines einzelnen Teils: ein Ort für Aufruf, Rückmeldung und frischen Stand. Was gerade
// geschaltet wird, steht in `laufend` (Schlüssel app oder app/teil), damit Liste, Karten und Detailansicht dasselbe zeigen.
import { api, type Schaltung } from './api';
import { meldungen } from './meldung.svelte';
import { lage } from './stand.svelte';

const schluessel = (app: string, teil?: string): string => (teil ? `${app}/${teil}` : app);

class Schalten {
  laufend = $state<Record<string, Schaltung>>({});

  /** Was gerade mit der Webapp (oder dem Teil) geschieht; undefined, wenn nichts */
  was(app: string, teil?: string): Schaltung | undefined {
    return this.laufend[schluessel(app, teil)];
  }

  /** Schaltet und meldet das Ergebnis unter `name`; gibt zurück, ob es gelang. */
  async tun(name: string, art: Schaltung, app: string, teil?: string): Promise<boolean> {
    const k = schluessel(app, teil);
    this.laufend = { ...this.laufend, [k]: art };
    try {
      const e = await (teil ? api.teil(app, teil, art) : api.app(app, art));
      meldungen.zeigen(`${name}: ${e.meldung}`, e.erfolg ? 'erfolg' : 'fehler');
      return e.erfolg;
    } catch (f) {
      meldungen.fehler(f);
      return false;
    } finally {
      // erst nach der Antwort aus dem dann gültigen Stand kopieren, sonst gingen parallele Schaltungen verloren
      const rest = { ...this.laufend };
      delete rest[k];
      this.laufend = rest;
      await lage.jetzt();
    }
  }
}

export const schalten = new Schalten();

/** Wort für eine laufende Schaltung, etwa in der Zustandsmarke */
export const SCHALTWORT: Record<Schaltung, string> = { starten: 'Startet', anhalten: 'Hält an', neustarten: 'Startet neu' };
