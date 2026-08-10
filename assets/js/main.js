'use strict';

/* ════════════════════════════════════════
   THÈME — le site n'a plus qu'un seul thème (sombre).
   data-theme="dark" est écrit en dur dans le <html> de chaque page ;
   il n'y a plus ni bouton de bascule ni script d'init dans le <head>.
════════════════════════════════════════ */

/* ════════════════════════════════════════
   1. NAVIGATION — sticky shadow + mobile + smart hide
════════════════════════════════════════ */
const nav       = document.querySelector('.nav');
const navToggle = document.querySelector('.nav__toggle');
const navMenu   = document.querySelector('.nav__menu');

// ── Ombre au scroll ──
window.addEventListener('scroll', () => {
  nav?.classList.toggle('scrolled', window.scrollY > 10);
}, { passive: true });

// ── Smart hide / reveal au scroll ──
{
  let lastY    = -1;   // -1 = non initialisé ; évite un faux "scroll down" à la restauration
  let ticking  = false;

  function handleNavScroll() {
    const y    = window.scrollY;
    const navH = nav ? nav.offsetHeight : 72;

    if (lastY < 0) { lastY = y; ticking = false; return; } // 1er appel : init seulement

    const delta = y - lastY;

    if (!navMenu?.classList.contains('open')) {
      if (delta > 0 && y > navH) {
        // Scrolle vers le bas → masquer
        nav?.classList.add('nav--hidden');
      } else if (delta < 0 || y <= navH) {
        // Scrolle vers le haut ou en haut de page → révéler
        nav?.classList.remove('nav--hidden');
      }
    }
    lastY   = y;
    ticking = false;
  }

  window.addEventListener('scroll', () => {
    if (!ticking) { requestAnimationFrame(handleNavScroll); ticking = true; }
  }, { passive: true });

  // Révèle si la souris s'approche du haut (desktop uniquement)
  document.addEventListener('mousemove', (e) => {
    if (e.clientY < 72) nav?.classList.remove('nav--hidden');
  }, { passive: true });
}

// ── Toggle mobile ──
navToggle?.addEventListener('click', () => {
  const isOpen = navMenu.classList.toggle('open');
  navToggle.setAttribute('aria-expanded', String(isOpen));
  if (isOpen) nav?.classList.remove('nav--hidden'); // toujours visible quand menu ouvert
});

// Ferme au clic extérieur
document.addEventListener('click', (e) => {
  if (navMenu?.classList.contains('open') && !nav?.contains(e.target)) {
    navMenu.classList.remove('open');
    navToggle?.setAttribute('aria-expanded', 'false');
  }
});

// Ferme au resize
window.addEventListener('resize', () => {
  if (window.innerWidth > 768) {
    navMenu?.classList.remove('open');
    navToggle?.setAttribute('aria-expanded', 'false');
  }
}, { passive: true });

// Touche Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && navMenu?.classList.contains('open')) {
    navMenu.classList.remove('open');
    navToggle?.setAttribute('aria-expanded', 'false');
    navToggle?.focus();
  }
});

/* ════════════════════════════════════════
   2. LIEN NAV ACTIF
════════════════════════════════════════ */
{
  const pathParts  = window.location.pathname.split('/');
  const currentFile = pathParts[pathParts.length - 1] || 'index.html';

  document.querySelectorAll('.nav__link').forEach(link => {
    const href     = link.getAttribute('href') || '';
    const linkFile = href.split('/').pop() || 'index.html';
    if (linkFile === currentFile) link.classList.add('active');
  });
}

/* ════════════════════════════════════════
   3. FAQ ACCORDION — hauteur dynamique + aria
════════════════════════════════════════ */
document.querySelectorAll('.faq-item__question').forEach(btn => {
  // Initialise aria-expanded
  btn.setAttribute('aria-expanded', 'false');

  btn.addEventListener('click', () => {
    const item   = btn.closest('.faq-item');
    const isOpen = item.classList.contains('open');

    // Ferme tous les items ouverts
    document.querySelectorAll('.faq-item.open').forEach(openItem => {
      openItem.classList.remove('open');
      openItem.querySelector('.faq-item__question')
              ?.setAttribute('aria-expanded', 'false');
      const ans = openItem.querySelector('.faq-item__answer');
      if (ans) ans.style.maxHeight = '0';
    });

    // Ouvre le cliqué s'il était fermé
    if (!isOpen) {
      item.classList.add('open');
      btn.setAttribute('aria-expanded', 'true');

      const answer = item.querySelector('.faq-item__answer');
      if (answer) {
        /* scrollHeight du conteneur entier (pas juste firstElementChild) :
           une réponse avec plusieurs <p>/<ul> derrière voyait son max-height
           calé sur le premier enfant seulement, tronquant tout le reste. */
        answer.style.maxHeight = answer.scrollHeight + 'px';
      }
    }
  });
});

/* ════════════════════════════════════════
   4. SCROLL REVEAL — variantes typées + stagger
   Trois familles d'éléments, trois façons d'arriver
   (cf. « MOTION SYSTEM » dans style.css) :
     media  → masque qui remonte + dézoom  (images, vidéo)
     group  → le conteneur ne bouge pas, ses enfants s'enchaînent
              (en-têtes de section, colonnes de texte)
     card   → montée + léger rapprochement (défaut : cartes, items)
   Le type n'est PAS écrit dans le HTML : les 24 pages restent inchangées,
   la table ci-dessous est la seule source de vérité.
════════════════════════════════════════ */
if ('IntersectionObserver' in window) {
  /* Éléments qui portent DÉJÀ .reveal dans le HTML (pages d'articles de blog :
     .article-header, .article-body, .sidebar-card, .article-cta…).
     À relever AVANT que ce module ne pose ses propres classes, sinon la
     requête ramènerait aussi les éléments qu'il vient de marquer.

     Sans ceci, ces éléments restent à opacity:0 pour toujours : la classe
     .reveal les cache, mais aucun observer ne leur ajoute jamais .is-visible
     puisqu'ils ne figurent pas dans la table ci-dessous — le corps entier de
     blog/automatiser-2fa-tests.html et en/blog/automate-2fa.html était ainsi
     invisible. Les récupérer ici les remet dans le circuit. */
  const preMarked = Array.from(document.querySelectorAll('.reveal'));

  /* Ordre significatif : le premier motif qui matche gagne, donc les
     sélecteurs les plus spécifiques d'abord. */
  const REVEAL_MAP = [
    ['media', [
      '.intro__image',
      '.video__wrapper',
      '.blog__featured-img',
    ]],
    ['group', [
      '.section-header',
      /* Colonne de texte d'une section intro : label → titre → paragraphes
         arrivent en cascade. `:not()` écarte la colonne image du même grid. */
      '.intro__grid > div:not(.intro__image)',
    ]],
    ['card', [
      '.feature-card',
      '.faq-item',
      '.timeline-item',
      '.evo-card',
      '.product-card',
      '.stat-item',
      '.tool-tag',
      '.spec-item',
      '.contact-info__item',
      '.pricing-card',
      '.blog-card',
      '.calendly-box',
      /* Exclu de « media » : le bloc contient aussi un bouton, un masque
         clippé lui rognerait les angles (cf. .specs__image dans style.css). */
      '.specs__image',
      '.badge-lux',
      /* Exclu de « media » : un clip-path permanent sur le cadre du viewer 3D
         interférerait avec son passage en plein écran (et avec son canvas). */
      '.model-viewer-frame',
      '.contact-map',
    ]],
  ];

  const revealEls = [];
  const seen = new Set();

  REVEAL_MAP.forEach(([variant, selectors]) => {
    document.querySelectorAll(selectors.join(',')).forEach(el => {
      if (seen.has(el)) return;      // un élément ne prend qu'une variante
      seen.add(el);
      el.dataset.mxVariant = variant;
      revealEls.push(el);
    });
  });

  /* Variante « plain » pour les .reveal du HTML : montée + fondu, sans flou.
     Certains de ces blocs (.article-body) font plusieurs milliers de pixels de
     haut — y appliquer un filter coûterait une passe de flou sur toute la
     surface pour un effet invisible à cette échelle. */
  preMarked.forEach(el => {
    if (seen.has(el)) return;
    seen.add(el);
    el.dataset.mxVariant = 'plain';
    revealEls.push(el);
  });

  /* Un élément « group » dont un parent est déjà révélé en cascade serait
     animé deux fois (une fois comme enfant du groupe, une fois pour lui-même)
     et repartirait de zéro au milieu de sa propre arrivée. */
  const filtered = revealEls.filter(el =>
    !revealEls.some(other =>
      other !== el &&
      other.dataset.mxVariant === 'group' &&
      other.contains(el)
    )
  );

  // Stagger : index dans le groupe parent, max 5 (= 375 ms max)
  const parents = new Map();
  filtered.forEach(el => {
    const parent = el.parentElement;
    if (!parents.has(parent)) parents.set(parent, []);
    parents.get(parent).push(el);
  });
  parents.forEach(children => {
    children.forEach((el, i) => {
      el.style.setProperty('--stagger-i', Math.min(i, 5));
    });
  });

  // Ajoute les classes sans transition (évite le FOUC)
  filtered.forEach(el => {
    el.classList.add('reveal', 'reveal--' + el.dataset.mxVariant);
    el.style.transition = 'none';
  });

  // Double RAF : re-active les transitions après le premier paint
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      filtered.forEach(el => { el.style.transition = ''; });

      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        });
      }, { threshold: 0.08, rootMargin: '0px 0px -24px 0px' });

      filtered.forEach(el => observer.observe(el));
    });
  });
}

/* ════════════════════════════════════════
   5. COMPTEUR ANIMÉ — stats
════════════════════════════════════════ */
if ('IntersectionObserver' in window) {
  const counters = document.querySelectorAll('[data-count]');

  if (counters.length) {
    const counterObs = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;

        const el       = entry.target;
        const target   = parseFloat(el.dataset.count);
        const suffix   = el.dataset.suffix || '';
        const prefix   = el.dataset.prefix || '';
        const duration = 1400;
        const t0       = performance.now();

        const tick = (now) => {
          const progress = Math.min((now - t0) / duration, 1);
          const eased    = 1 - Math.pow(1 - progress, 3); // ease-out cubic
          el.textContent = prefix + Math.round(eased * target) + suffix;
          if (progress < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
        counterObs.unobserve(el);
      });
    }, { threshold: 0.6 });

    counters.forEach(el => counterObs.observe(el));
  }
}

/* ════════════════════════════════════════
   6. BACK TO TOP
════════════════════════════════════════ */
const backToTop = document.createElement('button');
backToTop.className = 'back-to-top';
backToTop.setAttribute(
  'aria-label',
  document.documentElement.lang === 'en' ? 'Back to top' : 'Retour en haut'
);
backToTop.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
  stroke-width="2.5" width="20" height="20" aria-hidden="true">
  <polyline points="18 15 12 9 6 15"/>
</svg>`;
document.body.appendChild(backToTop);

let rafPending = false;
window.addEventListener('scroll', () => {
  if (!rafPending) {
    requestAnimationFrame(() => {
      backToTop.classList.toggle('visible', window.scrollY > 500);
      rafPending = false;
    });
    rafPending = true;
  }
}, { passive: true });

backToTop.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

/* ════════════════════════════════════════
   11. LANGUE — préserve la position de scroll
   Stocke un ratio (scrollY / maxScroll) dans sessionStorage
   avant la navigation ; le restaure après le chargement complet.
════════════════════════════════════════ */
(function () {
  // Enregistre la position au clic sur le sélecteur de langue
  document.querySelectorAll('.nav__lang a').forEach(function (link) {
    link.addEventListener('click', function () {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      if (h > 0) {
        sessionStorage.setItem('qbot-scroll-pct', (window.scrollY / h).toFixed(5));
      }
    });
  });

  // Restaure après le chargement complet (images incluses → hauteur définitive)
  window.addEventListener('load', function () {
    var raw = sessionStorage.getItem('qbot-scroll-pct');
    if (raw === null) return;
    sessionStorage.removeItem('qbot-scroll-pct');
    var pct = parseFloat(raw);
    if (isNaN(pct) || pct <= 0) return;
    requestAnimationFrame(function () {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      if (h > 0) window.scrollTo({ top: pct * h, behavior: 'instant' });
    });
  });
}());

/* ════════════════════════════════════════
   7. UX ARTICLES — Progression + Temps de lecture + Copier code
════════════════════════════════════════ */
(function () {
  var articleBody = document.querySelector('.article-body');
  if (!articleBody) return;

  var FR = (document.documentElement.lang || 'fr').slice(0, 2) !== 'en';

  /* ── Temps de lecture estimé ── */
  var wordCount = (articleBody.textContent || '').trim().split(/\s+/).length;
  var minutes   = Math.max(1, Math.round(wordCount / 200));
  var metaEl    = document.querySelector('.article-meta');
  if (metaEl) {
    var rt = document.createElement('span');
    rt.className = 'reading-time';
    rt.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"' +
      ' stroke-width="2" aria-hidden="true">' +
        '<circle cx="12" cy="12" r="10"/><polyline points="12,6 12,12 16,14"/>' +
      '</svg>' +
      (FR ? minutes + ' min de lecture' : minutes + ' min read');
    metaEl.appendChild(rt);
  }

  /* ── Barre de progression de lecture ── */
  var bar = document.createElement('div');
  bar.className = 'reading-progress';
  bar.setAttribute('role', 'progressbar');
  bar.setAttribute('aria-valuemin', '0');
  bar.setAttribute('aria-valuemax', '100');
  bar.setAttribute('aria-valuenow', '0');
  bar.setAttribute('aria-label', FR ? 'Progression de lecture' : 'Reading progress');
  document.body.prepend(bar);

  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      var top  = window.scrollY;
      var h    = document.documentElement.scrollHeight - window.innerHeight;
      var pct  = h > 0 ? Math.min(100, (top / h) * 100) : 0;
      bar.style.width = pct + '%';
      bar.setAttribute('aria-valuenow', Math.round(pct));
      ticking = false;
    });
  }, { passive: true });

  /* ── Bouton Copier sur les blocs <pre> ── */
  document.querySelectorAll('.article-body pre').forEach(function (pre) {
    if (!navigator.clipboard) return;
    var copyBtn = document.createElement('button');
    copyBtn.className = 'code-copy-btn';
    copyBtn.textContent = FR ? 'Copier' : 'Copy';
    copyBtn.setAttribute('aria-label', FR ? 'Copier le code' : 'Copy code');
    copyBtn.addEventListener('click', function () {
      var code = pre.querySelector('code');
      var text = (code || pre).innerText || (code || pre).textContent || '';
      navigator.clipboard.writeText(text).then(function () {
        copyBtn.textContent = FR ? 'Copié !' : 'Copied!';
        copyBtn.classList.add('copied');
        setTimeout(function () {
          copyBtn.textContent = FR ? 'Copier' : 'Copy';
          copyBtn.classList.remove('copied');
        }, 2000);
      }).catch(function () { /* silencieux si refusé */ });
    });
    pre.style.position = 'relative';
    pre.appendChild(copyBtn);
  });
}());


/* ════════════════════════════════════════
   9. MOTION ENGINE — parallaxe au scroll
   Un seul listener de scroll et une seule boucle rAF pour tout le site.
   Le moteur n'écrit que des variables CSS (--mx-y, --orb-y, --hero-p) :
   les amplitudes finales, les media queries et prefers-reduced-motion sont
   gérés côté CSS (section « MOTION SYSTEM » de style.css).

   Amplitude (px) = déplacement maximal quand l'élément traverse le viewport.
     amplitude > 0 → l'élément traîne derrière le scroll  → paraît plus loin
     amplitude < 0 → l'élément devance le scroll           → paraît plus près
   Une image reçoit toujours le signe opposé à celui de son cadre : c'est ce
   contre-mouvement dans un cadre immobile qui lit comme de la profondeur,
   plutôt que comme un bloc qui glisse.

   L'interpolation (LERP) est ce qui distingue le rendu « premium » : la
   position poursuit sa cible au lieu de la suivre au pixel, ce qui donne
   l'inertie d'une masse. Sans elle, le parallaxe est net mais mécanique.
════════════════════════════════════════ */
(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var LAYERS = [
    /* Cadres — la couche la plus lente */
    ['.hero__image, .hero__film',                       34],
    ['.intro__image, .specs__image',                    38],
    /* .specs__image ne reçoit pas de contre-mouvement interne : son image et
       son bouton doivent rester solidaires (cf. style.css). */
    ['.blog__featured-img',                             28],
    ['.video__wrapper',                                 24],
    ['.model-viewer-frame',                             20],
    /* Images à l'intérieur d'un cadre clippé : contre-mouvement.
       L'amplitude reste sous la marge de sur-dimensionnement définie en CSS
       (--media-scale: 1.08, soit ~16 px de réserve de chaque côté sur une
       image de 420 px) — au-delà, un bord vide apparaîtrait dans le cadre. */
    /* Exclut .intro__image--product : ce contre-mouvement est fait pour une
       photo qui remplit son cadre ; sur un rendu détouré, il fait sortir le
       produit de son halo et le rogne au bord du cadre. */
    ['.intro__image:not(.intro__image--product) img',  -14],
    ['.blog__featured-img img',                        -12],
    /* Titres de section : dérive très légère, juste assez pour que le bloc de
       texte et son image ne défilent pas exactement à la même vitesse. */
    ['.section-header',                                -14],
  ];

  /* Progressions « scrubbées » : la variable passe de 0 à 1 pendant que
     l'élément traverse le viewport, le CSS en fait ce qu'il veut (ici le trait
     de la timeline qui se remplit). Sans interpolation : une progression doit
     coller au scroll, l'inertie y serait perçue comme du retard. */
  var PROGRESS = [
    ['.timeline', '--tl-p'],
    /* Même mécanique pour le rail horizontal de la section « évolution » :
       la portion teal du rail se remplit au fil du scroll (scaleX). */
    ['.evolution__rail', '--tl-p'],
  ];

  var LERP = 0.14;          // 0 = figé, 1 = suivi immédiat (aucune inertie)
  var SETTLED = 0.05;       // px — en dessous, on considère la cible atteinte
  var READ_LINE = 0.7;      // hauteur de viewport où « se lit » une progression

  var root  = document.documentElement;
  var hero  = document.querySelector('.hero');
  var items = [];
  var byEl  = new Map();

  LAYERS.forEach(function (layer) {
    document.querySelectorAll(layer[0]).forEach(function (el) {
      if (byEl.has(el)) return;   // une seule couche par élément
      el.classList.add('mx-parallax');
      /* visible: true au départ — les callbacks d'IntersectionObserver sont
         asynchrones, donc au premier update() tout serait encore « invisible »
         et les éléments déjà à l'écran partiraient de 0 pour rejoindre leur
         position, ce qui se verrait comme un sursaut au chargement. */
      var item = { el: el, amp: layer[1], cur: 0, target: 0, visible: true };
      byEl.set(el, item);
      items.push(item);
    });
  });

  var progressEls = [];
  PROGRESS.forEach(function (entry) {
    document.querySelectorAll(entry[0]).forEach(function (el) {
      progressEls.push({ el: el, name: entry[1] });
    });
  });

  if (!items.length && !progressEls.length && !hero) return;

  var vh = window.innerHeight;

  /* N'anime que ce qui est à l'écran (marge généreuse pour que l'élément soit
     déjà à la bonne position quand il entre réellement dans le viewport). */
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var item = byEl.get(entry.target);
        if (item) item.visible = entry.isIntersecting;
      });
      kick();
    }, { rootMargin: '25% 0px 25% 0px' });
    items.forEach(function (i) { io.observe(i.el); });
  }

  function clamp(v, min, max) { return v < min ? min : (v > max ? max : v); }

  /* snap = true : on se cale directement sur la cible sans interpolation
     (chargement, redimensionnement) — l'inertie n'a de sens qu'en réaction
     à un mouvement de l'utilisateur. */
  function update(snap) {
    var moving = false;
    var sy = window.scrollY;

    /* Orbes de fond — pilotées par le scroll absolu (elles sont ancrées au
       hero, pas traversées par le viewport). */
    root.style.setProperty('--orb-y', (sy * 0.1).toFixed(1) + 'px');

    /* Sortie du hero : 0 en haut de page, 1 quand il a entièrement défilé. */
    if (hero) {
      var h = hero.offsetHeight || 1;
      hero.style.setProperty('--hero-p', clamp(sy / h, 0, 1).toFixed(4));
    }

    /* Progressions : modèle de « ligne de lecture » — une ligne imaginaire à
       READ_LINE de la hauteur du viewport, la progression valant la fraction de
       l'élément déjà passée au-dessus d'elle. 0 quand son haut atteint la
       ligne, 1 quand son bas la franchit.
       (Une première version rapportait le défilement au seul haut de
       l'élément : sur un bloc haut, la barre était déjà pleine alors qu'on
       n'en avait lu que la moitié.) */
    for (var k = 0; k < progressEls.length; k++) {
      var pe = progressEls[k];
      var pr = pe.el.getBoundingClientRect();
      if (pr.height > 0) {
        pe.el.style.setProperty(
          pe.name,
          clamp((vh * READ_LINE - pr.top) / pr.height, 0, 1).toFixed(4)
        );
      }
    }

    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      if (!it.visible) continue;

      var rect = it.el.getBoundingClientRect();
      /* On retire le décalage déjà appliqué : getBoundingClientRect() reflète
         le translate en cours, et s'en servir tel quel ferait boucler le
         calcul sur lui-même (la position influencerait sa propre cible). */
      var top    = rect.top - it.cur;
      var center = top + rect.height / 2;

      /* Progression normalisée : -1 juste sous le viewport, 0 au centre,
         +1 juste au-dessus. Le dénominateur inclut la hauteur de l'élément,
         donc un grand bloc parcourt la même plage qu'un petit. */
      var p = clamp((vh / 2 - center) / ((vh + rect.height) / 2), -1, 1);

      it.target = p * it.amp;

      var delta = it.target - it.cur;
      if (snap || Math.abs(delta) <= SETTLED) {
        it.cur = it.target;
      } else {
        it.cur += delta * LERP;
        moving = true;
      }
      it.el.style.setProperty('--mx-y', it.cur.toFixed(2) + 'px');
    }
    return moving;
  }

  /* Boucle active seulement tant que quelque chose bouge : un scroll relance
     la boucle, l'inertie la maintient quelques frames après l'arrêt, puis
     elle s'éteint (aucun rAF ne tourne au repos). */
  var running = false;
  function loop() {
    running = update();
    if (running) requestAnimationFrame(loop);
  }
  function kick() {
    if (running) return;
    running = true;
    requestAnimationFrame(loop);
  }

  window.addEventListener('scroll', kick, { passive: true });
  window.addEventListener('resize', function () {
    vh = window.innerHeight;
    update(true);
  }, { passive: true });

  update(true);   // position initiale

  /* Second calage après `load` : c'est là que le navigateur restaure la
     position de scroll, et que le module 11 la réapplique au changement de
     langue. Sans ce snap, les couches partent de 0 et rejoignent leur
     position par interpolation — visible comme un glissement au chargement. */
  window.addEventListener('load', function () {
    vh = window.innerHeight;
    update(true);
  });
}());

/* ════════════════════════════════════════
   10. POINTEUR — inclinaison des cartes + du rendu produit
   Deux réglages font toute la différence entre « gadget » et « premium » :
     • l'amplitude — une carte s'incline de 3-4°, pas de 7° ;
     • la durée de transition — assez longue (0,4 s) pour que la carte
       *poursuive* le curseur avec de l'inertie au lieu d'y être collée.
       L'ancienne valeur (0,07 s) suivait la souris au pixel : net, mais nerveux.
════════════════════════════════════════ */
(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  /* Écarte le tactile : sur un écran tactile, `mousemove` n'est émis qu'au
     moment du tap et l'inclinaison resterait figée après le doigt. */
  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

  /* ── Cartes : inclinaison 3D + halo qui suit le curseur ── */
  var CARD_TRANSITION =
    'border-color 0.25s ease, box-shadow 0.4s ease, transform 0.4s cubic-bezier(0.4, 0, 0.2, 1)';

  document.querySelectorAll('.feature-card, .product-card').forEach(function (card) {
    card.addEventListener('mouseenter', function () {
      card.style.willChange = 'transform';
      card.style.transition = CARD_TRANSITION;
    });

    card.addEventListener('mousemove', function (e) {
      var rect = card.getBoundingClientRect();
      var xRatio = (e.clientX - rect.left) / rect.width  - 0.5; // -0.5 → 0.5
      var yRatio = (e.clientY - rect.top)  / rect.height - 0.5;

      card.style.transform =
        'perspective(900px)' +
        ' rotateY(' + (xRatio * 7).toFixed(2) + 'deg)' +
        ' rotateX(' + (-yRatio * 5).toFixed(2) + 'deg)' +
        ' translateY(-6px)';

      card.style.setProperty('--spot-x', (e.clientX - rect.left) + 'px');
      card.style.setProperty('--spot-y', (e.clientY - rect.top)  + 'px');
    });

    card.addEventListener('mouseleave', function () {
      card.style.willChange = '';
      card.style.transition = '';
      card.style.transform  = '';
    });
  });

  /* ── Rendu produit du hero : inclinaison depuis le centre du hero ──
     Remplace l'ancienne animation de flottement en boucle : le mouvement
     devient une réponse au visiteur plutôt qu'un va-et-vient automatique.
     Le CSS applique --mx-rx / --mx-ry (cf. « MOTION SYSTEM »), le suivi est
     lissé par la transition de 0,5 s posée sur .hero__image img. */
  /* Le hero porte soit un rendu produit (.hero__image > img), soit le film
     produit (.hero__film). Dans le premier cas on incline l'image dans son
     cadre ; dans le second on incline le cadre lui-même — incliner la vidéo à
     l'intérieur d'un cadre clippé arrondi en découvrirait les bords. */
  var heroFrame = document.querySelector('.hero__image, .hero__film');
  var heroImg   = heroFrame && (heroFrame.querySelector('img') || heroFrame);

  if (heroImg) {
    var MAX_TILT = 6;   // degrés

    /* Écoute sur .hero et non sur l'image : le mouvement démarre dès que le
       curseur entre dans la section, l'image réagit donc à l'approche. */
    var heroSection = heroFrame.closest('.hero') || heroFrame;

    heroSection.addEventListener('mousemove', function (e) {
      var rect = heroFrame.getBoundingClientRect();
      var x = (e.clientX - rect.left - rect.width  / 2) / (rect.width  / 2);
      var y = (e.clientY - rect.top  - rect.height / 2) / (rect.height / 2);
      /* Bornées : le curseur peut être loin de l'image (on écoute toute la
         section), sans quoi les ratios dépasseraient largement ±1. */
      x = Math.max(-1, Math.min(1, x));
      y = Math.max(-1, Math.min(1, y));

      heroImg.style.setProperty('--mx-ry', (x * MAX_TILT).toFixed(2) + 'deg');
      heroImg.style.setProperty('--mx-rx', (-y * MAX_TILT).toFixed(2) + 'deg');
    }, { passive: true });

    heroSection.addEventListener('mouseleave', function () {
      heroImg.style.setProperty('--mx-ry', '0deg');
      heroImg.style.setProperty('--mx-rx', '0deg');
    }, { passive: true });
  }
}());

/* ════════════════════════════════════════
   12. VIEWER 3D — contrôles personnalisés
   Page modele-3d.html / en/3d-model.html uniquement
════════════════════════════════════════ */
(function () {
  var viewer = document.querySelector('#qbot-viewer');
  if (!viewer) return;

  var frame          = viewer.closest('.model-viewer-frame');
  var fill           = frame?.querySelector('.mv-loading__fill');
  var rotateBtn      = frame?.querySelector('[data-mv-action="rotate"]');
  var resetBtn       = frame?.querySelector('[data-mv-action="reset"]');
  var fullscreenBtn  = frame?.querySelector('[data-mv-action="fullscreen"]');
  var zoomInBtn      = frame?.querySelector('[data-mv-action="zoom-in"]');
  var zoomOutBtn     = frame?.querySelector('[data-mv-action="zoom-out"]');
  var lightingBtn    = frame?.querySelector('[data-mv-action="lighting"]');
  var phoneBtn       = frame?.querySelector('[data-mv-action="phone"]');
  var slider         = document.querySelector('[data-mv-action="explode-slider"]');
  var sliderValueEl  = document.querySelector('[data-mv-explode-value]');
  var reduceMotion   = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var FR             = (document.documentElement.lang || 'fr').slice(0, 2) !== 'en';

  var DEFAULT_ORBIT  = viewer.getAttribute('camera-orbit') || '0deg 75deg 105%';
  var DEFAULT_FOV    = viewer.getAttribute('field-of-view') || '30deg';
  var DEFAULT_TARGET = viewer.getAttribute('camera-target') || 'auto auto auto';
  var STANDARD_SRC  = viewer.getAttribute('src');

  /* Presets d'éclairage — valeurs en dur : le viewer démarre en nuit (ses
     attributs exposure/shadow-intensity portent donc déjà le preset nuit
     pour le premier rendu), on ne peut plus les relire pour en déduire le
     preset jour. */
  var DAY_EXPOSURE   = 1.1;
  var DAY_SHADOW     = 1;
  var NIGHT_EXPOSURE = 0.5;
  var NIGHT_SHADOW   = 1.3;

  /* Le clip glTF "Explode" couvre deux segments temporels distincts (pour
     rester un seul clip robuste plutôt que de jongler entre plusieurs
     animationName, ce qui remettrait les autres pièces à leur pose de repos) :
     [0 .. EXPLODE_END]  pilote les pièces de la coque (slider d'éclatement).
       Les pièces ont une 3e keyframe à t=1.0 qui les ré-assemble avant le
       segment téléphone — sans ça, au-delà de leur dernière keyframe le clip
       les laisse figées à leur valeur "éclatée" (clamp glTF), et cliquer sur
       le bouton téléphone faisait donc exploser la coque au passage.
       EXPLODE_END < 1.0 pour ne jamais toucher exactement ce point de bascule.
     [PHONE_START .. PHONE_END] pilote le téléphone (position + échelle :
       invisible/échelle 0 tant qu'on n'a pas cliqué, cf. clamp avant sa
       1ère keyframe — pas besoin de logique JS pour le cacher par défaut). */
  var EXPLODE_END  = 0.98;
  var PHONE_START  = 1.0;
  var PHONE_END    = 2.0;
  var TIME_EPSILON = 0.001; // évite currentTime === duration exacte du clip (voir plus bas)

  /* Cache-busting : les .glb sont régulièrement régénérés sous le même nom
     pendant qu'on affine le modèle (position du téléphone, etc.) — sans ceci,
     un navigateur qui a déjà mis qbot-hd.glb en cache continue de servir une
     ancienne géométrie après une mise à jour, ce qui ressemble à un bug de
     positionnement alors que le fichier sur le serveur est déjà correct.
     À incrémenter à chaque remplacement de géométrie. */
  var MODEL_VERSION = 5;

  function fileNameOf(path) { return path.split('/').pop(); }

  function showFileProtocolHelp() {
    var fbTitle = frame?.querySelector('.model-viewer-frame__fallback h3');
    var fbText  = frame?.querySelector('.model-viewer-frame__fallback p');
    if (fbTitle) fbTitle.textContent = FR
      ? 'Ouvrez cette page via un serveur local'
      : 'Open this page through a local server';
    if (fbText) fbText.textContent = FR
      ? "Le navigateur bloque le chargement du modèle 3D quand la page est ouverte directement depuis le disque (file://). Lancez un serveur local (ex. : npx serve . ou python3 -m http.server) puis rouvrez la page via http://localhost. Cela fonctionnera normalement une fois le site en ligne."
      : 'Browsers block loading the 3D model when the page is opened directly from disk (file://). Start a local server (e.g. npx serve . or python3 -m http.server) and reopen the page via http://localhost. This will work normally once the site is live.';
  }

  /* Charge le .glb — gère aussi le cas file:// (fetch() bloqué par CORS pour
     les fichiers locaux) en basculant sur un data URI base64, chargé via une
     balise <script> classique (non soumise à cette restriction), depuis
     assets/models/qbot.glb.data.js qui remplit
     window.QBOT_MODEL_DATA['qbot.glb']. */
  function loadSrc(path) {
    if (!path) { showFileProtocolHelp(); return; }
    if (window.location.protocol !== 'file:') {
      viewer.src = path + '?v=' + MODEL_VERSION;
      return;
    }
    window.QBOT_MODEL_DATA = window.QBOT_MODEL_DATA || {};
    var key = fileNameOf(path);
    if (window.QBOT_MODEL_DATA[key]) {
      viewer.src = window.QBOT_MODEL_DATA[key];
      return;
    }
    var dataScript = document.createElement('script');
    dataScript.src = path + '.data.js';
    dataScript.onload = function () {
      if (window.QBOT_MODEL_DATA[key]) viewer.src = window.QBOT_MODEL_DATA[key];
      else showFileProtocolHelp();
    };
    dataScript.onerror = showFileProtocolHelp;
    document.head.appendChild(dataScript);
  }

  if (window.location.protocol === 'file:') loadSrc(STANDARD_SRC);

  if (reduceMotion) {
    viewer.removeAttribute('auto-rotate');
    rotateBtn?.setAttribute('aria-pressed', 'false');
  }

  if (slider) slider.disabled = true;

  viewer.addEventListener('progress', function (e) {
    if (!fill) return;
    var pct = Math.round((e.detail.totalProgress || 0) * 100);
    fill.style.width = pct + '%';
  });

  viewer.addEventListener('load', function () {
    frame?.classList.add('is-loaded');
    frame?.classList.remove('has-error');

    /* Fix : sans pause() explicite, l'horloge d'animation interne de
       model-viewer continue de tourner en arrière-plan (l'animation "Explode"
       est chargée mais jamais figée) et écrase le currentTime qu'on pilote
       nous-mêmes → le modèle "explosait" puis revenait tout seul à l'état
       assemblé une fraction de seconde après. */
    viewer.pause();

    if (slider) {
      slider.disabled = false;
      applySliderToModel();
    }
    if (phoneDocked) viewer.currentTime = PHONE_END - TIME_EPSILON;
  });

  viewer.addEventListener('error', function () {
    frame?.classList.add('has-error');
  });

  rotateBtn?.addEventListener('click', function () {
    var active = viewer.hasAttribute('auto-rotate');
    if (active) viewer.removeAttribute('auto-rotate');
    else viewer.setAttribute('auto-rotate', '');
    rotateBtn.setAttribute('aria-pressed', String(!active));
  });

  resetBtn?.addEventListener('click', function () {
    viewer.cameraOrbit = DEFAULT_ORBIT;
    viewer.cameraTarget = DEFAULT_TARGET;
    viewer.fieldOfView = DEFAULT_FOV;
    if (typeof viewer.jumpCameraToGoal === 'function') viewer.jumpCameraToGoal();
  });

  /* Zoom — vues larges ou serrées, en plus de la molette/pincement déjà
     gérés nativement par model-viewer (camera-controls). Les bornes sont
     posées par min-camera-orbit / max-camera-orbit sur la balise. */
  function zoomBy(factor) {
    if (typeof viewer.getCameraOrbit !== 'function') return;
    var o = viewer.getCameraOrbit();
    var nextRadius = o.radius * factor;
    viewer.cameraOrbit = o.theta.toFixed(4) + 'rad ' + o.phi.toFixed(4) + 'rad ' + nextRadius.toFixed(4) + 'm';
  }
  zoomInBtn?.addEventListener('click', function () { zoomBy(0.8); });
  zoomOutBtn?.addEventListener('click', function () { zoomBy(1.25); });

  fullscreenBtn?.addEventListener('click', function () {
    if (!frame) return;
    if (!document.fullscreenElement) {
      (frame.requestFullscreen || frame.webkitRequestFullscreen)?.call(frame);
    } else {
      (document.exitFullscreen || document.webkitExitFullscreen)?.call(document);
    }
  });

  document.addEventListener('fullscreenchange', function () {
    var isFull = document.fullscreenElement === frame;
    fullscreenBtn?.setAttribute('aria-pressed', String(isFull));
    frame?.classList.toggle('is-fullscreen', isFull);
  });

  /* Vue éclatée — slider continu sur l'animation glTF "Explode" (0% = assemblé,
     100% = éclaté, borné à EXPLODE_END < durée totale du clip donc jamais de
     souci de bouclage ici). viewer.pause() (voir listener 'load' ci-dessus)
     garantit que la position posée ici reste figée tant qu'on n'y touche pas. */
  function setSliderDisplay(pct) {
    if (!slider) return;
    slider.value = pct;
    frame?.classList.toggle('is-exploded', pct > 0);
    slider.style.setProperty('--mv-explode-pct', pct + '%');
    if (sliderValueEl) sliderValueEl.textContent = pct + '%';
  }
  function applySliderToModel() {
    if (!slider) return;
    var pct = Number(slider.value);
    viewer.currentTime = EXPLODE_END * (pct / 100);
    setSliderDisplay(pct);
  }
  slider?.addEventListener('input', applySliderToModel);

  /* Tween générique de currentTime (utilisé par le bouton téléphone — le
     slider d'éclatement, lui, est piloté en direct par le glissement). */
  function tweenCurrentTime(from, to, ms, onDone) {
    if (reduceMotion) {
      viewer.currentTime = to;
      if (onDone) onDone();
      return;
    }
    var t0 = null;
    function tick(now) {
      if (t0 === null) t0 = now;
      var p = Math.min((now - t0) / ms, 1);
      var eased = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
      viewer.currentTime = from + (to - from) * eased;
      if (p < 1) requestAnimationFrame(tick);
      else if (onDone) onDone();
    }
    requestAnimationFrame(tick);
  }

  /* Insérer/retirer un smartphone — petite animation sur le second segment
     du clip "Explode" ([PHONE_START..PHONE_END], voir plus haut). PHONE_END
     est la durée totale du clip : comme pour le slider à 100%, on reste à
     TIME_EPSILON de la borne exacte pour éviter que le mixer ne reboucle. */
  var phoneDocked = false;
  phoneBtn?.addEventListener('click', function () {
    var from = phoneDocked ? PHONE_END - TIME_EPSILON : PHONE_START;
    var to   = phoneDocked ? PHONE_START : PHONE_END - TIME_EPSILON;
    phoneDocked = !phoneDocked;
    /* Le segment téléphone [PHONE_START..PHONE_END] réassemble toujours la
       coque (cf. keyframe de snap-back plus haut) : sans ceci, le slider
       restait affiché à son ancienne valeur (ex. 100%) alors que le modèle
       venait de se réassembler visuellement — il fallait le rebouger à la
       main pour que l'affichage redevienne cohérent. */
    setSliderDisplay(0);
    phoneBtn.setAttribute('aria-pressed', String(phoneDocked));
    phoneBtn.setAttribute('aria-label', phoneDocked
      ? (FR ? 'Retirer le smartphone' : 'Remove the smartphone')
      : (FR ? 'Insérer un smartphone' : 'Insert a smartphone'));
    tweenCurrentTime(from, to, 700);
  });

  /* Jour/nuit — bascule l'exposition/l'intensité des ombres de model-viewer
     et assombrit le fond du cadre, sans toucher au modèle ni à l'animation. */
  lightingBtn?.addEventListener('click', function () {
    var toNight = lightingBtn.getAttribute('aria-pressed') !== 'true';
    lightingBtn.setAttribute('aria-pressed', String(toNight));
    lightingBtn.setAttribute('aria-label', toNight
      ? (FR ? 'Passer en éclairage jour' : 'Switch to day lighting')
      : (FR ? 'Passer en éclairage nuit' : 'Switch to night lighting'));
    viewer.exposure = toNight ? NIGHT_EXPOSURE : DAY_EXPOSURE;
    viewer.shadowIntensity = toNight ? NIGHT_SHADOW : DAY_SHADOW;
    frame?.classList.toggle('is-night', toNight);
  });
}());

/* ════════════════════════════════════════
   13. MAGNETIC BUTTONS — CTA suit le curseur
   Amplitude volontairement faible (0,10 / 0,14) : à 0,28 / 0,35 le bouton se
   déplaçait de plus de 20 px et pouvait fuir sous le curseur au bord de la
   zone, ce qui rend le clic difficile. Ici le déplacement reste sous ~6 px —
   perceptible comme une matière, jamais comme une cible mouvante.
════════════════════════════════════════ */
(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
  if (window.innerWidth < 1024) return;

  var PULL_X = 0.10;
  var PULL_Y = 0.14;
  var MAX    = 6;      // px — plafond, indépendant de la taille du bouton

  function bounded(v) { return Math.max(-MAX, Math.min(MAX, v)); }

  var SELECTORS = '.hero__actions .btn, .page-hero .btn, .calendly-box .btn, .cta-section .btn';
  document.querySelectorAll(SELECTORS).forEach(function (btn) {
    btn.addEventListener('mousemove', function (e) {
      var rect = btn.getBoundingClientRect();
      var x = bounded((e.clientX - rect.left - rect.width  / 2) * PULL_X);
      var y = bounded((e.clientY - rect.top  - rect.height / 2) * PULL_Y);
      btn.style.transform = 'translate(' + x.toFixed(2) + 'px, ' + y.toFixed(2) + 'px)';
    }, { passive: true });

    btn.addEventListener('mouseleave', function () {
      btn.style.transform = '';
    }, { passive: true });
  });
}());

/* ════════════════════════════════════════
   14. FILM DU HERO — respect de prefers-reduced-motion
   L'attribut `autoplay` est dans le HTML (il doit l'être : sans lui la lecture
   ne démarre pas assez tôt pour éviter un poster figé au chargement). Pour un
   visiteur qui demande moins d'animation, on l'arrête et on lui rend la main
   plutôt que de lui supprimer le contenu.
════════════════════════════════════════ */
(function () {
  var film = document.querySelector('.hero__film-video');
  if (!film) return;
  /* Même traitement pour « économiseur de données » : le film pèse ~3 Mo et
     l'autoplay le télécharge immédiatement. */
  var saveData = navigator.connection && navigator.connection.saveData;
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && !saveData) return;
  film.autoplay = false;
  film.loop     = false;
  film.controls = true;
  film.pause();
  film.currentTime = 0;
}());

