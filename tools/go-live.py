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
  3. si `--endpoint` est fourni, renseigne `data-endpoint` sur les formulaires
     qui n'en ont pas encore. Depuis le 2026-08-26 les QUATRE newsletters
     pointent sur le vrai endpoint Brevo du client (relevé sur son WordPress),
     donc il n'en reste que DEUX : les formulaires de contact FR et EN. Ce qui
     règle au passage un défaut de ce script, qui posait la même URL sur les six
     alors qu'une inscription newsletter et une demande de démo ne vont pas au
     même endroit. Sans endpoint, ces deux-là restent sur le repli courrier :
     rien n'est perdu, mais le visiteur doit appuyer sur « envoyer ».

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

# LES DEUX NOMBRES DU RAPPEL DE FIN NE SONT PLUS ÉCRITS À LA MAIN, et c'est le
# correctif d'un défaut réel, relevé par l'audit de contrôle n°3 du 2026-08-25 :
# ils annonçaient « 34 redirections » et « 0 sur 29 » alors qu'il y en a 52 et 28.
# Les scripts, eux, lisaient déjà la vraie liste. C'était le texte destiné à
# l'humain qui avait vieilli, et c'est le pire endroit pour un chiffre faux : il
# se lit le jour J, au moment où l'on a le moins envie de se demander lequel des
# deux croire. Ils se dérivent donc de leur source, la carte de redirections et le
# plan du site, et ne peuvent plus se désynchroniser.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from redirections_map import REDIRECTIONS  # noqa: E402

NB_REDIRECTIONS = len(REDIRECTIONS)
with io.open(os.path.join(RACINE, 'sitemap.xml'), encoding='utf-8') as _f:
    NB_PAGES = _f.read().count('<loc>')

# La balise est cherchée par MOTIF et non par chaîne littérale : `admin/index.html`
# l'écrit « noindex,nofollow » sans espace, et un remplacement littéral la ratait
# en silence. Même famille de piège que le cadratin en entité et l'apostrophe
# typographique, trois fois rencontrée sur ce dépôt : on ne retape pas, on filtre.
META = re.compile(r'[ \t]*<meta name="robots" content="noindex[^"]*">\n')
COMMENTAIRE = re.compile(r'[ \t]*<!--\s*PRÉ-LANCEMENT.*?-->\n', re.S)

# La note posée à côté des formulaires sans endpoint pour dire qu'il est en
# attente d'approbation. Elle n'a plus d'objet dès que --endpoint est fourni,
# et elle NE porte PAS la marque « PRÉ-LANCEMENT » à dessein : elle ne doit pas
# disparaître avec les verrous d'indexation, qui se lèvent peut-être avant que
# l'approbation n'arrive.
NOTE_ENDPOINT = re.compile(r'[ \t]*<!--\s*ROSOAI-EN-ATTENTE · (?:endpoint des formulaires|form endpoint).*?-->\n', re.S)

# CE QUI RESTE HORS INDEX POUR TOUJOURS. Ces balises ne sont PAS des verrous de
# pré-lancement, elles ne doivent donc jamais être retirées :
#   - admin/    : outil interne, que robots.txt ferme en plus par « Disallow: /admin/ » ;
#   - 404.html  : une page d'erreur n'a rien à faire dans un index. GitHub Pages la
#                 sert avec un vrai statut 404, donc le risque est théorique, mais une
#                 page d'erreur indexée est un défaut classique et la balise coûte zéro.
# Attention : ces fichiers portent la marque « PRÉ-LANCEMENT » comme les autres, parce
# qu'ils ont été écrits avec le même gabarit. C'est cette liste qui tranche, pas la marque.
JAMAIS = ('admin/', '404.html')

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

RESTE_MANUEL = f"""
────────────────────────────────────────────────────────────────────────────
CE QUI RESTE À FAIRE À LA MAIN, DANS CET ORDRE
────────────────────────────────────────────────────────────────────────────
 1. Rattacher le domaine q-bot.eu à GitHub Pages, basculer le DNS, activer
    HTTPS. Le site est alors public.
 2. VÉRIFIER LES {NB_REDIRECTIONS} REDIRECTIONS EN LIGNE avant toute chose :
       python3 tools/verif-redirections.py --enligne
 3. Créer la propriété Search Console et demander l'indexation. Relever le
    nombre de pages indexées : c'est le seul indicateur qui dise si la mise en
    ligne a réussi. Point de départ : 0 sur {NB_PAGES}.
 4. NE SUPPRIMER LE WORDPRESS QU'APRÈS l'étape 2. Les quatre pages légales
    vivent désormais dans ce dépôt, aux mêmes adresses, donc rien ne se perd ;
    mais tant que le WordPress répond encore, on peut comparer.
 5. Si aucun endpoint n'a été fourni : les deux formulaires de CONTACT restent
    sur le repli courrier (les quatre newsletters, elles, sont branchées sur
    Brevo). Chaque demande de démo demande alors un geste de plus au visiteur.
    Le live traitait ce formulaire avec Contact Form 7, un plugin DANS le
    WordPress : il n'y a rien à récupérer, et il meurt à l'étape 4.
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
                    help="URL de réception des formulaires encore sans endpoint (les 2 contacts)")
    a = ap.parse_args()
    ecrit = a.appliquer
    mode = 'APPLICATION' if ecrit else 'SIMULATION (rien n\'est écrit)'
    print(f"── Levée des verrous de pré-lancement — {mode}\n")

    n_meta = n_form = n_note = 0
    for f in pages():
        rel = os.path.relpath(f, RACINE)
        if rel.startswith(JAMAIS):
            print(f"  {rel} : laissé hors index à dessein (hors du site public)")
            continue
        s = io.open(f, encoding='utf-8').read()
        o = s
        s = META.sub('', s)
        s = COMMENTAIRE.sub('', s)
        if a.endpoint:
            neuf = s.replace('data-endpoint=""', f'data-endpoint="{a.endpoint}"')
            n_form += s.count('data-endpoint=""')
            s = neuf
            # La note qui explique que l'endpoint est en attente part AVEC la
            # valeur qu'elle attendait. Sans ça elle survivrait au point qu'elle
            # décrit, et une note qui ment est une note qu'on cesse de croire.
            avant = s
            s = NOTE_ENDPOINT.sub('', s)
            if s != avant:
                n_note += 1
        if s != o:
            n_meta += 1
            if ecrit:
                io.open(f, 'w', encoding='utf-8').write(s)
    print(f"  balise noindex et commentaire PRÉ-LANCEMENT retirés de {n_meta} fichiers")
    if a.endpoint:
        print(f"  data-endpoint renseigné sur {n_form} formulaires → {a.endpoint}")
        print(f"  note ROSOAI-EN-ATTENTE de l'endpoint retirée de {n_note} fichiers")
    else:
        print("  aucun endpoint fourni : les formulaires sans endpoint restent sur le repli courrier")

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
