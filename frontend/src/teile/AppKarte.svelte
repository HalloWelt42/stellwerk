<script lang="ts">
  // Eine Webapp: Zustand, Teile mit ihrem Stand, Schalter für alle Teile, Öffnen. Anhalten fragt erst nach (ohne Browser-Dialog).
  import { api, type Schaltung } from '../lib/api';
  import { gb } from '../lib/format';
  import { meldungen } from '../lib/meldung.svelte';
  import { lage } from '../lib/stand.svelte';
  import type { AppAnsicht } from '../lib/typen.gen';
  import { APPZUSTAND, ART, ZUSTAND, istAn } from '../lib/wort';
  import Protokoll from './Protokoll.svelte';

  let { app: a }: { app: AppAnsicht } = $props();

  let arbeitet = $state<Schaltung | ''>('');
  let fragen = $state<'' | 'anhalten' | 'neustarten'>('');
  let offen = $state<string | null>(null);

  const z = $derived(APPZUSTAND[a.zustand]);
  const an = $derived(istAn(a.zustand));

  async function tun(art: Schaltung) {
    fragen = '';
    arbeitet = art;
    try {
      const e = await api.app(a.kennung, art);
      meldungen.zeigen(`${a.name}: ${e.meldung}`, e.erfolg ? 'erfolg' : 'fehler');
      if (!e.erfolg) offen = a.teile.find((t) => t.zustand === 'gestoert')?.kennung ?? offen;
    } catch (f) {
      meldungen.fehler(f);
    } finally {
      arbeitet = '';
      await lage.jetzt();
    }
  }
</script>

<article class="karte app" class:an>
  <header>
    <span class="zustand {z.klasse}"><i class="fa-solid {arbeitet ? 'fa-circle-notch fa-spin' : z.symbol}"></i>{arbeitet === 'starten' ? 'Startet' : arbeitet === 'anhalten' ? 'Hält an' : arbeitet === 'neustarten' ? 'Startet neu' : z.wort}</span>
    <h2>{a.name}</h2>
    {#each a.arten as art (art)}<span class="art" title={ART[art].satz}><i class="fa-solid {ART[art].symbol}"></i>{ART[art].wort}</span>{/each}
    {#if a.gb_jetzt != null}<div class="speicherzahl" title="Was die eigenen Prozesse der Webapp gerade belegen; Container zählen bei Docker"><b class="zahl">{gb(a.gb_jetzt)}</b><span>belegt</span></div>{/if}
  </header>
  {#if a.beschreibung}<p class="beschreibung">{a.beschreibung}</p>{/if}

  <ul class="teile">
    {#each a.teile as t (t.kennung)}
      {@const tz = ZUSTAND[t.zustand]}
      <li>
        <div class="teil">
          <span class="zustand {tz.klasse}"><i class="fa-solid {tz.symbol}"></i>{tz.wort}</span>
          <b>{t.name}</b>
          <span class="leise" title={ART[t.art].satz}><i class="fa-solid {ART[t.art].symbol}"></i> {ART[t.art].wort}</span>
          {#if t.port}<span class="zahl leise" title="Port, auf dem der Teil antwortet">Port {t.port}</span>{/if}
          {#if t.aktiv}<span class="arbeitet" title="Prozessorlast {t.cpu_prozent} Prozent eines Kerns"><i class="fa-solid fa-gear fa-spin"></i> arbeitet</span>{/if}
          {#if t.fremd}<span class="leise" title="Lief schon, ohne vom Stellwerk gestartet zu sein; das Stellwerk misst ihn und kann ihn anhalten"><i class="fa-solid fa-hand"></i> von außen gestartet</span>{/if}
          <span class="rechts">
            {#if t.gb_jetzt != null}<span class="zahl" title="Gerade gemessen">{gb(t.gb_jetzt)}</span>{/if}
            <button class="knopf klein ohne" class:aktiv={offen === t.kennung} onclick={() => (offen = offen === t.kennung ? null : t.kennung)} title="Ausgabe dieses Teils"><i class="fa-solid fa-scroll"></i> Protokoll</button>
          </span>
        </div>
        {#if t.meldung && !t.fremd}<div class="hinweis klein {t.zustand === 'gestoert' ? 'gefahr' : 'warnung'}"><i class="fa-solid fa-triangle-exclamation"></i><span>{t.meldung}</span></div>{/if}
        {#if offen === t.kennung}<Protokoll ziel={{ art: 'teil', app: a.kennung, teil: t.kennung }} />{/if}
      </li>
    {/each}
  </ul>

  {#if fragen}
    <div class="bestaetigen"><i class="fa-solid fa-triangle-exclamation"></i>
      <span>{a.name} {fragen === 'anhalten' ? 'anhalten' : 'neu starten'}? Alle Teile werden beendet; wer die Webapp gerade nutzt, verliert die Verbindung.</span>
      <div class="rechts"><button class="knopf klein ohne" onclick={() => (fragen = '')}>Abbrechen</button>
        <button class="knopf klein gefahr-voll" onclick={() => tun(fragen as Schaltung)}>{fragen === 'anhalten' ? 'Ja, anhalten' : 'Ja, neu starten'}</button></div></div>
  {/if}

  <footer>
    {#if !an}
      <button class="knopf haupt" disabled={!!arbeitet} onclick={() => tun('starten')} title="Alle Teile starten, wer gebraucht wird zuerst"><i class="fa-solid fa-play"></i> Starten</button>
    {:else}
      <button class="knopf" disabled={!!arbeitet} onclick={() => (fragen = 'anhalten')} title="Alle Teile anhalten, in umgekehrter Folge"><i class="fa-solid fa-stop"></i> Anhalten</button>
      <button class="knopf ohne" disabled={!!arbeitet} onclick={() => (fragen = 'neustarten')} title="Alle Teile anhalten und wieder starten"><i class="fa-solid fa-rotate-right"></i> Neu starten</button>
    {/if}
    {#if a.oberflaeche && a.zustand === 'laeuft'}<a class="knopf ohne" href={a.oberflaeche} target="_blank" rel="noopener" title="Webapp im Browser öffnen"><i class="fa-solid fa-arrow-up-right-from-square"></i> Öffnen</a>{/if}
    {#if a.soll === 'laeuft'}<span class="leise klein" title="Läuft nach einem Neustart des Rechners wieder an"><i class="fa-solid fa-rotate"></i> startet mit dem Rechner</span>{/if}
    <span class="datei" title="Datei der Webapp: Teile, Befehle, Ordner, Ports">{a.datei}</span>
  </footer>
</article>

<style>
  .app { display: flex; flex-direction: column; gap: var(--sw-a3); }
  .app + :global(.app) { margin-top: var(--sw-a3); }
  header { display: flex; align-items: center; gap: var(--sw-a3); flex-wrap: wrap; }
  header h2 { font-size: var(--sw-gr-titel); }
  .art { display: inline-flex; align-items: center; gap: 6px; font-size: var(--sw-gr-klein); color: var(--sw-text-2); }
  .speicherzahl { margin-left: auto; text-align: right; line-height: 1.2; }
  .speicherzahl b { display: block; font-size: var(--sw-gr-titel); font-weight: 600; }
  .speicherzahl span { display: block; font-size: var(--sw-gr-marke); color: var(--sw-text-3); }
  .beschreibung { color: var(--sw-text-2); font-size: var(--sw-gr-klein); }
  .teile { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--sw-a2); }
  .teile li { background: var(--sw-karte-2); border-radius: var(--sw-ecke); padding: var(--sw-a2) var(--sw-a3); }
  .teil { display: flex; align-items: center; gap: var(--sw-a2) var(--sw-a4); flex-wrap: wrap; font-size: var(--sw-gr-klein); }
  .teil .rechts { margin-left: auto; display: inline-flex; align-items: center; gap: var(--sw-a3); }
  .teile .hinweis { margin-top: var(--sw-a2); }
  .arbeitet { color: var(--sw-akzent-schrift); }
  footer { display: flex; align-items: center; gap: var(--sw-a2) var(--sw-a3); flex-wrap: wrap; }
  .datei { margin-left: auto; font-family: var(--sw-schrift-code); font-size: var(--sw-gr-marke); color: var(--sw-text-3); overflow-wrap: anywhere; }
</style>
