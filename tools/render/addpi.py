# -*- coding: utf-8 -*-
"""Ajoute le nano-ordinateur (Raspberry Pi 5) au modèle 3D du boîtier.

    python3 tools/render/addpi.py

Lit  : Documentations/assets-sources/qbot-untextured.glb      (le boîtier nu, intact)
       Documentations/assets-sources/raspberrypi5-source.glb  (le modèle fourni, intact)
Écrit: Documentations/assets-sources/qbot-untextured-pi.glb   (la nouvelle source de la chaîne)

C'est le PREMIER pas de la chaîne du modèle livré, avant `patchglb-site.py` :

    python3 tools/render/addpi.py
    python3 tools/render/patchglb-site.py       # matière : grain, verre, écran 2FA
    npx @gltf-transform/cli@4 draco assets/models/qbot.glb assets/models/qbot.glb
    python3 tools/render/mkdata.py             # sidecar base64 pour le mode file://
    node tools/bump-assets.mjs                 # empreintes d'actifs

Les deux fichiers d'entrée ne sont JAMAIS réécrits : relancer le script sur sa
propre sortie la patcherait une seconde fois (UV par-dessus UV, carte déjà
décimée re-décimée), exactement le piège déjà documenté pour `patchglb-site.py`.

## Ce que fait le script, et pourquoi

**1. Il bake la transformation du modèle fourni.** Ses 752 nœuds la portent sous
forme de `matrix` (le boîtier, lui, emploie TRS : les deux formes sont traitées),
sur deux niveaux : une échelle 0,001 sous une rotation de 180° autour de X. Le
modèle est donc dessiné en millimètres et à l'envers. Une fois bakée par un
parcours du graphe, la carte tient dans 87,7 x 20,0 x 57,7 mm, ce qui est
la cote exacte d'une Pi 5 (85 x 56 mm de circuit, 20 mm avec les connecteurs) et
confirme que l'échelle est bien celle du boîtier : les deux fichiers sont en
mètres. Aucune mise à l'échelle n'est appliquée, et il ne faut pas en ajouter.

**2. Il décime.** Le modèle fourni pèse 11,6 Mo pour 104 232 triangles et
312 696 sommets, soit AUCUN partage de sommet, trois sommets par face. C'est
inacceptable pour un fichier téléchargé par le visiteur de l'accueil (le boîtier
entier tient en 585 Ko compressé). Deux temps :
  - **soudure des sommets coïncidents** : 312 696 -> 52 378 sommets, sans bouger
    un sommet ni perdre une face. C'est la soudure qui rend la décimation
    possible : sur un maillage entièrement dégroupé, le simplificateur ne peut
    effondrer aucune arête, et une décimation « à 15 % » ne retire que 0,3 % des
    faces (mesuré) ;
  - **décimation** (meshoptimizer, via `gltf-transform simplify`), et seulement
    sur les groupes de plus de 3 000 faces. Les petites pièces (LED, connecteurs
    FPC, cavalier PoE) sont déjà légères et une décimation les efface.
La note de CLAUDE.md sur la décimation vaut pour la COQUE, dont le facettage
était visible et que le client a demandé de garder à pleine résolution. Ici
l'objet est une carte de 88 mm dans un boîtier de 213 mm, vue à travers une
coque en verre pendant un pas de la séquence : ce n'est pas le même sujet.

**3. Il reconstruit les normales par arêtes vives** (crease). La soudure a
fusionné les normales par sommet ; des normales lissées feraient fondre une carte
électronique, qui n'est que des arêtes à 90°. Des normales plates (un sommet par
face) seraient justes mais tripleraient à nouveau les sommets. Un sommet est donc
dédoublé une fois par groupe de faces à moins de CREASE degrés l'une de l'autre.

**4. Il pose la carte sur le plancher du plateau, et l'oriente.** Rien n'est
estimé à l'œil :
  - le plateau (`mesh 0`) est un bac dont l'arrière (z de -100 à -20 mm) est un
    massif haut de 42 à 74 mm ; l'avant (z de -15 à +100 mm) est une plaque
    plane dont le dessus culmine à 4,25 mm. C'est ce plancher-là, « le socle en
    bas », qui reçoit la carte ; la cote 4,25 est le maximum relevé sous
    l'empreinte, donc la carte ne traverse aucune nervure ;
  - **rotation de +90° autour de Y**, si bien que le grand côté de la carte
    (87,7 mm) suit la profondeur du boîtier (206 mm de plancher libre) et non sa
    largeur (100 mm). Et le bloc Ethernet/USB, qui déborde du côté +X de la carte,
    se retrouve tourné vers -Z, c'est-à-dire vers l'ARRIÈRE du boîtier : c'est de
    là que sortent le réseau et l'alimentation, à l'opposé du poste de travail.
    Le sens était inversé jusqu'au 2026-09-03, cf. le commentaire sur place. La
    matrice est une vraie rotation (déterminant +1), pas un échange d'axes, qui
    serait une réflexion et retournerait les normales. Même précaution que pour le
    téléphone.

**5. Il ajoute la carte au clip « Explode ».** Trois keyframes aux MÊMES instants
que les quatre pièces mobiles du boîtier : 0 -> écarté à t=0,98 -> réassemblé à
t=1,0. Ce troisième keyframe n'est pas décoratif : sans lui la carte resterait
écartée pendant le segment du téléphone, cf. CLAUDE.md.

**6. Il n'ajoute AUCUNE texture.** Les 12 matériaux fournis n'en ont pas non
plus, ce sont des couleurs de base. Ils sont recopiés en les assombrissant vers
le vocabulaire du boîtier (charbon, gris métal) tout en gardant la carte
reconnaissable : un circuit imprimé vert, des blindages métalliques. Ils sont
nommés `pi-*`, et c'est ce préfixe que `patchglb-site.py` teste pour ne PAS leur
projeter d'UV ni leur poser le grain de la coque.
"""
import os, sys, collections
import numpy as np
from pygltflib import (GLTF2, Accessor, Asset, Buffer, BufferView, Material as GMat, Mesh,
                       Node, Primitive, Attributes, PbrMetallicRoughness, Scene,
                       AnimationChannel, AnimationChannelTarget, AnimationSampler)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.join(HERE, '..', '..', 'Documentations', 'assets-sources')
SRC_BOX  = os.path.join(SRC_ROOT, 'qbot-untextured.glb')
SRC_PI   = os.path.join(SRC_ROOT, 'raspberrypi5-source.glb')
OUT      = os.path.join(SRC_ROOT, 'qbot-untextured-pi.glb')

CREASE      = 32.0     # degrés : au-delà, l'arête est vive et le sommet se dédouble
DECIM_MIN   = 3000     # en dessous, un groupe est déjà léger : on n'y touche pas
DECIM_KEEP  = 0.18     # part des faces conservées dans les gros groupes
DECIM_ERROR = 0.01     # borne d'erreur, en fraction du rayon de la primitive
SEAT_Y      = 0.00425  # dessus du plancher du plateau sous l'empreinte, en mètres
FOOT_Z      = 0.0425   # centre de l'empreinte en profondeur (milieu du plancher libre)

# Déplacement atteint à t=0,98. La carte MONTE vers l'arrière-gauche, et cette
# direction n'a pas été choisie au jugé : quinze candidats ont été rendus au
# cadrage RÉEL du pas (theta -42°, phi 66°, r 0,82 m, champ 30°) et avec la coque
# EN VERRE, puisque c'est ainsi que le visiteur voit ce pas. Trois enseignements :
#   - toute direction vers le BAS sort du cadre. La carte est posée au fond du
#     bac (y = 4 mm) quand la caméra visait y = 73 mm : elle est déjà au bord bas
#     de l'image au repos, et 60 mm de descente l'en font sortir. Six candidats
#     « down » ont été rendus avant de comprendre cela ;
#   - la coque étant transparente pendant l'éclatement, la carte n'a AUCUN besoin
#     de sortir du volume du boîtier. Une recherche qui exige la sortie de la
#     boîte englobante de la coque (ce que j'avais écrit d'abord) élimine
#     mécaniquement toutes les directions vers le haut, c'est-à-dire les bonnes ;
#   - la carte est vissée sur le plancher : son axe de montage est la verticale,
#     et « elle sort par le haut » est donc aussi la convention du dessin
#     d'ensemble. Le décalage vers l'arrière-gauche la dégage du plateau, qui
#     part, lui, vers l'avant-bas-gauche.
# Elle se lit ainsi flottant au-dessus du plateau ouvert, entière dans le cadre.
EXPLODE = np.array([-0.054, 0.048, -0.022])

# Couleurs : celles du modèle fourni, ramenées dans le registre du boîtier.
# clé = nom du matériau source, valeur = (base RGB, métal, rugosité)
LOOK = {
    'board':        ([0.052, 0.115, 0.048], 0.00, 0.55),   # circuit imprimé, vert sombre
    'yellow':       ([0.115, 0.135, 0.055], 0.00, 0.60),   # sérigraphie
    'silver':       ([0.395, 0.410, 0.430], 0.85, 0.30),   # blindages, dissipateurs
    'gray':         ([0.105, 0.110, 0.120], 0.55, 0.38),
    'black':        ([0.030, 0.032, 0.035], 0.10, 0.44),   # connecteurs, puces
    'Material_0':   ([0.255, 0.265, 0.280], 0.35, 0.40),   # plastiques clairs, broches
    'creem_bright': ([0.215, 0.215, 0.185], 0.00, 0.50),   # connecteurs nappe
    'brown':        ([0.105, 0.070, 0.038], 0.00, 0.50),
    'blue':         ([0.030, 0.030, 0.180], 0.00, 0.45),   # inserts USB 3
    'golden':       ([0.230, 0.195, 0.075], 0.60, 0.35),
    'led_green':    ([0.090, 0.220, 0.045], 0.00, 0.35),
    'led_yellow':   ([0.290, 0.300, 0.055], 0.00, 0.35),
}

# ── lecture d'accesseurs ──────────────────────────────────────────────────
CT = {5120: 'i1', 5121: 'u1', 5122: 'i2', 5123: 'u2', 5125: 'u4', 5126: 'f4'}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}


def make_reader(g, blob):
    def read_acc(i):
        a = g.accessors[i]; bv = g.bufferViews[a.bufferView]
        dt = np.dtype(CT[a.componentType]).newbyteorder('<'); n = NC[a.type]
        off = (bv.byteOffset or 0) + (a.byteOffset or 0)
        stride = bv.byteStride or dt.itemsize * n
        if stride == dt.itemsize * n:
            return np.frombuffer(blob, dt, a.count * n, off).reshape(a.count, n)
        out = np.empty((a.count, n), dt)
        for k in range(a.count):
            out[k] = np.frombuffer(blob, dt, n, off + k * stride)
        return out
    return read_acc


def xform3(P, R, t=None):
    """P (N,3) transformé par la matrice 3x3 R, plus une translation.

    Écrit à la main, colonne par colonne, et NON par `R @ P.T` : sur cette
    machine, numpy 2.0 adossé à Accelerate part en faute de segmentation sur une
    cascade de petits produits (3,3)@(3,N), précédée d'avertissements
    « divide by zero encountered in matmul » sur des données pourtant toutes
    finies (vérifié : accesseurs dans les bornes, matrices de nœuds finies et de
    déterminant positif). Le produit d'une (N,3) par une 3x3 s'écrit en trois
    multiplications élémentwise, qui ne passent par aucune BLAS."""
    out = (P[:, 0:1] * R[:, 0] + P[:, 1:2] * R[:, 1] + P[:, 2:3] * R[:, 2])
    return out if t is None else out + t

def node_matrix(n):
    """Matrice 4x4 locale d'un nœud. Un nœud glTF porte SOIT `matrix`, SOIT le
    triplet TRS, et le modèle fourni emploie `matrix` sur ses 752 nœuds, alors
    que le boîtier emploie TRS : les deux formes sont traitées."""
    if n.matrix is not None:
        # glTF stocke la matrice en colonnes d'abord
        return np.array(n.matrix, float).reshape(4, 4).T
    M = np.eye(4)
    if n.rotation is not None:
        x, y, z, w = n.rotation
        M[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    if n.scale is not None:
        M[:3, :3] = M[:3, :3] @ np.diag(n.scale)
    if n.translation is not None:
        M[:3, 3] = n.translation
    return M


# ══ 1. le modèle fourni, transformation bakée, groupé par matériau ════════
def load_pi():
    g = GLTF2().load_binary(SRC_PI)
    rd = make_reader(g, g.binary_blob())
    groups = collections.defaultdict(list)

    def walk(i, M):
        n = g.nodes[i]
        W = M @ node_matrix(n)
        if n.mesh is not None:
            assert np.linalg.det(W[:3, :3]) > 0, f'nœud {i} : transformation miroir'
            for p in g.meshes[n.mesh].primitives:
                name = g.materials[p.material].name
                P = rd(p.attributes.POSITION).astype(np.float64)
                F = (rd(p.indices).astype(np.int64).ravel().reshape(-1, 3) if p.indices is not None
                     else np.arange(len(P), dtype=np.int64).reshape(-1, 3))
                groups[name].append((xform3(P, W[:3, :3], W[:3, 3]), F))
        for c in (n.children or []):
            walk(c, W)

    for r in g.scenes[g.scene or 0].nodes:
        walk(r, np.eye(4))
    out = {}
    for name, parts in groups.items():
        off = 0; PS = []; FS = []
        for P, F in parts:
            PS.append(P); FS.append(F + off); off += len(P)
        out[name] = (np.vstack(PS), np.vstack(FS))
    return out


# ══ 2. soudure des sommets coïncidents ════════════════════════════════════
def weld(P, F, tol=1e-7):
    key = np.round(P / tol).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    NP = P[first]
    NF = inv.ravel()[F]
    NF = NF[(NF[:, 0] != NF[:, 1]) & (NF[:, 1] != NF[:, 2]) & (NF[:, 0] != NF[:, 2])]
    return NP, NF


# ══ 3. décimation ═════════════════════════════════════════════════════════
# Par `gltf-transform simplify` (meshoptimizer), en sous-processus npx. Deux
# choses à savoir avant d'y toucher :
#
# - **open3d a été essayé d'abord et il est INUTILISABLE sur cette machine.**
#   `open3d 0.18` adossé à `numpy 2.0.2` part en faute de segmentation dès
#   `o3d.utility.Vector3dVector(...)`, y compris sur dix points et y compris en
#   passant une liste Python : la bibliothèque est compilée contre numpy 1.x.
#   Ce n'est pas un défaut de nos données (soudure vérifiée, tableaux finis).
# - **la dépendance npx n'est pas nouvelle** : la compression Draco du modèle
#   livré passe déjà par `npx @gltf-transform/cli`, cf. CLAUDE.md. Le paquet est
#   mis en cache au premier appel.
#
# Seuls les groupes de plus de DECIM_MIN faces sont envoyés. Les petites pièces
# (LED, connecteurs nappe, cavalier PoE) pèsent déjà peu et une décimation les
# efface : `--error` est relatif au rayon de la primitive, donc il ne les
# protège pas.
def decimate_groups(parts):
    import json, shutil, subprocess, tempfile
    big = [n for n in parts if len(parts[n][1]) > DECIM_MIN]
    if not big:
        return parts
    tmp = tempfile.mkdtemp(prefix='addpi-')
    try:
        t = GLTF2(asset=Asset(version='2.0'), scene=0)
        t.scenes = [Scene(nodes=list(range(len(big))))]
        buf = bytearray()

        def view(data):
            while len(buf) % 4:
                buf.append(0)
            off = len(buf); buf.extend(data)
            t.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data)))
            return len(t.bufferViews) - 1

        def acc(arr, typ, ctype):
            bvi = view(np.ascontiguousarray(arr).tobytes())
            t.accessors.append(Accessor(bufferView=bvi, componentType=ctype, count=len(arr),
                                        type=typ,
                                        min=[float(x) for x in np.atleast_2d(arr).min(0)],
                                        max=[float(x) for x in np.atleast_2d(arr).max(0)]))
            return len(t.accessors) - 1

        for k, name in enumerate(big):
            P, F = parts[name]
            t.materials.append(GMat(name=name))
            t.meshes.append(Mesh(name=name, primitives=[Primitive(
                attributes=Attributes(POSITION=acc(P.astype('<f4'), 'VEC3', 5126)),
                indices=acc(F.ravel().astype('<u4').reshape(-1, 1), 'SCALAR', 5125),
                material=k)]))
            t.nodes.append(Node(mesh=k))
        t.buffers = [Buffer(byteLength=len(buf))]
        t.set_binary_blob(bytes(buf))
        src = os.path.join(tmp, 'in.glb'); dst = os.path.join(tmp, 'out.glb')
        t.save(src)
        cmd = ['npx', '--yes', '@gltf-transform/cli@4', 'simplify', src, dst,
               '--ratio', str(DECIM_KEEP), '--error', str(DECIM_ERROR)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode or not os.path.exists(dst):
            raise SystemExit('gltf-transform simplify a échoué :\n' + (r.stderr or r.stdout))
        h = GLTF2().load_binary(dst)
        rd = make_reader(h, h.binary_blob())
        seen = set()
        for me in h.meshes:
            for pr in me.primitives:
                name = h.materials[pr.material].name
                assert name in parts and name not in seen, f'primitive inattendue : {name}'
                seen.add(name)
                P = rd(pr.attributes.POSITION).astype(np.float64)
                F = rd(pr.indices).astype(np.int64).ravel().reshape(-1, 3)
                parts[name] = (P, F)
        assert seen == set(big), f'groupes perdus par la décimation : {set(big) - seen}'
        return parts
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ══ 4. normales par arêtes vives ══════════════════════════════════════════
def crease_normals(P, F, crease_deg=CREASE):
    fn = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    L = np.linalg.norm(fn, axis=1, keepdims=True)
    fn = fn / np.maximum(L, 1e-20)
    fa = 0.5 * L.ravel()
    cosmin = float(np.cos(np.radians(crease_deg)))
    vi = F.ravel(); fi = np.repeat(np.arange(len(F)), 3)
    o = np.argsort(vi, kind='stable'); vi = vi[o]; fi = fi[o]
    beg = np.searchsorted(vi, np.arange(len(P)))
    end = np.searchsorted(vi, np.arange(len(P)), side='right')
    NP = []; NN = []; remap = {}
    for v in range(len(P)):
        faces = fi[beg[v]:end[v]]
        if not len(faces):
            continue
        groups = []          # [somme pondérée des normales, faces]
        for f in faces:
            nf = fn[f]
            for gk in groups:
                acc = gk[0]; n = np.linalg.norm(acc)
                if n > 1e-20 and nf @ (acc / n) >= cosmin:
                    gk[0] = acc + nf * fa[f]; gk[1].append(f); break
            else:
                groups.append([nf * fa[f], [f]])
        for gk in groups:
            acc = gk[0]; n = np.linalg.norm(acc)
            nrm = acc / n if n > 1e-20 else fn[gk[1][0]]
            idx = len(NP); NP.append(P[v]); NN.append(nrm)
            for f in gk[1]:
                remap[(v, f)] = idx
    NF = np.empty_like(F)
    for k in range(len(F)):
        for j in range(3):
            NF[k, j] = remap[(F[k, j], k)]
    return np.asarray(NP, np.float32), np.asarray(NN, np.float32), NF


# ══ montage dans le GLB du boîtier ════════════════════════════════════════
def main():
    for p in (SRC_BOX, SRC_PI):
        if not os.path.exists(p):
            raise SystemExit(f'source absente : {p}')

    pi = load_pi()
    tri0 = sum(len(F) for _, F in pi.values())
    box = np.vstack([P for P, _ in pi.values()])
    print(f"carte fournie : {tri0} faces, {sum(len(P) for P,_ in pi.values())} sommets, "
          f"{1000*(box.max(0)-box.min(0))[0]:.1f} x {1000*(box.max(0)-box.min(0))[1]:.1f} x "
          f"{1000*(box.max(0)-box.min(0))[2]:.1f} mm")

    # soudure, puis décimation des seuls gros groupes
    parts = {}; before = {}
    for name in sorted(pi, key=lambda k: -len(pi[k][1])):
        P, F = pi[name]
        before[name] = (len(P), len(F))
        parts[name] = weld(P, F)
    parts = decimate_groups(parts)
    for name in sorted(parts, key=lambda k: -before[k][1]):
        nv0, nf0 = before[name]
        print(f"  {name:14s} {nv0:7d} som. -> {len(parts[name][0]):6d}   "
              f"{nf0:6d} faces -> {len(parts[name][1]):6d}")
    tri1 = sum(len(F) for _, F in parts.values())
    print(f"total : {tri0} -> {tri1} faces ({100*tri1/tri0:.0f} %)")

    # ── orientation et pose ───────────────────────────────────────────────
    # +90° autour de Y : +X (bloc Ethernet/USB) -> -Z, donc vers l'ARRIÈRE.
    #
    # LE SENS A ÉTÉ INVERSÉ LE 2026-09-03, SUR CONSTAT DU CLIENT : les prises se
    # présentaient à l'avant du boîtier alors qu'elles sortent à l'arrière. La
    # première version tournait de -90°, en raisonnant sur le câblage INTERNE
    # (l'embase USB-C du téléphone est à l'avant, donc rapprocher les ports du
    # téléphone semblait juste). C'est la connectique EXTERNE qui commande : le
    # réseau et l'alimentation sortent du côté opposé au poste de travail.
    #
    # ET CE N'EST PAS UNE ROTATION AUTOUR DE X, malgré la formulation de la
    # demande : un demi-tour autour de X enverrait bien les prises vers l'arrière,
    # mais il retournerait la carte, composants vers le plancher. Le geste demandé
    # est un demi-tour à plat, donc autour de la verticale.
    RY = np.array([[0., 0., 1.], [0., 1., 0.], [-1., 0., 0.]])
    assert abs(np.linalg.det(RY) - 1) < 1e-12, 'la matrice doit être une rotation, pas une réflexion'
    for name in parts:
        P, F = parts[name]
        parts[name] = (xform3(P, RY), F)
    allP = np.vstack([P for P, _ in parts.values()])
    lo, hi = allP.min(0), allP.max(0)
    shift = np.array([-(lo[0] + hi[0]) / 2,               # centrée en largeur
                      SEAT_Y - lo[1],                     # posée sur le plancher
                      FOOT_Z - (lo[2] + hi[2]) / 2])      # centrée sur le plancher libre
    for name in parts:
        P, F = parts[name]
        parts[name] = (P + shift, F)
    allP = allP + shift
    lo, hi = allP.min(0), allP.max(0)
    print(f"posée : x[{1000*lo[0]:+.1f},{1000*hi[0]:+.1f}] y[{1000*lo[1]:+.1f},{1000*hi[1]:+.1f}] "
          f"z[{1000*lo[2]:+.1f},{1000*hi[2]:+.1f}] mm")
    seat = ((lo + hi) / 2)
    print(f"centre au repos : [{seat[0]:.4f}, {seat[1]:.4f}, {seat[2]:.4f}]  "
          f"écart t=0,98 : [{EXPLODE[0]:.5f}, {EXPLODE[1]:.5f}, {EXPLODE[2]:.5f}]")

    # ── écriture ──────────────────────────────────────────────────────────
    g = GLTF2().load_binary(SRC_BOX)
    blob = bytearray(g.binary_blob())
    n_mesh0, n_mat0, n_node0 = len(g.meshes), len(g.materials), len(g.nodes)

    def add_view(data, target=None):
        while len(blob) % 4:
            blob.append(0)
        off = len(blob); blob.extend(data)
        while len(blob) % 4:
            blob.append(0)
        g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data), target=target))
        return len(g.bufferViews) - 1

    def add_acc(arr, typ, ctype=5126, target=34962):
        bvi = add_view(np.ascontiguousarray(arr).tobytes(), target)
        g.accessors.append(Accessor(bufferView=bvi, componentType=ctype, count=len(arr), type=typ,
                                    min=[float(x) for x in np.atleast_2d(arr).min(0)],
                                    max=[float(x) for x in np.atleast_2d(arr).max(0)]))
        return len(g.accessors) - 1

    prims = []
    for name in sorted(parts):
        P, F = parts[name]
        NP, NN, NF = crease_normals(P, F)
        base, metal, rough = LOOK[name]
        g.materials.append(GMat(name='pi-' + name, doubleSided=False,
                                pbrMetallicRoughness=PbrMetallicRoughness(
                                    baseColorFactor=list(base) + [1.0],
                                    metallicFactor=metal, roughnessFactor=rough)))
        idx = NF.ravel().astype('<u4')
        prims.append(Primitive(
            attributes=Attributes(POSITION=add_acc(NP.astype('<f4'), 'VEC3'),
                                  NORMAL=add_acc(NN.astype('<f4'), 'VEC3')),
            indices=add_acc(idx.reshape(-1, 1), 'SCALAR', ctype=5125, target=34963),
            material=len(g.materials) - 1))

    g.meshes.append(Mesh(name='pi', primitives=prims))
    g.nodes.append(Node(name='pi', mesh=len(g.meshes) - 1, translation=[0.0, 0.0, 0.0]))
    pi_node = len(g.nodes) - 1
    g.nodes[0].children = list(g.nodes[0].children) + [pi_node]

    # keyframes : les MÊMES instants que les pièces du boîtier. On réutilise
    # leur accesseur de temps plutôt que d'en écrire un second, qui pourrait
    # dériver d'un millième et désynchroniser le réassemblage.
    anim = g.animations[0]
    tray_ch = next(c for c in anim.channels if c.target.node == 1 and c.target.path == 'translation')
    t_in = anim.samplers[tray_ch.sampler].input
    times = make_reader(g, bytes(blob))(t_in).ravel()
    assert len(times) == 3 and abs(times[0]) < 1e-6 and abs(times[2] - 1.0) < 1e-6, \
        f'instants inattendus sur le plateau : {times}'
    vals = np.array([[0, 0, 0], EXPLODE, [0, 0, 0]], '<f4')
    anim.samplers.append(AnimationSampler(input=t_in, output=add_acc(vals, 'VEC3', target=None),
                                          interpolation='LINEAR'))
    anim.channels.append(AnimationChannel(sampler=len(anim.samplers) - 1,
                                          target=AnimationChannelTarget(node=pi_node,
                                                                        path='translation')))

    g.set_binary_blob(bytes(blob))
    g.buffers[0].byteLength = len(blob)
    g.save(OUT)
    print(f"écrit {OUT} : {os.path.getsize(OUT)/1e6:.2f} Mo "
          f"(source {os.path.getsize(SRC_BOX)/1e6:.2f} Mo)")
    print(f"  meshes {n_mesh0} -> {len(g.meshes)}, matériaux {n_mat0} -> {len(g.materials)}, "
          f"nœuds {n_node0} -> {len(g.nodes)}, canaux d'animation {len(anim.channels)}")


if __name__ == '__main__':
    main()
