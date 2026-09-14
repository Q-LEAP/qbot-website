#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le pied de page des pages publiées : Produit / Ressources / Entreprise.

    python3 tools/maj-pied.py            # simulation
    python3 tools/maj-pied.py --ecrire
    node tools/bump-assets.mjs

Structure demandée par le client le 2026-09-14, avec deux écarts assumés :

  • « SÉCURITÉ » ET « SUPPORT » SONT DES ANCRES DE LA DOCUMENTATION, pas des
    pages. Deux pages qu'on ne peut pas remplir seraient minces et creuses, ce
    qui est pire pour le visiteur et pour le référencement que deux sections
    bien nourries ;
  • LA FAQ RESTE, sous Ressources. Elle a quitté la barre de navigation le
    2026-09-02 : hors du pied de page, elle ne serait plus atteignable que par
    le plan du site, alors que c'est la surface la plus citable du site.

Les coordonnées (courriel, téléphone, adresse) descendent dans la colonne
Entreprise : le plan du client n'avait plus de colonne pour elles, et une
société luxembourgeoise n'enlève pas son adresse de son pied de page.

LE PRÉFIXE DES LIENS N'EST PAS CELUI DES ASSETS. Une page `en/faq.html` pointe
`faq.html` (donc `en/faq.html`) alors que ses assets sont en `../` : le préfixe
compte les niveaux SOUS LA RACINE DE LA LANGUE, pas sous la racine du site.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bookings_conf as B  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
ECRIRE = '--ecrire' in sys.argv

L = {
 'fr': dict(prod='Produit', res='Ressources', ent='Entreprise',
            accueil='Accueil', specs='Caractéristiques', howto='Comment ça marche',
            demo='Demander une démo', doc='Documentation technique', faq='FAQ',
            secu='Sécurité', sup='Support', about='À propos', contact='Nous contacter',
            f_specs='caracteristiques.html', f_howto='cas-usage.html',
            f_doc='documentation.html', f_faq='faq.html', f_about='a-propos.html'),
 'en': dict(prod='Product', res='Resources', ent='Company',
            accueil='Home', specs='Technical specs', howto='How it works',
            demo='Request a demo', doc='Technical documentation', faq='FAQ',
            secu='Security', sup='Support', about='About', contact='Contact us',
            f_specs='technical-specs.html', f_howto='use-cases.html',
            f_doc='documentation.html', f_faq='faq.html', f_about='about.html'),
}

# page → clé de l'entrée à marquer « page courante »
COURANT = {
    'index.html': 'accueil', 'en/index.html': 'accueil',
    'caracteristiques.html': 'specs', 'en/technical-specs.html': 'specs',
    'cas-usage.html': 'howto', 'en/use-cases.html': 'howto',
    'documentation.html': 'doc', 'en/documentation.html': 'doc',
    'faq.html': 'faq', 'en/faq.html': 'faq',
    'a-propos.html': 'about', 'en/about.html': 'about',
    'contact.html': 'contact', 'en/contact.html': 'contact',
}

DEBUT = '      <div class="footer__col">'
FIN = '\n    </div>\n<div class="footer__bottom">'


def pages():
    # `en/index.html` est attrapée par `en/*.html` ET par `*/index.html` : sans
    # ce garde-fou elle est traitée deux fois, et le second passage travaille sur
    # un pied déjà remplacé.
    vus = set()
    for m in ('*.html', 'en/*.html', '*/index.html', 'en/*/index.html'):
        for p in sorted(RACINE.glob(m)):
            rel = p.relative_to(RACINE).as_posix()
            # LES FORKS DE RESSOURCES macOS (`._nom.html`) SONT DANS LE GLOB. Le
            # volume exFAT qui porte ce dépôt en écrit un à chaque écriture, ils
            # sont binaires, et `Path.glob` ne les saute pas. Le test porte sur le
            # NOM du fichier : `rel.startswith('.')` ne voit pas `en/._about.html`.
            if p.name.startswith('._') or rel in ('commandez.html', 'en/order.html'):
                continue
            if rel in vus:
                continue
            vus.add(rel)
            yield rel, p


def entree(libelle, href=None, courant=False, externe=False, attrs=''):
    if courant:
        return f'          <li><span aria-current="page">{libelle}</span></li>'
    ext = ' target="_blank" rel="noopener"' if externe else ''
    return f'          <li><a href="{href}"{ext}{attrs}>{libelle}</a></li>'


def colonnes(lang, prefixe, accueil, cur, adresse):
    x = L[lang]
    booking = ''.join('\n              %s="%s"' % (k, v.replace('"', '&quot;'))
                      for k, v in B.attributs(lang))
    prod = '\n'.join([
        entree(x['accueil'], accueil, cur == 'accueil'),
        entree(x['specs'], prefixe + x['f_specs'], cur == 'specs'),
        entree(x['howto'], prefixe + x['f_howto'], cur == 'howto'),
        entree(x['demo'], prefixe + 'contact.html', attrs=' data-booking-open' + booking + '\n              '),
    ])
    res = '\n'.join([
        entree(x['doc'], prefixe + x['f_doc'], cur == 'doc'),
        entree(x['faq'], prefixe + x['f_faq'], cur == 'faq'),
        entree(x['secu'], prefixe + x['f_doc'] + '#doc-securite'),
        entree(x['sup'], prefixe + x['f_doc'] + '#doc-support'),
    ])
    ent = '\n'.join([
        entree(x['about'], prefixe + x['f_about'], cur == 'about'),
        entree('Q-Leap', 'https://q-leap.eu', externe=True),
        entree(x['contact'], prefixe + 'contact.html', cur == 'contact'),
    ])
    return (f'      <div class="footer__col">\n        <h3>{x["prod"]}</h3>\n'
            f'        <ul role="list">\n{prod}\n        </ul>\n      </div>\n'
            f'      <div class="footer__col">\n        <h3>{x["res"]}</h3>\n'
            f'        <ul role="list">\n{res}\n        </ul>\n      </div>\n'
            f'      <div class="footer__col">\n        <h3>{x["ent"]}</h3>\n'
            f'        <ul role="list">\n{ent}\n        </ul>\n{adresse}      </div>')


def main():
    faits = 0
    for rel, p in pages():
        t = p.read_text(encoding='utf-8')
        if '<footer' not in t:
            continue
        lang = 'en' if rel.startswith('en/') else 'fr'
        sous = rel.count('/') - (1 if lang == 'en' else 0)
        prefixe = '../' * sous
        accueil = prefixe if sous else './'

        d = t.find(DEBUT)
        f = t.find(FIN, d)
        assert d != -1 and f != -1, f'{rel} : bornes du pied introuvables'
        ancien = t[d:f]
        assert ancien.count('footer__col') == 3, f'{rel} : {ancien.count("footer__col")} colonnes'

        # les coordonnées sont RELEVÉES dans la page, jamais retapées
        m = re.search(r'        <ul role="list">\s*<li><a href="mailto:.*?</p>\n', ancien, re.S)
        assert m, f'{rel} : bloc de coordonnées introuvable'
        adresse = m.group(0)

        neuf = colonnes(lang, prefixe, accueil, COURANT.get(rel), adresse)
        if neuf == ancien:
            continue
        t2 = t[:d] + neuf + t[f:]
        assert t2.count('<footer') == 1 and t2.count('</footer>') == 1
        assert t2.count('footer__col') == 3, f'{rel} : colonnes apres'
        assert t2.rstrip().endswith('</html>')
        if ECRIRE:
            p.write_text(t2, encoding='utf-8')
        faits += 1
        print(f'  {rel:30s} pied repris' + ('' if ECRIRE else '  (SIMULATION)'))
    print(f'\n{faits} pied(s) de page repris' + ('' if ECRIRE else ' — SIMULATION, rien écrit'))


if __name__ == '__main__':
    main()
