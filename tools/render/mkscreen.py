# -*- coding: utf-8 -*-
"""Écran du smartphone : validation d'authentification, purement iconographique.
Volontairement sans texte ni logo — ce n'est pas une reproduction de l'app
LuxTrust, juste la représentation générique d'une validation acceptée."""
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

W,H = 720, 1440
TEAL=(0,203,190)
im=Image.new('RGB',(W,H),(9,10,12)); d=ImageDraw.Draw(im)
# léger dégradé + halo teal derrière la pastille
for y in range(H):
    t=y/H; v=int(9+10*max(0.0, 1-abs(t-0.42)*2)); d.line([(0,y),(W,y)],fill=(v,v+1,v+2))
hal=Image.new('RGB',(W,H),(0,0,0)); dh=ImageDraw.Draw(hal)
dh.ellipse([W*0.5-260, H*0.42-260, W*0.5+260, H*0.42+260], fill=(0,110,103))
im=Image.fromarray(np.clip(np.asarray(im,np.int16)+np.asarray(hal.filter(ImageFilter.GaussianBlur(90)),np.int16),0,255).astype(np.uint8))
d=ImageDraw.Draw(im)
# anneau + coche
cx,cy,r = W*0.5, H*0.42, 168
d.ellipse([cx-r,cy-r,cx+r,cy+r], outline=TEAL, width=14)
d.line([(cx-72,cy+6),(cx-16,cy+62),(cx+82,cy-56)], fill=TEAL, width=22, joint='curve')
# barres de texte factices (aucun mot lisible)
for i,(wd,al) in enumerate(((0.52,190),(0.34,110))):
    y=cy+r+130+i*54
    d.rounded_rectangle([cx-W*wd/2, y, cx+W*wd/2, y+22], radius=11, fill=(al,al,al))
# bouton d'action
by=H*0.80
d.rounded_rectangle([W*0.14, by, W*0.86, by+92], radius=46, fill=TEAL)
# encoche + barre d'accueil
d.rounded_rectangle([W*0.34, 26, W*0.66, 62], radius=18, fill=(0,0,0))
d.rounded_rectangle([W*0.33, H-46, W*0.67, H-32], radius=7, fill=(70,72,76))
im.save('tex-screen.png'); print('écran ok', im.size)
