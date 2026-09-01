#!/usr/bin/env python3
"""Capture le visuel de la section « La solution », dans les deux langues.

    python3 tools/render/shoot-solution-visual.py
    python3 tools/bump-assets.py     # ensuite : le NOM du fichier ne change pas

DENSITÉ 2 PUIS RÉDUCTION LANCZOS, pas une capture directe : à densité 1 les
diagonales des pictogrammes crénellent. Même raisonnement que shoot-guide-thumbs.py
et que la maquette d'interface.

LA TAILLE EST MESURÉE, PAS DÉDUITE — ET LA PREMIÈRE MESURE ÉTAIT FAUSSE. J'avais
relevé 741 px de large à 2560 px : c'était la boîte TRANSFORMÉE, saisie avant que
la révélation ne soit finie (la variante « média » part à `--media-scale + 0.05`).
`getBoundingClientRect()` inclut la transformation ; il faut lire `offsetWidth`, ou
mesurer une fois la révélation terminée. La vraie boîte fait 656 x 492 px, donc
1312 px à densité 2. La planche sort en 1500 x 1125 : 14 % de marge, et aucun
agrandissement à aucune largeur (1,14 au plus serré, 2,19 sur téléphone).
"""
import os
from PIL import Image
from playwright.sync_api import sync_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE = 'file://' + os.path.join(RACINE, 'tools/render/solution-visual.html')
SORTIE = os.path.join(RACINE, 'assets/img')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 900, 'height': 700}, device_scale_factor=2)
    pg.goto(PAGE, wait_until='load')
    pg.wait_for_timeout(700)          # la police doit être posée avant la capture
    for langue, suffixe in (('fr', ''), ('en', '-en')):
        pg.evaluate("(l)=>{document.documentElement.className=l}", langue)
        pg.wait_for_timeout(250)
        tmp = os.path.join(SORTIE, '_tmp.png')
        pg.query_selector('#solution').screenshot(path=tmp)
        im = Image.open(tmp).convert('RGB')
        assert im.size == (1520, 1140), im.size
        im = im.resize((1500, 1125), Image.LANCZOS)
        chemin = os.path.join(SORTIE, 'qbot-2fa-flux%s.jpg' % suffixe)
        im.save(chemin, 'JPEG', quality=88, optimize=True, progressive=True)
        print('  %-40s %d Ko' % (os.path.relpath(chemin, RACINE),
                                 os.path.getsize(chemin) // 1024))
        os.remove(tmp)
    b.close()
