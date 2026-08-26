#!/usr/bin/env python3
"""Génère le guide « Tester une authentification LuxTrust en automatisé », FR + EN.

POURQUOI UN SCRIPT ET PAS DEUX FICHIERS ÉCRITS À LA MAIN. Les passes d'audit ont
reproché plusieurs fois aux pages écrites l'une après l'autre d'avoir divergé de
structure. Même choix que `gen-legal.py` et que les pages de cas d'usage : un
gabarit, deux jeux de textes.

L'HABILLAGE EST EXTRAIT D'UNE PAGE EXISTANTE, JAMAIS RETAPÉ. En-tête, barre de
navigation, pied de page et fin de document sont découpés dans `cas-usage.html`
(FR) et `en/use-cases.html` (EN). C'est la règle apprise à ses dépens sur ce
dépôt : on ne retape pas une chaîne d'un fichier, on l'extrait. Conséquence
utile : si le pied de page change, une régénération suffit.

CE QUE LE GUIDE APPLIQUE, ET QUI VIENT DE L'AUDIT ROSOAI :
  - le format guide, pas la page produit (cinq fois sur cinq dans les résultats) ;
  - chaque titre est une QUESTION, suivie d'une réponse autonome de 40 à 60 mots ;
  - une source vérifiable tous les 150 à 200 mots ;
  - une date de mise à jour visible ;
  - et le courage de dire dans quel cas le concurrent gagne. C'est la section
    « Dans quels cas un robot n'est pas la bonne réponse », qui envoie le lecteur
    vers une bibliothèque TOTP gratuite. Une comparaison qui gagne sur tous les
    critères n'est crue par personne.

    python3 tools/gen-guide-luxtrust.py
    python3 tools/bump-assets.py     # ensuite, toujours
"""

import io
import os
import re

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL_FR = 'https://q-bot.eu/automatiser-authentification-luxtrust.html'
URL_EN = 'https://q-bot.eu/en/automate-luxtrust-authentication.html'
MAJ_ISO, MAJ_FR, MAJ_EN = '2026-08-26', '26 août 2026', '26 August 2026'

CHECK = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
         '<polyline points="4,12 9,17 20,6"/></svg>')


def liste(items):
    out = ['    <ul class="api-facts">']
    for t in items:
        out.append('        <li>' + CHECK + '<span>' + t + '</span></li>')
    out.append('    </ul>')
    return '\n'.join(out)


def bloc(idc, label, titre, capsule, corps):
    return f'''
<section class="section" aria-labelledby="{idc}">
  <div class="container">
    <div class="section-header">
      <span class="section-label">{label}</span>
      <h2 class="section-title" id="{idc}">{titre}</h2>
      <p class="section-subtitle">{capsule}</p>
    </div>
{corps}
  </div>
</section>
'''


# ══════════════════════════════════════════════════════════════════════════════
# LES TEXTES. Le français n'est pas une traduction littérale de l'anglais (règle
# du dépôt) : même substance, chacun dans ses propres moyens.
# ══════════════════════════════════════════════════════════════════════════════
FR = dict(
    lang='fr', autre='en/automate-luxtrust-authentication.html',
    fichier='automatiser-authentification-luxtrust.html',
    donneur='cas-usage.html', locale='fr_FR',
    title="Tester une authentification LuxTrust en automatisé | Q-Bot",
    desc="Une validation LuxTrust ne se calcule pas, elle s'approuve sur le téléphone. Où s'arrête Selenium, et comment franchir l'étape sur un vrai appareil Android.",
    fil='Guide LuxTrust', accueil='Accueil',
    label='Guide', h1="Tester une authentification LuxTrust en automatisé",
    lead="Une authentification LuxTrust ne se calcule pas&nbsp;: elle s'approuve, sur le téléphone de l'utilisateur. Aucune bibliothèque ne peut la reproduire, parce qu'il n'existe aucun secret partagé à recalculer. Ce guide explique où s'arrêtent Selenium et Cypress, et comment franchir cette étape sur un vrai appareil Android.",
    datel=f'Mis à jour le <time datetime="{MAJ_ISO}">{MAJ_FR}</time>',
    cta_h2="Vous voulez le voir sur votre propre parcours&nbsp;?",
    cta_h3="Réservez une démo", cta_btn="Prendre rendez-vous", cta_href='contact.html',
    sections=[
        dict(id='pourquoi-title', label='Le point de départ',
             titre="Pourquoi une authentification LuxTrust ne s'automatise pas comme un code Authenticator&nbsp;?",
             capsule="Un code Authenticator est un calcul. La norme TOTP part d'un secret partagé et de l'heure, donc une bibliothèque gratuite le reproduit sans téléphone. Une validation LuxTrust n'est pas un calcul&nbsp;: elle s'approuve dans l'application, sur l'appareil. Il n'existe aucun secret à recalculer, donc rien à simuler.",
             corps="""    <p>La différence tient en une phrase&nbsp;: dans un cas vous possédez la clé, dans l'autre non.</p>
    <p>Un code à six chiffres d'application d'authentification suit la norme <a href="https://www.rfc-editor.org/rfc/rfc6238" target="_blank" rel="noopener">TOTP, décrite par la RFC&nbsp;6238</a>. Elle prend un secret partagé, y ajoute l'heure courante, et produit le code. Ce secret, votre équipe l'a reçu au moment de l'enrôlement&nbsp;: elle peut donc recalculer le code dans le test lui-même, sans aucun appareil.</p>
    <p>Une validation par <a href="https://www.luxtrust.com/" target="_blank" rel="noopener">LuxTrust</a> ne fonctionne pas ainsi. Il n'y a pas de code à recalculer&nbsp;: il y a une demande qui arrive sur l'appareil enrôlé, et un geste humain qui l'approuve. Le secret ne quitte jamais l'appareil, ce qui est précisément l'intérêt du dispositif. Aucune bibliothèque ne peut se mettre à sa place, et c'est voulu.</p>
    <p>Conséquence pour votre chaîne de tests&nbsp;: la seule façon d'approuver, c'est d'appuyer. Sur un vrai appareil.</p>"""),
        dict(id='outils-title', label='Ce que font les outils du marché',
             titre="Où s'arrêtent Selenium, Cypress et Playwright&nbsp;?",
             capsule="Ces trois outils pilotent un navigateur, et ils le font très bien. L'approbation 2FA, elle, se passe dans une application, sur un téléphone, hors du navigateur&nbsp;: aucun sélecteur ne l'atteint. La documentation de Selenium le dit elle-même et conseille de désactiver la double authentification en test.",
             corps="""    <p>Ce n'est pas une faiblesse de ces outils, c'est leur périmètre. Un pilote de navigateur agit sur le document affiché&nbsp;; il n'a aucune prise sur une notification système ni sur une application native.</p>
    <p>La <a href="https://www.selenium.dev/documentation/test_practices/discouraged/two_factor_authentication/" target="_blank" rel="noopener">documentation de Selenium consacre une page à la question</a> et recommande trois voies&nbsp;: désactiver la double authentification dans l'environnement de test, la désactiver pour un compte donné, ou récupérer le secret partagé pour recalculer le code.</p>
    <p>Les trois se tiennent. Mais lisez la définition qu'elle emploie&nbsp;: elle décrit la 2FA comme un code reçu par application, par SMS ou par courriel. Elle ne parle ni des demandes à approuver, ni des applications d'identité souveraine. Sa frontière est là, et c'est exactement l'endroit où votre parcours réel se trouve si vos utilisateurs se connectent avec LuxTrust ou <a href="https://www.itsme-id.com/" target="_blank" rel="noopener">itsme</a>.</p>
    <p>Et désactiver la 2FA a un coût qu'on énonce rarement&nbsp;: vous ne testez plus le parcours que vos utilisateurs empruntent.</p>"""),
        dict(id='pas-nous-title', label='Le cas où nous ne sommes pas la réponse',
             titre="Dans quels cas un robot n'est pas la bonne réponse&nbsp;?",
             capsule="Pour Google Authenticator ou Microsoft Authenticator, n'achetez rien. Ce sont des codes TOTP&nbsp;: une bibliothèque de quelques lignes les calcule, gratuitement, plus vite qu'un appareil physique. Un robot ne se justifie que là où il n'y a aucun secret à récupérer, donc aucun calcul possible.",
             corps="""    <p>Nous préférons le dire ici plutôt que de vous le laisser découvrir&nbsp;: si votre double authentification repose sur un code TOTP dont vous détenez le secret, la bonne solution est une bibliothèque, pas un robot. Elle est gratuite, elle s'exécute en une milliseconde, elle ne tombe pas en panne et elle ne demande aucun matériel.</p>
    <p>Un appareil réel piloté n'a de valeur que dans les situations où il n'y a rien à calculer&nbsp;:</p>
""" + liste([
                 "une demande à <strong>approuver</strong> sur l'appareil enrôlé, sans code à saisir&nbsp;: LuxTrust Mobile, itsme",
                 "un code qui n'existe <strong>que</strong> sur l'écran de l'application, sans secret partagé remis à votre équipe",
                 "un QR code affiché sur un second écran, que l'appareil doit venir scanner",
                 "un parcours que vous devez tester <strong>tel que l'utilisateur le vit</strong>, sans rien désactiver",
             ]) + """
    <p style="margin-top:26px;">Si aucune de ces quatre lignes ne décrit votre situation, gardez votre bibliothèque TOTP&nbsp;: elle fait le travail.</p>"""),
        dict(id='comment-title', label='La méthode',
             titre="Comment Q-Bot franchit une validation LuxTrust&nbsp;?",
             capsule="Un vrai téléphone Android, relié en USB au boîtier, piloté par ADB. Chaque appui arrive sur l'écran physique, dans la véritable application. Le scénario se construit à la souris sur une capture de cet écran&nbsp;: des points d'appui numérotés et des temps d'attente, aucun script à écrire.",
             corps="""    <p>Le principe est volontairement simple&nbsp;: puisque la seule façon d'approuver est d'appuyer, on appuie pour de bon.</p>
""" + liste([
                 "Le téléphone est un appareil Android ordinaire, celui de votre environnement de test, relié en USB au boîtier et piloté par <a href=\"https://developer.android.com/tools/adb\" target=\"_blank\" rel=\"noopener\">ADB</a>",
                 "Vous versez une capture de l'écran de l'application 2FA, qui sert de fond à l'étape, et vous posez les points d'appui en cliquant dessus",
                 "Vous réglez les temps d'attente à la milliseconde, pour coller au comportement réel de l'application",
                 "Votre test déclenche le scénario par un appel HTTP, ou laisse l'app compagnon le déclencher seule dès qu'une notification 2FA arrive",
                 "Quand l'écran affiche un code, un point d'entrée dédié le renvoie à votre test",
             ]) + """
    <p style="margin-top:26px;">Il n'y a ni simulateur, ni bouchon, ni SDK à intégrer dans votre application. La <a href="caracteristiques.html">fiche technique détaille l'éditeur de scénarios et la pile matérielle</a>.</p>"""),
        dict(id='appel-title', label='Dans votre chaîne de tests',
             titre="À quoi ressemble l'appel depuis votre test&nbsp;?",
             capsule="À une requête HTTP, et rien de plus. Si votre outil sait appeler une URL, il sait piloter le robot&nbsp;: aucun SDK, aucun greffon, aucune clé d'API. Le test déclenche le scénario, attend la réponse, et reprend son cours là où il s'était arrêté.",
             corps="""    <figure class="ucs__snippet code-panel">
      <figcaption>Python / Selenium</figcaption>
      <div class="code-block"><pre><code># L'utilisateur a saisi ses identifiants,
# LuxTrust attend son approbation.
import requests

requests.get(
  &quot;http://q-bot.local:8000&quot;
  &quot;/scenarios/42/execute&quot;
)

# Le robot a approuvé sur le téléphone.
# Le test reprend son cours.
driver.find_element(
  By.ID, &quot;dashboard&quot;
).is_displayed()</code></pre></div>
    </figure>
    <p style="margin-top:26px;">Trois points d'entrée couvrent les cas courants&nbsp;: exécuter un scénario, lire le code affiché, afficher un QR code sur l'écran du boîtier. Ils sont documentés sur la <a href="caracteristiques.html">fiche technique</a>, et <a href="cas-usage.html">les exemples d'appel par outil</a> couvrent Cypress, Playwright, Robot Framework et JUnit.</p>"""),
        dict(id='limites-title', label='Les limites, énoncées',
             titre="Qu'est-ce que cela n'automatise pas&nbsp;?",
             capsule="Q-Bot pilote un appareil <strong>Android</strong>. Il n'automatise pas la double authentification sur iOS, et cette limite ne se contourne pas&nbsp;: le pilotage repose sur ADB, qui n'a pas d'équivalent sur iPhone. L'appareil doit aussi être physiquement relié au boîtier.",
             corps="""    <p>Trois choses qu'il vaut mieux savoir avant qu'après&nbsp;:</p>
""" + liste([
                 "<strong>Android uniquement.</strong> Si votre parcours doit être validé sur iPhone, ce n'est pas l'outil",
                 "<strong>Un appareil physique par boîtier.</strong> Le téléphone est relié en USB, il n'est pas dans un nuage",
                 "<strong>Une application, pas un boîtier matériel.</strong> Un jeton physique à écran n'entre pas dans ce modèle",
             ]) + """
    <p style="margin-top:26px; font-size:0.9375rem;">Q-Bot est un produit de Q-Leap&nbsp;S.A. et n'est ni édité, ni distribué, ni approuvé par LuxTrust. Les noms cités appartiennent à leurs détenteurs respectifs.</p>"""),
        dict(id='donnees-title', label='Sécurité et données',
             titre="Où vont les données de vos tests&nbsp;?",
             capsule="Nulle part. Les scénarios et leurs captures d'écran restent dans le boîtier, sur votre réseau, dans une base locale. Aucun envoi vers un service en ligne, et aucune connexion internet n'est nécessaire pendant l'exécution des tests. C'est ce qui rend l'outil défendable devant une équipe sécurité.",
             corps="""    <p>C'est souvent la question qui décide, et elle ne vient pas du testeur&nbsp;: elle vient de la personne qui doit signer.</p>
""" + liste([
                 "Les scénarios et leurs captures sont stockés dans le boîtier, jamais sur un service en ligne",
                 "Aucune connexion internet n'est nécessaire pendant les tests",
                 "Aucune clé d'API à distribuer, donc aucun secret à faire circuler dans votre chaîne d'intégration",
                 "Le boîtier reste sur votre réseau, dans vos locaux",
             ])),
    ])

EN = dict(
    lang='en', autre='../automatiser-authentification-luxtrust.html',
    fichier='en/automate-luxtrust-authentication.html',
    donneur='en/use-cases.html', locale='en_GB',
    title="Automating a LuxTrust authentication in tests | Q-Bot",
    desc="A LuxTrust approval is not computed, it is granted on the phone. Where Selenium and Cypress stop, and how to clear that step on a real Android device.",
    fil='LuxTrust guide', accueil='Home',
    label='Guide', h1="Automating a LuxTrust authentication in your tests",
    lead="A LuxTrust authentication is not computed, it is approved on the user's phone. No library can stand in for it, because there is no shared secret left to recompute. This guide sets out where Selenium and Cypress stop, and how to clear that step on a real Android device.",
    datel=f'Updated <time datetime="{MAJ_ISO}">{MAJ_EN}</time>',
    cta_h2="Want to see it on your own login flow?",
    cta_h3="Book a demo", cta_btn="Make an appointment", cta_href='contact.html',
    sections=[
        dict(id='pourquoi-title', label='The starting point',
             titre="Why can a LuxTrust authentication not be automated like an Authenticator code?",
             capsule="An Authenticator code is a computation. The TOTP standard takes a shared secret and the current time, so a free library reproduces it with no phone involved. A LuxTrust approval is not a computation: it is granted in the app, on the device. There is no secret to recompute, so nothing to simulate.",
             corps="""    <p>The difference fits in one sentence: in one case you hold the key, in the other you do not.</p>
    <p>A six-digit authenticator code follows the <a href="https://www.rfc-editor.org/rfc/rfc6238" target="_blank" rel="noopener">TOTP standard set out in RFC&nbsp;6238</a>. It takes a shared secret, adds the current time, and produces the code. Your team received that secret at enrolment, so it can recompute the code inside the test itself, with no device at all.</p>
    <p>An approval through <a href="https://www.luxtrust.com/" target="_blank" rel="noopener">LuxTrust</a> does not work that way. There is no code to recompute: there is a request arriving on the enrolled device, and a human gesture approving it. The secret never leaves the device, which is precisely the point of the scheme. No library can stand in its place, and that is by design.</p>
    <p>What that means for your pipeline: the only way to approve is to tap. On a real device.</p>"""),
        dict(id='outils-title', label='What the usual tools do',
             titre="Where do Selenium, Cypress and Playwright stop?",
             capsule="All three drive a browser, and they do it very well. The 2FA approval, however, happens in an app, on a phone, outside the browser: no selector reaches it. Selenium's own documentation says as much, and advises turning two-factor authentication off in test environments.",
             corps="""    <p>This is not a weakness of those tools, it is their scope. A browser driver acts on the rendered document; it has no hold on a system notification or a native app.</p>
    <p>Selenium <a href="https://www.selenium.dev/documentation/test_practices/discouraged/two_factor_authentication/" target="_blank" rel="noopener">devotes a documentation page to the question</a> and recommends three routes: disable two-factor authentication in the test environment, disable it for one account, or obtain the shared secret and recompute the code.</p>
    <p>All three are sound. But read the definition it works from: it describes 2FA as a code received through an app, an SMS or an email. It does not cover requests to approve, nor sovereign identity apps. That is where its boundary sits, and it is exactly where your real login flow lives if your users sign in with LuxTrust or <a href="https://www.itsme-id.com/" target="_blank" rel="noopener">itsme</a>.</p>
    <p>And turning 2FA off carries a cost that is rarely stated: you are no longer testing the journey your users actually take.</p>"""),
        dict(id='pas-nous-title', label='Where we are not the answer',
             titre="When is a robot not the right answer?",
             capsule="For Google Authenticator or Microsoft Authenticator, buy nothing. Those are TOTP codes: a few lines of library compute them, for free, faster than any physical device. A robot only earns its place where there is no secret to obtain, and therefore nothing to compute.",
             corps="""    <p>We would rather say this here than let you find it out later: if your second factor is a TOTP code whose secret you hold, the right answer is a library, not a robot. It is free, it runs in a millisecond, it does not break down, and it needs no hardware.</p>
    <p>A driven physical device is only worth it where there is nothing to compute:</p>
""" + liste([
                 "a request to <strong>approve</strong> on the enrolled device, with no code to type: LuxTrust Mobile, itsme",
                 "a code that exists <strong>only</strong> on the app's screen, with no shared secret handed to your team",
                 "a QR code shown on a second screen that the device has to scan",
                 "a flow you need to test <strong>as the user lives it</strong>, without switching anything off",
             ]) + """
    <p style="margin-top:26px;">If none of those four lines describes your situation, keep your TOTP library: it does the job.</p>"""),
        dict(id='comment-title', label='The method',
             titre="How does Q-Bot clear a LuxTrust approval?",
             capsule="A real Android phone, connected over USB to the box, driven through ADB. Every tap lands on the physical screen, in the genuine app. The scenario is built with the mouse on a screenshot of that screen: numbered tap points and waiting times, no script to write.",
             corps="""    <p>The principle is deliberately plain: since the only way to approve is to tap, we tap for real.</p>
""" + liste([
                 "The phone is an ordinary Android device from your test environment, connected over USB and driven through <a href=\"https://developer.android.com/tools/adb\" target=\"_blank\" rel=\"noopener\">ADB</a>",
                 "You upload a screenshot of the 2FA app screen as the background of the step, then place the tap points by clicking on it",
                 "You set the waiting times to the millisecond, to match how the app really behaves",
                 "Your test triggers the scenario with an HTTP call, or lets the companion app fire it on its own as soon as a 2FA notification arrives",
                 "When the screen shows a code, a dedicated endpoint returns it to your test",
             ]) + """
    <p style="margin-top:26px;">There is no simulator, no stub, and no SDK to embed in your application. The <a href="technical-specs.html">technical page covers the scenario editor and the hardware stack</a>.</p>"""),
        dict(id='appel-title', label='In your pipeline',
             titre="What does the call from your test look like?",
             capsule="An HTTP request, and nothing more. If your tool can call a URL, it can drive the robot: no SDK, no plugin, no API key. The test triggers the scenario, waits for the answer, and picks up exactly where it left off.",
             corps="""    <figure class="ucs__snippet code-panel">
      <figcaption>Python / Selenium</figcaption>
      <div class="code-block"><pre><code># The user has entered their credentials,
# LuxTrust is waiting for approval.
import requests

requests.get(
  &quot;http://q-bot.local:8000&quot;
  &quot;/scenarios/42/execute&quot;
)

# The robot approved it on the phone.
# The test picks up where it left off.
driver.find_element(
  By.ID, &quot;dashboard&quot;
).is_displayed()</code></pre></div>
    </figure>
    <p style="margin-top:26px;">Three endpoints cover the usual cases: run a scenario, read the code on screen, show a QR code on the box's own display. They are documented on the <a href="technical-specs.html">technical page</a>, and <a href="use-cases.html">the per-tool call examples</a> cover Cypress, Playwright, Robot Framework and JUnit.</p>"""),
        dict(id='limites-title', label='The limits, stated',
             titre="What does this not automate?",
             capsule="Q-Bot drives an <strong>Android</strong> device. It does not automate two-factor authentication on iOS, and that limit has no workaround: the driving relies on ADB, which has no equivalent on iPhone. The device also has to be physically connected to the box.",
             corps="""    <p>Three things worth knowing beforehand rather than afterwards:</p>
""" + liste([
                 "<strong>Android only.</strong> If your flow has to be validated on an iPhone, this is not the tool",
                 "<strong>One physical device per box.</strong> The phone is wired over USB, it does not live in a cloud",
                 "<strong>An app, not a hardware token.</strong> A physical token with its own display does not fit this model",
             ]) + """
    <p style="margin-top:26px; font-size:0.9375rem;">Q-Bot is a Q-Leap&nbsp;S.A. product and is not published, distributed or endorsed by LuxTrust. Names quoted belong to their respective owners.</p>"""),
        dict(id='donnees-title', label='Security and data',
             titre="Where does your test data go?",
             capsule="Nowhere. Scenarios and their screenshots stay inside the box, on your network, in a local database. Nothing is sent to an online service, and no internet connection is needed while the tests run. That is what makes the tool defensible in front of a security team.",
             corps="""    <p>This is often the question that decides, and it does not come from the tester: it comes from whoever has to sign it off.</p>
""" + liste([
                 "Scenarios and their screenshots are stored in the box, never on an online service",
                 "No internet connection is needed while the tests run",
                 "No API key to hand out, so no secret circulating through your integration pipeline",
                 "The box stays on your network, in your own premises",
             ])),
    ])


def construire(cfg):
    donneur = io.open(os.path.join(RACINE, cfg['donneur']), encoding='utf-8').read()
    prof = '../' if cfg['lang'] == 'en' else ''
    base = 'https://q-bot.eu/' + ('en/' if cfg['lang'] == 'en' else '')
    url = 'https://q-bot.eu/' + cfg['fichier']

    # ---- HEAD : on garde l'Organization tel quel, on remplace le reste ----
    head = donneur[:donneur.index('</head>')]
    head = re.sub(r'<title>.*?</title>', '<title>' + cfg['title'] + '</title>', head, count=1)
    head = re.sub(r'<meta name="description" content=".*?">',
                  '<meta name="description" content="' + cfg['desc'] + '">', head, count=1)
    head = re.sub(r'<link rel="canonical" href=".*?">',
                  '<link rel="canonical" href="' + url + '">', head, count=1)
    # PAR ATTRIBUT, jamais par un bloc de trois lignes : le donneur anglais les
    # écrit dans un autre ordre (en, fr, x-default) et un motif ordonné ne
    # correspondait à rien, en silence. Même famille de piège que le motif
    # multi-lignes qui échouait sur en/technical-specs.html.
    for code, cible in (('fr', URL_FR), ('en', URL_EN), ('x-default', URL_FR)):
        head = re.sub(r'<link rel="alternate" hreflang="' + code + r'" href="[^"]*">',
                      '<link rel="alternate" hreflang="' + code + '" href="' + cible + '">',
                      head, count=1)
    for prop, val in (('og:title', cfg['title']), ('og:description', cfg['desc']),
                      ('og:url', url), ('og:type', 'article')):
        head = re.sub(r'<meta property="' + prop + r'" content=".*?">',
                      '<meta property="' + prop + '" content="' + val + '">', head, count=1)
    for name, val in (('twitter:title', cfg['title']), ('twitter:description', cfg['desc'])):
        head = re.sub(r'<meta name="' + name + r'" content=".*?">',
                      '<meta name="' + name + '" content="' + val + '">', head, count=1)

    # le fil d'Ariane structuré remplace celui du donneur, in situ
    fil = f'''{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{
      "@type": "ListItem",
      "position": 1,
      "name": "{cfg['accueil']}",
      "item": "{base}"
    }},
    {{
      "@type": "ListItem",
      "position": 2,
      "name": "{cfg['fil']}",
      "item": "{url}"
    }}
  ]
}}'''
    head = re.sub(r'\{\s*"@context": "https://schema\.org",\s*"@type": "BreadcrumbList".*?\n\}',
                  fil, head, count=1, flags=re.S)

    # TechArticle : le format guide, déclaré comme tel
    guide = f'''  <script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "{cfg['h1'].replace('&nbsp;', ' ')}",
  "description": "{cfg['desc']}",
  "datePublished": "{MAJ_ISO}",
  "dateModified": "{MAJ_ISO}",
  "inLanguage": "{cfg['lang']}",
  "image": "https://q-bot.eu/assets/img/qbot-og.jpg",
  "mainEntityOfPage": {{ "@type": "WebPage", "@id": "{url}" }},
  "author": {{ "@id": "https://q-bot.eu/#organization" }},
  "publisher": {{ "@id": "https://q-bot.eu/#organization" }},
  "about": [
    {{ "@type": "Thing", "name": "LuxTrust" }},
    {{ "@type": "Thing", "name": "two-factor authentication" }},
    {{ "@type": "Thing", "name": "test automation" }}
  ]
}}
  </script>
</head>'''
    head += guide

    # ---- HABILLAGE : du <body> au <main>, puis du </main> à la fin ----
    haut = donneur[donneur.index('<body>'):donneur.index('<main id="main">')]
    # notre page n'est pas dans le menu : on retire l'état courant du donneur
    haut = haut.replace(' class="nav__link active" aria-current="page"', ' class="nav__link"')
    haut = re.sub(r'(<div class="nav__lang">\s*<a href=")[^"]*(")',
                  r'\g<1>' + cfg['autre'] + r'\g<2>', haut, count=1)

    bas = donneur[donneur.index('</main>'):]
    # ni dans le pied de page : on rend son lien à l'entrée marquée courante
    lien_cu = 'use-cases.html' if cfg['lang'] == 'en' else 'cas-usage.html'
    nom_cu = 'Use cases' if cfg['lang'] == 'en' else "Cas d'usage"
    bas = bas.replace(f'<span aria-current="page">{nom_cu}</span>',
                      f'<a href="{lien_cu}">{nom_cu}</a>')

    corps = ''.join(bloc(s['id'], s['label'], s['titre'], s['capsule'], s['corps'])
                    for s in cfg['sections'])

    principal = f'''<main id="main">
<section class="page-hero" aria-labelledby="page-title">
  <div class="container">
    <span class="section-label">{cfg['label']}</span>
    <h1 id="page-title">{cfg['h1']}</h1>
    <p>{cfg['lead']}</p>
    <p class="guide-date">{cfg['datel']}</p>
  </div>
</section>

<div class="breadcrumb">
  <div class="container">
    <ol class="breadcrumb__list" aria-label="{'Breadcrumb' if cfg['lang'] == 'en' else "Fil d'Ariane"}">
      <li><a href="{prof}index.html">{cfg['accueil']}</a></li>
      <li><span aria-hidden="true">&rsaquo;</span></li>
      <li><span aria-current="page">{cfg['fil']}</span></li>
    </ol>
  </div>
</div>
{corps}
<section class="section" aria-labelledby="cta-guide-title">
  <div class="container cta-block">
    <h2 class="section-title" id="cta-guide-title" style="margin-bottom:16px;">{cfg['cta_h2']}</h2>
    <h3 style="font-size:1.5rem; font-weight:500; margin-bottom:32px; color:var(--teal-text);">{cfg['cta_h3']}</h3>
    <a href="{cfg['cta_href']}" class="btn btn--primary btn--lg">{cfg['cta_btn']}</a>
  </div>
</section>
'''
    return head + '\n' + haut + principal + bas


for cfg in (FR, EN):
    # les deux contraintes dures d'affichage en recherche, vérifiées avant d'écrire
    assert len(cfg['title']) <= 62, (cfg['fichier'], 'titre', len(cfg['title']))
    assert len(cfg['desc']) <= 158, (cfg['fichier'], 'description', len(cfg['desc']))
    s = construire(cfg)
    # Le cadratin est interdit dans le CONTENU, pas dans les commentaires : ceux de
    # l'habillage extrait en contiennent encore, et ils ne sont pas lus par le
    # visiteur. Le contrôle porte donc sur le document commentaires retirés, et sur
    # le caractère ET l'entité (cinq cadratins avaient déjà échappé à une recherche
    # du seul caractère parce qu'ils étaient écrits `&mdash;`).
    visible = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    assert '—' not in visible and '&mdash;' not in visible, (cfg['fichier'], 'cadratin')
    chemin = os.path.join(RACINE, cfg['fichier'])
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    io.open(chemin, 'w', encoding='utf-8').write(s)
    print(f"  écrit {cfg['fichier']:34s} titre {len(cfg['title'])} c, description {len(cfg['desc'])} c")
