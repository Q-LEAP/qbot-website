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

# LE MOTIF DOIT RECONNAÎTRE LE BOUTON DÉJÀ ÉQUIPÉ, sans quoi ce script ne sert
# qu'une fois. Sa première version exigeait des attributs À VALEUR
# (`data-booking-xxx="…"`) et ne pouvait donc pas revoir un bouton portant
# `data-booking-open`, qui est un attribut NU. Relevé le 2026-09-01 : sur les
# 23 pages équipées, il n'en reconnaissait plus AUCUNE. Autrement dit la « source
# unique » de « bookings_conf.py » ne l'était plus : le jour où l'agenda change
# d'URL, la commande annoncée en tête de ce fichier n'aurait rien mis à jour, et
# elle l'aurait annoncé sans erreur.
BOUTON = re.compile(
    r'<a href="((?:\.\./)?)(reservation\.html|booking\.html|commandez\.html|order\.html)"'
    r'((?:\s+data-booking-open|\s+data-booking-[a-z]+="[^"]*")*)'
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
    # ON NE CHERCHE QUE DANS LA BARRE. Sans cette borne, le motif attrapait sur
    # « faq.html » un appel à l'action du CORPS de la page, qui porte le même
    # libellé et la même classe : le script annonçait « 1 bouton équipé » en
    # visant le mauvais élément, et laissait la vraie barre inchangée.
    d = t.find('class="nav__actions"')
    fin = t.find('</nav>', d) if d != -1 else -1
    m = BOUTON.search(t, d, fin) if fin != -1 else None
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
