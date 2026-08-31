#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pose sur le bouton « Réserver une démo » de la barre de navigation les
attributs qui lui font ouvrir l'agenda dans une fenêtre.

    python3 tools/maj-nav-booking.py            # simulation
    python3 tools/maj-nav-booking.py --ecrire

LE BOUTON RESTE UN LIEN, et c'est le point : le module 20 intercepte son clic
seulement s'il peut ouvrir la fenêtre (page en https et <dialog> disponible). Sans
JavaScript, hors https, ou sur un navigateur trop ancien, le clic NAVIGUE vers la
page de réservation comme aujourd'hui. Rien n'est perdu dans aucun cas.

L'URL et les libellés viennent de « bookings_conf.py », source unique.
"""
import io, os, re, sys, glob

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bookings_conf as conf

ECRIRE = '--ecrire' in sys.argv

# le bouton de la barre, dans les deux langues, avec ou sans préfixe de profondeur
BOUTON = re.compile(
    r'<a href="((?:\.\./)?)(reservation\.html|booking\.html|commandez\.html|order\.html)"'
    r'((?:\s+data-booking-[a-z]+="[^"]*")*)'
    r'\s+class="btn btn--primary">(Réserver une démo|Book a demo)</a>')

def pages():
    vus = set()
    for m in ('*.html', 'en/*.html', '*/index.html', 'en/*/index.html'):
        for f in glob.glob(os.path.join(RACINE, m)):
            if not os.path.basename(f).startswith('._'):
                vus.add(f)
    return sorted(vus)

faits, sautes, ko = 0, [], []
for f in pages():
    rel = os.path.relpath(f, RACINE)
    t = io.open(f, encoding='utf-8').read()
    if '<header' not in t:
        continue
    m = BOUTON.search(t)
    if not m:
        sautes.append(rel + ' (bouton de barre non reconnu)')
        continue
    langue = 'en' if m.group(4) == 'Book a demo' else 'fr'
    attrs = ''.join('\n       %s="%s"' % (k, v.replace('"', '&quot;'))
                    for k, v in conf.attributs(langue))
    neuf = ('<a href="%s%s" data-booking-open%s\n       class="btn btn--primary">%s</a>'
            % (m.group(1), m.group(2), attrs, m.group(4)))
    if m.group(0) == neuf:
        sautes.append(rel + ' (déjà à jour)')
        continue
    t = t[:m.start()] + neuf + t[m.end():]
    # garde-fous : la structure de l'en-tête ne doit pas bouger
    for quoi, motif in (('feuille de style', r'<link[^>]+style\.css'),
                        ('en-tête', r'<header'), ('barre', r'class="nav__inner"')):
        if not re.search(motif, t):
            ko.append('%s : invariant perdu (%s)' % (rel, quoi)); break
    else:
        if ECRIRE:
            io.open(f, 'w', encoding='utf-8').write(t)
        faits += 1

print('%d bouton(s) de barre équipé(s)%s' % (faits, '' if ECRIRE else ' (SIMULATION)'))
for s in sautes:
    print('   sauté : ' + s)
if ko:
    print('ECHECS :', file=sys.stderr)
    for s in ko:
        print('   ' + s, file=sys.stderr)
    sys.exit(1)
