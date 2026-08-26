#!/usr/bin/env python3
"""Contrôle TOUTES les redirections des anciennes adresses WordPress.

Le nombre n'est pas écrit ici, à dessein : il a valu « 34 » pendant que la
carte en contenait déjà 52, et un chiffre faux dans une consigne se lit le jour
de la bascule, au plus mauvais moment. La liste qui fait foi est
`tools/redirections_map.py`, et le compte réel est imprimé en fin d'exécution.

Deux modes, et le second est celui qui compte le jour de la mise en ligne :

    python3 tools/verif-redirections.py            # en local, sur un serveur statique
    python3 tools/verif-redirections.py --enligne  # sur https://q-bot.eu, après la bascule

EN LOCAL il vérifie que chaque page de redirection existe, que son
`meta refresh`, son lien visible et son `location.replace` désignent bien la
même cible, et que cette cible est un fichier présent dans le dépôt.

EN LIGNE il suit réellement chaque ancienne adresse et vérifie qu'elle aboutit
sur une page du site (présence du logo de l'en-tête). C'est le contrôle à passer
AVANT de supprimer le WordPress : tant qu'il répond encore, une erreur est
réparable ; après, l'adresse est perdue.

Le mode local n'a pas besoin de navigateur. Le mode en ligne non plus : un
`meta refresh` se lit dans le HTML, on suit donc la chaîne sans rendu, ce qui
évite d'ouvrir une fenêtre sur la machine de qui lance le contrôle.
"""

import argparse
import io
import os
import re
import sys
import urllib.request
import urllib.error

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from redirections_map import REDIRECTIONS  # noqa: E402


def local():
    ko = 0
    for ancien, (cible, _lang) in sorted(REDIRECTIONS.items()):
        f = os.path.join(RACINE, ancien, 'index.html')
        if not os.path.exists(f):
            print(f"  ✗ {ancien} : page de redirection absente"); ko += 1; continue
        s = io.open(f, encoding='utf-8').read()
        meta = re.search(r'<meta http-equiv="refresh" content="0; url=([^"]+)"', s)
        lien = re.search(r'<p><a href="([^"]+)">', s)
        js = re.search(r"location\.replace\('([^']+)'\)", s)
        if not (meta and lien and js):
            print(f"  ✗ {ancien} : page incomplète"); ko += 1; continue
        if not (meta.group(1) == lien.group(1) == js.group(1)):
            print(f"  ✗ {ancien} : les trois cibles diffèrent"); ko += 1; continue
        dest = os.path.normpath(os.path.join(RACINE, ancien, meta.group(1).split('#')[0]))
        if not os.path.exists(dest):
            print(f"  ✗ {ancien} → {meta.group(1)} : cible absente du dépôt"); ko += 1
    print(f"\n{len(REDIRECTIONS)} redirections, {ko} défaut(s)")
    return ko


def suivre(url, sauts=0):
    """Suit les redirections HTTP puis les meta refresh, jusqu'à une page réelle."""
    if sauts > 5:
        return url, '', 'trop de sauts'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh) Chrome/127',
        'Accept-Language': 'fr-FR,fr;q=0.9'})
    try:
        with urllib.request.urlopen(req, timeout=30) as h:
            corps = h.read().decode('utf-8', 'replace')
            final = h.url
    except urllib.error.HTTPError as e:
        return url, '', f'HTTP {e.code}'
    except Exception as e:
        return url, '', type(e).__name__
    m = re.search(r'<meta http-equiv="refresh" content="0;\s*url=([^"]+)"', corps, re.I)
    if m:
        return suivre(urllib.request.urljoin(final, m.group(1)), sauts + 1)
    return final, corps, ''


def enligne(base):
    ko = 0
    for ancien, (cible, _lang) in sorted(REDIRECTIONS.items()):
        final, corps, err = suivre(base + '/' + ancien)
        attendu = cible.split('#')[0].rsplit('/', 1)[-1]
        arrive = 'nav__logo' in corps
        if err or not arrive:
            print(f"  ✗ {ancien:<58} → {final}  {err or 'pas une page du site'}"); ko += 1
        elif attendu not in final and not final.rstrip('/').endswith(('q-bot.eu', '/en')):
            print(f"  ? {ancien:<58} → {final}  (attendu {attendu})")
    print(f"\n{len(REDIRECTIONS)} redirections suivies sur {base}, {ko} en échec")
    return ko


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--enligne', action='store_true')
    ap.add_argument('--base', default='https://q-bot.eu')
    a = ap.parse_args()
    sys.exit(1 if (enligne(a.base) if a.enligne else local()) else 0)
