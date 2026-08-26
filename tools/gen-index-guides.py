#!/usr/bin/env python3
"""Réécrit la liste de cartes des deux index de blog depuis les pages elles-mêmes.

POURQUOI UN SCRIPT. Onze cartes écrites à la main dans deux langues divergent du
contenu qu'elles annoncent dès la première correction de titre. Ici, le titre,
l'accroche et le temps de lecture sont RELEVÉS dans la page cible : une carte ne
peut pas mentir sur ce qu'elle ouvre.

L'ORDRE EST VOULU : les guides d'abord, la page pilier en tête, puis les billets
datés. Les guides sont le contenu stratégique ; les billets de 2023 portent tous
une note disant que le produit a évolué depuis, et ils ont leur place, en dessous.

    python3 tools/gen-index-guides.py
    python3 tools/bump-assets.py     # ensuite, toujours
"""

import io
import os
import re

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# L'ordre de la grille, et la vignette de chacun. Les vignettes sont des visuels
# du produit déjà présents dans le dépôt : aucune image n'est inventée pour
# l'occasion, et la vignette carrée recadre au centre.
ORDRE = [
    # (slug FR, slug EN, image FR, image EN, étiquette FR, étiquette EN)
    ('automatiser-2fa-dans-vos-tests.html', 'automate-2fa-in-your-tests.html',
     'qbot-specs.jpg', 'qbot-specs.jpg', 'Guide de référence', 'Reference guide'),
    ('automatiser-authentification-luxtrust.html', 'automate-luxtrust-authentication.html',
     'qbot-photo-dock.jpg', 'qbot-photo-dock.jpg', 'Guide', 'Guide'),
    ('desactiver-2fa-en-test.html', 'disable-2fa-in-testing.html',
     'blog/post-2fa.webp', 'blog/post-2fa.webp', 'Guide', 'Guide'),
    ('automatiser-2fa-sans-cle-secrete.html', 'automate-2fa-without-shared-secret.html',
     'qbot-interface.jpg', 'qbot-interface-en.jpg', 'Guide', 'Guide'),
    ('tester-2fa-appareil-reel.html', 'test-2fa-real-device.html',
     'qbot-photo-poste.jpg', 'qbot-photo-poste.jpg', 'Comparatif', 'Comparison'),
    ('securite-conformite-donnees-de-test.html', 'security-compliance-test-data.html',
     'blog/post-tokens.webp', 'blog/post-tokens.webp', 'Guide', 'Guide'),
    ('campagnes-de-nuit-bloquees-au-login.html', 'night-runs-blocked-at-login.html',
     'qbot-gen-actuelle.webp', 'qbot-gen-actuelle.webp', 'Guide', 'Guide'),
    ('cout-etape-manuelle-authentification.html', 'cost-of-manual-authentication-step.html',
     'qbot-proto-1-boitier.webp', 'qbot-proto-1-boitier.webp', 'Guide', 'Guide'),
]

# Les billets datés, conservés tels quels sous les guides.
BILLETS_FR = [('innovation-merkur.html', 'blog/post-merkur.webp', 'Presse', 'Mars 2023'),
              ('authentification-deux-facteurs.html', 'blog/post-2fa.webp', 'Sécurité', 'Mars 2023')]
BILLETS_EN = [('innovation-merkur.html', 'blog/post-merkur.webp', 'Press', 'March 2023'),
              ('two-factor-authentication.html', 'blog/post-2fa.webp', 'Security', 'March 2023')]

FLECHE = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
          'stroke-width="2.5" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7"/></svg>')


def relève(chemin):
    """Titre, accroche et temps de lecture, RELEVÉS dans la page cible.

    Les guides et les billets datés n'ont pas la même structure : un guide porte
    `<h1 id="page-title">` et un `<main id="main">`, un billet porte un h1 nu et un
    `<main class="article-body">`. On accepte les deux formes plutôt que de
    supposer la première, sinon la fonction casse sur les billets.
    """
    s = io.open(os.path.join(RACINE, chemin), encoding='utf-8').read()
    m = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
    assert m, (chemin, 'aucun h1')
    titre = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    desc = re.search(r'<meta name="description" content="(.*?)">', s).group(1)
    m2 = re.search(r'<main[^>]*>(.*?)</main>', s, re.S)
    mots = len(re.sub(r'<[^>]+>', ' ', m2.group(1)).split()) if m2 else 400
    return titre, desc, max(2, round(mots / 200))


def carte(lien, img, etiquette, titre, accroche, meta, lire, prefixe):
    return f'''      <article class="blog-card reveal" role="listitem">
        <img src="{prefixe}assets/img/{img}" alt="{titre}" width="768" height="768" loading="lazy">
        <div class="blog-card__content">
          <span class="blog-card__tag">{etiquette}</span>
          <h3 class="blog-card__title"><a href="blog/{lien}">{titre}</a></h3>
          <p class="blog-card__excerpt">{accroche}</p>
          <div class="blog-card__meta">
            <span>{meta}</span>
            <span>{lire}</span>
          </div>
          <a href="blog/{lien}" class="blog-card__read-more">
            {"Lire le guide" if prefixe == "" else "Read the guide"} {FLECHE}
          </a>
        </div>
      </article>
'''


def construire(langue):
    fr = (langue == 'fr')
    prefixe = '' if fr else '../'
    dossier = 'blog/' if fr else 'en/blog/'
    out = []
    for slug_fr, slug_en, img_fr, img_en, et_fr, et_en in ORDRE:
        slug = slug_fr if fr else slug_en
        titre, accroche, mn = relève(dossier + slug)
        meta = ('Mis à jour le 26 août 2026' if fr else 'Updated 26 August 2026')
        out.append(carte(slug, img_fr if fr else img_en, et_fr if fr else et_en,
                         titre, accroche, meta, f'{mn} min', prefixe))
    for slug, img, et, date in (BILLETS_FR if fr else BILLETS_EN):
        titre, accroche, mn = relève(dossier + slug)
        c = carte(slug, img, et, titre, accroche, date, f'{mn} min', prefixe)
        # un billet daté n'est pas un guide : le libellé du lien le dit
        out.append(c.replace('Lire le guide', "Lire l'article").replace('Read the guide', 'Read the article'))
    return '\n'.join(out)


for page, langue in (('blog.html', 'fr'), ('en/blog.html', 'en')):
    chemin = os.path.join(RACINE, page)
    s = io.open(chemin, encoding='utf-8').read()
    debut = s.index('<div class="blog__grid" role="list">') + len('<div class="blog__grid" role="list">')
    fin = s.index('\n    </div>', debut)
    neuf = s[:debut] + '\n\n' + construire(langue) + s[fin:]
    # garde-fou : chaque lien de carte doit désigner un fichier réel
    base = os.path.dirname(chemin)
    for h in re.findall(r'<a href="(blog/[^"]+)"', neuf):
        cible = os.path.normpath(os.path.join(base, h))
        assert os.path.exists(cible), (page, 'lien de carte cassé : ' + h)
    io.open(chemin, 'w', encoding='utf-8').write(neuf)
    print('  %-14s %d cartes' % (page, neuf.count('class="blog-card reveal"')))
