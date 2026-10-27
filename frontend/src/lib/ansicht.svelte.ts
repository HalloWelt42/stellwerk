// Ansicht je Gerät: Thema, Schriftstufe und wie die Webapps gezeigt werden, gemerkt im Browser. Farbwelt, Blauart und
// Flächen (Ziegel) stehen fest in index.html.

export type Thema = 'dunkel' | 'hell';
export type Schrift = 'klein' | 'mittel' | 'gross';
/** Webapps als ausführliche Liste (je App alle Teile) oder als Karten zum Überblick */
export type AppAnsichtArt = 'liste' | 'karten';

function lesen<T extends string>(schluessel: string, erlaubt: readonly T[], vorgabe: T): T {
  try {
    const wert = localStorage.getItem(`stellwerk-${schluessel}`);
    return erlaubt.includes(wert as T) ? (wert as T) : vorgabe;
  } catch {
    return vorgabe;
  }
}

function merken(schluessel: string, wert: string): void {
  try {
    localStorage.setItem(`stellwerk-${schluessel}`, wert);
  } catch {
    /* privater Modus: dann gilt die Wahl nur bis zum Neuladen */
  }
}

class Ansicht {
  thema = $state<Thema>(lesen('thema', ['dunkel', 'hell'] as const, 'dunkel'));
  schrift = $state<Schrift>(lesen('schrift', ['klein', 'mittel', 'gross'] as const, 'gross'));
  apps = $state<AppAnsichtArt>(lesen('apps', ['liste', 'karten'] as const, 'liste'));

  setzeThema(t: Thema): void {
    this.thema = t;
    merken('thema', t);
    ansichtAnwenden();
  }

  setzeSchrift(s: Schrift): void {
    this.schrift = s;
    merken('schrift', s);
    ansichtAnwenden();
  }

  setzeApps(a: AppAnsichtArt): void {
    this.apps = a;
    merken('apps', a);
  }
}

export const ansicht = new Ansicht();

export function ansichtAnwenden(): void {
  document.documentElement.dataset.theme = ansicht.thema;
  document.documentElement.dataset.schrift = ansicht.schrift;
}
