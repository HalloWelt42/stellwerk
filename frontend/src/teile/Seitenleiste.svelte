<script lang="ts">
  // Menü wie in Leitstelle und Maschinenraum: oben die Arbeitsseiten, darunter System, ganz unten die Ansicht.
  // Pillen nur, wo etwas Bedeutsames passiert; nie Gesamtzahlen.
  import { ansicht } from '../lib/ansicht.svelte';
  import { lage } from '../lib/stand.svelte';
  import { weg, type Seite } from '../lib/weg.svelte';

  const s = $derived(lage.stand);
  const pillen = $derived.by(() => {
    const p: Partial<Record<Seite, { zahl: number; klasse: string; satz: string }>> = {};
    if (!s) return p;
    const gestoert = s.apps.filter((a) => a.zustand === 'gestoert');
    if (gestoert.length) p.apps = { zahl: gestoert.length, klasse: 'gefahr', satz: `Gestört: ${gestoert.map((a) => a.name).join(', ')}` };
    if (s.ladefehler.length) p.ordner = { zahl: s.ladefehler.length, klasse: 'gefahr', satz: `Fehlerhafte Dateien: ${s.ladefehler.map((f) => f.datei).join(', ')}` };
    return p;
  });

  const NAVI: [string, string, Seite][] = [
    ['Übersicht', 'fa-traffic-light', 'uebersicht'],
    ['Webapps', 'fa-window-maximize', 'apps'],
  ];
  const SYSTEM: [string, string, Seite][] = [
    ['Protokoll', 'fa-terminal', 'protokoll'],
    ['Ordner', 'fa-folder-open', 'ordner'],
  ];
</script>

{#snippet eintrag(name: string, symbol: string, seite: Seite)}
  <a class="navi" class:aktiv={weg.seite === seite} href={weg.pfad(seite)} onclick={(e) => weg.klick(e, seite)} title={name}>
    <i class="fa-solid {symbol}"></i>{name}
    {#if pillen[seite]}<span class="zaehler pille {pillen[seite]?.klasse}" title={pillen[seite]?.satz}>{pillen[seite]?.zahl}</span>{/if}
  </a>
{/snippet}

<nav class="seite">
  {#each NAVI as [name, symbol, seite] (seite)}{@render eintrag(name, symbol, seite)}{/each}
  <div class="etikett">System</div>
  {#each SYSTEM as [name, symbol, seite] (seite)}{@render eintrag(name, symbol, seite)}{/each}

  <div class="ansicht">
    <div class="etikett">Ansicht</div>
    <span class="stufen" title="Thema dieser Oberfläche auf diesem Gerät">
      <button class:an={ansicht.thema === 'dunkel'} onclick={() => ansicht.setzeThema('dunkel')}>Dunkel</button>
      <button class:an={ansicht.thema === 'hell'} onclick={() => ansicht.setzeThema('hell')}>Hell</button>
    </span>
    <span class="stufen" title="Schriftgröße auf diesem Gerät">
      <button class:an={ansicht.schrift === 'klein'} onclick={() => ansicht.setzeSchrift('klein')}>Klein</button>
      <button class:an={ansicht.schrift === 'mittel'} onclick={() => ansicht.setzeSchrift('mittel')}>Mittel</button>
      <button class:an={ansicht.schrift === 'gross'} onclick={() => ansicht.setzeSchrift('gross')}>Groß</button>
    </span>
  </div>
</nav>
