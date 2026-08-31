#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble la « homepage bis » : une variante d'accueil bâtie avec le contenu de
la page Démo, à comparer avec l'accueil actuel.

    python3 tools/gen-accueil-bis.py

Elle est GÉNÉRÉE et non écrite à la main, pour la raison habituelle de ce dépôt :
deux pages rédigées l'une après l'autre divergent. Elle est aussi
DÉLIBÉRÉMENT HORS DU PLAN DU SITE, hors du décompte de robots.txt, et aucune page
ne pointe vers elle : c'est une maquette de comparaison, pas une page publiée. Les
deux audits énumérant les pages depuis « sitemap.xml », elle en est exclue d'office.

L'habillage vient de l'accueil (en-tête, barre, pied de page, feuilles de style),
le contenu vient de la page Démo. Les deux donneurs sont à la MÊME profondeur que
la page produite, donc aucun chemin relatif n'est à réécrire.
"""
import io, os, re, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── les six sections reprises de la page Démo, dans l'ordre du récit ──
# le nom est l'« aria-labelledby » de la section chez le donneur
SECTIONS = ['roi-title', 'how-title', 'process-title',
            'pricing-title', 'guarantee-title', 'usecases-title']

LOTS = [
    dict(sortie='accueil-bis.html', habillage='index.html', contenu='commandez.html',
         langue='fr', bascule=('href="en/"', 'href="en/home-bis.html"'),
         titre_prefixe='Variante · ',
         repere="Variante d'accueil, non publiée"),
    dict(sortie='en/home-bis.html', habillage='en/index.html', contenu='en/order.html',
         langue='en', bascule=('href="../"', 'href="../accueil-bis.html"'),
         titre_prefixe='Variant · ',
         repere='Homepage variant, not published'),
]

def lire(rel):
    with io.open(os.path.join(RACINE, rel), encoding='utf-8') as f:
        return f.read()

def section(txt, ident, ou):
    """Renvoie le bloc <section …aria-labelledby="ident"…> … </section>,
    en comptant les balises pour supporter une imbrication."""
    m = re.search(r'<section[^>]*aria-labelledby="%s"[^>]*>' % re.escape(ident), txt)
    if not m:
        sys.exit('ECHEC : section « %s » introuvable dans %s' % (ident, ou))
    i, prof, j = m.start(), 0, m.start()
    for t in re.finditer(r'</?section\b', txt[i:]):
        prof += 1 if t.group(0) == '<section' else -1
        if prof == 0:
            j = i + t.end()
            j = txt.index('>', j) + 1
            return txt[i:j]
    sys.exit('ECHEC : section « %s » non refermée dans %s' % (ident, ou))

def film(bloc, langue):
    """Dans la section « Comment Q-Bot automatise votre 2FA », la photo fixe du
    téléphone docké cède la place à la BOUCLE du boîtier en action : même sujet, en
    mouvement. Extrait de QBV1.2.12 fourni le 2026-08-31, 4,6 s en 960x540 (2,6 Mo),
    choisi sans aucune incrustation, celles du film étant en anglais.

    Le préfixe de profondeur est LU dans le balisage du donneur, jamais déduit."""
    m = re.search(r'<div class="intro__image intro__image--dock">[\s\S]*?</div>', bloc)
    if not m:
        return bloc                      # la photo a pu disparaître du donneur
    pref = re.search(r'src="([^"]*)assets/img/qbot-photo-dock\.jpg"', m.group(0))
    pref = pref.group(1) if pref else ''
    alt = ('La boucle montre le geste : la notification arrive, le scénario se joue.'
           if langue == 'fr' else
           'The loop shows the gesture: the notification arrives, the scenario plays.')
    neuf = ('<div class="video__wrapper video__wrapper--film">\n'
            '        <!-- Boucle muette, sans commande, chargée par le module 18 quand la\n'
            '             section approche. Sans JavaScript il reste l\'affiche. %s -->\n'
            '        <video class="video__player" data-film="%sassets/video/qbot-action.mp4"\n'
            '               poster="%sassets/img/qbot-action-poster.jpg"\n'
            '               muted loop playsinline\n'
            '               aria-hidden="true" tabindex="-1"></video>\n'
            '      </div>' % (alt, pref, pref))
    return bloc.replace(m.group(0), neuf)


def reteinte(bloc, gris):
    """Impose la teinte de fond, l'alternance étant refaite après réordonnancement."""
    def r(m):
        cls = [c for c in m.group(1).split() if c not in ('section--gray',)]
        if gris and 'section' in cls:
            cls.insert(cls.index('section') + 1, 'section--gray')
        return 'class="%s"' % ' '.join(cls)
    return re.sub(r'class="([^"]*)"', r, bloc, count=1)

def genere(lot):
    hab, cont = lire(lot['habillage']), lire(lot['contenu'])

    # ── découpe de l'habillage ──
    for marque in ('</head>', '<main id="main">', '</main>'):
        if marque not in hab:
            sys.exit('ECHEC : « %s » absent de %s' % (marque, lot['habillage']))
    tete = hab[:hab.index('</head>')]
    entre = hab[hab.index('</head>'):hab.index('<main id="main">') + len('<main id="main">')]
    queue = hab[hab.index('</main>'):]
    corps_hab = hab[hab.index('<main id="main">') + len('<main id="main">'):hab.index('</main>')]

    hero = section(corps_hab, 'hero-title', lot['habillage'])
    cta = section(corps_hab, 'cta-title', lot['habillage'])

    # ── la tête : pas de canonique, pas de hreflang, pas de données structurées ──
    # cette page n'appartient pas aux grappes publiques et n'a pas à être comprise
    # par une machine ; le « noindex » de pré-lancement est conservé tel quel.
    tete = re.sub(r'[ \t]*<link rel="canonical"[^>]*>\n', '', tete)
    tete = re.sub(r'[ \t]*<link rel="alternate" hreflang="[^"]*"[^>]*>\n', '', tete)
    tete = re.sub(r'[ \t]*<script type="application/ld\+json">[\s\S]*?</script>\n', '', tete)
    tete = re.sub(r'(<title>)', r'\1' + lot['titre_prefixe'], tete, count=1)

    # le sélecteur de langue doit viser la variante de l'autre langue
    av, ap = lot['bascule']
    if av not in entre:
        sys.exit('ECHEC : bascule de langue « %s » absente de %s' % (av, lot['habillage']))
    entre = entre.replace(av, ap)

    # ── alternance des fonds, calculée depuis la fin ──
    # le bloc d'appel final est mis en gris, la section qui le précède doit donc
    # être claire, et ainsi de suite en remontant jusqu'au hero.
    blocs = []
    for k, i in enumerate(SECTIONS):
        b = section(cont, i, lot['contenu'])
        if i == 'how-title':
            b = film(b, lot['langue'])
        blocs.append(reteinte(b, gris=(k % 2 == 0)))
    cta = reteinte(cta, gris=True)

    repere = (
        '\n<!-- Repère de variante : une seule ligne à retirer le jour où cette page\n'
        '     serait retenue. Encre noire sur le teal de charte (8,0:1), jamais du blanc. -->\n'
        '<div style="position:fixed;z-index:9999;bottom:14px;left:14px;background:#00CBBE;'
        'color:#231F20;font:700 12px/1 Roboto,system-ui,sans-serif;letter-spacing:.06em;'
        'text-transform:uppercase;padding:9px 13px;border-radius:999px;'
        'box-shadow:0 4px 16px rgba(0,0,0,.5);pointer-events:none">%s</div>\n' % lot['repere'])

    out = tete + entre + '\n' + hero + '\n' + '\n'.join(blocs) + '\n' + cta + '\n' + queue
    out = out.replace('</body>', repere + '</body>', 1)

    # ── garde-fous de structure ──
    for quoi, motif in (('feuille de style', r'<link[^>]+style\.css'),
                        ('balise main', r'<main\b'),
                        ('pied de page', r'<footer'),
                        ('noindex', r'name="robots" content="noindex')):
        if not re.search(motif, out):
            sys.exit('ECHEC %s : invariant perdu (%s)' % (lot['sortie'], quoi))
    if 'qbot-action.mp4' not in out:
        sys.exit('ECHEC %s : la boucle du boîtier en action n\'a pas été posée' % lot['sortie'])
    if out.count('<h1') != 1:
        sys.exit('ECHEC %s : %d h1' % (lot['sortie'], out.count('<h1')))
    if 'application/ld+json' in out:
        sys.exit('ECHEC %s : des données structurées subsistent' % lot['sortie'])

    chemin = os.path.join(RACINE, lot['sortie'])
    with io.open(chemin, 'w', encoding='utf-8') as f:
        f.write(out)
    print('OK %-22s %6d octets, %d sections' % (lot['sortie'], len(out), 2 + len(blocs)))

for lot in LOTS:
    genere(lot)
print('\nRAPPEL : page hors plan du site, hors robots.txt, non liée. Ne pas les y ajouter.')
