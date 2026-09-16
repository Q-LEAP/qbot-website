#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La page « méthodes d'authentification », dans les deux langues.

    python3 tools/gen-methodes-auth.py
    node tools/bump-assets.mjs

POURQUOI UNE PAGE ET PAS UN BLOC. Relevé le 2026-09-16 : « QR code » et « code à
usage unique » n'apparaissaient dans AUCUN titre de page ni AUCUNE
méta-description du site. Ils vivaient dans deux réponses de FAQ repliées, deux
`h3` de `cas-usage.html` et un `h2` de la documentation. Une requête longue
traîne se gagne sur le titre et le `h1`, pas sur un `h3` enfoui.

LA PAGE EST CLONÉE DE SA DONNEUSE (`cas-usage.html` / `en/use-cases.html`), même
profondeur, donc aucun chemin relatif à réécrire. Barre de navigation, pied de
page, polices et bloc Organization restent ceux du site et le RESTENT : il suffit
de relancer après une passe sitewide. C'est la leçon de `gen-legal.py`, qui avait
accumulé cinq régressions faute d'avoir tourné.

TOUT EST SOURCÉ DANS LE SITE, RIEN N'EST INVENTÉ : la validation dans l'app vient
du mécanisme même, l'OTP de `GET /get-luxtrust-otp`, le QR code de
`POST /display-image` et de l'écran intégré, la notification de l'app compagnon.

LE SMS EST MARQUÉ `A_CONFIRMER` : il est plausible (le téléphone piloté reçoit
bien ses SMS) mais il n'est documenté nulle part dans le produit. Le client l'a
demandé pour la branche d'aperçu le 2026-09-16, le temps de vérifier auprès de
Sylvain Perez. NE PAS LE FAIRE PASSER SUR `main` SANS CETTE CONFIRMATION.

LA BIOMÉTRIE N'EST PAS LISTÉE, ET C'EST DÉLIBÉRÉ : Q-Bot pilote le téléphone par
ADB, c'est-à-dire par des appuis. Un appui ne satisfait pas un capteur
d'empreinte ni une reconnaissance faciale. L'annoncer serait une revendication
fausse, pas une incertitude. Elle est donc énoncée comme une LIMITE, ce qui est
la façon dont ce dépôt traite déjà le périmètre iOS.
"""
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PUBLIE = MODIFIE = '2026-09-16'

COCHE = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
         '<polyline points="4,12 9,17 20,6"/></svg>')

PAGES = [
    dict(lang='fr', sortie='methodes-authentification.html', donneuse='cas-usage.html',
         url='https://q-bot.eu/methodes-authentification.html',
         alt='https://q-bot.eu/en/authentication-methods.html'),
    dict(lang='en', sortie='en/authentication-methods.html', donneuse='en/use-cases.html',
         url='https://q-bot.eu/en/authentication-methods.html',
         alt='https://q-bot.eu/methodes-authentification.html'),
]

META = {
    'fr': dict(
        titre="Méthodes 2FA automatisées : OTP, QR code | Q-Bot by Q-Leap",
        desc=("Code à usage unique, QR code à scanner, notification à confirmer : "
              "Q-Bot franchit l'étape de double authentification de vos tests, "
              "sur la vraie application."),
        label="Méthodes d'authentification",
        h1="Les méthodes d'authentification que <span class=\"nb\">Q-Bot</span> automatise",
        h1_txt="Les méthodes d'authentification que Q-Bot automatise",
        chapeau=("Une double authentification ne prend pas toujours la même forme. Selon "
                 "l'application et le parcours, il faut valider une demande, saisir un code à "
                 "usage unique, scanner un QR code ou confirmer une notification. Q-Bot les "
                 "traite sur le véritable téléphone, sans clé secrète et sans simulateur.")),
    'en': dict(
        titre="Automated 2FA methods: OTP, QR code | Q-Bot by Q-Leap",
        desc=("One-time passcode, QR code to scan, notification to confirm: Q-Bot clears "
              "the two-factor authentication step in your tests, on the real app."),
        label="Authentication methods",
        h1="The authentication methods <span class=\"nb\">Q-Bot</span> automates",
        h1_txt="The authentication methods Q-Bot automates",
        chapeau=("Two-factor authentication does not always take the same shape. Depending on "
                 "the app and the journey, you approve a request, type a one-time passcode, "
                 "scan a QR code or confirm a notification. Q-Bot handles all of them on the "
                 "real phone, with no shared secret and no simulator.")),
}

# Chaque section : un `h2` en QUESTION suivi d'une réponse autonome de 40 à 60
# mots, la fenêtre que l'audit RosoAI mesure comme celle où un moteur de réponse
# recopie un paragraphe au lieu de le résumer. Le script le VÉRIFIE.
SECTIONS = {
    'fr': [
        dict(id='m-app', label='Validation dans l\'application', gris=False,
             titre="Comment Q-Bot valide une demande dans l'application 2FA&nbsp;?",
             capsule=("Q-Bot rejoue sur le téléphone le parcours que vous avez enregistré&nbsp;: il "
                      "ouvre l'application, appuie aux endroits que vous avez désignés et confirme "
                      "la demande. Rien n'est simulé et aucune clé secrète n'est nécessaire, "
                      "puisque c'est la véritable application d'authentification qui valide, sur un "
                      "appareil réel posé sur votre réseau."),
             faits=["Fonctionne avec toute application 2FA qui tourne sous Android",
                    "Validé avec LuxTrust Mobile, itsme, Microsoft Authenticator et Google Authenticator",
                    "Aucun secret partagé à extraire ni à stocker"]),
        dict(id='m-otp', label='Code à usage unique', gris=True,
             titre="Q-Bot peut-il récupérer un code à usage unique (OTP)&nbsp;?",
             capsule=("Oui. L'API expose <code>GET /get-luxtrust-otp</code>, qui renvoie le code à "
                      "usage unique affiché par l'application sur le téléphone relié. Votre test "
                      "récupère la valeur et la saisit là où il en a besoin. Le code est lu sur la "
                      "véritable application, il n'est jamais recalculé depuis une clé secrète."),
             faits=["Le code est lu à l'écran, pas régénéré depuis un secret TOTP",
                    "Fonctionne avec les applications dont le secret n'est pas exportable"]),
        dict(id='m-qr', label='QR code', gris=False,
             titre="Comment automatiser un parcours qui demande de scanner un QR code&nbsp;?",
             capsule=("Le boîtier porte un petit écran intégré, et l'API expose "
                      "<code>POST /display-image</code> pour y afficher une image. Un parcours qui "
                      "demande de scanner un QR code se déroule donc en entier&nbsp;: votre test "
                      "envoie l'image, le téléphone posé dans le socle la scanne, et la validation "
                      "se poursuit sans personne devant l'écran."),
             faits=["L'écran du boîtier affiche l'image, le téléphone la scanne",
                    "Le parcours se déroule de bout en bout, sans intervention"]),
        dict(id='m-push', label='Notification', gris=True,
             titre="Comment Q-Bot répond à une notification d'authentification&nbsp;?",
             capsule=("Une application compagnon installée sur le téléphone surveille les "
                      "notifications des applications 2FA. Dès qu'une demande arrive, elle "
                      "déclenche le scénario correspondant et la validation se fait seule, sans "
                      "aucun appel depuis votre chaîne de tests. C'est le second mode de "
                      "déclenchement, à côté de l'appel HTTP."),
             faits=["Le scénario part de lui-même à l'arrivée de la notification",
                    "Aucun appel à écrire dans la chaîne de tests"]),
        dict(id='m-sms', label='SMS', gris=False, a_confirmer=True,
             titre="Et un code reçu par SMS&nbsp;?",
             capsule=("Le téléphone piloté par Q-Bot est un vrai smartphone Android, avec sa carte "
                      "SIM&nbsp;: il reçoit ses messages comme n'importe quel appareil. Un scénario "
                      "peut donc ouvrir l'application de messagerie, lire le code reçu et le "
                      "reporter dans le parcours, exactement comme le ferait la personne assise "
                      "devant l'écran."),
             faits=["Le code est lu sur l'appareil, il ne transite par aucun service tiers"]),
        dict(id='m-limites', label='Périmètre', gris=True,
             titre="Ce que Q-Bot n'automatise pas",
             capsule=("Q-Bot pilote un appareil Android par ADB, c'est-à-dire par des appuis sur "
                      "l'écran. Il ne franchit donc pas une empreinte digitale ni une "
                      "reconnaissance faciale, qui demandent un capteur biométrique. Il ne pilote "
                      "pas non plus d'iPhone&nbsp;: l'automatisation de la 2FA sur iOS sort de son "
                      "périmètre."),
             faits=["Android uniquement, un appareil filaire par boîtier",
                    "Outil de test, à utiliser avec des comptes dédiés"]),
    ],
    'en': [
        dict(id='m-app', label='In-app approval', gris=False,
             titre="How does Q-Bot approve a request inside the 2FA app?",
             capsule=("Q-Bot replays on the phone the journey you recorded: it opens the app, taps "
                      "where you pointed and confirms the request. Nothing is simulated and no "
                      "shared secret is needed, because the real authentication app is the one "
                      "approving, on an actual device sitting on your own network."),
             faits=["Works with any 2FA app running on Android",
                    "Validated with LuxTrust Mobile, itsme, Microsoft Authenticator and Google Authenticator",
                    "No shared secret to extract or store"]),
        dict(id='m-otp', label='One-time passcode', gris=True,
             titre="Can Q-Bot retrieve a one-time passcode (OTP)?",
             capsule=("Yes. The API exposes <code>GET /get-luxtrust-otp</code>, which returns the "
                      "one-time passcode displayed by the app on the connected phone. Your test "
                      "picks up the value and types it where it needs to. The code is read from "
                      "the real app, never recomputed from a shared secret."),
             faits=["The code is read on screen, not regenerated from a TOTP secret",
                    "Works with apps whose secret cannot be exported"]),
        dict(id='m-qr', label='QR code', gris=False,
             titre="How do you automate a journey that asks you to scan a QR code?",
             capsule=("The device carries a small built-in screen, and the API exposes "
                      "<code>POST /display-image</code> to show an image on it. A journey that "
                      "requires scanning a QR code therefore runs end to end: your test sends the "
                      "image, the phone in the dock scans it, and the journey carries on with "
                      "nobody in front of the screen."),
             faits=["The device screen shows the image, the phone scans it",
                    "The journey runs end to end, with no human step"]),
        dict(id='m-push', label='Notification', gris=True,
             titre="How does Q-Bot answer an authentication notification?",
             capsule=("A companion app installed on the phone watches notifications from 2FA apps. "
                      "As soon as a request arrives, it fires the matching scenario and the "
                      "approval happens on its own, with no call from your test suite at all. "
                      "This is the second trigger, alongside the HTTP call."),
             faits=["The scenario starts by itself when the notification lands",
                    "No call to write into your test suite"]),
        dict(id='m-sms', label='SMS', gris=False, a_confirmer=True,
             titre="What about a code received by SMS?",
             capsule=("The phone Q-Bot drives is a real Android smartphone with its own SIM card: "
                      "it receives messages like any other device. A scenario can therefore open "
                      "the messaging app, read the code that arrived and carry it into the "
                      "journey, exactly as the person sitting in front of the screen would have "
                      "done."),
             faits=["The code is read on the device, it goes through no third-party service"]),
        dict(id='m-limites', label='Scope', gris=True,
             titre="What Q-Bot does not automate",
             capsule=("Q-Bot drives an Android device over ADB, which means through taps on the "
                      "screen. It therefore does not clear a fingerprint or a face scan, both of "
                      "which need a biometric sensor. It does not drive an iPhone either: "
                      "automating 2FA on iOS is outside its scope."),
             faits=["Android only, one wired device per unit",
                    "A testing tool, to be used with dedicated accounts"]),
    ],
}


def mots(html):
    """Compte les mots du texte RENDU : on retire les balises, pas on les compte."""
    t = re.sub(r'<[^>]+>', ' ', html).replace('&nbsp;', ' ')
    return len([m for m in re.split(r'\s+', t) if m.strip(' .,:;!?')])


def extraire(t, debut, fin):
    d = t.index(debut)
    return t[d:t.index(fin, d) + len(fin)]


def section_html(s):
    gris = ' section--gray' if s.get('gris') else ''
    faits = ''
    if s.get('faits'):
        li = '\n'.join(f'      <li>{COCHE}<span>{f}</span></li>' for f in s['faits'])
        faits = f'\n    <ul class="api-facts">\n{li}\n    </ul>'
    marque = ''
    if s.get('a_confirmer'):
        marque = ('\n  <!-- A_CONFIRMER : capacité plausible mais non documentée dans le produit.\n'
                  '       Demandée pour la branche d\'aperçu le 2026-09-16, en attente de\n'
                  '       Sylvain Perez. NE PAS FAIRE PASSER SUR main SANS CONFIRMATION. -->')
    return (f'<section class="section{gris}" aria-labelledby="{s["id"]}">{marque}\n'
            f'  <div class="container">\n'
            f'    <div class="section-header">\n'
            f'      <span class="section-label">{s["label"]}</span>\n'
            f'      <h2 class="section-title" id="{s["id"]}">{s["titre"]}</h2>\n'
            f'      <p class="section-subtitle">{s["capsule"]}</p>\n'
            f'    </div>{faits}\n'
            f'  </div>\n</section>\n')


def techarticle(page, meta):
    return ('<script type="application/ld+json">\n  {\n'
            '    "@context": "https://schema.org",\n'
            '    "@type": "TechArticle",\n'
            f'    "headline": "{meta["h1_txt"]}",\n'
            f'    "description": "{meta["desc"]}",\n'
            f'    "url": "{page["url"]}",\n'
            f'    "inLanguage": "{page["lang"]}",\n'
            f'    "datePublished": "{PUBLIE}",\n'
            f'    "dateModified": "{MODIFIE}",\n'
            '    "image": "https://q-bot.eu/assets/img/qbot-og.jpg",\n'
            '    "author": { "@id": "https://q-bot.eu/#organization" },\n'
            '    "isPartOf": { "@type": "WebSite", "name": "Q-Bot", "url": "https://q-bot.eu/" },\n'
            '    "about": { "@type": "Product", "name": "Q-Bot" },\n'
            '    "publisher": { "@id": "https://q-bot.eu/#organization" }\n'
            '  }\n  </script>')


def main():
    fr, en = SECTIONS['fr'], SECTIONS['en']
    assert [x['id'] for x in fr] == [x['id'] for x in en], 'les deux langues divergent'
    for a, b in zip(fr, en):
        assert sorted(a) == sorted(b), 'section %s : clés différentes' % a['id']

    for page in PAGES:
        lang = page['lang']
        meta, secs = META[lang], SECTIONS[lang]

        assert len(meta['titre']) <= 62, '%s : titre %d caractères' % (lang, len(meta['titre']))
        assert len(meta['desc']) <= 158, '%s : description %d caractères' % (lang, len(meta['desc']))
        for s in secs:
            n = mots(s['capsule'])
            assert 40 <= n <= 60, '%s / %s : réponse de %d mots, attendu 40 à 60' % (lang, s['id'], n)

        src = (RACINE / page['donneuse']).read_text(encoding='utf-8')

        parts = [f'<main id="main">\n'
                 f'<section class="page-hero" aria-labelledby="page-title">\n'
                 f'  <div class="container">\n'
                 f'    <span class="section-label">{meta["label"]}</span>\n'
                 f'    <h1 id="page-title">{meta["h1"]}</h1>\n'
                 f'    <p>{meta["chapeau"]}</p>\n'
                 f'  </div>\n</section>\n']
        parts += [section_html(s) for s in secs]
        parts.append(extraire(src, '<section class="section section--dark" aria-labelledby="cta-title"',
                              '</section>') + '\n')
        t = src[:src.index('<main')] + '\n'.join(parts) + '</main>' + src[src.index('</main>') + 7:]

        for motif, neuf in [
            (r'<title>.*?</title>', f'<title>{meta["titre"]}</title>'),
            (r'<meta name="description" content="[^"]*">',
             f'<meta name="description" content="{meta["desc"]}">'),
            (r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{page["url"]}">'),
            (r'<meta property="og:title" content="[^"]*">',
             f'<meta property="og:title" content="{meta["titre"]}">'),
            (r'<meta property="og:description" content="[^"]*">',
             f'<meta property="og:description" content="{meta["desc"]}">'),
            (r'<meta property="og:url" content="[^"]*">',
             f'<meta property="og:url" content="{page["url"]}">'),
            (r'<meta name="twitter:title" content="[^"]*">',
             f'<meta name="twitter:title" content="{meta["titre"]}">'),
            (r'<meta name="twitter:description" content="[^"]*">',
             f'<meta name="twitter:description" content="{meta["desc"]}">'),
        ]:
            t, n = re.subn(motif, lambda m: neuf, t, count=1, flags=re.S)
            assert n == 1, f'{lang} : en-tête, motif sans effet : {motif}'

        for h, cible in (('fr', page['url'] if lang == 'fr' else page['alt']),
                         ('en', page['alt'] if lang == 'fr' else page['url']),
                         ('x-default', page['url'] if lang == 'fr' else page['alt'])):
            t, n = re.subn(rf'(<link rel="alternate" hreflang="{h}" href=")[^"]*(">)',
                           lambda m, c=cible: m.group(1) + c + m.group(2), t, count=1)
            assert n == 1, f'{lang} : hreflang {h} introuvable'

        # LA DONNEUSE N'A PAS DE BLOC `Product` À REMPLACER : `cas-usage.html` ne
        # porte qu'un `Organization` et un `BreadcrumbList`. On INSÈRE donc le
        # TechArticle juste avant le fil d'Ariane, et on remplace s'il existe
        # déjà, pour que le script reste idempotent.
        if '"TechArticle"' in t:
            t = re.sub(r'<script type="application/ld\+json">\s*\{\s*"@context": "https://schema\.org",\s*'
                       r'"@type": "TechArticle".*?</script>', lambda m: techarticle(page, meta),
                       t, count=1, flags=re.S)
        else:
            ancre = t.index('<script type="application/ld+json">', t.index('"BreadcrumbList"') - 400)
            t = t[:ancre] + techarticle(page, meta) + '\n  ' + t[ancre:]
        assert t.count('"TechArticle"') == 1, f'{lang} : TechArticle non posé une seule fois'
        t = re.sub(r'("BreadcrumbList".*?"position": 2,\s*"name": ")[^"]*(",\s*"item": ")[^"]*(")',
                   lambda m: m.group(1) + meta['h1_txt'] + m.group(2) + page['url'] + m.group(3),
                   t, count=1, flags=re.S)

        assert '—' not in re.sub(r'<!--.*?-->', '', t, flags=re.S), f'{lang} : cadratin'
        (RACINE / page['sortie']).write_text(t, encoding='utf-8')
        print(f'  écrit {page["sortie"]:34s} {len(t):7d} octets · {len(secs)} sections')


if __name__ == '__main__':
    main()
