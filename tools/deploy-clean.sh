#!/bin/sh
# Nettoyage avant mise en ligne.
#
# Le dépôt vit sur un volume exFAT : macOS y sème des fichiers « AppleDouble »
# (._quelquechose) et des .DS_Store à chaque accès. Ils sont ignorés par git —
# donc absents du dépôt — mais un déploiement qui COPIE le dossier (rsync, FTP,
# glisser-déposer) les publierait : au dernier comptage, 1392 fichiers parasites.
#
# À lancer juste avant de copier, ou à remplacer par les exclusions de votre
# outil :   rsync -av --exclude='._*' --exclude='.DS_Store' --exclude='.git' ...
set -eu
cd "$(dirname "$0")/.."
n=$(find . -name '._*' -not -path './.git/*' | wc -l | tr -d ' ')
m=$(find . -name '.DS_Store' -not -path './.git/*' | wc -l | tr -d ' ')
find . -name '._*'      -not -path './.git/*' -delete
find . -name '.DS_Store' -not -path './.git/*' -delete
echo "supprimés : $n fichiers AppleDouble, $m .DS_Store"
echo
echo "RAPPEL avant publication :"
echo "  1. retirer le noindex — chercher « PRÉ-LANCEMENT » (robots.txt + les 23 pages)"
echo "  2. renseigner data-endpoint sur les 6 formulaires (contact FR/EN,"
echo "     newsletter des 2 homepages et des 2 index de blog)"
