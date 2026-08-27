# -*- coding: utf-8 -*-
"""Les vignettes des guides, et leur description d'image, en un seul endroit.

POURQUOI UN MODULE À PART. Deux scripts s'en servent : `gen-index-guides.py`
pour la carte de l'index de blog, et `gen-guides.py` pour la figure posée dans
le corps du guide. La MÊME image y apparaît deux fois, et si les deux scripts
portaient chacun leur texte alternatif, la première correction de l'un ferait
diverger l'autre en silence. Même raison que `redirections_map.py`, et un nom
de fichier à tiret ne serait pas importable.

CE QUE CETTE TABLE NE CONTIENT PAS : la légende de la figure. Une légende n'est
pas une description d'image — elle s'adresse à qui VOIT le schéma, elle dit ce
qu'il faut en retenir, et un assistant la lit comme du texte. Elle vit donc avec
la section qu'elle illustre, dans `gen-guides.py`.

SIX SCHÉMAS ET DEUX PHOTOS. Le partage n'est pas arbitraire : un schéma là où le
sujet est conceptuel, une photo là où le sujet est l'objet. Les schémas sont
construits dans la charte par `tools/render/guide-thumbs.html`, donc sans aucune
image tierce et sans licence à surveiller.
"""

# clé = base du fichier. Un schéma existe en deux langues (`-fr` / `-en` ajouté
# par `fichier()`), une photo est le même fichier dans les deux.
VIGNETTES = {
    'guides/familles-2fa': dict(
        bilingue=True,
        fr="Les quatre familles de second facteur : code calculé, demande à approuver, code affiché, QR code",
        en="The four families of second factor: computed code, request to approve, displayed code, QR code"),
    'guides/trois-voies': dict(
        bilingue=True,
        fr="Les trois voies possibles : désactiver, recalculer le code, ou piloter un appareil réel",
        en="The three possible routes: disable, recompute the code, or drive a real device"),
    'guides/avec-sans-cle': dict(
        bilingue=True,
        fr="Deux chemins : avec un secret partagé on calcule, sans secret on appuie sur l'appareil",
        en="Two paths: with a shared secret you compute, without one you tap the device"),
    'guides/rien-ne-sort': dict(
        bilingue=True,
        fr="Scénarios, captures et base locale restent dans votre réseau : aucun envoi vers l'extérieur",
        en="Scenarios, screenshots and local store stay on your network: nothing is uploaded"),
    'guides/campagne-bute': dict(
        bilingue=True,
        fr="Une campagne de tests qui franchit les premières étapes puis s'arrête net à la 2FA",
        en="A test run clearing the first steps then stopping dead at the 2FA step"),
    'guides/le-calcul': dict(
        bilingue=True,
        fr="Le calcul du coût : testeurs multipliés par minutes puis par jours ouvrés, en heures puis en journées",
        en="The cost calculation: testers times minutes times working days, in hours then in days"),
    'qbot-photo-dock': dict(
        bilingue=False, ext='jpg',
        fr="Un smartphone dans le socle du Q-Bot, affichant une demande de validation LuxTrust",
        en="A smartphone in the Q-Bot cradle, showing a LuxTrust approval request"),
    'qbot-photo-poste': dict(
        bilingue=False, ext='jpg',
        fr="Le boîtier Q-Bot et son téléphone posés sur un poste de travail, à côté d'un écran",
        en="The Q-Bot enclosure and its phone on a desk, beside a monitor"),
}

# Les schémas sont carrés et sortis en 900 px par `shoot-guide-thumbs.py` ; les
# deux photos ont leurs propres dimensions, déclarées ici pour que le navigateur
# réserve la place avant le chargement différé.
DIMENSIONS = {True: (900, 900), False: (768, 768)}


def fichier(base, lang):
    """Le chemin de l'image, sous `assets/img/`."""
    v = VIGNETTES[base]
    return f'{base}-{lang}.webp' if v['bilingue'] else f"{base}.{v.get('ext', 'webp')}"


def alt(base, lang):
    return VIGNETTES[base][lang]


def dimensions(base):
    return DIMENSIONS[VIGNETTES[base]['bilingue']]
