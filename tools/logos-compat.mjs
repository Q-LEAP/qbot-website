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
 * SOURCE DES FICHIERS : `tools/logos/<slug>.svg`, un fichier par marque, tel
 * qu'il a été récupéré à sa source officielle. Le script le NORMALISE au
 * moment de la pose (voir plus bas) : le fichier reste donc intact et son
 * origine reste vérifiable. Le dossier `tools/` n'est pas publié (cf.
 * `_config.yml`) et seules les formes sont recopiées dans le HTML, il n'y a
 * aucune requête de plus.
 *
 * POUR AJOUTER UNE MARQUE MANQUANTE : déposer son SVG dans `tools/logos/`,
 * renseigner son slug dans MARQUES ci-dessous, relancer. Le script refuse de
 * tourner si le fichier annoncé manque, s'il n'a pas de `viewBox`, ou s'il
 * contient du texte ou une image matricielle.
 *
 * USAGE
 *     node tools/logos-compat.mjs            # simulation
 *     node tools/logos-compat.mjs --ecrire
 */

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const RACINE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const LOGOS = path.join(RACINE, 'tools', 'logos');

/* Nom affiché dans la case  ->  { slug, hex } , ou null si la marque n'a pas
   encore été fournie. Les deux entrées « porte ouverte » ne sont pas des
   marques : elles n'auront jamais de logo, et c'est voulu.
 *
 * `hex` EST LA COULEUR OFFICIELLE DE LA MARQUE, appliquée au tracé. Elle est
 * nécessaire parce que la collection employée ne livre que du monochrome : le
 * fichier n'a pas de couleur, elle est publiée à côté. Un `hex` à null veut
 * dire « le fichier porte déjà ses vraies couleurs, ne pas y toucher », ce qui
 * est le cas de Katalon, récupéré chez l'éditeur.
 *
 * POURQUOI LES COULEURS ET PLUS LE MONOCHROME : décision du client du
 * 2026-09-08, « si ça nous permet de gagner du temps ». Et c'est le cas : en
 * couleur, une icône d'application matricielle devient utilisable, alors qu'un
 * PNG ne peut pas donner une silhouette monochrome propre. */
const MARQUES = {
  // applications d'authentification
  /* Ces deux-là sont des ICÔNES D'APPLICATION en PNG, récupérées chez l'éditeur
     (icône déclarée dans le <head> d'itsme, favicon 256 px de LuxTrust, extrait
     de son .ico). Elles portent leur propre fond, donc elles REMPLISSENT la
     pastille au lieu d'y flotter : c'est ce que dit `plein`. Elles vivent dans
     `assets/img/brands/` et non dans `tools/logos/`, puisqu'elles sont servies. */
  'LuxTrust Mobile': { image: 'luxtrust.png', plein: true },
  'itsme': { image: 'itsme.png', plein: true },
  /* Microsoft a fait retirer ses marques des collections publiques et ne les
     diffuse que par son centre de marque, mais l'ICÔNE DE L'APPLICATION est
     publiée par l'éditeur lui-même sur les magasins : celle-ci vient de la
     fiche App Store, en 256 px, réduite à 96. C'est exactement la même source
     que ses deux voisines, et c'est la bonne pour une colonne qui liste des
     applications. */
  'Microsoft Authenticator': { image: 'microsoft-authenticator.png', plein: true },
  'Google Authenticator': { slug: 'googleauthenticator', hex: '#4285F4' },
  'Toute app 2FA Android': null,    // pas une marque
  'Any Android 2FA app': null,      // pas une marque
  // outils de test
  'Selenium': { slug: 'selenium', hex: '#43B02A' },
  'Cypress': { slug: 'cypress', hex: '#69D3A7' },
  'Appium': { slug: 'appium', hex: '#EE376D' },
  'Playwright': { slug: 'playwright', hex: '#2EAD33' },
  'Robot Framework': { slug: 'robotframework', hex: '#000000' },
  'Katalon': { slug: 'katalon', hex: null },  // symbole officiel bicolore, katalon.info
  /* TESTCOMPLETE N'A PAS DE SYMBOLE, ET CE N'EST PAS UN OUBLI. Cherché le
     2026-09-08 sur toutes les propriétés de SmartBear : la page produit, le
     portail de documentation et le CDN de marque. Le seul fichier qui existe
     est le LOGOTYPE en lettres, `viewBox` 554 x 108, soit un rapport de 5:1 ;
     réduit à 22 px il est illisible et il redit le nom écrit juste à côté. Un
     logotype n'est pas une icône, c'est le même arbitrage que pour LuxTrust,
     dont l'icône d'application a fini par servir. TestComplete n'étant pas une
     application mobile, il n'y a pas d'icône équivalente à aller chercher. */
  'TestComplete': null,
  'Jenkins CI': { slug: 'jenkins', hex: '#D24939' },
  'GitLab CI': { slug: 'gitlab', hex: '#FC6D26' },
  'API REST': null,                 // pas une marque
  'REST API': null,                 // pas une marque
};

const PAGES = [
  'index.html', 'caracteristiques.html', 'commandez.html',
  'en/index.html', 'en/technical-specs.html', 'en/order.html',
];

/* NORMALISATION D'UN LOGO EN MARQUE MONOCHROME.
 *
 * Les fichiers officiels ne se ressemblent pas : la collection de marques donne
 * un tracé unique en `viewBox` 24×24 sans couleur, un éditeur donne deux formes
 * en 145×145 avec des `fill` en dur, un autre met ses couleurs dans un bloc
 * `<style>` et des classes. On ramène tout au même dénominateur : le `viewBox`
 * d'origine est CONSERVÉ (le forcer déformerait la marque) et toute couleur est
 * retirée pour que `currentColor` s'applique.
 *
 * CE QUI EST REFUSÉ, et c'est volontaire : un logo qui contient du texte ou une
 * image matricielle. Un `<text>` ne se lit pas à 22 px et dépend d'une police
 * absente ; un `<image>` n'est pas vectoriel. Dans les deux cas la marque n'est
 * pas utilisable à cette taille, mieux vaut le dire que le poser quand même.
 */
function marque(slug, hex) {
  const f = path.join(LOGOS, slug + '.svg');
  if (!fs.existsSync(f)) throw new Error('logo absent : ' + f);
  let s = fs.readFileSync(f, 'utf8');

  const vb = (s.match(/viewBox="([^"]+)"/) || [])[1];
  if (!vb) throw new Error(slug + ' : pas de viewBox, la marque ne peut pas être mise à l\'échelle');
  if (/<text\b/i.test(s)) throw new Error(slug + ' : contient du texte, illisible à 22 px');
  if (/<image\b/i.test(s)) throw new Error(slug + ' : contient une image matricielle, non vectoriel');

  // le corps, sans l'enveloppe <svg>, sans les blocs <style> ni <defs>
  let corps = s.replace(/^[\s\S]*?<svg[^>]*>/i, '').replace(/<\/svg>[\s\S]*$/i, '');
  corps = corps.replace(/<defs\b[\s\S]*?<\/defs>/gi, '').replace(/<style\b[\s\S]*?<\/style>/gi, '');
  /* LE <title> DU FICHIER SOURCE EST RETIRÉ, et ce n'est pas cosmétique : il
     porte le nom de la marque, qui est DÉJÀ le texte de la case. Laissé en
     place, il double ce nom dans `textContent` (« SeleniumSelenium »), ce que
     verra toute sonde qui lit le texte rendu, et il fait apparaître une bulle
     d'aide au survol du logo. Un lecteur d'écran ne l'entend pas, l'emplacement
     étant `aria-hidden`, mais ce n'est pas une raison pour le garder. */
  corps = corps.replace(/<title\b[\s\S]*?<\/title>/gi, '');
  corps = corps.replace(/\s(?:class|style|id|data-name)="[^"]*"/gi, '');

  /* DEUX CAS, ET IL NE FAUT PAS LES CONFONDRE.
     - `hex` donné : le fichier vient d'une collection monochrome, il n'a pas de
       couleur, on lui applique la couleur officielle de la marque. On retire au
       passage tout `fill` résiduel, sans quoi il gagnerait sur l'attribut posé
       sur le <svg>.
     - `hex` à null : le fichier porte DÉJÀ ses vraies couleurs, on n'y touche
       pas. Les recolorer serait altérer la marque, ce que la plupart des
       chartes interdisent. */
  if (hex) corps = corps.replace(/\s(?:fill|stroke)="(?!none)[^"]*"/gi, '');
  corps = corps.replace(/\s+/g, ' ').trim();

  const formes = (corps.match(/<(path|circle|rect|polygon|ellipse|polyline)\b/gi) || []).length;
  if (!formes) throw new Error(slug + ' : aucune forme vectorielle trouvée');
  return { vb, corps, formes, hex };
}

const MARQUAGES = {};
for (const [nom, m] of Object.entries(MARQUES)) {
  if (!m) continue;
  if (m.image) {
    const f = path.join(RACINE, 'assets', 'img', 'brands', m.image);
    if (!fs.existsSync(f)) throw new Error('image de marque absente : ' + f);
    const v = crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex').slice(0, 8);
    MARQUAGES[nom] = { image: m.image, plein: !!m.plein, formes: 'png', v };
  } else {
    MARQUAGES[nom] = marque(m.slug, m.hex);
  }
}

/* `prefixe` : les pages de `en/` atteignent les actifs par `../`. On le déduit
   du chemin de la page plutôt que de le déclarer, pour qu'une page ajoutée dans
   un sous-dossier n'ait rien à configurer. */
function emplacement(nom, prefixe) {
  const m = MARQUAGES[nom];
  if (!m) return '<span class="compat__logo" aria-hidden="true"></span>';

  if (m.image) {
    const cls = 'compat__logo' + (m.plein ? ' compat__logo--plein' : '');
    /* PAS DE `loading="lazy"` SUR CES DEUX-LÀ, et c'est un choix mesuré.
       Réduites, elles pèsent 3 et 9 Ko : le report de chargement ne fait rien
       gagner, alors qu'il crée une classe entière de « je ne vois pas les
       logos ». Une image différée n'est chargée ni dans un onglet en
       arrière-plan, ni tant que l'observateur du navigateur ne l'a pas vue
       approcher, et le symptôme est indistinguable d'une image cassée.
       `?v=` : l'empreinte du contenu. Ces fichiers ont déjà été RÉÉCRITS sous
       le même nom (256 px puis 96 px) ; sans version, un visiteur qui a la
       première garderait la première. C'est le défaut du 2026-08-25. */
    return '<span class="' + cls + '" aria-hidden="true"><img src="' + prefixe
      + 'assets/img/brands/' + m.image + '?v=' + m.v + '" alt="" width="28" height="28"'
      + ' decoding="async"></span>';
  }
  const teinte = m.hex ? ' fill="' + m.hex + '"' : '';
  return '<span class="compat__logo" aria-hidden="true"><svg viewBox="' + m.vb
    + '"' + teinte + ' aria-hidden="true">' + m.corps + '</svg></span>';
}

const ecrire = process.argv.includes('--ecrire');
let total = 0, inconnues = new Set();

for (const f of PAGES) {
  const p = path.join(RACINE, f);
  let s = fs.readFileSync(p, 'utf8');
  let n = 0;
  const prefixe = '../'.repeat(f.split('/').length - 1);

  s = s.replace(
    /(<li class="compat__item[^"]*"[^>]*>)(?:<span class="compat__logo[^"]*"[\s\S]*?<\/span>)?([\s\S]*?)(<\/li>)/g,
    (tout, ouvre, corps, ferme) => {
      const nom = corps.replace(/<[^>]+>/g, '').trim();
      if (!(nom in MARQUES)) { inconnues.add(nom); return tout; }
      n++;
      return ouvre + emplacement(nom, prefixe) + corps + ferme;
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
  .filter(([n, m]) => m === null && !/Toute app|Any Android|API REST|REST API/.test(n))
  .map(([n]) => n);
console.log(`\n${total} cases, ${Object.keys(MARQUAGES).length} marques posées `
  + `(${Object.entries(MARQUAGES).map(([n, m]) => n + ' ' + m.formes + 'f').join(', ')}).`);
console.log('En attente de fichier : ' + manquantes.join(', '));
if (!ecrire) console.log('\nSimulation. Relancer avec --ecrire.');
