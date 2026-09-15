#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refonte de la page Caractéristiques en page de QUALIFICATION produit.

    python3 tools/refonte-caracteristiques.py
    node tools/bump-assets.mjs

USAGE UNIQUE, GARDÉ COMME TRACE. Le script est idempotent par refus : il s'arrête
si la page porte déjà la nouvelle structure, plutôt que de la refondre deux fois.

POURQUOI. Relevé le 2026-09-14 sur les 9 274 px de la page : « L'architecture de
Q-Bot » faisait 2 541 px en TROISIÈME position et « Un appel HTTP » 1 203 px en
sixième, soit 40 % de la page en documentation d'intégration, avant même d'avoir
dit si le produit convient. Le client : « ce n'est plus vraiment une page de
caractéristiques, c'est déjà une documentation d'intégration ».

CE QUI PART, CE QUI RESTE, ET POURQUOI :
  • la section « Un appel HTTP » PART ENTIÈREMENT vers `documentation.html` : ses
    cinq exemples de code y sont déjà, extraits par `gen-documentation.py` ;
  • la fiche « L'architecture » DESCEND en bas de page, en accordéons ;
  • une section « Déploiement et support » est créée avec les quatre lignes de la
    catégorie Déploiement, QUI NE SONT DONC PAS reprises en accordéon. Le plan du
    client les mettait aux deux endroits ; les écrire deux fois est exactement la
    duplication qu'il demande de supprimer.
"""
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

T = {
 'fr': dict(
  integ_label='Intégration', integ_h2="Comment <span class=\"nb\">Q-Bot</span> s'intègre dans votre environnement",
  integ_faits=["Compatible avec toute chaîne capable d'un appel HTTP",
               "Se déclenche depuis votre intégration continue",
               "Aucun SDK, aucun agent à installer"],
  integ_lien="Les exemples d'appel, outil par outil", integ_href='documentation.html#doc-call',
  dep_label='Déploiement', dep_h2='Déploiement et support',
  dep_chapeau="Le boîtier est loué, installé et maintenu par Q-Leap. Ce qui suit est inclus.",
  tech_label='Fiche technique', tech_h2='Détails techniques',
  tech_chapeau="Le détail pour qui veut regarder sous le capot. Dépliez la catégorie qui vous concerne.",
  tech_cta='Consulter la documentation technique', tech_href='documentation.html',
  acc=['Matériel et système', 'Smartphone et communication', 'Interface et stockage', 'Réseau'],
  privacy_h2='Données et environnement',
 ),
 'en': dict(
  integ_label='Integration', integ_h2="How <span class=\"nb\">Q-Bot</span> fits into your environment",
  integ_faits=["Works with any test suite that can make an HTTP call",
               "Triggered from your continuous integration",
               "No SDK, no agent to install"],
  integ_lien='The call, tool by tool', integ_href='documentation.html#doc-call',
  dep_label='Deployment', dep_h2='Deployment and support',
  dep_chapeau="The device is rented, installed and maintained by Q-Leap. What follows is included.",
  tech_label='Specifications', tech_h2='Technical details',
  tech_chapeau="The detail for whoever wants to look under the bonnet. Open the category you need.",
  tech_cta='Read the technical documentation', tech_href='documentation.html',
  acc=['Hardware and system', 'Phone and communication', 'Interface and storage', 'Network'],
  privacy_h2='Data and environment',
 ),
}

PAGES = [('fr', 'caracteristiques.html'), ('en', 'en/technical-specs.html')]

COCHE = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
         '<polyline points="4,12 9,17 20,6"/></svg>')
PLUS = ('<span class="faq-item__icon" aria-hidden="true">\n'
        '            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="3"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>\n'
        '          </span>')


def section(t, aid):
    """La section entière qui porte cet `aria-labelledby`, bornes structurelles."""
    i = t.index(f'aria-labelledby="{aid}"')
    d = t.rindex('<section', 0, i)
    f = t.index('</section>', i) + len('</section>')
    bloc = t[d:f]
    assert bloc.count('<section') == 1, f'{aid} : borne fausse ({bloc.count("<section")} sections)'
    return bloc


def bloc_equilibre(t, debut):
    """Du `<div` en `debut` jusqu'à son `</div>` — PAR COMPTAGE, pas par motif.

    UN `.*?</div>` NON GOURMAND S'ARRÊTE AU PREMIER `</div>` RENCONTRÉ, donc au
    premier `.spec-item`, et rend un fragment déséquilibré : 13 ouvertures pour
    11 fermetures, des accordéons imbriqués les uns dans les autres, et trois
    d'entre eux ouverts en même temps. Constaté au rendu le 2026-09-14.
    L'indentation ne sauve pas non plus : la liste et ses lignes sont au même
    niveau dans le fichier. Seul le comptage est sûr.
    """
    i, profondeur = debut, 0
    for m in re.finditer(r'<div\b|</div>', t[debut:]):
        profondeur += 1 if m.group(0) == '<div' else -1
        if profondeur == 0:
            return t[debut:debut + m.end()]
    raise AssertionError('bloc <div> non refermé')


def categories(fiche):
    """Les blocs `<h3 class="compat__head">…` de la fiche, par nom de catégorie."""
    out = {}
    for m in re.finditer(r'<h3 class="compat__head">(.*?)</h3>', fiche, re.S):
        debut = fiche.index('<div class="specs__list"', m.end())
        bloc = bloc_equilibre(fiche, debut)
        assert bloc.count('<div') == bloc.count('</div>'), 'découpe déséquilibrée'
        out[m.group(1).strip()] = bloc
    return out


def main():
    for lang, chemin in PAGES:
        p = RACINE / chemin
        t = p.read_text(encoding='utf-8')
        if 'id="tech-title"' in t:
            print(f'  {chemin} : deja refondue, rien a faire')
            continue
        x = T[lang]

        hero    = section(t, 'page-title')
        boitier = section(t, 'compact-title')
        fiche   = section(t, 'fiche-title')
        editeur = section(t, 'editor-title')
        integ   = section(t, 'interface-title')
        api     = section(t, 'api-title')
        privacy = section(t, 'privacy-title')
        compat  = section(t, 'compat-title')
        cta     = section(t, 'cta-title')

        cats = categories(fiche)
        assert len(cats) == 6, f'{lang} : {len(cats)} categories, attendu 6'
        noms = list(cats)
        # ordre du fichier : Matériel, Smartphone, Interface, API, Données et réseau, Déploiement
        acc_src = [noms[0], noms[1], noms[2], noms[4]]
        dep_src = noms[5]

        # ── la section d'intégration ──
        integ = integ.replace('<span class="section-label">Interface &amp; API</span>',
                              f'<span class="section-label">{x["integ_label"]}</span>')
        integ = re.sub(r'(<h2 class="section-title" id="interface-title">).*?(</h2>)',
                       lambda m: m.group(1) + x['integ_h2'] + m.group(2), integ, count=1, flags=re.S)
        faits = '\n'.join(f'      <li>{COCHE}<span>{f}</span></li>' for f in x['integ_faits'])
        lien = (f'    <p style="margin-top:24px;"><a class="link-edito" href="{x["integ_href"]}">'
                f'<span>{x["integ_lien"]}</span><svg width="15" height="15" viewBox="0 0 24 24" '
                f'fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
                f'<path d="M5 12h14M12 5l7 7-7 7"/></svg></a></p>')
        marque = '</div>\n\n    <figure class="appwin"'
        assert integ.count(marque) == 1, f'{lang} : ancre de la fenetre introuvable'
        integ = integ.replace(marque, '</div>\n\n    <ul class="api-facts api-facts--deux">\n'
                              + faits + '\n    </ul>\n' + lien + '\n\n    <figure class="appwin"')

        # ── la section déploiement et support ──
        dep = (f'<!-- ======= DÉPLOIEMENT ET SUPPORT =======\n'
               f'     Créée le 2026-09-14 avec les quatre lignes de la catégorie Déploiement de\n'
               f'     l\'ancienne fiche. Elles NE sont donc pas reprises en accordéon : le plan du\n'
               f'     client les mettait aux deux endroits, et les écrire deux fois est la\n'
               f'     duplication qu\'il demande justement de supprimer. -->\n'
               f'<section class="section" aria-labelledby="deploy-title">\n'
               f'  <div class="container">\n'
               f'    <div class="section-header">\n'
               f'      <span class="section-label">{x["dep_label"]}</span>\n'
               f'      <h2 class="section-title" id="deploy-title">{x["dep_h2"]}</h2>\n'
               f'      <p class="section-subtitle">{x["dep_chapeau"]}</p>\n'
               f'    </div>\n{cats[dep_src]}\n  </div>\n</section>\n')

        # ── les détails techniques, en accordéons ──
        intro = re.search(r'<div class="specs__grid specs__grid--intro">.*?\n    </div>', fiche, re.S)
        assert intro, f'{lang} : bloc d\'introduction de la fiche introuvable'
        items = []
        for i, (nom, titre) in enumerate(zip(acc_src, x['acc']), start=1):
            items.append(
                f'      <div class="faq-item" id="spec-acc{i}">\n'
                f'        <button class="faq-item__question" aria-expanded="false" '
                f'id="spec-b{i}" aria-controls="spec-a{i}">\n'
                f'          {titre}\n          {PLUS}\n        </button>\n'
                f'        <div class="faq-item__answer" id="spec-a{i}" role="region" '
                f'aria-labelledby="spec-b{i}">\n{cats[nom]}\n        </div>\n      </div>')
        tech = (f'<!-- ======= DÉTAILS TECHNIQUES =======\n'
                f'     L\'ancienne fiche « L\'architecture », descendue en bas de page et repliée\n'
                f'     (2026-09-14). Elle faisait 2 541 px en troisième position ; le client :\n'
                f'     « excellente comme source d\'information, mais trop dense aussi haut ».\n'
                f'     Aucun script propre à la page : le module 3 apporte `hidden`, les\n'
                f'     `aria-controls` et la mesure de hauteur, comme pour la FAQ. -->\n'
                f'<section class="section section--gray" aria-labelledby="tech-title">\n'
                f'  <div class="container">\n'
                f'    <div class="section-header">\n'
                f'      <span class="section-label">{x["tech_label"]}</span>\n'
                f'      <h2 class="section-title" id="tech-title">{x["tech_h2"]}</h2>\n'
                f'      <p class="section-subtitle">{x["tech_chapeau"]}</p>\n'
                f'    </div>\n{intro.group(0)}\n'
                f'    <div class="faq__list">\n' + '\n'.join(items) + '\n    </div>\n'
                f'    <p style="margin-top:32px;"><a href="{x["tech_href"]}" '
                f'class="btn btn--outline">{x["tech_cta"]}</a></p>\n'
                f'  </div>\n</section>\n')

        # ── « Données et confidentialité » devient « Données et environnement » ──
        privacy = re.sub(r'(<h2 class="section-title" id="privacy-title">).*?(</h2>)',
                         lambda m: m.group(1) + x['privacy_h2'] + m.group(2),
                         privacy, count=1, flags=re.S)

        neuf = ('<main id="main">\n' + hero + '\n\n' + boitier + '\n\n' + integ + '\n\n'
                + editeur + '\n\n' + compat + '\n\n' + privacy + '\n\n' + dep + '\n'
                + tech + '\n' + cta + '\n\n</main>')
        t2 = t[:t.index('<main')] + neuf + t[t.index('</main>') + len('</main>'):]

        # ── garde-fous de STRUCTURE ──
        # DEUX SECTIONS PARTENT (la fiche et l'API), DEUX ARRIVENT (déploiement et
        # détails) : le compte ne bouge pas. C'est l'invariant qui compte, pas un
        # delta — un garde-fou par comptage doit porter sur la structure, pas sur
        # ce qu'on croit avoir écrit.
        assert t2.count('<section') == t.count('<section'), (
            'sections : %d -> %d' % (t.count('<section'), t2.count('<section')))
        assert t2.count('</section>') == t2.count('<section'), 'sections non refermees'
        assert t2.count('<h1') == 1 and t2.count('</main>') == 1
        assert t2.rstrip().endswith('</html>')
        for perdu in ('api-title', 'fiche-title'):
            assert perdu not in t2, f'{perdu} subsiste'
        for garde in ('compact-title', 'editor-title', 'compat-title', 'privacy-title',
                      'interface-title', 'deploy-title', 'tech-title', 'cta-title'):
            assert t2.count(f'id="{garde}"') == 1, f'{garde} absent ou double'
        p.write_text(t2, encoding='utf-8')
        print(f'  {chemin:26s} refondue · {t2.count("<section")} sections · '
              f'{len(items)} accordeons · {len(t) - len(t2):+d} octets')


if __name__ == '__main__':
    main()
