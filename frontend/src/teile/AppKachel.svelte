<script lang="ts">
  // Eine Webapp als Karte zum Überblick: Name mit Zweck, Schalter, Zustand, Teile kurz mit Programm, Kerne, RAM und
  // Platte, Hinweise. Ein Klick auf die
  // Karte (nicht auf Schalter oder Öffnen) führt zur Detailansicht: der Namenslink überdeckt die Karte, die Bedienung
  // liegt darüber. So geht es auch per Tastatur und mit Mittelklick in einen neuen Reiter.
  import { gb, kerne } from '../lib/format';
  import { SCHALTWORT, schalten } from '../lib/schalten.svelte';
  import type { AppAnsicht } from '../lib/typen.gen';
  import { weg } from '../lib/weg.svelte';
  import { APPZUSTAND, ART, MASS, PUNKT, ZUSTAND } from '../lib/wort';
  import Schalter from './Schalter.svelte';
  import TeilName from './TeilName.svelte';
  import Zweck from './Zweck.svelte';

  let { app: a }: { app: AppAnsicht } = $props();

  const z = $derived(APPZUSTAND[a.zustand]);
  const arbeitet = $derived(schalten.was(a.kennung));
  // ohne Messwert sagt der Tooltip, warum: nichts eingetragen oder noch nicht gemessen
  const platteSatz = $derived(a.platte_gb != null ? MASS.platte.satz
    : a.teile.some((t) => t.daten.length || t.art === 'docker') ? 'Noch nicht gemessen' : 'Keine Datenorte eingetragen (Feld daten der App-Datei)');
  // Hinweise knapp und gleich gebaut; die ganzen Meldungen stehen in der Detailansicht
  const hinweise = $derived([
    ...a.teile.filter((t) => t.zustand === 'gestoert' && t.meldung).slice(0, 1)
      .map((t) => ({ klasse: 'gefahr', symbol: 'fa-triangle-exclamation', text: `${t.name}: ${t.meldung}` })),
    ...(a.nutzt.some((n) => n.erreichbar === false)
      ? [{ klasse: 'warnung', symbol: 'fa-link-slash', text: `Nicht erreichbar: ${a.nutzt.filter((n) => n.erreichbar === false).map((n) => n.name).join(', ')}` }]
      : []),
  ]);
</script>

<article class="karte kachel">
  <div class="kopfzeile">
    <div class="titel">
      <h2><a class="ziel" href={weg.pfad('apps', a.kennung)} onclick={(e) => weg.klick(e, 'apps', a.kennung)}>{a.name}</a></h2>
      <Zweck zweck={a.zweck} />
    </div>
    <div class="bedienung">
      {#if a.oberflaeche && a.zustand === 'laeuft'}<a class="knopf klein ohne symbol" href={a.oberflaeche} target="_blank" rel="noopener" title="Webapp im Browser öffnen" aria-label="{a.name} öffnen"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>{/if}
      <Schalter app={a} />
    </div>
  </div>

  <div class="lagezeile">
    <span class="zustand {z.klasse}"><i class="fa-solid {arbeitet ? 'fa-circle-notch fa-spin' : z.symbol}"></i>{arbeitet ? SCHALTWORT[arbeitet] : z.wort}</span>
    {#each a.arten as art (art)}<span class="art"><i class="fa-solid {ART[art].symbol}"></i>{ART[art].wort}</span>{/each}
  </div>

  <ul class="teilchen" aria-label="Teile">
    {#each a.teile as t (t.kennung)}<li><span class="punkt {PUNKT[t.zustand]}" title={ZUSTAND[t.zustand].wort}></span><TeilName teil={t} /></li>{/each}
  </ul>

  <dl class="last">
    <div title={MASS.kerne.satz}><dt>{MASS.kerne.wort}</dt><dd><b class="zahl">{kerne(a.cpu_prozent)}</b></dd></div>
    <div title={MASS.ram.satz}><dt>{MASS.ram.wort}</dt><dd><b class="zahl">{gb(a.gb_jetzt)}</b></dd></div>
    <div title={platteSatz}><dt>{MASS.platte.wort}</dt><dd><b class="zahl">{gb(a.platte_gb)}</b></dd></div>
  </dl>

  {#if hinweise.length}
    <div class="hinweise">
      {#each hinweise as h (h.text)}<p class="hinweis klein {h.klasse}"><i class="fa-solid {h.symbol}"></i><span>{h.text}</span></p>{/each}
    </div>
  {/if}
</article>

<style>
  .kachel { position: relative; display: flex; flex-direction: column; gap: var(--sw-a3); min-width: 0; transition: background var(--sw-schnell); }
  .kachel:hover { background: var(--sw-karte-2); }
  .kachel:focus-within { outline: 2px solid rgba(var(--sw-akzent-rgb), 0.5); outline-offset: 2px; }
  .kopfzeile { display: flex; align-items: flex-start; gap: var(--sw-a3); }
  .titel { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  h2 { font-size: var(--sw-gr-titel); line-height: 1.25; overflow-wrap: anywhere; }
  .ziel { color: var(--sw-text); }
  .ziel:focus-visible { outline: none; }
  /* der Namenslink überdeckt die ganze Karte */
  .ziel::after { content: ""; position: absolute; inset: 0; border-radius: var(--sw-ecke); }
  .bedienung { position: relative; z-index: 1; display: flex; align-items: center; gap: var(--sw-a2); flex: none; }
  .lagezeile { display: flex; align-items: center; gap: var(--sw-a2) var(--sw-a3); flex-wrap: wrap; }
  .art { display: inline-flex; align-items: center; gap: 6px; font-size: var(--sw-gr-klein); color: var(--sw-text-2); }
  .teilchen { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: var(--sw-a1) var(--sw-a3); font-size: var(--sw-gr-klein); color: var(--sw-text-2); }
  .teilchen li { display: inline-flex; align-items: center; min-width: 0; overflow-wrap: anywhere; }
  .last { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--sw-a2); margin: 0; }
  .last div { background: var(--sw-flaeche); border-radius: var(--sw-ecke); padding: 6px var(--sw-a3); min-width: 0; }
  .last dt { font-size: var(--sw-gr-marke); font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--sw-text-3); }
  .last dd { margin: 0; font-size: var(--sw-gr-klein); color: var(--sw-text-2); white-space: nowrap; }
  .last b { color: var(--sw-text); font-weight: 600; font-size: var(--sw-gr-text); }
  .hinweise { margin-top: auto; display: flex; flex-direction: column; gap: var(--sw-a2); }
  .hinweise .hinweis { margin: 0; }
  /* höchstens zwei Zeilen; die ganze Meldung steht in der Detailansicht */
  .hinweise .hinweis span { display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
</style>
