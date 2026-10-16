<script lang="ts">
  // Kleiner Schalter für eine Webapp: an startet alle Teile, aus hält sie an (mit Rückfrage in der Zeile, ohne Browser-Dialog)
  import { api } from '../lib/api';
  import { meldungen } from '../lib/meldung.svelte';
  import { lage } from '../lib/stand.svelte';
  import type { AppAnsicht } from '../lib/typen.gen';
  import { istAn } from '../lib/wort';

  let { app: a }: { app: AppAnsicht } = $props();
  let arbeitet = $state(false);
  let fragen = $state(false);
  const an = $derived(istAn(a.zustand));

  async function schalten() {
    fragen = false;
    arbeitet = true;
    try {
      const e = await api.app(a.kennung, an ? 'anhalten' : 'starten');
      meldungen.zeigen(`${a.name}: ${e.meldung}`, e.erfolg ? 'erfolg' : 'fehler');
    } catch (f) {
      meldungen.fehler(f);
    } finally {
      arbeitet = false;
      await lage.jetzt();
    }
  }
</script>

{#if fragen}
  <span class="frage"><span>{a.name} anhalten?</span>
    <button class="knopf klein ohne" onclick={() => (fragen = false)}>Nein</button>
    <button class="knopf klein gefahr-voll" onclick={schalten}>Ja</button></span>
{:else if arbeitet}
  <i class="fa-solid fa-circle-notch fa-spin warten" title="Wird geschaltet"></i>
{:else}
  <button class="schalter" class:an onclick={() => (an ? (fragen = true) : schalten())} aria-label="{a.name} {an ? 'anhalten' : 'starten'}"
          title={an ? 'Alle Teile anhalten' : 'Alle Teile starten, wer gebraucht wird zuerst'}></button>
{/if}

<style>
  .frage { display: inline-flex; align-items: center; gap: var(--sw-a2); font-size: var(--sw-gr-klein); }
  .warten { width: 46px; text-align: center; color: var(--sw-text-3); }
</style>
