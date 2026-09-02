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
    'blog/':                        ('index.html', 'fr'),
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
        ('index.html', 'fr'),
    'lancement-merkur/':            ('index.html', 'fr'),
    # même titre que notre article 2FA, au mot près
    'test-tests-logiciels/':        ('index.html', 'fr'),

    # ---- la page « vidéos » : le film vit maintenant dans la page d'accueil ----
    'video/':                       ('index.html', 'fr'),
    'en/videos/':                   ('en/index.html', 'en'),

    # ---- les billets de la frise datée, retirée du site le 2026-08-12 ----
    #      Ils atterrissaient sur la section « évolution du produit », qui
    #      racontait la même histoire sans les dates devenues fausses. CETTE
    #      SECTION A ÉTÉ RETIRÉE DE L'ACCUEIL LE 2026-09-02 (« pas utile sur la
    #      homepage », retour du client) : l'ancre n'existe plus, et une ancre
    #      morte fait atterrir le visiteur en haut de page sans le dire. Ils
    #      visent donc l'accueil de leur langue, comme les autres archives.
    'fevrier-2022/':          ('index.html', 'fr'),
    'prototype-fonctionnel/': ('index.html', 'fr'),   # « Mai 2022 »
    'qbot-token-luxtrust/':   ('index.html', 'fr'),   # « Juin 2022 »
    'decembre-2022/':         ('index.html', 'fr'),
    'juin-2023/':             ('index.html', 'fr'),
    'decembre-2023/':         ('index.html', 'fr'),
    'en/february-2022/':      ('en/index.html', 'en'),
    'en/may-2022/':           ('en/index.html', 'en'),
    'en/june-2022/':          ('en/index.html', 'en'),
    'en/december-2022/':      ('en/index.html', 'en'),
    'en/june-2023/':          ('en/index.html', 'en'),
    'en/december-2023/':      ('en/index.html', 'en'),

    # ---- archives WordPress (catégories, étiquettes, auteurs) ----
    'category/presse/':                 ('index.html', 'fr'),
    'category/timeline/':               ('index.html', 'fr'),
    'tag/2fa/':                         ('index.html', 'fr'),
    'tag/automatisation-des-tests/':    ('index.html', 'fr'),
    'author/marie-krust/':              ('index.html', 'fr'),
    'author/sstefancic/':               ('index.html', 'fr'),
    'en/category/timeline-en/':         ('en/index.html', 'en'),

    # ---- thème WordPress de démonstration ----
    # ARBITRÉ PAR LE CLIENT LE 2026-08-25 : plus aucune 404. Ces dix-huit adresses
    # sont du contenu factice jamais remplacé (même lot que l'équipe fictive
    # « Colabrio ») et n'ont aucun équivalent sur le nouveau site. Elles renvoient
    # donc à l'accueil.
    # LE COMPROMIS, ÉNONCÉ UNE FOIS : un moteur peut lire dix-huit redirections
    # sans rapport comme des soft-404, ce qui vaut à peu près une 404 côté
    # référencement. En échange, un humain qui clique un vieux lien atterrit sur
    # le produit au lieu d'une page d'erreur. C'est l'humain qui a été privilégié.
    'portfolio/appearance-design-of-website-pages/':        ('index.html', 'fr'),
    'portfolio/beautiful-design-of-mobile-application/':    ('index.html', 'fr'),
    'portfolio/buy-and-sell-first-class-electronics/':      ('index.html', 'fr'),
    'portfolio/designing-a-mobile-store-application/':      ('index.html', 'fr'),
    'portfolio/graphic-design-of-mobile-pages/':            ('index.html', 'fr'),
    'portfolio/implement-a-variety-of-internal-site-pages/':('index.html', 'fr'),
    'portfolio/intersting-stories-about-it-world/':         ('index.html', 'fr'),
    'portfolio/login-mobile-interface-illustrations/':      ('index.html', 'fr'),
    'portfolio/providing-computer-services-to-companies/':  ('index.html', 'fr'),
    'portfolio/responsive-design-for-a-variety-of-sizes/':  ('index.html', 'fr'),
    'portfolio/some-new-ideas-for-branding/':               ('index.html', 'fr'),
    'portfolio/store-advertising-banner-design/':           ('index.html', 'fr'),
    'portfolio/the-difference-between-ui-and-ux-in-design/':('index.html', 'fr'),
    'portfolio/the-future-of-food-delivery-app-ui-kit/':    ('index.html', 'fr'),
    'portfolio-cat/ecommerce/':                             ('index.html', 'fr'),
    'portfolio-cat/graphic-templates/':                     ('index.html', 'fr'),
    'portfolio-cat/ux-and-ui-kits/':                        ('index.html', 'fr'),
    'portfolio-tag/uncategorized/':                         ('index.html', 'fr'),
}
