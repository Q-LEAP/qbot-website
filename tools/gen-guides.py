#!/usr/bin/env python3
"""Génère les guides du blog, en français et en anglais, depuis un gabarit unique.

    python3 tools/gen-guides.py
    python3 tools/bump-assets.py     # ensuite, toujours

POURQUOI UN SCRIPT ET PAS DES FICHIERS ÉCRITS À LA MAIN. Les passes d'audit ont
reproché plusieurs fois aux pages écrites l'une après l'autre d'avoir divergé de
structure. Un gabarit, deux jeux de textes par guide, et la structure ne peut plus
diverger entre les langues.

L'HABILLAGE EST EXTRAIT D'UNE PAGE EXISTANTE, JAMAIS RETAPÉ. En-tête, navigation,
pied de page et fin de document sont découpés dans `cas-usage.html` (FR) et
`en/use-cases.html` (EN), puis descendus d'un niveau par `profondeur_plus_un()`
puisque les guides vivent dans `blog/` et `en/blog/`. C'est la règle du dépôt
appliquée aux bornes autant qu'au contenu : on n'retape pas, on extrait.

CE QUE LE FORMAT APPLIQUE, ET QUI VIENT DE L'AUDIT ROSOAI :
  - le format guide, pas la page produit (sur les cinq pages de résultats
    analysées, c'est le guide qui se classe, cinq fois sur cinq) ;
  - chaque titre est une QUESTION, suivie d'une réponse autonome de 40 à 60 mots ;
  - une source vérifiable tous les 150 à 200 mots ;
  - une date de mise à jour visible.

CE QUE LE FORMAT N'APPLIQUE PLUS : la section « dans quels cas un robot n'est pas
la bonne réponse ». Elle envoyait le lecteur vers une bibliothèque TOTP gratuite,
et le client l'a fait retirer le 2026-08-26. NE PAS la réintroduire, sur aucun
guide. Ce qui porte l'honnêteté du format à sa place : chaque guide énonce son
périmètre COMME UNE LIMITE, et le guide LuxTrust porte sa non-affiliation.

LE MAILLAGE EST LA MOITIÉ DU TRAVAIL. Huit guides isolés ne pèsent rien. La page
pilier (`automatiser-2fa-tests`) pointe vers les sept autres, chaque guide renvoie
à la page pilier, et les pages produit pointent vers le guide qui les prolonge.
C'est `MAILLAGE` ci-dessous, et il est vérifié en fin de script.
"""

import io
import os
import re

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
# L'INTENDANCE D'UN GUIDE, POSÉE UNE FOIS. Chaque guide ne déclare que ses textes ;
# les chemins, les URL canoniques, la page donneuse et la langue viennent d'ici.
# C'est ce qui garantit que le FR et l'EN d'un même guide ne peuvent pas divariguer
# de structure, et que les huit guides ne peuvent pas divariguer entre eux.
# ══════════════════════════════════════════════════════════════════════════════
def guide(slug_fr, slug_en, fr, en):
    fr = dict(fr, lang='fr', donneur='cas-usage.html', locale='fr_FR',
              accueil='Accueil', fichier='blog/' + slug_fr,
              autre='../en/blog/' + slug_en)
    en = dict(en, lang='en', donneur='en/use-cases.html', locale='en_GB',
              accueil='Home', fichier='en/blog/' + slug_en,
              autre='../../blog/' + slug_fr)
    for c in (fr, en):
        c['url_fr'] = 'https://q-bot.eu/blog/' + slug_fr
        c['url_en'] = 'https://q-bot.eu/en/blog/' + slug_en
    return {'fr': fr, 'en': en}


# Les valeurs communes à tous les guides : le bloc d'appel à l'action de fin.
CTA_FR = dict(cta_h2="Vous voulez le voir sur votre propre parcours&nbsp;?",
              cta_h3="Réservez une démo", cta_btn="Prendre rendez-vous",
              cta_href='../contact.html')
CTA_EN = dict(cta_h2="Want to see it on your own login flow?",
              cta_h3="Book a demo", cta_btn="Make an appointment",
              cta_href='../contact.html')
DATE_FR = dict(datel='Mis à jour le <time datetime="%s">%s</time>' % (MAJ_ISO, MAJ_FR))
DATE_EN = dict(datel='Updated <time datetime="%s">%s</time>' % (MAJ_ISO, MAJ_EN))

LUX_FR = dict(
    title="Tester une authentification LuxTrust en automatisé | Q-Bot",
    desc="Une validation LuxTrust ne se calcule pas, elle s'approuve sur le téléphone. Où s'arrête Selenium, et comment franchir l'étape sur un vrai appareil Android.",
    fil='Guide LuxTrust',
    label='Guide', h1="Tester une authentification LuxTrust en automatisé",
    lead="Une authentification LuxTrust ne se calcule pas&nbsp;: elle s'approuve, sur le téléphone de l'utilisateur. Aucune bibliothèque ne peut la reproduire, parce qu'il n'existe aucun secret partagé à recalculer. Ce guide explique où s'arrêtent Selenium et Cypress, et comment franchir cette étape sur un vrai appareil Android.",
    datel=f'Mis à jour le <time datetime="{MAJ_ISO}">{MAJ_FR}</time>',
    cta_h2="Vous voulez le voir sur votre propre parcours&nbsp;?",
    cta_h3="Réservez une démo", cta_btn="Prendre rendez-vous", cta_href='../contact.html',
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
             corps="""    <p>Ce n'est pas une faiblesse de <a href="https://www.selenium.dev/" target="_blank" rel="noopener">Selenium</a>, de <a href="https://www.cypress.io/" target="_blank" rel="noopener">Cypress</a> ni de <a href="https://playwright.dev/" target="_blank" rel="noopener">Playwright</a>, c'est leur périmètre. Un pilote de navigateur agit sur le document affiché&nbsp;; il n'a aucune prise sur une notification système ni sur une application native.</p>
    <p>La <a href="https://www.selenium.dev/documentation/test_practices/discouraged/two_factor_authentication/" target="_blank" rel="noopener">documentation de Selenium consacre une page à la question</a> et recommande trois voies&nbsp;: désactiver la double authentification dans l'environnement de test, la désactiver pour un compte donné, ou récupérer le secret partagé pour recalculer le code.</p>
    <p>Les trois se tiennent. Mais lisez la définition qu'elle emploie&nbsp;: elle décrit la 2FA comme un code reçu par application, par SMS ou par courriel. Elle ne parle ni des demandes à approuver, ni des applications d'identité souveraine. Sa frontière est là, et c'est exactement l'endroit où votre parcours réel se trouve si vos utilisateurs se connectent avec LuxTrust ou <a href="https://www.itsme-id.com/" target="_blank" rel="noopener">itsme</a>.</p>
    <p>Et désactiver la 2FA a un coût qu'on énonce rarement&nbsp;: vous ne testez plus le parcours que vos utilisateurs empruntent.</p>"""),
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
    <p style="margin-top:26px;">Il n'y a ni simulateur, ni bouchon, ni SDK à intégrer dans votre application. La <a href="../caracteristiques.html">fiche technique détaille l'éditeur de scénarios et la pile matérielle</a>, et la <a href="automatiser-2fa-dans-vos-tests.html">page de référence</a> replace cette méthode parmi les trois approches possibles.</p>"""),
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
    <p style="margin-top:26px;">Trois points d'entrée couvrent les cas courants&nbsp;: exécuter un scénario, lire le code affiché, afficher un QR code sur l'écran du boîtier. Ils sont documentés sur la <a href="../caracteristiques.html">fiche technique</a>, et <a href="../cas-usage.html">les exemples d'appel par outil</a> couvrent Cypress, Playwright, Robot Framework et JUnit.</p>"""),
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
    ]
)

LUX_EN = dict(
    title="Automating a LuxTrust authentication in tests | Q-Bot",
    desc="A LuxTrust approval is not computed, it is granted on the phone. Where Selenium and Cypress stop, and how to clear that step on a real Android device.",
    fil='LuxTrust guide',
    label='Guide', h1="Automating a LuxTrust authentication in your tests",
    lead="A LuxTrust authentication is not computed, it is approved on the user's phone. No library can stand in for it, because there is no shared secret left to recompute. This guide sets out where Selenium and Cypress stop, and how to clear that step on a real Android device.",
    datel=f'Updated <time datetime="{MAJ_ISO}">{MAJ_EN}</time>',
    cta_h2="Want to see it on your own login flow?",
    cta_h3="Book a demo", cta_btn="Make an appointment", cta_href='../contact.html',
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
             corps="""    <p>This is not a weakness of <a href="https://www.selenium.dev/" target="_blank" rel="noopener">Selenium</a>, <a href="https://www.cypress.io/" target="_blank" rel="noopener">Cypress</a> or <a href="https://playwright.dev/" target="_blank" rel="noopener">Playwright</a>, it is their scope. A browser driver acts on the rendered document; it has no hold on a system notification or a native app.</p>
    <p>Selenium <a href="https://www.selenium.dev/documentation/test_practices/discouraged/two_factor_authentication/" target="_blank" rel="noopener">devotes a documentation page to the question</a> and recommends three routes: disable two-factor authentication in the test environment, disable it for one account, or obtain the shared secret and recompute the code.</p>
    <p>All three are sound. But read the definition it works from: it describes 2FA as a code received through an app, an SMS or an email. It does not cover requests to approve, nor sovereign identity apps. That is where its boundary sits, and it is exactly where your real login flow lives if your users sign in with LuxTrust or <a href="https://www.itsme-id.com/" target="_blank" rel="noopener">itsme</a>.</p>
    <p>And turning 2FA off carries a cost that is rarely stated: you are no longer testing the journey your users actually take.</p>"""),
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
    <p style="margin-top:26px;">There is no simulator, no stub, and no SDK to embed in your application. The <a href="../technical-specs.html">technical page covers the scenario editor and the hardware stack</a>, and the <a href="automate-2fa-in-your-tests.html">reference page</a> places this method among the three possible approaches.</p>"""),
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
    <p style="margin-top:26px;">Three endpoints cover the usual cases: run a scenario, read the code on screen, show a QR code on the box's own display. They are documented on the <a href="../technical-specs.html">technical page</a>, and <a href="../use-cases.html">the per-tool call examples</a> cover Cypress, Playwright, Robot Framework and JUnit.</p>"""),
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
    ]
)

def profondeur_plus_un(html):
    """Ajoute un niveau à tous les chemins RELATIFS de l'habillage extrait.

    Les pages donneuses sont à la racine (FR) et dans `en/` (EN) ; le guide vit un
    cran plus bas, dans `blog/` et `en/blog/`. On ne réécrit pas l'habillage à la
    main : on préfixe `../`, ce qui marche uniformément (`x.html` devient
    `../x.html`, `../assets/` devient `../../assets/`). Les adresses absolues, les
    ancres, `mailto:` et `tel:` sont laissées telles quelles, et le JSON-LD n'est
    pas touché puisque seuls les attributs `href` et `src` le sont.
    Le garde-fou qui compte est en fin de script : chaque chemin relatif produit
    doit désigner un fichier qui existe.
    """
    def remplace(m):
        att, v = m.group(1), m.group(2)
        if re.match(r'^(https?:|//|mailto:|tel:|data:|#)', v):
            return m.group(0)
        return att + '="../' + v + '"'
    return re.sub(r'\b(href|src)="([^"]*)"', remplace, html)


def construire(cfg):
    donneur = io.open(os.path.join(RACINE, cfg['donneur']), encoding='utf-8').read()
    prof = '../../' if cfg['lang'] == 'en' else '../'
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
    for code, cible in (('fr', cfg['url_fr']), ('en', cfg['url_en']), ('x-default', cfg['url_fr'])):
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
    head = profondeur_plus_un(head) + guide

    # ---- HABILLAGE : du <body> au <main>, puis du </main> à la fin ----
    haut = profondeur_plus_un(donneur[donneur.index('<body>'):donneur.index('<main id="main">')])
    # notre page n'est pas dans le menu : on retire l'état courant du donneur
    haut = haut.replace(' class="nav__link active" aria-current="page"', ' class="nav__link"')
    haut = re.sub(r'(<div class="nav__lang">\s*<a href=")[^"]*(")',
                  r'\g<1>' + cfg['autre'] + r'\g<2>', haut, count=1)

    bas = profondeur_plus_un(donneur[donneur.index('</main>'):])
    # ni dans le pied de page : on rend son lien à l'entrée marquée courante
    # Posé APRÈS profondeur_plus_un() : il porte donc son `../` lui-même.
    lien_cu = '../' + ('use-cases.html' if cfg['lang'] == 'en' else 'cas-usage.html')
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
      <li><a href="{prof}{'blog.html' if cfg['lang'] == 'fr' else 'blog.html'}">Blog</a></li>
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




# ── Guide 2 · la question que la cible tape avant de connaître le produit ──────
DESACT_FR = dict(
    title="Faut-il désactiver la 2FA en environnement de test ? | Q-Leap",
    desc="Désactiver la 2FA en test se défend dans trois cas et coûte cher dans trois autres. Comment décider, et ce que recommande la documentation de Selenium.",
    fil='Désactiver la 2FA en test', label='Guide',
    h1="Faut-il désactiver la 2FA en environnement de test&nbsp;?",
    lead="Souvent oui, parfois non, et la réponse tient à une seule question&nbsp;: le parcours de connexion fait-il partie de ce que vous testez&nbsp;? Ce guide donne les trois cas où désactiver est le bon choix, les trois où c'est un risque, et comment trancher en trois minutes.",
    sections=[
        dict(id='perdez-title', label='Ce que ça change',
             titre="Que perdez-vous exactement en la désactivant&nbsp;?",
             capsule="Vous ne testez plus le parcours que vos utilisateurs empruntent. La connexion réelle passe par un second facteur&nbsp;; celle de vos tests non. Tout ce qui dépend de cette étape reste hors couverture&nbsp;: la redirection après validation, l'expiration de session, et le comportement en cas de refus.",
             corps="""    <p>C'est un arbitrage, pas une faute. Mais il faut savoir ce qu'on met de côté.</p>
""" + liste([
                 "la <strong>redirection</strong> après validation, souvent le point où un parcours casse",
                 "l'<strong>expiration de session</strong>, qui dépend du moment de l'authentification",
                 "le <strong>refus</strong> et le renvoi vers l'écran de connexion",
                 "les <strong>tentatives multiples</strong> et le verrouillage de compte",
             ]) + """
    <p style="margin-top:26px;">Autrement dit&nbsp;: vous gardez la couverture de l'application, vous perdez celle de la porte d'entrée.</p>"""),
        dict(id='oui-title', label='Les trois cas où oui',
             titre="Dans quels cas la désactiver est le bon choix&nbsp;?",
             capsule="Quand la connexion n'est pas le sujet du test. Un test unitaire, un test d'interface sur un écran interne, un jeu de données monté par script&nbsp;: dans ces trois cas, franchir une authentification forte n'apporte rien et ne fait qu'allonger l'exécution.",
             corps="""    <p>Trois situations où la réponse est nette&nbsp;:</p>
""" + liste([
                 "un <strong>test unitaire</strong> ou d'intégration qui ne passe pas par l'interface",
                 "un <strong>écran interne</strong> atteint avec une session déjà ouverte, montée par script",
                 "un <strong>jeu de données</strong> préparé par API, où la connexion n'est qu'un préalable",
             ]) + """
    <p style="margin-top:26px;">Dans ces cas, une session injectée ou un compte de service sans second facteur est plus simple et plus rapide que n'importe quel outil.</p>"""),
        dict(id='non-title', label='Les trois cas où non',
             titre="Dans quels cas est-ce un risque&nbsp;?",
             capsule="Quand la connexion EST le sujet, quand le test sert de porte de sortie avant une mise en production, ou quand un auditeur demandera la preuve que le parcours réel a été joué. Là, un test qui contourne le second facteur ne prouve pas ce qu'on lui demande de prouver.",
             corps="""    <p>Les trois cas qui coûtent cher&nbsp;:</p>
""" + liste([
                 "une <strong>recette de non-régression</strong> sur le parcours de connexion lui-même",
                 "une <strong>porte de sortie</strong> avant mise en production, où le test vaut décision",
                 "un <strong>contexte réglementé</strong>, où il faut montrer que le parcours réel a été joué",
             ]) + """
    <p style="margin-top:26px;">Le signe qui ne trompe pas&nbsp;: si personne n'accepterait de livrer sans qu'un humain se soit connecté une fois à la main, c'est que le test ne couvre pas ce qu'on croit.</p>"""),
        dict(id='selenium-title', label='Ce que dit la source',
             titre="Que recommande la documentation de Selenium&nbsp;?",
             capsule="Elle consacre une page à la question et propose trois voies&nbsp;: désactiver la 2FA dans l'environnement de test, la désactiver pour un compte donné, ou récupérer le secret partagé pour recalculer le code. Les trois se tiennent, et sa définition de la 2FA en dessine la frontière.",
             corps="""    <p>La page en question est <a href="https://www.selenium.dev/documentation/test_practices/discouraged/two_factor_authentication/" target="_blank" rel="noopener">« Two Factor Authentication », dans les pratiques déconseillées</a>. C'est une source d'autorité, écrite par le projet que votre équipe utilise tous les jours.</p>
    <p>Lisez cependant la définition qu'elle emploie&nbsp;: elle décrit la 2FA comme un code reçu par application, par SMS ou par courriel. Elle ne couvre ni les demandes à <strong>approuver</strong>, ni les applications d'identité souveraine. Sa troisième voie, récupérer le secret partagé, suppose qu'un secret existe et qu'on vous le donne.</p>
    <p>C'est exactement là que sa frontière passe, et c'est le sujet du <a href="automatiser-2fa-sans-cle-secrete.html">guide sur l'automatisation sans clé secrète partagée</a>.</p>"""),
        dict(id='trancher-title', label='La décision',
             titre="Comment trancher en trois questions&nbsp;?",
             capsule="Le parcours de connexion fait-il partie du périmètre de ce test&nbsp;? Détenez-vous le secret qui permet de recalculer le code&nbsp;? Et le résultat de ce test sert-il à décider d'une mise en production&nbsp;? Trois réponses, et le choix est fait.",
             corps="""    <p>Dans l'ordre&nbsp;:</p>
""" + liste([
                 "<strong>hors périmètre</strong> et sans enjeu de livraison&nbsp;: désactivez, c'est le choix simple",
                 "<strong>dans le périmètre</strong> et vous détenez le secret&nbsp;: recalculez le code, une bibliothèque suffit",
                 "<strong>dans le périmètre</strong> et il n'existe aucun secret à obtenir&nbsp;: il faut un appareil réel",
             ]) + """
    <p style="margin-top:26px;">Le troisième cas est celui des demandes à approuver et des applications d'identité&nbsp;: la <a href="automatiser-2fa-dans-vos-tests.html">page qui couvre le sujet en entier</a> détaille les trois approches, et le <a href="automatiser-authentification-luxtrust.html">guide LuxTrust</a> en donne un exemple complet.</p>"""),
    ])

DESACT_EN = dict(
    title="Should you disable 2FA in test environments? | Q-Leap",
    desc="Disabling 2FA in testing is defensible in three cases and expensive in three others. How to decide, and what Selenium's own documentation recommends.",
    fil='Disabling 2FA in testing', label='Guide',
    h1="Should you disable 2FA in test environments?",
    lead="Often yes, sometimes no, and the answer comes down to a single question: is the login journey part of what you are testing? This guide gives the three cases where disabling is the right call, the three where it is a risk, and how to decide in three minutes.",
    sections=[
        dict(id='perdez-title', label='What it changes',
             titre="What exactly do you lose by disabling it?",
             capsule="You stop testing the journey your users take. A real sign-in goes through a second factor; the one in your tests does not. Everything that depends on that step falls outside coverage: the redirect after approval, session expiry, and what happens on refusal.",
             corps="""    <p>It is a trade-off, not a mistake. But you should know what you are setting aside.</p>
""" + liste([
                 "the <strong>redirect</strong> after approval, often where a journey breaks",
                 "<strong>session expiry</strong>, which depends on when authentication happened",
                 "<strong>refusal</strong> and the return to the sign-in screen",
                 "<strong>repeated attempts</strong> and account lock-out",
             ]) + """
    <p style="margin-top:26px;">In short: you keep coverage of the application and lose coverage of its front door.</p>"""),
        dict(id='oui-title', label='The three cases for yes',
             titre="When is disabling it the right call?",
             capsule="When sign-in is not the subject of the test. A unit test, a UI test on an internal screen, a dataset built by script: in those three cases, clearing a strong authentication adds nothing to the coverage and only lengthens the run. An injected session is simpler than any tool.",
             corps="""    <p>Three situations where the answer is clear:</p>
""" + liste([
                 "a <strong>unit or integration test</strong> that never goes through the interface",
                 "an <strong>internal screen</strong> reached with a session already opened by script",
                 "a <strong>dataset</strong> prepared through the API, where sign-in is only a prerequisite",
             ]) + """
    <p style="margin-top:26px;">In those cases an injected session or a service account without a second factor is simpler and faster than any tool.</p>"""),
        dict(id='non-title', label='The three cases for no',
             titre="When is it a risk?",
             capsule="When sign-in IS the subject, when the test acts as a release gate, or when an auditor will ask for proof that the real journey ran. There, a test that bypasses the second factor does not prove what it is asked to prove.",
             corps="""    <p>The three expensive cases:</p>
""" + liste([
                 "a <strong>regression suite</strong> on the sign-in journey itself",
                 "a <strong>release gate</strong>, where the test result is the decision",
                 "a <strong>regulated context</strong>, where you must show the real journey ran",
             ]) + """
    <p style="margin-top:26px;">The tell-tale sign: if nobody would agree to ship without a human having signed in once by hand, the test is not covering what you think it covers.</p>"""),
        dict(id='selenium-title', label='What the source says',
             titre="What does Selenium's documentation recommend?",
             capsule="It devotes a page to the question and offers three routes: disable 2FA in the test environment, disable it for one account, or obtain the shared secret and recompute the code. All three are sound, and the definition it works from draws its own boundary.",
             corps="""    <p>The page is <a href="https://www.selenium.dev/documentation/test_practices/discouraged/two_factor_authentication/" target="_blank" rel="noopener">« Two Factor Authentication », under discouraged practices</a>. It is an authoritative source, written by the project your team uses every day.</p>
    <p>Read the definition it works from, though: it describes 2FA as a code received through an app, an SMS or an email. It covers neither requests to <strong>approve</strong> nor sovereign identity apps. Its third route, obtaining the shared secret, assumes a secret exists and that someone hands it to you.</p>
    <p>That is exactly where its boundary lies, and it is the subject of the <a href="automate-2fa-without-shared-secret.html">guide on automating without a shared secret</a>.</p>"""),
        dict(id='trancher-title', label='The decision',
             titre="How do you decide, in three questions?",
             capsule="Is the sign-in journey part of this test's scope? Do you hold the secret that lets you recompute the code? And does this test's result decide whether something ships or not? Three answers, and the choice is made without a meeting and without a proof of concept.",
             corps="""    <p>In order:</p>
""" + liste([
                 "<strong>out of scope</strong> and nothing ships on it: disable, that is the simple choice",
                 "<strong>in scope</strong> and you hold the secret: recompute the code, a library is enough",
                 "<strong>in scope</strong> and no secret can be obtained: you need a real device",
             ]) + """
    <p style="margin-top:26px;">The third case covers approval requests and identity apps: the <a href="automate-2fa-in-your-tests.html">page covering the whole subject</a> sets out the three approaches, and the <a href="automate-luxtrust-authentication.html">LuxTrust guide</a> gives a worked example.</p>"""),
    ])

# ── Guide 3 · LA PAGE PILIER. Elle pointe vers les sept autres : c'est le moyeu ──
PILIER_FR = dict(
    title="Automatiser la double authentification dans vos tests | Q-Leap",
    desc="Les quatre familles de 2FA, ce qu'un navigateur sait faire et où il s'arrête, et les trois approches pour franchir l'étape sans intervention humaine.",
    fil='Automatiser la 2FA', label='Guide de référence',
    h1="Automatiser la double authentification dans vos tests",
    lead="La double authentification est le dernier verrou manuel de beaucoup de chaînes de tests. Ce guide fait le tour du sujet&nbsp;: ce qui bloque exactement, les quatre familles de second facteur, ce qu'un navigateur sait faire et où il s'arrête, et les trois approches possibles pour franchir l'étape.",
    sections=[
        dict(id='bloque-title', label='Le point de départ',
             titre="Qu'est-ce qui bloque exactement dans une chaîne de tests&nbsp;?",
             capsule="Un scénario automatisé sait remplir un identifiant et un mot de passe. Il ne sait pas approuver une demande qui arrive sur un téléphone. La campagne s'arrête donc à la porte d'entrée, et tout ce qui vient après reste non testé, quelle que soit la qualité du reste de la suite.",
             corps="""    <p>Le symptôme se lit dans un rapport de campagne&nbsp;: un grand nombre de scénarios en échec, tous au même endroit, et la même trace. Ce n'est pas la suite qui est fragile, c'est qu'elle ne peut pas franchir une étape.</p>
    <p>Ce que ça coûte se mesure en heures d'astreinte, et c'est le sujet du <a href="cout-etape-manuelle-authentification.html">guide sur le coût de l'étape manuelle</a>. Le symptôme lui-même est détaillé dans <a href="campagnes-de-nuit-bloquees-au-login.html">« pourquoi vos campagnes de nuit s'arrêtent au login »</a>.</p>"""),
        dict(id='familles-title', label='Le paysage',
             titre="Quelles sont les quatre familles de second facteur&nbsp;?",
             capsule="Un code calculé, une demande à approuver, un code affiché nulle part ailleurs, et un QR code à scanner. Ces quatre familles ne s'automatisent pas de la même façon, et c'est la seule distinction qui compte pour décider d'une approche.",
             corps="""    <p>Dans l'ordre de difficulté croissante&nbsp;:</p>
""" + liste([
                 "<strong>un code calculé</strong> (TOTP)&nbsp;: Google Authenticator, Microsoft Authenticator. Il dérive d'un secret partagé et de l'heure, selon la <a href=\"https://www.rfc-editor.org/rfc/rfc6238\" target=\"_blank\" rel=\"noopener\">RFC 6238</a>",
                 "<strong>une demande à approuver</strong>&nbsp;: LuxTrust Mobile, <a href=\"https://www.itsme-id.com/\" target=\"_blank\" rel=\"noopener\">itsme</a>. Aucun code, un geste sur l'appareil enrôlé",
                 "<strong>un code affiché</strong> et lisible uniquement sur l'écran de l'application",
                 "<strong>un QR code</strong> présenté sur un écran, que l'appareil doit venir scanner",
             ]) + """
    <p style="margin-top:26px;">La première famille se calcule. Les trois autres non, et c'est toute la différence.</p>"""),
        dict(id='navigateur-title', label='Les outils',
             titre="Que sait faire un navigateur, et où s'arrête-t-il&nbsp;?",
             capsule="Selenium, Cypress et Playwright pilotent le document affiché, et ils le font très bien. Ils n'ont aucune prise sur une notification système ni sur une application native&nbsp;: aucun sélecteur n'atteint l'écran d'un téléphone. Ce n'est pas une faiblesse, c'est leur périmètre.",
             corps="""    <p><a href="https://www.selenium.dev/" target="_blank" rel="noopener">Selenium</a>, <a href="https://www.cypress.io/" target="_blank" rel="noopener">Cypress</a> et <a href="https://playwright.dev/" target="_blank" rel="noopener">Playwright</a> agissent sur le DOM. Dès que l'étape sort du navigateur, ils sont hors de leur domaine, et aucune option ne les y ramène.</p>
    <p>La documentation de Selenium <a href="https://www.selenium.dev/documentation/test_practices/discouraged/two_factor_authentication/" target="_blank" rel="noopener">le dit elle-même</a> et conseille de désactiver la double authentification en test. C'est une recommandation défendable, dont <a href="desactiver-2fa-en-test.html">le guide dédié</a> détaille les cas où elle s'applique et ceux où elle coûte cher.</p>"""),
        dict(id='approches-title', label='Les trois voies',
             titre="Quelles sont les trois approches possibles&nbsp;?",
             capsule="Désactiver le second facteur, recalculer le code depuis son secret partagé, ou piloter un appareil réel. Chacune a un domaine où elle est le bon choix, et le domaine se lit sur une seule question&nbsp;: existe-t-il un secret que vous détenez&nbsp;?",
             corps="""    <p>Les trois, avec leur domaine&nbsp;:</p>
""" + liste([
                 "<strong>désactiver</strong>&nbsp;: simple et gratuit, dès que le parcours de connexion sort du périmètre du test",
                 "<strong>recalculer</strong>&nbsp;: quelques lignes de bibliothèque, dès que vous détenez le secret partagé",
                 "<strong>piloter un appareil réel</strong>&nbsp;: la seule voie quand il n'existe aucun secret à obtenir",
             ]) + """
    <p style="margin-top:26px;">Le troisième cas est celui des demandes à approuver et des applications d'identité souveraine. Pourquoi il n'y a rien à calculer y est expliqué dans <a href="automatiser-2fa-sans-cle-secrete.html">« automatiser la 2FA sans clé secrète partagée »</a>, et les familles d'outils qui s'en chargent sont comparées dans <a href="tester-2fa-appareil-reel.html">« quel outil pour tester la 2FA sur appareil réel »</a>.</p>"""),
        dict(id='concret-title', label='En pratique',
             titre="À quoi ressemble l'appel depuis un test&nbsp;?",
             capsule="À une requête HTTP, et rien de plus. Le test déclenche le franchissement de l'étape, attend la réponse, et reprend son cours. Aucun SDK à intégrer dans l'application testée, aucun agent à installer, aucune clé d'API à distribuer dans la chaîne d'intégration.",
             corps="""    <figure class="ucs__snippet code-panel">
      <figcaption>Python / Selenium</figcaption>
      <div class="code-block"><pre><code># L'identifiant et le mot de passe sont saisis,
# le second facteur attend une validation.
import requests

requests.get(
  &quot;http://q-bot.local:8000&quot;
  &quot;/scenarios/42/execute&quot;
)

# L'étape est franchie, le test reprend.
driver.find_element(
  By.ID, &quot;dashboard&quot;
).is_displayed()</code></pre></div>
    </figure>
    <p style="margin-top:26px;">Le détail des points d'entrée est sur la <a href="../caracteristiques.html">fiche technique</a>, et <a href="../cas-usage.html">les exemples par outil</a> couvrent Cypress, Playwright, Robot Framework et JUnit. Un cas complet, de bout en bout, est déroulé dans le <a href="automatiser-authentification-luxtrust.html">guide LuxTrust</a>.</p>"""),
        dict(id='revue-title', label='Et la revue de sécurité',
             titre="Que répondre à l'équipe sécurité&nbsp;?",
             capsule="C'est souvent la question qui décide, et elle ne vient pas du testeur. Elle porte sur trois points&nbsp;: où vont les données manipulées pendant un test, quels secrets circulent, et ce qui sort du réseau. Les trois ont une réponse courte et vérifiable.",
             corps="""    <p>Résumé&nbsp;: les scénarios et leurs captures restent dans le boîtier, sur votre réseau&nbsp;; aucune clé d'API n'est à distribuer&nbsp;; aucune connexion internet n'est nécessaire pendant l'exécution des tests.</p>
    <p>Le détail, y compris ce que cette approche ne couvre PAS, est dans <a href="securite-conformite-donnees-de-test.html">« sécurité, conformité et données de test »</a>.</p>"""),
    ])

PILIER_EN = dict(
    title="Automating two-factor authentication in tests | Q-Leap",
    desc="The four families of second factor, what a browser can and cannot reach, and the three approaches to clearing the step with nobody in front of the screen.",
    fil='Automating 2FA', label='Reference guide',
    h1="Automating two-factor authentication in your tests",
    lead="Two-factor authentication is the last manual step in many test pipelines. This guide covers the whole subject: what exactly blocks, the four families of second factor, what a browser can reach and where it stops, and the three possible approaches to clearing the step.",
    sections=[
        dict(id='bloque-title', label='The starting point',
             titre="What exactly blocks in a test pipeline?",
             capsule="An automated scenario can fill in a username and a password. It cannot approve a request that lands on a phone. The run therefore stops at the front door, and everything past it stays untested, however good the rest of the suite may be.",
             corps="""    <p>The symptom shows up in a run report: a large number of failures, all in the same place, with the same trace. The suite is not flaky; it simply cannot clear one step.</p>
    <p>What that costs is measured in hours, and it is the subject of the <a href="cost-of-manual-authentication-step.html">guide on the cost of the manual step</a>. The symptom itself is covered in <a href="night-runs-blocked-at-login.html">« why your night runs stop at login »</a>.</p>"""),
        dict(id='familles-title', label='The landscape',
             titre="What are the four families of second factor?",
             capsule="A computed code, a request to approve, a code shown nowhere else, and a QR code to scan. These four families are not automated the same way, and that distinction is the only one that matters when you choose an approach. Everything else in this guide follows from it.",
             corps="""    <p>In order of increasing difficulty:</p>
""" + liste([
                 "<strong>a computed code</strong> (TOTP): Google Authenticator, Microsoft Authenticator. It derives from a shared secret and the current time, per <a href=\"https://www.rfc-editor.org/rfc/rfc6238\" target=\"_blank\" rel=\"noopener\">RFC 6238</a>",
                 "<strong>a request to approve</strong>: LuxTrust Mobile, <a href=\"https://www.itsme-id.com/\" target=\"_blank\" rel=\"noopener\">itsme</a>. No code, just a gesture on the enrolled device",
                 "<strong>a displayed code</strong>, readable only on the app's own screen",
                 "<strong>a QR code</strong> shown on a screen that the device has to scan",
             ]) + """
    <p style="margin-top:26px;">The first family can be computed. The other three cannot, and that is the whole difference.</p>"""),
        dict(id='navigateur-title', label='The tools',
             titre="What can a browser reach, and where does it stop?",
             capsule="Selenium, Cypress and Playwright drive the rendered document, and they do it very well. They have no hold on a system notification or a native app: no selector reaches a phone's screen. That is not a weakness, it is their scope.",
             corps="""    <p><a href="https://www.selenium.dev/" target="_blank" rel="noopener">Selenium</a>, <a href="https://www.cypress.io/" target="_blank" rel="noopener">Cypress</a> and <a href="https://playwright.dev/" target="_blank" rel="noopener">Playwright</a> act on the DOM. As soon as the step leaves the browser they are outside their domain, and no option brings them back in.</p>
    <p>Selenium's documentation <a href="https://www.selenium.dev/documentation/test_practices/discouraged/two_factor_authentication/" target="_blank" rel="noopener">says so itself</a> and advises disabling two-factor authentication in testing. That is a defensible recommendation, and <a href="disable-2fa-in-testing.html">the dedicated guide</a> sets out where it applies and where it costs you.</p>"""),
        dict(id='approches-title', label='The three routes',
             titre="What are the three possible approaches?",
             capsule="Disable the second factor, recompute the code from its shared secret, or drive a real device. Each has a domain where it is the right choice, and that domain comes down to one question: is there a secret that you hold?",
             corps="""    <p>All three, with their domain:</p>
""" + liste([
                 "<strong>disable</strong>: simple and free, whenever the sign-in journey is out of the test's scope",
                 "<strong>recompute</strong>: a few lines of library, whenever you hold the shared secret",
                 "<strong>drive a real device</strong>: the only route when no secret can be obtained",
             ]) + """
    <p style="margin-top:26px;">The third case covers approval requests and sovereign identity apps. Why there is nothing to compute is explained in <a href="automate-2fa-without-shared-secret.html">« automating 2FA without a shared secret »</a>, and the families of tools that handle it are compared in <a href="test-2fa-real-device.html">« which tool for testing 2FA on a real device »</a>.</p>"""),
        dict(id='concret-title', label='In practice',
             titre="What does the call from a test look like?",
             capsule="An HTTP request, and nothing more. The test triggers the step, waits for the answer, and picks up where it left off. No SDK to embed in the application under test, no agent to install, and no API key to distribute through the integration pipeline.",
             corps="""    <figure class="ucs__snippet code-panel">
      <figcaption>Python / Selenium</figcaption>
      <div class="code-block"><pre><code># Username and password are entered,
# the second factor is waiting for approval.
import requests

requests.get(
  &quot;http://q-bot.local:8000&quot;
  &quot;/scenarios/42/execute&quot;
)

# The step is cleared, the test resumes.
driver.find_element(
  By.ID, &quot;dashboard&quot;
).is_displayed()</code></pre></div>
    </figure>
    <p style="margin-top:26px;">The endpoints are detailed on the <a href="../technical-specs.html">technical page</a>, and <a href="../use-cases.html">the per-tool examples</a> cover Cypress, Playwright, Robot Framework and JUnit. One end-to-end case is worked through in the <a href="automate-luxtrust-authentication.html">LuxTrust guide</a>.</p>"""),
        dict(id='revue-title', label='And the security review',
             titre="What do you tell the security team?",
             capsule="This is often the question that decides, and it does not come from the tester. It covers three points: where the data handled during a test goes, which secrets circulate, and what leaves the network. All three have a short, checkable answer.",
             corps="""    <p>In short: scenarios and their screenshots stay inside the box, on your network; no API key has to be distributed; and no internet connection is needed while the tests run.</p>
    <p>The detail, including what this approach does NOT cover, is in <a href="security-compliance-test-data.html">« security, compliance and test data »</a>.</p>"""),
    ])

# ── Guide 4 · le comparatif. RÈGLE D'ÉCRITURE : on nomme des FAMILLES d'outils et
#    des différences d'architecture vérifiables, jamais une limite qu'on prêterait à
#    un fournisseur nommé sans pouvoir la prouver. La valeur pour le lecteur est la
#    liste de questions à poser, pas un jugement.
REEL_FR = dict(
    title="Quel outil pour tester la 2FA sur appareil réel ? | Q-Leap",
    desc="Un appareil dans le nuage et un appareil sur votre réseau ne répondent pas à la même contrainte. La différence, et les six questions à poser à un fournisseur.",
    fil='Tester sur appareil réel', label='Comparatif',
    h1="Quel outil pour tester la 2FA sur appareil réel&nbsp;?",
    lead="Deux familles d'outils font tourner des tests sur de vrais téléphones&nbsp;: les parcs d'appareils hébergés et les appareils posés sur votre propre réseau. Elles ne répondent pas à la même contrainte, et le choix se joue sur ce que votre application d'authentification exige.",
    sections=[
        dict(id='familles-title', label='Les deux familles',
             titre="Quelles sont les deux familles d'outils&nbsp;?",
             capsule="D'un côté les parcs d'appareils hébergés, où vous louez l'accès à des téléphones qui vivent chez un fournisseur. De l'autre les appareils posés sur votre réseau, pilotés depuis chez vous. La première famille apporte le nombre et la diversité, la seconde la proximité.",
             corps="""    <p>Les deux font tourner du code sur du vrai matériel, ce qui est déjà l'essentiel. La différence est ailleurs&nbsp;: dans <strong>où</strong> se trouve l'appareil, et donc dans ce qu'il peut atteindre.</p>
""" + liste([
                 "un <strong>parc hébergé</strong> donne accès à des dizaines de modèles et de versions, sans matériel à gérer",
                 "un <strong>appareil sur votre réseau</strong> voit ce que votre réseau voit, et rien ne sort de chez vous",
             ]) + """
    <p style="margin-top:26px;">Aucune des deux n'est meilleure en soi. Elles répondent à deux contraintes différentes, et beaucoup d'équipes ont besoin des deux.</p>"""),
        dict(id='nuage-title', label='Le nuage',
             titre="Que change un appareil hébergé chez un fournisseur&nbsp;?",
             capsule="Il apporte la couverture&nbsp;: beaucoup de modèles, beaucoup de versions d'Android et d'iOS, disponibles à la demande. C'est la bonne réponse quand la question est « est-ce que mon application s'affiche correctement partout », et c'est une question qui compte.",
             corps="""    <p>C'est l'outil du test de compatibilité, et il n'a pas d'équivalent pour ça. Deux points à vérifier quand une étape d'authentification entre dans le parcours&nbsp;:</p>
""" + liste([
                 "l'appareil doit pouvoir <strong>joindre votre environnement de test</strong>, souvent derrière un réseau privé",
                 "l'application d'authentification doit pouvoir être <strong>enrôlée</strong> sur cet appareil, et le rester d'une session à l'autre",
             ]) + """
    <p style="margin-top:26px;">Ce sont deux questions d'intendance, pas des objections&nbsp;: elles se règlent, mais elles se posent avant le choix, pas après.</p>"""),
        dict(id='reseau-title', label='Votre réseau',
             titre="Que change un appareil posé sur votre réseau&nbsp;?",
             capsule="Il est enrôlé une fois et le reste, il joint vos environnements internes sans passerelle, et rien de ce qu'il affiche ne quitte vos locaux. C'est la réponse quand l'authentification elle-même fait partie du test, et quand une revue de sécurité doit signer.",
             corps="""    <p>Le compte utilisé pour les tests reste enrôlé sur un appareil qui ne bouge pas, et c'est ce qui rend le parcours rejouable tous les soirs sans intervention.</p>
    <p>C'est le modèle de Q-Bot&nbsp;: un téléphone Android ordinaire, relié en USB, piloté par <a href="https://developer.android.com/tools/adb" target="_blank" rel="noopener">ADB</a>, sur votre réseau. Les données du test restent dans le boîtier, sujet traité par le <a href="securite-conformite-donnees-de-test.html">guide sécurité et conformité</a>.</p>"""),
        dict(id='questions-title', label='La liste à emporter',
             titre="Quelles six questions poser à un fournisseur&nbsp;?",
             capsule="Elles ne portent pas sur les fonctions annoncées mais sur ce qui bloque en pratique. Posez-les à n'importe quel fournisseur, y compris à nous&nbsp;: les réponses vous diront en cinq minutes si l'outil couvre votre parcours ou seulement une partie.",
             corps="""    <p>À poser telles quelles&nbsp;:</p>
""" + liste([
                 "l'appareil peut-il <strong>joindre mon environnement de test</strong> interne&nbsp;?",
                 "mon compte d'authentification reste-t-il <strong>enrôlé entre deux sessions</strong>&nbsp;?",
                 "l'outil sait-il approuver une <strong>demande poussée</strong>, ou seulement saisir un code&nbsp;?",
                 "sait-il <strong>lire un code affiché</strong> et le rendre à mon test&nbsp;?",
                 "<strong>où sont stockées</strong> les captures d'écran de mes scénarios&nbsp;?",
                 "quelles <strong>plateformes</strong> exactement, et lesquelles PAS&nbsp;?",
             ]) + """
    <p style="margin-top:26px;">Notre réponse à la dernière est écrite&nbsp;: <strong>Android uniquement, pas d'iOS</strong>. Le pilotage repose sur ADB, qui n'a pas d'équivalent sur iPhone. Si votre parcours doit être validé sur iPhone, un parc hébergé est le bon outil, pas le nôtre.</p>
    <p style="margin-top:18px; font-size:0.9375rem;">Les autres outils cités le sont pour situer les familles. Nous ne prêtons aucune limite à un fournisseur nommé&nbsp;: les six questions sont là pour que vous obteniez ses réponses de sa propre bouche.</p>"""),
    ])

REEL_EN = dict(
    title="Which tool for testing 2FA on a real device? | Q-Leap",
    desc="A device in the cloud and a device on your own network answer different constraints. The difference, and the six questions to ask any vendor.",
    fil='Testing on a real device', label='Comparison',
    h1="Which tool for testing 2FA on a real device?",
    lead="Two families of tools run tests on real phones: hosted device farms, and devices sitting on your own network. They answer different constraints, and the choice comes down to what your authentication app requires.",
    sections=[
        dict(id='familles-title', label='The two families',
             titre="What are the two families of tools?",
             capsule="On one side, hosted device farms, where you rent access to phones that live at a provider. On the other, devices sitting on your own network, driven from your side. The first family brings numbers and variety, the second brings proximity. Many teams end up needing both.",
             corps="""    <p>Both run code on real hardware, which is already the main thing. The difference lies elsewhere: in <strong>where</strong> the device sits, and therefore in what it can reach.</p>
""" + liste([
                 "a <strong>hosted farm</strong> gives access to dozens of models and versions, with no hardware to manage",
                 "a <strong>device on your network</strong> sees what your network sees, and nothing leaves your premises",
             ]) + """
    <p style="margin-top:26px;">Neither is better in the abstract. They answer two different constraints, and many teams need both.</p>"""),
        dict(id='nuage-title', label='The cloud',
             titre="What does a hosted device change?",
             capsule="It brings coverage: many models, many Android and iOS versions, all available on demand and with no hardware to manage. It is the right answer when the question is « does my application render correctly everywhere », and that question matters a great deal.",
             corps="""    <p>It is the compatibility-testing tool, and nothing else replaces it. Two things to check once an authentication step enters the journey:</p>
""" + liste([
                 "the device must be able to <strong>reach your test environment</strong>, often behind a private network",
                 "the authentication app must be <strong>enrolable</strong> on that device, and stay enrolled between sessions",
             ]) + """
    <p style="margin-top:26px;">These are logistics questions, not objections: they can be solved, but they should be asked before the choice, not after.</p>"""),
        dict(id='reseau-title', label='Your network',
             titre="What does a device on your own network change?",
             capsule="It is enrolled once and stays enrolled, it reaches your internal environments with no gateway, and nothing it displays leaves your premises. That is the answer when authentication is itself part of the test, and when a security review has to sign off.",
             corps="""    <p>The account used for testing stays enrolled on a device that does not move, and that is what makes the journey replayable every night with nobody watching.</p>
    <p>This is Q-Bot's model: an ordinary Android phone, wired over USB, driven through <a href="https://developer.android.com/tools/adb" target="_blank" rel="noopener">ADB</a>, on your network. Test data stays inside the box, a subject covered by the <a href="security-compliance-test-data.html">security and compliance guide</a>.</p>"""),
        dict(id='questions-title', label='The list to take with you',
             titre="Which six questions should you ask a vendor?",
             capsule="They are not about advertised features but about what actually blocks in practice. Ask them of any vendor, including us: the answers will tell you within five minutes whether the tool covers your whole journey or only a part of it. Ask for them in writing.",
             corps="""    <p>Ask them as they stand:</p>
""" + liste([
                 "can the device <strong>reach my internal test environment</strong>?",
                 "does my authentication account <strong>stay enrolled between sessions</strong>?",
                 "can the tool approve a <strong>pushed request</strong>, or only type a code?",
                 "can it <strong>read a displayed code</strong> and hand it back to my test?",
                 "<strong>where are</strong> my scenarios' screenshots stored?",
                 "which platforms exactly, and which ones NOT?",
             ]) + """
    <p style="margin-top:26px;">Our answer to the last one is on the record: <strong>Android only, no iOS</strong>. The driving relies on ADB, which has no equivalent on iPhone. If your journey has to be validated on an iPhone, a hosted farm is the right tool, not ours.</p>
    <p style="margin-top:18px; font-size:0.9375rem;">Other tools are named here only to place the families. We attribute no limitation to any named vendor: the six questions exist so that you get their answers from them.</p>"""),
    ])

# ── Guide 5 · celui qui parle à l'équipe sécurité, pas au testeur ──────────────
SECU_FR = dict(
    title="Sécurité, conformité et données de test 2FA | Q-Leap",
    desc="Quelles données un test d'authentification manipule, où elles vont, et les questions d'une revue de sécurité. Avec ce que cette approche ne couvre pas.",
    fil='Sécurité et données de test', label='Guide',
    h1="Sécurité, conformité et données de test",
    lead="C'est souvent la question qui décide, et elle ne vient pas du testeur&nbsp;: elle vient de la personne qui doit signer. Ce guide répond aux trois points d'une revue de sécurité, dit ce qu'il faut inscrire dans un registre de traitement, et énonce ce que l'approche ne couvre pas.",
    sections=[
        dict(id='quoi-title', label='L\'inventaire',
             titre="Quelles données un test d'authentification manipule-t-il&nbsp;?",
             capsule="Moins qu'on ne l'imagine, et il vaut de le poser noir sur blanc&nbsp;: un compte de test, ses identifiants, les captures d'écran des scénarios, et les codes à usage unique lus au vol. Aucune donnée de production, aucune donnée de client réel, si l'environnement est correctement séparé.",
             corps="""    <p>L'inventaire complet, ligne par ligne&nbsp;:</p>
""" + liste([
                 "un <strong>compte de test</strong> et son mot de passe, gérés comme n'importe quel secret de la chaîne",
                 "les <strong>captures d'écran</strong> qui servent de fond aux étapes d'un scénario",
                 "les <strong>codes à usage unique</strong>, valables quelques dizaines de secondes, lus puis rendus au test",
             ]) + """
    <p style="margin-top:26px;">Le point qui rassure une revue&nbsp;: il n'y a <strong>aucun secret d'authentification à extraire</strong> de l'application. Le pourquoi est dans <a href="automatiser-2fa-sans-cle-secrete.html">« automatiser la 2FA sans clé secrète partagée »</a>.</p>"""),
        dict(id='ou-title', label='La localisation',
             titre="Où vont ces données&nbsp;?",
             capsule="Nulle part. Les scénarios et leurs captures restent dans le boîtier, sur votre réseau, dans une base locale. Rien n'est envoyé vers un service en ligne, et aucune connexion internet n'est nécessaire pendant l'exécution des tests. Cela se vérifie en coupant le réseau et en relançant une campagne.",
             corps="""    <p>Concrètement&nbsp;:</p>
""" + liste([
                 "les scénarios et leurs captures sont stockés <strong>dans le boîtier</strong>, jamais sur un service en ligne",
                 "<strong>aucune connexion internet</strong> n'est nécessaire pendant les tests",
                 "<strong>aucune clé d'API</strong> à distribuer, donc aucun secret à faire circuler dans la chaîne d'intégration",
                 "le boîtier et le téléphone restent <strong>dans vos locaux</strong>, sur votre réseau",
             ]) + """
    <p style="margin-top:26px;">C'est ce qui distingue ce modèle d'un appareil hébergé chez un tiers, différence détaillée dans <a href="tester-2fa-appareil-reel.html">le comparatif des deux familles d'outils</a>.</p>"""),
        dict(id='revue-title', label='La revue',
             titre="Que demande une revue de sécurité&nbsp;?",
             capsule="Presque toujours les mêmes cinq choses&nbsp;: la surface exposée, les secrets en circulation, la localisation des données, la traçabilité des accès et la fin de vie du matériel. Les avoir préparées transforme une revue de trois semaines en une réunion d'une heure.",
             corps="""    <p>Les cinq, avec ce qu'il faut pouvoir montrer&nbsp;:</p>
""" + liste([
                 "<strong>surface exposée</strong>&nbsp;: une API HTTP sur votre réseau local, pas d'accès entrant depuis l'extérieur",
                 "<strong>secrets</strong>&nbsp;: le compte de test, rien d'autre&nbsp;; pas de clé d'API à provisionner",
                 "<strong>localisation</strong>&nbsp;: base locale sur le boîtier, dans vos locaux",
                 "<strong>traçabilité</strong>&nbsp;: qui déclenche quel scénario, et depuis quelle chaîne",
                 "<strong>fin de vie</strong>&nbsp;: ce qu'il reste sur le matériel quand il est rendu ou remplacé",
             ]) + """
    <p style="margin-top:26px;">Sur le dernier point, la réponse honnête est qu'un boîtier rendu contient encore vos captures d'écran tant qu'on ne l'a pas effacé&nbsp;: c'est une ligne à écrire dans votre procédure de restitution, pas une propriété du produit.</p>"""),
        dict(id='limites-title', label='Les limites, énoncées',
             titre="Qu'est-ce que cette approche ne couvre pas&nbsp;?",
             capsule="Trois choses, et mieux vaut les savoir avant qu'après&nbsp;: elle ne remplace pas la séparation de vos environnements, elle ne chiffre pas les captures au repos, et elle ne dispense pas de gérer le compte de test comme un secret de production.",
             corps="""    <p>À traiter chez vous, parce que ce n'est pas le produit qui le fera&nbsp;:</p>
""" + liste([
                 "la <strong>séparation des environnements</strong>&nbsp;: si votre recette parle à la production, aucun outil de test ne corrigera ça",
                 "le <strong>chiffrement au repos</strong> des captures dans le boîtier n'est pas assuré&nbsp;: à couvrir par le chiffrement du support si votre politique l'exige",
                 "le <strong>compte de test</strong> reste un secret à faire tourner, à révoquer et à surveiller comme les autres",
             ]) + """
    <p style="margin-top:26px;">Le reste du sujet, du point de vue du testeur cette fois, est dans la <a href="automatiser-2fa-dans-vos-tests.html">page de référence sur l'automatisation de la 2FA</a>.</p>"""),
    ])

SECU_EN = dict(
    title="Security, compliance and 2FA test data | Q-Leap",
    desc="What data an authentication test handles, where it goes, and the questions a security review will ask. Including what this approach does not cover.",
    fil='Security and test data', label='Guide',
    h1="Security, compliance and test data",
    lead="This is often the question that decides, and it does not come from the tester: it comes from whoever has to sign off. This guide answers the three points of a security review, says what belongs in a processing record, and states what the approach does not cover.",
    sections=[
        dict(id='quoi-title', label='The inventory',
             titre="What data does an authentication test handle?",
             capsule="Less than people assume, and it is worth putting on the record: a test account, its credentials, the screenshots used by scenarios, and one-time codes read on the fly. No production data and no real customer data, provided environments are properly separated.",
             corps="""    <p>The full inventory, line by line:</p>
""" + liste([
                 "a <strong>test account</strong> and its password, handled like any other secret in the pipeline",
                 "the <strong>screenshots</strong> used as the background of a scenario's steps",
                 "<strong>one-time codes</strong>, valid for a few dozen seconds, read and handed back to the test",
             ]) + """
    <p style="margin-top:26px;">The point that reassures a review: there is <strong>no authentication secret to extract</strong> from the application. Why is covered in <a href="automate-2fa-without-shared-secret.html">« automating 2FA without a shared secret »</a>.</p>"""),
        dict(id='ou-title', label='The location',
             titre="Where does that data go?",
             capsule="Nowhere. Scenarios and their screenshots stay inside the box, on your own network, in a local database. Nothing is sent to an online service, and no internet connection is needed while the tests run. That last point can be verified by cutting the network and running a campaign.",
             corps="""    <p>Concretely:</p>
""" + liste([
                 "scenarios and their screenshots are stored <strong>in the box</strong>, never on an online service",
                 "<strong>no internet connection</strong> is needed while tests run",
                 "<strong>no API key</strong> to distribute, so no secret circulating through the integration pipeline",
                 "the box and the phone stay <strong>on your premises</strong>, on your network",
             ]) + """
    <p style="margin-top:26px;">That is what separates this model from a device hosted by a third party, a difference set out in <a href="test-2fa-real-device.html">the comparison of the two families of tools</a>.</p>"""),
        dict(id='revue-title', label='The review',
             titre="What does a security review ask for?",
             capsule="Almost always the same five things: the exposed surface, the secrets in circulation, where the data sits, access traceability, and hardware end of life. Having all five prepared in advance turns a review that drags on for three weeks into a single one-hour meeting.",
             corps="""    <p>All five, with what you need to be able to show:</p>
""" + liste([
                 "<strong>exposed surface</strong>: an HTTP API on your local network, no inbound access from outside",
                 "<strong>secrets</strong>: the test account, nothing else; no API key to provision",
                 "<strong>location</strong>: a local database on the box, on your premises",
                 "<strong>traceability</strong>: who triggers which scenario, and from which pipeline",
                 "<strong>end of life</strong>: what remains on the hardware when it is returned or replaced",
             ]) + """
    <p style="margin-top:26px;">On that last point the honest answer is that a returned box still holds your screenshots until it is wiped: that is a line for your return procedure, not a property of the product.</p>"""),
        dict(id='limites-title', label='The limits, stated',
             titre="What does this approach not cover?",
             capsule="Three things, and they are better known beforehand: it does not replace the separation of your environments, it does not encrypt screenshots at rest, and it does not excuse you from handling the test account like any other production secret. All three stay on your side.",
             corps="""    <p>To handle on your side, because the product will not:</p>
""" + liste([
                 "<strong>environment separation</strong>: if your staging talks to production, no test tool will fix that",
                 "<strong>encryption at rest</strong> of the screenshots in the box is not provided: cover it with disk encryption if your policy requires it",
                 "the <strong>test account</strong> remains a secret to rotate, revoke and monitor like any other",
             ]) + """
    <p style="margin-top:26px;">The rest of the subject, from the tester's point of view this time, is in the <a href="automate-2fa-in-your-tests.html">reference page on automating 2FA</a>.</p>"""),
    ])

# ── Guide 6 · le coeur technique du différenciateur ───────────────────────────
SANSCLE_FR = dict(
    title="Automatiser la 2FA sans clé secrète partagée | Q-Leap",
    desc="Récupérer le secret TOTP d'un compte de test marche, et suppose qu'on vous le donne. Les parcours où aucune clé n'existe, et comment franchir l'étape sans.",
    fil='Sans clé secrète partagée', label='Guide',
    h1="Automatiser la 2FA sans clé secrète partagée",
    lead="La voie classique consiste à récupérer le secret d'un compte de test pour recalculer son code. Elle marche, et elle suppose deux choses&nbsp;: qu'un secret existe, et qu'on vous le confie. Ce guide traite les parcours où ni l'une ni l'autre n'est vraie.",
    sections=[
        dict(id='probleme-title', label='Le coût caché',
             titre="Pourquoi une clé partagée est-elle un problème&nbsp;?",
             capsule="Parce que c'est un secret d'authentification comme un autre. Dès qu'il entre dans votre chaîne de tests, il faut le stocker, le distribuer aux agents d'exécution, le faire tourner, et répondre de sa fuite éventuelle. Un code à six chiffres devient une obligation de gestion.",
             corps="""    <p>Ce n'est pas une objection de principe&nbsp;: c'est une charge, et elle se paie ailleurs que dans le test.</p>
""" + liste([
                 "il faut le <strong>stocker</strong> quelque part que vos agents d'exécution puissent lire",
                 "il faut le <strong>faire tourner</strong> comme n'importe quel secret, avec la procédure qui va avec",
                 "il faut pouvoir dire, en revue, <strong>qui y a accès</strong> et depuis quand",
             ]) + """
    <p style="margin-top:26px;">La <a href="securite-conformite-donnees-de-test.html">page sur la sécurité et les données de test</a> détaille ce qu'une revue demande sur ce point précis.</p>"""),
        dict(id='totp-title', label='Ce que la norme suppose',
             titre="Que suppose exactement la norme TOTP&nbsp;?",
             capsule="Qu'un secret a été partagé entre le service et l'appareil au moment de l'enrôlement, et que ce secret plus l'heure courante suffisent à produire le code. C'est écrit dans la RFC 6238, et c'est ce qui rend une bibliothèque capable de remplacer le téléphone.",
             corps="""    <p>La <a href="https://www.rfc-editor.org/rfc/rfc6238" target="_blank" rel="noopener">RFC 6238</a> décrit un mot de passe à usage unique fondé sur le temps&nbsp;: le service et l'appareil détiennent la même graine, et chacun calcule le même code au même instant.</p>
    <p>Deux conséquences, et la seconde est celle qu'on oublie&nbsp;: si vous détenez la graine, aucun appareil n'est nécessaire&nbsp;; et si vous ne la détenez pas, aucun calcul n'est possible. Il n'y a pas de troisième cas.</p>
    <p>C'est aussi la troisième voie que <a href="https://www.selenium.dev/documentation/test_practices/discouraged/two_factor_authentication/" target="_blank" rel="noopener">la documentation de Selenium</a> recommande, et sa condition d'application est exactement celle-là.</p>"""),
        dict(id='sans-title', label='Les parcours concernés',
             titre="Quels parcours n'ont aucune clé à obtenir&nbsp;?",
             capsule="Ceux où le second facteur n'est pas un code calculé. Une demande poussée sur l'appareil enrôlé, un code affiché seulement dans l'application, un QR code à scanner&nbsp;: dans ces trois cas, il n'existe aucune graine que quiconque puisse vous remettre.",
             corps="""    <p>Les trois familles, avec ce qui les caractérise&nbsp;:</p>
""" + liste([
                 "une <strong>demande à approuver</strong>&nbsp;: le secret ne quitte jamais l'appareil, c'est l'intérêt du dispositif",
                 "un <strong>code affiché</strong> et rien d'autre&nbsp;: il existe, mais nulle part où votre test puisse le lire",
                 "un <strong>QR code</strong>&nbsp;: l'information passe par un canal optique, pas par un calcul",
             ]) + """
    <p style="margin-top:26px;">Les applications d'identité souveraine relèvent de la première famille&nbsp;: le <a href="automatiser-authentification-luxtrust.html">guide LuxTrust</a> en déroule un cas complet.</p>"""),
        dict(id='comment-title', label='La méthode',
             titre="Comment franchir l'étape sans clé&nbsp;?",
             capsule="En appuyant pour de bon. Un téléphone Android relié en USB, piloté par ADB&nbsp;: chaque appui arrive sur l'écran physique, dans la véritable application. Il n'y a rien à calculer, donc rien à détenir, et aucun secret n'entre dans votre chaîne de tests.",
             corps="""    <p>Le scénario se construit à la souris sur une capture de l'écran de l'application&nbsp;: des points d'appui numérotés et des temps d'attente, sans écrire de script. Votre test déclenche ensuite le scénario par un appel HTTP.</p>
    <p>Le détail des points d'entrée est sur la <a href="../caracteristiques.html">fiche technique</a>, et les trois approches possibles sont mises côte à côte dans la <a href="automatiser-2fa-dans-vos-tests.html">page de référence</a>.</p>
    <p style="margin-top:18px; font-size:0.9375rem;">Périmètre&nbsp;: Android uniquement, pas d'iOS, et un appareil relié par boîtier. Le pilotage repose sur ADB, qui n'a pas d'équivalent sur iPhone.</p>"""),
    ])

SANSCLE_EN = dict(
    title="Automating 2FA without a shared secret | Q-Leap",
    desc="Obtaining a test account's TOTP seed works, and assumes someone hands it to you. The journeys where no seed exists, and how to clear the step without one.",
    fil='Without a shared secret', label='Guide',
    h1="Automating 2FA without a shared secret",
    lead="The classic route is to obtain a test account's seed and recompute its code. It works, and it assumes two things: that a seed exists, and that someone hands it to you. This guide covers the journeys where neither is true.",
    sections=[
        dict(id='probleme-title', label='The hidden cost',
             titre="Why is a shared secret a problem?",
             capsule="Because it is an authentication secret like any other. Once it enters your test pipeline you have to store it, distribute it to runners, rotate it, and answer for it if it leaks. A six-digit code turns into a management obligation.",
             corps="""    <p>This is not an objection on principle: it is a cost, and it is paid somewhere other than in the test.</p>
""" + liste([
                 "it has to be <strong>stored</strong> somewhere your runners can read",
                 "it has to be <strong>rotated</strong> like any other secret, with the procedure that comes with it",
                 "you have to be able to say, in a review, <strong>who has access</strong> and since when",
             ]) + """
    <p style="margin-top:26px;">The <a href="security-compliance-test-data.html">page on security and test data</a> sets out what a review asks on that exact point.</p>"""),
        dict(id='totp-title', label='What the standard assumes',
             titre="What exactly does the TOTP standard assume?",
             capsule="That a secret was shared between the service and the device at enrolment, and that this secret plus the current time is enough to produce the code. That is written into RFC 6238, and it is what lets a library stand in for the phone.",
             corps="""    <p><a href="https://www.rfc-editor.org/rfc/rfc6238" target="_blank" rel="noopener">RFC 6238</a> describes a time-based one-time password: the service and the device hold the same seed, and each computes the same code at the same instant.</p>
    <p>Two consequences, and the second is the one people forget: if you hold the seed, no device is needed; and if you do not, no computation is possible. There is no third case.</p>
    <p>It is also the third route <a href="https://www.selenium.dev/documentation/test_practices/discouraged/two_factor_authentication/" target="_blank" rel="noopener">Selenium's documentation</a> recommends, and this is precisely its condition of use.</p>"""),
        dict(id='sans-title', label='The journeys concerned',
             titre="Which journeys have no seed to obtain?",
             capsule="Those where the second factor is not a computed code. A request pushed to the enrolled device, a code displayed only inside the app, a QR code to scan: in those three cases there is no seed anyone could hand you.",
             corps="""    <p>The three families, and what characterises them:</p>
""" + liste([
                 "a <strong>request to approve</strong>: the secret never leaves the device, which is the point of the scheme",
                 "a <strong>displayed code</strong> and nothing else: it exists, but nowhere your test can read it",
                 "a <strong>QR code</strong>: the information travels through an optical channel, not a computation",
             ]) + """
    <p style="margin-top:26px;">Sovereign identity apps belong to the first family: the <a href="automate-luxtrust-authentication.html">LuxTrust guide</a> works through a complete case.</p>"""),
        dict(id='comment-title', label='The method',
             titre="How do you clear the step without a seed?",
             capsule="By tapping for real. An Android phone wired over USB and driven through ADB: every tap lands on the physical screen, in the genuine app. There is nothing to compute, therefore nothing to hold, and no secret enters your test pipeline.",
             corps="""    <p>The scenario is built with the mouse on a screenshot of the app screen: numbered tap points and waiting times, with no script to write. Your test then triggers the scenario with an HTTP call.</p>
    <p>The endpoints are detailed on the <a href="../technical-specs.html">technical page</a>, and the three possible approaches sit side by side on the <a href="automate-2fa-in-your-tests.html">reference page</a>.</p>
    <p style="margin-top:18px; font-size:0.9375rem;">Scope: Android only, no iOS, and one wired device per box. The driving relies on ADB, which has no equivalent on iPhone.</p>"""),
    ])

# ── Guide 7 · le symptôme, tel que la cible le ressent ────────────────────────
NUIT_FR = dict(
    title="Pourquoi vos campagnes de nuit s'arrêtent au login | Q-Leap",
    desc="Un paquet d'échecs au même endroit, la même trace : c'est presque toujours le second facteur. Les trois rustines habituelles, et ce qu'elles coûtent vraiment.",
    fil='Campagnes bloquées au login', label='Guide',
    h1="Pourquoi vos campagnes de nuit s'arrêtent au login",
    lead="Le rapport du matin montre un paquet d'échecs, tous au même endroit, avec la même trace. Ce n'est presque jamais une suite fragile&nbsp;: c'est une étape que rien n'a pu franchir pendant la nuit. Ce guide explique le symptôme, les rustines habituelles, et ce qu'il faut pour aller au bout.",
    sections=[
        dict(id='symptome-title', label='Le symptôme',
             titre="À quoi ressemble le symptôme dans un rapport&nbsp;?",
             capsule="À une grappe d'échecs qui partagent trois traits&nbsp;: ils sont nombreux, ils tombent tous au même endroit du parcours, et ils portent la même trace. Une suite réellement instable échoue de façon dispersée&nbsp;; celle-ci échoue avec une régularité qui devrait mettre la puce à l'oreille.",
             corps="""    <p>Les trois signes qui distinguent un blocage d'une instabilité&nbsp;:</p>
""" + liste([
                 "les échecs sont <strong>groupés</strong> sur une même étape, pas dispersés dans la suite",
                 "la trace est <strong>identique</strong> d'un scénario à l'autre",
                 "les scénarios qui ne passent pas par la connexion, eux, <strong>passent</strong>",
             ]) + """
    <p style="margin-top:26px;">Quand ces trois signes sont réunis, chercher la cause dans la suite est une perte de temps&nbsp;: la cause est en amont.</p>"""),
        dict(id='pourquoi-title', label='La cause',
             titre="Pourquoi est-ce presque toujours le second facteur&nbsp;?",
             capsule="Parce que c'est la seule étape du parcours qui attend un geste humain. Tout le reste s'automatise&nbsp;: la saisie, la navigation, les assertions. Une validation à approuver sur un téléphone, non&nbsp;: elle attend quelqu'un, et à trois heures du matin il n'y a personne.",
             corps="""    <p>Un pilote de navigateur agit sur le document affiché. Dès que l'étape sort du navigateur, il n'a plus de prise&nbsp;: aucun sélecteur n'atteint l'écran d'un téléphone. Ce n'est pas une faiblesse de l'outil, c'est son périmètre, et <a href="automatiser-2fa-dans-vos-tests.html">la page de référence</a> détaille ce partage.</p>
    <p>Les quatre familles de second facteur ne posent d'ailleurs pas le même problème&nbsp;: un code calculé se recalcule, une demande à approuver ne se calcule pas. La distinction est faite dans <a href="automatiser-2fa-sans-cle-secrete.html">« automatiser la 2FA sans clé secrète partagée »</a>.</p>"""),
        dict(id='rustines-title', label='Les rustines',
             titre="Que coûtent les trois rustines habituelles&nbsp;?",
             capsule="Une astreinte de nuit coûte cher et n'est pas tenable longtemps. Un compte sans second facteur fait passer les tests mais ne teste plus le parcours réel. Et sauter l'étape en test vide de son sens toute assertion qui vient après la connexion.",
             corps="""    <p>Les trois, avec leur facture&nbsp;:</p>
""" + liste([
                 "<strong>quelqu'un d'astreinte</strong>&nbsp;: ça marche une semaine, pas un trimestre, et ça se paie en heures",
                 "<strong>un compte sans 2FA</strong>&nbsp;: rapide, mais le parcours testé n'est plus celui des utilisateurs",
                 "<strong>sauter l'étape</strong>&nbsp;: la campagne repasse au vert et ne prouve plus la même chose",
             ]) + """
    <p style="margin-top:26px;">La deuxième et la troisième se défendent dans certains cas&nbsp;: <a href="desactiver-2fa-en-test.html">le guide sur la désactivation en test</a> dit lesquels, et lesquels non. La première se chiffre, et c'est le sujet du <a href="cout-etape-manuelle-authentification.html">guide sur le coût de l'étape manuelle</a>.</p>"""),
        dict(id='bout-title', label='Ce qu\'il faut',
             titre="Que faut-il pour qu'une campagne aille au bout&nbsp;?",
             capsule="Que l'étape se franchisse sans personne, sur le parcours réel. Cela suppose un appareil qui reste enrôlé, joignable depuis votre chaîne de tests, et une commande que le test puisse déclencher lui-même au moment voulu. Trois conditions, et toutes les trois se vérifient avant d'acheter quoi que ce soit.",
             corps="""    <p>Trois conditions, et elles se vérifient avant d'acheter quoi que ce soit&nbsp;:</p>
""" + liste([
                 "un appareil <strong>enrôlé une fois</strong> et qui le reste d'une nuit à l'autre",
                 "un appareil qui <strong>joint votre environnement</strong> de test sans passerelle",
                 "une <strong>commande déclenchable</strong> depuis la chaîne, au moment où le test en a besoin",
             ]) + """
    <p style="margin-top:26px;">Les deux familles d'outils qui répondent à ces conditions sont comparées dans <a href="tester-2fa-appareil-reel.html">« quel outil pour tester la 2FA sur appareil réel »</a>.</p>"""),
    ])

NUIT_EN = dict(
    title="Why your night runs stop at login | Q-Leap",
    desc="A cluster of failures in the same place with the same trace: it is almost always the second factor. The three usual workarounds, and what they really cost.",
    fil='Runs blocked at login', label='Guide',
    h1="Why your night runs stop at login",
    lead="The morning report shows a cluster of failures, all in the same place, with the same trace. It is almost never a flaky suite: it is a step nothing could clear overnight. This guide covers the symptom, the usual workarounds, and what it takes to reach the end.",
    sections=[
        dict(id='symptome-title', label='The symptom',
             titre="What does the symptom look like in a report?",
             capsule="A cluster of failures sharing three traits: there are many of them, they all land at the same point in the journey, and they carry the same trace. A genuinely flaky suite fails in a scattered way; this one fails with a regularity that should raise a flag.",
             corps="""    <p>The three signs that separate a blockage from instability:</p>
""" + liste([
                 "failures are <strong>clustered</strong> on one step, not scattered through the suite",
                 "the trace is <strong>identical</strong> from one scenario to the next",
                 "the scenarios that never go through sign-in do <strong>pass</strong>",
             ]) + """
    <p style="margin-top:26px;">When those three signs line up, looking for the cause inside the suite is wasted time: the cause is upstream.</p>"""),
        dict(id='pourquoi-title', label='The cause',
             titre="Why is it almost always the second factor?",
             capsule="Because it is the only step in the journey waiting for a human gesture. Everything else automates: typing, navigation, assertions. An approval on a phone does not: it waits for someone, and at three in the morning there is nobody.",
             corps="""    <p>A browser driver acts on the rendered document. As soon as the step leaves the browser it has no hold: no selector reaches a phone's screen. That is not a weakness of the tool, it is its scope, and <a href="automate-2fa-in-your-tests.html">the reference page</a> sets out that division.</p>
    <p>The four families of second factor do not pose the same problem either: a computed code can be recomputed, an approval request cannot. That distinction is drawn in <a href="automate-2fa-without-shared-secret.html">« automating 2FA without a shared secret »</a>.</p>"""),
        dict(id='rustines-title', label='The workarounds',
             titre="What do the three usual workarounds cost?",
             capsule="Someone on night duty is expensive and not sustainable for long. An account without a second factor makes tests pass but stops testing the real journey. And skipping the step empties every assertion that comes after sign-in of its meaning.",
             corps="""    <p>All three, with their bill:</p>
""" + liste([
                 "<strong>someone on duty</strong>: it works for a week, not a quarter, and it is paid in hours",
                 "<strong>an account without 2FA</strong>: quick, but the journey tested is no longer the users'",
                 "<strong>skipping the step</strong>: the run goes green again and no longer proves the same thing",
             ]) + """
    <p style="margin-top:26px;">The second and third are defensible in some cases: <a href="disable-2fa-in-testing.html">the guide on disabling 2FA in testing</a> says which, and which not. The first one can be costed, and that is the subject of the <a href="cost-of-manual-authentication-step.html">guide on the cost of the manual step</a>.</p>"""),
        dict(id='bout-title', label='What it takes',
             titre="What does it take for a run to reach the end?",
             capsule="That the step is cleared with nobody there, on the real journey. That means a device which stays enrolled between runs, one that is reachable from your pipeline, and a command the test can trigger itself at the right moment. All three can be checked before buying anything.",
             corps="""    <p>Three conditions, and they can be checked before buying anything:</p>
""" + liste([
                 "a device <strong>enrolled once</strong> that stays enrolled from one night to the next",
                 "a device that <strong>reaches your test environment</strong> with no gateway",
                 "a <strong>triggerable command</strong> from the pipeline, at the moment the test needs it",
             ]) + """
    <p style="margin-top:26px;">The two families of tools that meet those conditions are compared in <a href="test-2fa-real-device.html">« which tool for testing 2FA on a real device »</a>.</p>"""),
    ])


# ── Guide 8 · le coût. AUCUN TARIF Q-BOT N'Y FIGURE, ni en clair ni par déduction :
#    arbitrage du client du 2026-08-24. Le calcul rend au lecteur SON coût, en heures.
COUT_FR = dict(
    title="Combien coûte l'étape manuelle d'authentification ? | Q-Leap",
    desc="Le calcul se fait en heures, avec vos chiffres : testeurs, minutes perdues, jours ouvrés. Les trois coûts qu'on oublie, et ce que le calcul ne dit pas.",
    fil='Le coût de l\'étape manuelle', label='Guide',
    h1="Combien coûte l'étape manuelle d'authentification&nbsp;?",
    lead="Personne ne peut répondre à votre place&nbsp;: le chiffre dépend de vos effectifs et de vos campagnes. Ce guide donne la formule, les trois coûts que l'on oublie systématiquement, et ce que ce calcul ne dit pas. Vous repartez avec votre chiffre, pas avec le nôtre.",
    sections=[
        dict(id='formule-title', label='Le calcul',
             titre="Comment se calcule le coût, en heures&nbsp;?",
             capsule="Trois nombres suffisent&nbsp;: combien de personnes sont mobilisées par cette étape, combien de minutes chacune y perd par jour, et combien de jours ouvrés compte le mois. Le produit des trois donne des heures, et les heures se convertissent en journées de test.",
             corps="""    <p>La formule, telle quelle&nbsp;:</p>
""" + liste([
                 "<strong>testeurs mobilisés</strong> × <strong>minutes perdues par jour</strong> × <strong>21 jours ouvrés</strong>",
                 "le résultat est en minutes&nbsp;: divisé par 60, il donne des heures",
                 "divisé par 7, il donne des <strong>journées de test</strong>, l'unité dans laquelle on planifie",
             ]) + """
    <p style="margin-top:26px;">Le calcul est posé sur la <a href="../commandez.html">page de démonstration</a>, avec deux curseurs et le détail affiché sous le résultat. Un grand nombre sans son calcul est un argument publicitaire&nbsp;; avec son calcul, c'est une mesure que vous pouvez contredire.</p>"""),
        dict(id='oublies-title', label='Ce qu\'on oublie',
             titre="Quels sont les trois coûts que l'on oublie&nbsp;?",
             capsule="Le temps de reprise après interruption, qui ne se voit dans aucun relevé. La disponibilité de nuit, qui ne se paie pas au tarif de jour. Et les campagnes abandonnées, dont le coût n'est pas le temps passé mais l'information qu'on n'a pas eue.",
             corps="""    <p>Les trois, dans l'ordre où ils grossissent&nbsp;:</p>
""" + liste([
                 "la <strong>reprise après interruption</strong>&nbsp;: valider un code prend dix secondes, retrouver le fil en prend davantage",
                 "la <strong>disponibilité de nuit</strong>&nbsp;: une astreinte ne se compare pas à une heure de journée",
                 "les <strong>campagnes abandonnées</strong>&nbsp;: le coût n'est pas le temps passé, c'est le défaut qu'on n'a pas vu",
             ]) + """
    <p style="margin-top:26px;">Le troisième est le plus lourd et le plus difficile à chiffrer. Le symptôme, lui, est visible dès le rapport du matin&nbsp;: <a href="campagnes-de-nuit-bloquees-au-login.html">« pourquoi vos campagnes de nuit s'arrêtent au login »</a>.</p>"""),
        dict(id='mesurer-title', label='Chez vous',
             titre="Comment le mesurer chez vous cette semaine&nbsp;?",
             capsule="Sans outil et sans réunion&nbsp;: relevez pendant cinq jours le nombre de validations manuelles faites par votre équipe, et le nombre de scénarios en échec à la même étape. Deux colonnes dans un tableur suffisent, et le résultat est difficile à contester.",
             corps="""    <p>Le protocole, tel qu'il tient sur un coin de table&nbsp;:</p>
""" + liste([
                 "une ligne par jour, deux colonnes&nbsp;: <strong>validations faites à la main</strong> et <strong>scénarios en échec à cette étape</strong>",
                 "cinq jours, pas un&nbsp;: un lundi ne ressemble pas à un jeudi de fin d'itération",
                 "notez à part les <strong>campagnes relancées</strong> le lendemain matin",
             ]) + """
    <p style="margin-top:26px;">Ce relevé sert deux fois&nbsp;: il donne le chiffre, et il montre à une direction où part le temps.</p>"""),
        dict(id='pasdit-title', label='Les limites du calcul',
             titre="Qu'est-ce que ce calcul ne dit pas&nbsp;?",
             capsule="Il ne dit pas ce qu'une solution coûte, il dit ce que le problème coûte. Convertir des heures en euros demanderait votre taux horaire, que nous n'avons pas et que nous n'inventerons pas. Le rapprochement des deux, c'est votre calcul, avec vos chiffres.",
             corps="""    <p>Deux précisions qui rendent ce calcul défendable&nbsp;:</p>
""" + liste([
                 "il rend un résultat en <strong>heures et en journées</strong>, jamais en euros&nbsp;: le taux horaire est le vôtre",
                 "il ne suppose <strong>aucun gain</strong> de notre côté&nbsp;: c'est votre coût actuel, pas une économie promise",
             ]) + """
    <p style="margin-top:26px;">Ce que change concrètement l'automatisation de cette étape est décrit dans la <a href="automatiser-2fa-dans-vos-tests.html">page de référence</a>, et le tarif se donne en démonstration, pas dans un guide.</p>"""),
    ])

COUT_EN = dict(
    title="What does the manual authentication step cost? | Q-Leap",
    desc="The calculation is in hours, with your numbers: testers, minutes lost, working days. The three costs people forget, and what it does not say.",
    fil='Cost of the manual step', label='Guide',
    h1="What does the manual authentication step cost?",
    lead="Nobody can answer for you: the figure depends on your headcount and your runs. This guide gives the formula, the three costs that are systematically forgotten, and what the calculation does not say. You leave with your own number, not ours.",
    sections=[
        dict(id='formule-title', label='The calculation',
             titre="How is the cost calculated, in hours?",
             capsule="Three numbers are enough: how many people this step ties up, how many minutes each of them loses per day, and how many working days the month holds. Their product gives minutes, minutes give hours, and hours convert into testing days, which is the unit you actually plan in.",
             corps="""    <p>The formula, as it stands:</p>
""" + liste([
                 "<strong>testers involved</strong> × <strong>minutes lost per day</strong> × <strong>21 working days</strong>",
                 "the result is in minutes: divided by 60, it gives hours",
                 "divided by 7, it gives <strong>testing days</strong>, the unit you plan in",
             ]) + """
    <p style="margin-top:26px;">The calculation sits on the <a href="../order.html">demo page</a>, with two sliders and the working shown under the result. A large number without its working is an advertising claim; with its working, it is a measurement you can argue with.</p>"""),
        dict(id='oublies-title', label='What gets forgotten',
             titre="What are the three costs people forget?",
             capsule="The recovery time after an interruption, which appears in no timesheet. Night availability, which is not paid at daytime rates. And abandoned runs, whose cost is not the time spent but the information nobody ever got. The third one is the heaviest and the hardest to price.",
             corps="""    <p>All three, in the order in which they grow:</p>
""" + liste([
                 "<strong>recovery after interruption</strong>: approving a code takes ten seconds, picking the thread back up takes longer",
                 "<strong>night availability</strong>: being on call does not compare to a daytime hour",
                 "<strong>abandoned runs</strong>: the cost is not the time spent, it is the defect nobody saw",
             ]) + """
    <p style="margin-top:26px;">The third is the heaviest and the hardest to cost. The symptom, though, is visible in the morning report: <a href="night-runs-blocked-at-login.html">« why your night runs stop at login »</a>.</p>"""),
        dict(id='mesurer-title', label='On your side',
             titre="How do you measure it this week?",
             capsule="With no tool and no meeting: for five days, record how many manual approvals your team performs and how many scenarios fail at that same step. Two columns in a spreadsheet are enough, and the result is hard to argue with.",
             corps="""    <p>The protocol, as it fits on the back of an envelope:</p>
""" + liste([
                 "one row per day, two columns: <strong>approvals done by hand</strong> and <strong>scenarios failing at that step</strong>",
                 "five days, not one: a Monday does not look like the Thursday at the end of a sprint",
                 "note separately the <strong>runs relaunched</strong> the next morning",
             ]) + """
    <p style="margin-top:26px;">The record serves twice: it gives you the number, and it shows management where the time goes.</p>"""),
        dict(id='pasdit-title', label='The limits of the calculation',
             titre="What does this calculation not say?",
             capsule="It does not say what a solution costs, it says what the problem costs. Turning hours into money would need your hourly rate, which we do not have and will not invent. Putting the two together is your calculation, with your numbers.",
             corps="""    <p>Two points that make this calculation defensible:</p>
""" + liste([
                 "it returns a result in <strong>hours and days</strong>, never in money: the hourly rate is yours",
                 "it assumes <strong>no gain</strong> on our side: it is your current cost, not a promised saving",
             ]) + """
    <p style="margin-top:26px;">What automating this step actually changes is described on the <a href="automate-2fa-in-your-tests.html">reference page</a>, and pricing is given in a demo, not in a guide.</p>"""),
    ])

GUIDES = [
    # LA PAGE PILIER EST LE MOYEU : elle pointe vers les sept autres, chacun lui
    # renvoie, et les pages produit pointent vers le guide qui les prolonge. Huit
    # guides isolés ne pèsent rien ; c'est le maillage qui les fait exister.
    guide('automatiser-authentification-luxtrust.html', 'automate-luxtrust-authentication.html',
          dict(LUX_FR, **CTA_FR, **DATE_FR), dict(LUX_EN, **CTA_EN, **DATE_EN)),
    guide('desactiver-2fa-en-test.html', 'disable-2fa-in-testing.html',
          dict(DESACT_FR, **CTA_FR, **DATE_FR), dict(DESACT_EN, **CTA_EN, **DATE_EN)),
    guide('automatiser-2fa-dans-vos-tests.html', 'automate-2fa-in-your-tests.html',
          dict(PILIER_FR, **CTA_FR, **DATE_FR), dict(PILIER_EN, **CTA_EN, **DATE_EN)),
    guide('tester-2fa-appareil-reel.html', 'test-2fa-real-device.html',
          dict(REEL_FR, **CTA_FR, **DATE_FR), dict(REEL_EN, **CTA_EN, **DATE_EN)),
    guide('securite-conformite-donnees-de-test.html', 'security-compliance-test-data.html',
          dict(SECU_FR, **CTA_FR, **DATE_FR), dict(SECU_EN, **CTA_EN, **DATE_EN)),
    guide('automatiser-2fa-sans-cle-secrete.html', 'automate-2fa-without-shared-secret.html',
          dict(SANSCLE_FR, **CTA_FR, **DATE_FR), dict(SANSCLE_EN, **CTA_EN, **DATE_EN)),
    guide('campagnes-de-nuit-bloquees-au-login.html', 'night-runs-blocked-at-login.html',
          dict(NUIT_FR, **CTA_FR, **DATE_FR), dict(NUIT_EN, **CTA_EN, **DATE_EN)),
    guide('cout-etape-manuelle-authentification.html', 'cost-of-manual-authentication-step.html',
          dict(COUT_FR, **CTA_FR, **DATE_FR), dict(COUT_EN, **CTA_EN, **DATE_EN)),
]

ECRITS = []

for _g in GUIDES:
    for cfg in (_g['fr'], _g['en']):
        # les deux contraintes dures d'affichage en recherche, avant d'écrire
        assert len(cfg['title']) <= 62, (cfg['fichier'], 'titre', len(cfg['title']))
        assert len(cfg['desc']) <= 158, (cfg['fichier'], 'description', len(cfg['desc']))
        s = construire(cfg)
        # Le cadratin est interdit dans le CONTENU, pas dans les commentaires de
        # l'habillage extrait, que le visiteur ne lit pas. Le contrôle porte donc sur
        # le document commentaires retirés, et sur le caractère ET l'entité.
        visible = re.sub(r'<!--.*?-->', '', s, flags=re.S)
        assert '\u2014' not in visible and '&mdash;' not in visible, (cfg['fichier'], 'cadratin')
        chemin = os.path.join(RACINE, cfg['fichier'])
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        io.open(chemin, 'w', encoding='utf-8').write(s)
        ECRITS.append(chemin)
        print("  écrit %-48s titre %d c, description %d c"
              % (cfg['fichier'], len(cfg['title']), len(cfg['desc'])))

# LE GARDE-FOU QUI COMPTE, et il tourne quand LES DEUX pages existent : elles se
# désignent mutuellement par le sélecteur de langue, donc un contrôle page par page
# échouerait sur la première. La transformation de profondeur est mécanique ; la
# seule preuve qu'elle est juste est que chaque chemin relatif produit désigne un
# fichier réel. Sans cette assertion, un `../` en trop passe inaperçu jusqu'à ce
# qu'un visiteur clique.
for chemin in ECRITS:
    contenu = io.open(chemin, encoding='utf-8').read()
    base = os.path.dirname(chemin)
    relatifs, casses = set(), []
    for v in re.findall(r'\b(?:href|src)="([^"]*)"', contenu):
        if not v or re.match(r'^(https?:|//|mailto:|tel:|data:|#)', v):
            continue
        relatifs.add(v)
        cible = os.path.normpath(os.path.join(base, v.split('?')[0].split('#')[0]))
        if os.path.isdir(cible):
            cible = os.path.join(cible, 'index.html')
        if not os.path.exists(cible):
            casses.append(v)
    assert not casses, (os.path.relpath(chemin, RACINE),
                        'chemins relatifs cassés : ' + ', '.join(sorted(set(casses))[:6]))
    print('  %-46s %d chemin(s) relatif(s), tous valides'
          % (os.path.relpath(chemin, RACINE), len(relatifs)))
