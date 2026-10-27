<script lang="ts">
  // Fußleiste wie in der Leitstelle: Kurzstand links, Docker, Verbindung und Fassung rechts
  import { lage } from '../lib/stand.svelte';
  import { ZUSTAND, istAn } from '../lib/wort';

  const s = $derived(lage.stand);
  const laufen = $derived(s?.apps.filter((a) => istAn(a.zustand)).length ?? 0);
</script>

<footer class="fuss">
  {#if s}
    <span><i class="fa-solid fa-window-maximize"></i>&nbsp; <span class="zahl">{laufen}</span> von <span class="zahl">{s.apps.length}</span><span class="lang">&nbsp;Webapps</span> laufen</span>
  {/if}
  <div class="rechts">
    {#if s?.docker}<span title="Container-Laufzeit: {ZUSTAND[s.docker.zustand].wort}"><span class="punkt" class:lebt={s.docker.zustand === 'laeuft'} class:aus={s.docker.zustand === 'aus'} class:gefahr={s.docker.zustand === 'gestoert'}></span>Docker</span>{/if}
    <span title="Verbindung dieser Oberfläche zum Stellwerk"><span class="punkt" class:lebt={lage.erreichbar} class:gefahr={!lage.erreichbar}></span>{lage.erreichbar ? 'Live' : 'Getrennt'}</span>
    {#if s}<span class="schwach zahl fassung">{s.version}</span>{/if}
  </div>
</footer>

<style>
  .fuss span { white-space: nowrap; }
  /* Telefon: kurz, damit die Leiste einzeilig bleibt; die Fassung steht im Kopf der breiten Ansicht */
  @media (max-width: 600px) {
    .lang, .fassung { display: none; }
  }
</style>
