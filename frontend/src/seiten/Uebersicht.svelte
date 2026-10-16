<script lang="ts">
  // Übersicht wie in Leitstelle und Maschinenraum: Kennzahlen, links die Webapps mit Schaltern und das Protokoll,
  // rechts Docker und wo die KI herkommt.
  import { gb } from '../lib/format';
  import type { Stand } from '../lib/typen.gen';
  import { APPZUSTAND, ART, istAn } from '../lib/wort';
  import { weg } from '../lib/weg.svelte';
  import DockerKarte from '../teile/DockerKarte.svelte';
  import Protokoll from '../teile/Protokoll.svelte';
  import Schalter from '../teile/Schalter.svelte';

  let { stand: s }: { stand: Stand } = $props();

  const laufen = $derived(s.apps.filter((a) => istAn(a.zustand)));
  const gestoert = $derived(s.apps.filter((a) => a.zustand === 'gestoert'));
  const belegt = $derived(s.apps.reduce((x, a) => x + (a.gb_jetzt ?? 0), 0));
  const satz = $derived(gestoert.length ? `${gestoert.length === 1 ? 'Eine Webapp ist' : `${gestoert.length} Webapps sind`} gestört`
    : laufen.length ? `${laufen.length === 1 ? 'eine Webapp läuft' : `${laufen.length} Webapps laufen`}` : 'alles aus');
</script>

<div class="seiteninhalt seite-uebersicht">
  <div class="rahmen-kopf">
    <div class="seitenkopf"><h1>Übersicht</h1><span class="lagesatz" class:gefahr={gestoert.length > 0}>{satz}</span></div>
    <div class="kennzahlen">
      <div class="kennzahl erfolg"><b>{laufen.length}</b><span>Laufen</span></div>
      <div class="kennzahl"><b>{s.apps.length - laufen.length - gestoert.length}</b><span>Aus</span></div>
      {#if gestoert.length}<div class="kennzahl fehler"><b>{gestoert.length}</b><span>Gestört</span></div>{/if}
      <div class="kennzahl" title="Was die eigenen Prozesse aller Webapps gerade belegen (ohne Container)"><b>{gb(belegt)}</b><span>Webapps belegt</span>
        {#if s.docker?.gb_jetzt != null}<small>Docker {gb(s.docker.gb_jetzt)}</small>{/if}</div>
    </div>
  </div>

  <div class="rollfeld">
    <div class="spalten-uebersicht">
      <div class="links">
        <section class="abschnitt">
          <div class="abschnitt-kopf"><h2>Webapps</h2><a class="mehr" href={weg.pfad('apps')} onclick={(e) => weg.klick(e, 'apps')}>Alle Webapps</a></div>
          {#each s.apps as a (a.kennung)}
            {@const z = APPZUSTAND[a.zustand]}
            <div class="appzeile">
              <div class="name"><a href={weg.pfad('apps')} onclick={(e) => weg.klick(e, 'apps')}>{a.name}</a>
                <span class="zustand {z.klasse}"><i class="fa-solid {z.symbol}"></i>{z.wort}</span>
                {#each a.arten as art (art)}<span class="leise klein" title={ART[art].satz}><i class="fa-solid {ART[art].symbol}"></i> {ART[art].wort}</span>{/each}</div>
              <div class="werte" title="Teile, die laufen, und was sie belegen">
                <b class="zahl">{a.gb_jetzt != null ? gb(a.gb_jetzt) : '-'}</b><span>{a.teile.filter((t) => t.zustand === 'laeuft').length} von {a.teile.length} Teilen</span></div>
              {#if a.oberflaeche && a.zustand === 'laeuft'}<a class="knopf klein ohne" href={a.oberflaeche} target="_blank" rel="noopener" title="Webapp im Browser öffnen"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>{:else}<span></span>{/if}
              <Schalter app={a} />
            </div>
          {:else}
            <p class="leise">Noch keine Webapps. Je Webapp eine Datei im Ordner <span class="code">{s.ordner}/apps</span>.</p>
          {/each}
        </section>
        <section class="abschnitt">
          <div class="abschnitt-kopf"><h2>Protokoll</h2><a class="mehr" href={weg.pfad('protokoll')} onclick={(e) => weg.klick(e, 'protokoll')}>Ganzes Protokoll</a></div>
          <Protokoll zeilen={12} />
        </section>
      </div>
      <div class="rechts">
        {#if s.docker}<DockerKarte docker={s.docker} />{/if}
        <section class="karte">
          <h3><i class="fa-solid fa-tower-broadcast"></i> KI über die Leitstelle</h3>
          <p class="leise klein">Die Webapps halten selbst keine Modelle. Was sie an KI brauchen, holen sie über die Leitstelle; die Modelle laufen im Modell-Läufer und im Maschinenraum.</p>
        </section>
      </div>
    </div>
  </div>
</div>

<style>
  .lagesatz { color: var(--sw-erfolg); font-weight: 600; padding-bottom: 4px; }
  .lagesatz.gefahr { color: var(--sw-gefahr); }
  .spalten-uebersicht { display: grid; grid-template-columns: minmax(0, 1fr) 420px; gap: var(--sw-a5); align-items: start; }
  .links, .rechts { display: flex; flex-direction: column; gap: var(--sw-a4); min-width: 0; }
  .abschnitt-kopf { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: var(--sw-a2); }
  .abschnitt-kopf .mehr { font-size: var(--sw-gr-klein); }
  .appzeile { display: grid; grid-template-columns: minmax(0, 1fr) auto auto auto; align-items: center; gap: var(--sw-a3);
              padding: var(--sw-a3) var(--sw-a4); background: var(--sw-karte); border-radius: var(--sw-ecke); }
  .appzeile + .appzeile { margin-top: var(--sw-a2); }
  .name { display: flex; align-items: center; gap: var(--sw-a3); flex-wrap: wrap; min-width: 0; }
  .name a { color: var(--sw-text); font-weight: 600; }
  .werte { text-align: right; line-height: 1.2; }
  .werte b { display: block; font-weight: 600; }
  .werte span { font-size: var(--sw-gr-marke); color: var(--sw-text-3); }
  @media (max-width: 1100px) { .spalten-uebersicht { grid-template-columns: minmax(0, 1fr); } }
</style>
