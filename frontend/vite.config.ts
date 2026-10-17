import { readFileSync } from 'node:fs';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

// Entwicklung: Oberfläche auf 5550, Schnittstelle vom laufenden Stellwerk auf 8550.
// Gebaut wird direkt ins Python-Paket, das die Oberfläche selbst ausliefert.
const dienst = process.env.STELLWERK ?? 'http://127.0.0.1:8550';

// Fassung der gebauten Oberfläche aus der einzigen Quelle; weicht die des Dienstes ab, lädt die Oberfläche neu (lib/fassung.svelte.ts)
const FASSUNG = (JSON.parse(readFileSync(new URL('../version.json', import.meta.url), 'utf-8')) as { version: string }).version;

export default defineConfig({
  plugins: [svelte()],
  define: { __FASSUNG__: JSON.stringify(FASSUNG) },
  server: {
    port: 5550,
    strictPort: true,
    proxy: { '/api': { target: dienst, headers: { host: '127.0.0.1:8550' } } },
  },
  build: { outDir: '../stellwerk/oberflaeche', emptyOutDir: true, chunkSizeWarningLimit: 900 },
});
