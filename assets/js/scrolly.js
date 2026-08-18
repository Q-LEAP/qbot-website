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
    /* Un balayage continu vers la gauche, 34° → −128°, élévation fixe à 70° sauf
       au dernier pas. Chaque angle est choisi par ce que le pas doit MONTRER, et
       la monotonie de la rotation n'est que la conséquence d'un bon ordre :
       1. trois-quarts avant droit : le produit se présente ;
       2. de face, serré : la face inclinée et l'emplacement du téléphone ;
       3. trois-quarts avant GAUCHE, et c'est impératif — dans le clip du GLB le
          plateau sort vers −X, donc vers la gauche. Vu depuis la droite il
          coulisse DERRIÈRE la coque et l'ouverture ne se voit pas du tout : le
          pas « Ouvrez-le » montrait un boîtier fermé. Depuis la gauche, le
          plateau et sa mécanique dégagent franchement l'objet ;
       4. trois-quarts arrière gauche, vu de plus haut : l'emprise au sol. Il faut
          un angle EN COIN et non un profil — de profil le boîtier couvre la
          feuille, alors qu'en coin les quatre angles de celle-ci dépassent.
       Un tour complet réparti sur quatre pas avait déjà été écarté (il plaçait un
       pas de dos) ; ce balayage plus court garde la face avant sur trois pas. */
    { theta:   34, phi: 70, r: 0.62, zoom: 1.00, t: 0 },  // trois-quarts avant droit
    { theta:   -8, phi: 70, r: 0.52, zoom: 1.16, t: 0 },  // de face, serré
    { theta:  -42, phi: 66, r: 0.82, zoom: 1.02, t: 0 },  // trois-quarts avant gauche : l'ouverture
    /* Dernier pas, l'encombrement : c'est le SEUL où l'élévation change (70° →
       54°). À 70° le plan du sol est vu en rasant, la feuille A3 s'y réduit à un
       fuseau et l'emprise ne se lit pas ; en montant la caméra, la feuille
       s'ouvre et le boîtier se lit posé dessus. */
    { theta: -128, phi: 54, r: 0.76, zoom: 1.02, t: 0 }   // trois-quarts arrière gauche, en plongée
  ];
  /* Le clip contient aussi l'insertion du smartphone, sur [1s, 2s]. La séquence
     n'y va JAMAIS : le téléphone du GLB est un volume générique, moins soigné que
     le boîtier lui-même. En restant sous t=1.0 il garde son échelle 0, donc il
     est simplement absent — rien à masquer, c'est le clip qui s'en charge. */
  var PHONE_HANDOFF = 1.0;
  var EXPLODE_STEP  = 2;   // 3e pas : « Ouvrez-le »     // le dernier pas : l'éclatement est SCRUBBÉ, pas joué
  /* 0.92 et non 0.98. Le clip porte un keyframe de RÉASSEMBLAGE à t=1.0 (il
     existe pour que les pièces ne restent pas éclatées quand on passe au segment
     du téléphone). En s'approchant de 0.98, l'interpolation vers ce keyframe tire
     déjà les pièces vers leur position fermée : le mouvement s'inverse
     légèrement juste avant la fin — le « bump » signalé. S'arrêter à 0.92 laisse
     une marge suffisante pour rester hors de cette zone d'influence, sans perte
     visible d'amplitude : à 0.92 le boîtier est ouvert à 94 % de sa course. */
  var EXPLODE_END   = 0.92;
  /* Fenêtre de scrub, exprimée en fraction du pas parcourue par le centre du
     viewport. Elle DÉMARRE à 0.5 : c'est l'instant où ce pas devient le pas
     centré, donc celui où l'on bascule du segment téléphone au segment coque.
     Commencer avant reviendrait à ouvrir le boîtier pendant que le texte
     précédent est encore à l'écran ; commencer après ferait un saut visible.
     Elle finit à 0.80. Ce n'est pas la fin du pas : l'image qui compte est celle où
     le texte est centré, donc pleinement lisible, et l'ouverture doit y être
     complète — le pas s'appelle « Ouvrez-le ». Mais elle ne peut pas s'arrêter au
     centre non plus, parce que le pas doit AUSSI redevenir opaque avant que la
     caméra ne pivote vers le pas suivant (cf. SOLID_START plus bas), et cela
     demande de la place après le centre. À 0.80, les quatre temps du pas tiennent
     chacun sur au moins 190 px de défilement. */
  var SCRUB_IN = 0.04, SCRUB_OUT = 0.80;

  /* ── Radiographie de la coque ─────────────────────────────────────────────
     Sur le pas « Ouvrez-le », la coque devient d'abord du verre : on voit la
     mécanique à l'intérieur, puis les pièces s'écartent. Deux temps dans un seul
     geste de défilement, la coque restant transparente pendant l'éclatement —
     le montage se défait donc à vue.

     Ce n'est PAS dans le GLB : une animation glTF ne sait piloter que des
     translations, rotations, échelles et poids de morph — jamais une propriété de
     matériau. L'opacité est donc écrite à l'exécution, via l'API Material de
     model-viewer, exactement comme `currentTime` : le défilement en donne la
     valeur, image par image. Surcoût mesuré : 0,2 ms par image (le rendu du
     modèle lui-même en coûte 14 dans un navigateur sans GPU).

     Deux conditions étaient déjà remplies, sans quoi l'effet ne tiendrait pas :
     - il y a quelque chose à montrer — le plateau porte le rail et l'actionneur ;
     - la coque et le plateau sont en `doubleSided` (fait pour le hublot, cf.
       CLAUDE.md), donc les faces arrière ne sont pas éliminées et l'intérieur se
       lit vraiment au lieu de laisser voir le fond de la page.

     Le matériau est repéré par son index, faute de nom dans le fichier, mais
     l'index seul serait fragile si le GLB était réexporté : sa couleur de base est
     donc vérifiée. En cas d'écart, l'effet se désactive et la séquence continue
     sans lui — jamais de coque à moitié transparente sur un modèle inattendu. */
  var XRAY_ALPHA = 0.26;   // opacité de la coque « en verre »
  /* L'OPACITÉ N'EST PAS UNE PHASE : C'EST UNE FONCTION DE L'ÉCLATEMENT.
     Boîtier fermé → opaque. Boîtier ouvert → verre. Et tout ce qui se trouve entre
     les deux, dans un sens comme dans l'autre. Une seule ligne la calcule, à partir
     de la position réelle dans le clip, ce qui rend impossibles par construction les
     trois défauts qu'ont produits mes tentatives précédentes :
       — plus de coque translucide sur un boîtier fermé, ni l'inverse ;
       — plus de verre qui subsiste pendant la rotation vers le pas suivant, puisque
         l'éclatement y est remis à zéro et que l'opacité suit le même instant ;
       — plus de superposition verre + éclatement à mi-course, puisque les deux ne
         font plus qu'un seul mouvement.
     Ces défauts venaient tous de la même erreur : avoir traité l'opacité comme une
     animation autonome, avec ses propres bornes et sa propre inertie, alors qu'elle
     n'est qu'une lecture de l'état d'ouverture.

     TROIS TEMPS, ET NON DEUX : ouverture, TENUE, refermeture — à la même vitesse
     dans les deux sens. L'ouverture occupait d'abord la première moitié de la
     fenêtre (0 à 0.60) et la refermeture le dernier tiers, deux fois plus vite : on
     passait donc le pas à ouvrir puis à refermer, sans jamais s'arrêter sur l'image
     ouverte, et le même geste n'avait pas la même valeur selon le sens. Or le
     boîtier ouvert est CE QUE LE PAS MONTRE : il lui faut un palier.
       0     → 0.34   il s'ouvre        (~230 px, deux crans de molette)
       0.34  → 0.66   il RESTE ouvert   (~220 px, c'est ici que le texte se lit)
       0.66  → 1.00   il se referme     (~230 px, même vitesse qu'à l'ouverture)
     Les deux rampes ont la même longueur, donc la même vitesse par pixel parcouru :
     le mouvement est réversible à l'identique, ce qui est la lecture la plus
     naturelle quand on remonte le défilement. Le centre du pas — fraction 0.5, soit
     f = 0.605, l'instant où le texte est centré — tombe dans le palier : l'image que
     le visiteur regarde en lisant est bien le boîtier grand ouvert, et non une étape
     de son ouverture.
     La refermeture se termine à 0.80 du pas alors que la bascule vers le pas suivant
     n'a lieu qu'à 1.00 : le boîtier est refermé ET opaque, immobile, 180 px avant que
     la caméra ne bouge. C'est l'acquis de la passe précédente, il est conservé. */
  var BURST_FULL = 0.34;   // fin de l'ouverture, début de la tenue
  var BURST_HOLD = 0.66;   // fin de la tenue, début de la refermeture
  var SHELL_MAT  = 1;                       // 0 plateau, 1 coque, 2 petites pièces…
  var SHELL_BASE = [0.064, 0.068, 0.074];   // charbon de la passe matière
  var shellMat = null, shellRGB = null, shellBlend = false;

  function resolveShell() {
    try {
      var mats = viewer.model && viewer.model.materials;
      if (!mats || mats.length <= SHELL_MAT) return null;
      var m = mats[SHELL_MAT];
      var c = m.pbrMetallicRoughness.baseColorFactor;
      for (var i = 0; i < 3; i++) if (Math.abs(c[i] - SHELL_BASE[i]) > 0.02) return null;
      shellRGB = [c[0], c[1], c[2]];
      return m;
    } catch (e) { return null; }
  }

  /* Le mode alpha ne change qu'au franchissement du seuil : le basculer à chaque
     image recompilerait le shader de la coque soixante fois par seconde. */
  function setShellAlpha(a) {
    if (!shellMat) return;
    var blend = a < 0.99;
    if (blend !== shellBlend) {
      shellMat.setAlphaMode(blend ? 'BLEND' : 'OPAQUE');
      shellBlend = blend;
    }
    shellMat.pbrMetallicRoughness.setBaseColorFactor(
      [shellRGB[0], shellRGB[1], shellRGB[2], blend ? a : 1]);
  }

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
              zoom: SCENES[0].zoom, t: SCENES[0].t, alpha: 1 };
  var loaded = false, running = false, lastP = -1, wasScrub = false, onScreen = false;

  if (viewer) {
    viewer.addEventListener('load', function () {
      loaded = true;
      viewer.pause();          // sinon l'horloge interne écrase nos écritures
      shellMat = resolveShell();
      apply(true);
    });
  }

  function lerp(a, b, k) { return a + (b - a) * k; }
  /* Courbe en S de Hermite : plate aux deux bouts, la plus économique qui soit. */
  function smooth(x) { return x * x * (3 - 2 * x); }


  /* ══ CALQUE D'ANNOTATIONS PROJETÉES ═══════════════════════════════════════
     Le décor de la séquence était en CSS : un trait pour le bureau, un rectangle
     incliné en `perspective()` pour la feuille A3, des étiquettes de cote posées
     à des pourcentages du conteneur. Rien de tout cela ne connaissait la caméra,
     donc rien ne restait solidaire du produit : la feuille passait DEVANT le
     boîtier, les cotes désignaient le vide, et l'ensemble se lisait comme des
     autocollants sur une image.

     Ici les annotations partagent la caméra du rendu. On lit à chaque image
     l'orbite, la cible et l'angle de champ réels du `<model-viewer>`, on en
     reconstruit la matrice de vue, et on projette des points exprimés dans le
     repère du modèle. Une cote tracée ainsi tourne avec l'objet, se raccourcit
     quand il se met de profil, et passe derrière lui quand elle doit.

     Trois choix qui font le rendu :
     - on LIT la caméra au lieu de réutiliser nos valeurs cibles : model-viewer
       lisse ses propres transitions, donc seule la valeur relue correspond à ce
       qui est réellement affiché ;
     - le canevas 3D et ce calque vivent dans le même conteneur transformé, si
       bien que le zoom de scène ne peut pas les désolidariser ;
     - l'enveloppe convexe projetée du boîtier sert de masque : ce qui est posé
       au sol disparaît derrière le produit au lieu de le traverser.

     Les coordonnées ci-dessous sont relevées sur `assets/models/qbot.glb` (unités
     du modèle = mètres), pas estimées à l'œil. Si le modèle est réexporté, les
     relever à nouveau plutôt que les corriger au jugé. */
  var HUD = (function () {
    var svg   = root.querySelector('.scrolly__hud');
    var scene = root.querySelector('.scrolly__scene');
    if (!svg || !scene || !viewer) return { draw: function () { return 0; } };
    var NS = 'http://www.w3.org/2000/svg';

    /* Boîte englobante de la coque — la pièce fixe, jamais animée. Elle sert
       d'occulteur et de référence pour les cotes. */
    var BOX = { x: [-0.0585, 0.0585], y: [0, 0.1457], z: [-0.1064, 0.1064] };

    /* Feuille A3. Le modèle mesure 21,3 × 11,7 cm au sol alors que la fiche
       produit annonce 40 × 24 cm : les deux échelles ne coïncident pas (seule la
       hauteur, 14,6 cm pour 15 annoncés, tombe juste). La feuille est donc
       dimensionnée à partir de la fiche produit — 42/40 en profondeur, 29,7/24
       en largeur — et non à partir des unités du fichier. Le dessin dit alors
       exactement ce que dit le texte du pas : le boîtier occupe une A3 avec une
       marge. Dessiner une A3 à l'échelle du fichier montrerait un boîtier au
       quart de la feuille, ce qui contredirait la fiche. */
    var SHEET = { x: 0.117 * 29.7 / 24 / 2, z: 0.2129 * 42 / 40 / 2 };

    /* Emplacement du smartphone : position « à quai » du clip d'animation
       (dernière image du segment téléphone) et base locale du volume, relevées
       dans le GLB. Le téléphone s'appuie en biais, sa verticale locale penchée
       de 44°. */
    var DOCK = [-0.00242, 0.03883, 0.09051];
    var PH_R = [1, 0, 0], PH_U = [0, 0.7148, -0.6993], PH_N = [0, 0.6993, 0.7148];
    var PH = { r: 0.0355, u0: 0.002, u1: 0.147, n: 0.0082 };

    /* Vue éclatée : logement de chaque pièce mobile (centre de sa boîte
       englobante au repos) et déplacement atteint à la dernière image du segment
       coque. Les keyframes sont linéaires, donc l'écart à l'instant t vaut
       v · t / 0,96667. La coque n'y figure pas : c'est elle l'ancre. */
    var BURST_END = 0.96667;
    var PARTS = [
      { seat: [-0.0002, 0.0370, -0.0017], v: [-0.02948, -0.04801, -0.06233] },  // plateau
      { seat: [-0.0309, 0.0485, -0.0499], v: [-0.03507, -0.02829, -0.05657] },
      { seat: [ 0.0095, 0.0295,  0.0962], v: [ 0.00460, -0.04865,  0.10872] },  // embase
      { seat: [ 0.0138, 0.1123, -0.0118], v: [ 0.00042,  0.03842, -0.00619] }   // vitre
    ];

    /* ── Petite algèbre ─────────────────────────────────────────────────── */
    function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
    function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
    function crs(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
    function nrm(a) { var l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }
    function add(a, b, k) { return [a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k]; }

    /* ── La caméra du rendu, relue à la source ────────────────────────────
       `C` est l'état de caméra de l'image en cours, `midHi` la projection du
       centre du volume. Les deux sont partagés par toutes les primitives de
       dessin — c'est ce qui leur permet de décider seules de quel côté de l'objet
       se poser — et réécrits une fois par image, au début de draw(). */
    var C = null, midHi = [0, 0];
    function readCamera() {
      var o = viewer.getCameraOrbit(), t = viewer.getCameraTarget(), fov = viewer.getFieldOfView();
      /* Dimensions de MISE EN PAGE, pas la boîte affichée : `scene` porte un
         `scale()`, et un getBoundingClientRect() renverrait la taille zoomée
         alors que les unités du SVG, elles, ne le sont pas. */
      var w = scene.offsetWidth, h = scene.offsetHeight;
      if (!w || !h) return null;
      /* Position réelle de la scène à l'écran : elle sert à borner les étiquettes.
         `rect` est la boîte TRANSFORMÉE, `w`/`h` la boîte de mise en page — leur
         rapport donne le facteur de zoom courant, donc la conversion entre les
         unités du SVG et les pixels du viewport. */
      var rect = scene.getBoundingClientRect();
      var tgt = [t.x, t.y, t.z];
      var sp = Math.sin(o.phi), cp = Math.cos(o.phi);
      var eye = [tgt[0] + o.radius * sp * Math.sin(o.theta),
                 tgt[1] + o.radius * cp,
                 tgt[2] + o.radius * sp * Math.cos(o.theta)];
      var f = nrm(sub(tgt, eye));
      var s = nrm(crs(f, [0, 1, 0]));
      return { eye: eye, f: f, s: s, u: crs(s, f), w: w, h: h,
               th: Math.tan(fov * Math.PI / 360), aspect: w / h, theta: o.theta,
               px: rect.width / w, left: rect.left, top: rect.top };
    }
    function depth(p) { return dot(sub(p, C.eye), C.f); }
    function proj(p) {
      var d = sub(p, C.eye), z = dot(d, C.f);
      return [(0.5 + 0.5 * (dot(d, C.s) / z) / (C.th * C.aspect)) * C.w,
              (0.5 - 0.5 * (dot(d, C.u) / z) / C.th) * C.h];
    }
    /* Un segment dont une extrémité passe derrière l'œil doit être coupé, sinon
       sa projection part à l'infini du mauvais côté. La profondeur étant affine
       en position, le point de coupe se calcule directement. */
    var NEAR = 0.01;
    function seg(a, b) {
      var da = depth(a), db = depth(b);
      if (da < NEAR && db < NEAR) return '';
      if (da < NEAR) a = add(a, sub(b, a), (NEAR - da) / (db - da));
      else if (db < NEAR) b = add(b, sub(a, b), (NEAR - db) / (da - db));
      var p = proj(a), q = proj(b);
      return 'M' + p[0].toFixed(1) + ' ' + p[1].toFixed(1) + 'L' + q[0].toFixed(1) + ' ' + q[1].toFixed(1);
    }
    function poly(pts, close) {
      var d = '';
      for (var i = 0; i < pts.length; i++) {
        var p = proj(pts[i]);
        d += (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1);
      }
      return d + (close ? 'Z' : '');
    }
    function put(el, attrs) { for (var k in attrs) el.setAttribute(k, attrs[k]); }

    /* Sous 900 px la scène déborde volontairement de l'écran — l'objet est coupé
       par le bord droit. Une étiquette calculée au bon endroit dans le repère de
       la scène peut donc tomber hors du viewport : « 40 cm » se retrouvait à
       moitié dans le vide. On repousse le texte dans la fenêtre, en pixels réels,
       puis on revient en unités du SVG. Le trait, lui, ne bouge pas : il reste
       solidaire de l'objet, seule l'étiquette rentre. */
    function label(el, x, y, anchor, pad) {
      var sx = C.left + x * C.px, sy = C.top + y * C.px;
      sx = Math.min(Math.max(sx, pad), window.innerWidth - pad);
      sy = Math.min(Math.max(sy, 26), window.innerHeight - 26);
      put(el, { x: ((sx - C.left) / C.px).toFixed(1),
                y: ((sy - C.top) / C.px).toFixed(1), 'text-anchor': anchor });
    }

    /* ── Primitives de scène ────────────────────────────────────────────────
       Elles ne dépendent que de la caméra courante (`C`), donc elles vivent hors
       de la boucle de dessin : à 60 images par seconde, redéfinir sept fonctions
       par image ne coûte rien de visible mais ne sert à rien non plus. */

    /* Nappe de lumière au sol, et fondu du quadrillage : un cercle unité auquel
       on applique la carte affine du plan du sol — les deux demi-axes sont les
       projections de (R,0,0) et (0,0,R). Le dégradé étant en coordonnées d'objet,
       il s'étale dans le plan du sol et non dans celui de l'écran ; c'est ce qui
       fait qu'une nappe vue en rasant reste douce à son bord lointain, très
       raccourci, comme à son bord proche.
       La carte affine ignore le décentrement propre à la perspective ; sur un
       disque de 27 cm vu à 62 cm l'écart est négligeable, et surtout la forme et
       le dégradé subissent la MÊME approximation, donc ils coïncident. */
    function groundDisc(el, R) {
      var o = proj([0, 0, 0]), ax = proj([R, 0, 0]), az = proj([0, 0, R]);
      el.setAttribute('transform', 'matrix(' +
        (ax[0] - o[0]).toFixed(2) + ',' + (ax[1] - o[1]).toFixed(2) + ',' +
        (az[0] - o[0]).toFixed(2) + ',' + (az[1] - o[1]).toFixed(2) + ',' +
        o[0].toFixed(1) + ',' + o[1].toFixed(1) + ')');
    }

    /* Un point du plan du téléphone, repéré par (droite, haut) dans sa propre
       base : c'est ce système local qui permet d'arrondir les coins et de poser
       l'encoche en millimètres du modèle plutôt qu'en pixels. */
    function ph(r, u) {
      return [DOCK[0] + PH_R[0] * r + PH_U[0] * u + PH_N[0] * PH.n,
              DOCK[1] + PH_R[1] * r + PH_U[1] * u + PH_N[1] * PH.n,
              DOCK[2] + PH_R[2] * r + PH_U[2] * u + PH_N[2] * PH.n];
    }
    function xy(p) { var q = proj(p); return q[0].toFixed(1) + ' ' + q[1].toFixed(1); }
    function edgePt(c, o, rad) {
      var dr = o[0] - c[0], du = o[1] - c[1], l = Math.hypot(dr, du) || 1;
      return ph(c[0] + dr / l * rad, c[1] + du / l * rad);
    }
    /* Rectangle à coins arrondis tracé DANS le plan du téléphone : le rayon est
       une longueur du modèle (9 mm), donc il se raccourcit avec la perspective
       comme le reste. Sans les arrondis le fantôme se lisait comme un rectangle
       peint sur la face avant ; avec eux, plus le liseré de dalle en retrait et
       l'encoche, on reconnaît un téléphone. */
    function roundQuad(box, rad) {
      var c4 = [[-box.r, box.u0], [box.r, box.u0], [box.r, box.u1], [-box.r, box.u1]], d = '';
      for (var n = 0; n < 4; n++) {
        var c = c4[n], pv = c4[(n + 3) % 4], nx = c4[(n + 1) % 4];
        d += (n ? 'L' : 'M') + xy(edgePt(c, pv, rad)) +
             'Q' + xy(ph(c[0], c[1])) + ' ' + xy(edgePt(c, nx, rad));
      }
      return d + 'Z';
    }

    /* Une cote se pose du côté le plus proche de l'œil : elle passe alors devant
       l'objet et jamais dedans. On compare les profondeurs plutôt que de figer un
       côté, sinon la cote se cache dès que la caméra tourne. */
    function nearSide(a, b) { return depth(a) < depth(b) ? -1 : 1; }

    function cote(d, a0, b0, off) {
      var a = add(a0, off, 1), b = add(b0, off, 1);
      var tick = nrm(off);
      var path = seg(a, b) + seg(add(a, tick, -0.008), add(a, tick, 0.008)) +
                             seg(add(b, tick, -0.008), add(b, tick, 0.008));
      d.line.setAttribute('d', path);
      d.ext.setAttribute('d', seg(a0, add(a, tick, 0.006)) + seg(b0, add(b, tick, 0.006)));
      var pa = proj(a), pb = proj(b), cx = (pa[0] + pb[0]) / 2, cy = (pa[1] + pb[1]) / 2;
      var vx = cx - midHi[0], vy = cy - midHi[1], vl = Math.hypot(vx, vy) || 1;
      label(d.val, cx + vx / vl * 15, cy + vy / vl * 15, 'middle', 34);
    }

    /* Enveloppe convexe (parcours de Jarvis, 8 points : le coût est nul). */
    function hull(pts) {
      var n = pts.length, start = 0, i;
      for (i = 1; i < n; i++) if (pts[i][0] < pts[start][0]) start = i;
      var out = [], cur = start, guard = 0;
      do {
        out.push(pts[cur]);
        var nx = (cur + 1) % n;
        for (i = 0; i < n; i++) {
          var cross = (pts[nx][0] - pts[cur][0]) * (pts[i][1] - pts[cur][1]) -
                      (pts[nx][1] - pts[cur][1]) * (pts[i][0] - pts[cur][0]);
          if (cross < 0) nx = i;
        }
        cur = nx;
      } while (cur !== start && ++guard < 32);
      return out;
    }

    /* ── Éléments ───────────────────────────────────────────────────────── */
    function mk(tag, parent, cls) {
      var e = document.createElementNS(NS, tag);
      if (cls) e.setAttribute('class', cls);
      parent.appendChild(e);
      return e;
    }
    var occl    = [].slice.call(svg.querySelectorAll('.hud-occl'));
    var pool    = svg.querySelector('.hud-pool');
    var fadeDisc = svg.querySelector('.hud-fade-disc');
    var gridBox = svg.querySelector('.hud-grid');
    var ghost   = svg.querySelector('.hud-ghost');
    var gScreen = svg.querySelector('.hud-ghost-screen');
    var gNotch  = svg.querySelector('.hud-ghost-notch');
    var lead    = svg.querySelector('.hud-lead');
    var node    = svg.querySelector('.hud-node');
    var labDock = svg.querySelector('.hud-lab--dock');
    var burstG  = svg.querySelector('.hud-burst');
    var sheet   = svg.querySelector('.hud-sheet');
    var marks   = svg.querySelector('.hud-sheet-marks');
    var labShee = svg.querySelector('.hud-lab--sheet');
    var dims    = {};
    [].slice.call(svg.querySelectorAll('.hud-dim')).forEach(function (g) {
      dims[g.getAttribute('data-dim')] = {
        line: g.querySelector('.hud-dim-line'),
        ext:  g.querySelector('.hud-dim-ext'),
        val:  g.querySelector('.hud-val')
      };
    });

    /* Quadrillage du plan de travail : 13 lignes par axe, tous les 5,5 cm. Il
       n'a pas de bord — le masque radial l'éteint bien avant sa fin. */
    var GSTEP = 0.055, GN = 6, GL = GSTEP * GN, grid = [];
    for (var gi = -GN; gi <= GN; gi++) {
      for (var ax = 0; ax < 2; ax++) {
        var e = mk('path', gridBox);
        if (gi === 0) e.setAttribute('data-axis', '');
        grid.push({ el: e, k: gi * GSTEP, ax: ax });
      }
    }
    /* Repères d'assemblage : un trait pointillé et une bague par pièce. */
    var burst = PARTS.map(function () {
      return { line: mk('path', burstG), ring: mk('circle', burstG) };
    });

    /* ── Tracé ──────────────────────────────────────────────────────────── */
    function draw(t) {
      C = readCamera();
      if (!C) return 0;
      var i, j, p;

      /* Occulteur : l'enveloppe de la coque, en pixels. */
      var corners = [];
      for (i = 0; i < 2; i++) for (j = 0; j < 2; j++) for (var k = 0; k < 2; k++)
        corners.push(proj([BOX.x[i], BOX.y[j], BOX.z[k]]));
      var hp = hull(corners).map(function (c) { return c[0].toFixed(1) + ',' + c[1].toFixed(1); }).join(' ');
      for (i = 0; i < occl.length; i++) occl[i].setAttribute('points', hp);

      midHi = proj([0, BOX.y[1] / 2, 0]);            // centre du volume, pour orienter les cotes

      groundDisc(pool, 0.27);
      groundDisc(fadeDisc, 0.30);      /* un peu plus large que le quadrillage */

      for (i = 0; i < grid.length; i++) {
        var g = grid[i];
        grid[i].el.setAttribute('d', g.ax
          ? seg([-GL, 0, g.k], [GL, 0, g.k])
          : seg([g.k, 0, -GL], [g.k, 0, GL]));
      }

      /* ── Pas 2 : le contour du smartphone à quai ─────────────────────── */
      ghost.setAttribute('d', roundQuad(PH, 0.009));
      gScreen.setAttribute('d', roundQuad({ r: PH.r - 0.005, u0: PH.u0 + 0.008, u1: PH.u1 - 0.008 }, 0.005));
      /* Une encoche de 2 cm en haut de la dalle. C'est un détail minuscule, et
         c'est lui qui fait basculer la lecture : sans elle, deux rectangles
         concentriques posés sur la face avant passent pour un cadre décoratif. */
      gNotch.setAttribute('d', seg(ph(-0.010, PH.u1 - 0.016), ph(0.010, PH.u1 - 0.016)));
      var face = [ph(-PH.r, PH.u0), ph(PH.r, PH.u0), ph(PH.r, PH.u1), ph(-PH.r, PH.u1)];
      var dockPt = proj(DOCK);
      put(node, { cx: dockPt[0].toFixed(1), cy: dockPt[1].toFixed(1) });
      /* Ligne de rappel : elle part du sommet de la silhouette et s'écarte du
         centre — donc jamais par-dessus le produit, quel que soit l'angle. */
      var top = proj(face[2]), topL = proj(face[3]);
      if (topL[1] < top[1]) top = topL;
      var away = top[0] >= midHi[0] ? 1 : -1;
      var lx = top[0] + away * 34, ly = top[1] - 30;
      lead.setAttribute('d', 'M' + top[0].toFixed(1) + ' ' + top[1].toFixed(1) +
                             'L' + lx.toFixed(1) + ' ' + ly.toFixed(1) +
                             'h' + (away * 22));
      label(labDock, lx + away * 28, ly, away > 0 ? 'start' : 'end', 150);

      /* ── Pas 3 : les repères d'assemblage ────────────────────────────── */
      var kt = Math.max(0, Math.min(1, t / BURST_END));
      for (i = 0; i < PARTS.length; i++) {
        var s0 = PARTS[i].seat, now = add(s0, PARTS[i].v, kt);
        burst[i].line.setAttribute('d', seg(s0, now));
        var c0 = proj(s0);
        put(burst[i].ring, { cx: c0[0].toFixed(1), cy: c0[1].toFixed(1), r: (2.5 + 2 * kt).toFixed(1) });
      }

      /* ── Pas 4 : feuille A3 et cotes ─────────────────────────────────── */
      var sh = [[-SHEET.x, 0, -SHEET.z], [SHEET.x, 0, -SHEET.z], [SHEET.x, 0, SHEET.z], [-SHEET.x, 0, SHEET.z]];
      sheet.setAttribute('d', poly(sh, true));
      /* Équerres de repérage aux quatre coins : le langage d'un plan, et le
         seul endroit du tracé où le teal est franc. */
      var mk4 = '', L = 0.026;
      for (i = 0; i < 4; i++) {
        var sx = i === 0 || i === 3 ? -1 : 1, sz = i < 2 ? -1 : 1;
        var c = [sx * SHEET.x, 0, sz * SHEET.z];
        mk4 += seg(c, [c[0] - sx * L, 0, c[2]]) + seg(c, [c[0], 0, c[2] - sz * L]);
      }
      marks.setAttribute('d', mk4);
      /* L'étiquette de la feuille se pose sur celui de ses quatre coins dont la
         projection s'éloigne le plus du produit : c'est le seul critère qui
         garantisse à la fois qu'elle ne tombe pas SUR le boîtier et qu'elle reste
         dégagée des deux cotes au sol. Un choix figé (« le coin le plus bas »,
         « le plus haut ») marchait pour un angle et échouait pour le suivant. */
      var lab = null, ld = -1;
      for (i = 0; i < 4; i++) {
        p = proj(sh[i]);
        var pd = Math.hypot(p[0] - midHi[0], p[1] - midHi[1]);
        if (pd > ld) { ld = pd; lab = p; }
      }
      /* Le libellé se pose À L'INTÉRIEUR de la feuille, en retrait du coin, comme
         le cartouche d'un plan. Posé à l'extérieur il tombait entre le bord de la
         feuille et les lignes de cote, qui sont déportées plus loin encore (3,4 cm
         de l'objet, donc au-delà de la feuille) : le trait de cote traversait le
         texte. À l'intérieur, la zone est vide — le boîtier n'atteint pas le coin. */
      var lvx = lab[0] - midHi[0], lvy = lab[1] - midHi[1], lvl = Math.hypot(lvx, lvy) || 1;
      label(labShee, lab[0] - lvx / lvl * 22, lab[1] - lvy / lvl * 22, 'middle', 110);

      var OFF = 0.034;
      var sxSide = nearSide([-BOX.x[1], 0, 0], [BOX.x[1], 0, 0]);
      var szSide = nearSide([0, 0, -BOX.z[1]], [0, 0, BOX.z[1]]);

      /* Profondeur (40 cm) le long de Z, largeur (24 cm) le long de X. */
      cote(dims.depth, [sxSide * BOX.x[1], 0, BOX.z[0]], [sxSide * BOX.x[1], 0, BOX.z[1]],
           [sxSide * OFF, 0, 0]);
      cote(dims.width, [BOX.x[0], 0, szSide * BOX.z[1]], [BOX.x[1], 0, szSide * BOX.z[1]],
           [0, 0, szSide * OFF]);
      /* Hauteur (15 cm) sur l'arête de silhouette : celle dont la projection
         s'écarte le plus du centre, donc celle qui borde l'objet à l'écran. */
      var best = null, bd = -1;
      for (i = 0; i < 2; i++) for (j = 0; j < 2; j++) {
        var e0 = [BOX.x[i], 0, BOX.z[j]];
        p = proj(e0);
        var dd = Math.abs(p[0] - midHi[0]);
        if (dd > bd) { bd = dd; best = { x: BOX.x[i], z: BOX.z[j], sx: i ? 1 : -1, sz: j ? 1 : -1 }; }
      }
      /* Déport réduit pour la hauteur (2,2 cm au lieu de 3,4) : une cote
         verticale posée trop loin de l'arête ne se rattache plus à rien. */
      var ov = nrm([best.sx, 0, best.sz]);
      cote(dims.height, [best.x, BOX.y[0], best.z], [best.x, BOX.y[1], best.z],
           [ov[0] * 0.022, 0, ov[2] * 0.022]);

      return C.theta;
    }
    return { draw: draw };
  })();

  /* Progression 0→1 du bloc, et interpolation entre les deux scènes encadrantes.
     `onScreen` dit si la séquence est bien ce que le visiteur regarde : la
     section coupe-t-elle le milieu du viewport ? C'est le test qui manquait au
     CTA flottant (voir plus bas). */
  function progress() {
    var box = root.getBoundingClientRect();
    var mid = window.innerHeight / 2;
    onScreen = box.top < mid && box.bottom > mid;
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
    /* Le pas « Ouvrez-le » n'a plus qu'un seul mouvement : le boîtier s'ouvre. Son
       opacité en est la conséquence, calculée plus bas à partir de la position
       atteinte dans le clip. */
    var scrub = (i === EXPLODE_STEP);
    var f = scrub ? fraction(i) : 0;
    var burstK = !scrub                ? 0
               : f <= BURST_FULL       ? f / BURST_FULL
               : f <= BURST_HOLD       ? 1
               : 1 - (f - BURST_HOLD) / (1 - BURST_HOLD);
    var tTarget = scrub ? burstK * EXPLODE_END : g.t;
    var seg = tTarget < PHONE_HANDOFF;
    /* À l'instant où l'on entre ou sort du pas, on SAUTE : un lissage produisait un
       réassemblage d'une seconde pendant que la caméra pivotait de 86°, ce qui se
       lisait comme un mouvement parasite en fin de séquence. Et comme l'opacité est
       une lecture de cette position, elle saute avec — c'est ce qui garantit qu'on ne
       pivote jamais en verre.
       PENDANT le pas, en revanche, la position est légèrement lissée. Elle était
       collée au défilement brut, ce qui allait tant qu'elle ne pilotait que de la
       géométrie : un cran de molette déplaçait les pièces d'un coup, et un
       déplacement franc se lit très bien. Depuis que l'OPACITÉ en découle, le même
       cran fait sauter le fondu de 0,18 — et là ça se voit. Un lissage à 0,22
       (~250 ms) transforme les crans en glissement pour les deux à la fois, sans
       jamais rompre leur corrélation : c'est le même nombre qui les gouverne. */
    if ((cur.t < PHONE_HANDOFF) !== seg) cur.t = tTarget;   // on ne franchit jamais t=1.0
    else if (scrub !== wasScrub) cur.t = tTarget;           // entrée ou sortie du pas
    else if (scrub) cur.t = lerp(cur.t, tTarget, 0.22);     // pendant le pas
    else cur.t = lerp(cur.t, tTarget, k);
    wasScrub = scrub;
    if (cur.t > 1.98) cur.t = 1.98;   // jamais la durée exacte : le mixer y verrait une boucle
    if (cur.t > 0.98 && cur.t < PHONE_HANDOFF) cur.t = 0.98;

    /* L'opacité, lue sur la position RÉELLE dans le clip — donc après toutes les
       corrections ci-dessus, saut de segment compris. Aucune inertie propre : elle
       ne peut ni prendre du retard sur l'ouverture, ni la devancer. La courbe en S
       reste utile, l'œil étant plus sensible aux premiers pourcents de transparence
       qu'aux derniers. */
    cur.alpha = 1 - (1 - XRAY_ALPHA) * smooth(Math.min(1, cur.t / EXPLODE_END));

    /* La dérive s'ajoute à l'orbite calculée, elle ne la remplace pas : le
       scrub garde donc la main, et `idleK` fait le fondu dans les deux sens pour
       qu'aucune reprise ne se voie. */
    var now = performance.now();
    var idle = IDLE.on && !reduced && (now - lastScrollAt > IDLE.delay);
    idleK = lerp(idleK, idle ? 1 : 0, idle ? 0.02 : 0.12);
    var drift = Math.sin(now / IDLE.periodMs * Math.PI * 2) * IDLE.amp * idleK;

    /* Le calque d'annotations relit la caméra RÉELLE, que model-viewer lisse de
       son côté : après un saut (init, redimensionnement) elle met quelques
       images à rejoindre la consigne. Sans ce décalage dans la condition
       d'arrêt, la boucle s'arrêterait avant, et les cotes resteraient figées sur
       le cadrage précédent. */
    var camLag = false;
    if (viewer && loaded) {
      var goal = cur.theta + drift;
      viewer.cameraOrbit = goal.toFixed(2) + 'deg ' + cur.phi.toFixed(2) + 'deg ' + cur.r.toFixed(4) + 'm';
      viewer.currentTime = cur.t;
      setShellAlpha(cur.alpha);
      var shown = HUD.draw(cur.t);
      camLag = Math.abs(shown * 180 / Math.PI - goal) > 0.02;
    }
    stage.style.setProperty('--sc-zoom', cur.zoom.toFixed(4));
    stage.style.setProperty('--sc-glow', (p * 60 - 30).toFixed(1) + 'px');
    if (bar) bar.style.setProperty('--sc-p', p.toFixed(4));

    if (i !== lastP) {
      lastP = i;
      for (var j = 0; j < steps.length; j++) steps[j].classList.toggle('is-active', j === i);
      /* Le pas courant est exposé sur la section : les accessoires de scène sont
         alors purement déclaratifs en CSS, sans connaître l'ordre du HTML. */
      root.setAttribute('data-step', String(i));
      if (count) count.innerHTML = '<b>' + String(i + 1).padStart(2, '0') + '</b> / ' + String(steps.length).padStart(2, '0');
      /* `aria-current="step"` plutôt qu'une classe : l'état est alors annoncé,
         pas seulement colorié. */
      for (var q = 0; q < dots.length; q++) {
        if (q === i) dots[q].setAttribute('aria-current', 'step');
        else dots[q].removeAttribute('aria-current');
        /* `data-done` marque les cases déjà saisies : le code se remplit derrière
           le pas courant, il ne se vide pas quand on revient en arrière au-delà. */
        if (q < i) dots[q].setAttribute('data-done', '');
        else dots[q].removeAttribute('data-done');
      }
    }
    if (hint) hint.style.opacity = p > 0.02 ? '0' : '';
    /* Le CTA n'accompagne QUE la séquence. `progress()` étant borné à 1, la
       condition « p > 0.04 » restait vraie une fois la section franchie : le
       bouton restait donc épinglé sur tout le reste de la page, où il recouvrait
       le lien « Proposer une évolution » de la dernière carte d'évolution et, en
       bas de page, les deux liens légaux du pied de page — tout en faisant doublon
       avec le « Prendre rendez-vous » de la section finale. Il faut les deux
       tests : la progression pour ne pas l'afficher au tout premier pixel, et la
       présence à l'écran pour le retirer à la sortie. */
    if (cta) cta.classList.toggle('is-visible', onScreen && p > 0.04);
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
        cta.classList.toggle('is-unlocked', i === steps.length - 1);
      }
    }

    var moving = Math.abs(g.theta - cur.theta) > 0.01 || Math.abs(tTarget - cur.t) > 0.001 ||
                 Math.abs(g.zoom - cur.zoom) > 0.001 || Math.abs(g.r - cur.r) > 0.0005 ||
                 /* la dérive entretient la boucle : sans ça elle s'arrêterait au repos,
                    c'est-à-dire précisément quand elle doit jouer. */
                 idle || idleK > 0.002 || camLag;
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
