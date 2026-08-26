#!/usr/bin/env python3
"""Détoure la photo du premier prototype Q-Bot pour la carte « évolution ».

SOURCE : `assets/img/blog/qbot-photo.webp`, la photo de Mathilde Magne publiée
dans les articles de blog (900 x 900, sans canal alpha). Le client l'a identifiée
le 2026-08-26 comme le PREMIER prototype ; l'image qui occupait cette carte
jusque-là (`qbot-proto-gen1.png`, le portique) est en réalité le SECOND.

CE N'EST PAS UN FOND BLANC, C'EST UN FOND VERT DE STUDIO : (72, 112, 75)
uniforme sur les quatre bords. Une clé de luminance aurait rendu transparent le
texte blanc de l'afficheur ; c'est la TEINTE qui sépare, par la « verdeur »
`G - max(R, B)`. Mesuré sur la source : 37 pour le fond, un 99e centile à 0 pour
l'objet, et un maximum à 25 sur les seuls pixels de bord anticrénelés.

DEUX CONTRÔLES FAITS AVANT D'ÉCRIRE CE SCRIPT, ET QUI ÉVITENT UN REMPLISSAGE PAR
PROXIMITÉ :
  - aucun pixel vert n'est ISOLÉ dans l'objet (les 245 138 pixels de fond sont
    tous atteints depuis le bord), donc un seuil global ne peut pas trouer le
    boîtier ni l'anneau métallique ;
  - rien n'est légitimement vert dans la photo (le bouton est rouge, l'afficheur
    est blanc), donc le dé-débordement peut s'appliquer partout sans risque.

    python3 tools/render/detourer-proto.py
"""

import io
import os
import numpy as np
from PIL import Image

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE = os.path.join(RACINE, 'assets/img/blog/qbot-photo.webp')
SORTIE = os.path.join(RACINE, 'assets/img/qbot-proto-1-boitier.webp')

# Bornes de la rampe d'alpha, en unités de verdeur. En dessous de BAS l'objet est
# opaque, au-dessus de HAUT c'est le fond. Entre les deux, le bord anticrénelé
# reçoit un alpha partiel : sans cette rampe, la découpe est en escalier.
BAS, HAUT = 4, 26
MARGE = 0.03          # 3 % de respiration, convention du dépôt
LONG_COTE = 760       # 2,5x le plus grand cadre mesuré (398 x 299 à 2560 px)


def main():
    src = Image.open(SOURCE).convert('RGB')
    a = np.asarray(src).astype(np.float64)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    vert = G - np.maximum(R, B)

    alpha = np.clip((HAUT - vert) / (HAUT - BAS), 0.0, 1.0)
    # Les alphas quasi nuls ne portent aucune information et donnent au codeur
    # avec perte des pixels dont la couleur dérive librement : ils repassent à 0.
    alpha[alpha < 0.03] = 0.0

    # Dé-débordement : le vert qui bave sur le bord de l'objet. `min(G, max(R,B))`
    # est sans effet partout où le pixel n'est pas verdâtre, donc applicable
    # globalement. Sans lui, le boîtier porte un liseré vert sur une carte sombre.
    G2 = np.minimum(G, np.maximum(R, B))

    # LE VERT DOIT DISPARAÎTRE DU FICHIER, PAS SEULEMENT DEVENIR TRANSPARENT.
    # Le WebP avec perte sous-échantillonne la chrominance : la couleur des pixels
    # TRANSPARENTS bave dans leurs voisins opaques. Symptôme mesuré avant ce
    # correctif : un trait vert d'un pixel de large sur 36 de haut au bord gauche du
    # boîtier, à alpha 240, invisible dans la source et créé par le codeur.
    # On remplit donc les zones transparentes avec la couleur moyenne de l'objet :
    # il n'y a plus de vert à faire baver, et l'alpha rend la zone invisible de
    # toute façon.
    opaque = alpha > 0.5
    moyenne = np.array([R[opaque].mean(), G2[opaque].mean(), B[opaque].mean()])
    for canal, (plan, val) in enumerate(zip((R, G2, B), moyenne)):
        plan[alpha == 0] = val

    rgba = np.dstack([R, G2, B, alpha * 255.0]).round().clip(0, 255).astype(np.uint8)
    im = Image.fromarray(rgba)

    boite = im.getbbox()          # boîte de ce qui n'est pas totalement transparent
    assert boite, 'image entièrement transparente'
    x0, y0, x1, y1 = boite
    mx, my = int((x1 - x0) * MARGE), int((y1 - y0) * MARGE)
    x0, y0 = max(0, x0 - mx), max(0, y0 - my)
    x1, y1 = min(im.width, x1 + mx), min(im.height, y1 + my)
    im = im.crop((x0, y0, x1, y1))

    ech = LONG_COTE / max(im.size)
    if ech < 1:
        im = im.resize((round(im.width * ech), round(im.height * ech)), Image.LANCZOS)

        # LE DÉ-DÉBORDEMENT SE RÉAPPLIQUE APRÈS LA RÉDUCTION, ET C'EST LE POINT
        # LE MOINS ÉVIDENT DE CE SCRIPT. Lanczos « sonne » : sur un bord à fort
        # contraste il dépasse la valeur des voisins, et il recrée donc du vert
        # là où il n'y en avait plus. Mesuré étape par étape sur cette image :
        # verdeur 0 après dé-débordement, 0 après recadrage, puis **255 sur
        # 25 pixels après Lanczos**. Le symptôme visible était un trait vert
        # d'un pixel de large sur 36 de haut au bord gauche du boîtier.
        # Bilinéaire et « box » n'ont pas ce défaut (verdeur 1) mais perdent du
        # piqué : on garde donc Lanczos et on reborne après coup.
        q = np.asarray(im).astype(np.int16)
        q[..., 1] = np.minimum(q[..., 1], np.maximum(q[..., 0], q[..., 2]))
        im = Image.fromarray(q.clip(0, 255).astype(np.uint8))

    im.save(SORTIE, 'WEBP', quality=92, method=6)

    al = np.asarray(im)[..., 3]
    print(f"  écrit {os.path.relpath(SORTIE, RACINE)}")
    print(f"    {im.size[0]} x {im.size[1]}, {os.path.getsize(SORTIE) // 1024} Ko")
    print(f"    opaques {int((al == 255).sum())} | transparents {int((al == 0).sum())} "
          f"| bord dégradé {int(((al > 0) & (al < 255)).sum())}")


if __name__ == '__main__':
    main()
