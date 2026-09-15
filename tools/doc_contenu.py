# -*- coding: utf-8 -*-
"""Le contenu de la page Documentation technique, dans les deux langues.

SÉPARÉ DU GÉNÉRATEUR À DESSEIN : le gabarit ne change presque jamais, le texte
oui. Les deux dictionnaires ont les mêmes clés et le générateur le VÉRIFIE, ce
qui est le seul moyen qu'une section ajoutée d'un côté ne manque pas de l'autre.

RIEN N'EST INVENTÉ ICI. Chaque fait vient d'une page déjà publiée du site (fiche
technique, « Comment ça marche », FAQ) ou d'un document fourni par le client.
CE QUI MANQUE MANQUE VRAIMENT, et il ne faut pas le combler de tête :
  • aucune procédure d'installation pas à pas (le dépôt ne connaît que
    « conteneurs Docker, une seule commande Docker Compose ») ;
  • aucun dépannage : il n'existe pas une ligne sur le sujet ;
  • sur la sécurité, trois faits et pas un de plus (auto-hébergé, aucune clé
    d'API attendue, aucun appel externe pendant les tests). Une note du dépôt
    dit en toutes lettres de ne pas enrichir cette ligne sans information du
    client : rien sur l'authentification de l'API, les ACL ou l'isolation.
"""

# ── L'EN-TÊTE DE PAGE ──────────────────────────────────────────────────────
# LE TITRE PORTE « LuxTrust » À DESSEIN. La règle de l'audit RosoAI, vérifiée par
# `tools/audit-visibilite.py` : un titre qui contient « Q-Bot » doit contenir aussi
# « Q-Leap » ou « LuxTrust », sans quoi il désigne trois homonymes (un gestionnaire
# de file GitHub, une société britannique de robotique, l'ancien système de file de
# LEGOLAND). `titre_court` sert là où la qualification serait du bruit.
META = {
    'fr': dict(
        titre='Documentation technique de Q-Bot | Robot 2FA LuxTrust',
        titre_court='Documentation technique de Q-Bot',
        desc="Installer Q-Bot sur votre réseau, y relier un smartphone Android, "
             "construire un scénario et le déclencher par l'API REST depuis votre "
             "chaîne de tests.",
        label='Documentation',
        h1='Documentation technique',
        chapeau="Retrouvez ici les détails techniques de <span class=\"nb\">Q-Bot</span>, ainsi "
                "que les informations nécessaires pour l'installer, le configurer et l'utiliser.",
        sommaire='Sommaire',
    ),
    'en': dict(
        titre='Q-Bot technical documentation | LuxTrust 2FA robot',
        titre_court='Q-Bot technical documentation',
        desc="Install Q-Bot on your network, connect an Android phone, build a "
             "scenario and trigger it over the REST API from your test suite.",
        label='Documentation',
        h1='Technical documentation',
        chapeau="Find here the technical details of <span class=\"nb\">Q-Bot</span>, along with "
                "what you need to install it, configure it and use it.",
        sommaire='Contents',
    ),
}

# ── LES SECTIONS ───────────────────────────────────────────────────────────
# `corps` est une liste de blocs : ('p', texte) · ('faits', [..]) ·
# ('fiche', [(libellé, valeur), ..]) · ('ficheapi', [..]) pour la variante à
# libellés en chasse fixe · ('exemples', None) qui insère les cinq accordéons
# d'appel EXTRAITS de la page donneuse.
SECTIONS = {
 'fr': [
  dict(id='doc-architecture', label='Architecture', titre="Comment <span class=\"nb\">Q-Bot</span> fonctionne",
       chapeau="<span class=\"nb\">Q-Bot</span> est un nano-ordinateur autonome installé sur votre "
               "réseau local, avec une interface web intégrée.",
       visuel=dict(src='assets/img/qbot-gen-actuelle.webp', w=1000, h=969,
                   alt="Le robot Q-Bot, boîtier d'automatisation de la double authentification"),
       corps=[
        ('p', "Le téléphone sous test est relié à <span class=\"nb\">Q-Bot</span> par un câble USB. "
              "<span class=\"nb\">Q-Bot</span> le pilote via ADB, l'outil standard d'Android&nbsp;: "
              "chaque interaction est exécutée directement sur l'appareil, dans l'application "
              "d'authentification."),
        ('p', "Pendant les tests, <span class=\"nb\">Q-Bot</span> fonctionne localement, sans "
              "dépendre d'un service externe ni d'une connexion internet."),
        ('faits', ["Votre chaîne de tests appelle <span class=\"nb\">Q-Bot</span> en HTTP",
                   "<span class=\"nb\">Q-Bot</span> rejoue le scénario sur le téléphone, par ADB",
                   "Le second facteur est validé dans la vraie application",
                   "Votre test reprend son cours"]),
       ]),
  dict(id='doc-install', label='Installation', titre="Installation et réseau",
       chapeau="Le boîtier arrive prêt. Ce qu'il faut savoir, c'est où le brancher et ce "
               "qu'il attend de votre réseau.",
       corps=[
        ('fiche', [("Système", "Raspberry Pi OS Lite"),
                   ("Déploiement", "Conteneurs Docker, lancés par une seule commande Docker Compose"),
                   ("Réseau", "Ethernet Gigabit, Wi-Fi 5 (IEEE 802.11ac), Bluetooth"),
                   ("Accès", "Interface web, servie par le boîtier sur votre réseau local"),
                   ("Connexion internet", "Aucune n'est nécessaire pendant les tests"),
                   ("Mise en service", "48 à 72 heures après la commande")]),
        ('p', "Le boîtier se place sur le même réseau que la machine qui exécute vos tests&nbsp;: "
              "c'est ce réseau, et lui seul, qui donne accès à l'interface et à l'API."),
       ], gris=True),
  dict(id='doc-phone', label='Smartphone', titre="Connexion du smartphone",
       chapeau="Un téléphone Android physique, relié en USB, piloté par ADB. Ni émulateur, "
               "ni simulateur, ni application bouchon.",
       corps=[
        ('fiche', [("Système", "Android"),
                   ("Appareil", "Physique, ni émulateur ni simulateur"),
                   ("Liaison", "Câble USB entre le boîtier et le téléphone"),
                   ("Pilotage", "<a href=\"https://developer.android.com/tools/adb\" target=\"_blank\" rel=\"noopener\">ADB</a>, l'outil standard d'Android"),
                   ("Applications", "La véritable application 2FA, installée sur le téléphone")]),
        ('p', "Un boîtier pilote un appareil à la fois, et les demandes sont traitées l'une "
              "après l'autre, dans leur ordre d'arrivée."),
       ]),
  dict(id='doc-scenarios', label='Scénarios', titre="Création des scénarios",
       chapeau="Un scénario se construit à l'écran, sur une capture de l'application testée. "
               "Il n'y a pas de langage de script à apprendre.",
       corps=[
        ('faits', ["Une capture de l'écran de l'application sert de fond d'étape",
                   "Les points d'appui se posent au clic, et sont numérotés",
                   "Les temps d'attente se règlent à la milliseconde",
                   "Les étapes se réordonnent",
                   "Les scénarios sont versionnés dans le boîtier",
                   "Les captures restent stockées localement"]),
        ('p', "Chaque scénario porte un identifiant numérique&nbsp;: c'est lui que votre chaîne "
              "de tests appellera."),
       ], gris=True),
  dict(id='doc-api', label='API REST', titre="L'API REST",
       chapeau="Trois points d'entrée, en HTTP, sur le réseau local. Aucun SDK, aucun greffon "
               "propriétaire, aucun agent à installer dans votre intégration continue.",
       corps=[
        ('ficheapi', [("GET /scenarios/:id/execute", "Exécute un scénario enregistré sur le téléphone relié."),
                      ("GET /get-luxtrust-otp", "Renvoie le code à usage unique affiché par l'app LuxTrust."),
                      ("POST /display-image", "Affiche un QR code sur l'écran du boîtier.")]),
        ('faits', ["Auto-hébergé&nbsp;: tout reste sur votre réseau local",
                   "Compatible avec toute chaîne capable d'un appel HTTP",
                   "L'API n'attend aucune clé&nbsp;: le contrôle d'accès est celui de votre réseau"]),
       ]),
  dict(id='doc-call', label='Intégration', titre="Déclencher depuis votre chaîne de tests",
       chapeau="Le même appel HTTP, dans cinq outils. Dépliez celui qui vous concerne.",
       corps=[('exemples', None)], gris=True),
  dict(id='doc-companion', label='App compagnon', titre="L'app compagnon",
       chapeau="Le second chemin de déclenchement&nbsp;: l'application s'installe sur le téléphone "
               "sous test et part seule dès qu'une notification 2FA arrive.",
       corps=[
        ('p', "Installée sur le téléphone sous test, elle surveille les notifications des "
              "applications d'authentification et déclenche le scénario correspondant dès qu'une "
              "arrive. Aucun appel depuis votre chaîne de tests n'est nécessaire."),
        ('p', "Les deux chemins de déclenchement coexistent dans le même environnement&nbsp;: "
              "l'appel HTTP quand c'est votre test qui décide, l'app compagnon quand c'est "
              "l'application testée qui réclame le second facteur."),
       ]),
  dict(id='doc-qr', label='QR code', titre="Le QR code sur l'écran du boîtier",
       chapeau="Le boîtier porte un petit écran intégré. <code>POST /display-image</code> y "
               "affiche un QR code que le téléphone vient scanner.",
       corps=[
        ('p', "Certains parcours d'authentification demandent de scanner une image plutôt que "
              "de saisir un code. L'écran du boîtier sert alors de support&nbsp;: votre test y "
              "envoie l'image, le téléphone la scanne, le parcours continue."),
       ], gris=True),
  dict(id='doc-data', label='Données', titre="Stockage des données",
       chapeau="Les scénarios et leurs captures restent sur le boîtier. Rien n'est envoyé "
               "vers un service extérieur.",
       corps=[
        ('fiche', [("Base", "SQLite, sur le boîtier"),
                   ("Captures", "Stockées sur le boîtier"),
                   ("Cloud", "Aucune dépendance pendant l'exécution"),
                   ("Données", "De test uniquement")]),
        ('p', "<span class=\"nb\">Q-Bot</span> est conçu pour des données de test. Les comptes "
              "utilisés dans vos scénarios doivent être des comptes de test."),
       ]),
  dict(id='doc-security', label='Sécurité', titre="Sécurité",
       chapeau="Ce que le produit garantit aujourd'hui, et ce qu'il laisse à votre "
               "infrastructure. Énoncé tel quel, sans promesse au-delà.",
       corps=[
        ('faits', ["Auto-hébergé&nbsp;: le boîtier vit sur votre réseau, pas dans un cloud",
                   "Aucun appel vers un service extérieur pendant l'exécution des tests",
                   "Aucune connexion internet n'est nécessaire pour exécuter un scénario",
                   "Les scénarios et les captures ne quittent pas le boîtier"]),
        ('p', "<strong>L'API n'attend aucune clé d'authentification.</strong> Le contrôle d'accès "
              "est donc celui de votre réseau&nbsp;: placez le boîtier sur un segment dont l'accès "
              "est déjà maîtrisé, comme vous le feriez pour tout équipement de test. Pour toute "
              "question de conformité propre à votre environnement, "
              "<a href=\"contact.html\">écrivez-nous</a>."),
       ], gris=True),
  dict(id='doc-support', label='Support', titre="Support et remplacement",
       chapeau="Ce qui est inclus dans la location, et ce qui se passe en cas de panne.",
       corps=[
        ('fiche', [("Support", "Inclus, réponse sous 24 h ouvrées"),
                   ("Panne", "Réparation à distance en premier recours"),
                   ("Remplacement", "Boîtier neuf si la réparation n'aboutit pas"),
                   ("Mise en service", "48 à 72 heures après la commande")]),
       ]),
 ],
 'en': [
  dict(id='doc-architecture', label='Architecture', titre="How <span class=\"nb\">Q-Bot</span> works",
       chapeau="<span class=\"nb\">Q-Bot</span> is a self-contained nano-computer installed on your "
               "local network, with a built-in web interface.",
       visuel=dict(src='assets/img/qbot-gen-actuelle.webp', w=1000, h=969,
                   alt="The Q-Bot device, two-factor authentication automation robot"),
       corps=[
        ('p', "The phone under test is connected to <span class=\"nb\">Q-Bot</span> with a USB cable. "
              "<span class=\"nb\">Q-Bot</span> drives it over ADB, the standard Android tool: every "
              "interaction runs directly on the device, inside the authentication app."),
        ('p', "While tests run, <span class=\"nb\">Q-Bot</span> works locally, with no dependency on "
              "an external service or an internet connection."),
        ('faits', ["Your test suite calls <span class=\"nb\">Q-Bot</span> over HTTP",
                   "<span class=\"nb\">Q-Bot</span> replays the scenario on the phone, over ADB",
                   "The second factor is approved in the real app",
                   "Your test carries on"]),
       ]),
  dict(id='doc-install', label='Installation', titre="Installation and network",
       chapeau="The device arrives ready. What matters is where you plug it in and what it "
               "expects from your network.",
       corps=[
        ('fiche', [("System", "Raspberry Pi OS Lite"),
                   ("Deployment", "Docker containers, started with a single Docker Compose command"),
                   ("Network", "Gigabit Ethernet, Wi-Fi 5 (IEEE 802.11ac), Bluetooth"),
                   ("Access", "Web interface, served by the device on your local network"),
                   ("Internet connection", "None is needed while tests run"),
                   ("Lead time", "48 to 72 hours after ordering")]),
        ('p', "Put the device on the same network as the machine that runs your tests: that "
              "network, and only that network, is what gives access to the interface and the API."),
       ], gris=True),
  dict(id='doc-phone', label='Smartphone', titre="Connecting the phone",
       chapeau="A physical Android phone, connected over USB, driven by ADB. No emulator, no "
               "simulator, no stub app.",
       corps=[
        ('fiche', [("System", "Android"),
                   ("Device", "Physical, neither emulator nor simulator"),
                   ("Link", "USB cable between the device and the phone"),
                   ("Driving", "<a href=\"https://developer.android.com/tools/adb\" target=\"_blank\" rel=\"noopener\">ADB</a>, the standard Android tool"),
                   ("Apps", "The genuine 2FA app, installed on the phone")]),
        ('p', "One device drives one phone at a time, and requests are handled one after "
              "another, in the order they arrive."),
       ]),
  dict(id='doc-scenarios', label='Scenarios', titre="Building scenarios",
       chapeau="A scenario is built on screen, on a screenshot of the app under test. There is "
               "no scripting language to learn.",
       corps=[
        ('faits', ["A screenshot of the app is the background of each step",
                   "Tap points are placed with a click, and numbered",
                   "Waits are set to the millisecond",
                   "Steps can be reordered",
                   "Scenarios are versioned on the device",
                   "Screenshots stay stored locally"]),
        ('p', "Each scenario carries a numeric id: that is what your test suite will call."),
       ], gris=True),
  dict(id='doc-api', label='REST API', titre="The REST API",
       chapeau="Three endpoints, over HTTP, on the local network. No SDK, no proprietary "
               "plugin, no agent to install in your continuous integration.",
       corps=[
        ('ficheapi', [("GET /scenarios/:id/execute", "Runs a saved scenario on the connected phone."),
                      ("GET /get-luxtrust-otp", "Returns the one-time code shown by the LuxTrust app."),
                      ("POST /display-image", "Shows a QR code on the device screen.")]),
        ('faits', ["Self-hosted: everything stays on your local network",
                   "Works with any test suite that can make an HTTP call",
                   "The API expects no key: access control is your network's"]),
       ]),
  dict(id='doc-call', label='Integration', titre="Triggering from your test suite",
       chapeau="The same HTTP call, in five tools. Open the one you need.",
       corps=[('exemples', None)], gris=True),
  dict(id='doc-companion', label='Companion app', titre="The companion app",
       chapeau="The second way to trigger a run: the app is installed on the phone under test "
               "and starts on its own as soon as a 2FA notification arrives.",
       corps=[
        ('p', "Installed on the phone under test, it watches the notifications of the "
              "authentication apps and triggers the matching scenario as soon as one arrives. "
              "No call from your test suite is needed."),
        ('p', "Both trigger paths live side by side in the same environment: the HTTP call when "
              "your test decides, the companion app when the app under test asks for the second "
              "factor."),
       ]),
  dict(id='doc-qr', label='QR code', titre="The QR code on the device screen",
       chapeau="The device has a small built-in screen. <code>POST /display-image</code> shows "
               "a QR code on it for the phone to scan.",
       corps=[
        ('p', "Some authentication flows ask you to scan an image rather than type a code. The "
              "device screen then acts as the display: your test sends the image, the phone "
              "scans it, the flow carries on."),
       ], gris=True),
  dict(id='doc-data', label='Data', titre="Data storage",
       chapeau="Scenarios and their screenshots stay on the device. Nothing is sent to an "
               "external service.",
       corps=[
        ('fiche', [("Database", "SQLite, on the device"),
                   ("Screenshots", "Stored on the device"),
                   ("Cloud", "No dependency while tests run"),
                   ("Data", "Test data only")]),
        ('p', "<span class=\"nb\">Q-Bot</span> is built for test data. The accounts used in your "
              "scenarios should be test accounts."),
       ]),
  dict(id='doc-security', label='Security', titre="Security",
       chapeau="What the product guarantees today, and what it leaves to your infrastructure. "
               "Stated as it stands, with no promise beyond.",
       corps=[
        ('faits', ["Self-hosted: the device lives on your network, not in a cloud",
                   "No call to an external service while tests run",
                   "No internet connection is needed to run a scenario",
                   "Scenarios and screenshots do not leave the device"]),
        ('p', "<strong>The API expects no authentication key.</strong> Access control is therefore "
              "your network's: put the device on a segment whose access is already controlled, as "
              "you would for any test equipment. For any compliance question specific to your "
              "environment, <a href=\"contact.html\">write to us</a>."),
       ], gris=True),
  dict(id='doc-support', label='Support', titre="Support and replacement",
       chapeau="What the rental includes, and what happens if the device fails.",
       corps=[
        ('fiche', [("Support", "Included, answer within 24 working hours"),
                   ("Failure", "Remote repair first"),
                   ("Replacement", "A new device if the repair does not succeed"),
                   ("Lead time", "48 to 72 hours after ordering")]),
       ]),
 ],
}
