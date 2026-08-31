"""Audit d'accessibilité : douze contrôles sur le DOM réellement rendu.

    python3 tools/audit-a11y.py [largeur]      # 1440 par défaut, essayer aussi 390

La liste des pages vient de `sitemap.xml`, plus `404.html`. Il faut un serveur
statique sur le port 8137 (`python3 -m http.server 8137` depuis la racine).

TROIS EXEMPTIONS SONT CÂBLÉES, et sans elles la sortie est illisible :
  - `aria-hidden` sur un élément qui porte `tabindex="-1"` est LÉGITIME : il n'est
    pas focalisable au clavier. C'est le cas du film décoratif de l'accueil ;
  - WCAG 2.5.8 exempte les liens EN PLEINE PHRASE et le lien d'évitement ;
  - une case à cocher de 20 px dont le LABEL fait 444 x 64 a une cible utile
    conforme : c'est le label qui est cliquable.
La cible sous-dimensionnée qui reste est signalée pour être passée au calcul de
l'exception d'espacement, que ce script fait aussi (cercle de 24 px de diamètre
centré sur la boîte, sans intersection avec une autre cible).
"""
import sys
import io, sys
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
LARGEUR = int(sys.argv[1]) if len(sys.argv) > 1 else 1440

JS = r"""
() => {
  const d = [];
  const nom = e => e.tagName.toLowerCase() + (e.id?'#'+e.id:'') + '.' + (e.className||'').toString().split(' ')[0];
  const visible = e => e.offsetParent !== null || e.tagName === 'BODY';

  // 1. un seul h1, pas de saut de niveau
  const titres = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(visible);
  const h1 = titres.filter(t => t.tagName === 'H1');
  if (h1.length !== 1) d.push({c:'titres', m:`${h1.length} h1`});
  for (let i=1;i<titres.length;i++){
    const a=+titres[i-1].tagName[1], b=+titres[i].tagName[1];
    if (b-a>1) d.push({c:'titres', m:`saut h${a}→h${b}`, t:titres[i].textContent.trim().slice(0,34)});
  }

  // 2. images : alt présent
  [...document.images].forEach(i=>{
    if (!i.hasAttribute('alt')) d.push({c:'img-alt', m:'alt absent', t:i.src.split('/').pop().slice(0,34)});
  });

  // 3. contrôles de formulaire : nom accessible
  document.querySelectorAll('input,select,textarea').forEach(e=>{
    if (e.type==='hidden' || !visible(e)) return;
    const n = (e.labels&&e.labels.length) || e.getAttribute('aria-label') || e.getAttribute('aria-labelledby')
              || e.getAttribute('title') || (e.type==='submit'&&e.value);
    if (!n) d.push({c:'champ-sans-nom', m:e.type, t:nom(e)});
  });

  // 4. liens et boutons : nom accessible
  document.querySelectorAll('a[href],button').forEach(e=>{
    if (!visible(e) && !e.classList.contains('skip-nav')) return;
    const txt=(e.textContent||'').trim();
    const n = txt || e.getAttribute('aria-label') || e.getAttribute('title')
              || [...e.querySelectorAll('img[alt]')].some(i=>i.alt.trim());
    if (!n) d.push({c:'lien-sans-nom', m:e.tagName.toLowerCase(), t:nom(e)});
  });

  // 5. références ARIA orphelines
  ['aria-labelledby','aria-controls','aria-describedby','for'].forEach(a=>{
    document.querySelectorAll('['+a+']').forEach(e=>{
      (e.getAttribute(a)||'').split(/\s+/).filter(Boolean).forEach(id=>{
        if(!document.getElementById(id)) d.push({c:'aria-orphelin', m:a+'="'+id+'"', t:nom(e)});
      });
    });
  });

  // 6. aria-hidden sur un élément focalisable
  document.querySelectorAll('[aria-hidden="true"]').forEach(e=>{
    // `tabindex="-1"` retire de l'ordre de tabulation : aria-hidden y est légitime.
    if(e.getAttribute('tabindex')==='-1') return;
    const f=e.matches('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])')
      || e.querySelector('a[href],button,input,select,textarea,[tabindex]:not([tabindex="-1"])');
    if(f && visible(e)) d.push({c:'aria-hidden-focalisable', m:'', t:nom(e)});
  });

  // 7. role=list sans listitem
  document.querySelectorAll('[role="list"]').forEach(e=>{
    const n=[...e.children].filter(c=>c.getAttribute('role')==='listitem'||c.tagName==='LI').length;
    if(!n) d.push({c:'liste-sans-item', m:e.children.length+' enfants', t:nom(e)});
  });

  // 8. repères : un main, un header, un footer
  ['main','header[role="banner"]','footer[role="contentinfo"]'].forEach(s=>{
    const n=document.querySelectorAll(s).length;
    if(n!==1) d.push({c:'reperes', m:s+' × '+n});
  });

  // 9. langue du document
  const lg=document.documentElement.lang;
  if(!lg) d.push({c:'lang', m:'absent'});

  // 10. titre de document
  if(!document.title.trim()) d.push({c:'title', m:'vide'});

  // 11. tableaux : en-têtes
  document.querySelectorAll('table').forEach(t=>{
    if(!t.querySelector('th')) d.push({c:'tableau', m:'aucun th', t:nom(t)});
    t.querySelectorAll('th').forEach(th=>{ if(!th.getAttribute('scope')) d.push({c:'tableau', m:'th sans scope', t:(th.textContent||'').trim().slice(0,24)}); });
  });

  // 12. WCAG 2.5.8 : une cible sous-dimensionnée n'est un défaut que si
  // l'exception d'ESPACEMENT échoue aussi. On la calcule : un cercle de 24 px de
  // diamètre centré sur la boîte ne doit intersecter ni une autre cible, ni le
  // cercle d'une autre cible sous-dimensionnée. Sans ce calcul, la sonde liste les
  // liens de la barre de navigation (18 px de haut) qui sont pourtant conformes.
  const cibles=[...document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea')]
    .filter(visible).map(e=>({e, r:e.getBoundingClientRect()})).filter(x=>x.r.width>0&&x.r.height>0);
  for(const p of cibles){
    if(p.r.width>=24 && p.r.height>=24) continue;
    if(p.e.classList.contains('skip-nav')) continue;
    if(p.e.labels && p.e.labels.length){
      const rl=p.e.labels[0].getBoundingClientRect();
      if(rl.width>=24 && rl.height>=24) continue;      // le label est la cible
    }
    const par=p.e.parentElement;
    if(p.e.tagName==='A' && par && (par.textContent||'').trim().length > (p.e.textContent||'').trim().length+12)
      continue;                                        // lien en pleine phrase, exempté
    const cx=p.r.left+p.r.width/2, cy=p.r.top+p.r.height/2;
    let pire=Infinity, voisin=null;
    for(const q of cibles){
      if(q.e===p.e) continue;
      const dx=Math.max(q.r.left-cx,0,cx-q.r.right), dy=Math.max(q.r.top-cy,0,cy-q.r.bottom);
      const seuil=(q.r.width<24||q.r.height<24)?24:12;
      const m=Math.hypot(dx,dy)-seuil;
      if(m<pire){pire=m; voisin=(q.e.textContent||q.e.tagName).trim().slice(0,18);}
    }
    if(pire<0) d.push({c:'cible 2.5.8', m:Math.round(p.r.width)+'x'+Math.round(p.r.height)+' marge '+Math.round(pire),
                       t:(p.e.textContent||p.e.getAttribute('aria-label')||'').trim().slice(0,26)});
  }
  return d;
}
"""
with sync_playwright() as p:
    b = p.chromium.launch()
    total = {}
    injoignables = []
    for path in PAGES:
        pg = b.new_page(viewport={'width': LARGEUR, 'height': 900}, reduced_motion='reduce')
        try: pg.goto('http://127.0.0.1:8137/' + path, wait_until='load', timeout=25000)
        except Exception:
            # UN GARDE-FOU QUI NE CRIE PAS NE PROTEGE PAS. Sans ce compteur, l'outil
            # annonçait « aucun défaut » alors qu'il n'avait rien chargé du tout :
            # un audit lancé sans serveur local rendait exactement la même
            # conclusion qu'un audit réussi. Relevé par l'audit RosoAI n°5, §6.5.
            injoignables.append(path)
            pg.close()
            continue
        pg.evaluate("""async()=>{const h=document.body.scrollHeight;
          for(let y=0;y<h;y+=600){window.scrollTo({top:y,behavior:'instant'});await new Promise(r=>setTimeout(r,55));}
          window.scrollTo({top:0,behavior:'instant'});await new Promise(r=>setTimeout(r,500));}""")
        for x in pg.evaluate(JS):
            k = (x['c'], x.get('m',''), x.get('t',''))
            total.setdefault(k, []).append(path)
        pg.close()
    b.close()
lues = len(PAGES) - len(injoignables)
if injoignables:
    print(f"\n  ECHEC : {len(injoignables)} page(s) sur {len(PAGES)} n'ont pas pu etre chargees.")
    print("  Le resultat ci-dessous ne veut RIEN dire. Verifier que le serveur local")
    print("  tourne sur le port 8137, depuis la racine du depot :")
    print("     python3 -m http.server 8137")
    for x in injoignables[:8]: print(f"     - {x}")
    sys.exit(2)

print(f"  {LARGEUR} px · {lues} page(s) lue(s) sur {len(PAGES)} · {len(total)} type(s) de constat\n")
if not total: print('    aucun défaut')
for (c,m,t), pages in sorted(total.items()):
    print(f"   {c:24s} {m[:34]:34s} {t[:30]:30s} ({len(pages)} page(s)) {pages[0] if len(pages)<3 else ''}")
