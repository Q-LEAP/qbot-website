#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recale les `lastmod` de sitemap.xml sur la vraie date de chaque fichier.

POURQUOI CE SCRIPT EXISTE. Ces dates étaient écrites à la main, et une date
écrite à la main se périme : le 2026-08-26, l'audit RosoAI a relevé six pages
modifiées le jour même qui portaient encore la date de la veille (les deux
accueils, les deux index de blog, les deux pages de contact, c'est-à-dire
exactement celles qui venaient de recevoir le bloc de consentement). Sans
gravité tant que le site est fermé, mais `lastmod` est un des signaux qui
décident de ce que Google re-visite en premier après l'ouverture.

C'est la même famille que les compteurs « 34 redirections » et « 0 sur 29 »,
réglés en les DÉRIVANT de leur source plutôt qu'en les réécrivant. Un nombre —
ou une date — qu'on écrit à la main revient dans le rapport suivant.

LA RÈGLE DE DÉRIVATION, et son cas limite. La date d'un fichier est celle du
dernier commit qui l'a touché. Mais un fichier modifié et pas encore commité
porterait alors la date de sa version PRÉCÉDENTE, ce qui est précisément le
défaut qu'on corrige : ceux-là prennent donc la date du jour. Lancer ce script
juste avant de commiter donne le bon résultat dans les deux cas.

À LANCER APRÈS TOUTE MODIFICATION DE PAGE, AVANT DE COMMITER :

    python3 tools/maj-sitemap.py            # simulation, n'écrit rien
    python3 tools/maj-sitemap.py --ecrire
"""
import datetime
import io
import os
import re
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITEMAP = os.path.join(RACINE, 'sitemap.xml')
BASE = 'https://q-bot.eu/'


def fichier_de(loc):
    """L'adresse publiée d'une page vers son fichier dans le dépôt.

    Trois formes : la racine d'une langue (`/`, `/en/`), une page plate
    (`/faq.html`), et un répertoire dont le fichier est `index.html` (les
    quatre pages légales, dont l'adresse est celle du live à dessein).
    """
    rel = loc[len(BASE):]
    if rel == '' or rel.endswith('/'):
        rel += 'index.html'
    return rel


def date_git(rel):
    """Date du dernier commit qui a touché ce fichier, ou None s'il est neuf."""
    out = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', rel],
                         cwd=RACINE, capture_output=True, text=True).stdout.strip()
    return out or None


def modifie_non_commite(rel):
    out = subprocess.run(['git', 'status', '--porcelain', '--', rel],
                         cwd=RACINE, capture_output=True, text=True).stdout
    return bool(out.strip())


def main():
    ecrire = '--ecrire' in sys.argv
    aujourdhui = datetime.date.today().isoformat()
    src = io.open(SITEMAP, encoding='utf-8').read()

    # une entrée = un <url> ; on remplace le <lastmod> à l'intérieur de CHAQUE
    # bloc, jamais globalement : deux entrées peuvent partager la même date.
    change = manquants = 0
    total = 0

    def remplace(bloc):
        nonlocal change, manquants, total
        texte = bloc.group(0)
        loc = re.search(r'<loc>(.*?)</loc>', texte).group(1)
        rel = fichier_de(loc)
        total += 1
        if not os.path.exists(os.path.join(RACINE, rel)):
            manquants += 1
            print(f'  MANQUANT  {loc}  ->  {rel}')
            return texte
        date = aujourdhui if modifie_non_commite(rel) else (date_git(rel) or aujourdhui)
        actuel = re.search(r'<lastmod>(.*?)</lastmod>', texte)
        if actuel and actuel.group(1) != date:
            change += 1
            print(f'  {actuel.group(1)} -> {date}   {loc}')
            texte = texte.replace(f'<lastmod>{actuel.group(1)}</lastmod>',
                                  f'<lastmod>{date}</lastmod>')
        return texte

    sortie = re.sub(r'<url>.*?</url>', remplace, src, flags=re.S)

    print(f'\n{total} URL, {change} date(s) à corriger, {manquants} fichier(s) introuvable(s)')
    assert manquants == 0, 'une URL du plan de site ne désigne aucun fichier'
    if not ecrire:
        print("simulation — relancer avec --ecrire pour appliquer")
        return
    if change:
        io.open(SITEMAP, 'w', encoding='utf-8').write(sortie)
        print('sitemap.xml écrit')
    else:
        print('rien à écrire')


if __name__ == '__main__':
    main()
