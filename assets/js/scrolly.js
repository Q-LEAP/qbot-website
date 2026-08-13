/* ══════════════════════════════════════════════════════════════════════════
   SCROLLYTELLING — variante Q-BOTAlt
   Le scroll ne déclenche rien : il POSITIONNE. À chaque image, on lit la
   progression du bloc `.scrolly` dans le viewport et on en déduit l'état de la
   scène — orbite de caméra, zoom, position dans le clip « Explode », socle du
   téléphone. Défiler vite accélère l'animation, s'arrêter la fige : c'est le
   geste qui dicte le rythme, jamais un minuteur.

   Contraintes reprises du viewer de modele-3d.html (cf. CLAUDE.md) :
   - `animation-name="Explode"` DOIT être sur la balise, sinon `currentTime`
     ne pilote rien ;
   - `viewer.pause()` est obligatoire après chargement, sinon l'horloge interne
     avance seule et écrase toute valeur écrite de l'extérieur ;
   - ne jamais écrire `currentTime` égal à la durée totale : le mixer y voit une
     fin de boucle et repart à 0.
   ══════════════════════════════════════════════════════════════════════════ */
(function () {
  var root = document.querySelector('.scrolly');
  if (!root) return;

  var stage    = root.querySelector('.scrolly__stage');
  var viewer   = root.querySelector('model-viewer');   // mis à null si repli
  var steps    = [].slice.call(root.querySelectorAll('.scrolly__step'));
  var bar      = root.querySelector('.scrolly__nav-rail');
  var dots     = [].slice.call(root.querySelectorAll('.scrolly__dot'));
  var count    = root.querySelector('.scrolly__count');
  var hint     = root.querySelector('.scrolly__hint');
  var cta      = document.querySelector('.scrolly__cta');
  if (!steps.length) return;

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Repli pour appareil faible ou sans WebGL ────────────────────────────
     Pratique recommandée pour le scroll 3D : décider AVANT de charger la scène,
     et servir un visuel fixe qui conserve le langage et le chemin de conversion.
     Trois signaux : pas de contexte WebGL, mode économiseur de données, ou moins
     de trois cœurs logiques. On retire alors le modèle du DOM — le laisser
     seulement masqué déclencherait quand même son téléchargement. */
  function tooWeak() {
    try {
      var c = document.createElement('canvas');
      if (!(c.getContext('webgl2') || c.getContext('webgl'))) return 'sans WebGL';
    } catch (e) { return 'sans WebGL'; }
    var cn = navigator.connection || {};
    if (cn.saveData) return 'economiseur de donnees';
    if (navigator.hardwareConcurrency && navigator.hardwareConcurrency < 3) return 'peu de coeurs';
    return null;
  }

  var weak = tooWeak();
  var fallback = root.querySelector('.scrolly__fallback');
  if (weak) {
    if (viewer) viewer.parentNode.removeChild(viewer);
    viewer = null;
    if (fallback) fallback.hidden = false;
    root.setAttribute('data-fallback', weak);
  }

  /* Un état par pas. `orbit` est en degrés/mètres absolus : model-viewer
     recadre sur les bornes du modèle, donc un rayon en pourcentage donnerait un
     cadrage différent d'une scène à l'autre. `t` est la position dans le clip
     (0 = assemblé, 0.98 = éclaté, 1→2 = insertion du téléphone). */
  var SCENES = [
    /* Rotation sur UN SEUL AXE. L'azimut ne fait que croître — -28°, +26°, +152°,
       +332°, soit un tour complet réparti sur les quatre pas — et l'élévation
       reste fixe à 70°. Une version précédente montait la caméra sur le pas
       « encombrement » pour faire lire l'emprise au sol : le double mouvement se
       remarquait plus que l'argument. À élévation constante, le tour se lit comme
       un plateau tournant, et seul le cadrage (rayon, zoom) change avec le
       propos. */
    { theta:  -28, phi: 70, r: 0.62, zoom: 1.00, t: 0 },  // trois-quarts avant gauche
    { theta:   26, phi: 70, r: 0.52, zoom: 1.16, t: 0 },  // trois-quarts avant droit, serré
    { theta:  152, phi: 70, r: 0.66, zoom: 1.04, t: 0 },  // arrière : découvre le panneau de
                                                          // connecteurs. Rayon resserré de 0,78 à
                                                          // 0,66 — à 0,78 le boîtier était trop
                                                          // petit pour porter l'argument.
    { theta:  332, phi: 70, r: 0.82, zoom: 0.92, t: 0 }   // le tour est fermé, on revient de
                                                          // face : le boîtier s'ouvre vers le
                                                          // visiteur (t est scrubbé)
  ];
  /* Le clip contient aussi l'insertion du smartphone, sur [1s, 2s]. La séquence
     n'y va JAMAIS : le téléphone du GLB est un volume générique, moins soigné que
     le boîtier lui-même. En restant sous t=1.0 il garde son échelle 0, donc il
     est simplement absent — rien à masquer, c'est le clip qui s'en charge. */
  var PHONE_HANDOFF = 1.0;
  var EXPLODE_STEP  = 3;     // le dernier pas : l'éclatement est SCRUBBÉ, pas joué
  var EXPLODE_END   = 0.98;  // fin utile du segment coque (jamais le keyframe 1.0)
  /* Fenêtre de scrub, exprimée en fraction du pas parcourue par le centre du
     viewport. Elle DÉMARRE à 0.5 : c'est l'instant où ce pas devient le pas
     centré, donc celui où l'on bascule du segment téléphone au segment coque.
     Commencer avant reviendrait à ouvrir le boîtier pendant que le texte
     précédent est encore à l'écran ; commencer après ferait un saut visible.
     Elle finit à 1.15, soit au-delà du pas : le centre du viewport parcourt
     0.5 -> 1.5 sur la hauteur d'un écran, donc cette borne étale l'ouverture sur
     les deux premiers tiers du défilement, puis la maintient ouverte le dernier
     tiers. Une fenêtre plus courte donnait une ouverture expédiée en 400 px. */
  var SCRUB_IN = 0.50, SCRUB_OUT = 1.15;

  /* ── Dérive au repos ──────────────────────────────────────────────────────
     Quand le visiteur cesse de défiler, l'objet dérive très lentement : il se
     lit alors comme une scène vivante et non comme une image. Trois garde-fous,
     parce que le mouvement gratuit a déjà été écarté deux fois sur ce site (le
     cadre du film, puis le trait de progression) : l'amplitude reste sous 4°,
     elle porte sur LE SUJET et non sur son cadre ni sur un indicateur, et elle
     s'efface dès le moindre défilement. Pour la désactiver : passer `on` à
     false — c'est la seule ligne à toucher. */
  var IDLE = { on: true, delay: 1800, amp: 3.2, periodMs: 9000 };
  var lastScrollAt = 0, idleK = 0;

  var cur = { theta: SCENES[0].theta, phi: SCENES[0].phi, r: SCENES[0].r,
              zoom: SCENES[0].zoom, t: SCENES[0].t };
  var loaded = false, running = false, lastP = -1;

  if (viewer) {
    viewer.addEventListener('load', function () {
      loaded = true;
      viewer.pause();          // sinon l'horloge interne écrase nos écritures
      apply(true);
    });
  }

  function lerp(a, b, k) { return a + (b - a) * k; }

  /* Progression 0→1 du bloc, et interpolation entre les deux scènes encadrantes. */
  function progress() {
    var box = root.getBoundingClientRect();
    var travel = box.height - window.innerHeight;
    if (travel <= 0) return 0;
    return Math.min(1, Math.max(0, -box.top / travel));
  }

  /* Quel pas est réellement centré à l'écran ? On le mesure au lieu de le
     déduire d'une hauteur théorique : la course d'un bloc collant dépend du
     viewport, et toute formule fondée sur « n écrans » se décale d'un cran dès
     que la hauteur change. Mesurer supprime cette classe d'erreur. */
  function nearest() {
    var vc = window.innerHeight / 2, best = 0, bd = Infinity;
    for (var i = 0; i < steps.length; i++) {
      var r = steps[i].getBoundingClientRect();
      var d = Math.abs(r.top + r.height / 2 - vc);
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  }

  /* Quelle fraction du pas `i` le centre du viewport a-t-il parcourue ? C'est
     cette valeur qui sert de tête de lecture pour l'éclatement : elle suit le
     doigt à l'image près, dans les deux sens. */
  function fraction(i) {
    var r = steps[i].getBoundingClientRect();
    if (!r.height) return 0;
    var f = (window.innerHeight / 2 - r.top) / r.height;
    f = (f - SCRUB_IN) / (SCRUB_OUT - SCRUB_IN);
    return Math.min(1, Math.max(0, f));
  }

  function apply(snap) {
    var p = progress();
    var i = nearest();
    var g = SCENES[Math.min(i, SCENES.length - 1)];
    var k = snap ? 1 : 0.16;          // inertie : la scène chasse la cible
    cur.theta = lerp(cur.theta, g.theta, k);
    cur.phi   = lerp(cur.phi,   g.phi,   k);
    cur.r     = lerp(cur.r,     g.r,     k);
    cur.zoom  = lerp(cur.zoom,  g.zoom,  k);
    /* Position dans le clip. Sur le pas « L'intérieur », elle est lue
       directement dans le scroll : le boîtier s'ouvre et se referme au rythme du
       geste, sans inertie — une tête de lecture qui traîne se perçoit comme du
       retard, pas comme de la fluidité (même règle que les progressions
       scrubbées de main.js). Ailleurs, la transition garde son inertie. */
    var scrub = (i === EXPLODE_STEP);
    var tTarget = scrub ? fraction(i) * EXPLODE_END : g.t;
    var seg = tTarget < PHONE_HANDOFF;
    if ((cur.t < PHONE_HANDOFF) !== seg) cur.t = tTarget;   // on ne franchit jamais t=1.0
    else if (scrub) cur.t = tTarget;                         // scrub : collé au scroll
    else cur.t = lerp(cur.t, tTarget, k);
    if (cur.t > 1.98) cur.t = 1.98;   // jamais la durée exacte : le mixer y verrait une boucle
    if (cur.t > 0.98 && cur.t < PHONE_HANDOFF) cur.t = 0.98;

    /* La dérive s'ajoute à l'orbite calculée, elle ne la remplace pas : le
       scrub garde donc la main, et `idleK` fait le fondu dans les deux sens pour
       qu'aucune reprise ne se voie. */
    var now = performance.now();
    var idle = IDLE.on && !reduced && (now - lastScrollAt > IDLE.delay);
    idleK = lerp(idleK, idle ? 1 : 0, idle ? 0.02 : 0.12);
    var drift = Math.sin(now / IDLE.periodMs * Math.PI * 2) * IDLE.amp * idleK;

    if (viewer && loaded) {
      viewer.cameraOrbit = (cur.theta + drift).toFixed(2) + 'deg ' + cur.phi.toFixed(2) + 'deg ' + cur.r.toFixed(4) + 'm';
      viewer.currentTime = cur.t;
    }
    stage.style.setProperty('--sc-zoom', cur.zoom.toFixed(4));
    stage.style.setProperty('--sc-glow', (p * 60 - 30).toFixed(1) + 'px');
    if (bar) bar.style.setProperty('--sc-p', p.toFixed(4));

    if (i !== lastP) {
      lastP = i;
      for (var j = 0; j < steps.length; j++) steps[j].classList.toggle('is-active', j === i);
      if (count) count.innerHTML = '<b>' + String(i + 1).padStart(2, '0') + '</b> / ' + String(steps.length).padStart(2, '0');
      /* `aria-current="step"` plutôt qu'une classe : l'état est alors annoncé,
         pas seulement colorié. */
      for (var q = 0; q < dots.length; q++) {
        if (q === i) dots[q].setAttribute('aria-current', 'step');
        else dots[q].removeAttribute('aria-current');
      }
    }
    if (hint) hint.style.opacity = p > 0.02 ? '0' : '';
    if (cta) cta.classList.toggle('is-visible', p > 0.04);
    /* CTA contextuel. Le même bouton affichait « Demander une démo » du premier au
       dernier pas, en doublon de celui de la barre de navigation — les deux
       étaient visibles en même temps. Il accompagne maintenant le propos : il mène
       aux caractéristiques pendant qu'on décrit le produit, et ne demande la démo
       qu'au dernier pas, quand le boîtier s'ouvre, au moment où l'intérêt est le
       plus haut. */
    if (cta) {
      var spec = cta.getAttribute(i === steps.length - 1 ? 'data-cta-last' : 'data-cta-default');
      if (spec) {
        var parts = spec.split('|');
        var label = cta.querySelector('.scrolly__cta-label');
        if (label && label.textContent !== parts[0]) label.textContent = parts[0];
        if (cta.getAttribute('href') !== parts[1]) cta.setAttribute('href', parts[1]);
      }
    }

    var moving = Math.abs(g.theta - cur.theta) > 0.01 || Math.abs(tTarget - cur.t) > 0.001 ||
                 Math.abs(g.zoom - cur.zoom) > 0.001 || Math.abs(g.r - cur.r) > 0.0005 ||
                 /* la dérive entretient la boucle : sans ça elle s'arrêterait au repos,
                    c'est-à-dire précisément quand elle doit jouer. */
                 idle || idleK > 0.002;
    if (moving) { running = true; requestAnimationFrame(function () { apply(false); }); }
    else running = false;
  }

  function kick() { lastScrollAt = performance.now(); if (!running) { running = true; requestAnimationFrame(function () { apply(false); }); } }

  if (reduced) {
    /* Mise en scène neutralisée : on pose une seule fois un cadrage lisible et
       on marque tous les pas actifs. Le contenu reste entier. */
    steps.forEach(function (s) { s.classList.add('is-active'); });
    if (dots.length) dots[0].setAttribute('aria-current', 'step');
    if (cta) cta.classList.add('is-visible');
    if (viewer) viewer.addEventListener('load', function () {
      viewer.pause();
      viewer.cameraOrbit = '-28deg 74deg 0.62m';
      viewer.currentTime = 0;
    });
    return;
  }

  window.addEventListener('scroll', kick, { passive: true });
  window.addEventListener('resize', function () { apply(true); });
  window.addEventListener('load', function () { apply(true); });
  apply(true);
})();
