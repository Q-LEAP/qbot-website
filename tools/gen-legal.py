#!/usr/bin/env python3
"""Génère les quatre pages légales depuis le contenu relevé sur le live.

POURQUOI UN SCRIPT. Les quatre pages sont la MÊME structure avec deux jeux de
textes, comme les pages de cas d'usage : écrites l'une après l'autre elles
divergeraient, et les passes d'audit l'ont déjà reproché plusieurs fois à ce
dépôt. Ici c'est en plus une migration de contenu : le texte doit être repris
mot pour mot, donc il ne doit pas passer par mes doigts.

CHAÎNE COMPLÈTE
  1. tools/fetch-legal.py  relève les quatre pages du live dans un navigateur
     réel, en ne gardant que les blocs VISIBLES (`offsetParent !== null`, cf.
     la note sur les blocs masqués du live dans CLAUDE.md), et écrit
     tools/legal-source.json.
  2. tools/gen-legal.py    (ce fichier) reconstruit les quatre pages dans le
     gabarit du site.
Pour reprendre une mise à jour publiée sur le live : relancer les deux, dans
cet ordre.

CE QUI EST REPRIS À L'IDENTIQUE : chaque mot, SAUF les amendements énumérés plus
bas. Le texte n'est ni résumé ni traduit, et les conditions de vente ne sont pas
touchées du tout. Les deux politiques de confidentialité, elles, décrivaient le
WordPress qu'elles remplacent (cookies, Google Analytics, pixels tiers, comptes
client, serveurs « exclusivement dans l'Union européenne ») : la table
SECTIONS_AMENDEES / RETOUCHES dit ce qui est corrigé et pourquoi, une ligne par
écart, chacune assertée. Reprise demandée par le client le 2026-09-01.

CE QUI CHANGE, ET SEULEMENT CELA :
  — le BALISAGE. Le live écrit ses sous-titres en `<p><strong>…</strong></p>`,
    un artefact d'Elementor. Ce sont des titres : ils deviennent des `<h2>`.
    Les mots ne changent pas, la hiérarchie devient valide et citable.
  — les LIENS INTERNES, repointés sur nos pages locales, et `http://www.q-leap.eu`
    passé en `https://q-leap.eu` (même cible, sans contenu mixte).
  — l'HABILLAGE : notre en-tête, notre pied de page, notre appel à l'action.
    EXTRAITS d'une page du site (« a-propos.html » et « en/about.html »), jamais
    écrits ici : les libellés écrits à la main avaient vieilli d'une passe
    sitewide sans que rien ne le dise. Les deux articles de blog qui servaient
    de gabarits jusque-là ont été supprimés le 2026-08-28, ce qui rendait ce
    script MORT ; il l'est resté jusqu'au 2026-09-01.
  — le FIL D'ARIANE VISIBLE a été retiré du site le 2026-08-28 : il n'est plus
    écrit ici non plus. Le « BreadcrumbList » des données structurées reste.

L'ADRESSE DES PAGES EST CELLE DU LIVE, à dessein : `conditions-vente/index.html`
répond sur `https://q-bot.eu/conditions-vente/`, exactement comme aujourd'hui.
GitHub Pages ne sait pas rediriger (relevé par l'audit RosoAI) : garder l'URL
est donc le seul moyen de ne pas casser les liens entrants et les 52 liens de
pied de page le jour de la bascule. Les deux niveaux de profondeur (`../` pour
le français, `../../` pour l'anglais) sont ceux de `blog/` et `en/blog/`, donc
l'en-tête et le pied de page de ces gabarits se réutilisent tels quels.
"""

import io
import json
import os
import posixpath
import re

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = json.load(io.open(os.path.join(RACINE, 'tools/legal-source.json'), encoding='utf-8'))

# ── Les quatre pages. `bornes` délimite le contenu dans le relevé : du titre de
#    la page (exclu, il devient le <h1>) au bloc d'appel à l'action du live.
PAGES = [
    dict(cle='cv-fr', sortie='conditions-vente/index.html', lang='fr', prof=1,
         bornes=(6, 176), gabarit='a-propos.html',
         url='https://q-bot.eu/conditions-vente/',
         alt='https://q-bot.eu/en/terms-and-conditions-of-sale/',
         alt_rel='../en/terms-and-conditions-of-sale/',
         titre='Conditions générales de vente Q-Bot | Q-Leap',
         desc="Conditions générales de vente de Q-Bot, robot d'automatisation de la 2FA, "
              "édité par Q-Leap S.A. au Luxembourg.",
         label='Mentions légales', fil='Conditions de vente'),
    dict(cle='conf-fr', sortie='confidentialite/index.html', lang='fr', prof=1,
         bornes=(6, 56), gabarit='a-propos.html',
         url='https://q-bot.eu/confidentialite/',
         alt='https://q-bot.eu/en/privacy/', alt_rel='../en/privacy/',
         titre='Confidentialité des données Q-Bot | Q-Leap',
         desc="Politique de confidentialité de Q-Bot et de l'application Q-Bot Mobile : "
              "données collectées, finalités, vos droits, conservation.",
         label='Mentions légales', fil='Confidentialité'),
    dict(cle='cv-en', sortie='en/terms-and-conditions-of-sale/index.html', lang='en', prof=2,
         bornes=(6, 176), gabarit='en/about.html',
         url='https://q-bot.eu/en/terms-and-conditions-of-sale/',
         alt='https://q-bot.eu/conditions-vente/', alt_rel='../../conditions-vente/',
         titre='Q-Bot general terms and conditions | Q-Leap',
         desc='General terms and conditions of sale for Q-Bot, the 2FA test automation robot '
              'published by Q-Leap S.A. in Luxembourg.',
         label='Legal', fil='Terms and conditions'),
    dict(cle='priv-en', sortie='en/privacy/index.html', lang='en', prof=2,
         bornes=(6, 56), gabarit='en/about.html',
         url='https://q-bot.eu/en/privacy/',
         alt='https://q-bot.eu/confidentialite/', alt_rel='../../confidentialite/',
         titre='Q-Bot data privacy | Q-Leap',
         desc='Privacy policy for Q-Bot and the Q-Bot Mobile app: data collected, purposes, '
              'your rights, retention.',
         label='Legal', fil='Privacy'),
]

# ── Les liens du contenu, repointés. La clef est l'URL telle qu'elle est écrite
#    sur le live, la valeur est un gabarit où {p} est le préfixe de profondeur.
LIENS = {
    'http://www.q-leap.eu':              'https://q-leap.eu',
    'https://q-bot.eu/contact/':         '{p}contact.html',
    'https://q-bot.eu/en/contact/':      '{p}contact.html',
    'https://q-bot.eu/en/contact-1/':    '{p}contact.html',
    'https://q-bot.eu/en/contact-us/':   '{p}contact.html',
}

# ── Les dates de dernière mise à jour, en ISO. Le live les écrit en clair ; il
#    faut la forme lisible par machine à côté, sans changer le texte affiché.
DATES_ISO = {'Date de la dernière mise à jour : 7 juillet 2025': '2025-07-07',
             'Last update: June, 11th 2024': '2024-06-11'}


# ══════════════════════════════════════════════════════════════════════════════
# CE QUE LE TEXTE DU LIVE DIT, ET QUE LE NOUVEAU SITE NE FAIT PLUS
#
# La règle d'origine de ce script était « chaque mot du live, jamais reformulé ».
# Elle tenait tant que les deux sites étaient le même site. Ils ne le sont plus :
# la politique de confidentialité décrit un WordPress avec des cookies, une
# mesure d'audience Google Analytics, des scripts et pixels tiers, des comptes
# client et des commandes, et des serveurs « exclusivement situés au sein de
# l'Union européenne ». Mesuré sur le nouveau site : 0 `document.cookie`,
# 0 balise d'analytics, 0 requête vers un tiers au chargement, aucun compte,
# aucune commande, et un hébergement GitHub Pages.
#
# UNE POLITIQUE QUI ANNONCE PLUS DE COLLECTE QU'IL N'Y EN A N'EST PAS « PRUDENTE »,
# ELLE EST FAUSSE, et sur ce point précis le sens de la correction est agréable :
# la nouvelle version collecte moins. Reprise demandée par le client le
# 2026-09-01, après le relevé de l'audit RosoAI n°5 puis n°6.
#
# LES ÉCARTS AVEC LE LIVE SONT DONC ÉNUMÉRÉS ICI, ET NULLE PART AILLEURS. Chacun
# porte sa raison et son assertion : si le live change et que le texte visé n'est
# plus là, le script s'arrête au lieu de laisser tomber l'amendement en silence.
# Le reste du document — droits, conservation, sécurité, application mobile,
# conditions de vente — n'est pas touché : ce sont des engagements juridiques,
# pas une description du site.
# ══════════════════════════════════════════════════════════════════════════════

# Sections entières remplacées ou supprimées, désignées par leur intervalle de
# blocs dans le relevé. `titre` est l'assertion : le premier bloc de l'intervalle
# doit bien commencer par ce texte.
SECTIONS_AMENDEES = {
    'conf-fr': [
        dict(de=12, a=16, titre='Cookies',
             raison="le site ne dépose aucun cookie : la section décrivait ceux du WordPress",
             blocs=[
                 ('h2', 'Cookies'),
                 ('p', "Ce site ne dépose aucun cookie, n'utilise aucun traceur et ne mesure "
                       "pas son audience. Il n'y a donc pas de bandeau de consentement&nbsp;: "
                       "il n'y a rien à consentir."),
                 ('p', "Le site enregistre une seule information dans votre navigateur, dans "
                       "le stockage de session&nbsp;: votre position de lecture, le temps d'un "
                       "changement de langue, afin de vous ramener au même endroit de la page. "
                       "Elle est effacée dès qu'elle est relue, elle ne quitte jamais votre "
                       "navigateur et elle ne permet pas de vous identifier."),
             ]),
        dict(de=17, a=18, titre='Données recueillies par des technologies standard',
             raison="aucun script, pixel ni redirection tiers ; deux contenus extérieurs, "
                    "chargés seulement après un clic annoncé",
             blocs=[
                 ('h2', 'Contenus tiers, chargés seulement si vous le demandez'),
                 ('p', "Le site n'appelle aucun service tiers au chargement d'une page&nbsp;: "
                       "ni script, ni pixel, ni redirection, ni police distante. Deux contenus "
                       "extérieurs ne se chargent qu'après un clic de votre part, et ce clic "
                       "est annoncé à l'endroit où il se fait&nbsp;: la carte de la page "
                       "Contact, fournie par Google Maps, et l'agenda de réservation de "
                       "démonstration, fourni par Microsoft Bookings. Tant que vous ne cliquez "
                       "pas, votre navigateur ne contacte ni Google ni Microsoft. Dès lors que "
                       "vous cliquez, ces fournisseurs reçoivent votre adresse IP et peuvent "
                       "déposer leurs propres cookies, selon leurs politiques respectives."),
             ]),
        dict(de=19, a=20, titre='Données fournies par les appareils mobiles',
             raison="section supprimée : elle annonçait un traitement par « nos serveurs et "
                    "ceux de certains de nos partenaires (notamment Google Analytics) » qui "
                    "n'existe pas. La seule application est Q-Bot Mobile, dont la section "
                    "dédiée dit qu'elle ne collecte aucune donnée identifiante.",
             blocs=[]),
        dict(de=26, a=26, titre='Analyser le volume et l\u2019historique',
             raison="item supprim\u00e9 : le site ne mesure ni volume ni historique de "
                    "navigation, et il n'a aucun moyen de le faire. Retir\u00e9 sur "
                    "d\u00e9cision du client le 2026-09-01.",
             blocs=[]),
        dict(de=40, a=41, titre='Lieu de stockage des données et transferts',
             raison="le site est hébergé sur GitHub Pages : « exclusivement au sein de "
                    "l'Union européenne » n'est plus vrai",
             blocs=[
                 ('h2', 'Lieu de stockage des données et transferts'),
                 ('p', "Ce site est un site statique, sans base de données&nbsp;: il ne "
                       "conserve rien. Il est hébergé sur GitHub&nbsp;Pages "
                       "(GitHub,&nbsp;Inc., groupe Microsoft), dont le réseau de diffusion "
                       "sert les pages depuis des serveurs situés dans plusieurs pays, "
                       "y compris hors de l'Union européenne."),
                 ('p', "Les demandes envoyées depuis le formulaire de contact ne transitent "
                       "pas par le site&nbsp;: elles ouvrent votre propre logiciel de "
                       "courrier avec le message prérempli, et ne partent que si vous les "
                       "envoyez vous-même. Les inscriptions à la lettre d'information sont "
                       "transmises à Brevo (anciennement Sendinblue), notre sous-traitant "
                       "pour l'envoi des lettres d'information."),
                 ('p', "<a href=\"https://q-leap.eu\">Q-LEAP SA</a> s\u2019engage à vous "
                       "informer immédiatement, dans la mesure où nous y sommes légalement "
                       "autorisés, en cas de requête provenant d\u2019une autorité "
                       "administrative ou judiciaire relative à vos données."),
             ]),
    ],
    'priv-en': [
        dict(de=12, a=16, titre='Cookies',
             raison="see conf-fr",
             blocs=[
                 ('h2', 'Cookies'),
                 ('p', "This site sets no cookie, uses no tracker and does not measure its "
                       "audience. There is therefore no consent banner: there is nothing to "
                       "consent to."),
                 ('p', "The site stores one single piece of information in your browser, in "
                       "session storage: your reading position, for the time of a language "
                       "switch, so that you are returned to the same place on the page. It is "
                       "erased as soon as it is read back, it never leaves your browser, and "
                       "it cannot identify you."),
             ]),
        dict(de=17, a=18, titre='Data collected through standard Internet technologies',
             raison="see conf-fr",
             blocs=[
                 ('h2', 'Third-party content, loaded only if you ask for it'),
                 ('p', "The site calls no third-party service when a page loads: no script, no "
                       "pixel, no redirect, no remote font. Two external contents load only "
                       "after you click, and that click is announced where it happens: the map "
                       "on the Contact page, provided by Google Maps, and the demonstration "
                       "booking calendar, provided by Microsoft Bookings. Until you click, "
                       "your browser contacts neither Google nor Microsoft. Once you do, those "
                       "providers receive your IP address and may set their own cookies, under "
                       "their respective policies."),
             ]),
        dict(de=19, a=20, titre='Data from mobile devices',
             raison="see conf-fr",
             blocs=[]),
        dict(de=26, a=26, titre='To analyze the volume and history',
             raison="voir conf-fr", blocs=[]),
        dict(de=40, a=41, titre='Data storage location and transfers',
             raison="see conf-fr",
             blocs=[
                 ('h2', 'Data storage location and transfers'),
                 ('p', "This site is a static site, with no database: it keeps nothing. It is "
                       "hosted on GitHub&nbsp;Pages (GitHub,&nbsp;Inc., a Microsoft company), "
                       "whose delivery network serves the pages from servers located in "
                       "several countries, including outside the European Union."),
                 ('p', "Requests sent from the contact form do not travel through the site: "
                       "they open your own mail application with the message prefilled, and "
                       "are sent only if you send them yourself. Newsletter sign-ups are "
                       "passed to Brevo (formerly Sendinblue), our processor for sending "
                       "newsletters."),
                 ('p', "<a href=\"https://q-leap.eu\">Q-LEAP SA</a> undertakes to inform you "
                       "immediately, insofar as we are legally entitled to do so, in the event "
                       "of a request from an administrative or judicial authority relating to "
                       "your data."),
             ]),
    ],
}

# Retouches ponctuelles, appliquées au corps assemblé, sous la forme
# (ancien, nouveau, nombre d'occurrences attendu, raison). Le compte est écrit et
# non deviné : une retouche qui ne correspond plus arrête le script.
RETOUCHES = {
    # LES CONDITIONS DE VENTE NE SONT AMENDÉES QUE SUR CE POINT, et il ne relève
    # pas de la migration : c'est un fait d'état civil de la société. Leur clause
    # de définitions donnait encore l'ancien siège, alors que le numéro RCS y est
    # le même (B.167.970) et que le PostalAddress des 23 pages, le foundingLocation
    # et les deux politiques de confidentialité disent Bertrange. Le pied de page
    # FRANÇAIS du live dit Bertrange lui aussi ; seul son pied de page anglais est
    # resté en arrière. Confirmé par le client le 2026-09-01.
    'cv-fr': [
        ("ayant son si\u00e8ge social \u00e0 L-1717 Luxembourg, 10 rue Mathias Hardt",
         "ayant son si\u00e8ge social \u00e0 L-8070 Bertrange, 10B rue des M\u00e9rovingiens", 1,
         "si\u00e8ge actuel ; l'ordre code postal puis rue est celui du document"),
    ],
    'cv-en': [
        ("having its registered office at L-1717 Luxembourg, 10 rue Mathias Hardt",
         "having its registered office at L-8070 Bertrange, 10B rue des M\u00e9rovingiens", 1,
         "voir cv-fr"),
    ],
    'conf-fr': [
        ("notamment lors de commandes et lors de la cr\u00e9ation d\u2019un compte client "
         "ou lors de votre inscription ou notre formulaire de contact",
         "notamment lors de votre inscription \u00e0 notre lettre d\u2019information ou "
         "de l\u2019envoi du formulaire de contact", 1,
         "il n'y a sur ce site ni commande ni compte client"),
        ("Certaines donn\u00e9es sont collect\u00e9es automatiquement du fait de vos "
         "actions sur le site",
         "Aucune autre donn\u00e9e n\u2019est collect\u00e9e automatiquement du fait de "
         "votre navigation", 1,
         "rien n'est collect\u00e9 automatiquement : ni cookie, ni mesure d'audience"),
        ("le site bot.q-leap.eu", "le site q-bot.eu", 1,
         "bot.q-leap.eu \u00e9tait l'adresse de pr\u00e9production du WordPress"),
        ('<time datetime="2025-07-07">Date de la derni\u00e8re mise \u00e0 jour : '
         '7 juillet 2025',
         '<time datetime="2026-09-01">Date de la derni\u00e8re mise \u00e0 jour : '
         '1er septembre 2026', 1,
         "le document est modifi\u00e9 aujourd'hui : sa date doit le dire"),
    ],
    'priv-en': [
        ("registered office at 10 rue Mathias Hardt L-1717 Luxembourg",
         "registered office at 10B rue des M\u00e9rovingiens L-8070 Bertrange", 1,
         "l'adresse du si\u00e8ge, que la version fran\u00e7aise et les donn\u00e9es "
         "structur\u00e9es du site donnent correctement"),
        ("in particular when you place an order, create a customer account, register or "
         "use our contact form",
         "in particular when you subscribe to our newsletter or use our contact form", 1,
         "voir conf-fr"),
        ("Q-LEAP NV", "Q-LEAP SA", 2,
         "la soci\u00e9t\u00e9 est une SA, comme le dit le reste de la m\u00eame page. "
         "Deux et non trois : la troisi\u00e8me occurrence est dans le bloc 41, r\u00e9\u00e9crit "
         "juste au-dessus par l'amendement sur le lieu de stockage."),
        ("That\u2019s why we process as little data as possible. That\u2019s why we "
         "process as little data as possible.",
         "That\u2019s why we process as little data as possible.", 1,
         "phrase dupliqu\u00e9e dans le texte du live"),
        ("Some data is collected automatically as a result of your actions on the site",
         "No other data is collected automatically as a result of your browsing", 1,
         "voir conf-fr"),
        ("the bot.q-leap.eu website", "the q-bot.eu website", 1, "voir conf-fr"),
        ('<time datetime="2024-06-11">Last update: June, 11th 2024',
         '<time datetime="2026-09-01">Last update: 1 September 2026', 1,
         "voir conf-fr, et cela referme au passage l'ann\u00e9e de retard de l'anglais"),
    ],
}


def extraire(chemin, debut, fin):
    """Découpe un bloc entre deux marqueurs dans une page existante du site."""
    s = io.open(os.path.join(RACINE, chemin), encoding='utf-8').read()
    a = s.index(debut)
    b = s.index(fin, a) + len(fin)
    return s[a:b]


def reecrire_liens(html, prof):
    p = '../' * prof
    for vieux, neuf in LIENS.items():
        html = html.replace(f'href="{vieux}"', 'href="' + neuf.format(p=p) + '"')
    return html


def profondeur_plus_un(html):
    """Ajoute un niveau à tous les chemins RELATIFS de l'habillage extrait.

    Même fonction que dans « gen-guides.py », et pour la même raison : on ne
    réécrit pas l'habillage à la main, on préfixe « ../ », ce qui marche
    uniformément (« x.html » devient « ../x.html », « ../assets/ » devient
    « ../../assets/ »). Les adresses absolues, les ancres, « mailto: » et
    « tel: » sont laissées telles quelles, et le JSON-LD n'est pas touché
    puisque seuls les attributs « href » et « src » le sont.
    """
    def remplace(m):
        att, v = m.group(1), m.group(2)
        if re.match(r'^(https?:|//|mailto:|tel:|data:|#)', v):
            return m.group(0)
        # NORMALISÉ, sinon « ./ » (la forme des liens vers l'accueil depuis le
        # 2026-08-26) donnerait « .././ ». La barre finale est réintroduite :
        # elle distingue un répertoire d'un fichier, et « normpath » la mange.
        nouveau = posixpath.normpath('../' + v) + ('/' if v.endswith('/') else '')
        return att + '="' + nouveau + '"'
    return re.sub(r'\b(href|src)="([^"]*)"', remplace, html)


def est_titre(bloc):
    """Un <p> qui ne contient QUE du gras est un titre déguisé, pas un paragraphe."""
    h = bloc['html'].strip()
    m = re.fullmatch(r'<(strong|b)>(.*)</\1>', h, re.S) or \
        re.fullmatch(r'<span style="font-weight: ?[6-9]00;?">(.*)</span>', h, re.S)
    return bool(m)


def insecable(html):
    """Entoure « Q-Bot » de la classe qui l'empêche de se couper en fin de ligne.

    Posée sur tout le site le 2026-08-28. Le texte du relevé ne l'a pas, donc une
    régénération la perdait sur les 36 occurrences des deux politiques.
    ATTENTION : jamais À L'INTÉRIEUR d'une balise (un « href » peut contenir le
    mot), d'où le découpage sur les chevrons. Et jamais dans un conteneur flex,
    piège du 2026-08-31 — ici tout est dans « .article-body », qui est un bloc.
    """
    out = []
    for i, part in enumerate(re.split(r'(<[^>]*>)', html)):
        out.append(part if i % 2 else
                   re.sub(r'\bQ-Bot\b', '<span class="nb">Q-Bot</span>', part))
    return ''.join(out)


def amendements(cle):
    """Les intervalles amendés, indexés par leur premier bloc."""
    return {a['de']: a for a in SECTIONS_AMENDEES.get(cle, [])}


def corps(page):
    """Reconstruit le corps de la page. C'est ici que le balisage est réparé."""
    cle = page['cle']
    debut, fin = page['bornes'][0] + 1, page['bornes'][1]
    amend, saute = amendements(cle), set()
    for a in amend.values():
        # L'ASSERTION EST TOUTE LA SÛRETÉ DU DISPOSITIF : si le live est relevé à
        # nouveau et que la section visée a bougé, on s'arrête ici au lieu de
        # remplacer le mauvais paragraphe ou de laisser tomber l'amendement.
        vu = SRC[cle][a['de']]['txt'].strip()
        assert vu.startswith(a['titre']), \
            f"{cle}[{a['de']}] : « {vu[:60]} » n'est pas « {a['titre']} »"
        saute.update(range(a['de'], a['a'] + 1))

    out, liste, vu_chapeau = [], [], False
    for i in range(debut, fin):
        if i in amend:
            # UNE SUPPRESSION SEULE NE COUPE PAS LA LISTE QUI L'ENTOURE : on ne
            # ferme le <ul> en cours que s'il y a quelque chose à écrire à la
            # place. Sinon un item retiré au milieu d'une liste la scindait en
            # deux, ce qui ne se voit pas dans le texte rendu mais casse la
            # sémantique et la puce.
            if amend[i]['blocs']:
                if liste:
                    out.append('      <ul>\n' + '\n'.join(liste) + '\n      </ul>')
                    liste = []
                for tag, txt in amend[i]['blocs']:
                    out.append(f'      <{tag}>{txt}</{tag}>')
            continue
        if i in saute:
            continue
        b = SRC[cle][i]
        if b['tag'] == 'li':
            liste.append('        <li>' + reecrire_liens(b['html'], page['prof']) + '</li>')
            continue
        if liste:
            out.append('      <ul>\n' + '\n'.join(liste) + '\n      </ul>')
            liste = []

        html = reecrire_liens(b['html'], page['prof'])
        txt = b['txt'].strip()

        # le chapeau (premier h5 en gras) est déjà remonté dans le page-hero
        if b['tag'] == 'h5' and not vu_chapeau:
            vu_chapeau = True
            continue
        if txt in DATES_ISO:
            out.append(f'      <p class="legal-date"><time datetime="{DATES_ISO[txt]}">'
                       f'{txt}</time></p>')
        elif b['tag'] == 'h4':                       # section de premier niveau
            out.append(f'      <h2>{html}</h2>')
        elif b['tag'] == 'h5':                       # section de second niveau
            out.append(f'      <h3>{html}</h3>')
        elif b['tag'] == 'p' and est_titre(b):       # titre déguisé en paragraphe
            out.append(f'      <h2>{txt}</h2>')
        else:
            out.append('      <p>' + html.replace('\n', '<br>') + '</p>')
    if liste:
        out.append('      <ul>\n' + '\n'.join(liste) + '\n      </ul>')
    html = '\n'.join(out)

    for ancien, neuf, attendu, _raison in RETOUCHES.get(cle, []):
        n = html.count(ancien)
        assert n == attendu, \
            f"{cle} : « {ancien[:50]} » trouvé {n} fois, attendu {attendu}"
        html = html.replace(ancien, neuf)
    return insecable(html)


def chapeau(page):
    """Le premier h5 en gras du live : c'est l'accroche de la page."""
    for b in SRC[page['cle']][page['bornes'][0]:page['bornes'][1]]:
        if b['tag'] == 'h5':
            return b['txt'].strip()
    return ''


def titre_h1(page):
    return SRC[page['cle']][page['bornes'][0]]['txt'].strip()


for page in PAGES:
    p = '../' * page['prof']
    g = page['gabarit']
    # LES BORNES SONT STRUCTURELLES, PAS DES COMMENTAIRES. « a-propos.html » porte
    # ses bandeaux « ======= NAVIGATION ======= », « en/about.html » non : un
    # découpage par commentaire marchait sur une langue et échouait sur l'autre.
    nav = extraire(g, '<header class="nav"', '</header>')
    pied = extraire(g, '<footer class="footer"', '</footer>')
    cta = extraire(g, '<section class="section section--dark" aria-labelledby="cta-',
                   '</section>').replace('cta-about-title', 'cta-legal-title')
    orga = extraire(g, '<script type="application/ld+json">', '</script>')

    # LA PROFONDEUR SE CALCULE, elle ne se remplace plus. Les deux gabarits sont
    # désormais « a-propos.html » (racine) et « en/about.html » (dans en/) : dans
    # les deux cas la page légale vit UN CRAN plus bas, donc un même « +1 »
    # convient. L'ancienne version remplaçait un préfixe littéral, ce qui
    # supposait un gabarit déjà en profondeur, et elle visait deux articles de
    # blog SUPPRIMÉS le 2026-08-28 : ce script était mort depuis, sans que rien
    # ne le dise. Le garde-fou de fin vérifie que chaque chemin produit existe.
    nav, pied, cta = (profondeur_plus_un(nav), profondeur_plus_un(pied),
                      profondeur_plus_un(cta))

    # LE GABARIT EST UNE PAGE DU SITE, DONC SON PIED MARQUE SA PROPRE ENTRÉE COMME
    # COURANTE. Sans cela, « À propos » arrivait sur les quatre pages légales en
    # texte mort au lieu d'un lien. On lui rend son lien, qui est le gabarit
    # lui-même. Même précaution que dans « gen-guides.py ».
    soi = '../' + os.path.basename(g)
    for etiquette in re.findall(r'<span aria-current="page">([^<]*)</span>', pied):
        pied = pied.replace(f'<span aria-current="page">{etiquette}</span>',
                            f'<a href="{soi}">{etiquette}</a>')

    # le sélecteur de langue pointe la page légale de l'autre langue. Le motif ne
    # nomme plus une page précise : dans la barre, le seul « href » suivi d'un
    # « hreflang » est celui du sélecteur.
    nav = re.sub(r'href="[^"]*"(?=\s+hreflang)', f'href="{page["alt_rel"]}"', nav)

    fr = page['lang'] == 'fr'
    T = dict(skip='Aller au contenu principal' if fr else 'Skip to main content',
             fil_accueil='Accueil' if fr else 'Home',
             fil_label="Fil d'Ariane" if fr else 'Breadcrumb',
             cta_label="Démonstration" if fr else 'Demonstration',
             cta_h2='Vous souhaitez en savoir plus&nbsp;?' if fr else 'Would you like to know more?',
             cta_h3='Réservez une démo' if fr else 'Book a demo',
             cta_btn='Prendre rendez-vous' if fr else 'Make an appointment',
             maj='Migré depuis' if fr else 'Migrated from')

    # L'ACCUEIL DU FIL EST CELUI DE LA LANGUE, PAS LA RACINE. Les quatre pages
    # légales vivent un cran sous leur racine de langue (`conditions-vente/` en
    # français, `en/privacy/` en anglais) : `../` est donc l'accueil de la langue
    # dans les deux cas, là où `{p}` vaut `../../` en anglais et renvoyait le
    # lecteur anglais sur l'accueil FRANÇAIS. Relevé le 2026-08-26.
    fil_url = '../'
    hreflang_fr = page['url'] if fr else page['alt']
    hreflang_en = page['alt'] if fr else page['url']

    html = f"""<!DOCTYPE html>
<html lang="{page['lang']}" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{page['titre']}</title>
  <meta name="description" content="{page['desc']}">
  <!-- PRÉ-LANCEMENT — à retirer le jour de la mise en ligne. Le site entier est
       hors index le temps de la mise au point ; le pendant de cette balise est le
       « Disallow: / » de robots.txt. Chercher « PRÉ-LANCEMENT » pour tout retrouver. -->
  <meta name="robots" content="noindex, nofollow">
  <link rel="canonical" href="{page['url']}">
  <link rel="alternate" hreflang="fr" href="{hreflang_fr}">
  <link rel="alternate" hreflang="en" href="{hreflang_en}">
  <link rel="alternate" hreflang="x-default" href="{hreflang_fr}">

  <!-- Open Graph & Twitter Card -->
  <meta property="og:title" content="{page['titre']}">
  <meta property="og:description" content="{page['desc']}">
  <meta property="og:url" content="{page['url']}">
  <meta property="og:type" content="website">
  <meta property="og:image" content="https://q-bot.eu/assets/img/qbot-og.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{'Le boîtier Q-Bot sur un bureau, un smartphone Android inséré dans son socle, l&#39;interface web à l&#39;écran' if fr else 'The Q-Bot enclosure on a desk, an Android smartphone docked in its cradle, the web interface on screen'}">
  <meta property="og:locale" content="{'fr_FR' if fr else 'en_GB'}">
  <meta property="og:site_name" content="Q-Bot">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{page['titre']}">
  <meta name="twitter:description" content="{page['desc']}">
  <meta name="twitter:image" content="https://q-bot.eu/assets/img/qbot-og.jpg">
  <!-- Favicon -->
  <link rel="icon" href="{p}assets/img/favicon-32.png" sizes="32x32" type="image/png">
  <link rel="icon" href="{p}assets/img/favicon.png" sizes="192x192" type="image/png">
  <link rel="apple-touch-icon" href="{p}assets/img/apple-touch-icon.png">
  <meta name="theme-color" content="#000000">

  <!-- PAS DE GOOGLE FONTS. Roboto est servie par le site, en local : « style.css »
       déclare ses @font-face sur « assets/fonts/roboto-latin.woff2 ». Les trois
       balises qui étaient ici venaient du WordPress et ne servaient à rien : trois
       requêtes vers deux origines tierces, bloquantes au rendu, pour une police
       déjà présente, et l'IP du visiteur qui part chez Google SUR LA PAGE DE
       POLITIQUE DE CONFIDENTIALITÉ. Retirées le 2026-08-31, relevé RosoAI n°5.

       ET AUCUNE EMPREINTE ÉCRITE À LA MAIN. Ce gabarit en portait une, périmée de
       plusieurs jours : une régénération aurait réintroduit la panne de cache du
       2026-08-25. Le chemin est nu, et « tools/bump-assets » y pose l'empreinte
       réelle. NE PAS écrire ici un exemple de chemin versionné : ce script-là
       remplace le paramètre de version PARTOUT dans le fichier, commentaires
       compris, et rendrait cette phrase illisible. -->
  <link rel="stylesheet" href="{p}assets/css/style.css">
  {orga}
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{ "@type": "ListItem", "position": 1, "name": "{T['fil_accueil']}", "item": "{'https://q-bot.eu/' if fr else 'https://q-bot.eu/en/'}" }},
      {{ "@type": "ListItem", "position": 2, "name": "{page['fil']}", "item": "{page['url']}" }}
    ]
  }}
  </script>
</head>
<body>

<a href="#main" class="skip-nav">{T['skip']}</a>

{nav}

<!-- ======= PAGE HERO ======= -->
<section id="main" class="page-hero" aria-labelledby="legal-title">
  <div class="container">
    <span class="section-label">{page['label']}</span>
    <h1 id="legal-title">{titre_h1(page)}</h1>
    <p>{chapeau(page)}</p>
  </div>
</section>

<main>
<!-- ======= TEXTE LÉGAL =======
     Repris mot pour mot de {page['url']}. Le seul écart avec le live est le
     balisage : ses sous-titres, écrits en <p><strong> par Elementor, sont ici
     de vrais titres. Ne pas reformuler ce texte : il est juridique, et sa
     source est le live. Pour reprendre une mise à jour, relancer
     tools/fetch-legal.py puis tools/gen-legal.py. -->
<section class="section" aria-label="{page['fil']}">
  <div class="container">
    <div class="article-body">
{corps(page)}
    </div>
  </div>
</section>

<!-- ======= CONTACT CTA ======= -->
{cta}
</main>

{pied}

<!-- Chemin nu : « tools/bump-assets » y pose l'empreinte réelle. Une
     empreinte écrite à la main ici se périme et rejoue la panne de cache
     du 2026-08-25. -->
<script src="{p}assets/js/main.js" defer></script>
</body>
</html>
"""
    dest = os.path.join(RACINE, page['sortie'])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    io.open(dest, 'w', encoding='utf-8').write(html)
    print(f"  écrit {page['sortie']:<48} {len(html):>7} octets")
