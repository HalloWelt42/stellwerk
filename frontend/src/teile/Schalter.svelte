<script lang="ts">
  // Kleiner Schalter für eine Webapp: an startet alle Teile, aus hält sie an (mit Rückfrage in der Zeile, ohne Browser-Dialog)
  import { schalten } from '../lib/schalten.svelte';
  import type { AppAnsicht } from '../lib/typen.gen';
  import { istAn } from '../lib/wort';

  let { app: a }: { app: AppAnsicht } = $props();
  let fragen = $state(false);
  const an = $derived(istAn(a.zustand));
  const arbeitet = $derived(!!schalten.was(a.kennung));

  async function umlegen() {
    fragen = false;
    await schalten.tun(a.name, an ? 'anhalten' : 'starten', a.kennung);
  }
</script>

{#if fragen}
  <span class="frage"><span>{a.name} anhalten?</span>
    <button class="knopf klein ohne" onclick={() => (fragen = false)}>Nein</button>
    <button class="knopf klein gefahr-voll" onclick={umlegen}>Ja</button></span>
{:else if arbeitet}
  <i class="fa-solid fa-circle-notch fa-spin warten" title="Wird geschaltet"></i>
{:else}
  <button class="schalter" class:an onclick={() => (an ? (fragen = true) : umlegen())} aria-label="{a.name} {an ? 'anhalten' : 'starten'}"
          title={an ? 'Alle Teile anhalten' : 'Alle Teile starten, wer gebraucht wird zuerst'}></button>
{/if}

<style>
  .frage { display: inline-flex; align-items: center; gap: var(--sw-a2); font-size: var(--sw-gr-klein); flex-wrap: wrap; }
  .warten { width: 50px; text-align: center; color: var(--sw-text-3); }
</style>
