#!/usr/bin/env python3
"""Capture les vignettes des guides depuis tools/render/guide-thumbs.html.

    python3 tools/render/shoot-guide-thumbs.py

Une capture par bloc et par langue, en 900 x 900, à densité 2 puis réduite : le
texte est ainsi net sans que le fichier pèse le prix d'une image de 1536 px.

DENSITÉ 2 PUIS RÉDUCTION, ET PAS UNE CAPTURE DIRECTE EN 768. Une capture à densité 1
rend le texte crénelé sur les diagonales des pictogrammes ; à densité 2 puis réduite
en Lanczos, les bords sont propres. C'est le même raisonnement que pour les rendus 3D
du dépôt, et le dé-débordement n'a pas d'objet ici puisqu'il n'y a pas de fond à
détourer.
"""
import io
import os
from PIL import Image
from playwright.sync_api import sync_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE = 'file://' + os.path.join(RACINE, 'tools/render/guide-thumbs.html')
SORTIE = os.path.join(RACINE, 'assets/img/guides')

# (identifiant du bloc, nom de fichier sans langue)
BLOCS = [
    ('t-pilier', 'familles-2fa'),
    ('t-desactiver', 'trois-voies'),
    ('t-sanscle', 'avec-sans-cle'),
    ('t-securite', 'rien-ne-sort'),
    ('t-nuit', 'campagne-bute'),
    ('t-cout', 'le-calcul'),
]

os.makedirs(SORTIE, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 900, 'height': 900}, device_scale_factor=2)
    pg.goto(PAGE, wait_until='load')
    pg.wait_for_timeout(600)          # la police doit être posée avant la capture
    for langue in ('fr', 'en'):
        pg.evaluate("(l)=>{document.documentElement.className=l}", langue)
        pg.wait_for_timeout(250)
        for ident, nom in BLOCS:
            tmp = os.path.join(SORTIE, '_tmp.png')
            pg.query_selector('#' + ident).screenshot(path=tmp)
            im = Image.open(tmp).convert('RGB')
            assert im.size == (1536, 1536), (ident, im.size)
            # 900 PX, ET LA PREMIÈRE RÉFÉRENCE ÉTAIT FAUSSE. J'avais dimensionné sur
            # 398 px en croyant le conteneur plafonné à 1180 : il vaut
            # `clamp(1180px, 72vw, 1440px)`, donc 1440 à partir de 2000 px de large, et
            # la carte de blog monte alors à 441 px. À densité 2 il faut donc 882 px.
            # 900 couvre le cas, avec la marge. LEÇON : on MESURE la carte, on ne déduit
            # pas sa largeur d'une note sur le conteneur.
            im = im.resize((900, 900), Image.LANCZOS)
            chemin = os.path.join(SORTIE, '%s-%s.webp' % (nom, langue))
            im.save(chemin, 'WEBP', quality=90, method=6)
            print('  %-42s %d Ko' % (os.path.relpath(chemin, RACINE),
                                     os.path.getsize(chemin) // 1024))
            os.remove(tmp)
    b.close()
