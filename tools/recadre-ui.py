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

L'ÉDITEUR A SON PROPRE MASTER, ET IL EST EN DENSITÉ 1. Le client a fourni le
2026-09-14 une capture plus représentative — un scénario dont l'écran du
téléphone montre le vrai défi LuxTrust, code couleur et champ OTP — et elle
alimente MAINTENANT LES DEUX découpes de l'éditeur : l'onglet « Scenario Editor »
des fiches techniques ET la vignette carrée des accueils. C'est le même écran,
il n'y a aucune raison qu'il diffère d'une page à l'autre.

Elle est en densité 1 : son titre mesure 28 px là où celui des deux masters
« home » et « api » en mesure 55. Les découpes sont donc dimensionnées en px CSS
d'application et non en pixels de fichier :
  • l'onglet à 1180 px = les mêmes 1180 px CSS que les 2360 px DPR 2 des deux
    autres panneaux, donc aucun saut d'échelle au changement d'onglet ;
  • le carré à 650 px = les mêmes 650 px CSS que les 1300 px DPR 2 de l'ancien
    master, donc le cadrage validé est reproduit à l'identique.
Le prix est la densité, moitié moindre, donc un rendu un peu plus doux sur un
écran retina. UNE REPRISE DE LA CAPTURE EN DENSITÉ 2 (écran retina, ou
navigateur à 200 %) SE REBRANCHE EN CHANGEANT LE SEUL MASTER, sans toucher aux
coordonnées : il suffira de les doubler.

PAS D'ANONYMISATION À FAIRE SUR CE MASTER-CI. Le précédent (une liste de comptes
Google Authenticator) portait trois fois l'adresse professionnelle d'une
personne réelle et avait dû être repris avant archivage ; celui-ci ne montre
qu'un défi LuxTrust, transitoire et à usage unique. Le contrôle reste à faire
sur toute nouvelle capture : le dépôt est public et son historique ne se
réécrit pas.

`qbot-ui-scenario-source.jpeg` N'EST PLUS LU PAR CE SCRIPT. Il reste archivé,
c'est le master de l'ancien écran d'accueil du téléphone.
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

PANNEAUX = ('home', 'api')  # « scenario » a son propre master, voir ci-dessous

# ── LE MASTER DE L'ÉDITEUR, EN DENSITÉ 1, QUI ALIMENTE LES DEUX DÉCOUPES ──
# Relevé sur ce fichier : barre de l'application y[0,62], titre y[117,145],
# barre de commandes y[202,230], champ « Scenario » y[280,315], palette et
# téléphone y[337,889], contenu x[677,1117] donc centré sur x = 897.
SCN_SRC = 'qbot-ui-scenario-v3-source.png'

# L'onglet des fiches techniques. Largeur 1180 (voir le docstring), hauteur
# donnée par le rapport du cadre. La fenêtre part sous la barre de l'application
# — elle est déjà dessinée par le balisage de `.appwin`, la garder ferait deux
# bandeaux — et s'arrête sous le champ OTP.
SCN_X0, SCN_LARG = 307, 1180
SCN_Y0 = 100

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
# Côté 650 = les mêmes 650 px CSS que les 1300 px DPR 2 de l'ancien master, donc
# le même cadrage : la barre de commandes en haut, la palette à gauche, le
# téléphone coupé net en bas. Centré sur x = 897 comme le reste du contenu.
CARRE_X0, CARRE_Y0, CARRE_N = 572, 185, 650


def main() -> None:
    rapport = (X1 - X0) / HAUTEUR

    def ecrire(nom, decoupe):
        cible = DST / f'qbot-ui-{nom}.webp'
        poids = cible.stat().st_size if cible.exists() else 0
        decoupe.save(cible, 'WEBP', quality=QUALITE, method=6)
        print(f'{nom:>9} {decoupe.size}  {poids // 1024} Ko -> {cible.stat().st_size // 1024} Ko')

    for nom in PANNEAUX:
        master = SRC / f'qbot-ui-{nom}-source.jpeg'
        s = Image.open(master).convert('RGB')
        assert s.width == 3168, f'{nom} : largeur du master {s.width}, attendu 3168'
        assert s.height >= Y0 + HAUTEUR, f'{nom} : master trop court ({s.height} px)'

        c = s.crop((X0, Y0, X1, Y0 + HAUTEUR))
        assert c.size == (X1 - X0, HAUTEUR), f'{nom} : découpe {c.size}'
        ecrire(nom, c)

    # LES DEUX DÉCOUPES DE L'ÉDITEUR VIENNENT DU MÊME MASTER : c'est le même
    # écran, montré sur les fiches techniques et sur les accueils.
    s = Image.open(SRC / SCN_SRC).convert('RGB')

    scn_haut = round(SCN_LARG / rapport)
    assert s.width >= SCN_X0 + SCN_LARG, f'scenario : master trop étroit ({s.width} px)'
    assert s.height >= SCN_Y0 + scn_haut, f'scenario : master trop court ({s.height} px)'
    c = s.crop((SCN_X0, SCN_Y0, SCN_X0 + SCN_LARG, SCN_Y0 + scn_haut))
    # LE RAPPORT DOIT TOMBER SUR CELUI DU CADRE : les images sont en
    # `object-fit: cover`, donc un écart ne déforme pas, il RECADRE en silence.
    assert abs(c.width / c.height - rapport) < 1e-3, f'scenario : rapport {c.width / c.height}'
    ecrire('scenario', c)

    assert s.width >= CARRE_X0 + CARRE_N, f'carré : master trop étroit ({s.width} px)'
    assert s.height >= CARRE_Y0 + CARRE_N, f'carré : master trop court ({s.height} px)'
    c = s.crop((CARRE_X0, CARRE_Y0, CARRE_X0 + CARRE_N, CARRE_Y0 + CARRE_N))
    assert c.size == (CARRE_N, CARRE_N), f'decoupe carree {c.size}'
    ecrire('editeur', c)

    largeur = X1 - X0
    print(f'\naspect-ratio a declarer : {largeur} / {HAUTEUR}')
    print(f'affiche a 1440 px de large : {round(1132 * HAUTEUR / largeur)} px de haut')


if __name__ == '__main__':
    main()
