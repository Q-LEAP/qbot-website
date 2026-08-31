"""Audit de visibilité : métadonnées, hreflang, données structurées, plan du site.

    python3 tools/audit-visibilite.py

Serveur statique attendu sur le port 8137. La liste des pages vient de
`sitemap.xml`, plus `404.html`.

`404.html` EST EXEMPTÉE de canonical, de hreflang et des métadonnées sociales :
une page d'erreur ne se canonicalise pas et ne se partage pas. Sans cette
exemption elle produit 15 faux constats à elle seule.
"""
import sys
import io, json, re, os
from playwright.sync_api import sync_playwright


def pages_du_plan():
    """Les pages à auditer : celles du plan du site, plus la page d'erreur."""
    import os, re
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sm = io.open(os.path.join(racine, 'sitemap.xml'), encoding='utf-8').read()
    out = []
    for l in re.findall(r'<loc>https://q-bot\.eu/(.*?)</loc>', sm):
        out.append((l or 'index.html') if not l.endswith('/') else l + 'index.html')
    return out + ['404.html']

PAGES = pages_du_plan()
JS = r"""
() => {
  const g=(s,a)=>{const e=document.querySelector(s);return e?e.getAttribute(a||'content'):null;};
  const jl=[...document.querySelectorAll('script[type="application/ld+json"]')].map(s=>s.textContent);
  return {
    titre: (document.title||'').trim(),
    desc: g('meta[name="description"]'),
    robots: g('meta[name="robots"]'),
    canonical: g('link[rel="canonical"]','href'),
    hreflang: [...document.querySelectorAll('link[rel="alternate"][hreflang]')]
                .map(l=>[l.getAttribute('hreflang'), l.getAttribute('href')]),
    og: {t:g('meta[property="og:title"]'), d:g('meta[property="og:description"]'),
         u:g('meta[property="og:url"]'), i:g('meta[property="og:image"]'),
         w:g('meta[property="og:image:width"]'), h:g('meta[property="og:image:height"]'),
         a:g('meta[property="og:image:alt"]'), l:g('meta[property="og:locale"]'),
         s:g('meta[property="og:site_name"]'), ty:g('meta[property="og:type"]')},
    tw: {c:g('meta[name="twitter:card"]'), t:g('meta[name="twitter:title"]'),
         d:g('meta[name="twitter:description"]'), i:g('meta[name="twitter:image"]')},
    lang: document.documentElement.lang,
    jsonld: jl,
    h1: [...document.querySelectorAll('h1')].map(h=>h.textContent.trim()).slice(0,3),
  };
}
"""
REQ={'Organization':['name','url'],'Product':['name','description','image','brand'],
     'BlogPosting':['headline','datePublished','author','image'],'FAQPage':['mainEntity'],
     'BreadcrumbList':['itemListElement'],'WebSite':['name','url'],'Person':['name'],
     'TechArticle':['headline','datePublished','author','image']}
pb=[]
titres={}
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':1440,'height':900})
    injoignables=[]
    for path in PAGES:
        # Meme garde-fou que dans audit-a11y : sans lui, une page non chargee
        # passait pour une page sans defaut. Audit RosoAI n5, §6.5.
        try: pg.goto('http://127.0.0.1:8137/'+path, wait_until='load', timeout=25000)
        except Exception: injoignables.append(path); continue
        d=pg.evaluate(JS)
        A=lambda m: pb.append((path,m))
        err404 = (path == '404.html')
        if not d['titre']: A('titre vide')
        elif len(d['titre'])>62: A(f"titre {len(d['titre'])} c")
        if not d['desc']: A('description absente')
        elif len(d['desc'])>158: A(f"description {len(d['desc'])} c")
        if d['titre'] in titres: A(f"titre en doublon avec {titres[d['titre']]}")
        else: titres[d['titre']]=path
        if 'noindex' not in (d['robots'] or ''): A('pas de noindex (pré-lancement)')
        if not d['canonical']:
            if not err404: A('canonical absent')
        elif not d['canonical'].startswith('https://q-bot.eu/'): A('canonical non absolu')
        if not err404:
            hl=dict(d['hreflang'])
            if not hl: A('aucun hreflang')
            else:
                if 'x-default' not in hl: A('x-default absent')
                auto = d['canonical'] in hl.values()
                if not auto: A('hreflang non auto-référent')
                for c,h in d['hreflang']:
                    if not h.startswith('https://'): A(f'hreflang {c} non absolu')
        if not err404:
            for k,v in d['og'].items():
                if not v: A(f'og manquant: {k}')
            for k,v in d['tw'].items():
                if not v: A(f'twitter manquant: {k}')
        if not d['lang']: A('lang absent')
        if len(d['h1'])!=1: A(f"{len(d['h1'])} h1")
        if 'Q-Bot' in d['titre'] and 'Q-Leap' not in d['titre'] and 'LuxTrust' not in d['titre']:
            A('titre : « Q-Bot » seul')
        for txt in d['jsonld']:
            try: o=json.loads(txt)
            except Exception as e: A('JSON-LD invalide: '+str(e)[:40]); continue
            for x in (o if isinstance(o,list) else [o]):
                t=x.get('@type'); t=t[0] if isinstance(t,list) else t
                if t in REQ:
                    mq=[k for k in REQ[t] if k not in x]
                    if mq: A(f'{t} manque {",".join(mq)}')
                if 'offers' in x: A(f'{t} porte encore offers')
    b.close()

# plan du site
sm=io.open('sitemap.xml',encoding='utf-8').read()
locs=re.findall(r'<loc>(.*?)</loc>', sm)
for l in locs:
    rel=l.replace('https://q-bot.eu/','') or 'index.html'
    if rel.endswith('/'): rel+='index.html'
    if not os.path.exists(rel): pb.append(('sitemap', f'{l} → fichier absent'))
if len(re.findall(r'<lastmod>', sm))!=len(locs): pb.append(('sitemap','lastmod manquant sur certaines URL'))
if sm.count('hreflang')< len(locs)*3: pb.append(('sitemap','paires hreflang incomplètes'))

if injoignables:
    print(f"\n  ECHEC : {len(injoignables)} page(s) sur {len(PAGES)} n'ont pas pu etre chargees.")
    print("  Le resultat ci-dessous ne veut RIEN dire. Lancer un serveur local :")
    print("     python3 -m http.server 8137")
    for x in injoignables[:8]: print(f"     - {x}")
    sys.exit(2)

print(f"  {len(PAGES)-len(injoignables)} page(s) lue(s) sur {len(PAGES)} · {len(pb)} constat(s)\n")
for path,m in pb: print(f"   {path:44s} {m}")
if not pb: print("    aucun défaut")
