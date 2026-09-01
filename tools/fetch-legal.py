"""Relève les quatre pages légales du live et écrit tools/legal-source.json.

    python3 tools/fetch-legal.py
    python3 tools/gen-legal.py       # ensuite, dans cet ordre

TROIS DÉFAUTS CORRIGÉS LE 2026-09-01, tous trouvés en vérifiant que les outils du
dépôt tournent encore. Aucun contrôle ne l'avait fait depuis sa création :

  - il écrivait « legal/plein.json », dans un dossier qui n'existe pas, alors que
    « gen-legal.py » lit « tools/legal-source.json ». LES DEUX BOUTS DE LA CHAÎNE
    NE SE PARLAIENT PAS : relancer la chaîne documentée échouait au premier pas,
    et aurait de toute façon écrit à côté ;
  - il lançait le navigateur en mode FENÊTRÉ, contre la règle du 2026-08-25 (mode
    invisible par défaut, fenêtré seulement pour chasser un artefact de rendu 3D).
    Ici on lit le DOM : le mode invisible donne le même résultat et n'ouvre pas
    une fenêtre sur la machine du client ;
  - il écrasait le relevé sans sauvegarde.

ET IL A UNE DATE DE PÉREMPTION : il relève le WordPress de q-bot.eu, qui sera
supprimé le jour de la bascule. Après quoi « tools/legal-source.json » est le
SEUL exemplaire du texte d'origine, et il le restera. Ne pas le perdre, d'autant
que « gen-legal.py » en dérive maintenant un texte amendé.
"""
import asyncio, json, os, shutil
from playwright.async_api import async_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, 'tools', 'legal-source.json')
JOBS = [("https://q-bot.eu/conditions-vente/", "fr-FR", "cv-fr"),
        ("https://q-bot.eu/confidentialite/",  "fr-FR", "conf-fr"),
        ("https://q-bot.eu/en/privacy/",       "en-GB", "priv-en"),
        ("https://q-bot.eu/en/terms-and-conditions-of-sale/", "en-GB", "cv-en")]
JS = """() => {
  const vis = el => el.offsetParent !== null && getComputedStyle(el).visibility !== 'hidden';
  const out = [];
  document.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li').forEach(el => {
    if (!vis(el)) return;
    if (el.querySelector('h1,h2,h3,h4,h5,h6,p,li')) return;
    const t = el.innerText.replace(/[ \\t]+/g,' ').trim();
    if (!t) return;
    const cs = getComputedStyle(el);
    out.push({tag: el.tagName.toLowerCase(), txt: t, html: el.innerHTML.trim(),
              w: parseInt(cs.fontWeight), fs: Math.round(parseFloat(cs.fontSize))});
  });
  return out;
}"""
async def main():
    out={}
    async with async_playwright() as p:
        b=await p.chromium.launch()   # invisible : on lit le DOM, pas des pixels
        for url, loc, name in JOBS:
            ctx=await b.new_context(viewport={'width':1440,'height':900}, locale=loc,
                                    extra_http_headers={'Accept-Language': loc+',en;q=0.8'})
            pg=await ctx.new_page()
            await pg.goto(url, wait_until='networkidle', timeout=60000)
            await pg.wait_for_timeout(1500)
            out[name]=await pg.evaluate(JS)
            print(name, len(out[name]), "blocs")
            await ctx.close()
        await b.close()
    # LE RELEVÉ PRÉCÉDENT EST GARDÉ. Le live disparaît à la bascule : un relevé
    # raté (redirection de langue, page vide) ne doit pas effacer le seul
    # exemplaire du texte d'origine.
    if os.path.exists(SORTIE):
        shutil.copy2(SORTIE, SORTIE + '.avant')
        print("sauvegarde :", os.path.relpath(SORTIE, RACINE) + '.avant')
    manque = [n for n, b in out.items() if len(b) < 20]
    assert not manque, f"relevé trop court pour {manque} : rien n'est écrit"
    with open(SORTIE, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("écrit", os.path.relpath(SORTIE, RACINE))
asyncio.run(main())
