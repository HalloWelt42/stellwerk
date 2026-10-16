<script lang="ts">
  // Kopf wie in der Leitstelle: Marke links, rechts die Lage der Webapps
  import { lage } from '../lib/stand.svelte';
  import { istAn } from '../lib/wort';
  import { weg } from '../lib/weg.svelte';

  const s = $derived(lage.stand);
  const gestoert = $derived(s?.apps.filter((a) => a.zustand === 'gestoert') ?? []);
  const laufen = $derived(s?.apps.filter((a) => istAn(a.zustand)).length ?? 0);
</script>

<header class="kopf">
  <div class="marke">
    <img class="marke-bild" src="/symbol.svg" alt="" />
    <span class="marke-name">Stellwerk</span>
    {#if s}<span class="zahl">{s.version}</span>{/if}
  </div>
  {#if s}<span class="rechner" title="Dieser Rechner"><i class="fa-solid fa-desktop"></i>{s.rechner}</span>{/if}

  <div class="kopf-aktionen">
    {#if !lage.erreichbar}
      <span class="lage engpass" title="Die Oberfläche bekommt keine Antwort vom Stellwerk"><span class="punkt gefahr"></span>Keine Antwort</span>
    {:else if s}
      <a class="lage {gestoert.length ? 'engpass' : 'ruhig'}" href={weg.pfad('apps')} onclick={(e) => weg.klick(e, 'apps')}
         title={gestoert.length ? `Gestört: ${gestoert.map((a) => a.name).join(', ')}` : 'Webapps, die laufen'}>
        <span class="punkt" class:lebt={!gestoert.length && laufen > 0} class:gefahr={gestoert.length > 0} class:aus={!gestoert.length && !laufen}></span>
        {gestoert.length ? `${gestoert.length} gestört` : `${laufen} von ${s.apps.length} Webapps laufen`}</a>
    {/if}
  </div>
</header>

<style>
  .rechner { display: inline-flex; align-items: center; gap: var(--sw-a2); color: var(--sw-text-2); white-space: nowrap; }
  .rechner i { color: var(--sw-text-3); }
  a.lage { text-decoration: none; }
</style>
