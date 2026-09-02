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

/* ── La barre reste visible ──
   Le masquage au défilement vers le bas a été retiré le 2026-08-28 à la
   demande du client : la barre doit rester sous les yeux en permanence.
   Elle garde son ombre au défilement (au-dessus) et sa position collante,
   qui vient du CSS. La classe .nav--hidden n'a plus d'utilisateur. */

// ── Toggle mobile ──
navToggle?.addEventListener('click', () => {
  const isOpen = navMenu.classList.toggle('open');
  navToggle.setAttribute('aria-expanded', String(isOpen));
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

   La comparaison porte sur l'ADRESSE RÉSOLUE, pas sur le nom de fichier.
   Comparer les noms marquait « Accueil » comme page courante sur toutes les
   pages qui s'appellent index.html sans être l'accueil : les quatre pages
   légales et les relais de redirection. Un « /faq/index.html » et un
   « /index.html » ont le même nom et ne sont pas la même page.
════════════════════════════════════════ */
{
  /* « /a/index.html » et « /a/ » désignent la même ressource : on ramène les
     deux à la forme répertoire avant de comparer. */
  const normaliser = (u) => u.pathname.replace(/index\.html$/, '');
  const ici = normaliser(window.location);

  document.querySelectorAll('.nav__link').forEach(link => {
    const href = link.getAttribute('href');
    if (!href) return;
    let cible;
    try { cible = normaliser(new URL(href, window.location.href)); } catch (e) { return; }
    if (cible !== ici) return;
    link.classList.add('active');
    /* La classe coloriait, elle n'annonçait rien : le lien de la page courante
       était un lien ordinaire pour un lecteur d'écran. `aria-current` le dit.
       Il reste un lien — c'est le motif attendu d'une navigation persistante,
       contrairement au fil d'Ariane où le dernier élément est la page. */
    link.setAttribute('aria-current', 'page');
  });
}

/* ════════════════════════════════════════
   3. FAQ ACCORDION — hauteur dynamique + aria

   Une réponse repliée l'était VISUELLEMENT seulement (`max-height: 0` +
   `overflow: hidden`). Rien ne la retirait de l'arbre d'accessibilité : une
   personne non-voyante s'entendait énoncer les dix-sept réponses d'affilée,
   et un lien contenu dans une réponse fermée restait atteignable au clavier.
   L'attribut `hidden` corrige les deux d'un coup.

   POURQUOI `hidden` EST POSÉ ICI ET NON DANS LE HTML. C'est l'écart délibéré
   avec le chantier 05 du plan de bascule. Le texte des réponses présent en
   clair dans la source est ce qui rend cette FAQ citable par un moteur ou une
   IA — l'audit le porte au crédit du site. Un `hidden` écrit dans le HTML le
   servirait comme contenu masqué à tout le monde, y compris aux robots, et
   retirerait les réponses du rendu pour un visiteur sans JavaScript. Posé par
   le script, il ne s'applique qu'aux navigateurs qui savent aussi rouvrir :
   sans JavaScript on retombe exactement sur l'état d'avant, pas plus mauvais.
════════════════════════════════════════ */
(function () {
  const boutons = document.querySelectorAll('.faq-item__question');
  if (!boutons.length) return;

  /* Durée du repli, lue dans la feuille de style plutôt que recopiée : la
     transition vaut 0.42s côté CSS, et deux constantes finiraient par diverger.
     La marge de 60 ms couvre le décalage entre la fin de la transition et le
     tour de boucle qui l'observe. */
  const REPLI_MS = 480;

  const replier = (item, immediat) => {
    const ans = item.querySelector('.faq-item__answer');
    if (!ans) return;
    ans.style.maxHeight = '0';
    if (immediat) { ans.hidden = true; return; }
    setTimeout(() => {
      /* Rouverte entre-temps : on ne la referme pas dans le dos du visiteur. */
      if (!item.classList.contains('open')) ans.hidden = true;
    }, REPLI_MS);
  };

  boutons.forEach(btn => {
    const item = btn.closest('.faq-item');
    btn.setAttribute('aria-expanded', 'false');
    /* État initial : toutes fermées. `immediat`, sinon les 17 réponses
       resteraient énoncées pendant la demi-seconde qui suit le chargement. */
    if (item) replier(item, true);

    btn.addEventListener('click', () => {
      const etaitOuvert = item.classList.contains('open');

      document.querySelectorAll('.faq-item.open').forEach(ouvert => {
        ouvert.classList.remove('open');
        ouvert.querySelector('.faq-item__question')
              ?.setAttribute('aria-expanded', 'false');
        replier(ouvert, false);
      });

      if (!etaitOuvert) {
        item.classList.add('open');
        btn.setAttribute('aria-expanded', 'true');

        const answer = item.querySelector('.faq-item__answer');
        if (answer) {
          /* L'ORDRE DE CES DEUX LIGNES EST LA CORRECTION. Un élément `hidden`
             est en `display: none` et mesure zéro : mesurer avant de le
             démasquer donnerait une réponse ouverte sur une hauteur nulle,
             donc vide. La lecture de `scrollHeight` force au passage le calcul
             de mise en page, ce qui est aussi ce qui permet à la transition
             de partir de `max-height: 0` au lieu de sauter.

             Et c'est `scrollHeight` du conteneur entier, pas de son premier
             enfant : une réponse à plusieurs <p>/<ul> voyait tout le reste
             tronqué. */
          answer.hidden = false;
          answer.style.maxHeight = answer.scrollHeight + 'px';
        }
      }
    });
  });
}());

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
    /* EN PREMIER, donc gagnant : les blocs de code de la bande d'exemples de la page
       des cas d'usage. Ils entrent PAR LA DROITE, poussés par le défilement ; un
       masque qui remonte et un passage de lumière verticaux n'ont aucun sens sur un
       objet qui glisse latéralement, et les cinq cartes se révélant au même instant,
       les cinq éclats se voyaient ensemble. Ils gardent la montée et le fondu. */
    // `.ucs-api__track` n'existe plus dans aucune page depuis le 2026-09-02 (la
    // bande d'exemples est devenue un accordéon). L'entrée reste : un sélecteur
    // qui ne correspond à rien ne coûte rien, et le jour où la bande revient,
    // elle retrouve sa variante « plain ». Cf. la note du CSS.
    ['plain', ['.ucs-api__track .code-block']],
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
      /* Le bloc de code de la section API : c'est un objet encadré, donc un média
         au sens du site. Il apparaissait sans rien. Il n'a pas d'<img>, donc le
         dézoom de la variante ne s'applique à rien et seul le masque joue. */
      '.code-block',
    ]],
    ['group', [
      '.section-header',
      /* Colonne de texte d'une section intro : label → titre → paragraphes
         arrivent en cascade. `:not()` écarte la colonne image du même grid. */
      '.intro__grid > div:not(.intro__image)',
    ]],
    /* La variante « éventail » doit précéder « carte » : un élément ne prend que la
       première variante qui le désigne. Réservée aux grilles à plusieurs colonnes —
       les quatre atouts (accueil, caracteristiques) et les six garanties
       (commandez). Écartés à dessein : les listes verticales (`.spec-item`,
       `.faq-item`, `.product-card`, `.contact-info__item`), où une rotation ne se
       lirait pas comme un éventail mais comme des lignes de guingois ; `.evo-card`,
       dont la pastille doit atterrir sur le rail de la section au pixel près ; et
       `.blog-card`, qui n'est que deux cartes.
       `.guarantee-item` n'avait AUCUNE révélation jusqu'ici — ni elle, ni sa grille :
       six cartes arrivaient sans entrée alors que toutes les autres grilles du site
       en ont une. Elles la reçoivent ici. */
    ['fan', [
      '.feature-card',
      '.guarantee-item',
      /* Les cases de la matrice de compatibilité : c'est cette révélation qui leur
         donne `.is-visible` et `--stagger-i`, dont dépend le tracé du liseré (cf.
         la feuille de style, section « matrice de compatibilité »). */
      '.compat__item',
    ]],
    /* La note en tête d'article : montée et fondu, sans flou. Elle est courte et
       posée haut dans la page, un flou n'y ajouterait rien. */
    /* La note d'article et les lignes de faits à coche : montée et fondu, sans
       flou. Les faits sont courts et nombreux, un flou par ligne coûterait une
       couche de composition pour rien. C'est aussi ce qui donne aux coches leur
       `.is-visible` et leur `--stagger-i`, dont dépend le tracé (cf. la feuille
       de style, section « coches qui se dessinent »). */
    ['plain', ['.article-note', '.api-facts li']],
    ['card', [
      /* Les titres de section d'un article arrivent un à un. Le corps entier est
         déjà une révélation « plain » — un seul fondu pour plusieurs milliers de
         pixels — donc rien ne marquait le passage d'une partie à l'autre. */
      '.article-body h2',
      '.faq-item',
      '.timeline-item',
      '.evo-card',
      '.product-card',
      '.stat-item',
      '.spec-item',
      '.contact-info__item',
      '.pricing-card',
      /* Les cinq cas d'usage de la page commande n'avaient aucune entrée, ni eux ni
         leurs volets : cinq blocs qui apparaissent d'un coup sur la page où l'on
         décide d'acheter. Le liseré teal de leur volet « solution » se dessine
         ensuite, cf. la feuille de style. */
      '.usecase',
      /* Ajouté pour le liseré vivant : il se déclenche sur .is-visible, que
         seul le système de révélation pose. Effet de bord assumé et
         cohérent — le bloc prend l'arrivée standard des cartes du site. */
      '.pricing-highlight',
      '.blog-card',
      '.booking-box',
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

}());

  /* ══════════════════════════════════════════════════════════════════════════
     7 bis. BOUTON COPIER SUR LES BLOCS DE CODE
     ══════════════════════════════════════════════════════════════════════════
     Sorti du module 7, qui s'arrête net s'il n'y a pas d'article sur la page
     (`if (!articleBody) return;`) : le temps de lecture et la barre de
     progression n'ont pas de sens ailleurs, mais un bloc de code, si. La section
     API de la page Caractéristiques en porte un, et un exemple d'appel qu'on ne
     peut pas copier ne sert à rien. Le défaut ne se voyait pas : le bouton
     n'apparaissait simplement pas, sans erreur.                                 */
  (function () {
    if (!navigator.clipboard) return;
    var FR = document.documentElement.lang !== 'en';
    document.querySelectorAll('.article-body pre, .code-block pre').forEach(function (pre) {
      var copyBtn = document.createElement('button');
      copyBtn.className = 'code-copy-btn';
      copyBtn.textContent = FR ? 'Copier' : 'Copy';
      copyBtn.setAttribute('aria-label', FR ? 'Copier le code' : 'Copy code');
      copyBtn.addEventListener('click', function () {
        var code = pre.querySelector('code');
        var text = (code || pre).innerText || (code || pre).textContent || '';
        navigator.clipboard.writeText(text).then(function () {
          copyBtn.textContent = FR ? 'Copié !' : 'Copied!';
          copyBtn.classList.add('copied');
          setTimeout(function () {
            copyBtn.textContent = FR ? 'Copier' : 'Copy';
            copyBtn.classList.remove('copied');
          }, 2000);
        }).catch(function () { /* silencieux si refusé */ });
      });
      /* Le bouton va dans le BANDEAU du bloc quand il y en a un (les exemples
         d'appel de la page des cas d'usage) : posé dans le `pre`, il se retrouvait
         au-dessus des lignes de code, qui passaient dessous — et il défilait avec
         elles dès qu'une ligne dépassait. Ailleurs (un bloc de code d'article), on
         garde le coin supérieur droit, faute de bandeau où le mettre. */
      var fig = pre.closest('figure');
      var bandeau = fig && fig.querySelector(':scope > figcaption');
      if (bandeau) {
        bandeau.appendChild(copyBtn);
      } else {
        pre.style.position = 'relative';
        pre.appendChild(copyBtn);
      }
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
    ['.intro__image:not(.intro__image--product):not(.intro__image--fit) img', -14],
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
    /* `.evolution__rail` était ici : son trait teal se remplissait au scroll.
       Retiré — ce trait indique où en est le PRODUIT (il s'arrête sur le point
       « Génération actuelle »), pas où en est la lecture ; scrubbé, il
       s'allongeait et se raccourcissait et ne collait plus à son point. Il est
       désormais figé en CSS (--evo-fill). Aucune page ne porte plus de
       `.timeline`, donc ce tableau ne pilote aujourd'hui plus rien : on le
       garde parce que c'est le chemin de code d'une progression scrubbée. */
    /* La colonne vertébrale des cas d'usage : elle se remplit à mesure qu'on lit
       les cinq cas. Premier usage réel de ce tableau depuis le retrait de
       `.timeline`. Le modèle de la ligne de lecture est le bon ici — le bloc
       TRAVERSE le viewport, il n'est pas épinglé (seul le schéma l'est). */
    /* La séquence des cas d'usage : rail épinglé, cinq états. Le moteur écrit la
       progression ET le numéro du cas, comme pour l'acte épinglé de la page
       Caractéristiques. C'est ce qui a permis de supprimer l'observateur
       d'intersection qui s'en chargeait : une seule grandeur gouverne la carte
       affichée, le halo, l'index et le rail, donc rien ne peut se désynchroniser. */
    /* La bande d'exemples d'appel : le troisième argument dit au moteur que c'est
       un rail ÉPINGLÉ (mesuré à sa course de collage et non à la ligne de lecture)
       et lui fait écrire `data-panel`, qui sert ici à marquer la carte en cours. */
    // Idem : plus aucune page ne porte `.ucs-api`, le moteur n'a donc rien à
    // scruber ici. Gardé pour la même raison.
    ['.ucs-api', '--api-p', 5],
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
      /* La classe dit « cet élément est scrubbé par le moteur ». Elle permet à la
         feuille de style de ne poser une mise en scène épinglée QUE si le moteur
         tourne : sans JavaScript, une section épinglée dont le numéro d'état ne
         bouge jamais cache tout son contenu sauf le premier état. */
      el.classList.add('mx-scrubbed');
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

  /* POURQUOI ON ATTEND LA DÉFINITION DU COMPOSANT.

     `viewer.src = …` posé sur un <model-viewer> pas encore PROMU crée une
     propriété propre sur l'élément. Quand le composant est défini ensuite, cette
     propriété propre MASQUE l'accesseur du prototype : le setter ne s'exécute
     jamais et le modèle ne charge plus, sans une ligne d'erreur.

     Le cas s'est produit le 2026-08-25 en rapatriant la visionneuse : elle est
     désormais chargée par un `import()` dynamique, donc définie strictement plus
     tard qu'avec une balise statique. En file:// la source est le CDN, donc un
     aller-retour réseau, pendant lequel ce fichier-ci (local, instantané) passait
     devant. Chromium ne chargeait plus rien, WebKit s'en sortait par chance
     d'ordonnancement : le pire des symptômes, un défaut qui dépend du moteur.

     `whenDefined` supprime la classe entière de bug, quel que soit l'ordre. */
  if (window.location.protocol === 'file:') {
    if (window.customElements && customElements.whenDefined) {
      customElements.whenDefined('model-viewer').then(function () {
        loadSrc(STANDARD_SRC);
      });
    } else {
      loadSrc(STANDARD_SRC);
    }
  }

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

  var SELECTORS = '.hero__actions .btn, .page-hero .btn, .booking-box .btn, .cta-section .btn';
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
   14. (retiré) : garde-fou du film du hero
   Ce module coupait la lecture automatique du film pour `prefers-reduced-motion`
   et pour l'économiseur de données. Il visait `.hero__film-video`, classe
   qu'aucune page ne porte depuis que le film a quitté le hero, et son garde-fou
   vit désormais dans le module 18, qui pilote le film là où il se trouve.
   Le numéro n'est pas réattribué : deux ans de messages de commit y renvoient.
════════════════════════════════════════ */

/* ════════════════════════════════════════
   15. FORMULAIRES — plus jamais d'envoi qui disparaît
   Les formulaires du site (à l'origine six : contact FR/EN, newsletter des deux
   homepages et des deux index de blog) étaient en `action="#"` : le visiteur remplissait,
   cliquait, la page se rechargeait, sa saisie était perdue — et rien n'indiquait
   l'échec. C'est le pire des trois cas possibles, parce qu'il est invisible.

   UN SEUL POINT DE CONFIGURATION : l'attribut `data-endpoint` du <form>.
     data-endpoint=""                     → repli courrier
     data-endpoint="https://…/f/xxxx"     → envoi HTTP, sans toucher au reste

   OÙ EN SONT LES FORMULAIRES (2026-09-02). IL N'EN RESTE QUE DEUX, les deux
   contacts, et ils passent par le logiciel de courrier du visiteur PAR DÉCISION
   DU CLIENT du 2026-08-26 (« ne me fais pas passer par des sites tiers pour
   contact, tant pis ça ouvrira une boîte mail »). Ce n'est donc pas un point
   ouvert, et `data-endpoint` reste vide à dessein.
   LES QUATRE NEWSLETTERS ONT DISPARU : les deux des index de blog avec le blog
   (2026-08-28), les deux des accueils le 2026-09-02, remplacées par une ligne
   du pied de page (« l'emailing on n'est pas près d'en avoir un »). Le profil
   Brevo et les libellés `okNews` / `sujetN` ci-dessous n'ont donc plus
   d'appelant : ils sont GARDÉS parce qu'ils portent la correspondance de champs
   relevée sur le formulaire du client, qui ne se redevine pas, et parce que le
   mécanisme redevient utile le jour où un formulaire revient.

   Si le service impose ses propres noms de champs, ils se déclarent par
   `data-endpoint-kind` et la correspondance vit dans PROFILS ci-dessous, jamais
   dans le balisage.

   Sans endpoint, on n'invente pas un envoi : on ouvre le client courrier du
   visiteur avec un message déjà rédigé. Ce n'est pas idéal — il faut qu'il
   appuie sur « envoyer » — mais rien n'est perdu et il le SAIT.
════════════════════════════════════════ */
(function () {
  var forms = document.querySelectorAll('form[data-form]');
  if (!forms.length) return;

  var FR = (document.documentElement.lang || 'fr').slice(0, 2) !== 'en';
  var MAIL = 'bot@q-leap.eu';
  /* 1900 et non 2048 : marge pour l'objet, l'adresse et l'encodage du
     protocole par le système, qui ne sont pas tous comptés pareil. */
  var MAILTO_MAX = 1900;
  var T = FR ? {
    envoi:   'Envoi en cours…',
    ok:      'Merci, votre message est parti. Nous revenons vers vous rapidement.',
    okNews:  'Merci, votre inscription est enregistrée.',
    manque:  'Merci de compléter les champs obligatoires.',
    courrier:'Votre logiciel de courrier vient de s’ouvrir avec le message prérempli : il reste à appuyer sur « envoyer ». S’il ne s’est pas ouvert, copiez votre message ci-dessous.',
    secours: 'Votre message, prêt à copier. À envoyer à ',
    longCourrier:'Votre message est long : certains logiciels de courrier le tronquent. Vérifiez qu’il est entier avant d’envoyer, ou copiez-le ci-dessous.',
    copier:  'Copier le message',
    copie:   'Message copié',
    aChamp:  'À',
    objet:   'Objet',
    echecCourrier:'L’envoi direct a échoué. Votre logiciel de courrier vient de s’ouvrir avec le message prérempli. S’il ne s’est pas ouvert, copiez votre message ci-dessous et envoyez-le à {MAIL}.',
    sujetC:  'Demande via le site Q-Bot',
    sujetN:  'Inscription à la newsletter Q-Bot'
  } : {
    envoi:   'Sending…',
    ok:      'Thank you, your message is on its way. We will get back to you shortly.',
    okNews:  'Thank you, your subscription is registered.',
    manque:  'Please fill in the required fields.',
    courrier:'Your mail application just opened with the message prefilled: all that is left is to hit send. If it did not open, copy your message below.',
    secours: 'Your message, ready to copy. Send it to ',
    longCourrier:'Your message is long, and some mail applications truncate it. Check that it arrived whole before sending, or copy it below.',
    copier:  'Copy the message',
    copie:   'Message copied',
    aChamp:  'To',
    objet:   'Subject',
    echecCourrier:'Direct submission failed. Your mail application just opened with the message prefilled. If it did not open, copy your message below and send it to {MAIL}.',
    sujetC:  'Enquiry from the Q-Bot website',
    sujetN:  'Q-Bot newsletter subscription'
  };

  /* CORRESPONDANCE DES NOMS DE CHAMPS. Certains services imposent les leurs, et
     on ne renomme PAS dans le HTML : `email` et `consent` sont les noms du site,
     et le repli courrier comme la validation s'appuient dessus. La table vit ici,
     et le formulaire déclare son profil par `data-endpoint-kind`.

     Brevo (ex-Sendinblue) : relevé sur le formulaire du live q-bot.eu le
     2026-08-26. Il attend EMAIL, OPT_IN à la valeur « 1 » (et non le « on » par
     défaut d'une case sans attribut `value`), le pot de miel
     `email_address_check` qui doit partir VIDE, et `locale`. Son endpoint est
     déclaré en `application/x-www-form-urlencoded` et non en multipart : on lui
     envoie donc un URLSearchParams, dont fetch déduit seul le bon Content-Type.
     Les deux valeurs restent des en-têtes autorisés sans pré-vol CORS, ce qui
     est ce qui permet de lire la réponse (mesuré : `type: 'cors'`, 200,
     `{"success":true}`). */
  var PROFILS = {
    brevo: {
      noms:    { email: 'EMAIL', consent: 'OPT_IN' },
      valeurs: { OPT_IN: '1' },
      urlencode: true
    }
  };

  /* Ce qui part réellement. Sans profil, le multipart du formulaire tel quel :
     c'est ce qu'attendent Formspree et compagnie. */
  function charge(form) {
    var fd = new FormData(form);
    var prof = PROFILS[form.getAttribute('data-endpoint-kind')];
    if (!prof || !prof.urlencode) return fd;

    var p = new URLSearchParams();
    fd.forEach(function (v, k) {
      var nom = (prof.noms && prof.noms[k]) || k;
      p.append(nom, (prof.valeurs && prof.valeurs[nom] !== undefined) ? prof.valeurs[nom] : v);
    });
    var loc = form.getAttribute('data-locale');
    if (loc && !p.has('locale')) p.append('locale', loc);
    return p;
  }

  /* LE BLOC DE SECOURS, ET POURQUOI IL EXISTE. Un `mailto:` est le seul envoi
     qu'un site statique sache faire sans sous-traitant, mais il a un défaut qui
     ne se voit pas : sur un poste sans logiciel de courrier associé (webmail,
     téléphone sans compte configuré), il ne se passe RIEN. Le visiteur a rempli
     sept champs, cliqué, et son écran n'a pas bougé. C'est la famille de défauts
     que ce module a été écrit pour supprimer, et il en restait un.

     Le message composé est donc aussi PRÉSENTÉ, avec un bouton de copie et
     l'adresse. Rien n'est envoyé, rien ne quitte la page : c'est le même texte
     que le courrier, montré au lieu d'être seulement passé au système.

     Il est construit ici et non écrit dans les six pages : c'est un état
     d'exception, il n'a pas à peser sur le balisage servi. */
  function secours(form, dest, sujet) {
    var bloc = form.querySelector('.form-relay');
    if (!bloc) {
      bloc = document.createElement('div');
      bloc.className = 'form-relay';
      bloc.hidden = true;
      bloc.innerHTML =
          '<p class="form-relay__lead"></p>'
        + '<textarea class="form-relay__text" readonly rows="7" spellcheck="false"></textarea>'
        + '<button type="button" class="form-relay__copy"></button>';

      var apres = form.querySelector('.form-status');
      if (apres && apres.parentNode === form) form.insertBefore(bloc, apres.nextSibling);
      else form.appendChild(bloc);
    }

    var lead = bloc.querySelector('.form-relay__lead');
    var zone = bloc.querySelector('.form-relay__text');
    var bout = bloc.querySelector('.form-relay__copy');

    lead.textContent = T.secours;
    var lien = document.createElement('a');
    lien.href = 'mailto:' + dest;
    lien.textContent = dest;
    lead.appendChild(lien);

    zone.value = T.aChamp + ' : ' + dest + '\n'
               + T.objet  + ' : ' + sujet + '\n\n'
               + corps(form);
    bout.textContent = T.copier;
    bloc.hidden = false;

    if (!bout.getAttribute('data-lie')) {
      bout.setAttribute('data-lie', '1');
      bout.addEventListener('click', function () {
        /* On sélectionne AVANT toute tentative : si les deux mécanismes de copie
           échouent (contexte non sécurisé, permission refusée), le texte reste
           sélectionné et il n'y a plus qu'à faire Cmd+C. Un plancher, jamais un
           bouton qui ne fait rien. */
        zone.focus();
        zone.select();
        var confirme = function () {
          bout.textContent = T.copie;
          setTimeout(function () { bout.textContent = T.copier; }, 2200);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(zone.value).then(confirme, function () {});
          return;
        }
        try { if (document.execCommand('copy')) confirme(); } catch (e) {}
      });
    }
  }

  function dire(form, texte, type) {
    var el = form.querySelector('.form-status');
    if (!el) return;
    el.textContent = texte;
    el.hidden = false;
    el.setAttribute('data-state', type);
  }

  /* Corps du courrier : « Libellé : valeur », un champ par ligne. On prend le
     <label> associé quand il existe, sinon le nom du champ — le destinataire lit
     ainsi le message dans les mots du formulaire.

     LE LIBELLÉ SE LIT DANS `el.labels`, PAS DANS UN `label[for=…]` CHERCHÉ À LA
     MAIN, et la différence n'est pas cosmétique : `labels` reconnaît aussi le
     libellé qui ENVELOPPE son champ, ce qui est la forme de toutes les mentions
     de consentement du site. Sans ça, une case sans `id` retombait sur son
     attribut `name` et le courrier portait « consent : oui » au lieu de la phrase
     acceptée, or pour une trace de consentement c'est la phrase qui a de la
     valeur, pas le mot. Les `id` ont été posés en plus, mais le repli ne doit pas
     dépendre d'eux.

     Les espaces sont ramenés à un seul : un libellé écrit sur plusieurs lignes de
     source (les mentions de consentement le sont toutes) insérait ses retours à
     la ligne dans le message et cassait le « un champ par ligne ». */
  function corps(form) {
    var lignes = [];
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.type === 'submit' || el.type === 'button') return;
      /* Une liste déroulante part avec le LIBELLÉ choisi, pas son code : le
         message disait « Sujet : demo » là où le visiteur avait lu « Demande de
         démonstration ». Le destinataire doit lire ce que le visiteur a vu. */
      var v = el.type === 'checkbox' ? (el.checked ? (FR ? 'oui' : 'yes') : (FR ? 'non' : 'no'))
            : (el.tagName === 'SELECT' && el.selectedIndex >= 0 ? el.options[el.selectedIndex].text.trim() : el.value);
      if (!v) return;
      var lab = (el.labels && el.labels[0]) || form.querySelector('label[for="' + el.id + '"]');
      var nom = (lab ? lab.textContent : el.name).replace(/\s+/g, ' ').replace(/\s*\*\s*$/, '').trim();
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

      /* LE REPLI COURRIER N'EST PLUS SEULEMENT L'ÉTAT « PAS D'ENDPOINT », C'EST
         AUSSI LE FILET QUAND L'ENVOI ÉCHOUE. Sans lui, un endpoint qui refuse
         laisse le visiteur devant « l'envoi a échoué » et rien d'autre : un
         cul-de-sac, alors que le site sait parfaitement composer le message.
         Constaté en vrai le 2026-08-26 : Brevo refuse nos envois en 400 faute de
         jeton reCAPTCHA, et la bande newsletter ne proposait plus aucune issue. */
      /* LA DESTINATION EST CELLE DU FORMULAIRE, pas une constante du script.
         `data-mailto` sur le <form>, `bot@q-leap.eu` par défaut. Les demandes de
         contact partent sur `contact@q-leap.eu`, qui est déjà l'adresse des
         quatre pages légales du site : les formulaires étaient les seuls à ne pas
         la suivre. Un seul attribut à changer si une adresse bouge. */
      function versCourrier(message, etat) {
        var dest = (form.getAttribute('data-mailto') || '').trim() || MAIL;

        /* Le sujet reprend le motif choisi dans la liste : « Demande via le site
           Q-Bot : Questions tarifaires » se trie sans ouvrir le message. */
        var sujet = news ? T.sujetN : T.sujetC;
        var motif = form.querySelector('select[name="subject"]');
        if (motif && motif.value && motif.selectedIndex >= 0) {
          sujet += ' : ' + motif.options[motif.selectedIndex].text.trim();
        }

        var lien = 'mailto:' + dest
          + '?subject=' + encodeURIComponent(sujet)
          + '&body=' + encodeURIComponent(corps(form));

        /* LA LONGUEUR D'UN `mailto:` N'EST PAS ILLIMITÉE, et ce chemin est
           désormais le chemin DÉFINITIF du formulaire de contact, pas un
           provisoire : le cas limite compte donc pour de vrai. Mesuré sur ce
           formulaire, une demande de 1 000 caractères produit une URL de 1 964,
           et plusieurs logiciels (Outlook, les gestionnaires Windows) tronquent
           vers 2 048.
           ON NE DÉGRADE PAS POUR AUTANT : envoyer un objet sans corps pénaliserait
           tout le monde pour protéger une minorité. Le message part entier, et
           au-delà du seuil le visiteur est AVERTI qu'il doit vérifier, avec le
           texte copiable juste en dessous. Prévenir plutôt que tronquer en
           silence. */
        window.location.href = lien;
        dire(form, (lien.length > MAILTO_MAX ? T.longCourrier : message).replace('{MAIL}', dest), etat);
        secours(form, dest, sujet);
      }

      if (!url) {                                   // pas d'endpoint du tout
        versCourrier(T.courrier, 'info');
        return;
      }

      dire(form, T.envoi, 'info');
      var bouton = form.querySelector('[type="submit"]');
      if (bouton) bouton.disabled = true;
      fetch(url, { method: 'POST', body: charge(form), headers: { Accept: 'application/json' } })
        .then(function (r) {
          if (!r.ok) throw new Error(r.status);
          form.reset();
          dire(form, news ? T.okNews : T.ok, 'ok');
        })
        .catch(function () { versCourrier(T.echecCourrier, 'info'); })
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




/* ════════════════════════════════════════
   17. CALCULATEUR DE ROI : ce que la 2FA coûte déjà
   Deux curseurs sur commandez / order, en remplacement du prix (arbitrage
   client du 2026-08-24 : le tarif n'est plus prononcé, il est retourné en ROI).

   LE CALCUL EST UNE MULTIPLICATION, ET IL EST AFFICHÉ. testeurs × minutes par
   jour × 21 jours ouvrés = minutes par mois. Puis, pour l'équivalence,
   ÷ 7 heures = journées de test. Aucun euro : convertir demanderait un coût
   horaire, donc un troisième curseur ou une hypothèse inventée. Le lecteur fait
   la multiplication par son propre taux s'il le veut, et ce sera son chiffre.

   TROIS POINTS À NE PAS DÉFAIRE :
   1. le module ne CRÉE rien. Les valeurs du HTML sont déjà celles des positions
     par défaut, curseurs et rails compris. Sans JavaScript le bloc se lit juste,
     il ne réagit plus. C'est la règle du dépôt appliquée à un calcul ;
   2. `--roi-p` est écrite ici parce que WebKit et Chromium n'ont pas
     l'équivalent de `::-moz-range-progress`. Firefox remplit son rail seul et
     n'a donc pas besoin de cette écriture, mais on la fait quand même : elle
     n'y sert à rien et ne coûte rien ;
   3. les libellés au singulier (« 1 testeur ») ne sont pas un détail : la
     formule est LUE, c'est tout son intérêt, et « 1 testeurs » la décrédibilise.

   L'espace insécable est celui du reste du site : « 36 h 45 », « 35 min » ne
   doivent pas se couper en fin de ligne.
════════════════════════════════════════ */
(function () {
  var bloc = document.querySelector('[data-roi]');
  if (!bloc) return;

  var JOURS  = 21;   /* jours ouvrés par mois, arrondi usuel */
  var HEURES = 7;    /* une journée de test */
  var NBSP   = ' ';

  var EN = (document.documentElement.lang || 'fr').slice(0, 2) === 'en';
  var T = EN ? {
    tester: 'tester', testers: 'testers', jours: 'working days', min: 'min'
  } : {
    tester: 'testeur', testers: 'testeurs', jours: 'jours ouvrés', min: 'min'
  };

  var inputs = {};
  var outs   = {};
  Array.prototype.forEach.call(bloc.querySelectorAll('[data-roi-in]'), function (el) {
    inputs[el.getAttribute('data-roi-in')] = el;
  });
  Array.prototype.forEach.call(bloc.querySelectorAll('[data-roi-out]'), function (el) {
    outs[el.getAttribute('data-roi-out')] = el;
  });
  if (!inputs.people || !inputs.min) return;

  /* Une décimale, mais jamais un « ,0 » traînant : « 24,0 journées » se lit
     comme un défaut d'affichage, « 24 journées » comme une mesure. */
  function decimal(n) {
    var s = n.toFixed(1).replace(/\.0$/, '');
    return EN ? s : s.replace('.', ',');
  }

  function rail(el) {
    var min = parseFloat(el.min), max = parseFloat(el.max), v = parseFloat(el.value);
    el.style.setProperty('--roi-p', ((v - min) / (max - min) * 100).toFixed(1) + '%');
  }

  function rendre() {
    var p = parseInt(inputs.people.value, 10);
    var m = parseInt(inputs.min.value, 10);
    var total = p * m * JOURS;                  /* minutes par mois */
    var h = Math.floor(total / 60), r = total % 60;

    rail(inputs.people); rail(inputs.min);

    if (outs.people)  outs.people.textContent = String(p);
    if (outs.min)     outs.min.textContent    = m + NBSP + T.min;
    if (outs.hours)   outs.hours.textContent  =
      r ? h + NBSP + 'h' + NBSP + (r < 10 ? '0' + r : r) : h + NBSP + 'h';
    if (outs.days)    outs.days.textContent   = decimal(total / 60 / HEURES);
    if (outs.formula) outs.formula.textContent =
      p + ' ' + (p > 1 ? T.testers : T.tester) + ' × ' + m + ' min × ' + JOURS + ' ' + T.jours;
  }

  inputs.people.addEventListener('input', rendre);
  inputs.min.addEventListener('input', rendre);
  rendre();
}());


/* ════════════════════════════════════════
   18. LES FILMS : chargés à l'approche, en pause hors champ
   Demandé par le client le 2026-08-25 pour la boucle : « vraiment juste une vidéo
   loop ». Ces boucles ne portent donc ni `controls` ni `src`, et le CSS coupe
   leurs `pointer-events` pour qu'il n'y ait rien non plus au clic droit.

   DEPUIS LE 2026-09-02, UN DES FILMS SE PILOTE. Le film de démonstration est
   entré dans l'accueil (« c'est un bon moyen de comprendre ce que fait Q-Bot »)
   et il dure cinquante secondes : il porte `controls`. Le module ne fait aucune
   différence entre les deux, sauf sur un point, plus bas : il ne redémarre pas un
   film que le VISITEUR a mis en pause.

   POURQUOI LE `src` EST DANS `data-film` ET NON DANS L'ATTRIBUT. Le fichier pèse
   2,9 Mo et la section est à environ 5 000 px du haut de la page. Avec un `src`
   et `autoplay`, le navigateur le télécharge dès l'arrivée sur l'accueil, qu'on
   descende ou non : le premier écran paierait 2,9 Mo pour une boucle que la
   plupart des visiteurs ne verront jamais. Ici le fichier est demandé quand la
   section approche, avec 200 px d'avance, si bien qu'elle tourne déjà quand elle
   entre dans le champ. Le visiteur voit exactement ce qu'il a demandé.

   200 px D'AVANCE ET PAS 400 : la leçon du 2026-08-20 sur le filet de la séquence
   3D. Une marge trop large arme l'observateur dès le chargement sur un téléphone,
   ce qui annule tout le bénéfice.

   ELLE SE MET EN PAUSE HORS CHAMP. Un `<video>` hors écran continue d'être décodé
   dans plusieurs navigateurs : c'est de la batterie dépensée pour une boucle que
   personne ne regarde. L'observateur n'est donc pas déconnecté après le premier
   passage, il pilote lecture et pause.

   ON NE CHARGE RIEN DU TOUT en mouvement réduit, en économiseur de données ou sur
   connexion lente : l'affiche reste, et c'est une vraie image du film. Une boucle
   décorative de 2,9 Mo n'a pas à s'imposer à quelqu'un qui a dit le contraire.
   Ce garde-fou remplace l'ancien module 14, qui visait `.hero__film-video`, une
   classe qu'aucune page ne porte plus.
════════════════════════════════════════ */
(function () {
  /* PLUSIEURS films, depuis le 2026-08-31 : l'accueil en a un, la fiche technique
     porte désormais la boucle du boîtier en action. Un seul mécanisme pour les deux. */
  var films = document.querySelectorAll('.video__player[data-film]');
  if (!films.length) return;

  var co = navigator.connection || {};
  var lente = co.saveData === true ||
              co.effectiveType === '2g' || co.effectiveType === 'slow-2g' ||
              (co.effectiveType === '3g' && (co.downlink || 99) < 1.2);
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || lente) return;

  Array.prototype.forEach.call(films, function (film) {
    function essayer() {
      var p = film.play();
      /* Si le navigateur refuse malgré `muted`, on ne laisse pas un cadre noir :
         l'affiche est toujours là, elle fait le travail. */
      if (p && p.catch) p.catch(function () {});
    }

    function jouer() {
      if (!film.getAttribute('src')) {
        /* `preload` passe à `auto` AVANT le `src`. La balise n'en porte plus dans le
           HTML : `preload="none"` y disait au navigateur de ne rien tamponner, ce qui
           contrarie une lecture automatique dès que le fichier est branché. */
        film.preload = 'auto';
        film.setAttribute('src', film.getAttribute('data-film'));
        /* `load()` explicite, et un second essai à `canplay`. Safari rejette un
           `play()` appelé dans le même tour de boucle que l'affectation du `src`,
           parce qu'aucune donnée n'est encore arrivée ; le `catch` avalait cet échec
           en silence et l'affiche restait. Deux tentatives, dont une quand le
           navigateur dit lui-même qu'il est prêt. */
        film.load();
        film.addEventListener('canplay', essayer, { once: true });
      }
      essayer();
    }

    if (!('IntersectionObserver' in window)) { jouer(); return; }

    /* ON NE REDÉMARRE PAS UN FILM QUE LE VISITEUR A ARRÊTÉ. Sur un film à
       commandes, sortir du champ puis revenir relançait la lecture par-dessus sa
       décision. Le discriminant est simple et n'a pas besoin d'un drapeau autour
       de notre propre appel : le module ne met en pause que HORS champ, donc une
       pause survenue DANS le champ vient forcément de lui. Repartir en lecture
       lui rend la main. */
    var visible = false, manuel = false;
    film.addEventListener('pause', function () { if (visible) manuel = true; });
    film.addEventListener('play', function () { manuel = false; });

    new IntersectionObserver(function (entrees) {
      entrees.forEach(function (e) {
        visible = e.isIntersecting;
        if (e.isIntersecting) { if (!manuel) jouer(); }
        else if (film.getAttribute('src')) film.pause();
      });
    }, { rootMargin: '200px 0px' }).observe(film);
  });
}());

/* ═══════════════════════════════════════════════════════════════════════
   19. LA CARTE DE CONTACT NE SE CHARGE QU'AU CLIC

   L'iframe Google était servie au chargement de la page : elle dépose ses
   cookies avant que le visiteur ait rien demandé, sur un site qui publie une
   page Confidentialité juste en dessous. Le balisage porte désormais un cadre
   avec l'adresse et un bouton ; l'iframe est CRÉÉE au clic, et le bouton dit
   ce que ce clic déclenche.

   Trois choses à ne pas défaire :

   • l'adresse est dans le HTML, pas dans le script. Sans JavaScript, on lit
     l'adresse et on a le lien « itinéraire » : l'état au repos est un état
     complet, comme pour le film de l'accueil.
   • l'iframe garde `loading="lazy"` : créée au clic, elle est de toute façon
     dans le champ, mais l'attribut ne coûte rien et reste juste.
   • le focus passe sur l'iframe une fois posée. Un visiteur au clavier vient
     d'activer un bouton qui disparaît ; sans cela son focus retombe sur le
     document et il perd sa place.
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  var cadres = document.querySelectorAll('.contact-map[data-map-src]');
  if (!cadres.length) return;

  Array.prototype.forEach.call(cadres, function (cadre) {
    var btn = cadre.querySelector('[data-map-load]');
    if (!btn) return;

    btn.addEventListener('click', function () {
      var ask = cadre.querySelector('.contact-map__ask');
      var f = document.createElement('iframe');
      f.className = 'contact-map__iframe';
      f.src = cadre.getAttribute('data-map-src');
      f.title = cadre.getAttribute('data-map-title') || 'Google Maps';
      f.loading = 'lazy';
      f.referrerPolicy = 'no-referrer-when-downgrade';
      f.setAttribute('tabindex', '0');
      cadre.insertBefore(f, cadre.firstChild);
      cadre.classList.remove('is-differee');
      if (ask) ask.remove();
      f.focus();
    });
  });
}());


/* ═══════════════════════════════════════════════════════════════════════
   20. L'AGENDA DE RÉSERVATION S'OUVRE DANS UNE FENÊTRE, AU CLIC

   Deux raisons, dans cet ordre.

   • RIEN N'EST DEMANDÉ À MICROSOFT AVANT QUE LE VISITEUR NE LE DEMANDE. L'iframe
     est créée au clic, comme la carte de contact du module 19 : aucun cookie tiers
     n'est déposé sur une page qui publie une politique de confidentialité.
   • LE CONTENU DE BOOKINGS EST TROP HAUT POUR LE FLUX DE LA PAGE. Mesuré :
     1 523 px à 1 130 px de large, 1 838 px à 342 px. Inséré dans la page il
     imposait un défilement imbriqué, qui capture la molette du visiteur au milieu
     de la page ; dans une fenêtre dédiée, un défilement interne est ATTENDU.

   LA FENÊTRE EST UN <dialog> NATIF, et c'est ce qui rend ce module court : le piège
   de focus, la touche Échap, le fond assombri et le RETOUR DU FOCUS sur le bouton
   d'origine sont donnés par le navigateur. Une fenêtre bricolée en <div> demande
   d'émuler les quatre, et c'est là qu'on se trompe.

   TROIS REPLIS, et le bouton n'est ARMÉ que si aucun ne s'applique. Sans armement,
   le CSS montre le lien externe comme action principale du bloc :
   • pas de JavaScript : rien n'arme, le lien reste ;
   • pas de https : Bookings répond « frame-ancestors https: », donc la fenêtre
     resterait vide sur http ou en file:// ;
   • pas de <dialog> : navigateur trop ancien.

   L'IFRAME EST DÉTRUITE À LA FERMETURE. Dans une fenêtre fermée elle continuerait
   de faire tourner les scripts de Microsoft, et la réouverture ne coûte qu'une
   seconde (mesuré : l'agenda peint 1,0 s après la navigation).
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  /* Deux sortes de déclencheurs : le cadre de la page de réservation, et le bouton
     « Réserver une démo » de la barre de navigation, présent sur toutes les pages.
     Le second reste un LIEN vers la page de réservation : on n'intercepte son clic
     que si la fenêtre peut réellement s'ouvrir. */
  var cadres = document.querySelectorAll('.booking-frame[data-booking-src]');
  var liens = document.querySelectorAll('a[data-booking-open][data-booking-src]');
  if (!cadres.length && !liens.length) return;
  if (location.protocol !== 'https:') return;
  if (typeof document.createElement('dialog').showModal !== 'function') return;

  var n = 0;

  /* `source` est l'élément qui porte les attributs data-booking-* : le cadre sur la
     page de réservation, le lien de la barre partout ailleurs. */
  function ouvre(source) {
    var cadre = source;
    {
      var titre = cadre.getAttribute('data-booking-title') || 'Agenda';
      var idt = 'booking-modal-titre-' + (++n);

      var fen = document.createElement('dialog');
      fen.className = 'booking-modal';
      fen.setAttribute('aria-labelledby', idt);

      var boite = document.createElement('div');
      boite.className = 'booking-modal__box';

      var barre = document.createElement('div');
      barre.className = 'booking-modal__bar';

      /* Pictogramme au trait, en teal : le même langage que les icônes du site.
         Jamais d'emoji, règle du dépôt. */
      var legende = document.createElement('div');
      legende.className = 'booking-modal__legende';
      legende.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" ' +
        'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true">' +
        '<rect x="3" y="4" width="18" height="17" rx="2"/>' +
        '<line x1="3" y1="9" x2="21" y2="9"/>' +
        '<line x1="8" y1="2" x2="8" y2="5"/>' +
        '<line x1="16" y1="2" x2="16" y2="5"/></svg>';

      var h = document.createElement('p');
      h.className = 'booking-modal__titre';
      h.id = idt;
      h.textContent = titre;
      legende.appendChild(h);

      var croix = document.createElement('button');
      croix.type = 'button';
      croix.className = 'booking-modal__close';
      croix.setAttribute('aria-label', cadre.getAttribute('data-booking-fermer') || 'Fermer');
      croix.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" ' +
        'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true">' +
        '<line x1="5" y1="5" x2="19" y2="19"/><line x1="19" y1="5" x2="5" y2="19"/></svg>';
      barre.appendChild(legende);
      barre.appendChild(croix);

      var zone = document.createElement('div');
      zone.className = 'booking-modal__zone';

      var f = document.createElement('iframe');
      f.className = 'booking-modal__iframe';
      f.src = cadre.getAttribute('data-booking-src');
      f.title = titre;
      f.loading = 'eager';
      f.setAttribute('referrerpolicy', 'no-referrer-when-downgrade');

      var att = document.createElement('p');
      att.className = 'booking-modal__chargement';
      att.setAttribute('role', 'status');
      att.appendChild(document.createTextNode(
        cadre.getAttribute('data-booking-attente') || 'Chargement'));
      for (var i = 0; i < 3; i++) att.appendChild(document.createElement('i'));

      /* Filet : si l'agenda ne répond pas, on cesse de faire tourner les points et
         on renvoie au lien du pied, qui n'est jamais retiré. */
      var lent = setTimeout(function () {
        var m = cadre.getAttribute('data-booking-lent');
        if (m) att.textContent = m;
      }, 20000);

      /* MESURÉ : l'agenda peint 0,28 s après son « load ». Aucune attente minimale
         longue ne se justifie, elle ne ferait que retarder un chargement rapide. Ce
         plancher de 400 ms, calé sur le fondu, évite un clignotement sur cache chaud.
         Le test « isConnected » couvre le cas d'une fermeture avant la fin du
         chargement, où la fenêtre n'est plus dans le document. */
      var depart = Date.now();
      f.addEventListener('load', function () {
        clearTimeout(lent);
        var reste = 400 - (Date.now() - depart);
        setTimeout(function () {
          if (fen.isConnected) fen.classList.add('is-pret');
        }, reste > 0 ? reste : 0);
      });

      zone.appendChild(f);
      zone.appendChild(att);
      boite.appendChild(barre);
      boite.appendChild(zone);
      fen.appendChild(boite);
      document.body.appendChild(fen);

      croix.addEventListener('click', function () { fen.close(); });
      /* Clic sur le fond : la cible est le <dialog> lui-même, la boîte étant à
         l'intérieur. C'est la façon standard de distinguer les deux. */
      fen.addEventListener('click', function (e) { if (e.target === fen) fen.close(); });

      /* showModal() n'empêche pas partout la page de défiler derrière : on la
         verrouille explicitement, et on restaure la valeur d'origine. */
      var deb = document.documentElement.style.overflow;
      document.documentElement.style.overflow = 'hidden';

      fen.addEventListener('close', function () {
        clearTimeout(lent);
        document.documentElement.style.overflow = deb;
        if (fen.parentNode) fen.parentNode.removeChild(fen);
      });

      fen.showModal();
      croix.focus();
    }
  }

  Array.prototype.forEach.call(cadres, function (cadre) {
    var btn = cadre.querySelector('[data-booking-load]');
    if (!btn) return;
    /* Cette classe montre le bouton et le pied du cadre : ils n'existent donc que
       là où quelque chose sait y répondre. */
    cadre.classList.add('is-armee');
    btn.addEventListener('click', function () { ouvre(cadre); });
  });

  Array.prototype.forEach.call(liens, function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      ouvre(a);
    });
  });
}());


/* ════════════════════════════════════════
   21. LE CARROUSEL DE PHOTOS D'ÉQUIPE
   Demandé par le client le 2026-09-02 : « mets pas de photo à “Q-Bot, conçu par
   des experts du test logiciel” et fais un carrousel juste en dessous, en vrai ».

   IL FONCTIONNE SANS CE MODULE, ET C'EST LE POINT DE DÉPART. La piste est un
   défilement horizontal natif avec accrochage (`scroll-snap`) : sans JavaScript
   on fait défiler au doigt, à la molette ou à la barre de défilement, et les
   quatre photos sont là. Ce module n'ajoute que le confort : deux flèches, des
   pastilles, et l'état de tout cela.
   C'est la même mécanique que le repli de la bande d'exemples d'appel, déjà dans
   la feuille de style depuis le 2026-08-20.

   IL N'AVANCE PAS TOUT SEUL, ET CE N'EST PAS UN OUBLI. Le client avait fait
   retirer les bandes d'outils défilantes le 2026-08-20 (« les carrousels sont un
   peu illisibles cognitivement ») : ce qui les rendait illisibles, c'était le
   défilement automatique, pas le motif. Ici le visiteur décide. Ajouter un
   défilement automatique demanderait en plus un bouton de pause, sans quoi c'est
   un défaut d'accessibilité (WCAG 2.2.2).

   L'ÉTAT SE LIT SUR LA POSITION RÉELLE, jamais sur un compteur interne : le
   défilement peut venir du doigt, de la molette, de la barre ou d'une flèche, et
   un index maison se désynchronise au premier de ces gestes. On mesure
   `scrollLeft` et on en déduit la vue courante.
════════════════════════════════════════ */
(function () {
  var cars = document.querySelectorAll('[data-carousel]');
  if (!cars.length) return;

  Array.prototype.forEach.call(cars, function (car) {
    var piste = car.querySelector('.carousel__track');
    var vues = car.querySelectorAll('.carousel__slide');
    var prec = car.querySelector('[data-carousel-prev]');
    var suiv = car.querySelector('[data-carousel-next]');
    var pastilles = car.querySelectorAll('[data-carousel-dot]');
    if (!piste || !vues.length) return;

    /* Le pas est la largeur d'une vue plus la gouttière, relue sur place : elle
       change avec la largeur de fenêtre, et une constante serait fausse partout
       ailleurs qu'à la largeur où on l'a écrite. */
    function pas() {
      if (vues.length < 2) return piste.clientWidth;
      return vues[1].offsetLeft - vues[0].offsetLeft;
    }

    /* COMBIEN DE POSITIONS LA PISTE A-T-ELLE VRAIMENT ? Avec cinq photos et trois
       visibles, il n'y a que TROIS départs possibles : la course vaut deux pas.
       Le compte se déduit donc de la course réelle, et il change avec la largeur
       de fenêtre (trois positions au large, cinq sur téléphone).
       C'est ce qui permet aux pastilles de dire la vérité : on en masque celles
       qui ne correspondent à aucune position, au lieu de les laisser inertes.
       Modèle retenu : une pastille = un DÉPART, donc la pastille allumée est
       toujours celle sur laquelle on vient de cliquer. Le modèle « vue centrée »
       a été essayé et écarté : il décalait l'allumage d'un cran par rapport au
       clic, ce qui est pire qu'une pastille en moins. */
    function positions() {
      var p = pas();
      if (!p) return 1;
      return Math.floor((piste.scrollWidth - piste.clientWidth) / p + 0.01) + 1;
    }

    function index() {
      var p = pas();
      return p ? Math.min(positions() - 1, Math.round(piste.scrollLeft / p)) : 0;
    }

    function etat() {
      var i = index();
      var fin = piste.scrollWidth - piste.clientWidth;
      if (prec) prec.disabled = piste.scrollLeft <= 2;
      if (suiv) suiv.disabled = piste.scrollLeft >= fin - 2;
      var n = positions();
      Array.prototype.forEach.call(pastilles, function (d, k) {
        /* `hidden` et non une classe : une pastille sans position n'existe pas
           pour cette largeur de fenêtre, elle ne doit pas non plus être annoncée
           ni recevoir le focus. */
        d.hidden = k >= n;
        if (k === i) d.setAttribute('aria-current', 'true');
        else d.removeAttribute('aria-current');
      });
    }

    /* On amène la vue demandée au bord gauche, en bornant à la course réelle : la
       piste clampe de toute façon, mais borner ici évite que l'état se calcule sur
       une cible impossible. */
    function vers(i) {
      var max = piste.scrollWidth - piste.clientWidth;
      var cible = Math.min(max, Math.max(0, i * pas()));
      piste.scrollTo({ left: cible, behavior: 'smooth' });
    }

    if (prec) prec.addEventListener('click', function () { vers(Math.max(0, index() - 1)); });
    if (suiv) suiv.addEventListener('click', function () {
      vers(Math.min(vues.length - 1, index() + 1));
    });
    Array.prototype.forEach.call(pastilles, function (d, k) {
      d.addEventListener('click', function () { vers(k); });
    });

    var attente;
    piste.addEventListener('scroll', function () {
      clearTimeout(attente);
      attente = setTimeout(etat, 90);
    });
    window.addEventListener('resize', etat);
    etat();
  });
}());
