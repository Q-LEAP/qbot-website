// Recale le numéro de version des feuilles et des scripts sur leur CONTENU.
//
// JUMEAU NODE DE `tools/bump-assets.py`, MÊME COMPORTEMENT. Il existe parce que
// la machine de développement du 2026-08-28 n'a pas de Python : seuls les alias
// Microsoft Store répondent à `python3`, et tout `tools/*.py` y est
// inutilisable. Les deux fichiers doivent rester d'accord ; si l'un change,
// changer l'autre.
//
// LE PROBLÈME QU'IL RÈGLE, ET IL A COÛTÉ CHER. Les pages du dépôt chargent
// `style.css?v=…` et `main.js?v=…`. Ce paramètre force le navigateur à
// retélécharger le fichier quand il change. Écrit à la main, il n'était pas mis
// à jour : le 2026-08-25, après une dizaine de modifications de `main.js` dans
// la journée, le numéro datait encore de la veille au soir. Chez le client le
// navigateur servait donc l'ANCIEN script depuis son cache. Défaut invisible en
// local, où le serveur de développement ne met rien en cache, et invisible dans
// un navigateur piloté, qui part d'un profil vierge à chaque essai.
//
// CE QU'IL FAIT. Il remplace le `?v=` par les huit premiers caractères de
// l'empreinte SHA-256 du fichier. Une empreinte de contenu change exactement
// quand le fichier change, et jamais autrement.
//
// À LANCER APRÈS TOUTE MODIFICATION D'UN CSS OU D'UN JS, avant de commiter :
//
//     node tools/bump-assets.mjs
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const RACINE = path.dirname(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1')));

// Les fichiers versionnés. Le chemin peut être précédé de « ../ » ou « ../../ »
// selon la profondeur de la page ; on ne cherche que le nom de fichier.
//
// LES IMAGES RÉÉCRITES EN PLACE SONT LE MÊME PIÈGE. Une image dont le contenu
// change sous un nom inchangé reste servie depuis le cache. Une image dont le
// NOM change n'a pas besoin d'être ici. `qbot-og.jpg` en particulier :
// versionner son URL est aussi le moyen de forcer les réseaux sociaux à relire
// l'aperçu.
const SUIVIS = [
  'assets/css/style.css', 'assets/css/scrolly.css',
  'assets/js/main.js', 'assets/js/scrolly.js',
  'assets/img/qbot-interface.jpg', 'assets/img/qbot-interface-en.jpg',
  // `qbot-film-poster.jpg` est sorti de la liste le 2026-09-02 : plus aucune
  // page ne le cite depuis que le film de démonstration a remplacé la boucle
  // décorative des accueils.
  'assets/img/qbot-og.jpg',
];

const empreinte = c =>
  crypto.createHash('sha256').update(fs.readFileSync(path.join(RACINE, c))).digest('hex').slice(0, 8);

function pages() {
  const IGNORE = new Set(['.git', 'Documentations', 'tools', 'assets', 'website 3', 'node_modules']);
  const out = [];
  (function marcher(d) {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) {
        if (IGNORE.has(e.name) || e.name.normalize('NFC').startsWith('Screen mod')) continue;
        marcher(p);
      } else if (e.name.startsWith('.')) {
        // « ._page.html » : fork de ressources macOS sur ce volume exFAT, pas une
        // page. Le jumeau Python ne le voit pas (glob ignore les noms cachés) et
        // les deux doivent rester d'accord : sans cette ligne, le décompte des
        // deux scripts diverge dès qu'une page est écrite depuis un Mac.
        continue;
      } else if (e.name.endsWith('.html')) {
        // les pages de redirection ne chargent ni feuille ni script
        if (fs.readFileSync(p, 'utf8').slice(0, 1200).includes('<meta http-equiv="refresh"')) continue;
        out.push(p);
      }
    }
  })(RACINE);
  return out.sort();
}

const versions = Object.fromEntries(SUIVIS.map(c => [c, empreinte(c)]));
for (const [c, v] of Object.entries(versions)) console.log(`  ${c.padEnd(30)} -> v=${v}`);

const liste = pages();
let touchees = 0;
for (const f of liste) {
  const o = fs.readFileSync(f, 'utf8');
  let s = o;
  for (const [c, v] of Object.entries(versions)) {
    const nom = path.basename(c).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    // on remplace le paramètre quel qu'il soit, ou on l'ajoute s'il manque
    s = s.replace(new RegExp(`(${nom})\\?v=[^"']*`, 'g'), `$1?v=${v}`);
    s = s.replace(new RegExp(`(${nom})(["'])`, 'g'), `$1?v=${v}$2`);
  }
  if (s !== o) { fs.writeFileSync(f, s, 'utf8'); touchees++; }
}
console.log(`\n${touchees} page(s) mise(s) à jour sur ${liste.length}`);
