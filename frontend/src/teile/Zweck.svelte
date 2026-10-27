<script lang="ts">
  // Kurzer Zweck neben dem Namen einer Webapp (aus der App-Datei). Fehlt er, steht der Hinweis an seiner Stelle, statt
  // still leer zu bleiben: die Apps sollen sich nie verwechseln lassen.
  let { zweck, datei = null }: { zweck: string | null; datei?: string | null } = $props();
</script>

{#if zweck}
  <span class="zweck">{zweck}</span>
{:else}
  <span class="zweck fehlt" title={datei ? `Feld zweck in ${datei} eintragen, ein Begriff oder wenige Wörter` : undefined}>
    <i class="fa-solid fa-pen-to-square"></i>Zweck fehlt: in der App-Datei eintragen</span>
{/if}

<style>
  .zweck { color: var(--sw-text-2); font-size: var(--sw-gr-text); font-weight: 500; line-height: 1.3; overflow-wrap: anywhere; }
  .fehlt { color: var(--sw-warnung); font-size: var(--sw-gr-klein); font-weight: 600; display: inline-flex; align-items: baseline; gap: var(--sw-a2); }
</style>
