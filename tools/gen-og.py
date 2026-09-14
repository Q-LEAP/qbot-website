#!/usr/bin/env python3
"""L'aperçu de partage : le mot-symbole Q-Bot sur fond noir.

    python3 tools/gen-og.py
    node tools/bump-assets.mjs      # le fichier est réécrit sous le même nom

POURQUOI LE LOGO ET PLUS LA PHOTO. Demandé par le client le 2026-09-14 : l'aperçu
servait une découpe de la photo du poste de travail, et dans un fil Teams on y
voyait un bout d'écran et un pied de moniteur, pas Q-Bot. Un aperçu de lien est
une carte de marque, pas une illustration.

LA CONTRAINTE QUI DÉCIDE DE TOUT EST LE RECADRAGE CARRÉ. L'image est servie en
1200 x 630 (le format Open Graph, et les `og:image:width/height` des 18 pages le
déclarent), mais Teams et WhatsApp n'en montrent que le CARRÉ CENTRAL. Un logo
posé large en tirerait ses extrémités hors du cadre. Tout ce qui compte tient
donc dans les 630 px du milieu, et l'aperçu fonctionne aussi bien en 1,91:1
(LinkedIn, Slack) qu'en carré.

LA LARGEUR DU MOT-SYMBOLE EST CALCULÉE, PAS CHOISIE. La charte impose une zone
d'exclusion de 0,618 x la hauteur du lockup sur les quatre côtés. Le mot-symbole
a un rapport de 4,025 ; pour que la marque ET sa zone d'exclusion tiennent dans
le carré central : 4,025 h + 2 x 0,618 h <= 630, donc h <= 119,7 et une largeur
maximale de 481,99 px. On pose 480, ce qui laisse un cheveu de marge et reste
un nombre rond. L'assertion plus bas refait le calcul : si le rapport du
mot-symbole change un jour, elle mord.

PAS DE HALO TEAL DERRIÈRE LE LOGO. Une version a été rendue et écartée : les
trois retours du 2026-09-14 vont tous vers moins de lueur et plus de mat, un
halo irait à l'encontre. Fond noir pur, qui est aussi celui du hero.

LE MOT-SYMBOLE VIENT DE LA CHARTE, PAS DU PNG DE LA BARRE DE NAVIGATION.
`logo-qbot-neg.png` ne fait que 300 px de large : l'employer ici demanderait de
l'agrandir 1,6 fois. `Documentations/Q-BOT BrandGuidelines.pdf` est VECTORIEL
(page 2, lockup Négatif de gauche) : rendu à 600 dpi il donne 982 x 244 px
d'encre, largement de quoi. Le tick teal du Q est conservé, c'est le seul élément
coloré de la marque et la charte le garde dans la version Négative.

Le lockup complet « POWERED BY Q-LEAP » n'est PAS repris : le produit s'appelle
Q-Bot depuis le 2026-08-28 et la barre de navigation porte le mot-symbole seul.

APRÈS AVOIR REGÉNÉRÉ, VERSIONNER. Le fichier garde son nom, donc seuls les `?v=`
forcent les réseaux sociaux à relire l'aperçu. C'est le seul moyen.
"""
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
CHARTE = RACINE / 'Documentations' / 'Q-BOT BrandGuidelines.pdf'
CIBLE = RACINE / 'assets' / 'img' / 'qbot-og.jpg'

W, H = 1200, 630
LARGEUR_LOGO = 480          # voir le docstring : le maximum exact est 481,99
QUALITE = 92

# Repères relevés sur la page 2 rendue à 600 dpi : la bande noire, puis la
# fenêtre horizontale du lockup Négatif de gauche. Le découpage final se fait
# par l'encre, pas par ces bornes — elles ne servent qu'à isoler le bon lockup.
PAGE = 1
BANDE_Y = (2482, 3915)
FENETRE_X = (0.30, 0.50)
MOT_Y = (520, 835)          # sous le haut du mot-symbole, avant « POWERED BY »


def mot_symbole() -> Image.Image:
    """Le mot-symbole négatif, détouré à l'encre, en RGBA."""
    page = fitz.open(CHARTE)[PAGE]
    pm = page.get_pixmap(dpi=600)
    a = np.asarray(Image.frombytes('RGB', (pm.width, pm.height), pm.samples), dtype=float)
    x0, x1 = int(FENETRE_X[0] * pm.width), int(FENETRE_X[1] * pm.width)
    bloc = a[BANDE_Y[0] + MOT_Y[0]: BANDE_Y[0] + MOT_Y[1], x0:x1]

    encre = bloc.max(2) > 60
    ys = np.where(encre.any(axis=1))[0]
    xs = np.where(encre.any(axis=0))[0]
    crop = bloc[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]

    # l'encre est peinte SUR du noir : l'alpha est sa luminosité, et la couleur
    # se retrouve en dé-prémultipliant, sans quoi le tick teal virerait au sombre
    alpha = crop.max(2)
    rgb = np.zeros_like(crop)
    vu = alpha > 0
    rgb[vu] = crop[vu] / (alpha[vu][:, None] / 255.0)
    return Image.fromarray(
        np.dstack([rgb.clip(0, 255), alpha.clip(0, 255)]).astype('uint8')).convert('RGBA')


def main() -> None:
    logo = mot_symbole()
    assert logo.width > 900, f'mot-symbole trop petit : {logo.size}'
    teal = np.asarray(logo)[:, :, :3]
    assert ((teal[:, :, 1] > 150) & (teal[:, :, 2] > 140) & (teal[:, :, 0] < 120)).sum() > 1000, \
        'le tick teal du Q a disparu du découpage'

    h = round(LARGEUR_LOGO * logo.height / logo.width)
    assert LARGEUR_LOGO + 2 * 0.618 * h <= H, 'la zone d\'exclusion ne tient pas dans le carré central'

    carte = Image.new('RGB', (W, H), (0, 0, 0))
    l = logo.resize((LARGEUR_LOGO, h), Image.LANCZOS)
    carte.paste(l, ((W - LARGEUR_LOGO) // 2, (H - h) // 2), l)

    avant = CIBLE.stat().st_size if CIBLE.exists() else 0
    carte.save(CIBLE, 'JPEG', quality=QUALITE, optimize=True)
    print(f'{CIBLE.name}  {W}x{H}  logo {LARGEUR_LOGO}x{h}  '
          f'{avant // 1024} Ko -> {CIBLE.stat().st_size // 1024} Ko')


if __name__ == '__main__':
    main()
