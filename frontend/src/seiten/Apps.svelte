<script lang="ts">
  // Alle Webapps, als ausführliche Liste (je App alle Teile) oder als Karten zum Überblick; die Wahl merkt sich das
  // Gerät. Name oder Karte führen zur Detailansicht. Fehlerhafte App-Dateien oben als Hinweis, Docker darunter, wenn
  // eine Webapp es braucht.
  import { ansicht, type AppAnsichtArt } from '../lib/ansicht.svelte';
  import { gb } from '../lib/format';
  import type { Stand } from '../lib/typen.gen';
  import { istAn } from '../lib/wort';
  import AppKachel from '../teile/AppKachel.svelte';
  import AppKarte from '../teile/AppKarte.svelte';
  import DockerKarte from '../teile/DockerKarte.svelte';

  let { stand: s }: { stand: Stand } = $props();
  const laufen = $derived(s.apps.filter((a) => istAn(a.zustand)).length);
  const gestoert = $derived(s.apps.filter((a) => a.zustand === 'gestoert').length);
  const belegt = $derived(s.apps.reduce((x, a) => x + (a.gb_jetzt ?? 0), 0));

  const ARTEN: [AppAnsichtArt, string, string, string][] = [
    ['liste', 'Liste', 'fa-list', 'Je Webapp alle Teile mit Zustand, Port und Protokoll'],
    ['karten', 'Karten', 'fa-table-cells-large', 'Je Webapp eine Karte zum Überblick; Klick öffnet die Detailansicht'],
  ];
</script>

<div class="seiteninhalt seite-apps">
  <div class="rahmen-kopf">
    <div class="seitenkopf"><h1>Webapps</h1><span class="zahl">{s.apps.length}</span>
      <div class="aktionen">
        <span class="stufen" role="group" aria-label="Ansicht der Webapps">
          {#each ARTEN as [art, wort, symbol, satz] (art)}
            <button class:an={ansicht.apps === art} aria-pressed={ansicht.apps === art} title={satz} onclick={() => ansicht.setzeApps(art)}><i class="fa-solid {symbol}"></i> {wort}</button>
          {/each}
        </span>
      </div>
      <p class="unterzeile">Eigene Webapps dieses Rechners mit allen Teilen, nativ oder mit Docker. KI nutzen sie nur über die Leitstelle; die KI-Dienste selbst stehen im Maschinenraum.</p></div>
    <div class="kennzahlen">
      <div class="kennzahl erfolg"><b>{laufen}</b><span>Laufen</span></div>
      <div class="kennzahl"><b>{s.apps.length - laufen - gestoert}</b><span>Aus</span></div>
      {#if gestoert}<div class="kennzahl fehler"><b>{gestoert}</b><span>Gestört</span></div>{/if}
      <div class="kennzahl" title="Arbeitsspeicher, den die eigenen Prozesse aller Webapps fest belegen (ohne Container)"><b>{gb(belegt)}</b><span>RAM</span></div>
    </div>
  </div>
  <div class="rollfeld liste-apps">
    {#each s.ladefehler as f (f.datei)}
      <div class="hinweis gefahr klein"><i class="fa-solid fa-file-circle-exclamation"></i><span>Datei <b>{f.datei}</b> wird übergangen: {f.meldung}</span></div>
    {/each}
    {#if ansicht.apps === 'karten'}
      <div class="raster-kacheln">{#each s.apps as a (a.kennung)}<AppKachel app={a} />{/each}</div>
    {:else}
      {#each s.apps as a (a.kennung)}<AppKarte app={a} />{/each}
    {/if}
    {#if s.docker}<DockerKarte docker={s.docker} />{/if}
    {#if !s.apps.length}
      <div class="leer"><i class="fa-solid fa-window-maximize"></i><h2>Noch keine Webapps</h2>
        <p>Je Webapp eine Datei im Ordner <span class="code">{s.ordner}/apps</span> anlegen: Name, Zweck und ihre Teile, jeder mit Ordner und Befehl oder Container. Das Stellwerk liest sie im nächsten Takt.</p></div>
    {/if}
  </div>
</div>

<style>
  .liste-apps { display: flex; flex-direction: column; gap: var(--sw-a3); overflow-x: clip; }
  .liste-apps :global(.app), .liste-apps :global(.docker) { margin: 0; }
  .raster-kacheln { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(340px, 100%), 1fr)); gap: var(--sw-a3); }
  .raster-kacheln :global(.karte + .karte) { margin-top: 0; }
  .stufen button { display: inline-flex; align-items: center; gap: 7px; }
</style>
