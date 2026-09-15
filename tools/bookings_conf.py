# -*- coding: utf-8 -*-
"""SOURCE UNIQUE de l'agenda Microsoft Bookings.

L'URL et les libellés de la fenêtre vivent ICI, et nulle part ailleurs.
« maj-nav-booking.py » les lit pour le bouton de la barre de navigation.

LES DEUX PAGES DE RÉSERVATION N'EXISTENT PLUS depuis le 2026-09-02 (demande du
client), et « gen-reservation.py » a été supprimé avec elles : un générateur dont
la sortie est supprimée est une régression en attente. La fenêtre Bookings, elle,
est conservée : elle s'ouvre depuis le bouton de la barre, sur les 21 pages.

POURQUOI UN MODULE ET PAS UNE CONSTANTE DANS CHAQUE SCRIPT : le bouton de la barre
porte les mêmes attributs sur toutes les pages, donc l'URL y est répétée. Sans
source unique, un changement d'agenda en laisserait forcément une derrière.
Même raison que « redirections_map.py » et « vignettes_guides.py ».

UN AGENDA PAR LANGUE DEPUIS LE 2026-09-15. L'anglais a été créé ce jour-là dans
le locataire ; jusque-là il retombait sur le français, par la décision du client
du 2026-09-03 (« le booking en anglais pour l'instant c'est pas dans le scope »).
`adresse()` garde ce repli : une langue sans agenda propre retombe sur le
français, elle ne tombe jamais sur rien.

LA PAGE MICROSOFT NE SE TRADUIT PAS, ET CE N'EST PAS UNE SUPPOSITION. Mesuré le
2026-08-31 (en-GB, nl-BE) et REMESURÉ le 2026-09-15 sur cinq combinaisons :
`Accept-Language: en-US`, `?lang=en-US`, `?mkt=en-US`, `?lang=en-GB&mkt=en-GB` et
sans paramètre — la page rend « Démonstration Q-Bot avec Sylvain PEREZ » dans les
cinq cas. La langue vient du RÉGLAGE de la page de réservation dans le locataire
Microsoft, pas du visiteur : un second agenda est donc la seule voie, il n'y a
aucun paramètre d'URL à trouver.

POUR CHANGER D'AGENDA : modifier URL ci-dessous, puis
    python3 tools/maj-nav-booking.py
    node tools/bump-assets.mjs
"""

URL = {
    'fr': ('https://outlook.office.com/book/'
           'DmonstrationQBotwithSylvainPEREZ@q-leap.eu/s/HTmIB9vz2UyuVzQ4Gft70Q2'),
    # L'agenda anglais, créé le 2026-09-15 en DUPLIQUANT le français dans
    # Bookings, puis réglé en « English (United Kingdom) », rendu public
    # (« Available to anyone ») et retraduit (nom de la page, nom du service,
    # description). Mêmes créneaux, même durée, même employé que le français.
    # L'ALIAS DE BOÎTE AUX LETTRES GARDE LE NOM DE LA DUPLICATION et ne peut
    # plus changer : Microsoft le fige à la création. Il est invisible au
    # visiteur, la fenêtre l'affichant dans un cadre ; il ne se voit que par le
    # repli « ouvrir dans un nouvel onglet ». Pour une adresse propre, il
    # faudrait créer une page neuve au nom anglais, pas une copie.
    'en': ('https://outlook.office.com/book/'
           'DmonstrationQBotavecSylvainPEREZCopier@q-leap.eu/s/HTmIB9vz2UyuVzQ4Gft70Q2'),
}


def adresse(langue):
    """L'agenda de la langue, ou le français tant que l'autre n'existe pas."""
    return URL.get(langue) or URL['fr']


# Les libellés de la fenêtre, eux, sont traduits depuis toujours.
LIBELLES = {
    'fr': dict(
        titre='Agenda de réservation Q-Bot',
        attente='Chargement de l’agenda',
        lent='L’agenda tarde à répondre. Ouvrez-le dans un nouvel onglet.',
        fermer='Fermer l’agenda',
    ),
    'en': dict(
        titre='Q-Bot booking calendar',
        attente='Loading the calendar',
        lent='The calendar is slow to respond. Open it in a new tab.',
        fermer='Close the calendar',
    ),
}

def attributs(langue):
    """Les attributs data-* du déclencheur, dans un ordre stable."""
    l = LIBELLES[langue]
    return [('data-booking-src', adresse(langue)),
            ('data-booking-title', l['titre']),
            ('data-booking-attente', l['attente']),
            ('data-booking-lent', l['lent']),
            ('data-booking-fermer', l['fermer'])]
