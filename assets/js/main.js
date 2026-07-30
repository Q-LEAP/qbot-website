'use strict';

/* ════════════════════════════════════════
   0. DARK / LIGHT MODE — toggle bouton
   L'état initial est défini par theme-init.js
   (dans <head>) pour éviter le flash au chargement.
════════════════════════════════════════ */
(function () {
  var html = document.documentElement;
  var FR   = (html.lang || 'fr').slice(0, 2) !== 'en';

  function current()       { return html.getAttribute('data-theme') || 'light'; }

  function applyTheme(theme) {
    html.setAttribute('data-theme', theme);
    localStorage.setItem('qbot-theme', theme);
    updateBtn(theme);
  }

  function updateBtn(theme) {
    var btn = document.querySelector('.nav__theme-btn');
    if (!btn) return;
    var dark = theme === 'dark';
    btn.setAttribute('aria-label',
      dark
        ? (FR ? 'Activer le mode clair'  : 'Switch to light mode')
        : (FR ? 'Activer le mode sombre' : 'Switch to dark mode')
    );
    btn.setAttribute('aria-pressed', String(dark));
  }

  /* Injection du bouton dans .nav__actions, avant le bouton search */
  var actions = document.querySelector('.nav__actions');
  if (actions) {
    var btn = document.createElement('button');
    btn.className = 'nav__theme-btn';
    btn.type      = 'button';
    btn.setAttribute('aria-pressed', String(current() === 'dark'));
    btn.innerHTML =
      '<svg class="icon-sun" width="18" height="18" viewBox="0 0 24 24" fill="none"' +
      ' stroke="currentColor" stroke-width="2" aria-hidden="true">' +
        '<circle cx="12" cy="12" r="4"/>' +
        '<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41' +
              'M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>' +
      '</svg>' +
      '<svg class="icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none"' +
      ' stroke="currentColor" stroke-width="2" aria-hidden="true">' +
        '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>' +
      '</svg>';

    actions.insertBefore(btn, actions.firstElementChild);
    updateBtn(current());

    btn.addEventListener('click', function () {
      applyTheme(current() === 'dark' ? 'light' : 'dark');
    });
  }

  /* Suit les changements de préférence système (si pas de préférence stockée) */
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
    if (!localStorage.getItem('qbot-theme')) {
      applyTheme(e.matches ? 'dark' : 'light');
    }
  });
}());

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
   4. SCROLL REVEAL — classes CSS, stagger
════════════════════════════════════════ */
if ('IntersectionObserver' in window) {
  const REVEAL_SELECTORS = [
    '.feature-card',
    '.faq-item',
    '.timeline-item',
    '.product-card',
    '.stat-item',
    '.tool-tag',
    '.spec-item',
    '.contact-info__item',
    '.pricing-card',
    '.intro__image',
    '.specs__image',
    '.section-header',
    '.calendly-box',
    '.video__wrapper',
    '.badge-lux',
    '.model-viewer-frame',
  ].join(',');

  const revealEls = Array.from(document.querySelectorAll(REVEAL_SELECTORS));

  // Stagger : index dans le groupe parent, max 5 (= 400ms max)
  const groups = new Map();
  revealEls.forEach(el => {
    const parent = el.parentElement;
    if (!groups.has(parent)) groups.set(parent, []);
    groups.get(parent).push(el);
  });
  groups.forEach(children => {
    children.forEach((el, i) => {
      el.style.setProperty('--stagger-i', Math.min(i, 5));
    });
  });

  // Ajoute .reveal sans transition (évite le FOUC)
  revealEls.forEach(el => {
    el.classList.add('reveal');
    el.style.transition = 'none';
  });

  // Double RAF : re-active les transitions après le premier paint
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      revealEls.forEach(el => { el.style.transition = ''; });

      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        });
      }, { threshold: 0.08, rootMargin: '0px 0px -24px 0px' });

      revealEls.forEach(el => observer.observe(el));
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
   9. PARALLAX — index.html uniquement
   Trois couches de profondeur au scroll :
   orbes (lentes) · image hero · images de section.
   Utilise la propriété CSS `translate` individuelle
   pour composer sans conflit avec transform/animations.
════════════════════════════════════════ */
(function () {
  /* Uniquement sur l'index (seule page avec .hero) */
  var hero = document.querySelector('.hero');
  if (!hero) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var heroImg   = document.querySelector('.hero__image');
  var introImgs = Array.from(document.querySelectorAll('.intro__image img'));
  var root      = document.documentElement;
  var vh        = window.innerHeight;

  window.addEventListener('resize', function () { vh = window.innerHeight; }, { passive: true });

  var ticking = false;

  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;

    requestAnimationFrame(function () {
      var sy = window.scrollY;

      /* ── Couche 1 : orbes (très lentes, facteur 0.12) ── */
      root.style.setProperty('--orb-y', (sy * 0.12) + 'px');

      /* ── Couche 2 : image hero (facteur 0.20 → apparaît plus profonde) ── */
      if (heroImg) {
        heroImg.style.translate = '0 ' + (sy * 0.20) + 'px';
      }

      /* ── Couche 3 : images de section (parallax dans fenêtre overflow:hidden) ── */
      introImgs.forEach(function (img) {
        var rect    = img.getBoundingClientRect();
        if (rect.top > vh + 100 || rect.bottom < -100) return;
        /* Progress : 0 quand l'élément entre en bas, augmente en scrollant */
        var progress = (vh - rect.top) * 0.10;
        img.style.translate = '0 ' + progress + 'px';
      });

      ticking = false;
    });
  }, { passive: true });
}());

/* ════════════════════════════════════════
   10. CARD — Spotlight curseur + 3D tilt
   Feature cards et product cards réagissent
   au curseur : rotation 3D + halo teal.
════════════════════════════════════════ */
(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var FAST_TRANSITION = 'border-color 0.25s ease, box-shadow 0.3s ease, transform 0.07s ease';

  document.querySelectorAll('.feature-card, .product-card').forEach(function (card) {
    card.addEventListener('mouseenter', function () {
      card.style.willChange  = 'transform';
      card.style.transition  = FAST_TRANSITION;
    });

    card.addEventListener('mousemove', function (e) {
      var rect = card.getBoundingClientRect();
      var xRatio = (e.clientX - rect.left) / rect.width  - 0.5; // -0.5 → 0.5
      var yRatio = (e.clientY - rect.top)  / rect.height - 0.5;

      card.style.transform =
        'perspective(700px)' +
        ' rotateY(' + (xRatio * 14) + 'deg)' +
        ' rotateX(' + (-yRatio * 10) + 'deg)' +
        ' translateZ(8px) translateY(-6px)';

      card.style.setProperty('--spot-x', (e.clientX - rect.left) + 'px');
      card.style.setProperty('--spot-y', (e.clientY - rect.top)  + 'px');
    });

    card.addEventListener('mouseleave', function () {
      card.style.willChange  = '';
      card.style.transition  = '';
      card.style.transform   = '';
    });
  });
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

  var DAY_EXPOSURE   = Number(viewer.getAttribute('exposure')) || 1.1;
  var DAY_SHADOW     = Number(viewer.getAttribute('shadow-intensity')) || 1;
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
   10. MAGNETIC BUTTONS — CTA suit le curseur
   Les boutons principaux suivent légèrement
   le curseur pour un effet premium.
════════════════════════════════════════ */
(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (window.innerWidth < 1024) return; // touch screens

  var SELECTORS = '.hero__actions .btn, .page-hero .btn, .calendly-box .btn, .cta-section .btn';
  document.querySelectorAll(SELECTORS).forEach(function (btn) {
    btn.addEventListener('mousemove', function (e) {
      var rect = btn.getBoundingClientRect();
      var x = (e.clientX - rect.left  - rect.width  / 2) * 0.28;
      var y = (e.clientY - rect.top   - rect.height / 2) * 0.35;
      btn.style.transform = 'translate(' + x + 'px, ' + y + 'px) translateY(-1px)';
    });
    btn.addEventListener('mouseleave', function () {
      btn.style.transform = '';
    });
  });
}());