<script lang="ts">
  // Die Container-Laufzeit: startet von selbst, wenn ein Docker-Teil startet; anhalten nur von Hand und nur, wenn kein
  // Docker-Teil mehr läuft (das prüft das Stellwerk und sagt, welche Webapps noch laufen).
  import { api } from '../lib/api';
  import { gb } from '../lib/format';
  import { meldungen } from '../lib/meldung.svelte';
  import { lage } from '../lib/stand.svelte';
  import type { DockerAnsicht } from '../lib/typen.gen';
  import { ZUSTAND, istAn } from '../lib/wort';
  import Protokoll from './Protokoll.svelte';

  let { docker: d }: { docker: DockerAnsicht } = $props();
  let arbeitet = $state(false);
  let fragen = $state(false);
  let protokollOffen = $state(false);
  const z = $derived(ZUSTAND[d.zustand]);
  const an = $derived(istAn(d.zustand));

  async function schalten() {
    fragen = false;
    arbeitet = true;
    try {
      const e = await api.docker(an ? 'anhalten' : 'starten');
      meldungen.zeigen(`Docker: ${e.meldung}`, e.erfolg ? 'erfolg' : 'fehler');
    } catch (f) {
      meldungen.fehler(f);
    } finally {
      arbeitet = false;
      await lage.jetzt();
    }
  }
</script>

<section class="karte docker">
  <h3><i class="fa-solid fa-box"></i> Docker
    <span class="rechts"><span class="zustand {z.klasse}"><i class="fa-solid {arbeitet ? 'fa-circle-notch fa-spin' : z.symbol}"></i>{arbeitet ? (an ? 'Hält an' : 'Startet') : z.wort}</span></span></h3>
  <p class="leise klein">Laufzeit für {d.apps.join(', ')}. Startet von selbst, wenn eine dieser Webapps startet; angehalten wird sie nur von Hand.
    {#if d.gb_jetzt != null}Belegt <b class="zahl">{gb(d.gb_jetzt)}</b> mit allen Containern.{/if}</p>
  {#if d.meldung}<div class="hinweis klein {d.zustand === 'gestoert' ? 'gefahr' : 'warnung'}"><i class="fa-solid fa-triangle-exclamation"></i><span>{d.meldung}</span></div>{/if}
  {#if fragen}
    <div class="bestaetigen"><i class="fa-solid fa-triangle-exclamation"></i><span>Docker anhalten? Geht nur, wenn keine Docker-Teile mehr laufen.</span>
      <div class="rechts"><button class="knopf klein ohne" onclick={() => (fragen = false)}>Abbrechen</button>
        <button class="knopf klein gefahr-voll" onclick={schalten}>Ja, anhalten</button></div></div>
  {/if}
  <div class="knoepfe">
    {#if an}<button class="knopf klein" disabled={arbeitet} onclick={() => (fragen = true)}><i class="fa-solid fa-stop"></i> Anhalten</button>
    {:else}<button class="knopf klein" disabled={arbeitet} onclick={schalten}><i class="fa-solid fa-play"></i> Starten</button>{/if}
    <button class="knopf klein ohne" class:aktiv={protokollOffen} onclick={() => (protokollOffen = !protokollOffen)}><i class="fa-solid fa-scroll"></i> Protokoll</button>
  </div>
  {#if protokollOffen}<Protokoll ziel={{ art: 'docker' }} zeilen={100} />{/if}
</section>

<style>
  .docker { display: flex; flex-direction: column; gap: var(--sw-a3); }
  .knoepfe { display: flex; gap: var(--sw-a2); flex-wrap: wrap; }
</style>
