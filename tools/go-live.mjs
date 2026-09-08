#!/usr/bin/env node
/**
 * Lève les verrous de pré-lancement, en une fois. Jumeau Node de `go-live.py`.
 *
 * POURQUOI UN JUMEAU. Le poste Windows du client n'a pas de Python utilisable
 * (seuls les alias Microsoft Store répondent), et le jour de la mise en ligne
 * n'est pas le moment de découvrir qu'un script ne démarre pas. Même contrat
 * que la version Python : LES DEUX FICHIERS DOIVENT RESTER D'ACCORD, si l'un
 * change, changer l'autre. C'est le même arrangement que `bump-assets`.
 *
 * USAGE
 *     node tools/go-live.mjs                    # simulation, n'écrit rien
 *     node tools/go-live.mjs --appliquer        # lève les verrous
 *     node tools/go-live.mjs --appliquer --endpoint "https://…"
 *
 * LA SIMULATION EST LE DÉFAUT, à dessein : ce script rend le site public, et
 * cela ne doit pas pouvoir arriver par une faute de frappe.
 *
 * DEUX PIÈGES DE CE DÉPÔT SONT TRAITÉS ICI, et il ne faut pas les défaire :
 *
 *  1. LES FICHIERS SONT EN CRLF (`core.autocrlf true`). Python lisait en mode
 *     texte, donc voyait des `\n` ; Node lit les octets bruts. Tout motif de
 *     fin de ligne s'écrit donc `\r?\n`, et on ne s'ancre JAMAIS en début de
 *     ligne pour supprimer, sous peine de manger le saut de ligne précédent.
 *     C'est exactement ce qui avait décroché `- tools/` de `_config.yml` le
 *     2026-08-28.
 *  2. LE « É » DE « PRÉ-LANCEMENT » PEUT ÊTRE COMPOSÉ OU DÉCOMPOSÉ (NFC/NFD).
 *     Le motif accepte les deux graphies. Cinquième variante du piège « on ne
 *     retape pas une chaîne, on l'extrait », après le cadratin en entité,
 *     l'apostrophe typographique, l'espace insécable et le NFD de « marché ».
 *
 * CE QU'IL NE FAIT PAS, ET QUI RESTE MANUEL : le DNS, HTTPS, la Search Console
 * et la suppression du WordPress. Il les rappelle en fin d'exécution.
 *
 * LES PAGES DE REDIRECTION N'ONT PAS DE BALISE noindex et n'en veulent pas :
 * leur seul rôle est de transmettre un signal. Elles sont donc ignorées ici.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const RACINE = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

// Pages que le jour J ne doit JAMAIS sortir de l'index :
//  - « 404.html », une page d'erreur ne s'indexe pas.
// Ces fichiers portent la marque « PRÉ-LANCEMENT » comme les autres, parce
// qu'ils ont été écrits avec le même gabarit. C'est cette liste qui tranche,
// pas la marque.
const JAMAIS = ['404.html'];

// Dossiers qui ne sont pas le site. Ils sont déjà hors publication via
// `_config.yml`, mais un `*/index.html` les balaierait quand même.
const HORS_SITE = new Set(['Documentations', 'tools', 'website 3', 'Screen modèle 3D',
                           'node_modules', '.git', 'assets']);

// La balise est cherchée par MOTIF et non par chaîne littérale : une variante
// « noindex,nofollow » sans espace se raterait en silence.
const META = /[ \t]*<meta name="robots" content="noindex[^"]*">\r?\n/g;

// Le commentaire est ancré sur « LANCEMENT », pas sur un `<!--` suivi d'un
// `.*?` non borné : c'est ce dernier motif qui avait emporté 239 lignes des
// deux accueils le 2026-08-26.
// Les deux graphies du « E accent aigu » : composee (U+00C9) et decomposee
// (E + U+0301). Visuellement identiques, distinctes a l octet. Ecrites en
// echappements pour que ce fichier soit lui-meme insensible a sa propre
// normalisation.
const COMMENTAIRE = /[ \t]*<!--\s*PR(?:\u00C9|E\u0301)-LANCEMENT[\s\S]*?-->\r?\n/g;

// La note posée à côté des formulaires sans endpoint. Elle ne porte PAS la
// marque « PRÉ-LANCEMENT » à dessein : elle ne doit pas disparaître avec les
// verrous d'indexation, qui se lèvent peut-être avant que la décision arrive.
const NOTE_ENDPOINT = /[ \t]*<!--\s*ROSOAI-EN-ATTENTE · (?:endpoint des formulaires|form endpoint)[\s\S]*?-->\r?\n/g;

const ROBOTS_OUVERT = [
  '# https://q-bot.eu/robots.txt',
  '',
  'User-agent: *',
  'Allow: /',
  '',
  '# ══════════════════════════════════════════════════════════════════════════',
  "# MOTEURS DE RÉPONSE IA : AUTORISÉS, ET C'EST UNE DÉCISION.",
  '# Le WordPress qui précède ce site les bloquait TOUS (Amazonbot, anthropic-ai,',
  '# Applebot-Extended, Bytespider, CCBot, ClaudeBot, FacebookBot,',
  '# Google-Extended, GPTBot, meta-externalagent, omgili, PerplexityBot…).',
  '# Les ouvrir est la condition sine qua non pour être cité par un assistant :',
  '# llms.txt, les réponses-capsules et les données structurées de ce site ne',
  '# servent à rien si les robots qui les lisent sont refoulés à l\'entrée.',
  '# En contrepartie, le contenu devient lisible par ces modèles.',
  '# ══════════════════════════════════════════════════════════════════════════',
  '',
  'User-agent: GPTBot',
  'Allow: /',
  '',
  'User-agent: ChatGPT-User',
  'Allow: /',
  '',
  'User-agent: OAI-SearchBot',
  'Allow: /',
  '',
  'User-agent: ClaudeBot',
  'Allow: /',
  '',
  'User-agent: Claude-User',
  'Allow: /',
  '',
  'User-agent: anthropic-ai',
  'Allow: /',
  '',
  'User-agent: PerplexityBot',
  'Allow: /',
  '',
  'User-agent: Perplexity-User',
  'Allow: /',
  '',
  'User-agent: Google-Extended',
  'Allow: /',
  '',
  'User-agent: Applebot-Extended',
  'Allow: /',
  '',
  'Sitemap: https://q-bot.eu/sitemap.xml',
  '',
].join('\r\n');

/** Les pages du site : racine, en/, et les index.html d'un niveau. */
function pages() {
  const vues = new Set();
  const ajoute = (p) => { if (fs.existsSync(p)) vues.add(p); };

  for (const f of fs.readdirSync(RACINE, { withFileTypes: true })) {
    if (f.isFile() && f.name.endsWith('.html')) ajoute(path.join(RACINE, f.name));
    if (f.isDirectory() && !HORS_SITE.has(f.name)) {
      ajoute(path.join(RACINE, f.name, 'index.html'));
      if (f.name === 'en') {
        for (const g of fs.readdirSync(path.join(RACINE, 'en'), { withFileTypes: true })) {
          if (g.isFile() && g.name.endsWith('.html')) ajoute(path.join(RACINE, 'en', g.name));
          if (g.isDirectory()) ajoute(path.join(RACINE, 'en', g.name, 'index.html'));
        }
      }
    }
  }
  return [...vues].sort();
}

/** Les deux nombres du rappel de fin se DÉRIVENT de leur source. Écrits à la
 *  main, ils avaient vieilli et annonçaient « 34 redirections » là où il y en
 *  a plus de cinquante : le pire endroit pour un chiffre faux, puisqu'il se lit
 *  le jour de la bascule. */
function compte(fichier, motif) {
  try {
    return (fs.readFileSync(path.join(RACINE, fichier), 'utf8').match(motif) || []).length;
  } catch { return 0; }
}

function compteFormulaires(motif) {
  let n = 0;
  for (const p of pages()) n += (fs.readFileSync(p, 'utf8').split(motif).length - 1);
  return n;
}

function main() {
  const argv = process.argv.slice(2);
  const ecrit = argv.includes('--appliquer');
  const iEnd = argv.indexOf('--endpoint');
  const endpoint = iEnd !== -1 ? argv[iEnd + 1] : null;

  console.log(`── Levée des verrous de pré-lancement — ${ecrit ? 'APPLICATION' : "SIMULATION (rien n'est écrit)"}\n`);

  let nMeta = 0, nForm = 0, nNote = 0;
  const touches = [];

  for (const f of pages()) {
    const rel = path.relative(RACINE, f).split(path.sep).join('/');
    if (JAMAIS.includes(rel)) {
      console.log(`  ${rel} : laissé hors index à dessein (hors du site public)`);
      continue;
    }
    const o = fs.readFileSync(f, 'utf8');
    let s = o.replace(META, '').replace(COMMENTAIRE, '');
    if (endpoint) {
      const avant = s;
      nForm += (s.split('data-endpoint=""').length - 1);
      s = s.split('data-endpoint=""').join(`data-endpoint="${endpoint}"`);
      const apres = s.replace(NOTE_ENDPOINT, '');
      if (apres !== s) nNote += 1;
      s = apres;
      void avant;
    }
    if (s !== o) {
      nMeta += 1;
      touches.push(rel);
      if (ecrit) fs.writeFileSync(f, s, 'utf8');
    }
  }

  console.log(`  balise noindex et commentaire PRÉ-LANCEMENT retirés de ${nMeta} fichiers`);
  for (const t of touches) console.log(`      ${t}`);
  if (endpoint) {
    console.log(`  data-endpoint renseigné sur ${nForm} formulaires → ${endpoint}`);
    console.log(`  note ROSOAI-EN-ATTENTE de l'endpoint retirée de ${nNote} fichiers`);
  } else {
    console.log('  aucun endpoint fourni : les formulaires sans endpoint restent sur le repli courrier');
  }

  if (ecrit) fs.writeFileSync(path.join(RACINE, 'robots.txt'), ROBOTS_OUVERT, 'utf8');
  console.log("  robots.txt remplacé par son contenu d'ouverture (exploration autorisée, moteurs IA autorisés)");

  if (ecrit) {
    const restants = pages()
      .map((f) => path.relative(RACINE, f).split(path.sep).join('/'))
      .filter((rel) => !JAMAIS.includes(rel)
        && fs.readFileSync(path.join(RACINE, rel), 'utf8').includes('name="robots" content="noindex'));
    console.log(`\n  contrôle : ${restants.length} page(s) portent encore une balise noindex`
      + (restants.length ? ` → ${restants.join(', ')}` : ' ✓'));
  }

  const nbRedir = compte('tools/redirections_map.py', /^[ \t]*'[^']+'\s*:/gm);
  const nbPages = compte('sitemap.xml', /<loc>/g);
  const nbNewsletter = compteFormulaires('data-endpoint-kind="brevo"');
  const nbContact = compteFormulaires('data-endpoint=""');

  console.log(`
────────────────────────────────────────────────────────────────────────────
CE QUI RESTE À FAIRE À LA MAIN, DANS CET ORDRE
────────────────────────────────────────────────────────────────────────────
 1. Rattacher le domaine q-bot.eu à GitHub Pages, basculer le DNS, activer
    HTTPS. Le site est alors public.
 2. VÉRIFIER LES ${nbRedir} REDIRECTIONS EN LIGNE avant toute chose.
 3. Créer la propriété Search Console et demander l'indexation. Relever le
    nombre de pages indexées : c'est le seul indicateur qui dise si la mise en
    ligne a réussi. Point de départ : 0 sur ${nbPages}.
 4. AVANT DE SUPPRIMER LE WORDPRESS, TRAITER « bot.q-leap.eu », qui répond 301
    vers q-bot.eu et vers lequel pointe la fiche Ministry of Testing. Cette
    redirection est servie par le WordPress et tombera avec lui.
 5. NE SUPPRIMER LE WORDPRESS QU'APRÈS l'étape 2. Les quatre pages légales
    vivent désormais dans ce dépôt, aux mêmes adresses, donc rien ne se perd ;
    mais tant que le WordPress répond encore, on peut comparer.
 6. Rien à faire pour les formulaires. Les ${nbContact} formulaires de contact passent
    par le logiciel de courrier du visiteur, PAR DÉCISION DU CLIENT du
    2026-08-26. Newsletters restantes : ${nbNewsletter}.
────────────────────────────────────────────────────────────────────────────
`);
  if (!ecrit) console.log('Relancer avec --appliquer pour exécuter.');
}

main();
