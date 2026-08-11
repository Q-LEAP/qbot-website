from PIL import Image, ImageDraw, ImageFilter
import numpy as np, shutil, sys

W,H = 2048,1024
THETA = -32.0                     # azimut caméra des plans héro
def u_of(theta): return (0.75 - theta/360.0) % 1.0
U_CAM  = u_of(THETA)              # d'où regarde la caméra
U_BACK = (U_CAM + 0.5) % 1.0      # contre-jour : rim

def blob(d, u, v, rx, ry, col):
    cx = u*W
    for dx in (-W, 0, W):                     # répète pour le raccord 0/1
        d.ellipse([cx+dx-rx, v*H-ry, cx+dx+rx, v*H+ry], fill=col)

base = Image.new('RGB',(W,H),(5,5,6)); db=ImageDraw.Draw(base)
for y in range(int(H*0.7)):
    t=1-y/(H*0.7); v=int(20*t+5); db.line([(0,y),(W,y)], fill=(v,v,int(v*1.06)))
db.rectangle([0,int(H*0.7),W,H], fill=(9,9,10))
base = base.filter(ImageFilter.GaussianBlur(60))

L = Image.new('RGB',(W,H),(0,0,0)); dl=ImageDraw.Draw(L)
blob(dl, (U_CAM-0.11)%1, 0.15, 520, 265, (255,255,255))   # key : grande source haute avant-gauche
blob(dl, (U_CAM+0.18)%1, 0.30, 300, 185, (120,126,134))   # fill doux
blob(dl, (U_CAM-0.02)%1, 0.42, 300, 175, (58,62,68))      # fill frontal : modelé de la face avant
blob(dl, U_BACK,          0.38, 165, 125, (0,255,242))     # rim teal en contre-jour (arête haute)
blob(dl, (U_CAM-0.27)%1,  0.46, 130, 110, (210,224,255))   # rim froid : détache un flanc du fond
blob(dl, (U_CAM+0.27)%1,  0.50, 115,  95, (0,190,180))     # rim teal : détache l'autre flanc
blob(dl, (U_BACK+0.13)%1, 0.56, 105,  85, (0,140,133))     # relance teal basse
L = L.filter(ImageFilter.GaussianBlur(24))

env = Image.fromarray(np.clip(np.asarray(base,np.int16)+np.asarray(L,np.int16),0,255).astype(np.uint8))
out = sys.argv[1] if len(sys.argv)>1 else 'env-v3.png'
env.save(out); shutil.copy(out,'/Volumes/CCCOMA_X64F/Sites/Q-Bot/_env.png')
print(f"u_cam={U_CAM:.3f} u_rim={U_BACK:.3f} | moyenne={np.asarray(env.convert('L')).mean():.1f}")
