# -*- coding: utf-8 -*-
"""SOURCE UNIQUE de l'agenda Microsoft Bookings.

L'URL et les libellés de la fenêtre vivent ICI, et nulle part ailleurs. Deux
scripts la lisent, « gen-reservation.py » pour les deux pages de réservation et
« maj-nav-booking.py » pour le bouton de la barre de navigation des 23 pages.

POURQUOI UN MODULE ET PAS UNE CONSTANTE DANS CHAQUE SCRIPT : le bouton de la barre
porte les mêmes attributs sur toutes les pages, donc l'URL y est répétée. Sans
source unique, un changement d'agenda en laisserait forcément une derrière.
Même raison que « redirections_map.py » et « vignettes_guides.py ».

POUR CHANGER D'AGENDA : modifier URL ci-dessous, puis
    python3 tools/gen-reservation.py
    python3 tools/maj-nav-booking.py
    python3 tools/gen-accueil-bis.py
    node tools/bump-assets.mjs
"""

URL = ('https://outlook.office.com/book/'
       'DmonstrationQBotwithSylvainPEREZ@q-leap.eu/s/HTmIB9vz2UyuVzQ4Gft70Q2')

# Le Bookings n'existe qu'en français : la page Microsoft ne se traduit pas
# (testée en en-GB et en nl-BE le 2026-08-31). Les libellés, eux, sont traduits.
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
    return [('data-booking-src', URL),
            ('data-booking-title', l['titre']),
            ('data-booking-attente', l['attente']),
            ('data-booking-lent', l['lent']),
            ('data-booking-fermer', l['fermer'])]
