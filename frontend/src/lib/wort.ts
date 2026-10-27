// Wörter, Symbole und Farben zu den Schlüsseln der Schnittstelle. Schlüssel werden nie gedruckt.
import type { AppZustand, Art, Zustand } from './typen.gen';

export const ZUSTAND: Record<Zustand, { wort: string; klasse: string; symbol: string }> = {
  aus: { wort: 'Aus', klasse: 'aus', symbol: 'fa-power-off' },
  startet: { wort: 'Startet', klasse: 'wartet', symbol: 'fa-circle-notch fa-spin' },
  laeuft: { wort: 'Läuft', klasse: 'fertig', symbol: 'fa-circle' },
  stoppt: { wort: 'Hält an', klasse: 'auslaufend', symbol: 'fa-circle-notch fa-spin' },
  gestoert: { wort: 'Gestört', klasse: 'fehler', symbol: 'fa-triangle-exclamation' },
};

export const APPZUSTAND: Record<AppZustand, { wort: string; klasse: string; symbol: string }> = {
  ...ZUSTAND,
  teilweise: { wort: 'Teilweise', klasse: 'auslaufend', symbol: 'fa-circle-half-stroke' },
};

export const ART: Record<Art, { wort: string; symbol: string; satz: string }> = {
  nativ: { wort: 'nativ', symbol: 'fa-microchip', satz: 'Eigener Prozess auf diesem Rechner' },
  docker: { wort: 'Docker', symbol: 'fa-box', satz: 'Container aus der Compose-Datei des Projekts' },
};

/** an: läuft oder ist dabei, ob ganz oder teilweise; dann zeigt der Schalter an und hält an */
export const istAn = (z: AppZustand | Zustand): boolean => z !== 'aus' && z !== 'gestoert';

/** Erreichbarkeit einer äußeren Abhängigkeit (null: noch nicht geprüft) */
export function erreichbarkeit(e: boolean | null): { wort: string; klasse: string; symbol: string } {
  if (e === null) return { wort: 'Wird geprüft', klasse: 'wartet', symbol: 'fa-circle-notch fa-spin' };
  return e ? { wort: 'Erreichbar', klasse: 'fertig', symbol: 'fa-circle-check' } : { wort: 'Nicht erreichbar', klasse: 'fehler', symbol: 'fa-circle-xmark' };
}

/** Punktfarbe für einen Teil in kurzen Aufzählungen */
export const PUNKT: Record<Zustand, string> = { aus: 'aus', startet: 'warnung', laeuft: 'lebt', stoppt: 'warnung', gestoert: 'gefahr' };
