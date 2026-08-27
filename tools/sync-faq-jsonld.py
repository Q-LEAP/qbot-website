#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recale le `FAQPage` sur le texte que le visiteur lit réellement.

POURQUOI CE SCRIPT EXISTE. Chaque réponse de FAQ vit en DOUBLE : le texte visible
et le `acceptedAnswer.text` du JSON-LD. En français les deux copies partageaient
souvent la même chaîne, donc un remplacement les tenait synchronisées ; en anglais
elles ne partagent RIEN (le visible porte des `<strong>`, le JSON a son propre
espacement). C'est le piège qui a déjà coûté des corrections, et un contrôle qui ne
compare que les 60 premiers caractères ne le voit pas : relevé le 2026-08-27, la
réponse anglaise « What is Q-Bot? » divergeait à partir du milieu de la phrase
(« and allow for increased security » côté JSON, « and it increases the security »
côté page), et cet écart avait survécu à trois passes.

LA RÉFÉRENCE EST LE TEXTE RENDU, PAS LE HTML. Aplatir le HTML à la main insère une
espace à chaque balise fermante et produit « +352 20 21 17 . » — c'est exactement
l'artefact qu'on retrouvait dans 17 entrées du JSON. `innerText` donne ce que le
visiteur lit. Il faut en revanche OUVRIR les accordéons d'abord : une réponse
repliée est en `max-height: 0` et son texte rendu serait vide.

    python3 tools/sync-faq-jsonld.py            # simulation
    python3 tools/sync-faq-jsonld.py --ecrire

Un serveur statique est attendu sur le port 8137.
"""
import io
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ['faq.html', 'en/faq.html']

# Les items d'une liste sont préfixés d'une puce : sans elles, six items se lisent
# comme une seule phrase interminable. C'est la convention du JSON existant.
JS = r"""
() => {
  document.querySelectorAll('.faq-item__question').forEach(b => {
    if (b.getAttribute('aria-expanded') !== 'true') b.click();
  });
  return [...document.querySelectorAll('.faq-item')].map(it => {
    const a = it.querySelector('.faq-item__answer');
    const bouts = [];
    for (const n of a.children) {
      if (n.tagName === 'UL' || n.tagName === 'OL') {
        for (const li of n.children) bouts.push('• ' + li.innerText.trim());
      } else {
        const t = n.innerText.trim();
        if (t) bouts.push(t);
      }
    }
    return {
      question: it.querySelector('.faq-item__question').innerText.trim(),
      texte: bouts.join(' ').replace(/\s+/g, ' ').trim(),
    };
  });
}
"""


def bloc_faq(src):
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', src, re.S):
        d = json.loads(m.group(1))
        if d.get('@type') == 'FAQPage':
            return d, m.span(1)
    raise LookupError('aucun bloc FAQPage')


def main():
    ecrire = '--ecrire' in sys.argv
    total = change = 0
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page()
        for page in PAGES:
            chemin = os.path.join(RACINE, page)
            src = io.open(chemin, encoding='utf-8').read()
            d, (deb, fin) = bloc_faq(src)
            pg.goto('http://127.0.0.1:8137/' + page, wait_until='load', timeout=30000)
            pg.wait_for_timeout(300)
            rendu = pg.evaluate(JS)
            assert len(rendu) == len(d['mainEntity']), \
                f"{page} : {len(rendu)} questions à l'écran, {len(d['mainEntity'])} déclarées"
            n = 0
            for r, e in zip(rendu, d['mainEntity']):
                total += 1
                # le libellé de la question aussi : il vit lui aussi en double
                q = r['question'].replace(' ', ' ')
                if e['name'] != q:
                    print(f"  {page} nom  : {e['name']!r}\n{'':>{len(page)+9}}-> {q!r}")
                    e['name'] = q
                    n += 1
                if e['acceptedAnswer']['text'] != r['texte']:
                    a, b = e['acceptedAnswer']['text'], r['texte']
                    i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
                    print(f"  {page} Q{d['mainEntity'].index(e)+1} : diverge à «…{a[max(0,i-40):i+40]}»")
                    e['acceptedAnswer']['text'] = b
                    n += 1
            change += n
            if n and ecrire:
                bloc = json.dumps(d, ensure_ascii=False, indent=2)
                # l'indentation du <script> dans la page est de deux espaces
                bloc = '\n' + '\n'.join('  ' + l for l in bloc.splitlines()) + '\n  '
                io.open(chemin, 'w', encoding='utf-8').write(src[:deb] + bloc + src[fin:])
                print(f'  {page} réécrit')
        nav.close()
    print(f'\n{total} entrées comparées, {change} recalée(s)')
    if change and not ecrire:
        print('simulation — relancer avec --ecrire pour appliquer')


if __name__ == '__main__':
    main()
