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
  /* Langue de la page : le compteur annoncé est la seule chaîne que ce script
     écrive à l'écran, mais elle doit se dire dans la langue du document. */
  var FR = (document.documentElement.lang || 'fr').toLowerCase().indexOf('en') !== 0;

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
    /* Connexion lente : le modèle est petit (571 Ko compressé en Draco) mais
       model-viewer et son décodeur pèsent encore quelques centaines de kilo-octets,
       et sur une liaison 2G/3G la séquence resterait figée sur son affiche le temps
       que tout arrive — le visiteur traverserait quatre écrans sans qu'il ne se
       passe rien. Le repli statique raconte la même chose en 110 Ko. Ce signal
       manquait : seul `saveData` était testé, or il est rarement activé. */
    if (cn.effectiveType && /(^|-)2g$/.test(cn.effectiveType)) return 'connexion lente';
    if (cn.effectiveType === '3g' && cn.downlink && cn.downlink < 1.2) return 'connexion lente';
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
       54°). À 70° le plan du sol est vu en rasant, la feuille s'y réduit à un
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

  /* ── Cadrages SCRUBBÉS, et non plus enclenchés ────────────────────────────
     La caméra sautait de cadrage au franchissement du milieu du pas : la cible
     changeait d'un coup et une inertie de 0.16 l'y amenait en ~300 ms, quel que
     soit le geste. Deux défauts, les mêmes que ceux corrigés sur l'éclatement :
     le mouvement ne répondait pas au défilement (on pouvait s'arrêter net, il
     continuait), et il ne se remontait pas — en revenant en arrière la caméra
     refaisait le trajet à sa propre vitesse au lieu de se laisser rembobiner.

     Chaque pas déclare donc un PALIER — la portion du pas où son cadrage est
     immobile — et la caméra interpole d'un palier au suivant, la tête de lecture
     étant le défilement lui-même. Même grammaire que l'éclatement : on tient
     l'image là où le texte se lit, on ne bouge qu'entre deux.

     Les bornes ne sont pas décoratives, chacune répond à une contrainte :
     - pas 1 : palier ouvert dès l'entrée dans la section, sinon le cadrage
       arriverait pendant que le premier texte est déjà lisible ;
     - pas 3 : le palier ENCADRE la fenêtre d'éclatement (SCRUB_IN…SCRUB_OUT)
       avec 0.08 de marge de part et d'autre — soit ~70 px. C'est la contrainte
       dure de la séquence : la caméra ne doit pas tourner pendant que la coque
       est en verre. La marge paie le lissage : la position dans le clip chasse sa
       cible en ~250 ms, elle finit donc de se refermer un peu après 0.80, et le
       palier doit couvrir ce retard. La borne d'entrée est négative : le cadrage
       est en place 36 px AVANT que le pas ne devienne courant, jamais après ;
     - pas 4 : le palier s'ouvre à 0.40, juste avant que son texte ne se centre —
       le mouvement 3 → 4 est le plus ample de la séquence (86° et une élévation),
       il a besoin de place et la prend là où il n'y a rien d'autre à lire.
     Les trois transitions occupent ainsi 324 / 252 / 468 px, soit 0.13 / 0.135 /
     0.165 degré par pixel : à peu près la même vitesse angulaire partout, la
     dernière étant un peu plus rapide parce que son trajet est deux fois plus long
     et qu'il n'y a pas la place de l'étirer davantage. */
  var HOLD = [
    [0.00, 0.82],
    [0.18, 0.68],
    [SCRUB_IN - 0.08, SCRUB_OUT + 0.08],
    [0.40, 1.00]
  ];

  /* Tête de lecture continue, en unités de pas : `i` + la fraction parcourue du
     pas `i`. Monotone et sans discontinuité au changement de pas, puisque la
     fraction vaut 1 à l'instant même où le pas suivant prend la main à 0. */
  function head(i) {
    var r = steps[i].getBoundingClientRect();
    if (!r.height) return i;
    return i + (window.innerHeight / 2 - r.top) / r.height;
  }

  /* Où en est la caméra sur le chemin des cadrages ? Renvoie les deux scènes à
     mêler et le mélange, adouci en S : une rampe linéaire fait démarrer et
     s'arrêter la rotation d'un coup, ce qui se voit sur un mouvement aussi ample
     que 3 → 4. */
  function camAt(u) {
    var n = SCENES.length;
    for (var i = 0; i < n - 1; i++) {
      var a = i + HOLD[i][1];
      var b = (i + 1) + HOLD[i + 1][0];
      if (u <= a) return { a: i, b: i, e: 0 };
      if (u < b)  return { a: i, b: i + 1, e: smooth((u - a) / (b - a)) };
    }
    return { a: n - 1, b: n - 1, e: 0 };
  }

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
  /* Fin de l'isolement de la carte : 0,605 est la fraction où le texte du pas est
     CENTRÉ dans l'écran, valeur déjà relevée pour cette séquence (cf. le pavé
     ci-dessus). L'isolement se termine donc pile à l'instant où le visiteur lit
     « Ce qu'il y a à l'intérieur », ce qui est la demande du client : ni pendant
     l'ouverture, ni à la fin du pas. Il commence à BURST_FULL, c'est-à-dire quand
     le boîtier est grand ouvert : les deux temps ne se chevauchent pas. */
  var ISO_END = 0.605;
  var SHELL_MAT  = 1;                       // 0 plateau, 1 coque, 2 petites pièces…
  var SHELL_BASE = [0.064, 0.068, 0.074];   // charbon de la passe matière

  /* ── ISOLEMENT DE LA CARTE ────────────────────────────────────────────────
     Le pas s'appelle « Ce qu'il y a à l'intérieur » et son texte nomme le nano-
     ordinateur : à l'instant où on le lit, c'est LUI qui doit être la seule chose
     solide de l'image. Le boîtier ne disparaît pas pour autant, il reste
     légèrement visible, sinon la carte flotte dans le vide et on perd l'échelle.

     LE TRI SE FAIT PAR LE NOM DU MATÉRIAU, ET C'EST LA SEULE FAÇON SÛRE. Les cinq
     matériaux du boîtier n'ont pas de nom dans le fichier (ils sont désignés par
     leur index), tandis que les douze de la carte sont nommés `pi-*` par
     `addpi.py`. Un test par index se casserait au premier matériau ajouté au
     boîtier ; un test sur le préfixe survit, et il vaut aussi pour une pièce qui
     serait ajoutée plus tard à la carte. */
  var fadeMats = null;    // tout ce qui n'est PAS la carte, avec sa couleur de base

  function resolveMats() {
    try {
      var mats = viewer.model && viewer.model.materials;
      if (!mats || mats.length <= SHELL_MAT) return false;
      /* La coque reste identifiée par sa couleur de base : en cas d'écart, le
         modèle n'est pas celui qu'on croit et l'effet se désactive en bloc plutôt
         que de rendre translucide une pièce au hasard. */
      var c = mats[SHELL_MAT].pbrMetallicRoughness.baseColorFactor;
      for (var i = 0; i < 3; i++) if (Math.abs(c[i] - SHELL_BASE[i]) > 0.02) return false;
      fadeMats = [];
      for (var k = 0; k < mats.length; k++) {
        if (/^pi-/.test(mats[k].name || '')) continue;
        var b = mats[k].pbrMetallicRoughness.baseColorFactor;
        fadeMats.push({ m: mats[k], rgb: [b[0], b[1], b[2]], shell: k === SHELL_MAT,
                        blend: false, a: 1 });
      }
      return fadeMats.length > 0;
    } catch (e) { fadeMats = null; return false; }
  }

  /* Le mode alpha ne change qu'au franchissement du seuil : le basculer à chaque
     image recompilerait le shader de la coque soixante fois par seconde.
     ET LA COQUE CESSE D'ÊTRE DOUBLE-FACE TANT QU'ELLE EST EN VERRE. Le GLB livré
     la déclare `doubleSided` pour une raison précise, notée dans CLAUDE.md : sans
     ça, le hublot de verre laisse voir le fond de la page au lieu d'une cavité
     sombre. Mais une surface double-face en mode BLEND additionne ses faces
     ARRIÈRE à ses faces avant sans les trier par profondeur : à mi-transparence on
     ne voit plus un boîtier translucide mais un empilement de plans dans un ordre
     arbitraire — des bandes claires et des coutures qui apparaissent et
     disparaissent au moindre degré de rotation. C'est le pire là où on l'attend le
     moins : vers α = 0,7, quand la coque est presque opaque, donc juste avant le
     retour à l'opaque entre les pas 3 et 4.
     Pendant le verre, la raison d'être du double-face tombe d'elle-même : la coque
     étant transparente, il n'y a plus de cavité à noircir. Simple face le temps de
     la transparence, double face dès le retour à l'opacité — un seul appel au
     franchissement du seuil, comme pour le mode alpha. */
  /* ON N'ÉCRIT QUE CE QUI CHANGE, ET C'EST UNE QUESTION D'IMAGES PAR SECONDE.
     Toute écriture sur un matériau ou sur la visionneuse SALIT la scène, donc
     force model-viewer à la redessiner. Mesuré : **448 900 triangles par image**,
     soit deux fois le modèle (la seconde passe est l'ombre portée), et cela dans
     TOUS les états, y compris à l'arrêt sur un pas où rien ne bouge. Le coût par
     écriture est pourtant minuscule côté JavaScript (1,17 µs pour les six
     matériaux) : ce n'est pas le temps de la fonction qui compte, c'est le rendu
     qu'elle déclenche.
     Le seuil de 0,004 est un peu moins d'un 256e : en dessous, l'écart ne peut
     pas se voir sur un canal 8 bits. */
  function setXray(aShell, aReste) {
    if (!fadeMats) return;
    for (var k = 0; k < fadeMats.length; k++) {
      var e = fadeMats[k], a = e.shell ? aShell : aReste, blend = a < 0.99;
      if (blend === e.blend && Math.abs(a - e.a) < 0.004) continue;
      if (blend !== e.blend) {
        e.m.setAlphaMode(blend ? 'BLEND' : 'OPAQUE');
        if (e.m.setDoubleSided) e.m.setDoubleSided(!blend);
        e.blend = blend;
      }
      e.a = a;
      e.m.pbrMetallicRoughness.setBaseColorFactor(
        [e.rgb[0], e.rgb[1], e.rgb[2], blend ? a : 1]);
    }
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

  /* Cible de cadrage, réécrite en place à chaque image : la boucle tourne à 60 Hz,
     inutile d'y allouer un objet. */
  var gTmp = { theta: 0, phi: 0, r: 0, zoom: 0, t: 0 };
  /* Au-delà d'un demi-pas parcouru en une image, ce n'est plus un geste mais un
     SAUT : glissé de barre de défilement, Page suivante, lien d'ancre, coup de
     molette d'une souris rapide. Un demi-pas (450 px) couvre déjà une transition
     entière, il n'y a donc rien à lisser — et lisser quand même coûte cher : la
     caméra met ~300 ms à rattraper son retard, pendant lesquelles l'éclatement,
     lui, est déjà arrivé. C'est comme cela qu'on obtenait une coque en verre qui
     tourne, seul cas où cela se produisait encore (mesuré identique sur la version
     à cadrages enclenchés : le défaut est antérieur aux rampes, il vient du
     lissage). Au-dessus du seuil, cadrage et position dans le clip sont posés
     d'un coup, ensemble : rien ne peut plus se désynchroniser. */
  var TELEPORT = 0.5;
  var lastU = null;
  var camPosee = false;   // cf. « le plan coté n'apparaît que caméra arrivée »
  var still = 1;          // 1 = caméra posée, 0 = elle tourne (cf. le verre)
  var derniereOrbite = null, dernierTemps = -1;   // cf. « on n'écrit que ce qui change »
  var lastShown = null;   // angle RÉEL de la caméra à l'image précédente, en degrés
  var cur = { theta: SCENES[0].theta, phi: SCENES[0].phi, r: SCENES[0].r,
              zoom: SCENES[0].zoom, t: SCENES[0].t, alpha: 1, iso: 0, isoA: 1 };
  var loaded = false, running = false, lastP = -1, wasScrub = false, onScreen = false;

  if (viewer) {
    viewer.addEventListener('load', function () {
      loaded = true;
      viewer.pause();          // sinon l'horloge interne écrase nos écritures
      resolveMats();
      apply(true);
    });
  }

  function lerp(a, b, k) { return a + (b - a) * k; }
  /* Écrit une propriété personnalisée seulement si sa valeur change. Le style
     d'un élément est lu en retour, ce qui est bon marché sur une propriété
     personnalisée (aucun calcul de mise en page n'en dépend directement). */
  function poser(style, prop, val) {
    if (style.getPropertyValue(prop) !== val) style.setProperty(prop, val);
  }
  var derniereImage = 0;
  /* ── LISSAGE NORMALISÉ AU TEMPS ───────────────────────────────────────────
     Un `lerp(a, b, 0.16)` appliqué UNE FOIS PAR IMAGE n'a pas la même vitesse
     selon la cadence : sur un écran à 120 Hz il converge deux fois plus lentement
     en secondes que sur un 60 Hz, et sur un écran à 144 Hz encore moins. Le
     défaut ne se voit pas en comparant deux machines l'une après l'autre, mais il
     est mesurable : en mode invisible, où le rendu logiciel du modèle tombe à
     ~7 images par seconde, la même constante converge en une image au lieu de
     vingt.
     `parImage(base, dt)` rend le facteur équivalent à `base` par image de 16,67 ms,
     quelle que soit la cadence réelle. La sensation devient donc la même partout,
     et c'est la condition pour que « aussi fluide que sur leur site » veuille dire
     quelque chose. Le facteur reste borné à 1, donc aucun dépassement possible
     après une longue interruption (changement d'onglet). */
  function parImage(base, dt) {
    /* La formule vaut dans LES DEUX SENS, et le court-circuit « si dt <= 16.67,
       renvoyer base » que j'avais écrit d'abord était faux : sur un écran à
       120 Hz (dt = 8,3 ms) il faut un facteur PLUS PETIT, pas le même, sans quoi
       le lissage y reste deux fois plus rapide qu'à 60 Hz. */
    return dt > 0 ? 1 - Math.pow(1 - base, dt / 16.67) : base;
  }
  /* Courbe en S de Hermite : plate aux deux bouts, la plus économique qui soit. */
  function smooth(x) { return x * x * (3 - 2 * x); }


  /* ══ CALQUE D'ANNOTATIONS PROJETÉES ═══════════════════════════════════════
     Le décor de la séquence était en CSS : un trait pour le bureau, un rectangle
     incliné en `perspective()` pour la feuille au sol, des étiquettes de cote posées
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

    /* Feuille de référence au sol, sans légende.

       ELLE EST DÉSORMAIS À L'ÉCHELLE RÉELLE, ET C'EST NOUVEAU. Le modèle mesure
       21,3 × 11,7 cm au sol pour 14,6 cm de haut ; la fiche produit annonçait
       40 × 24 cm, deux échelles qui ne coïncidaient pas, et la feuille devait
       être corrigée par un facteur (42/40 et 29,7/24) pour que le dessin ne
       contredise pas le texte. Les cotes publiées sont passées à 20 × 11 × 15 cm
       le 2026-08-28 : le fichier et la fiche disent maintenant la même chose à
       un centimètre près, donc le facteur n'a plus lieu d'être.

       La feuille passe de A3 à A4 (21 × 29,7 cm), exprimée directement en unités
       du fichier, qui sont des mètres. Un boîtier de 11,7 × 21,3 y tient avec
       une marge lisible ; sur une A3 il aurait occupé le quart de la page et la
       feuille aurait cessé d'être une référence pour devenir un vide. */
    var SHEET = { x: 0.210 / 2, z: 0.297 / 2 };

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
      { seat: [ 0.0138, 0.1123, -0.0118], v: [ 0.00042,  0.03842, -0.00619] },  // vitre
      { seat: [ 0.0000, 0.0143,  0.0425], v: [-0.05327,  0.04735, -0.02170] }   // nano-ordinateur
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
    /* Caméra NOMINALE du pas courant, et le centre du volume vu par elle. Tout ce
       qui est un CHOIX — de quel côté poser une cote, sur quel coin poser une
       étiquette — s'y réfère, jamais à la caméra en vol. Le placement, lui, reste
       calculé sur la caméra réelle : les annotations suivent donc l'objet image par
       image, seul le côté est figé.
       POURQUOI. Ces choix sont des comparaisons (« la face la plus proche »,
       « le coin le plus éloigné du centre »), et une comparaison bascule d'un coup.
       Mesuré sur la seconde moitié de la séquence : au franchissement de 0,611 du
       parcours, TROIS annotations sautaient dans la même image, à pleine opacité —
       « 15 cm » de 507 unités, « 11 cm » de 466, l'étiquette de la feuille de
       336. C'est ce que le balayage 3 → 4 donnait à voir : un plan qui se réorganise
       brusquement, que l'œil lit comme un défaut d'affichage du fond. Le même défaut
       avait été corrigé juste avant sur « emplacement du smartphone ». */
    var CN = null, midHiN = [0, 0];
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
    /* Même géométrie que `readCamera`, mais sur les valeurs de consigne du pas
       (degrés et mètres absolus de la table SCENES) au lieu de l'état du viewer.
       Le champ de vision reste celui du composant : il ne change jamais. */
    function camNominal(sc) {
      if (!sc) return null;
      var t = viewer.getCameraTarget(), w = scene.offsetWidth, h = scene.offsetHeight;
      if (!w || !h) return null;
      var th = sc.theta * Math.PI / 180, ph = sc.phi * Math.PI / 180;
      var tgt = [t.x, t.y, t.z], sp = Math.sin(ph), cp = Math.cos(ph);
      var eye = [tgt[0] + sc.r * sp * Math.sin(th),
                 tgt[1] + sc.r * cp,
                 tgt[2] + sc.r * sp * Math.cos(th)];
      var f = nrm(sub(tgt, eye)), sv = nrm(crs(f, [0, 1, 0]));
      return { eye: eye, f: f, s: sv, u: crs(sv, f), w: w, h: h,
               th: Math.tan(viewer.getFieldOfView() * Math.PI / 360), aspect: w / h };
    }
    function depth(p) { return dot(sub(p, C.eye), C.f); }
    /* Profondeur et projection dans la caméra nominale — pour les choix seulement.
       Repli sur la caméra réelle si la consigne n'est pas encore connue. */
    function depthN(p) { var c = CN || C; return dot(sub(p, c.eye), c.f); }
    function projN(p) {
      var c = CN || C, d = sub(p, c.eye), z = dot(d, c.f);
      return [(0.5 + 0.5 * (dot(d, c.s) / z) / (c.th * c.aspect)) * c.w,
              (0.5 - 0.5 * (dot(d, c.u) / z) / c.th) * c.h];
    }
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
    /* MÊME RÈGLE QUE POUR LES MATÉRIAUX : on n'écrit que ce qui change. Une
       écriture d'attribut SVG invalide le style de l'élément et fait recalculer
       la mise en page du calque ; sur un calque de trente éléments réécrits à
       chaque image, l'essentiel des écritures reposait la valeur déjà en place.
       `getAttribute` est une lecture d'attribut, pas de style calculé : elle ne
       force aucun recalcul. */
    /* Un seul attribut, même garde. Les appels directs à `setAttribute` du calque
       sont tous passés par ici : ils sont sur le chemin de chaque image. */
    function att(el, k, v) { v = String(v); if (el.getAttribute(k) !== v) el.setAttribute(k, v); }

    function put(el, attrs) {
      for (var k in attrs) {
        var v = String(attrs[k]);
        if (el.getAttribute(k) !== v) el.setAttribute(k, v);
      }
    }

    /* Sous 900 px la scène déborde volontairement de l'écran — l'objet est coupé
       par le bord droit. Une étiquette calculée au bon endroit dans le repère de
       la scène peut donc tomber hors du viewport : « 20 cm » se retrouvait à
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
      att(el, 'transform', 'matrix(' +
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
    function nearSide(a, b) { return depthN(a) < depthN(b) ? -1 : 1; }

    function cote(d, a0, b0, off) {
      var a = add(a0, off, 1), b = add(b0, off, 1);
      var tick = nrm(off);
      var path = seg(a, b) + seg(add(a, tick, -0.008), add(a, tick, 0.008)) +
                             seg(add(b, tick, -0.008), add(b, tick, 0.008));
      att(d.line, 'd', path);
      att(d.ext, 'd', seg(a0, add(a, tick, 0.006)) + seg(b0, add(b, tick, 0.006)));
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
    function draw(t, sc) {
      C = readCamera();
      CN = camNominal(sc);
      if (!C) return 0;
      var i, j, p;

      /* Occulteur : l'enveloppe de la coque, en pixels. */
      var corners = [];
      for (i = 0; i < 2; i++) for (j = 0; j < 2; j++) for (var k = 0; k < 2; k++)
        corners.push(proj([BOX.x[i], BOX.y[j], BOX.z[k]]));
      var hp = hull(corners).map(function (c) { return c[0].toFixed(1) + ',' + c[1].toFixed(1); }).join(' ');
      for (i = 0; i < occl.length; i++) att(occl[i], 'points', hp);

      midHi = proj([0, BOX.y[1] / 2, 0]);
      midHiN = projN([0, BOX.y[1] / 2, 0]);            // centre du volume, pour orienter les cotes

      groundDisc(pool, 0.27);
      groundDisc(fadeDisc, 0.30);      /* un peu plus large que le quadrillage */

      for (i = 0; i < grid.length; i++) {
        var g = grid[i];
        att(grid[i].el, 'd', g.ax
          ? seg([-GL, 0, g.k], [GL, 0, g.k])
          : seg([g.k, 0, -GL], [g.k, 0, GL]));
      }

      /* ── Pas 2 : le contour du smartphone à quai ─────────────────────── */
      att(ghost, 'd', roundQuad(PH, 0.009));
      att(gScreen, 'd', roundQuad({ r: PH.r - 0.005, u0: PH.u0 + 0.008, u1: PH.u1 - 0.008 }, 0.005));
      /* Une encoche de 2 cm en haut de la dalle. C'est un détail minuscule, et
         c'est lui qui fait basculer la lecture : sans elle, deux rectangles
         concentriques posés sur la face avant passent pour un cadre décoratif. */
      att(gNotch, 'd', seg(ph(-0.010, PH.u1 - 0.016), ph(0.010, PH.u1 - 0.016)));
      var face = [ph(-PH.r, PH.u0), ph(PH.r, PH.u0), ph(PH.r, PH.u1), ph(-PH.r, PH.u1)];
      var dockPt = proj(DOCK);
      put(node, { cx: dockPt[0].toFixed(1), cy: dockPt[1].toFixed(1) });
      /* Ligne de rappel : TOUJOURS vers la gauche, et depuis le coin haut gauche
         de la silhouette. Deux choix figés, et c'est tout l'objet de ce bloc.
         La version d'avant prenait « celui des deux coins hauts qui se projette le
         plus haut », puis partait « du côté opposé au centre du volume ». Les deux
         critères basculent pendant le balayage de caméra : mesuré image par image
         sur un défilement continu, le libellé sautait de `end` x=245 à `start`
         x=543 entre DEUX IMAGES, à pleine opacité — 298 unités d'un coup, au
         milieu du pas. Une annotation qui change de côté sous l'œil n'annote plus.
         POURQUOI LA GAUCHE. À ce cadrage la silhouette du téléphone est à 61
         unités du flanc gauche de la coque contre 102 du flanc droit : c'est par
         la gauche que le trait sort le plus court, donc le seul côté où le libellé
         se pose hors du produit. Verrouiller le côté sans changer le point
         d'accroche ne suffisait pas — l'ancien point est le coin haut DROIT, et
         mesuré ainsi le libellé mordait la coque sur les 151 images du pas.
         `face[3]` est le coin (−r, u1) du téléphone : son coin haut du côté des X
         négatifs. La séquence ne s'écarte jamais de plus de 42° de la face, donc
         ce coin reste à gauche à l'écran d'un bout à l'autre — le point d'accroche
         est stable par construction, pas par comparaison. */
      var top = proj(face[3]);
      var away = -1;
      /* Longueurs raccourcies de 16 unités au total (34→24, 22→18, 28→22) : le
         libellé était « légèrement trop à gauche », il se recentre vers le produit
         sans changer de côté ni de point d'accroche. Relevé après coup : il reste
         de 10 à 20 px du bord du boîtier pendant tout le pas, et le trait de
         rappel garde sa forme en L. */
      var lx = top[0] + away * 24, ly = top[1] - 30;
      att(lead, 'd', 'M' + top[0].toFixed(1) + ' ' + top[1].toFixed(1) +
                             'L' + lx.toFixed(1) + ' ' + ly.toFixed(1) +
                             'h' + (away * 18));
      label(labDock, lx + away * 22, ly, away > 0 ? 'start' : 'end', 150);

      /* ── Pas 3 : les repères d'assemblage ────────────────────────────── */
      var kt = Math.max(0, Math.min(1, t / BURST_END));
      /* LES REPÈRES D'ASSEMBLAGE N'EXISTENT QUE S'IL Y A QUELQUE CHOSE À REPÉRER.
         Le calque était allumé sur tout le pas 3, or l'éclatement s'y ouvre PUIS se
         referme : à la fin du pas, les traits ont une longueur nulle mais les quatre
         anneaux restent dessinés, rayon 2,5, sur un boîtier fermé. Mesuré : de 0,520
         à 0,555 du parcours, quatre ronds teal posés sur le produit, puis le fondu
         de sortie du calque par-dessus. C'est le défaut signalé par le client, celui
         qu'on voyait entre deux positions de défilement.
         L'opacité du calque suit donc l'ouverture. Elle est écrite ici plutôt que
         déduite d'un pas, parce que c'est la seule grandeur qui dise s'il y a un
         écartement à montrer. */
      poser(root.style, '--sc-burst', kt.toFixed(3));
      for (i = 0; i < PARTS.length; i++) {
        var s0 = PARTS[i].seat, now = add(s0, PARTS[i].v, kt);
        att(burst[i].line, 'd', seg(s0, now));
        var c0 = proj(s0);
        put(burst[i].ring, { cx: c0[0].toFixed(1), cy: c0[1].toFixed(1), r: (2.5 + 2 * kt).toFixed(1) });
      }

      /* ── Pas 4 : feuille de référence et cotes ─────────────────────────────────── */
      var sh = [[-SHEET.x, 0, -SHEET.z], [SHEET.x, 0, -SHEET.z], [SHEET.x, 0, SHEET.z], [-SHEET.x, 0, SHEET.z]];
      att(sheet, 'd', poly(sh, true));
      /* Équerres de repérage aux quatre coins : le langage d'un plan, et le
         seul endroit du tracé où le teal est franc. */
      var mk4 = '', L = 0.026;
      for (i = 0; i < 4; i++) {
        var sx = i === 0 || i === 3 ? -1 : 1, sz = i < 2 ? -1 : 1;
        var c = [sx * SHEET.x, 0, sz * SHEET.z];
        mk4 += seg(c, [c[0] - sx * L, 0, c[2]]) + seg(c, [c[0], 0, c[2] - sz * L]);
      }
      att(marks, 'd', mk4);
      /* La feuille n'est plus légendée : la mention « feuille A3 » a été retirée du
         site à la demande du client, qui la juge inutile puisque les trois cotes
         disent déjà l'encombrement. Le tracé de la feuille reste — c'est lui qui
         donne aux cotes au sol un cadre où se poser. Avec l'étiquette part le choix
         du coin le plus dégagé, qui n'existait que pour elle. */

      var OFF = 0.034;
      var sxSide = nearSide([-BOX.x[1], 0, 0], [BOX.x[1], 0, 0]);
      var szSide = nearSide([0, 0, -BOX.z[1]], [0, 0, BOX.z[1]]);

      /* Profondeur (20 cm) le long de Z, largeur (11 cm) le long de X. */
      cote(dims.depth, [sxSide * BOX.x[1], 0, BOX.z[0]], [sxSide * BOX.x[1], 0, BOX.z[1]],
           [sxSide * OFF, 0, 0]);
      cote(dims.width, [BOX.x[0], 0, szSide * BOX.z[1]], [BOX.x[1], 0, szSide * BOX.z[1]],
           [0, 0, szSide * OFF]);
      /* Hauteur (15 cm) sur l'arête de silhouette : celle dont la projection
         s'écarte le plus du centre, donc celle qui borde l'objet à l'écran. */
      var best = null, bd = -1;
      for (i = 0; i < 2; i++) for (j = 0; j < 2; j++) {
        var e0 = [BOX.x[i], 0, BOX.z[j]];
        p = projN(e0);
        var dd = Math.abs(p[0] - midHiN[0]);
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
    /* Écart réel depuis l'image précédente. Il sert à normaliser les lissages :
       cf. `parImage()`. `snap` remet la référence à zéro, sinon la première image
       après un saut ou un redimensionnement porterait l'écart de l'attente. */
    var maintenant = performance.now();
    var dt = (snap || !derniereImage) ? 16.67 : maintenant - derniereImage;
    derniereImage = maintenant;
    var p = progress();
    var i = nearest();
    var u = head(i);
    var jump = lastU !== null && Math.abs(u - lastU) > TELEPORT;
    lastU = u;
    var mix = camAt(u);
    var A = SCENES[mix.a], B = SCENES[mix.b], e = mix.e;
    var g = gTmp;
    g.theta = A.theta + (B.theta - A.theta) * e;
    g.phi   = A.phi   + (B.phi   - A.phi)   * e;
    g.r     = A.r     + (B.r     - A.r)     * e;
    g.zoom  = A.zoom  + (B.zoom  - A.zoom)  * e;
    g.t     = A.t     + (B.t     - A.t)     * e;
    /* Lissage, et non plus inertie : la cible étant désormais donnée par le
       défilement, ce facteur ne sert qu'à transformer un cran de molette en
       glissement, même rôle que le 0.22 de la position dans le clip.
       LES DEUX SONT NORMALISÉS AU TEMPS DEPUIS LE 2026-09-03, cf. `parImage()`. */
    var k = (snap || jump) ? 1 : parImage(0.16, dt);
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
    /* L'ISOLEMENT NE PEUT PAS ÊTRE UNE FONCTION DE LA POSITION DANS LE CLIP,
       contrairement à l'opacité de la coque, et ce n'est pas un oubli : pendant la
       TENUE le clip est à sa borne et ne bouge plus, par construction — c'est ce
       palier qui rend le boîtier ouvert lisible. Un second temps pendant la tenue
       ne peut donc se lire que sur le défilement. Il est en revanche soumis
       exactement à la même discipline que `cur.t` (saut à l'entrée et à la sortie
       du pas, lissage à 0,22 pendant), donc les deux ne peuvent pas se
       désynchroniser : c'est la mise en garde du pavé « L'OPACITÉ N'EST PAS UNE
       PHASE », et elle est respectée.
       Pendant la refermeture, l'isolement suit `burstK` : les pièces redeviennent
       solides à mesure que le boîtier se referme, et la valeur est continue au
       passage de BURST_HOLD, où `burstK` vaut encore 1. */
    var isoK = !scrub               ? 0
             : f <= BURST_FULL      ? 0
             : f <= BURST_HOLD      ? Math.min(1, (f - BURST_FULL) / (ISO_END - BURST_FULL))
             : burstK;
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
    var kt = parImage(0.22, dt);
    if ((cur.t < PHONE_HANDOFF) !== seg) cur.t = tTarget;   // on ne franchit jamais t=1.0
    else if (scrub !== wasScrub || jump) cur.t = tTarget;   // entrée/sortie du pas, ou saut
    else if (scrub) cur.t = lerp(cur.t, tTarget, kt);       // pendant le pas
    else cur.t = lerp(cur.t, tTarget, k);
    /* Le même mot à mot que ci-dessus, sur la même valeur de lissage : c'est ce qui
       garantit que l'isolement ne prend jamais un pixel de retard sur l'ouverture. */
    if (scrub !== wasScrub || jump) cur.iso = isoK;
    else if (scrub) cur.iso = lerp(cur.iso, isoK, kt);
    else cur.iso = lerp(cur.iso, isoK, k);
    wasScrub = scrub;
    if (cur.t > 1.98) cur.t = 1.98;   // jamais la durée exacte : le mixer y verrait une boucle
    if (cur.t > 0.98 && cur.t < PHONE_HANDOFF) cur.t = 0.98;

    /* L'opacité, lue sur la position RÉELLE dans le clip — donc après toutes les
       corrections ci-dessus, saut de segment compris. Aucune inertie propre : elle
       ne peut ni prendre du retard sur l'ouverture, ni la devancer. La courbe en S
       reste utile, l'œil étant plus sensible aux premiers pourcents de transparence
       qu'aux derniers. */
    cur.alpha = 1 - (1 - XRAY_ALPHA) * smooth(Math.min(1, cur.t / EXPLODE_END));
    /* Le reste du boîtier — plateau, petites pièces, embase, vitre — descend à la
       MÊME opacité que la coque, et pas plus bas : la carte devient ainsi la seule
       pièce solide de l'image, tout en laissant le boîtier « légèrement visible »,
       ce qui est ce qui donne l'échelle. La carte, elle, n'est jamais touchée. */
    cur.isoA = 1 - (1 - XRAY_ALPHA) * smooth(Math.max(0, Math.min(1, cur.iso)));

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
      /* MÊME RÈGLE QUE POUR LES MATÉRIAUX : on n'écrit que ce qui change. Ces deux
         propriétés sont les plus coûteuses de la boucle, non par leur exécution
         mais par le rendu qu'elles déclenchent. `currentTime` en particulier : aux
         pas 1, 2 et 4 le clip est immobile à 0, et le réécrire à chaque image
         faisait rejouer l'animation ET la passe d'ombre pour rien. */
      var orb = goal.toFixed(2) + 'deg ' + cur.phi.toFixed(2) + 'deg ' + cur.r.toFixed(4) + 'm';
      if (orb !== derniereOrbite) { viewer.cameraOrbit = orb; derniereOrbite = orb; }
      if (Math.abs(cur.t - dernierTemps) > 0.0005) { viewer.currentTime = cur.t; dernierTemps = cur.t; }
      var shown = HUD.draw(cur.t, SCENES[i]) * 180 / Math.PI;
      camLag = Math.abs(shown - goal) > 0.02;

      /* ── LE PLAN COTÉ N'APPARAÎT QUE CAMÉRA ARRIVÉE ──────────────────────
         Le pas 4 dessine un plan : une feuille au sol et trois cotes. Ses choix de
         côté sont figés sur la caméra NOMINALE du pas, pour qu'ils ne basculent
         pas en cours de route. Conséquence non vue à l'époque : tant que la caméra
         n'est pas arrivée, ce plan est juste pour un angle qui n'est pas celui
         qu'on regarde, et il traverse le produit. Constaté à l'image sur le GPU, à
         61° de l'angle final : la cote « 15 cm » barre le boîtier de haut en bas et
         l'étiquette de la feuille se pose sur sa face. Le balayage du pas 3 au pas 4
         fait 86°, le plus long de la séquence, et le calque s'allumait dès le
         premier pixel.

         On attend donc que la caméra soit posée. Deux détails :
         - seuil à 10°, hystérésis à 16° : sans elle, la dérive au repos (±3,2°)
           suffirait à faire clignoter le calque ;
         - la comparaison porte sur l'angle NOMINAL du pas et non sur ma consigne
           lissée, puisque c'est l'angle pour lequel le plan a été calculé.
         Le fondu de 0,55 s du calque fait le reste : le plan se pose au lieu
         d'apparaître. */
      var ecartNom = Math.abs(shown - SCENES[i].theta);
      if (ecartNom > 180) ecartNom = 360 - ecartNom;
      if (camPosee && ecartNom > 16) camPosee = false;
      else if (!camPosee && ecartNom < 10) camPosee = true;
      root.classList.toggle('is-cam-posee', camPosee);
      /* ET LE VERRE EXIGE UNE CAMÉRA POSÉE.
         Les paliers séparent déjà les deux mouvements tant que le défilement est un
         geste : l'éclatement se joue caméra immobile, mesuré à 42,00° d'un bout à
         l'autre de sa fenêtre. Ils n'y suffisent plus quand le défilement est
         PROGRAMMÉ. `html { scroll-behavior: smooth }` est posé sur tout le site, et
         les pastilles de la séquence sont de vrais liens d'ancre : un clic sur la
         pastille 3 parcourt jusqu'à trois pas en ~400 ms. La consigne de cadrage
         saute alors bien plus vite que la caméra ne la suit, et l'on voyait une
         coque en verre qui tourne. Le seuil de saut ne peut rien y faire : une
         animation de défilement avance par petits pas, indiscernables d'une molette
         rapide.
         La règle est donc énoncée sur l'état, et sur la SEULE grandeur qui la dise :
         le déplacement réel de la caméra d'une image à l'autre. Ni la consigne ni
         mon propre lissage ne suffisent — model-viewer lisse encore de son côté (le
         même retard qui oblige `camLag` à exister), si bien qu'un filet posé sur
         l'écart à ma cible laissait passer l'essentiel du défaut : mesuré, il n'en
         retirait que 2 images sur 15.
         Aucun blocage en retour : la caméra n'attend rien, elle converge, et le
         verre revient avec — la boucle continue de tourner tant que `camLag` est
         vrai, donc jusqu'à ce qu'elle soit posée. Sur un défilement à la molette le
         déplacement reste sous le seuil pendant toute la fenêtre : ce filet ne
         change rien à ce qui a été validé, il ne rattrape que les sauts. */
      /* LA VITESSE EST EN DEGRÉS PAR SECONDE, PLUS PAR IMAGE, DEPUIS LE 2026-09-03.
         Par image, le seuil dépendait de la cadence exactement comme les lissages
         (cf. `parImage`) : sur un écran à 120 Hz la caméra paraissait deux fois plus
         lente qu'à 60, et sur une machine qui tombe à 7 images par seconde elle
         paraissait vingt fois plus rapide, donc la coque restait opaque en
         permanence. Le défaut s'est révélé quand les pas ont été raccourcis le
         2026-09-03 : à 7 images par seconde, la coque ne repassait plus au verre au
         pas 3, alors qu'elle le faisait avec des pas d'un écran. Les seuils sont les
         anciens convertis à 60 Hz : 0,10 et 0,35 degré par image valent 6 et 21
         degrés par seconde.
         ET `still` DOIT ENTRER DANS `moving`, sinon la boucle peut s'arrêter sur une
         image où la caméra bougeait encore : la coque resterait opaque jusqu'au
         prochain défilement. Même famille que l'oubli de `cur.iso`. */
      var spin = (lastShown === null || dt <= 0) ? 0 : Math.abs(shown - lastShown) * 1000 / dt;
      lastShown = shown;
      still = Math.min(1, Math.max(0, (21 - spin) / 15));
      setXray(1 - (1 - cur.alpha) * still, 1 - (1 - cur.isoA) * still);
    }
    /* Même règle, et elle compte autant : `--sc-zoom` porte un `scale()` sur la
       scène qui CONTIENT le canevas, donc chaque écriture demande au compositeur
       de rematricer la couche ; `--sc-glow` déplace le centre d'un dégradé de
       4 Mpx, le piège documenté dans la feuille de style. Trois décimales pour le
       zoom (un dix-millième de facteur ne se voit pas sur 660 px) et le pixel
       entier pour le halo. */
    poser(stage.style, '--sc-zoom', cur.zoom.toFixed(3));
    poser(stage.style, '--sc-glow', (p * 60 - 30).toFixed(0) + 'px');
    if (bar) poser(bar.style, '--sc-p', p.toFixed(3));

    if (i !== lastP) {
      lastP = i;
      for (var j = 0; j < steps.length; j++) steps[j].classList.toggle('is-active', j === i);
      /* Le pas courant est exposé sur la section : les accessoires de scène sont
         alors purement déclaratifs en CSS, sans connaître l'ordre du HTML. */
      root.setAttribute('data-step', String(i));
      if (count) {
        /* Deux écritures pour une seule information. Le compteur était entièrement
           `aria-hidden` et les pastilles — les seules à porter `aria-current` —
           sont masquées sous 900 px : sur téléphone, un lecteur d'écran ne savait
           donc NI qu'une séquence de quatre pas était en cours, NI où elle en
           était. La forme chiffrée « 03 / 04 » reste pour l'œil, une phrase la
           double pour l'oreille, et le `role="status"` de l'élément la fait
           annoncer au changement de pas — quatre fois au total, pas de bavardage. */
        var num = String(i + 1).padStart(2, '0') + ' / ' + String(steps.length).padStart(2, '0');
        count.innerHTML = '<span aria-hidden="true"><b>' + num.slice(0, 2) + '</b>' + num.slice(2) + '</span>' +
          '<span class="visually-hidden">' + (FR ? 'Étape ' + (i + 1) + ' sur ' + steps.length
                                                : 'Step ' + (i + 1) + ' of ' + steps.length) + '</span>';
      }
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
    /* Le CSS ne peut pas savoir seul que la séquence est à l'écran, et deux
       éléments en dépendent sur téléphone : le bouton « retour en haut », qui
       recouvrait le compteur d'étapes (mesuré : boutons en collision sur 35 × 5 px),
       et le lien pour sortir de la séquence, qui n'existait qu'au focus clavier —
       donc pas du tout sur un téléphone. Un seul drapeau les gouverne. */
    document.body.classList.toggle('is-scrolly', onScreen);
    /* SORTIE DE SÉQUENCE. `p` atteint 1 pile au moment où le bloc collant se
       décroche : la dernière hauteur d'écran de la section sert à l'évacuer, et
       pendant ce temps le produit s'en va vers le haut. Sur téléphone la carte de
       texte est posée en `fixed` dans la zone du bas (cf. scrolly.css) : sans ce
       drapeau elle resterait accrochée à l'écran pendant que la scène part, et se
       retrouverait posée sur la section suivante. On la fait disparaître, ce qui
       clôt la séquence au lieu de la laisser traîner. Le drapeau n'est utilisé que
       sous 900 px : au-dessus, le texte est à côté de la scène et part avec elle,
       ce qui est le comportement voulu. */
    document.body.classList.toggle('is-scrolly-exit', onScreen && p >= 1);
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
                 /* L'ISOLEMENT DOIT FIGURER ICI, et son absence a été mesurée avant
                    d'être corrigée : la boucle s'arrêtait dès que la caméra et le clip
                    étaient posés, donc au milieu du fondu. Relevé à l'instant où le
                    texte est centré : opacité du boîtier à 0,49 au lieu de 0,26, soit
                    un isolement à moitié fait, et rien pour le reprendre puisque plus
                    aucune image n'était demandée. Toute valeur lissée ajoutée à
                    `apply()` doit entrer dans ce test. */
                 Math.abs(isoK - cur.iso) > 0.002 ||
                 still < 0.999 ||
                 /* la dérive entretient la boucle : sans ça elle s'arrêterait au repos,
                    c'est-à-dire précisément quand elle doit jouer. */
                 idle || idleK > 0.002 || camLag;
    if (moving) { running = true; requestAnimationFrame(function () { apply(false); }); }
    else running = false;
  }

  /* ── Hauteur réservée au texte, relevée sur les cartes elles-mêmes ────────
     Sur téléphone la scène occupe ce que la carte ne prend pas. Encore faut-il
     savoir ce que la carte prend : ses quatre variantes vont de 209 à 344 px
     selon le pas, la largeur de l'écran et la longueur du texte, et toute
     constante écrite à la main retombe fausse au premier mot ajouté — c'est
     comme ça que le recouvrement mesuré au départ (16 px sur iPhone SE) est
     réapparu deux fois pendant la correction. On relève donc la plus haute des
     cartes, une fois au chargement et à chaque redimensionnement, et le CSS en
     déduit la place de la scène.
     Rien n'est circulaire : la hauteur d'une carte ne dépend pas de la scène,
     seulement de sa propre largeur et de son contenu.
     La mise en page en deux colonnes du paysage n'a, elle, aucune zone à
     réserver : on retire alors la propriété pour laisser la feuille de style
     décider (un style en ligne l'emporterait sur elle). */
  /* ── Indicateur de chargement ─────────────────────────────────────────────
     Tant que le modèle n'est pas là, model-viewer affiche son affiche : une image
     figée, impossible à distinguer d'une séquence en panne. On expose donc la
     progression réelle du téléchargement, et on la retire dès que le modèle est
     prêt. `aria-hidden` : c'est une information d'attente, pas de contenu, et le
     texte du pas est déjà lisible pendant ce temps. */
  var loader = root.querySelector('.scrolly__loading');
  if (viewer && loader) {
    var pct = loader.querySelector('b');
    loader.hidden = false;
    viewer.addEventListener('progress', function (e) {
      var v = Math.round((e.detail && e.detail.totalProgress || 0) * 100);
      if (pct) pct.textContent = v + ' %';
      if (v >= 100) loader.hidden = true;
    });
    viewer.addEventListener('load', function () { loader.hidden = true; });
    /* FILET DE SÉCURITÉ. Le modèle est compressé en Draco, et model-viewer va
       chercher le décodeur correspondant sur www.gstatic.com — le même domaine que
       les polices du site, donc pas une dépendance d'un genre nouveau, mais une
       dépendance de plus. Vérifié en la bloquant : le modèle ne charge pas du tout,
       et la séquence reste alors sur son affiche sans jamais rien dire. Plutôt que
       de parier sur la disponibilité d'un tiers, on borne l'attente : passé le
       délai, le repli statique prend la place, et la séquence garde son récit.
       Le même filet couvre n'importe quelle autre panne — CDN indisponible,
       fichier corrompu, WebGL qui échoue après coup.

       DEUX PRÉCAUTIONS, sans lesquelles le filet étrangle ce qu'il devait protéger
       (constaté : sous 1440 px de large, la séquence tombait TOUJOURS sur son
       affiche, sur toutes les liaisons, y compris rapides) :

       1. Le compte à rebours part de l'ARRIVÉE près de la séquence, pas du
          chargement de la page. La balise porte `loading="lazy"` : tant que la
          séquence est sous la ligne de flottaison, model-viewer ne demande même
          pas le fichier. Or sur un écran étroit le hero occupe le premier écran
          entier, donc la scène est toujours hors champ au chargement : le délai
          expirait avant la première requête, et le visiteur n'a jamais vu le
          modèle. Vérifié : aucune requête `qbot.glb` à 390, 768 et 1024 px, et
          `data-fallback="modele indisponible"` à chaque fois.
       2. Le délai est relancé à chaque signe de vie. Un téléchargement qui
          progresse n'est pas une panne : 12 s comptent l'ABSENCE de progrès, pas
          la durée totale. Sinon une liaison lente est déclarée en panne alors que
          le fichier arrive. */
    var giveUp = null;
    function abandonner() {
      if (viewer.model) return;
      loader.hidden = true;
      if (fallback) {
        fallback.hidden = false;
        viewer.style.display = 'none';
        root.setAttribute('data-fallback', 'modele indisponible');
      }
    }
    function armer() {
      if (viewer.model) return;
      clearTimeout(giveUp);
      giveUp = setTimeout(abandonner, 12000);
    }
    viewer.addEventListener('progress', armer);
    viewer.addEventListener('load', function () { clearTimeout(giveUp); });
    /* Aucune marge sur l'observateur : il faut que la scène soit RÉELLEMENT à
       l'écran. Une marge de 400 px suffisait à armer le délai au chargement sur un
       téléphone (la séquence commence juste sous le hero), et on retombait sur le
       même défaut. */
    if (window.IntersectionObserver) {
      var veille = new IntersectionObserver(function (entrees) {
        for (var i = 0; i < entrees.length; i++) {
          if (entrees[i].isIntersecting) { armer(); veille.disconnect(); return; }
        }
      });
      veille.observe(stage || viewer);
    } else {
      armer();
    }
  }

  var STACKED = window.matchMedia('(max-width: 900px) and (not ((orientation: landscape) and (max-height: 520px)))');

  /* ── LA HAUTEUR DE LA SECTION EST LA SOMME MESURÉE DES PAS ────────────────
     Le CSS demande `--sc-step` par pas et en déduit quatre pas plus la queue.
     Mais `min-height` cède à son contenu : là où une carte est plus haute que le
     pas demandé, le pas grandit et la somme réelle dépasse la hauteur de la
     section. Les pas débordent alors la section, et la scène collante se
     désynchronise des textes.
     C'EST UN DÉFAUT ANTÉRIEUR À LA RÉDUCTION DU 2026-09-03, et il se mesure : à
     844 x 390 (téléphone en paysage), les quatre pas faisaient déjà
     390 / 463 / 390 / 521 px, soit 1 764, pour une section de 1 638. Écrire la
     somme relevée referme la classe entière, quelle que soit la hauteur qu'une
     carte finit par prendre.
     Sans JavaScript, le repli du CSS (quatre fois le pas demandé) reste ce qu'il
     était : on ne perd rien, on ne gagne simplement pas la correction. */
  function measureSteps() {
    var somme = 0;
    for (var i = 0; i < steps.length; i++) somme += steps[i].getBoundingClientRect().height;
    if (somme > 0) root.style.setProperty('--sc-steps-sum', Math.ceil(somme) + 'px');
  }

  function measureCards() {
    measureSteps();
    if (!STACKED.matches) { root.style.removeProperty('--sc-card-zone'); return; }
    var max = 0;
    for (var i = 0; i < steps.length; i++) {
      var inner = steps[i].querySelector('.scrolly__step-inner');
      if (inner) max = Math.max(max, inner.getBoundingClientRect().height);
    }
    if (!max) return;
    var pad = parseFloat(getComputedStyle(steps[0]).paddingBottom) || 0;
    root.style.setProperty('--sc-card-zone', Math.ceil(max + pad) + 'px');
    /* La zone réservée change la hauteur de la scène, donc celle des pas sur
       téléphone : on remesure la somme APRÈS l'avoir écrite. */
    measureSteps();
  }

  /* ══ ACCROCHAGE : LE PAS SE POSE TOUT SEUL ═══════════════════════════════
     Demandé le 2026-09-03, sur la référence de scfo.de : « que l'animation se
     fasse seule au scroll sans s'arrêter parce qu'on s'arrête de scroller ».

     LE DÉFAUT QUE ÇA CORRIGE. La séquence est SCRUBBÉE : cadrage, éclatement et
     fondu d'isolement sont des fonctions de la position de défilement. Un cran de
     molette de trop laissait donc le boîtier à moitié ouvert, la coque à moitié en
     verre, la caméra entre deux cadrages — trois états qui ne sont voulus nulle
     part et qu'aucun texte n'accompagne. Le scrub reste (c'est lui qui rend la
     séquence réversible au doigt), mais dès que le geste s'arrête, la séquence
     rejoint le pas le plus proche et l'animation se termine.

     LE POINT D'ACCROCHE EST LE CENTRE DU PAS, et il n'y a rien à régler : c'est
     déjà le critère de `nearest()`, et c'est la position où `fraction()` vaut
     0,605, donc celle où le texte est centré, où le boîtier est grand ouvert et où
     l'isolement de la carte est complet. Mesuré à 1440x900, 1440x700, 1920x1080 et
     390x844 : la cible vaut 0,5 du pas à toutes ces tailles, donc aucune constante
     dépendant du viewport.

     LA COURBE ET LA DURÉE SONT CELLES DE scfo.de, relevées et non estimées. Leur
     transition dure 444 ms et sa forme, ajustée sur dix points (2 % à 59 ms, 22 %
     à 159, 44 % à 210, 71 % à 260, 95 % à 353, 100 % à 459), est une CUBIQUE EN S :
     écart moyen 0,021, contre 0,034 pour une quadratique et 0,036 pour une
     quartique. Une exponentielle sortante, elle, s'en écarte de 0,296.

     TROIS GARDE-FOUS, parce qu'un accrochage qui se bat avec le visiteur est pire
     que pas d'accrochage :
     - il ne part qu'après SNAP_REST sans défilement, donc jamais pendant un geste ;
     - il s'annule au premier signe d'intention (molette, doigt, clavier) et ne
       part pas tant qu'un bouton de souris est enfoncé, sinon il tirerait la page
       sous une barre de défilement qu'on est en train de traîner ;
     - au-delà de SNAP_ZONE de pas, il LÂCHE. C'est ce qui permet de sortir de la
       séquence par le haut comme par le bas : passé cette distance du centre du
       dernier pas, plus rien ne retient. */
  var SNAP_MS    = 450;    // durée de la glissade, relevée sur scfo.de
  var SNAP_REST  = 110;    // repos sans défilement avant de partir
  var SNAP_SEUIL = 0.12;   // part de pas au-delà de laquelle le geste ENGAGE
  var snapT = null, snapAF = null, pointeur = false;
  var ancre = null;        // le pas où l'on est posé, null si hors séquence

  /* Cubique en S. `smooth()` existe déjà plus haut mais c'est une hermite
     (quadratique en S) : elle démarre deux fois plus vite et n'a pas la même
     signature. Celle-ci est celle de la référence. */
  function easeInOut(x) {
    return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
  }

  /* Position de défilement qui met le centre du pas `i` au centre de la fenêtre. */
  function cibleY(i) {
    var r = steps[i].getBoundingClientRect();
    return window.scrollY + r.top + r.height / 2 - window.innerHeight / 2;
  }

  function stopGlissade() {
    if (snapAF !== null) { cancelAnimationFrame(snapAF); snapAF = null; }
    if (snapT !== null) { clearTimeout(snapT); snapT = null; }
  }

  /* ── ON DÉPLACE LA CIBLE DU MOTEUR DE DÉFILEMENT, ON N'ANIME PLUS ─────────
     Corrigé le 2026-09-03 sur signalement du client (« c'est saccadé »). Avant,
     cette fonction animait `window.scrollY` sur sa propre cubique de 450 ms, et le
     moteur du module 22 se retirait de la séquence pour ne pas la concurrencer.
     Conséquence non vue : dans la séquence, un cran de molette faisait SAUTER la
     page de 120 px en une image, en défilement natif, avant que l'accrochage ne
     prenne la main 110 ms plus tard. Chaque geste commençait par une secousse.
     Le GPU a été mesuré au même moment, en mode fenêtré : 59,9 images par seconde,
     médiane 16,70 ms, aucune image perdue, avec ou sans le module 22, avec ou sans
     l'ombre portée. Ce n'était donc pas une chute de cadence mais un saut de
     position.
     Un seul mécanisme gouverne donc la position : celui du module 22. L'accrochage
     ne fait plus que lui dire où aller. Le changement de destination en cours de
     course est continu par construction, une approche exponentielle ne présentant
     aucune discontinuité de position.
     LE REPLI RESTE une glissade maison, pour le cas où le module 22 serait absent
     (fichier non chargé, moteur sans `requestAnimationFrame`). `behavior: 'instant'`
     y est obligatoire : `<html>` porte `scroll-behavior: smooth`, donc un
     `scrollTo` par défaut confierait chaque image au lissage du navigateur, qui
     interromprait la précédente. */
  function glisser(y, ms) {
    stopGlissade();
    if (Math.abs(y - window.scrollY) < 1) return;
    if (window.QBotDefil && window.QBotDefil.vers(y, ms || SNAP_MS)) { kick(); return; }
    var y0 = window.scrollY, d = y - y0;
    var t0 = performance.now();
    (function image() {
      var x = Math.min(1, (performance.now() - t0) / (ms || SNAP_MS));
      window.scrollTo({ top: y0 + d * easeInOut(x), behavior: 'instant' });
      kick();
      snapAF = x < 1 ? requestAnimationFrame(image) : null;
    }());
  }

  function versPas(i) {
    ancre = i;
    glisser(cibleY(i), SNAP_MS);
  }

  /* ── LA RÈGLE EST DIRECTIONNELLE, PAS « LE PAS LE PLUS PROCHE » ──────────
     Ma première version accrochait au pas le plus proche. Elle a deux défauts
     rédhibitoires, tous deux vérifiés avant d'être corrigés :
     - **elle annule les petits gestes.** Posé au centre du pas 2, un cran de
       molette avance de 120 px sur un pas de 900 : le plus proche reste le pas 2,
       donc l'accrochage ramenait exactement d'où l'on venait. Le visiteur pousse
       et rien ne se passe. Or c'est précisément l'inverse de la référence, où un
       cran vaut un panneau entier ;
     - **elle piège.** Pour sortir du pas 1 par le haut il aurait fallu franchir
       plus d'un demi-pas en un seul geste, soit 450 px, quand un cran en fait 120.
     La règle retenue lit donc l'INTENTION : de combien s'est-on éloigné du pas où
     l'on était posé, et dans quel sens.
       |écart| < SNAP_SEUIL  -> on revient se poser où l'on était (geste hésitant) ;
       sinon                 -> on va au pas suivant DANS CE SENS, et l'écart arrondi
                                dit de combien de pas, donc un geste franc peut en
                                franchir deux sans qu'on lui résiste ;
       hors des bornes       -> on ne retient RIEN. C'est ce qui permet de sortir de
                                la séquence par le haut comme par le bas, et c'est le
                                seul garde-fou qui compte contre le piège.
     `ancre` est remis à null dès que la séquence quitte l'écran, si bien qu'on est
     recapturé proprement à la prochaine arrivée, une seule fois, comme le fait
     n'importe quelle section à accrochage. */
  /* Pas le plus proche et tête de lecture continue, mesurés À LA POSITION VISÉE
     et non à la position courante. `decal` est l'écart entre la cible du moteur de
     défilement et l'endroit où l'on est : décaler le centre du viewport de cette
     valeur revient exactement à s'y trouver déjà. */
  function teteAu(decal) {
    var vc = window.innerHeight / 2 + decal, best = 0, bd = Infinity, i, r;
    for (i = 0; i < steps.length; i++) {
      r = steps[i].getBoundingClientRect();
      var d = Math.abs(r.top + r.height / 2 - vc);
      if (d < bd) { bd = d; best = i; }
    }
    r = steps[best].getBoundingClientRect();
    return { i: best, pos: best + (vc - r.top) / (r.height || 1) };
  }

  function planifierAccrochage() {
    if (snapT !== null) clearTimeout(snapT);
    snapT = setTimeout(function () {
      snapT = null;
      if (snapAF !== null || pointeur) return;
      if (!onScreen) { ancre = null; return; }
      /* ON LIT LA CIBLE DU MOTEUR, PAS LA POSITION COURANTE, et c'est ce qui rend
         l'accrochage compatible avec l'entrée en douceur. Mesuré avant correction :
         la rampe de 260 ms fait qu'au bout des 110 ms de repos la page n'a parcouru
         qu'une trentaine des 240 px demandés. L'écart lu valait donc 0,06, sous le
         seuil d'engagement, et l'accrochage ramenait au pas d'où l'on venait : la
         séquence restait bloquée sur le pas 1, un cran sur deux annulé. La cible,
         elle, contient l'intention entière dès l'instant du cran. */
      var yc = (window.QBotDefil && window.QBotDefil.cible) ? window.QBotDefil.cible() : window.scrollY;
      var t = teteAu(yc - window.scrollY);
      var i = t.i;
      if (ancre === null) {
        /* CAPTURE À L'ARRIVÉE, ET SEULEMENT DANS L'INTERVALLE DES PAS. Sans cette
           borne, les deux bouts de la séquence piègent : au pas 4, un cran vers le
           bas libère (le pas 5 n'existe pas), mais le repos suivant recapture et
           ramène au centre du pas 4. Mesuré, ça oscillait indéfiniment entre 4326
           et 4446 px, un cran sur deux annulé. Même symptôme en haut. La borne est
           positionnelle et non un drapeau d'état : dès qu'on est passé au-delà du
           centre du premier ou du dernier pas, on est dehors et plus rien ne
           retient ; et si l'on revient à l'intérieur, on est recapturé, sans avoir
           eu besoin de quitter la section pour réarmer quoi que ce soit. */
        var yA = cibleY(0), yZ = cibleY(steps.length - 1);
        if (yc >= yA - 1 && yc <= yZ + 1) versPas(i);
        return;
      }
      var ecart = t.pos - (ancre + 0.5);
      if (Math.abs(ecart) < SNAP_SEUIL) { glisser(cibleY(ancre), SNAP_MS); return; }
      var pas = Math.max(1, Math.round(Math.abs(ecart)));
      var but = ancre + (ecart > 0 ? pas : -pas);
      if (but < 0 || but > steps.length - 1) { ancre = null; return; }   // on s'en va
      versPas(but);
    }, SNAP_REST);
  }

  function kick() {
    lastScrollAt = performance.now();
    if (!running) { running = true; requestAnimationFrame(function () { apply(false); }); }
  }

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
  /* L'accrochage s'annule au premier signe d'intention. `pointerdown` couvre la
     barre de défilement : sans lui, une pause au milieu d'un glissé de barre
     déclenchait l'accrochage et tirait la page sous le curseur. */
  /* LE REPOS SE COMPTE SUR L'ENTRÉE, PAS SUR LE DÉFILEMENT, et c'est ce qui évite
     un double délai. Compté sur le défilement, l'accrochage attendait la fin du
     glissement du module 22 (jusqu'à 530 ms) PUIS ses 110 ms de repos PUIS sa
     propre course : près d'une seconde entre le cran et l'arrivée. Compté sur
     l'entrée, il déplace la cible 110 ms après le dernier cran, donc pendant que
     le glissement est encore en cours : le mouvement reste un seul et même
     mouvement, qui change simplement de destination. */
  ['wheel', 'touchstart', 'keydown'].forEach(function (ev) {
    window.addEventListener(ev, function () { stopGlissade(); planifierAccrochage(); },
                            { passive: true });
  });
  window.addEventListener('pointerdown', function () { pointeur = true; stopGlissade(); }, { passive: true });
  ['pointerup', 'pointercancel'].forEach(function (ev) {
    window.addEventListener(ev, function () { pointeur = false; planifierAccrochage(); }, { passive: true });
  });
  /* LES PASTILLES PASSENT PAR LA MÊME GLISSADE, et ce n'est pas cosmétique : le
     client les donne comme référence de la sensation voulue. Laissées en ancres
     nues, elles atterrissaient sur `scroll-padding-top`, soit le HAUT du pas à
     88 px du bord, donc à 0,40 du pas et non à 0,50 : l'isolement de la carte n'y
     était pas complet, et l'accrochage repartait aussitôt corriger de 88 px, ce
     qui se lisait comme deux mouvements. Elles visent maintenant le même point que
     l'accrochage, avec la même courbe.
     Elles restent de VRAIES ancres dans le balisage : sans JavaScript, et en
     mouvement réduit (où ce bloc n'est jamais atteint), le clic fonctionne comme
     avant. Un clic avec une touche de modification ou au bouton du milieu est
     laissé au navigateur, pour ne pas casser l'ouverture dans un nouvel onglet. */
  dots.forEach(function (a, i) {
    a.addEventListener('click', function (e) {
      if (e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      e.preventDefault();
      versPas(i);
      if (window.history && history.pushState) history.pushState(null, '', a.getAttribute('href'));
    });
  });
  window.addEventListener('resize', function () { stopGlissade(); measureCards(); apply(true); });
  window.addEventListener('load', function () { measureCards(); apply(true); });
  /* Les polices changent la hauteur du texte : on remesure quand elles arrivent. */
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () { measureCards(); apply(true); });
  }
  measureCards();
  apply(true);
})();
