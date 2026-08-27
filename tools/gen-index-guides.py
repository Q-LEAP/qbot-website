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
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vignettes_guides as vg
import re

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# L'ordre de la grille, et la vignette de chacun. Les vignettes sont des visuels
# du produit déjà présents dans le dépôt : aucune image n'est inventée pour
# l'occasion, et la vignette carrée recadre au centre.
ORDRE = [
    # (slug FR, slug EN, base de la vignette, étiquette FR, étiquette EN)
    #
    # Le fichier et la description d'image viennent de `vignettes_guides.py`, qui est
    # la source unique : la même vignette sert ici, sur la carte, ET dans le corps du
    # guide. Deux tables se seraient désynchronisées à la première correction de
    # texte alternatif, et personne ne l'aurait vu.
    ('automatiser-2fa-dans-vos-tests.html', 'automate-2fa-in-your-tests.html',
     'guides/familles-2fa', 'Guide de référence', 'Reference guide'),
    ('automatiser-authentification-luxtrust.html', 'automate-luxtrust-authentication.html',
     'qbot-photo-dock', 'Guide', 'Guide'),
    ('desactiver-2fa-en-test.html', 'disable-2fa-in-testing.html',
     'guides/trois-voies', 'Guide', 'Guide'),
    ('automatiser-2fa-sans-cle-secrete.html', 'automate-2fa-without-shared-secret.html',
     'guides/avec-sans-cle', 'Guide', 'Guide'),
    ('tester-2fa-appareil-reel.html', 'test-2fa-real-device.html',
     'qbot-photo-poste', 'Comparatif', 'Comparison'),
    ('securite-conformite-donnees-de-test.html', 'security-compliance-test-data.html',
     'guides/rien-ne-sort', 'Guide', 'Guide'),
    ('campagnes-de-nuit-bloquees-au-login.html', 'night-runs-blocked-at-login.html',
     'guides/campagne-bute', 'Guide', 'Guide'),
    ('cout-etape-manuelle-authentification.html', 'cost-of-manual-authentication-step.html',
     'guides/le-calcul', 'Guide', 'Guide'),
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
    # LA DATE EST LUE DANS LA PAGE, JAMAIS ÉCRITE ICI. Elle l'était, et elle s'est
    # périmée dès la première retouche des guides : la carte annonçait le 26 quand
    # la page disait le 27. Même principe que le titre et l'accroche juste au-dessus,
    # et que le `lastmod` du plan de site dérivé de son fichier.
    d = re.search(r'<p class="guide-date">.*?<time datetime="[^"]*">(.*?)</time>', s, re.S)
    return titre, desc, max(2, round(mots / 200)), (d.group(1) if d else None)


def carte(lien, img, etiquette, titre, accroche, meta, lire, prefixe, alt=None, dim=(768, 768)):
    return f'''      <article class="blog-card reveal" role="listitem">
        <img src="{prefixe}assets/img/{img}" alt="{alt or titre}" width="{dim[0]}" height="{dim[1]}" loading="lazy">
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
    for slug_fr, slug_en, base, et_fr, et_en in ORDRE:
        slug = slug_fr if fr else slug_en
        titre, accroche, mn, maj = relève(dossier + slug)
        assert maj, f'{slug} ne porte pas de date de mise à jour lisible'
        meta = ('Mis à jour le ' if fr else 'Updated ') + maj
        out.append(carte(slug, vg.fichier(base, langue), et_fr if fr else et_en,
                         titre, accroche, meta, f'{mn} min', prefixe,
                         vg.alt(base, langue), vg.dimensions(base)))
    for slug, img, et, date in (BILLETS_FR if fr else BILLETS_EN):
        titre, accroche, mn, _ = relève(dossier + slug)
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
