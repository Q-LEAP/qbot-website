#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pose les attributs qui font ouvrir l'agenda dans une fenêtre, sur les DEUX
déclencheurs de chaque page : le bouton « Réserver une démo » de la barre de
navigation, et l'entrée « Réserver une démo » du pied de page.

    python3 tools/maj-nav-booking.py            # simulation
    python3 tools/maj-nav-booking.py --ecrire

LE DÉCLENCHEUR DU PIED DE PAGE EST ARRIVÉ LE 2026-09-09 : « dans le footer,
quand on clique sur demander une démo, on ouvre l'agenda de Sylvain ». Cette
entrée menait à « commandez.html », que le même retour sort de la publication
(« dans l'état actuel, je préfère ne pas la publier »).

IL EST TRAITÉ ICI ET PAS À LA MAIN, parce que l'URL de l'agenda serait sinon
écrite à deux endroits par page. C'est exactement ce que « bookings_conf.py »
existe pour éviter, et le défaut relevé le 2026-09-01 quand le motif de ce
script ne reconnaissait plus aucune page : une « source unique » qui n'atteint
pas tous ses points d'usage n'en est pas une.

LES DEUX RESTENT DES LIENS, et c'est le point : le module 20 intercepte le clic
seulement s'il peut ouvrir la fenêtre (page en https et <dialog> disponible).
Sans JavaScript, hors https, ou sur un navigateur trop ancien, le clic NAVIGUE
vers la page contact, qui porte le formulaire. Rien n'est perdu dans aucun cas.

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
    r'<a href="((?:\.\./)?)(contact\.html|commandez\.html|order\.html)"'
    # « reservation.html » et « booking.html » ont disparu de cette liste avec
    # les deux pages, supprimées le 2026-09-02 à la demande du client. Le repli
    # sans JavaScript du bouton est désormais la page contact ; la fenêtre
    # Bookings, elle, vit dans les attributs et n'a pas bougé.
    r'((?:\s+data-booking-open|\s+data-booking-[a-z]+="[^"]*")*)'
    r'\s+class="btn btn--primary">(Réserver une démo|Book a demo)</a>')

def pages():
    vus = set()
    for m in ('*.html', 'en/*.html', '*/index.html', 'en/*/index.html'):
        for f in glob.glob(os.path.join(RACINE, m)):
            if not os.path.basename(f).startswith('._'):
                vus.add(f)
    return sorted(vus)

# L'ENTRÉE DU PIED DE PAGE. Elle menait aux pages « Démo » (commandez.html /
# en/order.html), sorties de la publication le 2026-09-09 : son repli sans
# JavaScript devient donc la page contact, comme celui du bouton de la barre.
# Le motif accepte l'ancienne cible ET la nouvelle, sans quoi ce script ne
# servirait qu'une fois — le défaut du 2026-09-01, à l'identique.
# `\s*` AVANT LE CHEVRON FERMANT, ET C'EST UN CORRECTIF (2026-09-09) : ce script
# écrit lui-même l'entrée du pied de page sur plusieurs lignes, en mettant le
# chevron en tête de la dernière. Son propre motif l'exigeait collé au dernier
# attribut, si bien qu'il ne reconnaissait plus AUCUNE des 17 pages qu'il venait
# d'équiper — « entrée de pied non reconnue » partout, sans erreur. Le jour d'un
# changement d'agenda, la barre aurait été mise à jour et le pied laissé sur
# l'ancienne URL : deux adresses pour un seul agenda. Un outil doit reconnaître
# sa propre sortie, et c'est ce que l'épreuve de vivacité vérifie (changer l'URL
# dans bookings_conf.py, relancer, lire 17 barres ET 17 pieds équipés).
PIED = re.compile(
    r'<li><a href="((?:\.\./)?)(contact\.html|commandez\.html|order\.html)"'
    r'((?:\s+data-booking-open|\s+data-booking-[a-z]+="[^"]*")*)'
    r'\s*>(Démo|Demo|Réserver une démo|Book a demo)</a></li>')

LIBELLE_PIED = {'fr': 'Réserver une démo', 'en': 'Book a demo'}

# LA BOÎTE DE RENDEZ-VOUS DE LA PAGE CONTACT N'EXISTE PLUS (2026-09-09) : le
# client a demandé de simplifier cette colonne au maximum. Une troisième passe
# avait été écrite pour son lien, quelques minutes plus tôt le même jour ; elle
# est retirée, et pas seulement parce qu'elle est sans objet.
# SON MOTIF ÉTAIT DANGEREUX : `<a href="contact.html" class="link-edito">`
# désigne aussi les liens de NAVIGATION posés par la hiérarchie des CTA, et le
# script s'apprêtait à en transformer un de la page 404 en déclencheur d'agenda
# (relevé : « 1 lien de boîte équipé » sur un site qui n'en a plus un seul).
# Un motif doit être borné à sa zone, comme les deux autres passes le sont à la
# barre de navigation et au pied de page. Si la boîte revient, la borner.

faits, faits_pied, sautes, ko = 0, 0, [], []
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
    change = False
    if m.group(0) == neuf:
        sautes.append(rel + ' (barre déjà à jour)')
    else:
        t = t[:m.start()] + neuf + t[m.end():]
        faits += 1
        change = True

    # ── L'entrée du pied de page, bornée au pied de page ──
    # Sans cette borne le motif attraperait une entrée de menu portant le même
    # libellé : c'est le défaut qui a fait viser le mauvais élément sur
    # « faq.html » avant que la recherche du bouton ne soit bornée à la barre.
    dp = t.find('<footer')
    finp = t.find('</footer>', dp) if dp != -1 else -1
    mp = PIED.search(t, dp, finp) if finp != -1 else None
    if not mp:
        # La page « Démo » elle-même marque sa propre entrée en texte mort :
        # rien à équiper, ce n'est pas un défaut.
        sautes.append(rel + ' (entrée de pied non reconnue)')
    else:
        prof = mp.group(1)
        attrs_p = ''.join('\n              %s="%s"' % (k, v.replace('"', '&quot;'))
                          for k, v in conf.attributs(langue))
        neuf_p = ('<li><a href="%scontact.html" data-booking-open%s\n              >%s</a></li>'
                  % (prof, attrs_p, LIBELLE_PIED[langue]))
        if mp.group(0) == neuf_p:
            sautes.append(rel + ' (pied déjà à jour)')
        else:
            t = t[:mp.start()] + neuf_p + t[mp.end():]
            faits_pied += 1
            change = True

    if not change:
        continue
    # garde-fous : la structure de l'en-tête et du pied ne doit pas bouger
    for quoi, motif in (('feuille de style', r'<link[^>]+style\.css'),
                        ('en-tête', r'<header'), ('barre', r'class="nav__inner"'),
                        ('pied', r'<footer')):
        if not re.search(motif, t):
            ko.append('%s : invariant perdu (%s)' % (rel, quoi)); break
    else:
        if ECRIRE:
            io.open(f, 'w', encoding='utf-8').write(t)

print('%d bouton(s) de barre et %d entrée(s) de pied équipé(s)%s'
      % (faits, faits_pied, '' if ECRIRE else ' (SIMULATION)'))
for s in sautes:
    print('   sauté : ' + s)
if ko:
    print('ECHECS :', file=sys.stderr)
    for s in ko:
        print('   ' + s, file=sys.stderr)
    sys.exit(1)
