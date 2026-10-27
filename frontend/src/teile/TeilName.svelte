<script lang="ts">
  // Name eines Teils mit dem Programm dahinter, etwa "Vektorspeicher · qdrant": nativ der Hauptprozess, solange er
  // läuft, bei Docker das Abbild. Gleich in Karte, Liste und Detailansicht.
  import type { TeilAnsicht } from '../lib/typen.gen';

  let { teil: t, fett = false }: { teil: TeilAnsicht; fett?: boolean } = $props();
  const satz = $derived(t.art === 'docker' ? 'Abbild des Containers' : 'Programm des Hauptprozesses');
</script>

<span class="teilname">{#if fett}<b>{t.name}</b>{:else}{t.name}{/if}{#if t.programm}<span class="programm" title={satz}>{t.programm}</span>{/if}</span>

<style>
  .teilname { min-width: 0; overflow-wrap: anywhere; }
  .programm { color: var(--sw-text-2); font-family: var(--sw-schrift-code); font-size: 0.88em; font-weight: 500; }
  /* Trenner wie im Titel des Stellwerks */
  .programm::before { content: "\b7"; margin: 0 0.4em; font-family: var(--sw-schrift); }
</style>
