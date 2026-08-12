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
  var viewer   = root.querySelector('model-viewer');
  var steps    = [].slice.call(root.querySelectorAll('.scrolly__step'));
  var bar      = root.querySelector('.scrolly__progress');
  var count    = root.querySelector('.scrolly__count');
  var hint     = root.querySelector('.scrolly__hint');
  var cta      = document.querySelector('.scrolly__cta');
  if (!steps.length) return;

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Un état par pas. `orbit` est en degrés/mètres absolus : model-viewer
     recadre sur les bornes du modèle, donc un rayon en pourcentage donnerait un
     cadrage différent d'une scène à l'autre. `t` est la position dans le clip
     (0 = assemblé, 0.98 = éclaté, 1→2 = insertion du téléphone). */
  var SCENES = [
    { theta: -28, phi: 74, r: 0.62, zoom: 1.00, t: 0.000 },  // le boîtier, posé
    { theta: -12, phi: 72, r: 0.56, zoom: 1.06, t: 1.980 },  // le téléphone se pose
    { theta:   2, phi: 62, r: 0.42, zoom: 1.22, t: 1.980 },  // gros plan sur la face avant
    { theta: -34, phi: 78, r: 0.74, zoom: 0.94, t: 1.980 },  // recul : l'encombrement
    { theta: -26, phi: 66, r: 0.80, zoom: 0.92, t: 0.980 }   // vue éclatée
  ];
  var PHONE_HANDOFF = 1.0;   // keyframe où la coque se réassemble

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

  function apply(snap) {
    var p = progress();
    var i = nearest();
    var g = SCENES[Math.min(i, SCENES.length - 1)];
    var k = snap ? 1 : 0.16;          // inertie : la scène chasse la cible
    cur.theta = lerp(cur.theta, g.theta, k);
    cur.phi   = lerp(cur.phi,   g.phi,   k);
    cur.r     = lerp(cur.r,     g.r,     k);
    cur.zoom  = lerp(cur.zoom,  g.zoom,  k);
    /* Le clip a deux segments séparés par le keyframe t=1.0, qui réassemble la
       coque. Le lissage ne doit jamais le franchir : on saute. */
    var seg = g.t < PHONE_HANDOFF;
    if ((cur.t < PHONE_HANDOFF) !== seg) cur.t = g.t;
    else cur.t = lerp(cur.t, g.t, k);
    if (cur.t > 1.98) cur.t = 1.98;   // jamais la durée exacte : le mixer y verrait une boucle
    if (cur.t > 0.98 && cur.t < PHONE_HANDOFF) cur.t = 0.98;

    if (viewer && loaded) {
      viewer.cameraOrbit = cur.theta.toFixed(2) + 'deg ' + cur.phi.toFixed(2) + 'deg ' + cur.r.toFixed(4) + 'm';
      viewer.currentTime = cur.t;
    }
    stage.style.setProperty('--sc-zoom', cur.zoom.toFixed(4));
    stage.style.setProperty('--sc-glow', (p * 60 - 30).toFixed(1) + 'px');
    if (bar) bar.style.setProperty('--sc-p', p.toFixed(4));

    if (i !== lastP) {
      lastP = i;
      for (var j = 0; j < steps.length; j++) steps[j].classList.toggle('is-active', j === i);
      if (count) count.innerHTML = '<b>' + String(i + 1).padStart(2, '0') + '</b> / ' + String(steps.length).padStart(2, '0');
    }
    if (hint) hint.style.opacity = p > 0.02 ? '0' : '';
    if (cta) cta.classList.toggle('is-visible', p > 0.04);

    var moving = Math.abs(g.theta - cur.theta) > 0.01 || Math.abs(g.t - cur.t) > 0.001 ||
                 Math.abs(g.zoom - cur.zoom) > 0.001 || Math.abs(g.r - cur.r) > 0.0005;
    if (moving) { running = true; requestAnimationFrame(function () { apply(false); }); }
    else running = false;
  }

  function kick() { if (!running) { running = true; requestAnimationFrame(function () { apply(false); }); } }

  if (reduced) {
    /* Mise en scène neutralisée : on pose une seule fois un cadrage lisible et
       on marque tous les pas actifs. Le contenu reste entier. */
    steps.forEach(function (s) { s.classList.add('is-active'); });
    if (cta) cta.classList.add('is-visible');
    if (viewer) viewer.addEventListener('load', function () {
      viewer.pause();
      viewer.cameraOrbit = '-28deg 74deg 0.62m';
      viewer.currentTime = 1.98;
    });
    return;
  }

  window.addEventListener('scroll', kick, { passive: true });
  window.addEventListener('resize', function () { apply(true); });
  window.addEventListener('load', function () { apply(true); });
  apply(true);
})();
