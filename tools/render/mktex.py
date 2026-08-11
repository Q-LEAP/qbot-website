from PIL import Image, ImageFilter
import numpy as np

S = 512
rng = np.random.default_rng(7)

def periodic_blur(a, r):
    """Flou gaussien à raccord périodique (texture tuilable)."""
    t = np.tile(a, (3,3))
    im = Image.fromarray((np.clip(t,0,1)*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    t = np.asarray(im, np.float32)/255
    return t[S:2*S, S:2*S]

# Grain fin + une trame plus large : la coque du produit a un aspect
# légèrement granuleux, pas un plastique lisse.
fine  = rng.random((S,S)).astype(np.float32)
fine  = periodic_blur(fine, 0.8)
mid   = periodic_blur(rng.random((S,S)).astype(np.float32), 3.0)
h = 0.72*(fine-fine.mean()) + 0.28*(mid-mid.mean())
h = h/ (np.abs(h).max()+1e-6)

# Normal map à partir de la hauteur (dérivées périodiques)
STR = 2.6
dx = (np.roll(h,-1,1)-np.roll(h,1,1))*0.5*STR
dy = (np.roll(h,-1,0)-np.roll(h,1,0))*0.5*STR
nz = np.ones_like(h)
n = np.stack([-dx,-dy,nz],-1)
n /= np.linalg.norm(n,axis=-1,keepdims=True)
Image.fromarray(((n*0.5+0.5)*255).astype(np.uint8)).save('tex-normal.png')

# metallicRoughness : G = rugosité (variation), B = métal (constant)
rough = np.clip(0.46 + 0.16*(mid-mid.mean())/ (np.abs(mid-mid.mean()).max()+1e-6) + 0.05*(fine-fine.mean()), 0.2, 0.85)
mr = np.zeros((S,S,3), np.uint8)
mr[...,1] = (rough*255).astype(np.uint8)
mr[...,2] = 255                       # multiplié par metallicFactor
Image.fromarray(mr).save('tex-mr.png')
print("textures ok — grain h rms %.3f, rugosité %.2f→%.2f" % (h.std(), rough.min(), rough.max()))
