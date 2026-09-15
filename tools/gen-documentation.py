#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La page « Documentation technique », dans les deux langues.

    python3 tools/gen-documentation.py
    node tools/bump-assets.mjs

DEUX PAGES ÉCRITES L'UNE APRÈS L'AUTRE DIVERGENT : c'est la leçon que le dépôt a
déjà payée sur les pages de cas d'usage et les pages légales. Le texte vit dans
« doc_contenu.py », le gabarit ici, et ce script VÉRIFIE que les deux langues ont
les mêmes sections.

LA PAGE EST CLONÉE DEPUIS SA PAGE DONNEUSE, elle n'est pas écrite de zéro : on
reprend « caracteristiques.html » (racine) et « en/technical-specs.html », on
remplace l'en-tête de page et le contenu de <main>. La barre de navigation, le
pied de page, les polices, les scripts et le bloc Organization sont donc
exactement ceux du reste du site, et le RESTENT si l'un d'eux change — il suffit
de relancer. Les deux pages vivent à la MÊME profondeur que leur donneuse, donc
aucun chemin relatif n'est à réécrire (contrairement aux guides du blog).

LES CINQ EXEMPLES D'APPEL SONT EXTRAITS, PAS RETAPÉS. Ils viennent de la section
API de la page donneuse, où ils vivaient depuis le 2026-09-09. On ne retape pas
une chaîne existante d'un fichier, on l'extrait : c'est la règle du dépôt, et
elle vaut d'autant plus pour 140 lignes de code échappé en entités HTML.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import doc_contenu as C  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent

# PUBLICATION ET MODIFICATION SONT DEUX DATES : estampiller une date de
# modification sur un contenu qui n'a pas changé est le signal trompeur contre
# lequel l'audit RosoAI met en garde.
PUBLIE, MODIFIE = '2026-09-14', '2026-09-14'

PAGES = [
    dict(lang='fr', sortie='documentation.html', donneuse='caracteristiques.html',
         url='https://q-bot.eu/documentation.html',
         alt='https://q-bot.eu/en/documentation.html', alt_rel='en/documentation.html'),
    dict(lang='en', sortie='en/documentation.html', donneuse='en/technical-specs.html',
         url='https://q-bot.eu/en/documentation.html',
         alt='https://q-bot.eu/documentation.html', alt_rel='../documentation.html'),
]

COCHE = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
         '<polyline points="4,12 9,17 20,6"/></svg>')
FLECHE = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
          'stroke-width="2" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7"/></svg>')


def extraire(t, debut, fin):
    """Le fragment de `debut` (inclus) à `fin` (inclus), bornes littérales."""
    d = t.index(debut)
    f = t.index(fin, d) + len(fin)
    return t[d:f]


def bloc_faits(items):
    li = '\n'.join(f'      <li>{COCHE}<span>{x}</span></li>' for x in items)
    return f'    <ul class="api-facts api-facts--deux">\n{li}\n    </ul>'


def bloc_fiche(lignes, api=False):
    v = ' spec-item--api' if api else ''
    out = ['    <div class="specs__list" role="list">']
    for lib, val in lignes:
        out.append(f'      <div class="spec-item{v}" role="listitem">')
        out.append(f'        <span class="spec-item__label">{lib}</span>')
        out.append(f'        <span class="spec-item__value">{val}</span>')
        out.append('      </div>')
    out.append('    </div>')
    return '\n'.join(out)


def corps_html(blocs, exemples):
    out = []
    for kind, val in blocs:
        if kind == 'p':
            out.append(f'    <p class="section-subtitle">{val}</p>')
        elif kind == 'faits':
            out.append(bloc_faits(val))
        elif kind == 'fiche':
            out.append(bloc_fiche(val))
        elif kind == 'ficheapi':
            out.append(bloc_fiche(val, api=True))
        elif kind == 'exemples':
            out.append(exemples)
        else:
            raise AssertionError(f'bloc inconnu : {kind}')
    return '\n'.join(out)


def decale(bloc, n):
    """Le bloc, décalé de `n` espaces, lignes vides laissées vides."""
    p = ' ' * n
    return '\n'.join(p + l if l.strip() else l for l in bloc.split('\n'))


def sommaire(sections, titre):
    li = '\n'.join(
        f'        <li><a class="link-edito" href="#{s["id"]}">'
        f'<span>{s["titre"]}</span>{FLECHE}</a></li>' for s in sections)
    return (f'    <nav class="doc-somm" aria-label="{titre}">\n'
            f'      <ol class="doc-somm__list">\n{li}\n      </ol>\n'
            f'    </nav>')


def main():
    # LE GARDE-FOU DE PARITÉ, QUE LE DOCSTRING PROMETTAIT SANS QU'IL EXISTE : une
    # section ajoutée d'un côté et pas de l'autre passait sans un mot, et les deux
    # pages divergeaient en silence — exactement ce que ce générateur existe pour
    # empêcher.
    fr, en = C.SECTIONS['fr'], C.SECTIONS['en']
    assert [x['id'] for x in fr] == [x['id'] for x in en], 'les deux langues divergent'
    for a, b in zip(fr, en):
        assert sorted(a) == sorted(b), 'section %s : clés différentes' % a['id']
        assert [k for k, _ in a['corps']] == [k for k, _ in b['corps']], \
            'section %s : blocs différents' % a['id']
    assert sorted(C.META['fr']) == sorted(C.META['en']), "l'en-tête diverge"

    for page in PAGES:
        lang = page['lang']
        meta, secs = C.META[lang], C.SECTIONS[lang]
        src = (RACINE / page['donneuse']).read_text(encoding='utf-8')

        # ── les cinq accordéons d'appel, extraits, jamais retapés ──
        # LA DONNEUSE NE LES PORTE PLUS : ils vivaient sur la fiche technique,
        # ils vivent ici depuis le 2026-09-14, et la fiche n'a gardé que ses
        # quatre accordéons de spécifications. Le générateur s'arrêtait donc sur
        # son assertion (« 4 exemples extraits, attendu 5 ») et ne pouvait plus
        # tourner — la panne qu'un générateur laissé en arrière finit toujours
        # par avoir. On reprend donc les accordéons dans la page DÉJÀ ÉCRITE,
        # et on retombe sur la donneuse pour une première génération.
        deja = RACINE / page['sortie']
        prec = deja.read_text(encoding='utf-8') if deja.exists() else ''
        if prec.count('class="faq-item" id="api-ex') == 5:
            ex = extraire(prec, '  <div class="faq__list">', '</div>\n      </div>')
        else:
            ex = extraire(src, '<div class="faq__list">', '</div>\n    </div>')
            ex = '\n'.join('  ' + l if l.strip() else l for l in ex.split('\n'))
        n_ex = ex.count('class="faq-item"')
        assert n_ex == 5, '%s : %d exemples extraits, attendu 5' % (lang, n_ex)

        # ── le corps de la page ──
        parts = [f'<main id="main">\n'
                 f'<section class="page-hero" aria-labelledby="page-title">\n'
                 f'  <div class="container">\n'
                 f'    <span class="section-label">{meta["label"]}</span>\n'
                 f'    <h1 id="page-title">{meta["h1"]}</h1>\n'
                 f'    <p>{meta["chapeau"]}</p>\n'
                 f'{sommaire(secs, meta["sommaire"])}\n'
                 f'  </div>\n</section>\n']
        for s in secs:
            gris = ' section--gray' if s.get('gris') else ''
            entete = (f'    <div class="section-header">\n'
                      f'      <span class="section-label">{s["label"]}</span>\n'
                      f'      <h2 class="section-title" id="{s["id"]}">{s["titre"]}</h2>\n'
                      f'      <p class="section-subtitle">{s["chapeau"]}</p>\n'
                      f'    </div>')
            vis = s.get('visuel')
            if not vis:
                parts.append(
                    f'<section class="section{gris}" aria-labelledby="{s["id"]}">\n'
                    f'  <div class="container">\n'
                    f'{entete}\n'
                    f'{corps_html(s["corps"], ex)}\n'
                    f'  </div>\n</section>\n')
                continue
            # LE VISUEL SE POSE À CÔTÉ DE LA PROSE, PAS À CÔTÉ DE TOUTE LA
            # SECTION : les listes à coches de cette page sont elles-mêmes sur
            # deux colonnes, les glisser dans une demi-colonne les réduirait à
            # une. Les paragraphes de tête montent donc dans la colonne de
            # gauche, et ce qui suit passe sous les deux colonnes.
            reste = list(s['corps'])
            tete = []
            while reste and reste[0][0] == 'p':
                tete.append(reste.pop(0))
            gauche = decale(entete + ('\n' + corps_html(tete, ex) if tete else ''), 4)
            parts.append(
                f'<section class="section{gris}" aria-labelledby="{s["id"]}">\n'
                f'  <div class="container">\n'
                f'    <div class="doc-split">\n'
                f'      <div>\n{gauche}\n      </div>\n'
                f'      <div class="doc-split__media">\n'
                f'        <img src="{vis["src"]}" alt="{vis["alt"]}" '
                f'width="{vis["w"]}" height="{vis["h"]}" loading="lazy">\n'
                f'      </div>\n'
                f'    </div>\n'
                + (corps_html(reste, ex) + '\n' if reste else '')
                + f'  </div>\n</section>\n')
        # le bloc d'appel à l'action, repris tel quel de la donneuse
        parts.append(extraire(src, '<section class="section section--dark" aria-labelledby="cta-title"',
                              '</section>') + '\n')
        corps = '\n'.join(parts) + '</main>'

        t = src[:src.index('<main')] + corps + src[src.index('</main>') + len('</main>'):]

        # ── l'en-tête de page ──
        rempl = [
            (r'<title>.*?</title>', f'<title>{meta["titre"]}</title>'),
            (r'<meta name="description" content="[^"]*">',
             f'<meta name="description" content="{meta["desc"]}">'),
            (r'<link rel="canonical" href="[^"]*">',
             f'<link rel="canonical" href="{page["url"]}">'),
            (r'<meta property="og:title" content="[^"]*">',
             f'<meta property="og:title" content="{meta["titre"]}">'),
            (r'<meta property="og:description" content="[^"]*">',
             f'<meta property="og:description" content="{meta["desc"]}">'),
            (r'<meta property="og:url" content="[^"]*">',
             f'<meta property="og:url" content="{page["url"]}">'),
            (r'<meta name="twitter:title" content="[^"]*">',
             f'<meta name="twitter:title" content="{meta["titre"]}">'),
            (r'<meta name="twitter:description" content="[^"]*">',
             f'<meta name="twitter:description" content="{meta["desc"]}">'),
        ]
        for motif, neuf in rempl:
            t, n = re.subn(motif, lambda m: neuf, t, count=1, flags=re.S)
            assert n == 1, f'{lang} : en-tête, motif sans effet : {motif}'

        # LES HREFLANG SE REMPLACENT PAR ATTRIBUT, JAMAIS EN BLOC : les deux
        # donneuses ne les écrivent pas dans le même ordre, et un motif ordonné
        # s'applique à une langue et échoue EN SILENCE sur l'autre (relevé le
        # 2026-08-26 sur le générateur des guides).
        for h, cible in (('fr', page['url'] if lang == 'fr' else page['alt']),
                         ('en', page['alt'] if lang == 'fr' else page['url']),
                         ('x-default', page['url'] if lang == 'fr' else page['alt'])):
            t, n = re.subn(rf'(<link rel="alternate" hreflang="{h}" href=")[^"]*(">)',
                           lambda m, c=cible: m.group(1) + c + m.group(2), t, count=1)
            assert n == 1, f'{lang} : hreflang {h} introuvable'

        # ── les données structurées : le Product de la donneuse devient un
        #    TechArticle, et le fil d'Ariane désigne cette page ──
        t = re.sub(r'<script type="application/ld\+json">\s*\{\s*"@context": "https://schema\.org",\s*"@type": "Product".*?</script>',
                   techarticle(page, meta), t, count=1, flags=re.S)
        assert '"TechArticle"' in t, f'{lang} : TechArticle non posé'
        t = re.sub(r'("BreadcrumbList".*?"position": 2,\s*"name": ")[^"]*(",\s*"item": ")[^"]*(")',
                   lambda m: m.group(1) + meta['h1'] + m.group(2) + page['url'] + m.group(3),
                   t, count=1, flags=re.S)

        (RACINE / page['sortie']).write_text(t, encoding='utf-8')
        print(f'  écrit {page["sortie"]:26s} {len(t):7d} octets · {len(secs)} sections')


# L'AUTEUR EST L'ORGANISATION, PAS UNE PERSONNE. Le dépôt signe quatre articles et
# les guides au nom de Sylvain Perez, mais seulement après qu'il les a relus :
# signer un texte au nom d'une personne réelle est une affirmation sur elle. À
# basculer sur `Person` le jour où il valide cette page.
def techarticle(page, meta):
    return ('<script type="application/ld+json">\n  {\n'
            '    "@context": "https://schema.org",\n'
            '    "@type": "TechArticle",\n'
            f'    "headline": "{meta["titre_court"]}",\n'
            f'    "description": "{meta["desc"]}",\n'
            f'    "url": "{page["url"]}",\n'
            f'    "inLanguage": "{page["lang"]}",\n'
            f'    "datePublished": "{PUBLIE}",\n'
            f'    "dateModified": "{MODIFIE}",\n'
            '    "image": "https://q-bot.eu/assets/img/qbot-og.jpg",\n'
            '    "author": { "@id": "https://q-bot.eu/#organization" },\n'
            '    "isPartOf": { "@type": "WebSite", "name": "Q-Bot", "url": "https://q-bot.eu/" },\n'
            '    "about": { "@type": "Product", "name": "Q-Bot" },\n'
            '    "publisher": { "@id": "https://q-bot.eu/#organization" }\n'
            '  }\n  </script>')


if __name__ == '__main__':
    main()
