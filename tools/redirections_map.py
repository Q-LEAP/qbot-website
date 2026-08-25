#!/usr/bin/env python3
"""La carte des anciennes adresses WordPress vers les nouvelles.

Un module à part parce que DEUX scripts la lisent : `tools/gen-redirects.py`,
qui écrit les pages, et `tools/verif-redirections.py`, qui les contrôle. Le nom
de `gen-redirects.py` contient un tiret, il n'est pas importable tel quel.

Pour ajouter une redirection : une ligne ici, puis relancer le générateur.
Pour retirer une ancienne adresse de la liste, penser à supprimer aussi le
dossier qu'elle avait créé.
"""

# ── ancienne adresse (sans le domaine)  →  (cible relative depuis la racine, langue)
REDIRECTIONS = {
    # ---- pages de contenu, correspondance directe ----
    'about/':                       ('a-propos.html', 'fr'),
    'blog/':                        ('blog.html', 'fr'),
    'caracteristiques-techniques/': ('caracteristiques.html', 'fr'),
    'contact/':                     ('contact.html', 'fr'),
    'faq/':                         ('faq.html', 'fr'),
    'en/about-us/':                 ('en/about.html', 'en'),
    'en/contact-us/':               ('en/contact.html', 'en'),
    'en/technical-specifications/': ('en/technical-specs.html', 'en'),
    # doublon du live, même titre, même contenu
    'en/technical-specifications-2/': ('en/technical-specs.html', 'en'),
    'en/f/':                        ('en/faq.html', 'en'),

    # ---- articles ----
    'automatiser-lutilisation-des-tokens-dans-vos-tests-logiciels/':
        ('blog/automatiser-tokens-tests-logiciels.html', 'fr'),
    'lancement-merkur/':            ('blog/innovation-merkur.html', 'fr'),
    # même titre que notre article 2FA, au mot près
    'test-tests-logiciels/':        ('blog/authentification-deux-facteurs.html', 'fr'),

    # ---- la page « vidéos » : le film vit maintenant dans la page d'accueil ----
    'video/':                       ('index.html', 'fr'),
    'en/videos/':                   ('en/index.html', 'en'),

    # ---- les billets de la frise datée, retirée du site le 2026-08-12 ----
    #      Ils atterrissent sur la section « évolution du produit », qui raconte
    #      la même histoire sans les dates devenues fausses.
    'fevrier-2022/':          ('index.html#evolution-title', 'fr'),
    'prototype-fonctionnel/': ('index.html#evolution-title', 'fr'),   # « Mai 2022 »
    'qbot-token-luxtrust/':   ('index.html#evolution-title', 'fr'),   # « Juin 2022 »
    'decembre-2022/':         ('index.html#evolution-title', 'fr'),
    'juin-2023/':             ('index.html#evolution-title', 'fr'),
    'decembre-2023/':         ('index.html#evolution-title', 'fr'),
    'en/february-2022/':      ('en/index.html#evolution-title', 'en'),
    'en/may-2022/':           ('en/index.html#evolution-title', 'en'),
    'en/june-2022/':          ('en/index.html#evolution-title', 'en'),
    'en/december-2022/':      ('en/index.html#evolution-title', 'en'),
    'en/june-2023/':          ('en/index.html#evolution-title', 'en'),
    'en/december-2023/':      ('en/index.html#evolution-title', 'en'),

    # ---- archives WordPress (catégories, étiquettes, auteurs) ----
    'category/presse/':                 ('blog.html', 'fr'),
    'category/timeline/':               ('blog.html', 'fr'),
    'tag/2fa/':                         ('blog.html', 'fr'),
    'tag/automatisation-des-tests/':    ('blog.html', 'fr'),
    'author/marie-krust/':              ('blog.html', 'fr'),
    'author/sstefancic/':               ('blog.html', 'fr'),
    'en/category/timeline-en/':         ('en/blog.html', 'en'),
}
