<script lang="ts">
  // Detailansicht einer Webapp unter /apps/<kennung>: Name mit Zweck und Beschreibung, alle Teile mit Zustand, Art,
  // Port, Ordner, Last, Laufzeit und Meldung, Starten und Anhalten der ganzen App und einzelner Teile, Protokollauszug
  // je Teil. Rechts die Abhängigkeiten: intern als Startreihenfolge (Teile, braucht, Docker-Laufzeit), außen was die
  // Webapp nutzt und ob es gerade erreichbar ist. Bestätigungen stehen in der Leiste unter dem Kopf, nie im Browser-Dialog.
  import type { Schaltung } from '../lib/api';
  import { dauer, gb, kerne, uhrzeit, vor } from '../lib/format';
  import { SCHALTWORT, schalten } from '../lib/schalten.svelte';
  import type { AppAnsicht, Stand, TeilAnsicht } from '../lib/typen.gen';
  import { weg } from '../lib/weg.svelte';
  import { APPZUSTAND, ART, ZUSTAND, erreichbarkeit, istAn } from '../lib/wort';
  import Protokoll from '../teile/Protokoll.svelte';
  import Zweck from '../teile/Zweck.svelte';

  let { stand: s, kennung }: { stand: Stand; kennung: string } = $props();

  const a = $derived<AppAnsicht | undefined>(s.apps.find((x) => x.kennung === kennung));
  let frage = $state<{ art: Schaltung; teil: TeilAnsicht | null } | null>(null);

  const nachKennung = $derived(new Map((a?.teile ?? []).map((t) => [t.kennung, t])));
  const folge = $derived((a?.folge ?? []).map((k) => nachKennung.get(k)).filter((t): t is TeilAnsicht => !!t));
  const laufen = $derived(a ? a.teile.filter((t) => t.zustand === 'laeuft').length : 0);
  const erreichbar = $derived(a ? a.nutzt.filter((n) => n.erreichbar).length : 0);
  const mitDocker = $derived(!!a && a.arten.includes('docker'));

  /** Was ein Teil vorher braucht, mit Namen; Docker-Teile brauchen die Container-Laufzeit */
  function braucht(t: TeilAnsicht): string[] {
    return [...(t.art === 'docker' ? ['Docker'] : []), ...t.braucht.map((k) => nachKennung.get(k)?.name ?? k)];
  }

  /** Teile, die einen Teil brauchen und gerade laufen: sie laufen weiter, wenn er allein anhält */
  function nutzer(t: TeilAnsicht): string[] {
    return (a?.teile ?? []).filter((x) => x.braucht.includes(t.kennung) && istAn(x.zustand)).map((x) => x.name);
  }

  const fragesatz = $derived.by(() => {
    if (!frage || !a) return '';
    const { art, teil } = frage;
    if (!teil) return art === 'anhalten' ? `${a.name} anhalten? Alle Teile werden in umgekehrter Folge beendet; wer die Webapp nutzt, verliert die Verbindung.`
      : `${a.name} neu starten? Alle Teile werden beendet und wieder gestartet.`;
    const weiter = nutzer(teil);
    const folgen = weiter.length ? ` ${weiter.join(', ')} ${weiter.length === 1 ? 'braucht ihn und läuft' : 'brauchen ihn und laufen'} weiter.` : '';
    return art === 'anhalten' ? `${teil.name} anhalten? Nur dieser Teil wird beendet.${folgen}` : `${teil.name} neu starten? Er ist dabei kurz nicht erreichbar.${folgen}`;
  });

  async function tun(art: Schaltung, teil: TeilAnsicht | null) {
    frage = null;
    if (!a) return;
    await (teil ? schalten.tun(`${a.name} ${teil.name}`, art, a.kennung, teil.kennung) : schalten.tun(a.name, art, a.kennung));
  }

  /** Starten sofort; Anhalten und Neustarten erst nach Bestätigung in der Leiste */
  function bitte(art: Schaltung, teil: TeilAnsicht | null = null) {
    if (art === 'starten') void tun(art, teil);
    else frage = { art, teil };
  }

  const appArbeitet = $derived(a ? schalten.was(a.kennung) : undefined);
</script>

{#if !a}
  <div class="seiteninhalt">
    <div class="verbinden"><div class="leer"><i class="fa-solid fa-circle-question"></i><h2>Diese Webapp gibt es hier nicht</h2>
      <p>Unter <span class="code">{s.ordner}/apps</span> steht keine Datei <span class="code">{kennung}.toml</span>, oder sie ist fehlerhaft.</p>
      <a class="knopf" href={weg.pfad('apps')} onclick={(e) => weg.klick(e, 'apps')}><i class="fa-solid fa-arrow-left"></i> Alle Webapps</a></div></div>
  </div>
{:else}
  {@const z = APPZUSTAND[a.zustand]}
  <div class="seiteninhalt seite-detail">
    <div class="rahmen-kopf">
      <a class="zurueck" href={weg.pfad('apps')} onclick={(e) => weg.klick(e, 'apps')}><i class="fa-solid fa-arrow-left"></i> Webapps</a>
      <div class="seitenkopf">
        <h1>{a.name}</h1>
        <Zweck zweck={a.zweck} datei={a.datei} />
        <span class="zustand {z.klasse}"><i class="fa-solid {appArbeitet ? 'fa-circle-notch fa-spin' : z.symbol}"></i>{appArbeitet ? SCHALTWORT[appArbeitet] : z.wort}</span>
        <div class="aktionen">
          {#if a.oberflaeche && a.zustand === 'laeuft'}<a class="knopf ohne" href={a.oberflaeche} target="_blank" rel="noopener" title="Webapp im Browser öffnen"><i class="fa-solid fa-arrow-up-right-from-square"></i> Öffnen</a>{/if}
          {#if !istAn(a.zustand)}
            <button class="knopf haupt" disabled={!!appArbeitet} onclick={() => bitte('starten')} title="Alle Teile starten, wer gebraucht wird zuerst"><i class="fa-solid fa-play"></i> Starten</button>
          {:else}
            <button class="knopf" disabled={!!appArbeitet} onclick={() => bitte('anhalten')} title="Alle Teile anhalten, in umgekehrter Folge"><i class="fa-solid fa-stop"></i> Anhalten</button>
            <button class="knopf ohne" disabled={!!appArbeitet} onclick={() => bitte('neustarten')} title="Alle Teile anhalten und wieder starten"><i class="fa-solid fa-rotate-right"></i> Neu starten</button>
          {/if}
        </div>
        {#if a.beschreibung}<p class="unterzeile">{a.beschreibung}</p>{/if}
      </div>
      <div class="kennzahlen">
        <div class="kennzahl" class:erfolg={laufen > 0 && laufen === a.teile.length}><b>{laufen} / {a.teile.length}</b><span>Teile laufen</span></div>
        <div class="kennzahl" title="Prozessorlast der eigenen Prozesse; ein Kern voll ausgelastet ist 1"><b>{kerne(a.cpu_prozent)}</b><span>Kerne</span></div>
        <div class="kennzahl" title="Was die eigenen Prozesse gerade belegen; Container zählen bei Docker"><b>{gb(a.gb_jetzt)}</b><span>Speicher</span></div>
        {#if a.nutzt.length}<div class="kennzahl" class:fehler={erreichbar < a.nutzt.length && a.nutzt.every((n) => n.erreichbar !== null)}><b>{erreichbar} / {a.nutzt.length}</b><span>Nutzt erreichbar</span></div>{/if}
      </div>
      {#if frage}
        <div class="bestaetigen"><i class="fa-solid fa-triangle-exclamation"></i>
          <span>{fragesatz}</span>
          <div class="rechts"><button class="knopf klein ohne" onclick={() => (frage = null)}>Abbrechen</button>
            <button class="knopf klein gefahr-voll" onclick={() => frage && tun(frage.art, frage.teil)}>{frage.art === 'anhalten' ? 'Ja, anhalten' : 'Ja, neu starten'}</button></div></div>
      {/if}
    </div>

    <div class="rollfeld">
      <div class="spalten-detail">
        <section class="spalte" aria-label="Teile">
          <h2 class="abschnitt">Teile</h2>
          {#each a.teile as t (t.kennung)}
            {@const tz = ZUSTAND[t.zustand]}
            {@const arbeitet = schalten.was(a.kennung, t.kennung)}
            {@const gesperrt = !!arbeitet || !!appArbeitet}
            <article class="karte teilkarte">
              <header>
                <span class="zustand {tz.klasse}"><i class="fa-solid {arbeitet ? 'fa-circle-notch fa-spin' : tz.symbol}"></i>{arbeitet ? SCHALTWORT[arbeitet] : tz.wort}</span>
                <h3>{t.name}</h3>
                {#if t.zweck}<span class="teilzweck">{t.zweck}</span>{/if}
                <span class="art" title={ART[t.art].satz}><i class="fa-solid {ART[t.art].symbol}"></i>{ART[t.art].wort}</span>
                {#if t.aktiv}<span class="arbeitet" title="Prozessorlast über der Schwelle des Teils"><i class="fa-solid fa-gear fa-spin"></i> arbeitet</span>{/if}
                {#if t.fremd}<span class="leise klein" title="Lief schon, ohne vom Stellwerk gestartet zu sein; das Stellwerk misst ihn und kann ihn anhalten"><i class="fa-solid fa-hand"></i> von außen gestartet</span>{/if}
              </header>
              <dl class="angaben">
                {#if t.port}<dt>Port</dt><dd class="zahl">{t.port}</dd>{/if}
                <dt>Ordner</dt><dd><span class="code">{t.ordner}</span></dd>
                {#if t.cpu_prozent != null || t.gb_jetzt != null}<dt>Last</dt><dd><span class="zahl">{kerne(t.cpu_prozent)}</span> Kerne, <span class="zahl">{gb(t.gb_jetzt)}</span> Speicher</dd>{/if}
                {#if t.laeuft_seit != null}<dt>Laufzeit</dt><dd>{dauer(s.zeit - t.laeuft_seit)} <span class="leise">(seit {uhrzeit(t.laeuft_seit)})</span></dd>{/if}
                {#if t.pids.length}<dt>Prozesse</dt><dd class="zahl" title="Prozesse, die das Stellwerk für diesen Teil führt">{t.pids.join(', ')}</dd>{/if}
              </dl>
              {#if t.meldung && !t.fremd}<div class="hinweis klein {t.zustand === 'gestoert' ? 'gefahr' : 'warnung'}"><i class="fa-solid fa-triangle-exclamation"></i><span>{t.meldung}</span></div>{/if}
              <div class="knoepfe">
                {#if !istAn(t.zustand)}
                  <button class="knopf klein" disabled={gesperrt} onclick={() => bitte('starten', t)} title="Diesen Teil starten, mit allem, was er braucht"><i class="fa-solid fa-play"></i> Starten</button>
                {:else}
                  <button class="knopf klein" disabled={gesperrt} onclick={() => bitte('anhalten', t)} title="Nur diesen Teil anhalten"><i class="fa-solid fa-stop"></i> Anhalten</button>
                  <button class="knopf klein ohne" disabled={gesperrt} onclick={() => bitte('neustarten', t)} title="Diesen Teil anhalten und wieder starten"><i class="fa-solid fa-rotate-right"></i> Neu starten</button>
                {/if}
                <a class="knopf klein ohne" href={weg.pfad('protokoll', `${a.kennung}/${t.kennung}`)} onclick={(e) => weg.klick(e, 'protokoll', `${a.kennung}/${t.kennung}`)} title="Ganzes Protokoll dieses Teils"><i class="fa-solid fa-scroll"></i> Ganzes Protokoll</a>
              </div>
              <div class="auszug"><Protokoll ziel={{ art: 'teil', app: a.kennung, teil: t.kennung }} zeilen={80} /></div>
            </article>
          {/each}
        </section>

        <section class="spalte abhaengig" aria-label="Abhängigkeiten">
          <h2 class="abschnitt">Abhängigkeiten</h2>
          <div class="karte">
            <h3><i class="fa-solid fa-list-ol"></i> Startreihenfolge</h3>
            <ol class="folge">
              {#if mitDocker && s.docker}
                {@const dz = ZUSTAND[s.docker.zustand]}
                <li><span class="nr zahl">1</span><div><b>Docker</b> <span class="zustand {dz.klasse}"><i class="fa-solid {dz.symbol}"></i>{dz.wort}</span>
                  <small>Container-Laufzeit; startet vor den Docker-Teilen, angehalten nur von Hand</small></div></li>
              {/if}
              {#each folge as t, i (t.kennung)}
                {@const tz = ZUSTAND[t.zustand]}
                {@const vorher = braucht(t)}
                <li><span class="nr zahl">{i + 1 + (mitDocker && s.docker ? 1 : 0)}</span><div><b>{t.name}</b> <span class="zustand {tz.klasse}"><i class="fa-solid {tz.symbol}"></i>{tz.wort}</span>
                  {#if vorher.length}<small>braucht {vorher.join(', ')}</small>{/if}</div></li>
              {/each}
            </ol>
            <p class="leise klein">Gestartet wird von oben nach unten, angehalten umgekehrt{mitDocker ? '; Docker bleibt dabei an' : ''}.</p>
          </div>

          <div class="karte">
            <h3><i class="fa-solid fa-link"></i> Nutzt <span class="rechts">außerhalb der Webapp</span></h3>
            {#each a.nutzt as n (n.name)}
              {@const e = erreichbarkeit(n.erreichbar)}
              <div class="nutzung">
                <div class="nutzung-kopf"><b>{n.name}</b><span class="zustand {e.klasse}"><i class="fa-solid {e.symbol}"></i>{e.wort}</span></div>
                <div class="nutzung-zweck">{n.zweck}</div>
                <div class="nutzung-ziel"><span class="code">{n.ziel}</span></div>
                {#if n.geprueft != null}<small>geprüft {vor(n.geprueft, s.zeit)}{n.meldung ? `: ${n.meldung}` : ''}</small>{/if}
              </div>
            {:else}
              <p class="leise klein">Was die Webapp außerhalb ihrer Teile braucht (Leitstelle, Kellerwolke, Fundus), steht in der App-Datei unter <span class="code">[[nutzt]]</span>; das Stellwerk prüft dann, ob es erreichbar ist.</p>
            {/each}
          </div>

          <div class="karte">
            <h3><i class="fa-solid fa-file-lines"></i> App-Datei</h3>
            <p class="datei"><span class="code">{a.datei}</span></p>
            {#if a.soll === 'laeuft'}<p class="leise klein"><i class="fa-solid fa-rotate"></i> Startet mit dem Rechner wieder an.</p>{/if}
          </div>
        </section>
      </div>
    </div>
  </div>
{/if}

<style>
  .zurueck { display: inline-flex; align-items: center; gap: var(--sw-a2); font-size: var(--sw-gr-klein); color: var(--sw-text-2); margin-bottom: var(--sw-a2); }
  .zurueck:hover { color: var(--sw-akzent-schrift); }
  .seite-detail h1 { overflow-wrap: anywhere; min-width: 0; }
  .seite-detail .seitenkopf { align-items: baseline; row-gap: var(--sw-a2); }
  .seite-detail .seitenkopf .aktionen { align-self: center; }
  .kennzahl b { white-space: nowrap; }
  .rollfeld { overflow-x: clip; }
  .spalten-detail { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 440px); gap: var(--sw-a5); align-items: start; }
  .spalte { display: flex; flex-direction: column; gap: var(--sw-a3); min-width: 0; }
  .spalte :global(.karte + .karte) { margin-top: 0; }
  .abschnitt { font-size: var(--sw-gr-titel); }
  .teilkarte { display: flex; flex-direction: column; gap: var(--sw-a3); }
  .teilkarte header { display: flex; align-items: center; gap: var(--sw-a2) var(--sw-a3); flex-wrap: wrap; }
  .teilkarte h3 { font-size: var(--sw-gr-titel); margin: 0; }
  .teilzweck { color: var(--sw-text-2); font-weight: 500; overflow-wrap: anywhere; }
  .art { display: inline-flex; align-items: center; gap: 6px; font-size: var(--sw-gr-klein); color: var(--sw-text-2); }
  .arbeitet { color: var(--sw-akzent-schrift); font-size: var(--sw-gr-klein); }
  .angaben { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: var(--sw-a2) var(--sw-a4); margin: 0; font-size: var(--sw-gr-klein); }
  .angaben dt { color: var(--sw-text-3); }
  .angaben dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
  .knoepfe { display: flex; gap: var(--sw-a2); flex-wrap: wrap; }
  .auszug { --hoehe: 220px; }
  .auszug :global(.protokoll) { margin-top: 0; }
  .folge { list-style: none; margin: 0 0 var(--sw-a3); padding: 0; display: flex; flex-direction: column; gap: var(--sw-a2); }
  .folge li { display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: var(--sw-a2); align-items: start; background: var(--sw-karte-2);
              border-radius: var(--sw-ecke); padding: var(--sw-a2) var(--sw-a3); }
  .folge .nr { color: var(--sw-text-3); font-weight: 600; text-align: right; line-height: 1.9; }
  .folge li > div { display: flex; flex-wrap: wrap; align-items: center; gap: 4px var(--sw-a2); min-width: 0; }
  .folge small, .nutzung small { display: block; width: 100%; color: var(--sw-text-3); font-size: var(--sw-gr-klein); }
  .nutzung { display: flex; flex-direction: column; gap: 4px; padding: var(--sw-a2) var(--sw-a3); background: var(--sw-karte-2); border-radius: var(--sw-ecke); }
  .nutzung + .nutzung { margin-top: var(--sw-a2); }
  .nutzung-kopf { display: flex; align-items: center; justify-content: space-between; gap: var(--sw-a2); flex-wrap: wrap; }
  .nutzung-zweck { color: var(--sw-text-2); }
  .nutzung-ziel, .datei { font-size: var(--sw-gr-klein); overflow-wrap: anywhere; }
  .datei { margin-bottom: var(--sw-a2); }
  /* eine Spalte: die Abhängigkeiten vorn, die Startreihenfolge ist zugleich die kurze Übersicht der Teile */
  @media (max-width: 1100px) { .spalten-detail { grid-template-columns: minmax(0, 1fr); } .abhaengig { order: -1; } }
</style>
