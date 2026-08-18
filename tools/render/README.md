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

## `hue-to-brand.py` — ramener un visuel fourni sur la teinte de la charte

Les visuels livrés par le client arrivent **bleus** (mesuré : teinte médiane 226° et
190° en HSV, quand la charte n'admet que le teal `#00CBBE`, soit 174°). Ce script
tourne la teinte sans toucher à la clarté perçue ni au grain de l'image.

```
python3 tools/render/hue-to-brand.py <master.png> <sortie.jpg> [largeur]
```

Quatre pièges, tous rencontrés et tous mesurés :

- **Ne pas utiliser `hue-rotate` (CSS/SVG) ni une rotation HSV.** Le premier est une
  approximation linéaire en YIQ : il décale la luminance et ternit les couleurs vives.
  Le second conserve V, qui n'est pas la clarté perçue — l'image s'éclaircit
  visiblement en passant du bleu au cyan. La rotation se fait donc **en Oklch**, où L
  et C sont conservés à l'identique.
- **L'ancre est l'accent lumineux, pas la teinte médiane.** Calée sur la médiane, la
  rotation était juste au sens de la mesure et fausse à l'œil : sur le rendu Q-Bot, la
  médiane est tirée à 208° par le fond sombre alors que les anneaux étaient déjà à
  193°, à 6° de la charte. Les aligner par la médiane les envoyait à 165°, du vert.
  L'ancre est le décile le plus clair des pixels colorés, pondéré par le chroma.
- **Resserrer l'étendue, pas seulement translater.** Une translation conserve les 30°
  d'écart entre le fond et les accents, ce qui envoie forcément l'un des deux hors du
  teal. Les écarts à l'ancre sont multipliés par 0,6 : l'étendue tombe à une dizaine de
  degrés, comme sur les visuels déjà en place.
- **Le test de gamme doit porter sur le linéaire NON écrêté.** `lin_to_srgb` écrête les
  négatifs (obligatoire : puissance fractionnaire d'un négatif = NaN), donc un test
  fait après conversion ne voit jamais un canal négatif. Premier jet : 0,01 % de pixels
  détectés hors gamme, alors qu'il y en avait 79 % — les aplats vifs passaient par
  l'écrêtage muet du canal rouge et perdaient les deux tiers de leur chroma (0,180 →
  0,069 sur la pastille du visuel produits). Corrigé, la remise en gamme se fait par
  réduction de chroma à L et h constants (méthode de CSS Color 4). Contrôle qui compte :
  après coup, 100 % des pixels sont dans la gamme et **41 % en sortiraient si on
  augmentait le chroma de 3 %** — le résultat est donc collé au bord, c'est le teal le
  plus vif que sRGB autorise à ces clartés.

**Limite physique à connaître.** Un bleu sombre et très saturé n'a pas d'équivalent teal
aussi chromatique : la gamme sRGB est nettement plus étroite du côté cyan à clarté
basse. Un aplat `#4a53cc` (L 0,53 / C 0,18) devient au mieux `#037b79` (C 0,093). Le
teal de charte, lui, est **clair** (L 0,76). Pour qu'un aplat lise comme `#00CBBE` il
faudrait donc aussi le rééclairer, ce qui n'est plus une correction de teinte mais une
réexposition du rendu : à demander au client, pas à décider ici.
