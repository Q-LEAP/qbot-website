"""Ramène la teinte d'un visuel sur celle de la charte (#00CBBE), sans toucher ni à
la clarté ni à la saturation.

Pourquoi Oklch et non une rotation HSV ou le `hue-rotate` de CSS :
- `hue-rotate` (CSS/SVG) est une approximation linéaire en YIQ. Elle décale la
  luminance et désature les couleurs vives : sur un rendu sombre à halos, les traits
  lumineux se ternissent.
- Une rotation HSV garde S et V, mais V n'est pas la clarté perçue : du bleu et du
  cyan de même V ne se ressemblent pas en clarté, si bien que l'image s'éclaircit
  visiblement en passant de 226° à 174°.
En Oklch, L (clarté perçue) et C (chroma) sont conservés à l'identique et seul h
tourne : c'est exactement « la même image, une autre teinte ».

L'ANCRE EST LA LUMIÈRE, PAS LA MÉDIANE. Premier essai : rotation calée sur la teinte
médiane de tous les pixels colorés. Résultat mesuré juste (médiane sur la charte) et
visuellement faux — les anneaux lumineux du rendu Q-Bot étaient partis dans le vert.
La raison est dans les chiffres : sur ce visuel, la médiane est tirée à 208° par le
fond sombre alors que les anneaux, eux, étaient déjà à 193°, à 6° de la charte. Tourner
de −29° pour aligner la médiane les emmenait à 165°, soit du vert. Or c'est l'accent
lumineux que l'œil lit comme « la couleur de l'image », pas le fond.
L'ancre est donc la teinte des pixels les plus CLAIRS parmi les colorés (décile
supérieur de clarté, pondéré par le chroma) — la même grandeur que celle mesurée sur
les visuels déjà en place, où elle vaut 175 à 188°.

LA DISPERSION EST RESSERRÉE, PAS SEULEMENT TRANSLATÉE. Une translation conserve
l'étendue des teintes : sur le visuel bleu, 30° d'écart entre le fond et les anneaux
restaient 30° après coup, ce qui envoie forcément l'un des deux hors du teal. Les
écarts à l'ancre sont donc multipliés par 0,6, ce qui ramène l'étendue au niveau de
celle des visuels du site (une dizaine de degrés) sans aplatir l'image en une seule
teinte. C'est la seule opération de ce script qui ne soit pas une isométrie, et elle
est assumée : ces deux visuels sont monochromes teal-sur-noir, la variété de teinte
n'y porte aucune information.

Hors gamme : une rotation à L et C constants peut sortir du sRGB. Les pixels
concernés voient leur chroma réduit par recherche dichotomique jusqu'à rentrer, ce
qui préserve la teinte obtenue et la clarté — un simple écrêtage, lui, aurait
retourné une teinte fausse là où ça déborde.
"""
import sys, os
import numpy as np
from PIL import Image

# Accelerate (le BLAS d'Apple, celui que numpy utilise ici) laisse traîner des
# drapeaux de virgule flottante sur les voies de remplissage de ses boucles
# vectorisées : chaque `@` remonte alors « divide by zero / overflow / invalid »
# alors que rien n'est faux. Vérifié : l'entrée est finie, la sortie est finie, et le
# même produit calculé par einsum — qui ne passe pas par BLAS — donne le même
# résultat à 1,1e-16. On coupe donc l'avertissement plutôt que de le laisser faire
# douter d'un calcul juste.
np.seterr(all="ignore")

M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
               [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]])
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
               [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717662, -0.8086757660]])
M2i = np.linalg.inv(M2)
M1i = np.linalg.inv(M1)

def srgb_to_lin(c):
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)

def lin_to_srgb(c):
    # Le clip est INDISPENSABLE ici (puissance fractionnaire d'un négatif = NaN) mais
    # il ne doit jamais servir de test de gamme : c'est lui qui, en ramenant un canal
    # négatif à zéro, désature silencieusement une couleur hors gamme. Tout contrôle
    # de gamme se fait donc sur le linéaire NON écrêté, cf. `to_linear`.
    c = np.clip(c, 0, None)
    return np.where(c > 0.0031308, 1.055 * c ** (1 / 2.4) - 0.055, 12.92 * c)

def to_oklab(rgb):                      # rgb sRGB dans [0,1], (...,3)
    lms = srgb_to_lin(rgb) @ M1.T
    return np.cbrt(lms) @ M2.T

def to_linear(lab):
    """Linéaire sRGB NON écrêté — la seule forme sur laquelle un test de gamme a du sens."""
    return (lab @ M2i.T) ** 3 @ M1i.T


def from_oklab(lab):
    return lin_to_srgb(to_linear(lab))

def oklch(rgb):
    lab = to_oklab(rgb)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    return L, np.hypot(a, b), np.degrees(np.arctan2(b, a)) % 360

def _lab(L, C, h):
    hr = np.radians(h)
    return np.stack([L, C * np.cos(hr), C * np.sin(hr)], -1)


def from_oklch(L, C, h):
    return from_oklab(_lab(L, C, h))


def in_gamut(L, C, h, eps=1e-4):
    lin = to_linear(_lab(L, C, h))
    return (lin.min(-1) >= -eps) & (lin.max(-1) <= 1 + eps)

BRAND = np.array([0x00, 0xCB, 0xBE]) / 255.0

def anchor_hue(L, C, h, l_pct=90, c_min=0.03):
    """Teinte de l'accent lumineux : médiane circulaire pondérée par le chroma sur le
       décile le plus clair des pixels colorés."""
    m = C > c_min
    if m.sum() < 100:
        return None
    ll, cc, hh = L[m], C[m], h[m]
    keep = ll >= np.percentile(ll, l_pct)
    hh, cc = hh[keep], cc[keep]
    ang = np.radians(hh)
    ref = np.degrees(np.arctan2((np.sin(ang) * cc).sum(), (np.cos(ang) * cc).sum())) % 360
    dev = (hh - ref + 180) % 360 - 180
    o = np.argsort(dev)
    cw = np.cumsum(cc[o]) / cc.sum()
    return (ref + dev[o][np.searchsorted(cw, 0.5)]) % 360


def rotate(path, out, width=None, quality=90, target=None, spread=0.6, report=True):
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im).astype(np.float64) / 255.0
    L, C, h = oklch(rgb)
    _, bC, bh = oklch(BRAND[None, None, :])
    goal = float(target if target is not None else bh[0, 0])
    ref = anchor_hue(L, C, h)
    dev = (h - ref + 180) % 360 - 180          # écart signé à l'ancre
    h2 = (goal + spread * dev) % 360
    # Remise en gamme par réduction de chroma à clarté et teinte constantes — la
    # méthode de CSS Color 4. Elle doit être PILOTÉE : premier jet, le test de gamme
    # portait sur le sRGB déjà écrêté, donc ne voyait jamais un canal négatif. Les
    # aplats vifs passaient alors par l'écrêtage muet du canal rouge et perdaient les
    # deux tiers de leur chroma — mesuré sur la pastille du visuel produits, C
    # 0,180 → 0,069, un teal éteint là où la gamme sRGB en autorisait bien plus. Le
    # bleu très saturé et sombre n'a pas d'équivalent teal aussi chromatique (la
    # gamme est nettement plus étroite du côté cyan), il y a donc forcément une
    # perte : autant qu'elle soit la plus petite possible et non le fruit d'un clip.
    ok = in_gamut(L, C, h2)
    n_bad = int((~ok).sum())
    if n_bad:
        lo = np.zeros(C.shape); hi = np.ones(C.shape)
        for _ in range(16):
            mid = (lo + hi) / 2
            good = in_gamut(L, C * mid, h2)
            lo = np.where(good, mid, lo); hi = np.where(good, hi, mid)
        C = C * np.where(ok, 1.0, lo)
    out_rgb = from_oklch(L, C, h2)
    out_rgb = np.clip(out_rgb, 0, 1)
    res = Image.fromarray((out_rgb * 255 + 0.5).astype(np.uint8))
    if width and width != res.width:
        res = res.resize((width, round(res.height * width / res.width)), Image.LANCZOS)
    for q in (quality, quality - 2, quality - 4, quality - 6, quality - 8):
        res.save(out, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0)
        if os.path.getsize(out) <= 190 * 1024:
            break
    if report:
        a2 = np.asarray(Image.open(out).convert("RGB")).astype(np.float64) / 255.0
        L2, C2, h3 = oklch(a2)
        m2 = C2 > 0.03
        w = (C2 * L2)[m2]; hs = h3[m2]
        o = np.argsort(hs); cw = np.cumsum(w[o]) / w.sum()
        p = lambda x: hs[o][np.searchsorted(cw, x)]
        print(f"  {os.path.basename(out):24s} accent {ref:6.1f}° → {anchor_hue(L2, C2, h3):6.1f}°"
              f" (cible {goal:.1f}°)  étendue p10-p90 {p(.1):.0f}→{p(.9):.0f}°"
              f" | remis en gamme {100*n_bad/ok.size:.2f} % | {res.width}×{res.height} q{q}"
              f" {os.path.getsize(out)//1024} Ko")
    return ref

if __name__ == "__main__":
    rotate(sys.argv[1], sys.argv[2], width=int(sys.argv[3]) if len(sys.argv) > 3 else None)
