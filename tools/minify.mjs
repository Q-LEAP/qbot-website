#!/usr/bin/env node
/* Produit les versions minifiées des feuilles de style et des scripts.

     node tools/minify.mjs        (appelé automatiquement par bump-assets.mjs)

   POURQUOI CETTE ÉTAPE EXISTE. Les sources de ce dépôt sont commentées à
   outrance, et c'est une valeur : c'est cette documentation en place qui a
   permis de retrouver la plupart des pièges d'une session à l'autre. Mais elle
   pèse. `style.css` fait 376 Ko dont plus de la moitié de commentaires, et
   c'est une feuille QUI BLOQUE LE RENDU : mesuré à l'outil de Google, 2 551 ms
   de blocage à elle seule.
   Les sources gardent donc tout, et le visiteur reçoit la version réduite.

   LES FICHIERS PRODUITS SONT COMMITÉS, parce que GitHub Pages sert le dépôt tel
   quel : il n'y a pas de construction côté serveur. C'est la raison pour
   laquelle ils ne peuvent pas être dans `.gitignore`.

   ILS NE SE MODIFIENT JAMAIS À LA MAIN. Toute édition part à la prochaine
   exécution ; la source est l'original commenté. Un en-tête le rappelle dans
   chaque fichier produit.

   esbuild est appelé par `npx`, comme `gltf-transform` pour le modèle 3D : pas
   d'installation, pas de `package.json`, rien à maintenir.
*/
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, existsSync, statSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const RACINE = join(dirname(fileURLToPath(import.meta.url)), '..');

export const FICHIERS = [
  ['assets/css/style.css',   'assets/css/style.min.css'],
  ['assets/css/scrolly.css', 'assets/css/scrolly.min.css'],
  ['assets/js/main.js',      'assets/js/main.min.js'],
  ['assets/js/scrolly.js',   'assets/js/scrolly.min.js'],
];

const ENTETE = {
  css: s => `/* Généré par tools/minify.mjs depuis ${s} — NE PAS MODIFIER À LA MAIN. */\n`,
  js:  s => `/* Généré par tools/minify.mjs depuis ${s} — NE PAS MODIFIER À LA MAIN. */\n`,
};

export function perimes() {
  /* Un produit plus vieux que sa source est un site qui sert l'ancienne
     feuille : le jumeau Python s'en sert pour refuser de versionner. */
  return FICHIERS.filter(([src, out]) => {
    const a = join(RACINE, src), b = join(RACINE, out);
    return !existsSync(b) || statSync(b).mtimeMs < statSync(a).mtimeMs;
  }).map(([src]) => src);
}

export function minifier() {
  const faits = [];
  for (const [src, out] of FICHIERS) {
    const abs = join(RACINE, src);
    const ext = src.endsWith('.css') ? 'css' : 'js';
    /* PAS DE `--bundle` : on réduit, on ne regroupe pas. Un `import()` dynamique
       reste donc une expression et n'est pas résolu — indispensable, `scrolly.js`
       important la visionneuse 3D par une URL calculée à l'exécution. Le langage
       est déduit de l'extension du fichier, `--loader` ne valant que pour
       l'entrée standard. */
    const min = execFileSync('npx', ['--yes', 'esbuild@0.24', abs, '--minify',
                                     '--charset=utf8', '--legal-comments=none'],
                             { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
    const avant = readFileSync(abs, 'utf8').length;
    writeFileSync(join(RACINE, out), ENTETE[ext](src.split('/').pop()) + min);
    faits.push([out, avant, min.length]);
  }
  return faits;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  for (const [out, a, b] of minifier()) {
    console.log(`${out.padEnd(30)} ${String(Math.round(a / 1024)).padStart(5)} Ko -> ${String(Math.round(b / 1024)).padStart(4)} Ko`);
  }
}
