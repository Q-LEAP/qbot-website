# -*- coding: utf-8 -*-
"""Applique au modèle LIVRÉ (assets/models/qbot.glb) la matière mise au point
pour les visuels : corps sombre à grain fin, hublot en verre, écran 2FA sur le
smartphone.

Deux contraintes qui n'existent pas pour le rendu hors-ligne :

1. **Le poids compte** — ce fichier est téléchargé par le visiteur. D'où deux
   écarts avec `patchglb.py` :
   - UV projetées **par sommet** (axe dominant de la NORMALE du sommet) et non
     par face : le triplanaire par face impose de dégrouper les sommets, ce qui
     les triple et fait passer le fichier de 3,6 à 15 Mo. Par sommet, la
     géométrie est intacte : on n'ajoute que 8 octets par sommet. Le compromis
     est une légère discontinuité de texture sur les arêtes vives — invisible
     avec un grain isotrope fin, et une arête moulée en a une de toute façon.
   - pas de texture métal/rugosité : facteurs constants, la variation était
     subtile et coûtait 137 Ko.
2. **Le hublot doit laisser voir l'intérieur.** Une vitre translucide sur une
   coque *single-sided* ne montre pas un intérieur sombre : les faces arrière
   sont éliminées au rendu et on voit le fond de la page à travers l'objet.
   La coque et le plateau passent donc en `doubleSided` — c'est ce qui donne
   la cavité sombre derrière le verre.

Comme `patchglb.py`, on PATCHE le GLB (pygltflib) sans le ré-exporter : le clip
« Explode » doit survivre, c'est lui qui pose le téléphone sur son socle.

    python3 patchglb-site.py            # écrit assets/models/qbot.glb (sauvegarde .bak)

Après exécution, régénérer le sidecar base64 (cf. CLAUDE.md) :
    qbot.glb.data.js, sinon l'ouverture en file:// affiche l'ancien modèle.
"""
import numpy as np, os, shutil, sys
from pygltflib import (GLTF2, Accessor, BufferView, Image as GImage, Sampler, Texture,
                       TextureInfo, NormalMaterialTexture, Material as GMat, Primitive,
                       Attributes, PbrMetallicRoughness)

HERE = os.path.dirname(os.path.abspath(__file__))
GLB  = os.path.join(HERE, '..', '..', 'assets', 'models', 'qbot.glb')
TEX_NORMAL = os.environ.get('TEX_NORMAL', 'tex-normal-256.png')
TEX_SCREEN = os.environ.get('TEX_SCREEN', 'tex-screen-512.png')
UV_SCALE   = float(os.environ.get('UV_SCALE', 42))
NORM_SCALE = float(os.environ.get('NORM_SCALE', 0.5))
GLASS_ALPHA = float(os.environ.get('GLASS_ALPHA', 0.42))

# Source = le modèle NON texturé archivé, jamais le fichier livré : relancer le
# script sur un GLB déjà patché le patcherait une seconde fois.
BAK = os.path.join(HERE, '..', '..', 'Documentations', 'assets-sources', 'qbot-untextured.glb')
if not os.path.exists(BAK):
    shutil.copy(GLB, BAK)
# load_binary explicite : pygltflib choisit son parseur d'après l'extension,
# et « .bak » le ferait partir sur du glTF JSON.
g = GLTF2().load_binary(BAK)
blob = bytearray(g.binary_blob())

CT = {5120:'i1',5121:'u1',5122:'i2',5123:'u2',5125:'u4',5126:'f4'}
NC = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}

def read_acc(i):
    a=g.accessors[i]; bv=g.bufferViews[a.bufferView]
    dt=np.dtype(CT[a.componentType]).newbyteorder('<'); n=NC[a.type]
    off=(bv.byteOffset or 0)+(a.byteOffset or 0)
    stride=bv.byteStride or dt.itemsize*n
    if stride==dt.itemsize*n:
        return np.frombuffer(blob, dt, a.count*n, off).reshape(a.count,n)
    out=np.empty((a.count,n),dt)
    for k in range(a.count): out[k]=np.frombuffer(blob,dt,n,off+k*stride)
    return out

def add_view(data, target=None):
    while len(blob)%4: blob.append(0)
    off=len(blob); blob.extend(data)
    while len(blob)%4: blob.append(0)
    g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(data), target=target))
    return len(g.bufferViews)-1

def add_acc(arr, typ, target=34962):
    bvi=add_view(np.ascontiguousarray(arr).tobytes(), target)
    g.accessors.append(Accessor(bufferView=bvi, componentType=5126, count=len(arr), type=typ,
                                min=[float(x) for x in np.atleast_2d(arr).min(0)],
                                max=[float(x) for x in np.atleast_2d(arr).max(0)]))
    return len(g.accessors)-1

def add_png(path):
    bvi=add_view(open(os.path.join(HERE, path) if not os.path.isabs(path) else path,'rb').read())
    g.images.append(GImage(bufferView=bvi, mimeType='image/png'))
    g.textures.append(Texture(source=len(g.images)-1, sampler=SAMPLER))
    return len(g.textures)-1

g.samplers.append(Sampler(magFilter=9729, minFilter=9987, wrapS=10497, wrapT=10497))
SAMPLER=len(g.samplers)-1
TEX_N = add_png(TEX_NORMAL)

# ── 1. UV par sommet, axe dominant de la normale ──────────────────────────
GLASS_MAT, PHONE_MAT = 3, 4
for mi, me in enumerate(g.meshes):
    for pr in me.primitives:
        if pr.material in (GLASS_MAT, PHONE_MAT): continue
        if pr.attributes.TEXCOORD_0 is not None: continue
        pos = read_acc(pr.attributes.POSITION).astype(np.float32)
        if pr.attributes.NORMAL is not None:
            nrm = read_acc(pr.attributes.NORMAL).astype(np.float32)
            dom = np.argmax(np.abs(nrm), axis=1)
        else:
            dom = np.full(len(pos), 2)
        uv = np.empty((len(pos),2), np.float32)
        for ax,(a,b) in {0:(1,2),1:(0,2),2:(0,1)}.items():
            m = dom==ax
            if m.any(): uv[m] = pos[m][:,[a,b]]*UV_SCALE
        pr.attributes.TEXCOORD_0 = add_acc(uv,'VEC2')
        print(f"  mesh {mi} mat {pr.material}: UV sur {len(pos)} sommets (géométrie intacte)")

# ── 2. Écran du smartphone : primitive dédiée (UV d'origine dégénérées) ───
TEX_SCR = add_png(TEX_SCREEN)
me = g.meshes[5]; pr = me.primitives[0]
pos = read_acc(pr.attributes.POSITION).astype(np.float32)
nrm = read_acc(pr.attributes.NORMAL).astype(np.float32) if pr.attributes.NORMAL is not None else None
uv0 = read_acc(pr.attributes.TEXCOORD_0).astype(np.float32)
tri = read_acc(pr.indices).astype(np.int64).ravel().reshape(-1,3)
P3 = pos[tri]
fn = np.cross(P3[:,1]-P3[:,0], P3[:,2]-P3[:,0])
ar = 0.5*np.linalg.norm(fn,axis=1); fn /= (np.linalg.norm(fn,axis=1,keepdims=True)+1e-12)
cand = fn[np.argsort(-ar)[:8]]
d = cand[np.argmax(cand[:,2])]; d /= np.linalg.norm(d)
sel = (fn@d) > 0.95
off = P3.mean(1)@d
sel &= off > (off[sel].max()-1e-4)
right = np.array([1.0,0,0]); up = np.cross(d,right); up /= np.linalg.norm(up)
Ps = P3[sel].reshape(-1,3); Ns = nrm[tri][sel].reshape(-1,3) if nrm is not None else None
u = Ps@right; v = Ps@up
u = (u-u.min())/(u.max()-u.min()); v = 1-(v-v.min())/(v.max()-v.min())
Pk = P3[~sel].reshape(-1,3); Nk = nrm[tri][~sel].reshape(-1,3) if nrm is not None else None
pr.attributes.POSITION = add_acc(Pk.astype('<f4'),'VEC3')
if Nk is not None: pr.attributes.NORMAL = add_acc(Nk.astype('<f4'),'VEC3')
pr.attributes.TEXCOORD_0 = add_acc(uv0[tri][~sel].reshape(-1,2).astype('<f4'),'VEC2')
pr.indices = None
g.materials.append(GMat(name='phone-screen',
    pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=[1,1,1,1], metallicFactor=0.0,
        roughnessFactor=0.16, baseColorTexture=TextureInfo(index=TEX_SCR)),
    emissiveFactor=[1,1,1], emissiveTexture=TextureInfo(index=TEX_SCR)))
att = Attributes(POSITION=add_acc(Ps.astype('<f4'),'VEC3'),
                 TEXCOORD_0=add_acc(np.stack([u,v],1).astype('<f4'),'VEC2'))
if Ns is not None: att.NORMAL = add_acc(Ns.astype('<f4'),'VEC3')
me.primitives.append(Primitive(attributes=att, material=len(g.materials)-1))
print(f"  écran smartphone : {int(sel.sum())} faces isolées")

# ── 3. Matériaux ──────────────────────────────────────────────────────────
LOOK = {
 0: dict(base=[0.072,0.076,0.082,1.0], metal=0.32, rough=0.44, tex=True),   # plateau
 1: dict(base=[0.064,0.068,0.074,1.0], metal=0.30, rough=0.42, tex=True),   # coque
 2: dict(base=[0.30,0.315,0.335,1.0],  metal=0.65, rough=0.30, tex=True),   # petites pièces
}
for mi, look in LOOK.items():
    m=g.materials[mi]; p=m.pbrMetallicRoughness or PbrMetallicRoughness()
    p.baseColorFactor=look['base']; p.metallicFactor=look['metal']; p.roughnessFactor=look['rough']
    p.metallicRoughnessTexture=None
    if look['tex']: m.normalTexture=NormalMaterialTexture(index=TEX_N, scale=NORM_SCALE)
    m.pbrMetallicRoughness=p
    # indispensable pour que le verre montre une cavité et non le fond de page
    m.doubleSided=True

# hublot : verre légèrement teinté, comme sur le produit réel
gl=g.materials[GLASS_MAT]
gl.pbrMetallicRoughness=PbrMetallicRoughness(
    baseColorFactor=[0.16,0.185,0.20, GLASS_ALPHA], metallicFactor=0.0, roughnessFactor=0.06)
gl.alphaMode='BLEND'; gl.doubleSided=True; gl.normalTexture=None

g.set_binary_blob(bytes(blob)); g.buffers[0].byteLength=len(blob)
g.save(GLB)
print(f"écrit {GLB}: {os.path.getsize(GLB)/1e6:.2f} Mo (avant : {os.path.getsize(BAK)/1e6:.2f} Mo)")
