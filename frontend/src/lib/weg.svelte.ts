// Weg durch die Seiten: echte Pfade (/apps, /protokoll ...); das Stellwerk liefert für jeden Pfad index.html.

export type Seite = 'uebersicht' | 'apps' | 'protokoll' | 'ordner';

const PFADE: Record<Seite, string> = { uebersicht: '/', apps: '/apps', protokoll: '/protokoll', ordner: '/ordner' };

function lesen(): { seite: Seite; teil: string | null } {
  const [, erster, ...rest] = location.pathname.split('/');
  const seite = (Object.entries(PFADE).find(([, p]) => p === `/${erster ?? ''}`)?.[0] ?? 'uebersicht') as Seite;
  return { seite, teil: rest.length ? rest.map(decodeURIComponent).join('/') : null };
}

class Weg {
  seite = $state<Seite>(lesen().seite);
  /** Rest des Pfades, zum Beispiel app/teil, dessen Protokoll offen ist */
  teil = $state<string | null>(lesen().teil);

  constructor() {
    window.addEventListener('popstate', () => {
      const w = lesen();
      this.seite = w.seite;
      this.teil = w.teil;
    });
  }

  pfad(seite: Seite, teil?: string | null): string {
    return PFADE[seite] + (teil ? `/${teil.split('/').map(encodeURIComponent).join('/')}` : '');
  }

  gehe(seite: Seite, teil: string | null = null, ersetzen = false): void {
    const ziel = this.pfad(seite, teil);
    if (ziel !== location.pathname) (ersetzen ? history.replaceState : history.pushState).call(history, null, '', ziel);
    this.seite = seite;
    this.teil = teil;
  }

  /** Für <a href>: normale Klicks bleiben in der Oberfläche, Mittelklick öffnet einen neuen Reiter */
  klick(e: MouseEvent, seite: Seite, teil: string | null = null): void {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
    e.preventDefault();
    this.gehe(seite, teil);
  }
}

export const weg = new Weg();
