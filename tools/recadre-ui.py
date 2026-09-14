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

LE PANNEAU « SCENARIO » A SON PROPRE MASTER, ET IL EST EN DENSITÉ 1. Le client a
fourni le 2026-09-14 une capture plus représentative (un scénario Google
Authenticator, l'écran de choix de compte), mais prise en densité 1 : son titre
mesure 28 px là où celui des deux autres masters en mesure 55. Elle ne peut donc
PAS être découpée à 2360 px de large — ce seraient 2360 px CSS d'application
dans un cadre de 1132, soit du texte à 10 px. Elle est découpée à 1180 px, ce
qui fait exactement les mêmes 1180 px CSS que les 2360 px DPR 2 des deux autres :
l'application garde sa taille native et les trois onglets s'échangent sans saut
d'échelle. Le prix est la densité, moitié moindre, donc un onglet un peu plus
doux sur un écran retina. Une reprise de la capture en densité 2 (écran retina,
ou navigateur à 200 %) se rebranche en changeant le seul master.

SON MASTER EST DÉJÀ ANONYMISÉ. La capture d'origine montrait trois fois
l'adresse professionnelle d'une personne réelle sur l'écran du téléphone,
lisible à la taille d'affichage. Elle a été remplacée par une adresse de rôle de
même longueur (`qa.automation@q-leap.eu`) AVANT archivage : le dépôt est public
et son historique ne se réécrit pas, donc la version brute n'y entre jamais.
C'est la règle qui avait déjà fait écarter l'onglet « Credits ».
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

# ── LE PANNEAU « SCENARIO », DEPUIS SON MASTER EN DENSITÉ 1 ──
# Largeur 1180 = les mêmes 1180 px CSS d'application que les 2360 px DPR 2 des
# deux autres, donc aucun saut d'échelle au changement d'onglet. La hauteur en
# découle par le rapport du cadre et n'est pas un choix : 1180 / (2360/1060).
# La fenêtre verticale part juste sous la barre de l'application (elle est déjà
# dessinée par le balisage de `.appwin`, la garder ferait deux bandeaux) et
# s'arrête sous la liste des comptes, qui est ce que la capture vient montrer.
V2_SRC = 'qbot-ui-scenario-v2-source.png'
V2_X0, V2_LARG = 307, 1180  # centré : le contenu occupe x[677,1117], centre 897
V2_Y0 = 100                 # la barre de l'application s'arrête à y = 63

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

    # Le panneau « scenario », depuis son master en densité 1.
    s = Image.open(SRC / V2_SRC).convert('RGB')
    v2_haut = round(V2_LARG / rapport)
    assert s.width >= V2_X0 + V2_LARG, f'scenario : master trop étroit ({s.width} px)'
    assert s.height >= V2_Y0 + v2_haut, f'scenario : master trop court ({s.height} px)'
    c = s.crop((V2_X0, V2_Y0, V2_X0 + V2_LARG, V2_Y0 + v2_haut))
    # LE RAPPORT DOIT TOMBER SUR CELUI DU CADRE : les images sont en
    # `object-fit: cover`, donc un écart ne déforme pas, il RECADRE en silence.
    assert abs(c.width / c.height - rapport) < 1e-3, f'scenario : rapport {c.width / c.height}'
    ecrire('scenario', c)

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
