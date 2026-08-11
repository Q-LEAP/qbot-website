# Chaîne de rendu des visuels produit

Ces scripts régénèrent les visuels 3D « design » du site à partir du modèle
authentique `assets/models/qbot.glb`. Rien ici n'est exécuté par le site : ce
sont des outils hors-ligne, lancés à la main quand un visuel doit être refait.

Rendu par **model-viewer piloté en headless** (Playwright + Chrome) : c'est le
même moteur que la page « Modèle 3D », donc les visuels et le viewer interactif
montrent exactement le même objet. Il n'y a pas de moteur de rendu hors-ligne
sur cette machine.

## Ordre

```bash
python3 mktex.py            # grain : normal map + variation de rugosité (tuilables)
python3 mkscreen.py         # écran du smartphone : validation 2FA, iconographique
python3 mkenv.py            # environnement équirectangulaire (key + rim teal)
cp env-v5.png  ../../_env.png            # servi à la racine pour le rendu
UV_SCALE=42 NORM_SCALE=0.55 python3 patchglb.py   # → ../../_qbot-render.glb
# servir le dépôt (python3 -m http.server 8123) avec _render.html à la racine,
# puis :
python3 shoot3.py shots.json             # → r/*.png détourés (alpha)
# enfin la composition (voir compose.py : backdrop / glow / reflection / grade)
```

Les fichiers `_env.png`, `_render.html` et `_qbot-render.glb` sont des
intermédiaires : ils vivent à la racine le temps du rendu et ne sont pas
versionnés.

## Points à ne pas redécouvrir

- **`animation-name="Explode"` est obligatoire** sur la balise `<model-viewer>`,
  sinon `currentTime` ne fait rien : aucun clip n'est sélectionné, le téléphone
  ne vient pas se poser (il est à l'échelle 0, donc invisible) et rien n'explose.
  `time: 1.999` = téléphone en place, `time: 0` = boîtier seul.
- **`patchglb.py` patche le GLB, il ne le ré-exporte pas.** Le clip « Explode »
  doit survivre — c'est lui qui place le téléphone. Un ré-export via trimesh le
  perdrait. L'animation pilote des transforms de *nœuds*, pas des sommets : on
  peut donc reconstruire librement la géométrie des primitives.
- **Le maillage n'a aucune UV.** Une projection planaire par pièce étire la
  texture sur les faces obliques et la transforme en stries bien visibles ;
  d'où la projection **triplanaire par face**, qui impose de dégrouper les
  sommets (×3). Sans importance : ce GLB ne sert qu'au rendu, il n'est pas livré.
- **L'écran du smartphone n'était pas texturable** : ses UV d'origine sont
  dégénérées (4 texels de palette, un par face). `patchglb.py` isole les faces
  de la dalle dans une primitive dédiée avec de vraies UV planaires et un
  matériau émissif.
- **Orientation de l'environnement** : `u = 0.75 − θ/360`, où θ est l'azimut de
  `camera-orbit`. Mesuré avec une sonde à quatre couleurs, pas deviné. Le rim
  en contre-jour se place donc à `u_caméra + 0.5`.
- Un environnement trop sombre donne un modèle noir : viser une luminance
  moyenne d'environ 70 et poser les sources **après** le flou de fond, sinon le
  flou écrase la key light.
- Les halos se calculent sur un calque **de la taille de la toile**, jamais de
  l'image produit : sinon le flou est coupé net à son bord et laisse un halo
  carré, très visible sur fond sombre.
