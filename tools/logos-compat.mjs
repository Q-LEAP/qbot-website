#!/usr/bin/env node
/**
 * Pose les logos de marque dans les grilles de compatibilité des six pages.
 *
 * POURQUOI UN SCRIPT ET PAS SIX ÉDITIONS À LA MAIN. La même grille vit sur
 * l'accueil, la fiche technique et la page Démo, dans les deux langues. Elles
 * avaient déjà divergé une fois (relevé le 2026-09-08 : trois listes d'outils
 * différentes sur le site français). Un générateur rend la divergence
 * impossible, et l'ajout d'une marque manquante coûte une ligne de la table
 * ci-dessous plus une relance.
 *
 * LES LOGOS SONT EN MONOCHROME, dans l'encre de la case, à la taille d'une
 * icône. Décision du client du 2026-09-08 : c'est le langage des pictogrammes
 * du site, et quinze logos en couleurs sur fond noir changeraient l'allure de
 * la section. Réserve à connaître : certaines chartes de marque interdisent de
 * recolorer un logo, l'accord obtenu par le client couvre cet usage.
 *
 * L'EMPLACEMENT EST RÉSERVÉ SUR TOUTES LES CASES, même sans marque : c'est ce
 * qui aligne les noms et ce qui fait que l'arrivée des marques manquantes ne
 * déplacera rien.
 *
 * SOURCE DES FICHIERS : `tools/logos/<slug>.svg`, un fichier par marque, un
 * seul `<path>` en `viewBox` 24×24 et sans couleur écrite, donc héritant de
 * `currentColor`. Le dossier `tools/` n'est pas publié (cf. `_config.yml`) :
 * seul le tracé est recopié dans le HTML, il n'y a aucune requête de plus.
 *
 * POUR AJOUTER UNE MARQUE MANQUANTE : déposer son SVG dans `tools/logos/`,
 * renseigner son slug dans MARQUES ci-dessous, relancer. Le script vérifie que
 * le fichier existe et refuse de tourner s'il manque.
 *
 * USAGE
 *     node tools/logos-compat.mjs            # simulation
 *     node tools/logos-compat.mjs --ecrire
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RACINE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const LOGOS = path.join(RACINE, 'tools', 'logos');

/* Nom affiché dans la case  ->  slug du fichier, ou null si la marque n'a pas
   encore été fournie. Les deux entrées « porte ouverte » ne sont pas des
   marques : elles n'auront jamais de logo, et c'est voulu. */
const MARQUES = {
  // applications d'authentification
  'LuxTrust Mobile': null,          // à fournir
  'itsme': null,                    // à fournir
  'Microsoft Authenticator': null,  // à fournir, Microsoft ne diffuse ses marques que par son centre de marque
  'Google Authenticator': 'googleauthenticator',
  'Toute app 2FA Android': null,    // pas une marque
  'Any Android 2FA app': null,      // pas une marque
  // outils de test
  'Selenium': 'selenium',
  'Cypress': 'cypress',
  'Appium': 'appium',
  'Playwright': 'playwright',
  'Robot Framework': 'robotframework',
  'Katalon': null,                  // à fournir
  'TestComplete': null,             // à fournir
  'Jenkins CI': 'jenkins',
  'GitLab CI': 'gitlab',
  'API REST': null,                 // pas une marque
  'REST API': null,                 // pas une marque
};

const PAGES = [
  'index.html', 'caracteristiques.html', 'commandez.html',
  'en/index.html', 'en/technical-specs.html', 'en/order.html',
];

/* On extrait le seul `d` du fichier. Un SVG à plusieurs formes ne passerait pas
   ce contrôle, et c'est voulu : le rendu monochrome suppose un tracé unique. */
function trace(slug) {
  const f = path.join(LOGOS, slug + '.svg');
  if (!fs.existsSync(f)) throw new Error('logo absent : ' + f);
  const s = fs.readFileSync(f, 'utf8');
  const paths = [...s.matchAll(/<path[^>]*\sd="([^"]+)"/g)].map((m) => m[1]);
  if (paths.length !== 1) throw new Error(slug + ' : ' + paths.length + ' tracés, un seul attendu');
  if (!/viewBox="0 0 24 24"/.test(s)) throw new Error(slug + " : viewBox inattendu");
  if (/fill="(?!none)/.test(s)) throw new Error(slug + ' : couleur écrite en dur, elle empêcherait currentColor');
  return paths[0];
}

const TRACES = {};
for (const [nom, slug] of Object.entries(MARQUES)) {
  if (slug) TRACES[nom] = trace(slug);
}

function emplacement(nom) {
  const d = TRACES[nom];
  return d
    ? '<span class="compat__logo" aria-hidden="true"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="'
      + d + '"/></svg></span>'
    : '<span class="compat__logo" aria-hidden="true"></span>';
}

const ecrire = process.argv.includes('--ecrire');
let total = 0, inconnues = new Set();

for (const f of PAGES) {
  const p = path.join(RACINE, f);
  let s = fs.readFileSync(p, 'utf8');
  let n = 0;

  s = s.replace(
    /(<li class="compat__item[^"]*"[^>]*>)(?:<span class="compat__logo"[\s\S]*?<\/span>)?([\s\S]*?)(<\/li>)/g,
    (tout, ouvre, corps, ferme) => {
      const nom = corps.replace(/<[^>]+>/g, '').trim();
      if (!(nom in MARQUES)) { inconnues.add(nom); return tout; }
      n++;
      return ouvre + emplacement(nom) + corps + ferme;
    },
  );

  if (ecrire) fs.writeFileSync(p, s, 'utf8');
  total += n;
  console.log(`${f} : ${n} case(s) traitée(s)`);
}

if (inconnues.size) {
  console.log('\nNOMS INCONNUS DE LA TABLE (laissés intacts) : ' + [...inconnues].join(', '));
}
const manquantes = Object.entries(MARQUES)
  .filter(([n, s]) => s === null && !/Toute app|Any Android|API REST|REST API/.test(n))
  .map(([n]) => n);
console.log(`\n${total} cases, ${Object.keys(TRACES).length} marques posées.`);
console.log('En attente de fichier : ' + manquantes.join(', '));
if (!ecrire) console.log('\nSimulation. Relancer avec --ecrire.');
