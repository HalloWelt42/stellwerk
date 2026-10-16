<script lang="ts">
  // Wo alles liegt und was eingestellt ist. Geändert wird in den Dateien; neue App-Dateien liest das Stellwerk im
  // nächsten Takt, geänderte Einstellungen nach einem Neustart.
  import type { Stand } from '../lib/typen.gen';

  let { stand: s }: { stand: Stand } = $props();
  const e = $derived(s.einstellungen);
  const pfade = $derived([
    ['Ordner', s.ordner, 'alles an einem Ort'],
    ['Einstellungen', `${s.ordner}/einstellungen.toml`, 'Oberfläche, Messung, Neustartregeln, Docker'],
    ['Webapps', `${s.ordner}/apps/`, 'je Webapp eine Datei mit ihren Teilen; der Dateiname ist die Kennung'],
    ['Protokolle', `${s.ordner}/protokolle/`, 'Ausgabe des Stellwerks und je Teil eine Datei'],
    ['Zustand', `${s.ordner}/zustand.json`, 'Sollzustand je Teil und gemessene Höchstwerte'],
  ]);
</script>

<div class="seiteninhalt seite-ordner">
  <div class="rahmen-kopf">
    <div class="seitenkopf"><h1>Ordner</h1>
      <p class="unterzeile">Neue oder geänderte App-Dateien liest das Stellwerk im nächsten Takt. Geänderte Einstellungen gelten nach einem Neustart des Stellwerks.</p></div>
  </div>
  <div class="rollfeld">
    {#each s.ladefehler as f (f.datei)}
      <div class="hinweis gefahr klein"><i class="fa-solid fa-file-circle-exclamation"></i><span>Datei <b>{f.datei}</b> wird übergangen: {f.meldung}</span></div>
    {/each}
    <div class="spalten-ordner">
      <section class="karte">
        <h3><i class="fa-solid fa-folder-open"></i> Pfade</h3>
        <dl class="angaben">{#each pfade as [name, pfad, satz] (name)}<dt>{name}</dt><dd><span class="code">{pfad}</span><small>{satz}</small></dd>{/each}</dl>
      </section>
      <section class="karte">
        <h3><i class="fa-solid fa-sliders"></i> Einstellungen</h3>
        <dl class="angaben">
          <dt>Name</dt><dd>{e.name ?? s.rechner}</dd>
          <dt>Oberfläche</dt><dd class="zahl">{e.oberflaeche.adresse}:{e.oberflaeche.port}</dd>
          <dt>Messtakt</dt><dd><span class="zahl">{e.messung.takt_s}</span> s</dd>
          <dt>Neustart nach Absturz</dt><dd>Pausen <span class="zahl">{e.neustart.pausen_s.join(', ')}</span> s, höchstens <span class="zahl">{e.neustart.im_fenster}</span> in <span class="zahl">{e.neustart.fenster_s}</span> s</dd>
          <dt>Docker starten</dt><dd class="code">{e.docker.befehl.join(' ')}</dd>
          <dt>Docker anhalten</dt><dd class="code">{e.docker.anhaltebefehl.join(' ')}</dd>
        </dl>
      </section>
    </div>
  </div>
</div>

<style>
  .spalten-ordner { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr)); gap: var(--sw-a4); align-items: start; }
  .spalten-ordner :global(.karte) { margin: 0; }
  .angaben { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: var(--sw-a3) var(--sw-a4); margin: 0; font-size: var(--sw-gr-klein); }
  .angaben dt { color: var(--sw-text-3); }
  .angaben dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
  .angaben small { display: block; color: var(--sw-text-3); font-size: var(--sw-gr-marke); margin-top: 2px; }
</style>
