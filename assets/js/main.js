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

    /* Seuil de 6 px avant de masquer la barre. Sans lui, UN pixel vers le bas
       suffisait : au doigt, l'inertie du défilement mobile produit sans arrêt de
       micro-variations, et la barre — donc le bouton de démo, seul CTA permanent
       du téléphone — clignotait à chaque hésitation. La révélation, elle, reste
       immédiate : on ne fait jamais attendre quelqu'un qui remonte. */
    if (delta > 0 && delta < 6) { lastY = y; ticking = false; return; }

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
    if (linkFile === currentFile) {
      link.classList.add('active');
      /* La classe coloriait, elle n'annonçait rien : le lien de la page courante
         était un lien ordinaire pour un lecteur d'écran. `aria-current` le dit.
         Il reste un lien — c'est le motif attendu d'une navigation persistante,
         contrairement au fil d'Ariane où le dernier élément est la page. */
      link.setAttribute('aria-current', 'page');
    }
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
      /* Figures d'article. Elles traversaient 4 à 7 écrans en fondu plat : la
         mesure des six articles donnait 0 élément en parallaxe et trois
         révélations « plain » pour toute la page. Le masque qui remonte est la
         signature du site pour un média, il n'y avait pas de raison de l'en
         priver. La légende est dans la figure, donc dans le masque : elle
         apparaît en dernier, ce qui est l'ordre de lecture. */
      '.article-figure',
    ]],
    ['group', [
      '.section-header',
      /* Colonne de texte d'une section intro : label → titre → paragraphes
         arrivent en cascade. `:not()` écarte la colonne image du même grid. */
      '.intro__grid > div:not(.intro__image)',
    ]],
    ['card', [
      /* Les titres de section d'un article arrivent un à un. Le corps entier est
         déjà une révélation « plain » — un seul fondu pour plusieurs milliers de
         pixels — donc rien ne marquait le passage d'une partie à l'autre. */
      '.article-body h2',
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
    /* Les pages d'article portent DÉJÀ une durée en dur (le back-office aussi,
       via son champ « rt »). Ce bloc en ajoutait une seconde : on affichait
       deux durées côte à côte, qui ne concordaient même pas (« 8 min de
       lecture » suivi de « 7 min de lecture »). On remplace donc le nombre là
       où il est, et on n'ajoute un badge que s'il n'y en a aucun.
       Le remplacement ne touche que les chiffres, dans le nœud texte : les
       trois habillages en place sont préservés (<span> simple, « Durée : » en
       gras, ou .article-meta__item avec pictogramme), et l'espace insécable
       qui précède « min » aussi. */
    var walk = document.createTreeWalker(metaEl, NodeFilter.SHOW_TEXT);
    var node, replaced = false;
    while (!replaced && (node = walk.nextNode())) {
      if (/\d+\s*min/i.test(node.textContent)) {
        node.textContent = node.textContent.replace(/\d+(?=\s*min)/i, minutes);
        replaced = true;
      }
    }
    if (!replaced) {
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
    /* .hero__film en est volontairement absent : le cadre du film reste fixe
       (cf. l'inclinaison au pointeur, plus bas, retirée pour la même raison) —
       un cadre qui dérive pendant que son contenu bouge déjà se lit comme un
       flottement parasite, pas comme de la profondeur. */
    ['.hero__image',                                    34],
    ['.intro__image, .specs__image',                    38],
    /* .specs__image ne reçoit pas de contre-mouvement interne : son image et
       son bouton doivent rester solidaires (cf. style.css). */
    ['.blog__featured-img',                             28],
    /* Figures d'article : la dérive la plus discrète du site (16 contre 20 à 38
       pour les autres cadres). Le texte autour est fixe et se lit ligne à ligne ;
       une amplitude franche y serait perçue comme un décalage, pas comme de la
       profondeur. La figure de la barre latérale en est exclue : elle est dans un
       bloc déjà collant, où une dérive lutterait contre l'épinglage. */
    ['.article-body .article-figure',                   16],
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
  /* Troisième champ facultatif : un nombre d'états. Quand il est là, on écrit AUSSI
     `data-panel` sur l'élément — l'index de l'état courant, déduit de la même
     progression. C'est le strict minimum pour qu'une section épinglée puisse
     changer de contenu : le CSS ne sait pas comparer un nombre, il sait faire
     `[data-panel="1"]`. Le principe du module tient : le JS ne décide pas de
     l'allure, il dit seulement où l'on en est. */
  var PROGRESS = [
    ['.timeline', '--tl-p'],
    ['.pin-modes', '--pin-p', 3],
    ['.faq-layout', '--faq-p'],
    ['.pin-3d', '--pin3-p', 3],
    /* `.evolution__rail` était ici : son trait teal se remplissait au scroll.
       Retiré — ce trait indique où en est le PRODUIT (il s'arrête sur le point
       « Génération actuelle »), pas où en est la lecture ; scrubbé, il
       s'allongeait et se raccourcissait et ne collait plus à son point. Il est
       désormais figé en CSS (--evo-fill). Aucune page ne porte plus de
       `.timeline`, donc ce tableau ne pilote aujourd'hui plus rien : on le
       garde parce que c'est le chemin de code d'une progression scrubbée. */
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
      progressEls.push({ el: el, name: entry[1], states: entry[2] || 0, panel: -1 });
    });
  });

  /* Le garde-fou d'origine coupait le moteur quand la page n'avait ni parallaxe,
     ni progression, ni hero — c'est-à-dire sur la FAQ, les pages de contact et
     les six articles. Il ne peut plus : le CALQUE AMBIANT est sur `body::before`,
     donc présent sur les 22 pages, et c'est ce moteur qui écrit sa variable.
     Le coût est nul là où il n'y a rien d'autre à animer : `moving` reste faux, la
     boucle s'arrête donc après une seule image, et il n'y a qu'une écriture par
     salve de défilement. */

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

    /* Progression dans la page entière, bornée à [0,1]. C'est la seule grandeur
       dont a besoin le calque ambiant (cf. « CALQUE AMBIANT » dans style.css) :
       le CSS en déduit la position des halos et leur intensité. Bornée, et non
       proportionnelle au scroll absolu comme `--orb-y`, parce qu'un halo qui
       traverse toute la page doit arriver au bout en même temps que le lecteur,
       quelle que soit la longueur de la page — 2 écrans sur `contact`, 12 sur
       l'accueil. */
    var span = document.documentElement.scrollHeight - window.innerHeight;
    root.style.setProperty('--amb-p', span > 0 ? clamp(sy / span, 0, 1).toFixed(4) : '0');

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
        /* Deux formules, parce qu'il y a deux objets. Un bloc qui TRAVERSE le
           viewport se mesure à la ligne de lecture — c'est le cas de `.timeline`.
           Un rail ÉPINGLÉ, lui, ne se mesure qu'à sa course de collage : sa scène
           reste collée pendant `hauteur − viewport`, et au-delà la progression n'a
           plus rien à piloter. Mesuré avec la première formule sur un rail de
           2 700 px : le dernier panneau était atteint à mi-course et tenait toute
           la seconde moitié. La présence d'un nombre d'états signale un rail. */
        var prog = pe.states
          ? clamp(-pr.top / Math.max(1, pr.height - vh), 0, 1)
          : clamp((vh * READ_LINE - pr.top) / pr.height, 0, 1);
        pe.el.style.setProperty(pe.name, prog.toFixed(4));
        if (pe.states) {
          /* Les bornes sont resserrées d'un dixième de part et d'autre : le premier
             état tient pendant que la section arrive et le dernier pendant qu'elle
             sort, sinon le premier panneau ne se voit jamais posé. */
          var q = clamp((prog - 0.1) / 0.8, 0, 0.9999);
          var idx = Math.floor(q * pe.states);
          if (idx !== pe.panel) {
            pe.panel = idx;
            pe.el.setAttribute('data-panel', String(idx));
          }
        }
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
  /* Uniquement le rendu produit fixe (.hero__image > img). Le cadre du film
     ne s'incline pas : sur une image déjà en mouvement, l'inclinaison ne se
     lit pas comme de la profondeur mais comme un cadre instable. */
  var heroFrame = document.querySelector('.hero__image');
  var heroImg   = heroFrame && heroFrame.querySelector('img');

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
  var slider         = document.querySelector('[data-mv-action="explode-slider"]');
  var sliderValueEl  = document.querySelector('[data-mv-explode-value]');
  var reduceMotion   = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var FR             = (document.documentElement.lang || 'fr').slice(0, 2) !== 'en';

  var DEFAULT_ORBIT  = viewer.getAttribute('camera-orbit') || '0deg 75deg 105%';
  var DEFAULT_FOV    = viewer.getAttribute('field-of-view') || '30deg';
  var DEFAULT_TARGET = viewer.getAttribute('camera-target') || 'auto auto auto';
  var STANDARD_SRC  = viewer.getAttribute('src');


  /* Le clip glTF "Explode" couvre deux segments : [0 .. 1.0] pour les pièces de
     la coque, [1.0 .. 2.0] pour l'insertion du smartphone.
     LE SECOND N'EST PLUS PILOTÉ. Le bouton « insérer un smartphone » a été retiré
     de la visionneuse : le téléphone du GLB est un volume générique, bien moins
     soigné que le boîtier, et le montrer desservait la page. En restant sous
     t=1.0 il garde son échelle 0 — il est donc simplement absent, c'est le clip
     qui s'en charge, il n'y a rien à masquer.
     La borne EXPLODE_END < 1.0 garde tout son sens : les pièces portent une 3e
     keyframe à t=1.0 qui les ré-assemble (elle existe pour que le segment
     téléphone ne les laisse pas éclatées), et l'atteindre referait se refermer la
     coque juste au moment où le slider arrive à 100 %. */
  var EXPLODE_END  = 0.98;

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


/* ════════════════════════════════════════
   15. FORMULAIRES — plus jamais d'envoi qui disparaît
   Les six formulaires du site (contact FR/EN, newsletter des deux homepages et
   des deux index de blog) étaient en `action="#"` : le visiteur remplissait,
   cliquait, la page se rechargeait, sa saisie était perdue — et rien n'indiquait
   l'échec. C'est le pire des trois cas possibles, parce qu'il est invisible.

   UN SEUL POINT DE CONFIGURATION : l'attribut `data-endpoint` du <form>.
     data-endpoint=""                     → repli courrier (l'état actuel)
     data-endpoint="https://…/f/xxxx"     → envoi HTTP, sans toucher au reste
   Brevo, Formspree et compagnie exposent tous une URL de ce genre qui accepte un
   POST multipart ; il suffira de la coller là, dans les six pages.

   Sans endpoint, on n'invente pas un envoi : on ouvre le client courrier du
   visiteur avec un message déjà rédigé. Ce n'est pas idéal — il faut qu'il
   appuie sur « envoyer » — mais rien n'est perdu et il le SAIT.
════════════════════════════════════════ */
(function () {
  var forms = document.querySelectorAll('form[data-form]');
  if (!forms.length) return;

  var FR = (document.documentElement.lang || 'fr').slice(0, 2) !== 'en';
  var MAIL = 'bot@q-leap.eu';
  var T = FR ? {
    envoi:   'Envoi en cours…',
    ok:      'Merci, votre message est parti. Nous revenons vers vous rapidement.',
    okNews:  'Merci, votre inscription est enregistrée.',
    erreur:  'L’envoi a échoué. Écrivez-nous à ' + MAIL + ', nous répondrons.',
    manque:  'Merci de compléter les champs obligatoires.',
    courrier:'Votre logiciel de courrier vient de s’ouvrir avec le message prérempli : il reste à appuyer sur « envoyer ».',
    sujetC:  'Demande via le site Q-Bot',
    sujetN:  'Inscription à la newsletter Q-Bot'
  } : {
    envoi:   'Sending…',
    ok:      'Thank you, your message is on its way. We will get back to you shortly.',
    okNews:  'Thank you, your subscription is registered.',
    erreur:  'Sending failed. Write to us at ' + MAIL + ' and we will answer.',
    manque:  'Please fill in the required fields.',
    courrier:'Your mail application just opened with the message prefilled — all that is left is to hit send.',
    sujetC:  'Enquiry from the Q-Bot website',
    sujetN:  'Q-Bot newsletter subscription'
  };

  function dire(form, texte, type) {
    var el = form.querySelector('.form-status');
    if (!el) return;
    el.textContent = texte;
    el.hidden = false;
    el.setAttribute('data-state', type);
  }

  /* Corps du courrier : « Libellé : valeur », un champ par ligne. On prend le
     <label> associé quand il existe, sinon le nom du champ — le destinataire lit
     ainsi le message dans les mots du formulaire. */
  function corps(form) {
    var lignes = [];
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.type === 'submit' || el.type === 'button') return;
      var v = el.type === 'checkbox' ? (el.checked ? (FR ? 'oui' : 'yes') : (FR ? 'non' : 'no')) : el.value;
      if (!v) return;
      var lab = form.querySelector('label[for="' + el.id + '"]');
      var nom = (lab ? lab.textContent : el.name).replace(/\s*\*\s*$/, '').trim();
      lignes.push(nom + ' : ' + v);
    });
    return lignes.join('\n');
  }

  Array.prototype.forEach.call(forms, function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var news = form.getAttribute('data-form') === 'newsletter';

      /* `novalidate` est posé sur le formulaire de contact pour maîtriser
         l'affichage : la validation reste à faire, à la main. */
      if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
        dire(form, T.manque, 'error');
        var premier = form.querySelector(':invalid');
        if (premier) premier.focus();
        return;
      }

      var url = (form.getAttribute('data-endpoint') || '').trim();

      if (!url) {                                   // repli courrier
        var sujet = news ? T.sujetN : T.sujetC;
        window.location.href = 'mailto:' + MAIL
          + '?subject=' + encodeURIComponent(sujet)
          + '&body=' + encodeURIComponent(corps(form));
        dire(form, T.courrier, 'info');
        return;
      }

      dire(form, T.envoi, 'info');
      var bouton = form.querySelector('[type="submit"]');
      if (bouton) bouton.disabled = true;
      fetch(url, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } })
        .then(function (r) {
          if (!r.ok) throw new Error(r.status);
          form.reset();
          dire(form, news ? T.okNews : T.ok, 'ok');
        })
        .catch(function () { dire(form, T.erreur, 'error'); })
        .then(function () { if (bouton) bouton.disabled = false; });
    });
  });
}());


/* ══════════════════════════════════════════════════════════════════════════
   16. INDEX DE LA FAQ — l'entrée courante, et l'ouverture au clic
   ══════════════════════════════════════════════════════════════════════════
   Deux services, aucun écouteur de défilement : le module 9 reste le seul du
   site à en avoir un.

   1. Marquer l'entrée qui correspond à la question la plus haute encore visible.
      Un IntersectionObserver suffit, et il ne se déclenche qu'aux franchissements
      — pas à chaque image.
   2. Ouvrir la question au clic sur son entrée. On ne réimplémente pas
      l'accordéon : on clique son bouton, ce qui repasse par le module 3 et sa
      mesure de `scrollHeight`. Une seconde implémentation finirait par diverger.

   `aria-current="location"` et non `"page"` : l'entrée ne désigne pas la page
   courante mais un endroit dans la page. C'est la valeur prévue pour ça.        */
(function () {
  var index = document.querySelector('.faq-index');
  if (!index) return;
  var liens = [].slice.call(index.querySelectorAll('a[href^="#faq-q"]'));
  if (!liens.length) return;

  var parId = {};
  liens.forEach(function (a) { parId[a.getAttribute('href').slice(1)] = a; });

  /* Ouverture au clic. On laisse le navigateur faire le défilement (l'ancre est
     un vrai lien, il fonctionne sans script), on ne fait qu'ouvrir. */
  liens.forEach(function (a) {
    a.addEventListener('click', function () {
      var item = document.getElementById(a.getAttribute('href').slice(1));
      if (!item) return;
      var bouton = item.querySelector('.faq-item__question');
      if (bouton && bouton.getAttribute('aria-expanded') !== 'true') bouton.click();
    });
  });

  if (!('IntersectionObserver' in window)) return;
  var vus = {};
  var io = new IntersectionObserver(function (entrees) {
    entrees.forEach(function (e) { vus[e.target.id] = e.isIntersecting ? e.boundingClientRect.top : null; });
    /* La question courante est la plus haute de celles qui touchent l'écran :
       c'est celle qu'on est en train de lire, pas la première de la liste. */
    var courant = null, meilleur = Infinity;
    for (var id in vus) {
      if (vus[id] === null) continue;
      var d = Math.abs(vus[id] - window.innerHeight * 0.25);
      if (d < meilleur) { meilleur = d; courant = id; }
    }
    liens.forEach(function (a) {
      var actif = a.getAttribute('href').slice(1) === courant;
      if (actif) a.setAttribute('aria-current', 'location');
      else a.removeAttribute('aria-current');
    });
  }, { rootMargin: '-10% 0px -55% 0px' });

  liens.forEach(function (a) {
    var item = document.getElementById(a.getAttribute('href').slice(1));
    if (item) io.observe(item);
  });
}());


/* ══════════════════════════════════════════════════════════════════════════
   17. PAGE 3D — trois poses, puis la main au visiteur
   ══════════════════════════════════════════════════════════════════════════
   La page du modèle faisait deux écrans : on y arrivait, un boîtier tournait sur
   lui-même, une barre d'outils attendait. Le visiteur qui ne saisit pas l'objet
   n'en voyait qu'une rotation.

   L'acte montre ce que la carte « Aperçu rapide » dit déjà : ses trois lignes —
   dimensions, processeur, fabrication — deviennent trois poses. AUCUN TEXTE N'EST
   AJOUTÉ : les trois libellés existent, le modèle se contente de les illustrer.

     dimensions   → trois-quarts arrière en plongée, l'emprise au sol se lit
     processeur   → vue éclatée, on voit l'intérieur
     fabrication  → trois-quarts avant, produit assemblé

   L'ordre finit sur le produit refermé : c'est l'état dans lequel le visiteur
   récupère la main, et non une carcasse ouverte.

   TROIS PRÉCAUTIONS, chacune pour une raison précise :
   - `camera-controls` et `auto-rotate` sont RETIRÉS pendant l'acte. Sans cela, la
     rotation automatique incrémente l'azimut pendant qu'on l'écrit, et le résultat
     tremble ; et un glissé du visiteur lutterait contre le défilement.
   - Ils sont RENDUS à la fin de l'acte, la rotation seulement si son bouton est
     encore enclenché — module 12 en garde l'état, il ne faut pas le contredire.
   - Le module ne fait rien sous 900 px ni sans épinglage : `data-panel` n'est
     écrit que par le module 9, qui ne tourne pas en mouvement réduit. La page
     reste alors ce qu'elle était, interactive d'emblée.                        */
(function () {
  var rail = document.querySelector('.pin-3d');
  var viewer = document.querySelector('#qbot-viewer');
  if (!rail || !viewer) return;
  /* Pas d'acte en mouvement réduit — et donc surtout pas de retrait des contrôles.
     Sans ce garde-fou le module retirait `camera-controls` sur la foi d'un
     `data-panel` qui, là, ne bouge jamais : le visiteur héritait d'un viewer mort. */
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var GRAND = window.matchMedia('(min-width: 901px)');
  /* L'éclatement est exprimé en POURCENTAGE DU CURSEUR, pas en position dans le
     clip, et il est appliqué en pilotant le curseur lui-même. Sans cela le modèle
     s'ouvrirait pendant que la barre d'outils continue d'afficher « 0 % » — c'est
     exactement le défaut qui avait été corrigé sur la séquence de l'accueil, où le
     curseur restait figé sur une valeur que le modèle ne montrait plus. Un seul
     propriétaire de l'état d'éclatement : le module 12.
     Le dernier rayon est à 100 % et non 92 % (la valeur par défaut de la page) :
     à 92 % le boîtier touche le bas du cadre et passe sous la barre d'outils. */
  var POSES = [
    { orbit: '-124deg 55deg 104%', ex: 0 },
    { orbit: '-42deg 66deg 108%',  ex: 94 },
    { orbit: '24deg 72deg 100%',   ex: 0 }
  ];
  var slider = document.querySelector('[data-mv-action="explode-slider"]');
  function poser(pose) {
    viewer.cameraOrbit = pose.orbit;
    if (slider) {
      if (+slider.value !== pose.ex) {
        slider.value = String(pose.ex);
        slider.dispatchEvent(new Event('input', { bubbles: true }));
      }
    } else {
      viewer.currentTime = pose.ex / 100 * 0.98;
    }
  }
  var rotateBtn = document.querySelector('[data-mv-action="rotate"]');
  var etatRendu = false;
  var dernier = -1;

  function prendreLaMain() {
    if (etatRendu) return;
    viewer.removeAttribute('camera-controls');
    viewer.removeAttribute('auto-rotate');
    etatRendu = true;
  }
  function rendreLaMain() {
    if (!etatRendu) return;
    viewer.setAttribute('camera-controls', '');
    if (!rotateBtn || rotateBtn.getAttribute('aria-pressed') === 'true') {
      viewer.setAttribute('auto-rotate', '');
    }
    etatRendu = false;
  }

  function appliquer() {
    if (!GRAND.matches || !viewer.model) { rendreLaMain(); return; }
    var i = parseInt(rail.getAttribute('data-panel') || '-1', 10);
    if (isNaN(i) || i < 0) return;
    /* Le dernier temps rend la main : l'acte est une présentation, pas une prise
       d'otage. On garde sa pose, on rebranche seulement les contrôles. */
    if (i >= POSES.length - 1) {
      if (dernier !== i) {
        dernier = i;
        prendreLaMain();
        poser(POSES[i]);
      }
      rendreLaMain();
      return;
    }
    prendreLaMain();
    if (dernier === i) return;
    dernier = i;
    poser(POSES[i]);
  }

  /* `data-panel` change au franchissement, pas à chaque image : un
     MutationObserver suffit et ne coûte rien entre deux changements. */
  new MutationObserver(appliquer).observe(rail, { attributes: true, attributeFilter: ['data-panel'] });
  viewer.addEventListener('load', appliquer);
  GRAND.addEventListener('change', function () { dernier = -1; appliquer(); });
  appliquer();
}());
