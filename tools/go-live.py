#!/usr/bin/env python3
"""Lève les verrous de pré-lancement, en une fois.

POURQUOI UN SCRIPT ET PAS UNE LISTE DE GESTES. L'audit RosoAI insiste sur un
point : les trois verrous doivent tomber ENSEMBLE. Ouvrir robots.txt en laissant
la balise `noindex` sur les pages donne un site explorable mais non indexable,
c'est-à-dire un site invisible qui a l'air ouvert ; l'inverse donne un site
indexable que personne n'explore. Fait à la main sur trente fichiers, on en
oublie un, et le symptôme est silencieux.

USAGE
    python3 tools/go-live.py                      # simulation, n'écrit rien
    python3 tools/go-live.py --appliquer          # lève les verrous
    python3 tools/go-live.py --appliquer --endpoint "https://…"   # + les formulaires

LA SIMULATION EST LE DÉFAUT, à dessein : ce script rend le site public, et cela
ne doit pas pouvoir arriver par une faute de frappe.

CE QU'IL FAIT
  1. retire `<meta name="robots" content="noindex, nofollow">` et le commentaire
     PRÉ-LANCEMENT qui l'accompagne, sur toutes les pages ;
  2. remplace robots.txt par son contenu d'ouverture ;
  3. si `--endpoint` est fourni, renseigne `data-endpoint` sur les six
     formulaires (contact FR/EN, newsletter des deux accueils et des deux index
     de blog). Sans endpoint ils basculent sur le repli courrier : rien n'est
     perdu, mais le visiteur doit appuyer sur « envoyer » dans son logiciel.

CE QU'IL NE FAIT PAS, ET QUI RESTE MANUEL : le DNS, HTTPS, la Search Console, et
la suppression du WordPress. Il les rappelle en fin d'exécution.

LES PAGES DE REDIRECTION N'ONT PAS DE BALISE noindex et n'en veulent pas : leur
seul rôle est de transmettre un signal. Elles sont donc ignorées ici, et c'est
normal qu'un contrôle « toutes les pages portent la balise » ne les compte pas.
"""

import argparse
import glob
import io
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# La balise est cherchée par MOTIF et non par chaîne littérale : `admin/index.html`
# l'écrit « noindex,nofollow » sans espace, et un remplacement littéral la ratait
# en silence. Même famille de piège que le cadratin en entité et l'apostrophe
# typographique, trois fois rencontrée sur ce dépôt : on ne retape pas, on filtre.
META = re.compile(r'[ \t]*<meta name="robots" content="noindex[^"]*">\n')
COMMENTAIRE = re.compile(r'[ \t]*<!--\s*PRÉ-LANCEMENT.*?-->\n', re.S)

# LE BACK-OFFICE RESTE HORS INDEX POUR TOUJOURS. Ce n'est pas un verrou de
# pré-lancement, c'est un outil interne : sa balise ne doit jamais être retirée,
# et robots.txt le ferme en plus par « Disallow: /admin/ ».
JAMAIS = ('admin/',)

ROBOTS_OUVERT = """# https://q-bot.eu/robots.txt

User-agent: *
Allow: /
Disallow: /admin/

# ══════════════════════════════════════════════════════════════════════════
# MOTEURS DE RÉPONSE IA : AUTORISÉS, ET C'EST UNE DÉCISION.
# Le WordPress qui précède ce site les bloquait TOUS (Amazonbot, anthropic-ai,
# Applebot-Extended, Bytespider, CCBot, ClaudeBot, FacebookBot,
# Google-Extended, GPTBot, meta-externalagent, omgili, PerplexityBot…).
# Les ouvrir est la condition sine qua non pour être cité par un assistant :
# llms.txt, les réponses-capsules et les données structurées de ce site ne
# servent à rien si les robots qui les lisent sont refoulés à l'entrée.
# En contrepartie, le contenu devient lisible par ces modèles.
# ══════════════════════════════════════════════════════════════════════════

User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Applebot-Extended
Allow: /

Sitemap: https://q-bot.eu/sitemap.xml
"""

RESTE_MANUEL = """
────────────────────────────────────────────────────────────────────────────
CE QUI RESTE À FAIRE À LA MAIN, DANS CET ORDRE
────────────────────────────────────────────────────────────────────────────
 1. Rattacher le domaine q-bot.eu à GitHub Pages, basculer le DNS, activer
    HTTPS. Le site est alors public.
 2. VÉRIFIER LES 34 REDIRECTIONS EN LIGNE avant toute chose :
       python3 tools/verif-redirections.py --enligne
 3. Créer la propriété Search Console et demander l'indexation. Relever le
    nombre de pages indexées : c'est le seul indicateur qui dise si la mise en
    ligne a réussi. Point de départ : 0 sur 29.
 4. NE SUPPRIMER LE WORDPRESS QU'APRÈS l'étape 2. Les quatre pages légales
    vivent désormais dans ce dépôt, aux mêmes adresses, donc rien ne se perd ;
    mais tant que le WordPress répond encore, on peut comparer.
 5. Si aucun endpoint n'a été fourni : les six formulaires basculent sur le
    repli courrier. Chaque demande de démo demande alors un geste de plus au
    visiteur. À brancher dès que possible.
────────────────────────────────────────────────────────────────────────────
"""


def pages():
    motifs = ['*.html', 'blog/*.html', 'en/*.html', 'en/blog/*.html',
              '*/index.html', 'en/*/index.html', 'admin/*.html']
    vus = set()
    for m in motifs:
        for f in glob.glob(os.path.join(RACINE, m)):
            vus.add(f)
    return sorted(vus)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--appliquer', action='store_true',
                    help="écrit réellement les fichiers (sans ce drapeau : simulation)")
    ap.add_argument('--endpoint', default=None,
                    help="URL de réception des six formulaires")
    a = ap.parse_args()
    ecrit = a.appliquer
    mode = 'APPLICATION' if ecrit else 'SIMULATION (rien n\'est écrit)'
    print(f"── Levée des verrous de pré-lancement — {mode}\n")

    n_meta = n_form = 0
    for f in pages():
        rel = os.path.relpath(f, RACINE)
        if rel.startswith(JAMAIS):
            print(f"  {rel} : laissé hors index à dessein (outil interne)")
            continue
        s = io.open(f, encoding='utf-8').read()
        o = s
        s = META.sub('', s)
        s = COMMENTAIRE.sub('', s)
        if a.endpoint:
            neuf = s.replace('data-endpoint=""', f'data-endpoint="{a.endpoint}"')
            n_form += s.count('data-endpoint=""')
            s = neuf
        if s != o:
            n_meta += 1
            if ecrit:
                io.open(f, 'w', encoding='utf-8').write(s)
    print(f"  balise noindex et commentaire PRÉ-LANCEMENT retirés de {n_meta} fichiers")
    if a.endpoint:
        print(f"  data-endpoint renseigné sur {n_form} formulaires → {a.endpoint}")
    else:
        print("  aucun endpoint fourni : les six formulaires restent sur le repli courrier")

    p = os.path.join(RACINE, 'robots.txt')
    if ecrit:
        io.open(p, 'w', encoding='utf-8').write(ROBOTS_OUVERT)
    print("  robots.txt remplacé par son contenu d'ouverture "
          "(exploration autorisée, /admin/ fermé, moteurs IA autorisés)")

    if ecrit:
        restants = [os.path.relpath(f, RACINE) for f in pages()
                    if not os.path.relpath(f, RACINE).startswith(JAMAIS)
                    and 'name="robots" content="noindex' in io.open(f, encoding='utf-8').read()]
        print(f"\n  contrôle : {len(restants)} page(s) portent encore une balise noindex"
              + (f" → {restants}" if restants else " ✓"))
    print(RESTE_MANUEL)
    if not ecrit:
        print("Relancer avec --appliquer pour exécuter.")


if __name__ == '__main__':
    main()
