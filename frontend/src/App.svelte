<script lang="ts">
  // Schale wie in Leitstelle und Maschinenraum: Kopf, Seitenleiste mit Menü und Ansicht, Hauptbereich, Fußleiste.
  import { onMount } from 'svelte';
  import { fassungVerfolgen } from './lib/fassung.svelte';
  import { TITEL } from './lib/marke';
  import { lage } from './lib/stand.svelte';
  import { weg } from './lib/weg.svelte';
  import AppDetail from './seiten/AppDetail.svelte';
  import Apps from './seiten/Apps.svelte';
  import Ordner from './seiten/Ordner.svelte';
  import Protokoll from './seiten/Protokoll.svelte';
  import Uebersicht from './seiten/Uebersicht.svelte';
  import Fuss from './teile/Fuss.svelte';
  import Kopf from './teile/Kopf.svelte';
  import NeueFassung from './teile/NeueFassung.svelte';
  import Rueckmeldungen from './teile/Rueckmeldungen.svelte';
  import Seitenleiste from './teile/Seitenleiste.svelte';

  lage.starten();
  // Neue Fassung des Stellwerks: von selbst neu laden, sobald es nichts unterbricht
  onMount(fassungVerfolgen);
  const s = $derived(lage.stand);
  document.title = TITEL;
</script>

<div class="schale">
  <Kopf />
  <Seitenleiste />
  <main class="haupt rahmen" id="haupt">
    <NeueFassung />
    {#if !s}
      <div class="verbinden"><div class="leer"><i class="fa-solid fa-traffic-light"></i>
        <h2>{lage.erreichbar ? 'Lade den Stand' : 'Das Stellwerk antwortet nicht'}</h2>
        <p>{lage.erreichbar ? 'Einen Augenblick.' : 'Läuft es noch? Neuer Versuch alle zwei Sekunden.'}</p></div></div>
    {:else if weg.seite === 'uebersicht'}<Uebersicht stand={s} />
    {:else if weg.seite === 'apps' && weg.rest}<AppDetail stand={s} kennung={weg.rest} />
    {:else if weg.seite === 'apps'}<Apps stand={s} />
    {:else if weg.seite === 'protokoll'}<Protokoll stand={s} />
    {:else if weg.seite === 'ordner'}<Ordner stand={s} />
    {/if}
  </main>
  <Fuss />
</div>
<Rueckmeldungen />
