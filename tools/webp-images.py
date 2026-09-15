#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les visuels lourds des accueils en WebP, et le hero en deux largeurs.

    python3 tools/webp-images.py

POURQUOI. Mesuré à l'outil de Google le 2026-09-15 : `qbot-photo-poste.jpg`
est l'élément du plus grand rendu de la page d'accueil, il pèse 94 Ko en
1400 px, et il s'affiche sur 342 px de large sur un téléphone. Deux gaspillages
d'un coup, le format et la taille, pour l'image qui décide du score.

LE JPEG D'ORIGINE RESTE, il n'est pas remplacé : c'est lui la source, et le
dépôt ne réencode jamais un encodage. Les WebP sont des PRODUITS, régénérables.

LA QUALITÉ EST MESURÉE, PAS CHOISIE : l'écart moyen avec la source est imprimé à
chaque exécution. Le dépôt a déjà accepté 1,05/255 pour un WebP de hero le
2026-08-10 ; c'est la barre. À 82 le hero montait à 1,32, d'où 88.
"""
import os
from PIL import Image, ImageChops
import math

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# (source, [largeurs], qualité) — une seule largeur = pas de variante.
# 88 pour l'image du plus grand rendu, qui est regardée de près ; 82 pour
# l'affiche du film, qui n'est qu'un arrêt sur image derrière un bouton de
# lecture et où les 20 Ko de plus ne se justifient pas.
TRAVAUX = [
    ('assets/img/qbot-photo-poste.jpg', [1400, 700], 88),
    ('assets/img/qbot-demo-poster.jpg', [1280], 82),
]


def ecart(a, b):
    """Écart moyen par canal, en niveaux sur 255."""
    d = ImageChops.difference(a.convert('RGB'), b.convert('RGB'))
    h = d.histogram()
    tot, n = 0, 0
    for canal in range(3):
        for v in range(256):
            c = h[canal * 256 + v]
            tot += c * v
            n += c
    return tot / max(n, 1)


def main():
    for rel, largeurs, qualite in TRAVAUX:
        src = os.path.join(RACINE, rel)
        im = Image.open(src).convert('RGB')
        base = rel[:-4]
        for L in largeurs:
            out = '%s.webp' % base if L == largeurs[0] else '%s-%d.webp' % (base, L)
            r = im if L == im.width else im.resize((L, round(im.height * L / im.width)),
                                                   Image.LANCZOS)
            chemin = os.path.join(RACINE, out)
            r.save(chemin, 'WEBP', quality=qualite, method=6)
            e = ecart(r, Image.open(chemin))
            print('%-40s %4d px %5d Ko -> %4d Ko  ecart %.2f/255'
                  % (out, L, os.path.getsize(src) / 1024,
                     os.path.getsize(chemin) / 1024, e))


if __name__ == '__main__':
    main()
