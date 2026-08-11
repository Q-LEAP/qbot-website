# -*- coding: utf-8 -*-
"""Patche qbot.glb pour le RENDU : matériaux sombres + micro-texture.

Chirurgical (pygltflib) plutôt qu'un ré-export : le clip « Explode » doit
survivre, c'est lui qui pose le téléphone sur son socle (currentTime = 2 s).
L'animation pilote des transforms de NŒUDS, pas des sommets : on peut donc
reconstruire librement la géométrie des primitives.

Le maillage n'a aucune UV. Une projection planaire par pièce étire la texture
sur les faces obliques et la transforme en stries — d'où une projection
TRIPLANAIRE par face : chaque triangle est projeté sur le plan perpendiculaire
à sa normale dominante. Cela impose de dégrouper les sommets (3 par triangle),
ce qui triple leur nombre : sans importance ici, ce GLB ne sert qu'au rendu
hors-ligne, il n'est pas livré sur le site.
"""
import numpy as np, os, sys
from pygltflib import (GLTF2, Accessor, BufferView, Image as GImage, Sampler,
                       Texture, TextureInfo, NormalMaterialTexture, PbrMetallicRoughness)

SRC='/Volumes/CCCOMA_X64F/Sites/Q-Bot/assets/models/qbot.glb'
DST='/Volumes/CCCOMA_X64F/Sites/Q-Bot/_qbot-render.glb'
UV_SCALE   = float(os.environ.get('UV_SCALE', 42))
NORM_SCALE = float(os.environ.get('NORM_SCALE', 0.55))

g=GLTF2().load(SRC); blob=bytearray(g.binary_blob())
CT={5120:'i1',5121:'u1',5122:'i2',5123:'u2',5125:'u4',5126:'f4'}
NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}

def read_acc(i):
    a=g.accessors[i]; bv=g.bufferViews[a.bufferView]
    n=NC[a.type]; dt=np.dtype(CT[a.componentType]).newbyteorder('<')
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

def add_acc(arr, typ, ctype=5126, target=34962):
    bvi=add_view(np.ascontiguousarray(arr).tobytes(), target)
    g.accessors.append(Accessor(bufferView=bvi, componentType=ctype, count=len(arr), type=typ,
                                min=[float(x) for x in np.atleast_2d(arr).min(0)],
                                max=[float(x) for x in np.atleast_2d(arr).max(0)]))
    return len(g.accessors)-1

def add_png(path):
    bvi=add_view(open(path,'rb').read())
    g.images.append(GImage(bufferView=bvi, mimeType='image/png'))
    g.textures.append(Texture(source=len(g.images)-1, sampler=SAMPLER))
    return len(g.textures)-1

g.samplers.append(Sampler(magFilter=9729, minFilter=9987, wrapS=10497, wrapT=10497))
SAMPLER=len(g.samplers)-1
TEX_N=add_png('tex-normal.png'); TEX_MR=add_png('tex-mr.png')

PHONE_MAT=4
for mi,me in enumerate(g.meshes):
    for pr in me.primitives:
        if pr.material==PHONE_MAT or pr.attributes.TEXCOORD_0 is not None: continue
        pos=read_acc(pr.attributes.POSITION).astype(np.float32)
        nrm=read_acc(pr.attributes.NORMAL).astype(np.float32) if pr.attributes.NORMAL is not None else None
        idx=read_acc(pr.indices).astype(np.int64).ravel() if pr.indices is not None else np.arange(len(pos))
        P=pos[idx]; N=nrm[idx] if nrm is not None else None
        tri=P.reshape(-1,3,3)
        fn=np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
        fn/= (np.linalg.norm(fn,axis=1,keepdims=True)+1e-12)
        dom=np.argmax(np.abs(fn),axis=1)                     # axe dominant par face
        AX={0:(1,2),1:(0,2),2:(0,1)}
        uv=np.empty((len(tri),3,2),np.float32)
        for ax,(a,b) in AX.items():
            m=dom==ax
            if m.any(): uv[m]=tri[m][:,:,[a,b]]*UV_SCALE
        uv=uv.reshape(-1,2)
        pr.attributes.POSITION=add_acc(P.astype('<f4'),'VEC3')
        if N is not None: pr.attributes.NORMAL=add_acc(N.astype('<f4'),'VEC3')
        pr.attributes.TEXCOORD_0=add_acc(uv.astype('<f4'),'VEC2')
        pr.indices=None
        print(f"  mesh {mi} mat {pr.material}: {len(tri)} faces -> {len(P)} sommets")

# ── Écran du smartphone ──
# Ses UV d'origine sont dégénérées (4 texels de palette, un par face) : on ne
# peut rien y peindre. On isole donc les faces de la dalle dans une primitive
# dédiée, avec de vraies UV planaires et un matériau émissif.
TEX_SCR=add_png('tex-screen.png')
from pygltflib import Mesh, Primitive, Attributes, Material as GMat, TextureInfo as TI
me=g.meshes[5]; pr=me.primitives[0]
pos=read_acc(pr.attributes.POSITION).astype(np.float32)
nrm=read_acc(pr.attributes.NORMAL).astype(np.float32) if pr.attributes.NORMAL is not None else None
uv0=read_acc(pr.attributes.TEXCOORD_0).astype(np.float32)
idx=read_acc(pr.indices).astype(np.int64).ravel()
tri=idx.reshape(-1,3)
P3=pos[tri]
fn=np.cross(P3[:,1]-P3[:,0], P3[:,2]-P3[:,0])
ar=0.5*np.linalg.norm(fn,axis=1); fn/= (np.linalg.norm(fn,axis=1,keepdims=True)+1e-12)
# La dalle regarde vers l'avant du téléphone, incliné : direction déduite des
# grandes faces plutôt que codée en dur.
cand=fn[np.argsort(-ar)[:8]]
d=cand[np.argmax(cand[:,2])]; d/=np.linalg.norm(d)
sel=(fn@d)>0.95
off=(P3.mean(1)@d)
sel &= off > (off[sel].max()-1e-4)
print(f"  écran : {sel.sum()} faces, normale ({d[0]:+.2f},{d[1]:+.2f},{d[2]:+.2f})")
right=np.array([1.0,0.0,0.0]); up=np.cross(d,right); up/=np.linalg.norm(up)
Ps=P3[sel].reshape(-1,3); Ns=(nrm[tri][sel].reshape(-1,3) if nrm is not None else None)
u=Ps@right; v=Ps@up
u=(u-u.min())/(u.max()-u.min()); v=1-(v-v.min())/(v.max()-v.min())
uvS=np.stack([u,v],1).astype(np.float32)
# le reste du téléphone garde sa palette
Pk=P3[~sel].reshape(-1,3); Nk=(nrm[tri][~sel].reshape(-1,3) if nrm is not None else None)
uvK=uv0[tri][~sel].reshape(-1,2)
pr.attributes.POSITION=add_acc(Pk.astype('<f4'),'VEC3')
if Nk is not None: pr.attributes.NORMAL=add_acc(Nk.astype('<f4'),'VEC3')
pr.attributes.TEXCOORD_0=add_acc(uvK.astype('<f4'),'VEC2'); pr.indices=None
g.materials.append(GMat(name='screen',
    pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=[1,1,1,1], metallicFactor=0.0,
        roughnessFactor=0.16, baseColorTexture=TI(index=TEX_SCR)),
    emissiveFactor=[1.0,1.0,1.0], emissiveTexture=TI(index=TEX_SCR)))
MAT_SCR=len(g.materials)-1
att=Attributes(POSITION=add_acc(Ps.astype('<f4'),'VEC3'), TEXCOORD_0=add_acc(uvS,'VEC2'))
if Ns is not None: att.NORMAL=add_acc(Ns.astype('<f4'),'VEC3')
me.primitives.append(Primitive(attributes=att, material=MAT_SCR))

LOOK={0:dict(base=[0.072,0.076,0.082,1.0],metal=0.32,rough=0.44,tex=True),
      1:dict(base=[0.064,0.068,0.074,1.0],metal=0.30,rough=0.42,tex=True),
      2:dict(base=[0.30,0.315,0.335,1.0], metal=0.65,rough=0.30,tex=True),
            # hublot d'écran du boîtier : verre sombre, pas un rectangle blanc
      3:dict(base=[0.085,0.092,0.10,1.0], metal=0.35,rough=0.10,tex=False)}
for mi,look in LOOK.items():
    m=g.materials[mi]; p=m.pbrMetallicRoughness or PbrMetallicRoughness()
    p.baseColorFactor=look['base']; p.metallicFactor=look['metal']; p.roughnessFactor=look['rough']
    if look['tex']:
        p.metallicRoughnessTexture=TextureInfo(index=TEX_MR)
        m.normalTexture=NormalMaterialTexture(index=TEX_N, scale=NORM_SCALE)
    m.pbrMetallicRoughness=p

g.set_binary_blob(bytes(blob)); g.buffers[0].byteLength=len(blob); g.save(DST)
print("écrit:", DST, os.path.getsize(DST)//1024//1024,"Mo | uv",UV_SCALE,"norm",NORM_SCALE)
