#!/usr/bin/env python3
"""Les trois captures de l'interface livrée, découpées depuis les masters.

    python3 tools/recadre-ui.py
    node tools/bump-assets.mjs      # les fichiers sont réécrits sous le même nom

ON RECADRE EN HAUTEUR, JAMAIS EN LARGEUR. Les masters sont des captures DPR 2
d'une fenêtre de 1575 px CSS : une découpe de 2360 px de large affichée sur les
1132 px du conteneur rend l'application à sa taille NATIVE, texte de 15 px à
15 px. Réduire la largeur du cadre divise cette échelle (900 px de cadre
donneraient 11,4 px de texte), c'est-à-dire le défaut même que ce cadrage
corrige. La hauteur, elle, ne coûte rien à la lisibilité.

DEUX VALEURS À CHANGER ENSEMBLE. La hauteur ci-dessous et l'`aspect-ratio` de
`.appwin__body` dans `assets/css/style.css`. Les trois panneaux sont en
`position: absolute`, donc le corps n'a pas de hauteur intrinsèque et c'est ce
rapport qui la lui donne ; l'image étant en `object-fit: cover`, un rapport
périmé ne déforme rien mais RECADRE en silence. Plus les attributs `height`
des six `<img>` (index, en/index, caracteristiques, en/technical-specs).

LES TROIS PANNEAUX DOIVENT GARDER LA MÊME HAUTEUR : ils sont échangés dans le
même cadre par le module 23, et deux hauteurs feraient sauter la fenêtre au
changement d'onglet.

Historique de la hauteur : 1500 au 2026-09-07, puis 1060 le 2026-09-09 (« le
screenshot ici est un peu imposant, je trouve, je réduirais »), ce qui fait
passer le cadre de 719 à 508 px d'affichage à 1440 px de large.

PAS DE QUATRIÈME PANNEAU « CREDITS » : cette capture nomme sept contributeurs
avec leur adresse de courriel, et la règle du dépôt est de ne nommer personne
sans accord écrit. `ScreenUI/` est tenu hors de git pour la même raison.
"""
from pathlib import Path

from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
SRC = RACINE / 'Documentations' / 'assets-sources'
DST = RACINE / 'assets' / 'img'

X0, X1 = 404, 2764          # bornes de la découpe, mesurées sur les masters
Y0 = 123                    # juste sous la barre du navigateur de la capture
HAUTEUR = 1060              # ← à garder d'accord avec l'aspect-ratio du CSS
QUALITE = 88                # WebP : 185 Ko pour les trois, contre 315 en JPEG

PANNEAUX = ('home', 'scenario', 'api')

# ── LA DÉCOUPE CARRÉE DE LA SECTION « L'ÉDITEUR » (accueil) ──
# Elle ne suit PAS la règle ci-dessus, et c'est voulu : la section a été refondue
# le 2026-09-09 en deux colonnes (« recadrer pour montrer uniquement ce qui est
# utile »), donc la fenêtre n'occupe plus la largeur du conteneur mais 600 px, et
# une découpe de 2 360 px y tomberait au quart de son échelle. Elle est cadrée sur
# la zone utile — barre de commandes, palette d'outils, écran du téléphone — et le
# téléphone est coupé net en bas : dans un cadre qui se lit comme une fenêtre, une
# page qui continue sous le bord est ce qu'on attend.
# 1 300 px de côté n'est pas un chiffre rond : à 600 px d'affichage, un écran de
# densité 2 en demande 1 200, donc l'agrandissement vaut 0,92. Les 1,15 relevés à
# 2 560 px sont la limite du master, qui n'a pas plus de pixels dans cette zone.
# LES TROIS REPÈRES NUMÉROTÉS SONT DU BALISAGE, pas des pixels : leurs positions
# en pourcentage vivent dans le HTML des deux accueils. Si ce cadrage change,
# elles doivent être revérifiées AU RENDU — une position juste sur le papier peut
# recouvrir l'élément qu'elle désigne.
CARRE_X0, CARRE_Y0, CARRE_N = 937, 330, 1300


def main() -> None:
    for nom in PANNEAUX:
        master = SRC / f'qbot-ui-{nom}-source.jpeg'
        s = Image.open(master).convert('RGB')
        assert s.width == 3168, f'{nom} : largeur du master {s.width}, attendu 3168'
        assert s.height >= Y0 + HAUTEUR, f'{nom} : master trop court ({s.height} px)'

        c = s.crop((X0, Y0, X1, Y0 + HAUTEUR))
        assert c.size == (X1 - X0, HAUTEUR), f'{nom} : découpe {c.size}'

        cible = DST / f'qbot-ui-{nom}.webp'
        avant = cible.stat().st_size if cible.exists() else 0
        c.save(cible, 'WEBP', quality=QUALITE, method=6)
        print(f'{nom:>9} {c.size}  {avant // 1024} Ko -> {cible.stat().st_size // 1024} Ko')

    # La découpe carrée de l'accueil, depuis le même master que « scenario ».
    s = Image.open(SRC / 'qbot-ui-scenario-source.jpeg').convert('RGB')
    assert s.width >= CARRE_X0 + CARRE_N and s.height >= CARRE_Y0 + CARRE_N, 'master trop petit'
    c = s.crop((CARRE_X0, CARRE_Y0, CARRE_X0 + CARRE_N, CARRE_Y0 + CARRE_N))
    assert c.size == (CARRE_N, CARRE_N), f'decoupe carree {c.size}'
    cible = DST / 'qbot-ui-editeur.webp'
    avant = cible.stat().st_size if cible.exists() else 0
    c.save(cible, 'WEBP', quality=QUALITE, method=6)
    print(f'  editeur {c.size}  {avant // 1024} Ko -> {cible.stat().st_size // 1024} Ko')

    largeur = X1 - X0
    print(f'\naspect-ratio a declarer : {largeur} / {HAUTEUR}')
    print(f'affiche a 1440 px de large : {round(1132 * HAUTEUR / largeur)} px de haut')


if __name__ == '__main__':
    main()
