// Weg durch die Seiten: echte Pfade (/apps, /apps/<kennung>, /protokoll ...); das Stellwerk liefert für jeden Pfad
// index.html. Zurück und Vor im Browser gehen mit (popstate).
// Ein Seitenwechsel ist der ruhige Moment für eine neue Fassung (die Adresse steht schon, das Neuladen landet dort).
import { nachOrtswechsel } from './fassung.svelte';

export type Seite = 'uebersicht' | 'apps' | 'protokoll' | 'ordner';

const PFADE: Record<Seite, string> = { uebersicht: '/', apps: '/apps', protokoll: '/protokoll', ordner: '/ordner' };

function lesen(): { seite: Seite; rest: string | null } {
  const [, erster, ...rest] = location.pathname.split('/');
  const seite = (Object.entries(PFADE).find(([, p]) => p === `/${erster ?? ''}`)?.[0] ?? 'uebersicht') as Seite;
  const teile = rest.filter(Boolean);
  return { seite, rest: teile.length ? teile.map(decodeURIComponent).join('/') : null };
}

class Weg {
  seite = $state<Seite>(lesen().seite);
  /** Rest des Pfades: unter Webapps die Kennung der App in der Detailansicht, im Protokoll app/teil */
  rest = $state<string | null>(lesen().rest);

  constructor() {
    window.addEventListener('popstate', () => {
      const w = lesen();
      this.seite = w.seite;
      this.rest = w.rest;
      nachOrtswechsel();
    });
  }

  pfad(seite: Seite, rest?: string | null): string {
    return PFADE[seite] + (rest ? `/${rest.split('/').map(encodeURIComponent).join('/')}` : '');
  }

  gehe(seite: Seite, rest: string | null = null, ersetzen = false): void {
    const ziel = this.pfad(seite, rest);
    const wechsel = ziel !== location.pathname;
    if (wechsel) (ersetzen ? history.replaceState : history.pushState).call(history, null, '', ziel);
    this.seite = seite;
    this.rest = rest;
    if (wechsel) nachOrtswechsel();
  }

  /** Für <a href>: normale Klicks bleiben in der Oberfläche, Mittelklick öffnet einen neuen Reiter */
  klick(e: MouseEvent, seite: Seite, rest: string | null = null): void {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
    e.preventDefault();
    this.gehe(seite, rest);
  }
}

export const weg = new Weg();
