import asyncio, json
from playwright.async_api import async_playwright
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
        b=await p.chromium.launch(headless=False)
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
    json.dump(out, open('legal/plein.json','w'), ensure_ascii=False, indent=1)
    print("écrit legal/plein.json")
asyncio.run(main())
