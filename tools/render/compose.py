# -*- coding: utf-8 -*-
"""Compose les visuels finaux à partir du rendu détouré (alpha)."""
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import numpy as np

TEAL=(0,203,190)

def trim(im, pad=0.02):
    b=im.getbbox(); p=int(pad*max(b[2]-b[0], b[3]-b[1]))
    return im.crop((max(0,b[0]-p),max(0,b[1]-p),min(im.width,b[2]+p),min(im.height,b[3]+p)))

def glow(rgba, radius, color, strength, canvas=None, at=(0,0)):
    """Halo coloré dérivé de la silhouette.

    Le flou doit être calculé sur un calque de la taille de la TOILE, pas de
    l'image produit : sinon il est coupé net au bord de celle-ci et laisse un
    halo carré parfaitement visible sur fond sombre.
    """
    size = canvas or rgba.size
    a = Image.new('L', size, 0)
    a.paste(rgba.split()[3], at)
    a = a.filter(ImageFilter.GaussianBlur(radius))
    a = Image.fromarray((np.asarray(a,np.float32)*strength).clip(0,255).astype(np.uint8))
    g = Image.new('RGBA', size, color+(0,)); g.putalpha(a); return g

def reflection(rgba, height=0.42, blur=9, opacity=0.30):
    w,h=rgba.size
    r=rgba.transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(blur))
    ramp=np.linspace(opacity,0,h)[:,None]**1.9
    a=(np.asarray(r.split()[3],np.float32)/255*ramp*255).astype(np.uint8)
    r.putalpha(Image.fromarray(a))
    return r.crop((0,0,w,int(h*height)))

def backdrop(size, cx, cy, warm=False):
    """Fond : nuit profonde, halo teal, sol en arcs concentriques, vignette."""
    W,H=size
    bg=Image.new('RGB',(W,H),(4,4,5))
    d=ImageDraw.Draw(bg)
    for y in range(H):                                   # dégradé vertical
        v=int(11*(1-y/H)**1.4+3); d.line([(0,y),(W,y)],fill=(v,v,int(v*1.12)))
    # halo teal derrière le produit
    hal=Image.new('RGB',(W,H),(0,0,0)); dh=ImageDraw.Draw(hal)
    dh.ellipse([cx-W*0.30, cy-H*0.34, cx+W*0.30, cy+H*0.30], fill=(0,120,112))
    dh.ellipse([cx-W*0.15, cy-H*0.17, cx+W*0.15, cy+H*0.15], fill=(0,190,178))
    hal=hal.filter(ImageFilter.GaussianBlur(int(W*0.075)))
    bg=ImageChops.add(bg, hal.point(lambda v:int(v*0.55)))
    # sol : arcs concentriques fins
    fl=Image.new('RGB',(W,H),(0,0,0)); df=ImageDraw.Draw(fl)
    fy=cy+H*0.24
    for i,rr in enumerate((0.20,0.30,0.42,0.56)):
        df.ellipse([cx-W*rr, fy-H*rr*0.22, cx+W*rr, fy+H*rr*0.22],
                   outline=(0,int(150-24*i),int(142-22*i)), width=max(1,int(W*0.0016)))
    fl=fl.filter(ImageFilter.GaussianBlur(int(W*0.004)))
    bg=ImageChops.add(bg, fl.point(lambda v:int(v*0.5)))
    # ligne d'horizon très douce
    hz=Image.new('RGB',(W,H),(0,0,0)); dz=ImageDraw.Draw(hz)
    dz.rectangle([0,int(fy-H*0.012),W,int(fy+H*0.012)], fill=(0,60,57))
    bg=ImageChops.add(bg, hz.filter(ImageFilter.GaussianBlur(int(W*0.03))))
    # vignette
    vg=np.zeros((H,W),np.float32)
    yy,xx=np.mgrid[0:H,0:W]
    r=np.sqrt(((xx-W/2)/(W*0.62))**2+((yy-H/2)/(H*0.62))**2)
    vg=np.clip((r-0.55)/0.9,0,1)**1.5
    bg=Image.fromarray((np.asarray(bg,np.float32)*(1-vg[...,None]*0.85)).astype(np.uint8))
    return bg.convert('RGBA')

def grade(rgba, lift=0.0, gain=1.0, gamma=1.0):
    a=np.asarray(rgba,np.float32)/255
    rgb=np.clip(((a[...,:3]*gain)**gamma)+lift,0,1)
    out=np.dstack([rgb, a[...,3:]])
    return Image.fromarray((out*255).astype(np.uint8),'RGBA')
