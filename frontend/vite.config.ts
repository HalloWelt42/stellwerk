import { readFileSync } from 'node:fs';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig, type Plugin } from 'vite';
import { MARKE, TITEL } from './src/lib/marke';

// Entwicklung: Oberfläche auf 5550, Schnittstelle vom laufenden Stellwerk auf 8550.
// Gebaut wird direkt ins Python-Paket, das die Oberfläche selbst ausliefert.
const dienst = process.env.STELLWERK ?? 'http://127.0.0.1:8550';

// Fassung der gebauten Oberfläche aus der einzigen Quelle; weicht die des Dienstes ab, lädt die Oberfläche neu (lib/fassung.svelte.ts)
const FASSUNG = (JSON.parse(readFileSync(new URL('../version.json', import.meta.url), 'utf-8')) as { version: string }).version;

/** Name und Kurzzweck (src/lib/marke.ts) im Titel der Startseite und im Manifest; Farben und Symbole in manifest.json */
function marke(): Plugin {
  const manifest = (): string => JSON.stringify(
    { name: TITEL, short_name: MARKE.name, ...JSON.parse(readFileSync(new URL('./manifest.json', import.meta.url), 'utf-8')) }, null, 2);
  return {
    name: 'stellwerk-marke',
    transformIndexHtml: (html) => html.replace(/<title>[^<]*<\/title>/, `<title>${TITEL}</title>`)
      .replace(/(name="apple-mobile-web-app-title" content=")[^"]*/, `$1${MARKE.name}`),
    configureServer(server) {
      server.middlewares.use('/site.webmanifest', (_anfrage, antwort) => {
        antwort.setHeader('Content-Type', 'application/manifest+json');
        antwort.end(manifest());
      });
    },
    generateBundle() {
      this.emitFile({ type: 'asset', fileName: 'site.webmanifest', source: manifest() });
    },
  };
}

export default defineConfig({
  plugins: [svelte(), marke()],
  define: { __FASSUNG__: JSON.stringify(FASSUNG) },
  server: {
    port: 5550,
    strictPort: true,
    proxy: { '/api': { target: dienst, headers: { host: '127.0.0.1:8550' } } },
  },
  build: { outDir: '../stellwerk/oberflaeche', emptyOutDir: true, chunkSizeWarningLimit: 900 },
});
