<script lang="ts">
  // Protokolle wie in der Leitstelle mit Reitern: das Stellwerk selbst, Docker und je Teil einer Webapp seine Ausgabe.
  import type { Protokollziel } from '../lib/api';
  import type { Stand } from '../lib/typen.gen';
  import { weg } from '../lib/weg.svelte';
  import Protokoll from '../teile/Protokoll.svelte';

  let { stand: s }: { stand: Stand } = $props();
  const reiter = $derived([
    ...(s.docker ? [{ pfad: 'docker', name: 'Docker', symbol: 'fa-box', ziel: { art: 'docker' } as Protokollziel }] : []),
    ...s.apps.flatMap((a) => a.teile.map((t) => ({ pfad: `${a.kennung}/${t.kennung}`, name: `${a.name} ${t.name}`, symbol: 'fa-gear',
                                                  ziel: { art: 'teil', app: a.kennung, teil: t.kennung } as Protokollziel }))),
  ]);
  const gewaehlt = $derived(reiter.find((r) => r.pfad === weg.rest) ?? null);
</script>

<div class="seiteninhalt seite-protokoll">
  <div class="rahmen-kopf">
    <div class="seitenkopf"><h1>Protokoll</h1></div>
    <div class="reiter">
      <button class:aktiv={gewaehlt === null} onclick={() => weg.gehe('protokoll')}><i class="fa-solid fa-traffic-light"></i> Stellwerk</button>
      {#each reiter as r (r.pfad)}
        <button class:aktiv={gewaehlt?.pfad === r.pfad} onclick={() => weg.gehe('protokoll', r.pfad)}><i class="fa-solid {r.symbol}"></i> {r.name}</button>
      {/each}
    </div>
  </div>
  <div class="rollfeld" style="--hoehe: calc(100vh - 300px)">
    {#key gewaehlt?.pfad}<Protokoll ziel={gewaehlt?.ziel ?? { art: 'stellwerk' }} zeilen={1000} />{/key}
  </div>
</div>
