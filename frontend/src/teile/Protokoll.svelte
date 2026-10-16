<script lang="ts">
  // Ende einer Protokolldatei, alle zwei Sekunden neu, solange sichtbar: das Stellwerk, Docker oder ein Teil einer Webapp.
  import { onDestroy } from 'svelte';
  import { api, type Protokollziel } from '../lib/api';

  let { ziel = { art: 'stellwerk' }, zeilen: anzahl = 300 }: { ziel?: Protokollziel; zeilen?: number } = $props();

  let zeilen = $state<string[]>([]);
  let datei = $state('');
  let feld = $state<HTMLPreElement | null>(null);
  let laeuft = true;

  async function holen() {
    if (!laeuft) return;
    try {
      const unten = !feld || feld.scrollHeight - feld.scrollTop - feld.clientHeight < 40;
      const p = await api.protokoll(ziel, anzahl);
      zeilen = p.zeilen;
      datei = p.datei;
      if (unten) requestAnimationFrame(() => feld && (feld.scrollTop = feld.scrollHeight));
    } catch {
      /* nächster Versuch im nächsten Takt */
    }
    if (laeuft) setTimeout(holen, 2000);
  }

  void holen();
  onDestroy(() => (laeuft = false));
</script>

<div class="protokoll">
  <pre bind:this={feld}>{zeilen.length ? zeilen.join('\n') : 'Noch keine Ausgabe.'}</pre>
  <div class="datei" title="Vollständige Datei">{datei}</div>
</div>

<style>
  .protokoll { margin-top: var(--sw-a3); }
  pre { margin: 0; max-height: var(--hoehe, 360px); overflow: auto; background: var(--sw-mulde); border-radius: var(--sw-ecke); padding: var(--sw-a3);
        font-family: var(--sw-schrift-code); font-size: 14px; line-height: 1.45; white-space: pre-wrap; overflow-wrap: anywhere; color: var(--sw-text-2); }
  .datei { margin-top: 6px; font-family: var(--sw-schrift-code); font-size: var(--sw-gr-marke); color: var(--sw-text-3); overflow-wrap: anywhere; }
</style>
