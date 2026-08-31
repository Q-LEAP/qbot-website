#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Écrit la page de réservation, dans les deux langues.

    python3 tools/gen-reservation.py

Demandée par le client le 2026-08-31 : une page dédiée, distincte de la page
contact, qui garde son formulaire. Elle porte le seul lien vers Microsoft
Bookings du site ; les huit appels à l'action des autres pages mènent ici.

GÉNÉRÉE et non écrite à la main, comme les pages légales, les guides et les
variantes d'accueil : deux pages rédigées l'une après l'autre divergent.
L'habillage est extrait de la page contact, qui est au MÊME niveau de
profondeur, donc aucun chemin relatif n'est à réécrire.

CE QU'ELLE N'AFFIRME PAS, ET C'EST DÉLIBÉRÉ : aucun format de rendez-vous.
Relevé le 2026-08-31 dans la page Bookings elle-même, elle n'annonce ni réunion
Teams ni lieu pour le rendez-vous (l'adresse affichée est celle de la société).
Écrire « en visioconférence » ou « dans nos locaux » serait une invention. Le
jour où l'option est activée côté Bookings, la ligne est à ajouter ici.
"""
import io, os, re, sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOKINGS = ('https://outlook.office.com/book/'
            'DmonstrationQBotwithSylvainPEREZ@q-leap.eu/s/HTmIB9vz2UyuVzQ4Gft70Q2')

FLECHE = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
          'stroke-width="2" aria-hidden="true"><path d="M5 12h14M12 5l7 7-7 7"/></svg>')

def ico(*formes):
    return ('<div class="guarantee-item__icon"><svg width="30" height="30" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
            'stroke-linejoin="round" aria-hidden="true">' + ''.join(formes) + '</svg></div>')

ECRAN   = ico('<rect x="2" y="3" width="20" height="14" rx="2"/>',
              '<line x1="8" y1="21" x2="16" y2="21"/>', '<line x1="12" y1="17" x2="12" y2="21"/>')
CADENAS = ico('<rect x="3" y="11" width="18" height="11" rx="2"/>',
              '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>')
CARNET  = ico('<path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v18H6.5A2.5 2.5 0 0 0 4 22z"/>')

NB = '<span class="nb">Q-Bot</span>'

FR = dict(
    sortie='reservation.html', donneur='contact.html', autre='en/booking.html',
    url='https://q-bot.eu/reservation.html', url_autre='https://q-bot.eu/en/booking.html',
    titre='Réserver une démo de Q-Bot | Q-Leap',
    social='Réserver une démo de Q-Bot',
    desc=("Réservez une démonstration de Q-Bot avec Sylvain Perez, son créateur. Une heure, "
          "un créneau dans son agenda, et le tarif communiqué à cette occasion."),
    fil='Réservation',
    label='Réservation',
    h1=f'Réserver une démonstration de {NB}',
    chapeau=(f"Vous choisissez un créneau dans l'agenda de Sylvain Perez, créateur de {NB} et CEO "
             f"de Q-Leap. Comptez une heure, pendant laquelle le boîtier pilote une vraie "
             f"application 2FA sous vos yeux, sur un téléphone Android. Vous posez vos questions, "
             f"et c'est à cette occasion que le tarif vous est communiqué."),
    s1_label='Le rendez-vous', s1_titre='Choisir un créneau',
    s1_chapeau=("L'agenda est celui de Sylvain Perez, et il montre ses disponibilités réelles, "
                "dans votre propre fuseau horaire. Vous réservez vous-même, sans passer par nous, "
                "et vous recevez une confirmation par courriel."),
    faits=[('Avec', 'Sylvain Perez, créateur de Q-Bot et CEO de Q-Leap'),
           ('Durée', 'Une heure')],
    cadre_titre='Agenda de réservation Q-Bot',
    cadre_accroche='Les disponibilités de Sylvain Perez, en direct',
    cadre_note=("L’agenda est fourni par Microsoft Bookings, qui dépose ses propres cookies. "
                "Il vous demandera votre nom, votre adresse électronique et votre téléphone."),
    cadre_bouton='Afficher l’agenda',
    cadre_lien_court='Ouvrir l’agenda',
    cadre_attente='Chargement de l’agenda',
    cadre_lent='L’agenda tarde à répondre. Le lien ci-dessous l’ouvre dans un nouvel onglet.',
    cadre_pied='Ou',
    cadre_lien='ouvrir la page de réservation dans un nouvel onglet',
    s2_label='Le contenu', s2_titre=f'Ce que la démonstration montre',
    montre=[(ECRAN, 'Le boîtier en fonctionnement',
             f'{NB} pilote la vraie application 2FA sur un téléphone Android relié en USB, '
             'déclenché par un simple appel HTTP depuis une chaîne de tests.'),
            (CADENAS, 'Vos propres applications',
             'LuxTrust Mobile, itsme, Microsoft ou Google Authenticator, ou toute autre '
             'application 2FA Android.'),
            (CARNET, 'La construction d’un scénario',
             'Une capture de l’écran 2FA, des points d’appui numérotés, des temps '
             'd’attente. Aucun script à écrire.')],
    s3_label='Autrement', s3_titre='Si aucun créneau ne convient',
    s3_texte=('Appelez-nous au <a href="tel:+352202117">+352 20 21 17</a>, ou décrivez votre '
              'besoin dans le <a href="contact.html">formulaire de contact</a>&nbsp;: nous vous '
              'proposons un autre moment.'),
)

EN = dict(
    sortie='en/booking.html', donneur='en/contact.html', autre='reservation.html',
    url='https://q-bot.eu/en/booking.html', url_autre='https://q-bot.eu/reservation.html',
    titre='Book a Q-Bot demo | Q-Leap',
    social='Book a Q-Bot demo',
    desc=("Book a Q-Bot demonstration with Sylvain Perez, its creator. One hour, a slot in his "
          "calendar, and the price given on the day."),
    fil='Booking',
    label='Booking',
    h1=f'Book a {NB} demonstration',
    chapeau=(f"You pick a slot in the calendar of Sylvain Perez, creator of {NB} and CEO of "
             f"Q-Leap. Allow one hour, during which the device drives a genuine 2FA app in front "
             f"of you, on a real Android phone. You ask your questions, and that is when the "
             f"price is given to you."),
    s1_label='The appointment', s1_titre='Pick a slot',
    s1_chapeau=("The calendar is Sylvain Perez's own, and it shows his real availability in your "
                "own time zone. You book it yourself, without going through us, and you receive "
                "a confirmation by email."),
    faits=[('With', 'Sylvain Perez, creator of Q-Bot and CEO of Q-Leap'),
           ('Duration', 'One hour')],
    cadre_titre='Q-Bot booking calendar',
    cadre_accroche='Sylvain Perez’s live availability',
    cadre_note=("The calendar is provided by Microsoft Bookings, which sets its own cookies. "
                "It will ask for your name, email address and phone number."),
    cadre_bouton='Show the calendar',
    cadre_lien_court='Open the calendar',
    cadre_attente='Loading the calendar',
    cadre_lent='The calendar is slow to respond. The link below opens it in a new tab.',
    cadre_pied='Or',
    cadre_lien='open the booking page in a new tab',
    s2_label='The content', s2_titre='What the demonstration shows',
    montre=[(ECRAN, 'The device at work',
             f'{NB} drives the genuine 2FA app on an Android phone connected over USB, triggered '
             'by a single HTTP call from a test pipeline.'),
            (CADENAS, 'Your own apps',
             'LuxTrust Mobile, itsme, Microsoft or Google Authenticator, or any other Android '
             '2FA app.'),
            (CARNET, 'Building a scenario',
             'A screenshot of the 2FA screen, numbered tap points, wait times. No script to '
             'write.')],
    s3_label='Otherwise', s3_titre='If no slot suits you',
    s3_texte=('Call us on <a href="tel:+352202117">+352 20 21 17</a>, or describe what you need '
              'in the <a href="contact.html">contact form</a>: we will offer another time.'),
)

def corps(L):
    faits = '\n'.join(
        f'            <li class="spec-item" role="listitem">'
        f'<span class="spec-item__label">{a}</span>'
        f'<span class="spec-item__value">{b}</span></li>' for a, b in L['faits'])
    montre = '\n'.join(
        f'        <div class="guarantee-item">\n          {i}\n'
        f'          <h3>{t}</h3>\n          <p>{p}</p>\n        </div>' for i, t, p in L['montre'])
    return f"""
<section class="page-hero" aria-labelledby="page-title">
  <div class="container">
    <span class="section-label">{L['label']}</span>
    <h1 id="page-title">{L['h1']}</h1>
    <p>{L['chapeau']}</p>
  </div>
</section>

<!-- ======= CHOIX DU CRÉNEAU =======
     L'agenda occupe toute la largeur du conteneur : Bookings est une interface
     complète (service, personnel, calendrier, créneaux) et une demi-colonne la
     rendrait illisible. -->
<section class="section" aria-labelledby="creneau-title">
  <div class="container">
    <span class="section-label">{L['s1_label']}</span>
    <h2 class="section-title" id="creneau-title">{L['s1_titre']}</h2>
    <p class="section-subtitle">{L['s1_chapeau']}</p>
    <ul class="specs__list booking-facts" role="list">
{faits}
    </ul>

    <div class="booking-frame"
         data-booking-src="{BOOKINGS}"
         data-booking-title="{L['cadre_titre']}"
         data-booking-attente="{L['cadre_attente']}"
         data-booking-lent="{L['cadre_lent']}">
      <div class="booking-frame__ask">
        <svg class="booking-frame__ask-pin" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3" y="4" width="18" height="17" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="8" y1="2" x2="8" y2="5"/><line x1="16" y1="2" x2="16" y2="5"/></svg>
        <p class="booking-frame__ask-titre">{L['cadre_accroche']}</p>
        <p class="booking-frame__ask-note">{L['cadre_note']}</p>
        <button type="button" class="booking-frame__ask-btn" data-booking-load>{L['cadre_bouton']}</button>
        <a class="booking-frame__ask-link" href="{BOOKINGS}" target="_blank" rel="noopener">{L['cadre_lien_court']} {FLECHE}</a>
      </div>
      <p class="booking-frame__foot">
        <span>{L['cadre_pied']}</span>
        <a href="{BOOKINGS}" target="_blank" rel="noopener">{L['cadre_lien']} {FLECHE}</a>
      </p>
    </div>
  </div>
</section>

<!-- ======= CE QUE LA DÉMONSTRATION MONTRE ======= -->
<section class="section section--gray" aria-labelledby="montre-title">
  <div class="container">
    <div class="section-header">
      <span class="section-label">{L['s2_label']}</span>
      <h2 class="section-title" id="montre-title">{L['s2_titre']}</h2>
    </div>
    <div class="guarantee-grid">
{montre}
    </div>
  </div>
</section>

<!-- ======= AUTRE VOIE ======= -->
<section class="section" aria-labelledby="autrement-title">
  <div class="container">
    <span class="section-label">{L['s3_label']}</span>
    <h2 class="section-title" id="autrement-title">{L['s3_titre']}</h2>
    <p style="max-width:640px;">{L['s3_texte']}</p>
  </div>
</section>
"""

def genere(L):
    d = io.open(os.path.join(RACINE, L['donneur']), encoding='utf-8').read()
    for marque in ('</head>', '<main id="main">', '</main>'):
        if marque not in d:
            sys.exit('ECHEC : « %s » absent de %s' % (marque, L['donneur']))
    tete = d[:d.index('</head>')]
    entre = d[d.index('</head>'):d.index('<main id="main">') + len('<main id="main">')]
    queue = d[d.index('</main>'):]

    # ── métadonnées ──
    t_av = re.search(r'<title>([^<]*)</title>', tete).group(1)
    d_av = re.search(r'<meta name="description" content="([^"]*)"', tete).group(1)
    s_av = re.search(r'<meta property="og:title" content="([^"]*)"', tete).group(1)
    if len(L['titre']) > 62:   sys.exit('ECHEC : titre à %d caractères' % len(L['titre']))
    if len(L['desc']) > 158:   sys.exit('ECHEC : description à %d caractères' % len(L['desc']))
    tete = tete.replace(f'<title>{t_av}</title>', f"<title>{L['titre']}</title>")
    tete = tete.replace(d_av, L['desc'])
    tete = tete.replace(s_av, L['social'])
    # adresses : canonique, hreflang et og:url, par attribut et non par bloc ordonné
    lang = 'fr' if L['sortie'] == 'reservation.html' else 'en'
    autre_lang = 'en' if lang == 'fr' else 'fr'
    tete = re.sub(r'(<link rel="canonical" href=")[^"]*"', r'\g<1>%s"' % L['url'], tete)
    tete = re.sub(r'(<link rel="alternate" hreflang="%s" href=")[^"]*"' % lang,
                  r'\g<1>%s"' % L['url'], tete)
    tete = re.sub(r'(<link rel="alternate" hreflang="%s" href=")[^"]*"' % autre_lang,
                  r'\g<1>%s"' % L['url_autre'], tete)
    fr_url = L['url'] if lang == 'fr' else L['url_autre']
    tete = re.sub(r'(<link rel="alternate" hreflang="x-default" href=")[^"]*"',
                  r'\g<1>%s"' % fr_url, tete)
    tete = re.sub(r'(<meta property="og:url" content=")[^"]*"', r'\g<1>%s"' % L['url'], tete)
    # fil d'Ariane : deuxième maillon
    tete = re.sub(r'("position": 2,\s*\n\s*"name": ")[^"]*(",\s*\n\s*"item": ")[^"]*"',
                  lambda m: m.group(1) + L['fil'] + m.group(2) + L['url'] + '"', tete)

    # ── sélecteur de langue ──
    cible = '../reservation.html' if lang == 'en' else 'en/booking.html'
    entre, n = re.subn(r'(<a href=")(?:en/)?(?:\.\./)?contact\.html("\s+hreflang=)', r'\g<1>%s\g<2>' % cible, entre)
    if n != 1:
        sys.exit('ECHEC %s : sélecteur de langue non repris (%d)' % (L['sortie'], n))

    # ── pied de page : l'entrée devient le marqueur de page courante ──
    lien = f'<li><a href="{os.path.basename(L["sortie"])}">{L["label"]}</a></li>'
    span = f'<li><span aria-current="page">{L["label"]}</span></li>'
    if lien not in queue:
        sys.exit('ECHEC %s : entrée de pied de page introuvable (%s)' % (L['sortie'], lien))
    queue = queue.replace(lien, span)

    out = tete + entre + corps(L) + queue
    if lang == 'en':
        marque = ('<!-- BOOKINGS-EN-A-VENIR : ce lien mène au Bookings FRANÇAIS, faute de page\n'
                  '     anglaise. Relevé le 2026-08-31 : la page Microsoft ne se traduit pas,\n'
                  '     testée en en-GB et en nl-BE. Une seule URL à remplacer le jour venu. -->\n          ')
        out = out.replace('<a href="%s"' % BOOKINGS, marque + '<a href="%s"' % BOOKINGS, 1)

    # ── garde-fous ──
    for quoi, motif in (('feuille de style', r'<link[^>]+style\.css'),
                        ('balise main', r'<main\b'), ('pied de page', r'<footer'),
                        ('noindex', r'name="robots" content="noindex')):
        if not re.search(motif, out):
            sys.exit('ECHEC %s : invariant perdu (%s)' % (L['sortie'], quoi))
    if out.count('<h1') != 1:
        sys.exit('ECHEC %s : %d h1' % (L['sortie'], out.count('<h1')))
    if out.count(BOOKINGS) != 3:
        sys.exit('ECHEC %s : %d mention(s) de l\'URL Bookings, 3 attendues (source du '
                 'cadre + action de repli + lien de pied)' % (L['sortie'], out.count(BOOKINGS)))
    if '—' in re.sub(r'<!--[\s\S]*?-->', '', out):
        sys.exit('ECHEC %s : cadratin dans le contenu' % L['sortie'])

    chemin = os.path.join(RACINE, L['sortie'])
    io.open(chemin, 'w', encoding='utf-8').write(out)
    mots = len(re.sub(r'<[^>]+>', ' ', corps(L)).split())
    print('OK %-22s %6d octets, %3d mots de contenu' % (L['sortie'], len(out), mots))

for L in (FR, EN):
    genere(L)
print('\nRAPPEL : seule page du site portant le lien Microsoft Bookings.')
