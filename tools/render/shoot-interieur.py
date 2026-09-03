# -*- coding: utf-8 -*-
"""Rend le film « ce qu'il y a à l'intérieur » de la fiche technique.

    FFMPEG=~/ffbin/ffmpeg python3 tools/render/shoot-interieur.py

Écrit  : assets/video/qbot-interieur.mp4        (le film, ~3,4 s, sans son)
         assets/img/qbot-interieur-poster.jpg   (sa DERNIÈRE image)

Le boîtier tourne lentement, la caméra se rapproche, et tout ce qui n'est pas la
carte devient translucide : à la fin il ne reste de solide que le nano-ordinateur,
en place au fond du bac. Le film s'arrête là et n'est pas bouclé, donc la dernière
image tient l'écran. C'est ce que le client a demandé le 2026-09-03 à la place
d'une photo de l'intérieur, qui n'existe pas : « reprendre le bout de l'animation
qui montre le raspberry en 3D et le freezer au moment où on voit le raspberry ».

## Pourquoi un film et non un `<model-viewer>` dans la page

La visionneuse pèse 1 043 Ko, le modèle 714 et le décodeur Draco 279, soit 2 Mo
sur une page qui porte déjà le film de démonstration. Le film ci-dessous fait deux
cents kilooctets et ne demande aucun script de plus : le module 18 de `main.js`
sait déjà demander un film à l'approche de sa section et le mettre en pause hors
champ. La contrepartie est qu'il faut le régénérer quand le modèle change, ce que
ce script fait en une commande.

## L'AFFICHE EST LA DERNIÈRE IMAGE, ET C'EST STRUCTUREL

Sans JavaScript, en mouvement réduit, en économiseur de données ou sur connexion
lente, le module 18 ne charge rien : c'est l'affiche qui reste. Elle doit donc
être l'état d'ARRIVÉE, pas une image de début — sinon ces visiteurs voient un
boîtier fermé sous un titre qui parle de ce qu'il y a dedans. C'est la règle du
dépôt (l'état au repos est un état complet) appliquée à un média.

## Les pièges de cette chaîne, tous rencontrés

- **le fond est peint dans le film**, `#121212`, parce que H.264 n'a pas de couche
  alpha. C'est exactement la couleur de fond de la section, relevée dans le
  navigateur (`rgb(18, 18, 18)`) et opaque : aucune couture possible. Si la
  section changeait de fond, il faudrait relancer ce script. Les pages à halo
  dérivant (`.orbz`) rendraient l'exercice impossible, la fiche technique n'en a
  pas.
- **la taille est celle du cadre, mesurée** : `.specs__image` fait au plus
  640 x 501 px (à 2560 px de large), donc 1280 x 1000 en densité 2. Rendre plus
  grand ne montrerait rien de plus et alourdirait le film. Les deux dimensions
  sont paires, ce qu'exige `yuv420p`.
- **le tri des matériaux se fait par le NOM** : tout ce qui n'est pas `pi-*`
  s'efface. Même règle que `scrolly.js`, même raison.
- **`animation-name="Explode"` reste sur la balise** même si le clip n'avance
  pas : sans lui `currentTime` ne fait rien, et le smartphone du modèle, dont
  l'échelle est nulle avant sa première keyframe, redeviendrait visible.
- **le Chromium de Playwright LIT le H.264 mais ne le rend pas en pixels
  relisibles** : la lecture avance (`currentTime`, `ended`), donc le comportement
  du module 18 se contrôle très bien avec lui, mais une capture d'écran du
  lecteur revient noire. Pour VOIR le film, c'est WebKit.
"""
import os, shutil, subprocess, sys, tempfile, threading
import http.server, socketserver

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(os.path.dirname(HERE))
FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')
PORT = int(os.environ.get('PORT', '8791'))

W, H = 1280, 1000            # le cadre mesuré, en densité 2
FPS = 30
DUREE = 3.4                  # secondes
FOND = '#121212'             # fond de la section, relevé dans le navigateur

# Les deux poses, et les fenêtres d'interpolation en fraction de la durée.
DEPART = dict(theta=-18, phi=74, r=0.62, ty=0.073, tz=0.000, alpha=1.00)
ARRIVEE = dict(theta=-52, phi=60, r=0.32, ty=0.024, tz=0.030, alpha=0.26)
CAM = (0.05, 0.92)           # la caméra part et arrive au repos
FADE = (0.30, 0.80)          # le fondu commence une fois le mouvement engagé

PAGE = """<!doctype html><meta charset=utf-8>
<style>html,body{margin:0;background:%(fond)s}
model-viewer{width:%(w)dpx;height:%(h)dpx;background:%(fond)s;--poster-color:transparent}</style>
<script type="module" src="/assets/js/model-viewer-4.3.1.min.js"></script>
<model-viewer id="mv" src="/assets/models/qbot.glb" environment-image="neutral"
  exposure="0.8" shadow-intensity="1.3" shadow-softness="0.75" field-of-view="30deg"
  camera-orbit="%(th)fdeg %(ph)fdeg %(r)fm" camera-target="0m %(ty)fm %(tz)fm"
  animation-name="Explode" interaction-prompt="none" disable-zoom disable-pan></model-viewer>
<script type="module">
  const mv = document.getElementById('mv');
  await new Promise(r => mv.addEventListener('load', r, {once: true}));
  mv.pause(); mv.currentTime = 0;
  const fade = mv.model.materials
    .filter(m => !/^pi-/.test(m.name || ''))
    .map(m => ({m, rgb: m.pbrMetallicRoughness.baseColorFactor.slice(0, 3), blend: false}));
  if (!fade.length) throw new Error('aucun materiau a effacer');
  window.__pose = (th, ph, r, ty, tz, a) => {
    mv.cameraOrbit = `${th}deg ${ph}deg ${r}m`;
    mv.cameraTarget = `0m ${ty}m ${tz}m`;
    for (const e of fade) {
      const blend = a < 0.99;
      if (blend !== e.blend) {
        e.m.setAlphaMode(blend ? 'BLEND' : 'OPAQUE');
        if (e.m.setDoubleSided) e.m.setDoubleSided(!blend);
        e.blend = blend;
      }
      e.m.pbrMetallicRoughness.setBaseColorFactor([...e.rgb, blend ? a : 1]);
    }
    return new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  };
  window.__ready = true;
</script>
"""


def lisse(x):
    """Smootherstep : dérivée ET dérivée seconde nulles aux deux bouts. La
    dérivée seconde compte ici, c'est elle qui évite qu'on voie le mouvement
    « prendre » au démarrage et « buter » à l'arrivée sur un film aussi court."""
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def rampe(u, borne):
    a, b = borne
    return lisse((u - a) / (b - a)) if b > a else 0.0


def serveur():
    os.chdir(RACINE)
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a, **k: None

    class S(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True
    srv = S(('127.0.0.1', PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def capturer(page, dossier, n):
    """Écrit la page de rendu à la racine, capture les n images, puis retire la
    page. Sortie de `main()` pour que le corps de celle-ci reste lisible."""
    from playwright.sync_api import sync_playwright
    with open(page, 'w', encoding='utf-8') as f:
        f.write(PAGE % dict(fond=FOND, w=W, h=H, th=DEPART['theta'], ph=DEPART['phi'],
                            r=DEPART['r'], ty=DEPART['ty'], tz=DEPART['tz']))
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        erreurs = []
        pg.on('console', lambda m: erreurs.append(m.text) if m.type == 'error' else None)
        pg.goto(f'http://127.0.0.1:{PORT}/_interieur.html', wait_until='load')
        pg.wait_for_function('window.__ready', timeout=90000)
        for k in range(n):
            u = k / (n - 1)
            c, a = rampe(u, CAM), rampe(u, FADE)
            pose = [DEPART[cle] + (ARRIVEE[cle] - DEPART[cle]) * (a if cle == 'alpha' else c)
                    for cle in ('theta', 'phi', 'r', 'ty', 'tz', 'alpha')]
            pg.evaluate('x => window.__pose(...x)', pose)
            pg.locator('#mv').screenshot(path=os.path.join(dossier, f'f{k:04d}.png'))
            if k % 20 == 0 or k == n - 1:
                print(f"  image {k+1}/{n} : theta {pose[0]:6.1f}  r {pose[2]:.3f}  "
                      f"opacité {pose[5]:.2f}")
        assert not erreurs, f'erreurs console : {erreurs[:3]}'
        b.close()


def main():
    if shutil.which(FFMPEG) is None and not os.path.exists(os.path.expanduser(FFMPEG)):
        raise SystemExit(
            "ffmpeg introuvable. Il n'est pas installé sur cette machine et il n'a pas à\n"
            "l'être : un binaire statique arm64 suffit, posé dans un dossier de travail.\n"
            "  curl -sSL -o ff.zip https://www.osxexperts.net/ffmpeg9arm.zip\n"
            "  unzip -q ff.zip -d ffbin/ && xattr -d com.apple.quarantine ffbin/ffmpeg\n"
            "  FFMPEG=$PWD/ffbin/ffmpeg python3 tools/render/shoot-interieur.py")

    page = os.path.join(RACINE, '_interieur.html')
    # FRAMES=<dossier> garde les images et saute le rendu si elles sont déjà là.
    # C'est ce qui permet de comparer plusieurs encodages sans refaire les cent
    # captures, qui coûtent une minute et demie.
    garde = os.environ.get('FRAMES')
    tmp = garde or tempfile.mkdtemp(prefix='interieur-')
    if garde:
        os.makedirs(tmp, exist_ok=True)
    n = int(round(DUREE * FPS))
    srv = serveur()
    try:
        if garde and os.path.exists(os.path.join(tmp, f'f{n-1:04d}.png')):
            print(f"  {n} images déjà présentes dans {tmp}, rendu sauté")
        else:
            capturer(page, tmp, n)

        # ── l'affiche : la dernière image, celle qui montre la carte ─────────
        from PIL import Image
        aff = os.path.join(RACINE, 'assets', 'img', 'qbot-interieur-poster.jpg')
        # Qualité 82 et non 88 : l'affiche est demandée par l'attribut `poster`,
        # donc AU CHARGEMENT de la page, alors que le film ne part qu'à l'approche
        # de la section. C'est le seul octet de cette chaîne que tout le monde
        # paie. Elle ne s'affiche jamais au-delà de 640 px (1280 en densité 2,
        # soit sa taille native) : mesuré, 82 et 88 sont indiscernables une fois
        # réduites de moitié, pour 45 Ko de moins.
        Image.open(os.path.join(tmp, f'f{n-1:04d}.png')).convert('RGB').save(
            aff, 'JPEG', quality=82, optimize=True, progressive=True)

        # ── le film ─────────────────────────────────────────────────────────
        out = os.path.join(RACINE, 'assets', 'video', 'qbot-interieur.mp4')
        cmd = [os.path.expanduser(FFMPEG), '-y', '-framerate', str(FPS),
               '-i', os.path.join(tmp, 'f%04d.png'),
               '-an',                              # aucune piste audio à porter
               '-c:v', 'libx264', '-preset', 'slow', '-crf', os.environ.get('CRF', '28'),
               '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.0',
               '-movflags', '+faststart', out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit('ffmpeg a échoué :\n' + r.stderr[-2000:])
        print(f"\n{os.path.relpath(out, RACINE)} : {os.path.getsize(out)/1e3:.0f} Ko "
              f"({n} images, {DUREE} s, {W}x{H})")
        print(f"{os.path.relpath(aff, RACINE)} : {os.path.getsize(aff)/1e3:.0f} Ko")
        print("\nEnsuite : node tools/bump-assets.mjs (le film et l'affiche sont "
              "réécrits sous le même nom)")
    finally:
        srv.shutdown()
        if not garde:
            shutil.rmtree(tmp, ignore_errors=True)
        if os.path.exists(page):
            os.remove(page)


if __name__ == '__main__':
    main()
