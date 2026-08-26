#!/usr/bin/env python3
"""Recale le numéro de version des feuilles et des scripts sur leur CONTENU.

LE PROBLÈME QU'IL RÈGLE, ET IL A COÛTÉ CHER. Les 30 pages du dépôt chargent
`style.css?v=…` et `main.js?v=…`. Ce paramètre est là pour forcer le navigateur
à retélécharger le fichier quand il change. Il était écrit à la main, donc il
n'était pas mis à jour : le 2026-08-25, après une dizaine de modifications de
`main.js` dans la journée, le numéro datait encore de la veille au soir. Chez le
client le navigateur servait donc l'ANCIEN script depuis son cache, et le film de
l'accueil ne démarrait pas parce que le code en cache cherchait une affiche
cliquable qui n'existe plus dans le HTML. Un défaut invisible en local, où le
serveur de développement ne met rien en cache, et invisible dans un navigateur
piloté, qui part d'un profil vierge à chaque essai.

CE QUE FAIT CE SCRIPT. Il remplace le `?v=` par les huit premiers caractères de
l'empreinte SHA-256 du fichier. Une empreinte de contenu change exactement quand
le fichier change, et jamais autrement : il n'y a plus rien à se rappeler, et
aucun moyen d'oublier. C'est aussi ce qui évite l'inverse, un numéro incrémenté
pour rien, qui ferait retélécharger 200 Ko de CSS sans raison.

À LANCER APRÈS TOUTE MODIFICATION D'UN FICHIER CSS OU JS, avant de commiter :

    python3 tools/bump-assets.py

Il n'écrit que si l'empreinte a changé, et il dit ce qu'il a fait.
"""

import glob
import hashlib
import io
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Les fichiers versionnés, et le motif qui les cherche dans les pages. Le chemin
# peut être précédé de « ../ » ou « ../../ » selon la profondeur de la page.
SUIVIS = ['assets/css/style.css', 'assets/css/scrolly.css',
          'assets/js/main.js', 'assets/js/scrolly.js',
          # LES IMAGES RÉÉCRITES EN PLACE SONT LE MÊME PIÈGE. Une image dont le
          # contenu change sous un nom de fichier inchangé reste servie depuis le
          # cache : le 2026-08-25, la maquette d'interface corrigée n'arrivait pas
          # chez le client pour cette raison. Une image dont le NOM change (les
          # photos ajoutées ce jour-là) n'a pas besoin d'être ici.
          # `qbot-og.jpg` en particulier : versionner son URL est aussi le moyen de
          # forcer les réseaux sociaux à relire l'aperçu.
          'assets/img/qbot-interface.jpg', 'assets/img/qbot-interface-en.jpg',
          'assets/img/qbot-og.jpg', 'assets/img/qbot-film-poster.jpg']


def empreinte(chemin):
    with io.open(os.path.join(RACINE, chemin), 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def pages():
    motifs = ['*.html', 'blog/*.html', 'en/*.html', 'en/blog/*.html',
              '*/index.html', 'en/*/index.html']
    vus = set()
    for m in motifs:
        for f in glob.glob(os.path.join(RACINE, m)):
            # les pages de redirection ne chargent ni feuille ni script
            s = io.open(f, encoding='utf-8').read(1200)
            if '<meta http-equiv="refresh"' in s:
                continue
            vus.add(f)
    return sorted(vus)


def main():
    versions = {c: empreinte(c) for c in SUIVIS}
    for c, v in versions.items():
        print(f"  {c:<28} → v={v}")

    touchees = 0
    for f in pages():
        s = io.open(f, encoding='utf-8').read()
        o = s
        for c, v in versions.items():
            nom = os.path.basename(c)
            # on remplace le paramètre quel qu'il soit, ou on l'ajoute s'il manque
            s = re.sub(r'(' + re.escape(nom) + r')\?v=[^"\']*', r'\1?v=' + v, s)
            s = re.sub(r'(' + re.escape(nom) + r')(["\'])', r'\1?v=' + v + r'\2', s)
        if s != o:
            io.open(f, 'w', encoding='utf-8').write(s)
            touchees += 1
    print(f"\n{touchees} page(s) mise(s) à jour sur {len(pages())}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
