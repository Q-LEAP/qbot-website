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

CE QUI EST REPRIS À L'IDENTIQUE : chaque mot. Le texte n'est jamais réécrit,
jamais résumé, jamais traduit. Le contrôle de non-régression compare le texte
rendu de nos pages à celui du live, bloc par bloc.

CE QUI CHANGE, ET SEULEMENT CELA :
  — le BALISAGE. Le live écrit ses sous-titres en `<p><strong>…</strong></p>`,
    un artefact d'Elementor. Ce sont des titres : ils deviennent des `<h2>`.
    Les mots ne changent pas, la hiérarchie devient valide et citable.
  — les LIENS INTERNES, repointés sur nos pages locales, et `http://www.q-leap.eu`
    passé en `https://q-leap.eu` (même cible, sans contenu mixte).
  — l'HABILLAGE : notre en-tête, notre pied de page, notre fil d'Ariane.

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
import re

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = json.load(io.open(os.path.join(RACINE, 'tools/legal-source.json'), encoding='utf-8'))

# ── Les quatre pages. `bornes` délimite le contenu dans le relevé : du titre de
#    la page (exclu, il devient le <h1>) au bloc d'appel à l'action du live.
PAGES = [
    dict(cle='cv-fr', sortie='conditions-vente/index.html', lang='fr', prof=1,
         bornes=(6, 176), gabarit='blog/innovation-merkur.html',
         url='https://q-bot.eu/conditions-vente/',
         alt='https://q-bot.eu/en/terms-and-conditions-of-sale/',
         alt_rel='../en/terms-and-conditions-of-sale/',
         titre='Conditions générales de vente | Q-Bot by Q-Leap',
         desc="Conditions générales de vente de Q-Bot, robot d'automatisation de la 2FA, "
              "édité par Q-Leap S.A. au Luxembourg.",
         label='Mentions légales', fil='Conditions de vente'),
    dict(cle='conf-fr', sortie='confidentialite/index.html', lang='fr', prof=1,
         bornes=(6, 56), gabarit='blog/innovation-merkur.html',
         url='https://q-bot.eu/confidentialite/',
         alt='https://q-bot.eu/en/privacy/', alt_rel='../en/privacy/',
         titre='Confidentialité des données | Q-Bot by Q-Leap',
         desc="Politique de confidentialité de Q-Bot et de l'application Q-Bot Mobile : "
              "données collectées, finalités, vos droits, conservation.",
         label='Mentions légales', fil='Confidentialité'),
    dict(cle='cv-en', sortie='en/terms-and-conditions-of-sale/index.html', lang='en', prof=2,
         bornes=(6, 176), gabarit='en/blog/innovation-merkur.html',
         url='https://q-bot.eu/en/terms-and-conditions-of-sale/',
         alt='https://q-bot.eu/conditions-vente/', alt_rel='../../conditions-vente/',
         titre='General terms and conditions | Q-Bot by Q-Leap',
         desc='General terms and conditions of sale for Q-Bot, the 2FA test automation robot '
              'published by Q-Leap S.A. in Luxembourg.',
         label='Legal', fil='Terms and conditions'),
    dict(cle='priv-en', sortie='en/privacy/index.html', lang='en', prof=2,
         bornes=(6, 56), gabarit='en/blog/innovation-merkur.html',
         url='https://q-bot.eu/en/privacy/',
         alt='https://q-bot.eu/confidentialite/', alt_rel='../../confidentialite/',
         titre='Data privacy | Q-Bot by Q-Leap',
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


def est_titre(bloc):
    """Un <p> qui ne contient QUE du gras est un titre déguisé, pas un paragraphe."""
    h = bloc['html'].strip()
    m = re.fullmatch(r'<(strong|b)>(.*)</\1>', h, re.S) or \
        re.fullmatch(r'<span style="font-weight: ?[6-9]00;?">(.*)</span>', h, re.S)
    return bool(m)


def corps(page):
    """Reconstruit le corps de la page. C'est ici que le balisage est réparé."""
    blocs = SRC[page['cle']][page['bornes'][0] + 1:page['bornes'][1]]
    out, liste, vu_chapeau = [], [], False
    for b in blocs:
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
    return '\n'.join(out)


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
    nav = extraire(g, '<!-- ======= NAVIGATION ======= -->', '</header>')
    pied = extraire(g, '<!-- ======= FOOTER ======= -->', '</footer>')
    orga = extraire(g, '<script type="application/ld+json">', '</script>')

    # profondeur : les gabarits de blog sont à 1 (fr) et 2 (en), comme nos pages
    if page['prof'] == 2:
        nav, pied = nav.replace('../../', '{{P}}'), pied.replace('../../', '{{P}}')
    else:
        nav, pied = nav.replace('../', '{{P}}'), pied.replace('../', '{{P}}')
    nav, pied = nav.replace('{{P}}', p), pied.replace('{{P}}', p)

    # le sélecteur de langue pointe la page légale de l'autre langue
    nav = re.sub(r'href="[^"]*(?:en/blog/innovation-merkur\.html|blog/innovation-merkur\.html)"'
                 r'(?=\s+hreflang)', f'href="{page["alt_rel"]}"', nav)
    # les liens légaux du pied de page deviennent internes : plus de nouvel onglet
    pied = (pied
            .replace('<a href="https://q-bot.eu/conditions-vente/" target="_blank" rel="noopener">',
                     f'<a href="{p}conditions-vente/">')
            .replace('<a href="https://q-bot.eu/confidentialite/" target="_blank" rel="noopener">',
                     f'<a href="{p}confidentialite/">')
            .replace('<a href="https://q-bot.eu/en/terms-and-conditions-of-sale/" target="_blank" rel="noopener">',
                     f'<a href="{p}en/terms-and-conditions-of-sale/">' if page['prof'] == 1
                     else f'<a href="{p}en/terms-and-conditions-of-sale/">')
            .replace('<a href="https://q-bot.eu/en/privacy/" target="_blank" rel="noopener">',
                     f'<a href="{p}en/privacy/">'))

    fr = page['lang'] == 'fr'
    T = dict(skip='Aller au contenu principal' if fr else 'Skip to main content',
             fil_accueil='Accueil' if fr else 'Home',
             fil_label="Fil d'Ariane" if fr else 'Breadcrumb',
             cta_label="Passez à l'action" if fr else 'Take action',
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
  <meta property="og:site_name" content="Q-Bot by Q-Leap">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{page['titre']}">
  <meta name="twitter:description" content="{page['desc']}">
  <meta name="twitter:image" content="https://q-bot.eu/assets/img/qbot-og.jpg">
  <!-- Favicon -->
  <link rel="icon" href="{p}assets/img/favicon-32.png" sizes="32x32" type="image/png">
  <link rel="icon" href="{p}assets/img/favicon.png" sizes="192x192" type="image/png">
  <link rel="apple-touch-icon" href="{p}assets/img/apple-touch-icon.png">
  <meta name="theme-color" content="#000000">

  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,300;0,400;0,500;0,700;1,400&display=swap" rel="stylesheet">

  <link rel="stylesheet" href="{p}assets/css/style.css?v=2026.46-08-29b">
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

<!-- ======= BREADCRUMB ======= -->
<div class="breadcrumb">
  <div class="container">
    <ol class="breadcrumb__list" aria-label="{T['fil_label']}">
      <li><a href="{fil_url}">{T['fil_accueil']}</a></li>
      <li><span aria-hidden="true">›</span></li>
      <li><span aria-current="page">{page['fil']}</span></li>
    </ol>
  </div>
</div>

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
<section class="section section--dark" aria-labelledby="cta-legal-title">
  <div class="container cta-block">
    <span class="section-label" style="color:var(--teal);">{T['cta_label']}</span>
    <h2 class="section-title" id="cta-legal-title" style="color:var(--white); margin-bottom:16px;">
      {T['cta_h2']}
    </h2>
    <h3 style="font-size:1.5rem; font-weight:600; margin-bottom:32px; color:var(--teal);">{T['cta_h3']}</h3>
    <a href="{p}contact.html" class="btn btn--primary btn--lg">{T['cta_btn']}</a>
  </div>
</section>
</main>

{pied}

<script src="{p}assets/js/main.js?v=2026.19-08-23" defer></script>
</body>
</html>
"""
    dest = os.path.join(RACINE, page['sortie'])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    io.open(dest, 'w', encoding='utf-8').write(html)
    print(f"  écrit {page['sortie']:<48} {len(html):>7} octets")
