// Was gerade läuft und durch ein Neuladen der Seite verloren ginge: schreibende Aufrufe, deren Antwort noch aussteht
// (Starten und Anhalten einer Webapp warten, bis alle Teile antworten). Die Fassungsprüfung fragt das ab, bevor sie
// die Seite von selbst neu lädt (lib/fassung.svelte.ts).

class Arbeit {
  /** schreibende Aufrufe, deren Antwort noch aussteht (lib/api.ts) */
  schreibend = $state(0);

  /** Rahmt einen schreibenden Aufruf: zählt mit, solange er läuft. */
  async rahmen<T>(aufruf: () => Promise<T>): Promise<T> {
    this.schreibend += 1;
    try {
      return await aufruf();
    } finally {
      this.schreibend -= 1;
    }
  }

  /** Nichts in Arbeit, das ein Neuladen abbräche. */
  ruhig(): boolean {
    return this.schreibend === 0;
  }
}

export const arbeit = new Arbeit();
