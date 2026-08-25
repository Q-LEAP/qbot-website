#!/usr/bin/env python3
"""Génère les pages de redirection des anciennes adresses WordPress.

LE PROBLÈME, RELEVÉ PAR L'AUDIT ROSOAI. Le jour où le domaine bascule du
WordPress vers GitHub Pages, les anciennes adresses (`/faq/`, `/blog/`,
`/about/`…) tombent en erreur : GitHub Pages ne sait pas renvoyer un 301. Tout
le référencement acquis sur ces URL est perdu, et les liens entrants aussi.

LA SOLUTION ICI, ET SA LIMITE. On ne peut pas faire un 301 sans serveur, mais on
peut poser à chaque ancienne adresse une page qui redirige côté navigateur :
`<meta http-equiv="refresh" content="0; url=…">` plus un `<link rel="canonical">`
vers la nouvelle adresse. Google traite un rafraîchissement à zéro seconde comme
une redirection et suit le canonical ; ce n'est pas aussi net qu'un 301, mais le
signal passe, et c'est la seule chose faisable sur un hébergement statique.
Le jour où le site passe derrière un vrai serveur ou un CDN, remplacer ces pages
par de véritables 301 est un progrès, pas une correction.

PAS DE `noindex` SUR CES PAGES, ET C'EST VOLONTAIRE. Leur unique raison d'être
est de transmettre un signal ; leur dire de ne pas être indexées reviendrait à
demander qu'on ignore ce signal. Le site reste de toute façon fermé par
robots.txt jusqu'à la mise en ligne. C'est la seule exception à la règle
« toutes les pages portent la balise PRÉ-LANCEMENT ».

PLUS AUCUNE 404, ARBITRÉ PAR LE CLIENT LE 2026-08-25. La première version laissait
volontairement tomber les dix-huit adresses du thème WordPress de démonstration
(`/portfolio/…`, `/portfolio-cat/…`, `/portfolio-tag/…`) : contenu factice jamais
remplacé, du même lot que l'équipe fictive « Colabrio ». Le client a tranché pour
zéro page d'erreur, elles renvoient donc à l'accueil.
Le compromis, énoncé une fois et pas rediscuté : un moteur peut lire dix-huit
redirections sans rapport comme des soft-404, ce qui vaut à peu près une 404 côté
référencement. En échange, un humain qui clique un vieux lien atterrit sur le
produit. C'est l'humain qui a été privilégié.

`?portfolio-filter=uncategorized` n'a besoin de rien : c'est une requête sur la
racine, pas un chemin, et un hébergement statique sert l'accueil en l'ignorant.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from redirections_map import REDIRECTIONS  # noqa: E402

T = {
    'fr': dict(lang='fr', titre='Page déplacée', h='Cette page a déménagé',
               p='Vous êtes redirigé automatiquement. Si rien ne se passe :',
               lien='continuer vers la nouvelle adresse'),
    'en': dict(lang='en', titre='Page moved', h='This page has moved',
               p='You are being redirected automatically. If nothing happens:',
               lien='continue to the new address'),
}

GABARIT = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titre}</title>
<!-- REDIRECTION. Cette page ne contient pas de contenu : elle existe pour que
     l'ancienne adresse WordPress continue de mener quelque part après la
     bascule vers GitHub Pages, qui ne sait pas renvoyer un 301. Générée par
     tools/gen-redirects.py, ne pas modifier à la main.
     Pas de balise noindex ici, à dessein : le seul rôle de cette page est de
     transmettre un signal de redirection. -->
<meta http-equiv="refresh" content="0; url={rel}">
<link rel="canonical" href="{abs}">
<style>
  html {{ color-scheme: dark; }}
  body {{ margin: 0; min-height: 100vh; display: flex; align-items: center;
         justify-content: center; background: #0A0A0A; color: #E6E7E8;
         font-family: Roboto, system-ui, -apple-system, sans-serif; text-align: center; }}
  main {{ padding: 32px; max-width: 34rem; }}
  h1 {{ font-size: 1.375rem; font-weight: 700; margin: 0 0 12px; }}
  p {{ color: #949699; font-size: .9375rem; line-height: 1.7; margin: 0 0 20px; }}
  a {{ color: #00CBBE; font-weight: 500; }}
</style>
</head>
<body>
<main>
  <h1>{h}</h1>
  <p>{p}</p>
  <p><a href="{rel}">{lien}</a></p>
</main>
<script>location.replace({js});</script>
</body>
</html>
"""

if __name__ == '__main__':
    ecrits = 0
    for ancien, (cible, lang) in sorted(REDIRECTIONS.items()):
        prof = ancien.rstrip('/').count('/') + 1          # profondeur du dossier créé
        rel = '../' * prof + cible
        t = dict(T[lang])
        t.update(rel=rel, abs='https://q-bot.eu/' + cible.replace('index.html', ''),
                 js="'" + rel.replace("'", "\\'") + "'")
        dest = os.path.join(RACINE, ancien, 'index.html')
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        io.open(dest, 'w', encoding='utf-8').write(GABARIT.format(**t))
        ecrits += 1
        print(f"  {ancien:<62} → {rel}")
    print(f"\n{ecrits} pages de redirection écrites")
