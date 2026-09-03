# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Static migration of the WordPress site at **https://q-bot.eu/** (source of truth).  
The visitor must perceive **zero difference** between the WordPress original and this static version.

## Architecture

Plain HTML/CSS/JS — no build step, no framework, no package manager.

```
index.html                  ← French homepage (default language)
a-propos.html
caracteristiques.html
contact.html
faq.html
modele-3d.html               ← Interactive 3D model viewer (Google <model-viewer>)
en/                         ← English versions (same structure)
assets/css/style.css        ← Single stylesheet, CSS custom properties design system
assets/js/main.js           ← Single script: nav, FAQ accordion, motion engine (scroll parallax + typed reveals), counters, back-to-top, 3D viewer controls
assets/img/                 ← Images downloaded from WordPress CDN
assets/models/               ← .glb 3D model(s) for modele-3d.html / en/3d-model.html
```

**3D viewer:** `modele-3d.html` / `en/3d-model.html` embed Google's `<model-viewer>` web component (loaded from jsDelivr CDN, no build step) to render `assets/models/qbot.glb` inline — no iframe, no new tab. The original Autodesk share link cannot be embedded (its viewer sends `X-Frame-Options: DENY`) and is a "protected" share with no download option, so it cannot be exported directly either.

`assets/models/qbot.glb` (~3.6 MB) is generated from `assets/3d/Q-LeapBox_v3.fbx` (a real FBX export of the v3 enclosure, ~5.5 MB, Kaydara FBX binary — **the authoritative source**, supersedes the earlier `assets/3d/Q-Leap Box_v3-08.obj`) plus a hand-built generic smartphone (6th part — not a replica of a specific Apple model, deliberately, to stay clear of IP concerns). The FBX ships as 5 already-separate named meshes (`Object.002`/`.003`/`.004`/`.005`/`.1`) — no vertex-welding or connected-components split needed (unlike the old OBJ, a single merged "3D Builder" export with duplicated per-face vertices and zero shared topology). Parsed with `assimp_py` (trimesh has no native FBX loader). Each FBX object was identified by face count: `Object.002`→tray (110122 f), `Object.003`→shell (83948 f), `Object.004`→small_part (3252 f), `Object.005`→**bracket** (1988 f, the USB-C connector nub — see phone docking below), `Object.1`→screen (12 f). Build pipeline: **no decimation** — the geometry is used at full FBX resolution, only `trimesh`'s `merge_vertices()` is applied per part (welds coincident vertices from the raw export and gives smooth normals; doesn't move a single vertex or drop any triangle) → recolor with brand-ish materials → bake a **single** glTF "Explode" animation clip with two independent time segments (see below) → export. If a new source export arrives, redo this pipeline (`scratchpad`-style script loading the FBX with `assimp_py`) rather than hand-authoring geometry.

There used to be a "standard" vs "HD" quality pair (an "HD" toggle button), decimated via custom voxel-clustering at two voxel sizes to keep the standard tier small. **Removed** — the decimation caused visible faceting/shading artifacts in standard quality (reported as "texture issues"), and the user asked for the FBX to be used untouched except for what the explode animation itself requires. There is now only one quality tier, faithful to the source file; no more `qbot-hd.glb`, no more HD button in the UI or `qualityBtn` logic in `main.js`.

**Phone docking point:** the user identified in Blender that the phone plugs onto **the summit (topmost vertex) of `Object.005`** — the small "bracket" part, a raised nub on the enclosure's front face, below-center and near the front, about a quarter of the way up the shell's height. The build script finds this vertex programmatically (`argmax` of Y among the bracket's raw vertices) rather than eyeballing a position, so it stays exact if the FBX is ever re-exported. The phone is built flat then put through two **proper** rotations (both determinant +1 — swapping two axes directly, e.g. `y'=z, z'=y` with `x'=x`, is a reflection and would mirror/invert normals, so every reorientation here is a real rotation matrix instead):
1. Stand it up vertical, matrix `[[-1,0,0],[0,0,1],[0,1,0]]` — camera-bump end goes to the **top**, screen faces the same +Z front the enclosure's own screen faces. (An earlier version used `[[1,0,0],[0,0,-1],[0,1,0]]`, which put the camera end at the bottom — wrong, fixed by flipping this sign choice rather than bolting on a separate 180° correction.)
2. Lean it back by the angle the shell's own front face slopes at, right above the bracket — the phone rests "en biais" against the enclosure like a stand, not bolt upright. The angle isn't hand-picked: `estimate_front_lean_deg()` in the build script samples the shell's outer surface (`z_max(y)` in a narrow X band centered on the bracket, ~40mm above its apex), fits a line, drops outliers from the screen-cutout edge, and returns the slope (~44° from vertical for the current FBX). Rotating about X by that angle is what "along the object" means here.

Both rotations are applied to the phone mesh once, then it's recentered so its own contact point (bottom-most vertex after rotation, `x` forced to 0 for symmetry) sits at the local origin — so the animation's translation keyframes can hold plain absolute undocked/docked world positions (same convention as the shell parts' explode offsets), and the "undocked" position is just the docked one offset along the *leaned* up-direction (`R_lean @ (0,1,0)`) rather than straight vertical, so it slides down along the same slope it rests against instead of dropping in from directly overhead.

**Animation clip design:** one clip named "Explode", `[0s, 0.98s]` drives the 4 non-shell Q-BOT parts (shell is the fixed anchor, never animated), `[1s, 2s]` drives the phone (undocked, floating above the bracket → docked, resting on its summit). Deliberately kept as **one clip** instead of two separate `animationName` values switched at runtime — three.js resets a node to its bind pose when its driving AnimationAction stops, so switching clips would have reset whichever control wasn't active. Nodes past their own track's last keyframe hold that value (glTF/three.js clamp semantics), which is what makes the two segments behave independently from a single shared `currentTime` — **but this bit twice**:
1. The shell parts originally had only 2 keyframes (assembled at 0, exploded at 1.0s); past that last keyframe they clamp-held the *exploded* value, so clicking the phone control (which plays on `[1,2]`) visibly exploded the shell. Fix: a 3rd keyframe re-assembles them right at `t=1.0`, and the slider's usable range was capped at `0.98` so it never reaches that handoff point.
2. The phone had no visibility control, so it just sat at its "undocked" spot permanently, plainly visible even with 0% explode. Fix: animate `scale` too (`[0,0,0] → [1,1,1]`) on the same `[1s, 2s]` range — before its first keyframe, the clamp holds scale at 0 (invisible) automatically, no JS required.

`viewer.duration` for this clip is `2s` — both the slider (via `EXPLODE_END = 0.98`, comfortably short of it) and the phone toggle (explicitly `PHONE_END - TIME_EPSILON`) avoid ever setting `currentTime` to exactly `2s`, or the internal AnimationMixer treats it as a loop boundary and jumps back to `0`.

**Viewer controls** (`assets/js/main.js`, module 12): rotate toggle, reset view (also restores `camera-target`), zoom in/out (adjusts `viewer.getCameraOrbit()` radius, clamped by `min-camera-orbit`/`max-camera-orbit` on the tag — wide and close framing both allowed), fullscreen, a day/night lighting toggle (swaps `exposure`/`shadow-intensity` between a day and night preset, plus a `.model-viewer-frame.is-night` class for a darker frame background), an exploded-view **slider** (0–100%, maps to `viewer.currentTime` in `[0, 1s]`, now a compact segment merged directly into the `.mv-controls` toolbar rather than a separate card), and a phone insert/remove toggle (tweens `currentTime` in `[1s, 2s]`). All the explode/phone controls live **inside** `.model-viewer-frame` (not after it) so they stay visible when that element goes fullscreen — anything outside it disappears on `requestFullscreen()`. `camera-target` is pinned explicitly to the enclosure's own center so the phone's off-to-the-side rest position doesn't skew the default auto-framing. Three critical fixes: (1) `viewer.pause()` **must** be called once the model has loaded — without it, model-viewer's internal animation clock keeps advancing on its own and overwrites any `currentTime` set from outside, which looked like "the model explodes for half a second then snaps back"; (2) never set `currentTime` to exactly the clip's total duration — the mixer treats that as a loop boundary and jumps back to 0, so both the slider (at 100%) and the phone toggle (when docked) stay `TIME_EPSILON` (1ms) short of the real endpoint; (3) the phone segment `[PHONE_START..PHONE_END]` always re-assembles the shell (via its snap-back keyframe at `t=1.0`), but the slider's own `<input>` doesn't know that — without an explicit reset it stayed showing e.g. 100% while the model was visibly back to assembled, forcing the visitor to nudge it manually to "unstick" the display. `phoneBtn`'s click handler now calls `setSliderDisplay(0)` up front so the slider always reflects reality after a phone toggle.

`assets/models/qbot.glb.data.js` re-encodes the `.glb` as a base64 `data:` URI: `window.QBOT_MODEL_DATA['qbot.glb'] = "data:model/gltf-binary;base64,..."`. main.js injects it dynamically (only when `location.protocol === 'file:'`) so the viewer works when someone double-clicks the HTML file instead of using a server — `fetch()` of local files is blocked by CORS, but a `<script src>` isn't. **Whenever `qbot.glb` is replaced, regenerate the sidecar too** (~4.8 MB base64 now that the model is full-resolution), or the file:// fallback will show a stale model:
```python
import base64
data = base64.b64encode(open('assets/models/qbot.glb', 'rb').read()).decode()
open('assets/models/qbot.glb.data.js', 'w').write(
    "window.QBOT_MODEL_DATA = window.QBOT_MODEL_DATA || {};\n"
    f'window.QBOT_MODEL_DATA["qbot.glb"] = "data:model/gltf-binary;base64,{data}";\n'
)
```

**Multilingual:** French at root (`/`), English under `/en/`. English pages reference assets with `../assets/`.

**Design tokens** (CSS custom properties in `:root`) — driven by `Documentations/Q-BOT BrandGuidelines.pdf`, see the brand section below:
- `--teal: #00CBBE` — brand primary; `--teal-dark: #00A79C`, `--teal-tint: #5CDCD3`, `--teal-text: #00857D`
- `--black: #000000` / `--dark: #000000` — brand secondary
- `--font: 'Roboto'`, `--font-heading: 'Roboto'` — Google Fonts
- `--container: 1180px`, `--section-py: 96px`

**Jamais de cadratin (`—`).** Règle du client, énoncée le 2026-08-19 : « ne mets jamais
de "—", aucun humain ne met de cadratin ». Selon le sens, on écrit deux-points, virgule,
parenthèses ou point. Passe faite le même jour : 121 occurrences reprises une par une dans
le contenu, les métadonnées, les `alt` et les `aria-label` des 23 pages, plus `llms.txt` et
`robots.txt`. **Le contrôle doit porter sur le caractère ET sur l'entité** : cinq cadratins
étaient écrits `&mdash;` dans les articles anglais, invisibles à une recherche du caractère
et pourtant bien affichés. Le seul test fiable est `document.body.innerText` dans le
navigateur, comme pour les emoji. Les commentaires de code (HTML, CSS, JS) et ce fichier en
contiennent encore : ils ne sont pas lus par le visiteur, mais toute NOUVELLE rédaction, y
compris les commentaires et les messages de commit, s'en passe.

**No emoji anywhere on the site — corporate icons only.** Client rule, not a preference:
every pictogram is an inline stroke SVG (24×24 viewBox, `fill="none"`, `stroke="currentColor"`),
the same language as the icons already in the markup. This covers badges, guarantee tiles, blog
banners, article meta and tool tags — and it covers what `admin/index.html` *publishes*, not just
the static pages. Watch for two disguises: HTML entities (`&#128272;` is a padlock, it slips past
a plain text search for emoji) and JS string fallbacks (`a.thumbnail || '📝'`). Tool tags carry no
icon at all now — the tool's name is the label.

**Single theme (dark).** There is no light mode and no theme toggle — `data-theme="dark"`
is written directly into the `<html>` tag of every page (and of the page template inside
`admin/index.html`). See the "night mode removed" section below.

**JS architecture** (main.js, independent IIFE modules in one file, numbered by comment banner):
0. *(removed — was the dark/light toggle)*
1. Nav sticky shadow + mobile toggle (hamburger → X via `aria-expanded` CSS selector) + smart hide on scroll down
2. Active nav link detection (pathname-based)
3. FAQ accordion with dynamic `scrollHeight` (no hardcoded max-height)
4. Scroll reveal: `.reveal` + a **variant** class added by JS → `.is-visible` via `IntersectionObserver`; double-RAF prevents FOUC; stagger via `--stagger-i` CSS custom property. See the motion section below.
5. Stats counter: `IntersectionObserver` + `requestAnimationFrame` on `[data-count]` elements
6. Back-to-top FAB (injected by JS)
7. Article UX: reading time, reading-progress bar, copy-code buttons
9. **Motion engine** — the single scroll listener/rAF loop for the whole site; writes CSS variables only
10. Pointer interactions: card 3D tilt + cursor spotlight, hero product-render tilt
11. Language switch preserves scroll position (ratio in `sessionStorage`)
12. 3D viewer controls
13. Magnetic CTA buttons

## Reference site

**https://q-bot.eu/** is always the source of truth.

Before any modification:
1. Compare the local page against the live WordPress page.
2. Identify visual and behavioural differences.
3. Document the gaps.
4. Fix the gaps — never the other way around.

**Never reword marketing copy.** Titles, subtitles, body text and button labels must match the original word for word.

**Mais le français n'est JAMAIS une traduction littérale de l'anglais.** Arbitré par le
client le 2026-08-19, sur le contenu de `Documentations/website` : « pour le FR la
traduction littérale ne rendra pas bien, sois expert en comm et marketing, garde
l'essence et la logique des phrases anglaises et retranscris-les en FR ». Exemple qui a
motivé la consigne : « Stop babysitting 2FA. Start shipping faster. » rendu d'abord par
« Plus personne pour surveiller la 2FA » — fidèle et plat. La formule retenue, du client,
est « La 2FA sans prise de tête. Livrez plus vite. » Donc : l'anglais reprend leurs textes
mot pour mot, le français rend l'intention avec ses propres moyens.

## Animation rules

- Prefer native CSS animations and transitions.
- Use GSAP only when CSS cannot achieve the required effect.
- Never remove an animation to simplify code.

Target behaviours to preserve:
- Hero: sequential `riseIn` entrance (label → title → desc → CTAs), `mediaIn` mask reveal on the product image, then scroll-driven depth (content lifts/fades via `--hero-p`, image lags via parallax) and cursor tilt. **No looping float** — see the motion section below.
- Page hero (sub-pages): `riseIn` entrance on label, h1, p.
- Scroll reveal: `.reveal` + variant → `.is-visible` with per-sibling stagger (`--stagger-i`, capped at 5).
- FAQ accordion: smooth `max-height` transition driven by `scrollHeight`.
- Mobile nav: hamburger animates to X; menu slides down (`menuSlideDown` keyframe).
- Timeline: teal progress line scrubbed by scroll (`--tl-p`).
- `prefers-reduced-motion` media query disables all animations **and** neutralises the whole motion layer (parallax, tilt, masks) while forcing every `.reveal` variant visible.

## Known placeholders to replace

| File | Placeholder | What to replace with |
|------|-------------|----------------------|
| `index.html`, `en/index.html`, newsletter `<form>` | Static `<form action="#">` | Sendinblue/Brevo embed code |

## SEO/GEO/UX audit (2026-07-09)

A full pass against the live site turned up several real bugs, not just stylistic gaps — fixed directly rather than just documented:

- **Sitewide broken logo**: `assets/img/logo.png` (128×150) was only ever a tiny cropped icon fragment (confirmed against the live site's own asset library) but was squished into a 120×40/110×36 wordmark slot in every page's nav + footer + JSON-LD `Organization.logo` — rendered as a barely-visible sliver. Replaced everywhere with `assets/img/logo-baseline.png` (300×128, byte-identical to the live site's actual footer logo asset), at the correct aspect ratio. Also fixed `.nav__logo img` CSS (`height: 80px` inside a `72px`-tall `.nav__inner` — logo was overflowing its own bar, just never noticed because it was invisible).
- **a-propos.html**: `logo-qleap.png`, `logo-qguard.png`, `products-lineup.jpg` were referenced but never existed (permanent broken-image icons) — downloaded the real assets from the live WordPress media library and wired them in, with `object-fit: contain` added to `.product-card__icon` (was hard-cropping/squishing wide logos into a 48×48 square). `qleap-office.jpg` turned out to reference an image that doesn't exist on the live page at all (that section is text-only there) — removed the image slot rather than substitute an unrelated stock photo. "Découvrir Q-Guard" (`href="#"`) → `https://q-guard.app/`; the Q-BOT product card's own CTA now points to the real `https://calendly.com/q-bot/30min` used live (was `contact.html`).
- **Wrong social links sitewide**: footer icons + every page's JSON-LD `sameAs` had invented/outdated handles (`facebook.com/qleap.lu`, `twitter.com/qleap_lu`) instead of the live site's real ones (`facebook.com/QLeapSa`, `twitter.com/qleap_sa`).
  **PÉRIMÉ, NE PAS S'EN SERVIR.** Le client a confirmé le 2026-08-25 que **LinkedIn est le seul
  compte actif** (`https://www.linkedin.com/company/q-leap`) et que le reste ne l'est plus. Ces
  deux comptes ne doivent donc PAS être remis dans `sameAs` ni dans le pied de page : un compte
  mort déclaré comme sien abîme la confiance dans tout le bloc de données structurées.
- **Footer legal links were `href="#"` on every page** ("Conditions de vente" / "Confidentialité", + the contact form's consent-checkbox privacy link). Verbatim legal text couldn't be reliably mirrored (fetch tooling declines to reproduce copyrighted policy pages verbatim), so these now link out to the real live pages (`https://q-bot.eu/conditions-vente/`, `/confidentialite/`, and the `/en/` equivalents) instead of shipping a paraphrased legal document of uncertain accuracy.
- **Favicon**: `favicon.png` was referenced but never existed (404 on every single page load). Sourced the real favicon from the live site and generated `favicon-32.png` / `favicon.png` (192×192) / `apple-touch-icon.png`; added a `theme-color` meta tag sitewide (missing before).
- **GEO**: `llms.txt` now lists the legal pages too. YouTube embed switched to `youtube-nocookie.com` (no tracking cookie before the visitor actually plays it — the placeholder `VIDEO_ID` itself is still pending, see below).
- Confirmed clean (no action needed): all hreflang/canonical pairs are consistent, no images 404, every `<img>` has `alt`, sitemap already includes per-URL hreflang alternates.

## Follow-up fixes (2026-07-09, same day)

- **FAQ accordion truncated answers**: `main.js` measured `answer.firstElementChild.scrollHeight` instead of the answer container's own `scrollHeight` — any FAQ answer with more than one paragraph/list had everything past the first `<p>` clipped by `max-height`. Fixed to measure the whole container.
- **a-propos.html product-card logos stretched + invisible in dark mode**: `.product-card__icon` forced `48×48`, squishing the wide (~4:1) logo lockups; fixed to `height:36px; width:auto; object-fit:contain`. Added `[data-theme="dark"] .product-card__icon { filter: brightness(0) invert(1); }` (they're black-on-transparent, invisible on a dark card without it).
- **Footer LinkedIn icon / "Made in Luxembourg" badge**: merged into a single `.footer__meta-row` flex row (previously two stacked block/inline-flex siblings) to remove any ambiguity around overlap.
- **`.spec-item` "card" variant (Interface & API section) stuck white in dark mode**: background was a literal inline `style="background:var(--white)"`, invisible to the dark-theme stylesheet — moved to a real `.spec-item--card` class with its own `[data-theme="dark"]` override. Audited the rest of the site for the same pattern (inline light backgrounds, or `color:var(--dark)` text inside a card that goes dark) — everything else already had proper dark-mode overrides.
- **`caracteristiques.html` vs `en/technical-specs.html`**: EN was missing the entire "Interface & API" section (Web interface / REST API / mobile notification) and "Zero data retention" section — added, translated from the real FR content (not present at all, not just under-translated).
- **`a-propos.html` vs `en/about.html`**: EN had a completely different, shorter structure — missing the whole Q-Leap/Q-Guard/Q-BOT products-grid section. The live EN page (`/en/about-us/`, not `/en/about/`) turns out to have its **own** distinct product copy (different descriptions/links per card, not a literal translation of the FR page) — used that real content rather than translating FR. Also found the live About page has a leftover WordPress-theme-demo "Meet the Professionals" team section with fake names/company ("Colabrio Media") that Q-Leap never replaced — deliberately not mirrored on either language (mirroring a client's own unfixed placeholder content would do more harm than the "zero difference" mandate is worth here).
- **Q-Digital**: live `/en/about-us/` lists a 4th product, "Q-Digital" (`digital.q-leap.eu`), that live `/about/` (FR) doesn't have at all. Initially ported to EN only, matching the live asymmetry — on reflection/per explicit direction, added to `a-propos.html` too (translated from the verified EN copy, no FR source exists for it) so both languages stay in sync even where the live site itself doesn't. No subtitle on the FR card (unlike EN's), matching the fact that FR's other 3 cards don't have one either.
- **`index.html` vs `en/index.html`**: EN was missing the "who is Q-BOT for" (use cases), video, timeline/evolution, and newsletter sections entirely, while carrying an extra "Compatible with all your testing tools" section absent from the live EN homepage — removed it, added the four missing sections (translated from FR, since the live EN homepage matches FR's shape here). Also found FR was itself missing the homepage FAQ preview section that both live homepages have — added it (reusing the exact wording already verified on `faq.html`).
- **`contact.html` / `en/contact.html`**: fixed the long-pending Calendly placeholder on both (and the third occurrence on `a-propos.html`'s Q-BOT card) to the real `https://calendly.com/q-bot/30min`. EN was also missing the closing "Would you like to know more?" CTA section present on FR.
- **`faq.html` vs `en/faq.html`**: EN had 10 of FR's 12 questions — added the missing "How do I acquire Q-BOT?" and "How is my personal information handled?" (content + FAQPage JSON-LD). Not ported the other way: live EN's FAQ page actually has 16 questions total (6 extra ones FR doesn't have — general test-automation background, warranty, a "how it works" walkthrough) — left as a known gap rather than add lower-confidence paraphrased content.
- Checked and already in parity, no changes needed: `commandez.html`/`en/order.html`, `blog.html`/`en/blog.html`, the 3 blog article pairs (matching h2 counts and comparable word counts), `modele-3d.html`/`en/3d-model.html`.
- **Product-card icons top-aligned instead of centered**: `.product-card` had `align-items: flex-start`; changed to `center` so the Q-Leap/Q-Digital/Q-Guard/Q-BOT logos sit vertically centered next to their text block instead of pinned to the top.
- **Footer text color (and every `.page-hero` subtitle sitewide) shifting with the light/dark toggle despite an always-dark background**: `.footer__desc` and the bare `<p>` inside `.page-hero` had no color of their own, so they fell through to the global `p { color: var(--gray) }` rule — which *does* change with the theme — instead of inheriting the fixed white-ish color their always-dark containers are designed around. Gave both an explicit `rgba(255,255,255,…)` color. Same root cause as the earlier `.spec-item--card` bug (an element skipping its container's intended fixed color and picking up a theme-variable one instead) — audited `.hero`, `.section--dark`, `.newsletter`, `.calendly-box` for the same pattern; all already had explicit colors on their text.

## 3D viewer: FBX at full resolution, no more decimation (2026-07-09)

The standard-quality model was showing visible faceting/shading artifacts ("texture and probably polygon issues"). Root cause: the voxel-clustering decimation step. Per explicit direction, removed decimation entirely — the FBX geometry is now used as-is (only `merge_vertices()`, which welds coincident vertices for smooth normals without moving anything or dropping a single triangle). This also removes the reason for a "standard vs HD" split: there's now **one** `assets/models/qbot.glb` (~3.6 MB, full FBX fidelity), no `qbot-hd.glb`, and no HD toggle button (`mv-quality-btn[data-mv-action="hd"]` removed from both HTML pages, `qualityBtn`/`HD_SRC` logic removed from `main.js`, the now-dead `.mv-quality-btn[data-loading]` CSS rule removed). The day/night lighting toggle still reuses the `.mv-quality-btn` class for its pill styling, so that CSS class itself stays. Regenerate `qbot.glb.data.js` (now ~4.8 MB base64) whenever `qbot.glb` is rebuilt.

## Brand guidelines — authoritative (2026-07-30)

`Documentations/Q-BOT BrandGuidelines.pdf` is the **authority on colour, typography and
logo usage** and overrides any design choice made previously in this repo. The PDF is
vector-only (no embedded bitmaps for the logo) — extract from it with `pymupdf`
(`pip install pymupdf`; there is no poppler/ImageMagick on this machine, and `qlmanage`
only renders page 1). What it specifies:

- **Primary colour `#00CBBE`** (C68 M0 Y35 K0 / R0 G203 B190) — and **nothing else but
  `#000000`** as secondary. There is no third brand colour.
- **Typography: Roboto only.** Titles = **Roboto Bold**, body = **Roboto Regular**;
  the specimen page shows Light / Regular / Italic / Bold.
- **Logo**: two lockups (`Q-BOT / POWERED BY Q-LEAP` and `Q-BOT / —BY Q-LEAP—`), each in a
  **Positive** (near-black ink) and **Negative** (white ink) version. **Both keep the teal
  accent tick on the Q** — it is the only coloured element of the mark.
- **Exclusion zone** (p. 3): measured off the PDF's dashed grid — a uniform margin of
  42.8 pt around a 69.3 pt-tall lockup, i.e. **0.618 × the lockup height on all four sides**.

Pass applied on 2026-07-30 to bring the site in line:

- **Palette de-navy-fied.** The site had been built on an invented navy identity
  (`--navy #1C244B`, `--dark #111F3D`, `--light #F0F4FF`, navy-tinted shadows, plus a stray
  purple radial glow `rgba(86,90,242,…)` and amber blog banners `#f59e0b`). Since the charter
  defines only teal + black, everything neutral was rebased on **the grey ramp of the charter
  document itself** (`#231F20 / #4C4B4C / #808285 / #BCBEC0 / #D1D3D4 / #E6E7E8 / #F9F9FA`) and
  all shadows/scrims on `rgba(0,0,0,…)`. `--navy` is gone; it had been serving as a
  *fixed* dark (never flipped by dark mode), a role `--dark` already plays — so all 12
  `var(--navy)` uses became `var(--dark)`. Dark-mode surfaces were retinted to neutral
  (`#0A0A0A` page, `#050505` nav, `#141414` cards, `#2B2B2B` borders).
  Also swept: the **old off-brand teal `#08B8B2`/`#069591`** still hardcoded in blog banner
  gradients and in `admin/index.html`.
- **Space Grotesk removed.** Headings were on Space Grotesk; the charter says Roboto Bold.
  `--font-heading` is now Roboto and the Google Fonts link in all 23 pages dropped the
  `&family=Space+Grotesk` segment. Heading tracking went `-0.025em` → `-0.01em` (the tight
  tracking was tuned for Space Grotesk; the charter shows plain Roboto).
  `font-weight: 600` and `800` were normalised to **700** — neither weight was ever loaded, so
  CSS font-matching already resolved both to 700; the declarations were simply lying, and
  Bold is the charter's heaviest documented weight. `500` is kept (it *is* loaded).
- **Negative logo asset added.** `.nav__logo img` and `.footer__logo img` both had
  `filter: brightness(0) invert(1)`, which flattens the lockup to solid white and **destroys
  the teal accent** — the one thing the charter's Negative version keeps. Generated
  `assets/img/logo-baseline-neg.png` (900×384) from the PDF's vector Negative lockup,
  padded to the **exact framing of `logo-baseline.png`** (lockup = 240/300 × 88/128 of the
  file) so it is a drop-in swap, with ink snapped to `#FFFFFF` and the tick to `#00CBBE`.
  All 23 pages' nav + footer `<img>` now point at it; the filters are gone (and so is the
  footer's `opacity: .9`, which desaturated the accent). **The JSON-LD `Organization.logo`
  deliberately still points at the positive `logo-baseline.png`** — that one is consumed on
  light/unknown backgrounds.
  `logo-baseline.png` itself was already exactly on-charter (pure `#000000` ink + `#00CBBE`
  tick) and is left byte-identical to the live site's asset. The favicon was already the
  charter's Q monogram. `theme-color` went `#1C244B` → `#000000` (the nav is black in both themes).
- **Exclusion zone enforced** via padding on `.nav__logo` / `.footer__logo`, expressed as
  `--logo-clear-y: 0.269` / `--logo-clear-x: 0.190` — the *complement* to the transparent margin
  already baked into the PNG (`0.618 × 88/128 − 20/128`, etc.). A negative left margin keeps the
  lockup optically flush with the container gutter, and the footer's `margin-bottom` has the
  padding subtracted, so neither the 72 px nav rhythm nor the footer spacing shifts.

### Bugs the pass surfaced (fixed)

A scripted WCAG contrast sweep over all 23 pages × light/dark (Playwright, walking each
text node's real composited background) caught pre-existing defects unrelated to colour taste:

- **`blog/automatiser-2fa-tests.html` + `en/blog/automate-2fa.html` were unreadable in light
  mode.** These two pages (and only these two — the other four article pages rely on the main
  stylesheet) carry a 298-line inline `<style>` block authored for a *dark* page — it even says
  `/* Breadcrumb override for dark bg */` — while `<body>` is white. `.article-header h1`,
  `.article-body h2/strong` were `color: var(--white)` and `.article-body` was
  `rgba(255,255,255,.85)`: **the entire article body was white-on-white**, contrast ratio 1.0.
  Repointed at the theme-aware tokens (`--black` / `--gray` / `--muted` / `--border`), which fixes
  light mode and keeps dark mode working.
- **`commandez.html` / `en/order.html`: 8 inline `color:var(--dark)` each** on body headings and
  `<strong>`. `--dark` is a *fixed* black, so in dark mode this was black on `#0A0A0A`. Being
  inline, no `[data-theme="dark"]` rule can reach them — switched to `var(--black)`, which flips.
- **~65 spots used full `#00CBBE` as text on white/light surfaces** (ratio 2.0:1). The stylesheet
  already documents this exact trap and ships `--teal-text: #00857D` (same hue, AA) for it —
  it just wasn't applied. Now it is, *except* on dark surfaces, where full teal is correct:
  4 inline cases (3 in `a-propos.html`, 1 in `en/about.html`) were identified by measuring
  their real background and deliberately left at full teal. Pictogram SVGs also keep full teal
  (they aren't text). Note `--teal-text` is redefined to `var(--teal)` in dark mode, so this
  change is a no-op there by design.

Residual audit findings (~860, all ratio ≥ 2.4) are the footer's translucent whites on black and
`--muted #808285` on white at 3.85:1 — both pre-existing, and `#808285` is itself a charter grey,
so they were left alone rather than restyled on a guess.

## Running locally

Open any `.html` file directly in a browser, or use any static server:

```
npx serve .
# or
python -m http.server 8080
```

No build step required.

## Motion pass — premium SaaS scroll layer (2026-07-30)

Brief: scroll animations in the spirit of `circle-website.webflow.io` (animated parallax),
and a rework of every image animation — the looping float was called out as unattractive —
toward an Apple/Linear feel while staying more dynamic than either.

### Architecture: JS writes variables, CSS decides how it looks

One module (`main.js` #9, "MOTION ENGINE") owns **the site's only scroll listener and rAF
loop**. It never writes computed styles, only CSS custom properties:

| Variable | Written on | Meaning |
|----------|-----------|---------|
| `--mx-y` | each `.mx-parallax` element | vertical parallax offset, px |
| `--orb-y` | `:root` | ambient hero glow offset |
| `--hero-p` | `.hero` | hero scroll-out progress, 0 → 1 |
| `--tl-p` | `.timeline` | scrubbed progress of the timeline line, 0 → 1 |
| `--mx-rx` / `--mx-ry` | hero `<img>` (module #10) | pointer tilt |

Amplitudes, breakpoint tuning and `prefers-reduced-motion` all live in CSS (section
"MOTION SYSTEM" at the end of `style.css`), so the *feel* can be retuned without touching
the script. Three things make the result read as premium rather than mechanical:

1. **LERP smoothing** (factor `0.14`): positions *chase* their target instead of tracking
   the scroll pixel-for-pixel, which reads as mass/inertia.
2. **Opposing layers**: a media frame drifts with a positive amplitude (lags behind the
   scroll → looks further away) while the image *inside* it gets a negative one. That
   counter-movement inside a still frame is what reads as depth. Sign convention is
   documented in both files.
3. **The loop shuts off at rest** — `kick()` restarts it on scroll, inertia keeps it a few
   frames, then it stops. No rAF runs when idle.

Two correctness details that are easy to regress:
- `getBoundingClientRect()` reflects the translate already applied, so the engine subtracts
  the current offset before computing the next target. Without that the position feeds back
  into itself.
- `update(true)` snaps without interpolation, and is called on init, on `resize`, **and on
  `load`** — `load` is when the browser restores scroll position (and when module #11
  re-applies it after a language switch); without the snap the layers visibly slide into
  place on arrival.

### Typed reveals

`main.js` #4 assigns a variant class from a table in the JS — **nothing was added to the 24
HTML pages**. Each element gets exactly one variant:

- `media` — mask reveal: `clip-path: inset(… round)` rising + the image settling from a
  slight overscale, plus a one-shot light sweep. Used for `.intro__image`,
  `.video__wrapper`, `.blog__featured-img`.
- `group` — the container itself doesn't move; its children cascade (label → title → text)
  via `--child-delay` on `nth-child`. Used for `.section-header` and intro text columns. A
  whole-block fade made all three land at once, which reads flat.
- `card` — rise + slight scale-up. Default for cards and list items.
- `plain` — rise + fade, no blur. Reserved for elements that already carry `.reveal` in the
  markup (see the bug below); a blur pass over a several-thousand-pixel `.article-body`
  costs a lot for an effect invisible at that scale.

`.specs__image` is deliberately **not** a media frame: it holds an image *and* a button, so
a clipped rounded frame would round the button's corners too. It keeps radius/shadow on the
`<img>` and moves as one block.

### What was removed or toned down

| Before | After | Why |
|--------|-------|-----|
| `@keyframes float` looping forever on the hero image | removed; replaced by scroll parallax + pointer tilt | the brief; motion now answers the visitor instead of bobbing on its own |
| `fadeInUp` / `fadeInRight` entrances | `riseIn` (rise + focus-in blur) / `mediaIn` (mask) | a mask reveal is the premium signature; both old keyframes are gone |
| `iconBounce` (scale 1.22 → 0.93) | `iconIn` (rise + settle) + a hover micro-interaction | the bounce read as a toy |
| Card tilt ±7°, transition 0.07 s | ±3.5°/±2.5°, transition 0.4 s | 0.07 s glued the card to the cursor; the longer transition gives it inertia |
| Magnetic buttons, factors 0.28/0.35 | 0.10/0.14, capped at 6 px | the button could move >20 px and slide out from under the cursor |
| Hero orbs: 12–16 s, scale 1.25, 40–50 px | 22–26 s, scale ~1.10, ~20 px | at the old scale it read as an animation, not as ambience |
| `.section-label` shimmer `infinite` | 2 iterations | a permanent shimmer on every label is template signature |

Also added: the timeline's teal progress line (`.timeline::after`, `scaleY(var(--tl-p))`) —
the only genuinely scroll-scrubbed effect on the site.

### Bugs the pass surfaced (all pre-existing, all fixed)

- **`blog/automatiser-2fa-tests.html` and `en/blog/automate-2fa.html` rendered their entire
  article invisible.** These pages carry `class="reveal"` **hardcoded in the HTML** on
  `.article-header`, `.article-meta`, `.article-body`, `.sidebar-card`, `.article-cta`,
  `.related-articles` — but none of those selectors were in `main.js`'s reveal list, so
  nothing ever added `.is-visible` and `.reveal { opacity: 0 }` held forever. Verified
  against the initial commit before fixing. Module #4 now collects pre-marked `.reveal`
  elements (before it stamps its own classes, or the query would return everything) and
  gives them the `plain` variant. **Any future `.reveal` written directly in markup is now
  picked up automatically.**
- **`.timeline`'s vertical lines painted over the dots**, striking through the step numbers.
  Root cause was subtle: the reveal left a `filter: blur(0)` on `.timeline-item`, and a
  non-`none` filter — even at zero — makes the element a stacking context, which trapped
  `.timeline-item__dot`'s `z-index: 1` inside it and dropped the whole item below the
  absolutely-positioned lines. Fixed both ends: revealed elements now end at `filter: none`
  (which also stops leaking one compositing layer per card, ~30 on some pages), and the
  timeline's stacking order is explicit (`item: z-index 1`, lines: `z-index 0`).
- **`.intro__image`'s shadow never rendered** — `overflow: hidden` on the container clipped
  a `box-shadow` declared on the child `<img>`. Radius and shadow now sit on the frame.
- **`prefers-reduced-motion` left below-the-fold `.reveal` content hidden** until the
  observer reached it, and the global override didn't reset `animation-delay`, so
  `backwards`-filled entrances held an empty screen for up to 0.4 s. Both fixed.

### Verifying a motion change

**LE NAVIGATEUR D'ANALYSE REND EN LOGICIEL EN MODE INVISIBLE.** Relevé le 2026-08-20 :
`chromium.launch(headless=True)` donne « ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device),
SwiftShader driver) », c'est-à-dire du rendu processeur ; `headless=False` donne « ANGLE
(Apple, ANGLE Metal Renderer: Apple M4) », le vrai GPU, celui du visiteur. **Tout défaut de
rendu 3D doit donc être cherché en mode fenêtré.** C'est ce qui a fait échouer trois tentatives
de reproduction du défaut entre les pas 3 et 4 : les captures logicielles ne montraient rien
d'anormal, et les mesures d'écart pixel non plus.

**Le balayage doit défiler en `behavior: 'instant'`.** `<html>` porte `scroll-behavior:
smooth` : un `scrollTo(0, y)` toutes les 110 ms ne tient aucune des positions échantillonnées
— chaque appel interrompt l'animation précédente, la page traîne derrière la boucle, puis le
`scrollTo` final la traverse à plus de 700 px par image et un élément peut n'intersecter à
aucune image. Mesuré sur l'accueil FR : 1 révélation manquée à chaque essai en `smooth`,
**0 sur 3 essais en `instant`**. Un faux positif coûteux — il ressemble exactement au vrai bug
« un bloc reste invisible » documenté plus bas, et il a déjà fait chercher un défaut inexistant.

`prefers-reduced-motion` and "did anything stay invisible" are the two things eyeballing
misses. A Playwright sweep over all 24 pages × (normal, reduced-motion) that scrolls to the
bottom and asserts no `.reveal` element (or `group` child) is left under `opacity: 0.9`,
plus no console error and no horizontal overflow, catches the whole class of regression —
that is how the article-body bug above was found. Worth re-running after any change here.

## Dark-only site + accurate product imagery (2026-08-10)

Four changes asked for in one pass. The first two are structural, the last two are content.

### 1. Night mode removed — the dark palette *is* the site

There is no longer a light theme, a toggle, or a system-preference follow. Instead:

- `data-theme="dark"` is hardcoded in the `<html>` tag of all 23 pages **and** in the article
  template string inside `admin/index.html` (pages it generates would otherwise render light).
- `assets/js/theme-init.js` is **deleted** and its `<script>` removed from every `<head>` —
  there is nothing to flash, so nothing to pre-empt.
- main.js module 0 (toggle injection + `matchMedia` listener) is gone; the banner comment that
  replaces it says why.
- `.nav__theme-btn` CSS is gone (including its `prefers-reduced-motion` line).
- The `[data-theme="dark"]` block in `style.css` is unchanged and is now simply *the* palette;
  its banner comment was rewritten to say so. The `:root` tokens above it remain as the base
  layer the dark block overrides — deliberately not merged, since keeping the two layers means
  the sitewide teal/grey/typography tokens still read as one charter-driven block.

**The 3D viewer's day/night button is a different thing and was kept** — it swaps
`exposure`/`shadow-intensity` on `<model-viewer>`, not the site theme. It now *starts* in night
(`aria-pressed="true"`, `.model-viewer-frame.is-night`, and the tag's own `exposure="0.5"` /
`shadow-intensity="1.3"` so the first paint is already right). Because those attributes now
carry the night preset, `DAY_EXPOSURE`/`DAY_SHADOW` in main.js can no longer be read back from
them and are hardcoded (1.1 / 1).

### 2. Homepage imagery regenerated from the real v3 model

`hero-device.png` / `device-3d.png` (the same washed-out CAD screenshot of an early proto) and
the gantry photos were still presenting the **first prototype** as the product. New renders are
produced from `assets/models/qbot.glb` itself — the authoritative v3 geometry — so the site and
the interactive 3D viewer now show the same object:

| Asset | Camera / state | Used by |
|-------|----------------|---------|
| `qbot-v3-hero.png` | `-32deg 68deg 105%`, phone docked | hero (FR+EN) + every page's `og:image`/`twitter:image`/JSON-LD `image` |
| `qbot-v3-solution.png` | `-28deg 70deg 92%`, no phone | homepage "La solution", evolution card 2 |
| `qbot-v3-luxtrust.png` | `-15deg 74deg 100%`, phone docked | homepage LuxTrust section, `commandez`/`order` |
| `qbot-v3-exploded.png` | `-25deg 65deg 118%`, `currentTime 0.97` | `caracteristiques`/`technical-specs` technical view |
| `qbot-v3-poster.png` | default orbit, night exposure | `<model-viewer poster>` (replaces `qbot-v3-render.png`, an Autodesk-Viewer screen grab complete with watermark and filename caption) |
| `qbot-proto-gen1.png` | — | `device-comparison.png` cropped/quantised, evolution card 1 |

**How to regenerate** (the interactive viewer is the renderer — no offline 3D pipeline):
serve the repo (`python -m http.server 8123`), drop a page at the repo root embedding
`<model-viewer src="/assets/models/qbot.glb" environment-image="neutral" animation-name="Explode" …>`,
then drive it from Playwright: wait for `load`, `mv.pause()`, set `cameraOrbit`/`exposure`/
`currentTime`, and `element.screenshot(omit_background=True)`. Two things are non-obvious:
`animation-name="Explode"` **must** be on the tag or `currentTime` does nothing (no clip is
selected, so the phone never docks and nothing explodes); and a custom equirectangular PNG as
`environment-image` renders the model pitch black — `neutral` is what works, and it also keeps
the stills consistent with the live viewer. Trim with `Image.getbbox()` + ~3 % padding.

The renders are transparent PNGs, which the old full-bleed photo frames were not built for:
- `.intro__image--product` (new modifier) gives the clipped frame its own surface — dark
  gradient + teal spotlight + hairline border + 30 px padding — so the detoured product sits on
  something instead of floating, and resets `--media-scale` to 1 (the 1.08 overscale exists to
  hide the edges of a photo during parallax; on a detoured render it just crops the product).
- The motion engine's internal counter-parallax is now scoped to
  `.intro__image:not(.intro__image--product) img` for the same reason.

`hero-device.png`, `device-3d.png`, `device-comparison.png` and `qbot-v3-render.png` are no
longer referenced anywhere; the files were left on disk. `device-photo.jpg` is still used on
`en/about.html`, where it is explicitly captioned as a prototype.

### 3. Timeline → product-evolution section

The dated "L'innovation continue… / Évolutions" timeline (Feb 2022 → Dec 2023, v1 / v2 /
"Mobile Pro") was inaccurate and is **replaced** on both homepages by `.evolution`: three cards
— *the first prototype* (gantry photo) → *Q-BOT today* (v3 render, links to the 3D model) →
*the roadmap is being written* (dashed frame + pulsing dots, links to contact). No dates are
claimed anywhere in the new copy, deliberately: the only two product states there is evidence
for are the proto photo and the current FBX.

The three cards hang off a horizontal rail whose teal portion stops on the *Q-BOT today* node.
`.evo-card` was added to the `card` reveal list.

**The rail's fill is fixed, not scrubbed (changed 2026-08-12).** It was first wired into the motion
engine's `PROGRESS` table (`--tl-p`, the timeline's mechanism) so it filled as the section scrolled.
Reported as wrong, and it was: that trait says where the *product* is, not where the *reading* is —
scrubbed, it grew and shrank under the visitor and no longer touched the node it exists to mark. It
is now `--evo-fill: 0.5` in CSS. `0.5` is not eyeballed: the rail runs from one outer column centre
to the other, so its midpoint *is* the middle column's centre. For a 4th step the value becomes
`(index of the current step) / (number of steps − 1)`. Side effect, an improvement: under
`prefers-reduced-motion` the teal portion now shows at all (the engine doesn't run there, so
`--tl-p` stayed 0 and the trait was simply absent). `PROGRESS` matched nothing on any page for a while
(and did so until the use-cases spine, 2026-08-20, gave it a real use again) — `.timeline` is used by none — but it is kept as the code path for a scrubbed progression.

**Stacking + entrance (2026-08-12).** The teal trait was painting *over* the nodes: both rail lines
are pseudo-elements of `.evolution__rail`, and `::after` is its **last** child, so it painted after
the cards. Made explicit — lines `z-index: 0`, `.evo-card` `z-index: 1` — the same fix the timeline
needed. The rail also has a **one-shot** entrance: the trait draws itself (`evoRailDraw`, 0.85s) and
the current node lands on it (`evoNodeLand`, delayed 0.62s so the bounce happens when the trait
arrives). No loop: the trait states a fact, it has no reason to keep moving. The trigger is the
`.is-visible` the observer already puts on the current card, read from the parent rail via `:has()`;
the animation is the **only** thing inside that `:has()` block, so a browser without `:has()` simply
keeps the static end state (full-length trait, node with its halo). It cannot replay on later scrolls
— module 4 `unobserve`s after adding `.is-visible`. Under `prefers-reduced-motion` the global
`animation-duration: 0.01ms` rule snaps both to their end state.

Two geometry details: the rail's ends sit at `calc((100% - 2 * var(--evo-gap)) / 6)` (the centre
of the outer columns, gaps included — a flat `16.666%` is off by half a gap), and card images are
`position: absolute; inset: 0; object-fit: contain` rather than `max-height: 88%`, because Chrome
does not reliably resolve a percentage `max-height` against a height that came from
`aspect-ratio`, and the images overflowed the bottom of their frame.

**Responsive — the trap this section fell into.** The card is `.evo-card__media` +
`.evo-card__body`, and the media frame is sized by `aspect-ratio`. That is fine in the 3-column
desktop grid (media ≈ 310 × 233), but the first version dropped straight to one full-width
column below 900 px: the media then followed the *card* width, so a 4/3 frame on an 852 px card
was 640 px tall — three enormous stacked blocks, a 2 470 px section and an empty dashed frame
the size of the viewport. Any Chrome window under ~900 px (a non-maximised window, a half-screen
split) showed it, which is exactly what got reported. Now:
- ≤ 900 px the card becomes a **row** — media `flex: 0 0 min(34%, 210px)`, square, text beside it
  (section back to ~1 070 px);
- ≤ 520 px it stacks again with the media on a **fixed 190 px height** (`aspect-ratio: auto`) —
  a full-width ratio would just reintroduce a needlessly tall frame, and the visuals are cut-out
  PNGs so they stay contained either way.

Check any change to this section at 375 / 520 / 601 / 768 / 900 / 901 / 1280 px, not just at
desktop width — the two breakpoints are where it goes wrong.

### 4. Newsletter band condensed (FR + EN)

Was ~450 px tall for one email field: a full-sentence lead, then three stacked paragraphs of
consent and Sendinblue boilerplate, all as inline styles. Now ~325 px — one-line lead, the
consent checkbox on a single line (with a real link to the privacy policy, `/confidentialite/`
for FR and `/en/privacy/` for EN, matching the footers), and one fine-print line that keeps the
substance (one-click unsubscribe + Sendinblue as processor). The inline styles moved into
`.newsletter__consent` / `.newsletter__legal`, and the section padding went 72 px → 52 px.
Note `.newsletter .newsletter__legal` is doubled up on purpose: `.newsletter p` sets both colour
and `margin-bottom` and would otherwise win on specificity.


## Media pass — client-supplied renders + product film (2026-08-10)

A folder of raw assets (three 1672×941 renders + `QBHome.mp4`) was handed over to be sorted and
placed. Masters are archived under `Documentations/assets-sources/` (renamed to stable ASCII
names); the delivered folder is gone.

**All three renders were blue.** Measured hue was a very tight ≈ 215° (p10 213, p90 217) while
the charter allows only teal `#00CBBE` (≈ 174°) and black. A single global hue rotation of −41°
lands them exactly on brand, and because the hue distribution is that narrow — the product itself
is neutral black/grey — nothing else in the image shifts. Blacks were then re-graded to a true
`#000` floor: the renders' background bottomed out around luminance 12-15, which read as a
visibly lighter rectangle sitting on the hero's pure black.

| Source | Becomes | Where |
|--------|---------|-------|
| `…14_05_23` (product right, empty left) | `qbot-hero.webp` — cropped to the product, edges feathered to alpha | hero, FR + EN |
| `…14_05_23` | `qbot-og.jpg` — 1200×630 | `og:image`/`twitter:image`/JSON-LD `image` on all 23 pages |
| `…14_02_59` (cinematic close-up) | `qbot-solution.jpg` | homepage "La solution" (plain `.intro__image`, full-bleed — not the `--product` frame) |
| `…14_05_26` (podium, UI cards) | `qbot-video-poster.jpg` | `poster` of the homepage video |

The hero is **WebP with alpha**: the same feathered crop as PNG was 766 KB, as WebP q88 it is
45 KB for a mean pixel difference of 1.05. Alpha is required (the hero background is black *plus*
two animated teal orbs, so a baked-in matte would show).

`og:image` previously pointed at `qbot-v3-hero.png` — a portrait transparent PNG, which social
previews crop badly and composite on an unpredictable colour. It is now a proper 1200×630 JPEG.

### The video

`QBHome.mp4` was 45.8 s / 1920×1080 — but the picture stops at **8.72 s** and the remaining 37 s
are pure black, and its audio track is **entirely silent** (both verified by sampling decoded
pixels and by `decodeAudioData` RMS in Chrome, not by screenshots — element screenshots of a
playing video go black under Chrome's video overlay and will lie to you). So it is really a
silent 8.7 s product film with a broken export tail.

Trimmed and re-encoded with macOS's `/usr/bin/avconvert` (`--preset Preset1280x720 --duration
8.72`) → `assets/video/qbot-home.mp4`, 2.9 MB. Note the toolchain: Playwright's bundled ffmpeg is
a stripped build with no H.264 decoder and no MP4 demuxer, so it is useless here; `avconvert` is
the one encoder present on this machine.

It replaced the long-standing `VIDEO_ID` YouTube placeholder in the homepage video section — then
moved again, see below.

**If a clean export arrives**, drop it at the same path; nothing else needs touching.

### Copy removed

"Découvrez d'autres vidéos avec Postman et l'interface Web !" / "Discover more videos with
Postman and the Web interface!" — flagged by the client as meaningless: it promised other videos
that do not exist and linked to the contact page. Removed from both homepages rather than
reworded. This is the one case where the "never reword marketing copy" rule yields: the site
owner explicitly called the line wrong.


## The film moved into the hero, autoplaying (2026-08-10)

Asked for: the film at the very top of the page, playing on its own.

**Full-bleed hero background was tried first and rejected.** The film is a *black* enclosure on a
*light grey* background, and the page is black. Two dead ends worth recording so nobody retries them:
- Keying the background out (SVG `feColorMatrix` alpha-from-luma, a real matte, blend modes) is
  pointless here — the subject is black, so removing the light background leaves black on black.
  The light backdrop is the only thing making the product readable.
- Dimming it behind the text (video at `opacity: .38` + a black scrim) does keep relative contrast,
  but most of the film's 8.7 s is *extreme close-ups*: dimmed, it reads as an abstract grey wedge,
  not as a product. Screenshotted and discarded.

So the film is the hero's **visual column** instead of its background: `.hero__film`, a 16/9 rounded
frame with a teal hairline, a soft teal glow and an inset vignette that melts its light edges into
the black page. It replaces `.hero__image` on both homepages (`qbot-hero.webp` is now unused but kept
on disk). `autoplay muted loop playsinline` — muted is what makes autoplay legal, and the film is
silent anyway.

**The frame does not move.** It was first wired into the motion layer like every other media frame —
parallax (amp 34) plus the hero pointer tilt — and that was wrong: on content that is already moving,
a drifting/tilting frame does not read as depth, it reads as an unstable frame. Reported as "ça fait
bizarre que le cadre bouge" and removed: `.hero__film` is out of the parallax table, and the pointer
tilt is back to `.hero__image` only. The only motion it keeps is the one-shot `mediaIn` mask entrance.
Keep it that way — the impulse to make it consistent with the other frames is the bug.

New module 14 turns autoplay off — pauses, unloops, exposes controls — for `prefers-reduced-motion`
**and** for `navigator.connection.saveData`: the file is ~2.9 MB and `autoplay` fetches it
immediately. (`avconvert` has no bitrate control; dropping to 960×540 only saved 22 %, not worth the
resolution, so the weight stands until a lighter export arrives.)

**Consequence on the section below:** it held the same film, so the player and its video-specific
header ("Q-Bot en moins d'une minute !" / "Q-Bot in less than a minute!") were removed rather than
show the same 8.7 s twice. What remains is the "100 % conçu et développé au Luxembourg" block, whose
`.section-label` was promoted to an `<h2>` (same class, no visual change) so the section's
`aria-labelledby` still points at a real heading. `.video__wrapper` / `.video__player` CSS is now
unused by any page — left in place, it is the slot for a future real demo video.


## Refonte des visuels produit — matériaux, texture, éclairage (2026-08-11)

Demande : que l'image de la section LuxTrust atteigne le niveau de celle de « La solution »
(un des renders IA retouchés), et que la carte « Génération actuelle » reste détourée mais
« un peu plus texturée ». Les deux visuels étaient des rendus gris plats du GLB.

Tout est régénéré **depuis `assets/models/qbot.glb`**, donc depuis la géométrie authentique —
pas d'image générée de l'extérieur. La chaîne est versionnée dans **`tools/render/`** (voir son
README, qui liste les pièges) ; elle produit :

- `qbot-luxtrust.jpg` — scène complète : fond nuit, halo teal, arcs de sol, reflet, bloom.
  Remplace le rendu gris dans la section LuxTrust (FR+EN) et dans `commandez`/`order`.
- `qbot-gen-actuelle.webp` — le même boîtier détouré, sur transparence, pour la carte évolution.

Ce qui a changé sur le modèle de rendu (`patchglb.py`, copie hors-ligne, le GLB du site n'est
pas touché) :

- **Matériaux** : corps quasi noir légèrement métallisé (0.064 / metal 0.30 / rough 0.42) au lieu
  du gris moyen ; le hublot d'écran du boîtier passe de blanc à du verre sombre.
- **Micro-texture** : normal map + variation de rugosité tuilables. Le maillage n'ayant aucune UV,
  elles sont projetées — en **triplanaire par face**, après avoir constaté qu'une projection
  planaire par pièce étire la texture sur les faces obliques et la transforme en stries franches.
- **Écran du smartphone** : ses UV d'origine sont dégénérées (4 texels de palette, un par face),
  donc rien n'y était peignable. Les faces de la dalle sont isolées dans une primitive dédiée
  avec de vraies UV et un matériau émissif, qui affiche une validation d'authentification.
  Volontairement iconographique — anneau, coche, barres muettes : **ce n'est pas une reproduction
  de l'interface LuxTrust**, et il ne faut pas la transformer en une.
- **Éclairage** : environnement équirectangulaire maison (key light large + rim teal en
  contre-jour + rim froid) au lieu du preset `neutral`. L'orientation n'est pas devinée : sonde à
  quatre couleurs → `u = 0.75 − θ/360`, donc le contre-jour se place à `u_caméra + 0.5`.

Le viewer interactif de `modele-3d.html` continue d'utiliser `assets/models/qbot.glb` inchangé.
`qbot-v3-luxtrust.png` et `qbot-v3-solution.png` ne sont plus référencés (fichiers laissés sur
le disque).


## Passe emoji + visuels de `caracteristiques` (2026-08-11)

- **Q-Digital retiré** de `a-propos.html` et `en/about.html`. Il avait été ajouté côté FR pour
  aligner les deux langues ; il part des deux, pour la même raison.
- **Zéro emoji** (voir la règle en tête de fichier). 24 fichiers touchés : drapeau du badge
  footer et du `badge-lux` → pictogramme « lieu » ; icônes des `guarantee-item` → SVG au trait en
  teal ; bannières de blog → SVG blanc translucide ; méta d'article (date / durée / auteur) → SVG
  alignés sur le texte ; `tool-tag` → plus d'icône du tout. Côté back-office : les vignettes
  d'amorçage passent à vide (repli sur une icône), et l'habillage propre à l'outil est nettoyé.
  Un emoji restait caché en **entité HTML** (`&#128272;`) dans `en/blog/selenium-2fa-guide.html` —
  invisible à une recherche de caractères, trouvé en testant `document.body.innerText` dans le
  navigateur. C'est ce contrôle-là qu'il faut refaire, pas un grep.
- **Vue éclatée remplacée** : `caracteristiques.html` / `en/technical-specs.html` montrent
  désormais `qbot-specs.jpg`, un plan produit dans le même style que la homepage.
- **« Interface & API »** montrait `interface-screenshot.png`, une coupe CAO des entrailles du
  proto — aucun rapport avec une interface. Remplacée par `qbot-interface.jpg` (+ `-en`), une
  **maquette** construite en HTML/CSS puis capturée (`tools/render/interface-mockup.html`).
  **Ce n'est pas une capture du produit** : c'est un schéma, et son `alt` le dit au visiteur
  (« Schéma de l'interface web Q-Bot »), donc rien n'est présenté pour ce qu'il n'est pas.
  **ARBITRÉ PAR LE CLIENT LE 2026-08-27 : la maquette reste, ce n'est plus une dette.** Motif
  donné : « pour l'instant c'est du full préprod côté Q-Bot donc c'est moche ». Autrement dit il
  n'existe aucune capture présentable, et il n'y en aura pas avant que l'interface soit finie —
  ne pas le remonter à chaque passe comme un correctif en attente. Dessinée à la taille réelle
  d'affichage (600 px) puis capturée en DPR 2 — une première
  version dessinée en 1080 px se retrouvait réduite de moitié dans sa colonne, texte à 6 px.


## Audit UX/UI + SEO/GEO (2026-08-11)

Passe mesurée, pas à l'œil : crawl instrumenté des 23 pages (Playwright/Chrome) — métadonnées,
structure de titres, hreflang, données structurées, contraste WCAG calculé sur le fond réellement
composité, cibles tactiles à 390 px, focus clavier, liens internes, poids transféré.

### Corrigé

- **Contraste : 16 défauts, le pire à 1,51:1 → plus aucun.** Le fond était la cause principale :
  **le teal de marque est une couleur claire**, du blanc dessus plafonne à 1,8:1. Toute la bande
  newsletter (titre, texte, consentement, mention légale, lien) et le prix `900€` de la page
  commande étaient en blanc sur teal. C'est le **noir de charte** qui va sur le teal (≈ 11:1) —
  règle notée dans la feuille de style. Le reste : blancs translucides du pied de page (badge 2,46,
  copyright 3,01, adresse et titres de colonnes 3,66) et le token `--muted` du thème sombre
  (`#6D6E71`, 3,3:1) remonté à `#949699`.
- **hreflang invalide sur 14 pages.** Chacune déclarait l'autre langue + `x-default`, **jamais
  elle-même**. Un cluster hreflang sans auto-référence est ignoré en bloc par Google — les paires
  FR/EN ne comptaient donc pas. Ajout du `hreflang` auto-référent partout.
- **Deux `<h1>` identiques et visibles** sur les 4 pages d'article longues : une fois dans le
  page-hero, une fois 500 px plus bas dans l'en-tête d'article. Le doublon est supprimé, l'`id`
  déplacé sur le titre conservé pour ne pas casser `aria-labelledby` (vérifié : plus aucune
  référence aria orpheline sur le site).
- **7 titres > 62 c et 6 descriptions > 158 c** (tronqués en SERP) raccourcis sans reformuler le
  message — on coupe le suffixe de marque ou la dernière proposition.
- **`og:image:width` / `height` / `alt`** ajoutés sur 22 pages (aperçus sociaux rendus sans
  attendre le téléchargement de l'image).
- **Sauts de niveau de titre** `h2 → h4` (colonnes de pied de page, blocs de contact) → `h3`.
- **Poids** : `device-photo.jpg` faisait 3,3 Mo en 3024 px pour 573 px affichés, `products-lineup.jpg`
  822 Ko en 1920 px pour 594 px, et le logo était servi en 900 px pour 84-89 px, deux fois par page.
  Résultat sur `en/about.html` : **4359 Ko → 216 Ko**.
- **Cibles tactiles** (WCAG 2.2 – 2.5.8, mesurées à 390 px) : hamburger 32×24 → 44×44, case de
  consentement 13×13 → 18×18 avec un label cliquable plus haut, sélecteur de langue élargi.
  Faux positif écarté : `.back-to-top` mesurait 35×35 à cause du `scale(0.8)` de son état masqué.
- `sitemap.xml` : `lastmod` figé au 2026-07-09 → date réelle du dernier commit par fichier.
- `llms.txt` : index de blog ajoutés + date de mise à jour.

### Vérifié sain

Focus clavier visible partout (contour teal 2 px), lien d'évitement fonctionnel, aucun lien interne
cassé (23 URL), aucun lien sans intitulé, tous les `alt` présents, `Organization` + `BreadcrumbList`
+ `Product`/`BlogPosting`/`FAQPage` valides, `robots.txt` couvrant les agents IA (GEO).

### Laissé ouvert — arbitré par le client le 2026-08-11

1. **Formulaires en `action="#"` — À RAPPELER AVANT LA MISE EN LIGNE.** `contact.html`,
   `en/contact.html` et les deux formulaires newsletter des homepages n'envoient rien, sans que le
   visiteur s'en aperçoive. Le client reporte volontairement le sujet et demande **qu'on le lui
   rappelle au moment de finaliser le site**. Donc : dès qu'il est question de livrer, publier ou
   faire une dernière relecture, remonter le point sans attendre qu'on le demande — il faut un
   endpoint (Brevo, Formspree ou équivalent), le client fournira l'embed. Tant que le site n'est
   pas public le coût est nul ; le jour de la mise en ligne, chaque envoi est un lead perdu.
2. **Homepage à ~2,9 Mo** (film en lecture automatique) : **accepté tel quel** par le client.
   Ne pas y revenir sans nouvelle demande.
3. Le visuel « Interface & API » est une **maquette**, pas une capture du produit.
   **PÉRIMÉ COMME POINT OUVERT, ARBITRÉ LE 2026-08-27** : l'interface réelle est en
   préproduction et n'est pas présentable, la maquette reste. Voir la note du 2026-08-11.
4. **Tarif : 850 € / mois HT** (arbitré par le client le 2026-08-19, remplace les 900 € TTC
   affichés jusque-là). Publié partout : prix visible et « TTC » → « HT » sur
   `commandez`/`order`, titre + les 3 métadonnées sociales de ces deux pages, la réponse
   « combien coûte Q-Bot » de la FAQ (texte visible **et** sa copie dans le JSON-LD `FAQPage`,
   FR + EN), `llms.txt` (2 lignes), le gabarit d'article de `admin/index.html`, et le
   `Product.offers` des 8 pages qui en portent un — où `priceSpecification` déclare désormais
   `"valueAddedTaxIncluded": false`, c'est la propriété schema.org qui dit « HT ».
   **Le live WordPress affiche encore 900 €** : cet écart est volontaire, ne pas le « corriger »
   en alignant sur le live. Un prix qui diffère entre le JSON-LD et la page étant pire que pas
   de prix, tout contrôle doit vérifier qu'aucun `900` de tarif ne subsiste
   (`grep -rn '€\s*900\|900\s*€\|900 EUR'`).


## Le mécanisme : ADB sur un vrai Android (2026-08-19)

`Documentations/website` (quatre pages fournies par le client, plus récentes que le live)
décrit le produit autrement que ne le faisait ce site, et **c'est ce contenu qui fait foi** :

- Q-Bot **pilote un vrai téléphone Android relié en USB, par ADB**. Chaque appui arrive sur
  l'écran physique, dans la véritable application 2FA. Ni simulateur, ni bouchon.
- Les scénarios se construisent **visuellement** : une capture de l'écran 2FA, des points
  d'appui numérotés, des temps d'attente. Aucun script.
- Deux déclenchements : l'**API REST** (`GET /scenarios/:id/execute`) ou l'**app compagnon**
  installée sur le téléphone, qui part seule dès qu'une notification 2FA arrive.
- Deux autres endpoints : `GET /get-luxtrust-otp` et `POST /display-image` (un QR code
  affiché sur le petit écran du boîtier, que le téléphone scanne).
- Confidentialité : les scénarios et leurs captures **restent sur le boîtier**, aucun envoi
  vers un cloud, aucune connexion internet nécessaire pendant les tests.

**Ce qui a donc été SUPPRIMÉ du site le 2026-08-19** (lot 1, 63 remplacements sur 9
fichiers) : l'actionneur qui appuie sur un bouton, la caméra HD, les leds qui éclairent
l'écran, la vision par ordinateur, le programme de reconnaissance, et les photos supprimées
après traitement. Contrôlé après coup : **0 occurrence** de ce récit sur les 23 pages.
Ne pas le réintroduire depuis le live WordPress, qui le porte encore.

Deux conséquences non évidentes :

- **la réponse « Comment Q-Bot fonctionne-t-il ? » de la FAQ existe en double**, en texte
  visible et dans le JSON-LD `FAQPage`. Les deux copies partagent les mêmes fragments de
  phrase : les remplacer par fragment corrige les deux d'un coup, et c'est le seul moyen de
  ne pas les désynchroniser ;
- **la carte du pas 2 de la séquence 3D s'allonge** (308 → 331 px à 375 px de large). Sans
  effet : `--sc-card-zone` est mesurée sur la plus haute des quatre cartes, qui est celle du
  pas 4 (344 px). Vérifié avant/après, zone et scène identiques au pixel.

**Le token PHYSIQUE ne fait plus partie de la compatibilité** (lot 2, même jour, arbitré par
le client). ADB pilote une application Android : un boîtier matériel à écran n'entre pas dans
ce modèle. Sont donc partis : la pastille « LuxTrust Token (physique) », la question de la FAQ
anglaise « What type of token does Q-Bot work with? » (devenue « Which 2FA apps does Q-Bot
work with? »), le cadre « retrieving the value of authentication tokens », la ligne « the
efficiency of the token's value recognition exceeds 99% » (il n'y a plus rien à reconnaître) et
la promesse « in a future version, Q-Bot will also support dual authentication on all types of
smartphones », que le présent a rattrapée. La liste devient : LuxTrust Mobile, Microsoft
Authenticator, Google Authenticator, **itsme**, toute app 2FA Android. Contrôlé : 0
revendication de token physique hors blog.

**Les six articles de blog gardent le vocabulaire du token, et c'est une question ouverte.**
Leur sujet même est « automatiser l'utilisation des tokens » : c'est dans leur titre, leur URL,
leur `headline` JSON-LD et leurs fils de navigation. L'un d'eux annonce même, en 2022, que
« prochainement, Q-Bot saura prendre en charge la totalité des tokens physiques du marché ainsi
que les smartcard ». Reprendre tout cela n'est plus une correction de compatibilité mais la
réécriture de six publications datées. À arbitrer avec le client avant d'y toucher.

## L'API sur la page Caractéristiques (2026-08-19, lot 3)

Les trois points d'entrée du produit sont désormais publiés, dans une section propre placée
juste après l'acte épinglé « Interface & API » : `GET /scenarios/:id/execute`,
`GET /get-luxtrust-otp`, `POST /display-image`. Avec un exemple d'appel Selenium/Python, les
quatre faits qui comptent (auto-hébergé, aucune clé, compatible HTTP, moins d'une heure
d'intégration) et le tableau d'appel par outil, sept lignes, reprises de leur page Use Cases.

Trois choses à savoir avant d'y toucher :

- **l'acte épinglé n'accepte QUE trois cartes.** `data-mode="0|1|2"`, trois zones de
  projecteur en CSS et `['.pin-modes', '--pin-p', 3]` dans le moteur : ajouter une quatrième
  carte demande de toucher les trois. C'est pourquoi l'API a sa propre section au lieu d'une
  carte de plus ;
- **le libellé d'une ligne de fiche est en capitales espacées**, ce qui est illisible pour une
  URL (`GET /SCENARIOS/:ID/EXECUTE`). La variante `.spec-item--api` le remet en minuscules et
  en chasse fixe ;
- **le bouton « Copier » du module 7 n'avait jamais rien à copier.** Le module s'arrête net
  s'il n'y a pas de `.article-body` sur la page, et aucun des six articles ne contient de
  bloc de code : la fonction était morte depuis toujours, sans erreur ni trace. Elle est
  sortie dans un module 7 bis qui vise `.article-body pre, .code-block pre`, et la section
  API est son premier usage réel.

Au passage, les `role="list"` de `.specs__list` n'avaient aucun `role="listitem"` : 22 lignes
sur quatre pages en ont reçu un. Même défaut que la liste d'outils de la page commande,
corrigé au lot J.

## L'app compagnon (2026-08-19, lot 4)

Le produit a **deux chemins de déclenchement**, et le site n'en connaissait qu'un. L'app
compagnon s'installe sur le téléphone sous test, surveille les notifications des applications
2FA et déclenche le scénario correspondant dès qu'une arrive, sans aucun appel depuis la
chaîne de tests. Les deux chemins coexistent dans le même environnement.

Publié dans une section « Déclenchement » sur `caracteristiques` / `technical-specs`, deux
cartes côte à côte : l'appel HTTP d'un côté, l'app de l'autre.

**Et la troisième carte de l'acte épinglé disait le contraire de la vérité** : « Notification
mobile : déclenchez MANUELLEMENT via notification mobile pour les cas de test
semi-automatisés. » Le déclenchement est automatique, c'est tout son intérêt. Elle est devenue
« App compagnon ». La zone de projecteur n°2 de la maquette montre justement la ligne
« notification envoyée au téléphone », donc le pointage reste juste.

La FAQ française décrivait déjà ce déclenchement automatique (question 12) : seule sa
terminologie a été alignée sur « app compagnon », dans le texte visible et dans le JSON-LD.
La FAQ anglaise n'a pas l'équivalent de cette question, asymétrie antérieure et non traitée
ici.

## Éditeur, matériel et cas d'usage (2026-08-19, lots 5 à 7)

Fin de la reprise du contenu de `Documentations/website`. Ce qui a été publié :

- **l'éditeur de scénarios** (`caracteristiques` / `technical-specs`) : capture de l'écran en
  fond d'étape, points d'appui numérotés posés au clic, temps d'attente à la milliseconde,
  étapes réordonnables, scénarios versionnés dans le boîtier, captures stockées localement.
  Section **sans visuel à dessein** : la maquette de l'éditeur illustre déjà la section
  suivante, qui zoome dedans. La montrer deux fois de suite ne dirait rien de plus ;
- **la pile matérielle**, en lignes de fiche plutôt qu'en section : `Système` passe de
  « Linux (Raspberry Pi OS) » à **Raspberry Pi OS Lite**, et quatre lignes arrivent
  (déploiement en conteneurs Docker par une seule commande Docker Compose, stockage SQLite
  sur le boîtier, **écran intégré**, aucune connexion internet pendant les tests) ;
- **l'écran du boîtier revient**, y compris sur les deux pages 3D. Il avait été retiré du
  site entier le 2026-08-12 parce qu'il n'était pas visible sur le live (cf. la section sur
  les blocs masqués). Le contenu fourni le confirme noir sur blanc, avec son usage : afficher
  un QR code que le téléphone vient scanner. **Dire « petit écran intégré » et pas « OLED »** :
  la technologie n'est confirmée nulle part ;
- **les cinq cas d'usage** sur `commandez` / `order` et non sur la page technique : c'est la
  page où l'on décide d'acheter. Chacun en deux volets, le blocage puis ce que Q-Bot en fait.

Détail de forme : les lignes de fiche de `en/technical-specs.html` sont écrites **sur une
seule ligne de source**, contrairement à celles de `caracteristiques.html`. Un motif de
remplacement multi-lignes échoue silencieusement sur l'une des deux pages.

## Proposition M : les cas d'usage arrivent, et leur solution se trace (2026-08-19)

Audit demandé après la reprise de contenu : les blocs ajoutés n'avaient pour la plupart
aucune entrée. Mesuré sur les pages enrichies — 5 cas d'usage sans rien, 10 des 15 faits à
coche sans rien, le bloc de code sans rien, la note d'article sans rien, contre 37 éléments
déjà révélés. Ce lot traite le plus visible : cinq blocs qui apparaissaient d'un coup sur la
page où l'on décide d'acheter.

Deux temps. Le bloc monte (variante `card`, échelonnée), puis **le liseré teal du volet
« Avec Q-Bot » se dessine** 0,28 s plus tard, quand le bloc est posé. C'est le procédé n°4 de
linearity.io (un tracé qui se dessine au défilement, 7 139 px chez eux en
`stroke-dashoffset`) transposé à l'échelle d'un bloc, et ici il dit quelque chose : la
réponse arrive après le problème.

Trois points à ne pas défaire :

- **le liseré est un pseudo-élément, pas une bordure** : une bordure ne se met pas à
  l'échelle ;
- **son retard suit `--reveal-delay`**, donc l'échelonnement du bloc : le trait se dessine
  après que SON bloc s'est posé, pas après le premier de la pile. Mesuré : 0,28 / 0,355 /
  0,43 s ;
- **l'état au repos est le liseré entier.** L'animation n'existe que sous `.is-visible`.
  Vérifié sans JavaScript et en mouvement réduit : opacité 1, trait à pleine hauteur, aucune
  animation. C'est la règle apprise sur le trait de la section évolution, qui restait
  invisible faute de valeur par défaut.

**Trois temps ont été écartés** : faire en plus arriver les deux volets en cascade demande la
variante « groupe », qui immobilise le conteneur, et le module 4 écarte justement un élément
de groupe dont le parent est déjà révélé (il serait animé deux fois et repartirait de zéro au
milieu de sa propre arrivée).

Au passage, la note en tête d'article reçoit la variante `plain` : elle n'avait pas d'entrée
non plus.

**Proposition N faite le même jour : les coches se dessinent.** Les quinze arguments à coche
des deux pages Caractéristiques reçoivent la variante `plain` (elles n'avaient aucune entrée)
et leur coche se trace, échelonnée, du talon vers la pointe.

Trois choses à savoir :

- **le sens du tracé est dans le balisage, pas dans le CSS.** La polyligne allait de la pointe
  longue `(20,6)` au talon `(4,12)` : dessinée dans cet ordre elle se construisait à l'envers
  d'une main. Les points ont été retournés dans les 30 SVG concernés. Aucune règle CSS ne peut
  le corriger — un motif de tirets se décale, il ne s'inverse pas, et un décalage négatif est
  équivalent au positif puisque la période du motif vaut deux fois la longueur ;
- **longueur mesurée de la polyligne : 22,63 unités** de viewBox (7,07 + 15,56), d'où
  `stroke-dasharray: 23` ;
- **l'état au repos est la coche entière** (décalage 0). Vérifié sans JavaScript et en
  mouvement réduit : opacité 1, décalage 0, aucune animation.

Le retard suit `--reveal-delay`, et comme l'index d'échelonnement est calculé par parent, il
repart de zéro à chaque liste : relevé 0 à 5 puis 0 à 3 puis 0 à 1 puis 0 à 2 sur les quatre
listes de la page. Quinze coches simultanées auraient fait du bruit.

**Proposition O faite le même jour : le bloc de code se dévoile comme un média.** Un objet
encadré est un média au sens de ce site : `.code-block` rejoint la variante `media` (masque qui
remonte, puis un passage de lumière). Il n'a pas d'`<img>`, donc le dézoom de la variante ne
s'applique à rien et seul le masque joue.

Deux lignes de CSS étaient obligatoires, et la première est le piège :

- **`overflow: hidden`**, sans quoi le passage de lumière (un `::after` translaté de −130 % à
  +130 %) s'échappe du cadre. C'est exactement ce qui avait causé 341 px de débordement
  horizontal sur les figures d'article, seul média du site à ne pas avoir cette propriété.
  Vérifié après coup : 0 débordement à 390, 768 et 1440 px ;
- **`--media-radius: var(--radius)`**, sinon le masque prend `--radius-lg` par défaut et
  arrondit plus que le cadre pendant toute la durée du dévoilement.

Le bouton « Copier » reste en place et cliquable (il est dans le `pre`, bien à l'intérieur du
masque), et le `pre` garde son propre défilement horizontal. Sans JavaScript et en mouvement
réduit : opacité 1, aucun masque.

Les trois propositions issues de l'audit d'animation (M, N, O) sont donc faites.

## Les deux FAQ sont alignées, et la garantie reste ouverte (2026-08-20)

**« Six questions manquent au français » était faux, et la note de juillet en était la
cause.** Elle comparait le live (12 questions FR contre 16 EN) à une époque où notre FR en
avait 12 ; quatre ont été ajoutées depuis. Relevé ce jour : **nos deux FAQ ont 16 questions
chacune**, et une seule question du live EN n'a jamais été reprise, celle de la garantie.

**Elle ne peut pas l'être en l'état** : sur le live, la réponse à « What are the warranty
conditions of Q-Bot? » ne parle pas de garantie, elle explique comment utiliser Q-Bot. Notre
copie avait hérité de ce défaut.

**ARBITRÉ PAR LE CLIENT LE 2026-08-20 : la question de la garantie reste hors du site.** Ce
n'est donc pas un oubli à combler, et il ne faut ni la réintroduire depuis le live, ni écrire
des conditions de garantie de notre propre chef. Ce qui la remplace existe déjà et suffit : la
question 15 (« Que faire en cas de dysfonctionnement ») énonce la réparation à distance puis
le remplacement par un robot neuf, et les pages commande portent la carte « Remplacement
garanti ». Si de vraies conditions arrivent un jour (durée, couverture, exclusions), la
question pourra être ajoutée dans les deux langues à la position 12 bis.

Ce qui a été corrigé ici :

- **la question 12 anglaise était mal intitulée** : « What are the warranty conditions of
  Q-Bot? » sur une réponse d'utilisation. Elle devient « How do I use Q-Bot? », comme son
  pendant français à la même position, dans le bouton, dans l'index et dans le JSON-LD ;
- **sa réponse était périmée** : elle parlait encore de récupérer la valeur d'un token et
  ignorait l'app compagnon. Elle dit maintenant les deux chemins de déclenchement ;
- **deux restes de l'ancien récit avaient échappé au lot 1** : la carte « Confidentialité
  totale » des pages commande affirmait encore « les photos sont supprimées après
  traitement ». Mon contrôle d'alors cherchait « photo est supprimée » et « Photos
  supprimées » et ne pouvait pas voir « les photos SONT supprimées ». Un motif de contrôle
  doit couvrir le singulier ET le pluriel, l'actif ET le passif ;
- au passage, un doublon du français : « le déclenchement du scénario peut être automatiquement
  déclenché ».

**Les questions 6 et 7 sont alignées (2026-08-20).** C'est l'ANGLAIS qui a suivi le français,
pas l'inverse : « à qui s'adresse » enchaîne après « pourquoi Q-Bot est l'allié des testeurs »,
et cela regroupe les trois questions de conversion (présentation, prix, acquisition). La
manœuvre échange le CONTENU des deux blocs et laisse les identifiants en place, donc aucune
renumérotation, aucune ancre cassée : `faq-q6` reste la sixième question lue. Trois endroits à
échanger ensemble, sans quoi l'index pointe à côté : le bloc visible, le libellé d'index, et
l'objet du JSON-LD. Vérifié : les 16 entrées d'index de chaque langue mènent à la bonne
question, et les deux listes sont identiques dans l'ordre.

**Et la queue du lot 2 y était restée.** Ma recherche d'alors portait sur « token », or le
français dit « dispositif » : la question 8 française annonçait encore « avec quels types de
DISPOSITIFS d'authentification », décrivait la première version de Q-Bot conçue pour les
boîtiers LuxTrust, et portait une coquille (« Aujoud'hui »). Repris, plus quatre revendications
de compatibilité matérielle ailleurs : « d'autres dispositifs similaires déployés dans
différents pays » sur l'accueil, « les nouveaux dispositifs 2FA du marché », « vos dispositifs
2FA », « votre dispositif spécifique » sur les pages commande, et l'ouverture de la FAQ et de
l'accueil (« qu'elle s'appuie sur des applications mobiles ou sur d'autres dispositifs
sécurisés »). Contrôle : 0 revendication matérielle restante.

**Leçon de méthode** : un contrôle de vocabulaire doit porter sur les mots des DEUX langues.
Chercher « token » ne trouve rien dans un texte français qui dit « dispositif », et le défaut
survit à un contrôle qui annonce zéro.

## Audit d'après refonte (2026-08-20)

Passe mesurée sur les 23 pages après deux jours de réécriture (mécanisme, compatibilité, API,
app compagnon, éditeur, matériel, cas d'usage, tarif, cadratins, trois lots d'animation).
Instrumentée comme les précédentes : contraste calculé sur le fond réellement composité,
hiérarchie des titres, cibles tactiles à 390 px, liens internes, longueurs d'affichage en
recherche, poids transféré.

**Résultat : aucun défaut réel.** Le détail, parce que les chiffres bruts trompent :

- **contraste** : une seule remontée, un `span.visually-hidden` à 1,65. Un élément réservé aux
  lecteurs d'écran n'a pas de contraste à respecter. Tout le contenu neuf passe, y compris les
  libellés de cas d'usage, les points d'entrée en teal et les faits à coche ;
- **titres** : 0 saut de niveau, exactement un `h1` par page, sur les 23 ;
- **cibles tactiles** : 45 remontées à moins de 24 px, toutes exemptées. Ce sont le lien
  d'évitement (1×1 hors focus) et des liens **en ligne dans une phrase** (adresses, téléphones,
  renvois), cas que WCAG 2.5.8 exclut explicitement. La case de consentement mesure 20×20 mais
  son label cliquable fait 342×87 : la cible utile est de 87 px de haut ;
- **longueurs d'affichage** : 0 titre au-delà de 62 caractères, 0 description au-delà de 158 ;
- **poids** : accueil 2 369 Ko (modèle 3D compris), page 3D 1 783 Ko. Le client a accepté ce
  poids d'accueil le 2026-08-11, ne pas y revenir sans nouvelle demande.

**Et la divergence avec la brochure est close.** Elle était signalée depuis le 2026-08-19 : la
brochure décrivait un pilotage d'application Android réelle (appuis, code à usage unique, QR
code, validation, « sans mock ni simulation », « aucun SDK aucun agent », itsme, stockage
local) alors que le site racontait l'actionneur et la caméra. Après les lots 1 à 7, le site dit
exactement ce que dit la brochure. Plus aucun écart à arbitrer sur le mécanisme.

## Matière du modèle 3D livré (2026-08-11)

Le client voulait sur le viewer interactif la matière mise au point pour les visuels — « le Q-BOT en
vrai a un léger grain au toucher et la petite vitre est légèrement transparente ». `assets/models/qbot.glb`
porte donc maintenant : **corps charbon à grain fin**, **hublot en verre** et **écran 2FA sur le
smartphone**. Régénéré par `tools/render/patchglb-site.py`.

Ce script est le jumeau « livré » de `tools/render/patchglb.py` (rendu hors-ligne). Deux écarts, qui
sont tout l'intérêt du fichier séparé :

- **UV par sommet, pas par face.** Le triplanaire par face impose de dégrouper les sommets : le GLB
  passe de 3,6 à **15 Mo**, impensable pour un fichier téléchargé par le visiteur. En projetant
  selon l'axe dominant de la *normale du sommet*, la géométrie reste intacte (+8 octets/sommet) et
  le fichier tient en **4,7 Mo**. Le compromis est une discontinuité de texture sur les arêtes
  vives — invisible avec un grain isotrope fin, et une arête moulée en a une de toute façon.
  Grain en 256² au lieu de 512², et pas de texture métal/rugosité (facteurs constants).
- **Coque et plateau passent en `doubleSided`.** Sans ça le verre ne sert à rien : sur une coque
  single-sided, les faces arrière sont éliminées au rendu et on voit *le fond de la page* à travers
  le hublot au lieu d'une cavité sombre. C'est le double-face qui donne l'intérieur visible.

Le hublot est un `alphaMode: BLEND` à alpha 0,42, pas une transmission KHR — suffisant pour l'effet
demandé (« légèrement transparente ») et sans coût de rendu supplémentaire.

**La vitre a aussi été redimensionnée.** La plaque d'origine fait 86 × 96 mm alors que l'ouverture
pratiquée dans la coque n'en montre que 44 × 59 : les deux tiers sont enfouis dans le boîtier.
Invisible à l'assemblage — mais en vue éclatée on voyait s'envoler une plaque presque aussi large
que le produit. Elle est ramenée à l'ouverture + 2 mm de recouvrement.

L'ouverture n'est pas codée en dur : le script la **mesure**, en rastérisant dans le plan de la
vitre tout ce qui la masque (tous les rayons de vue étant parallèles à sa normale, une projection
suffit — pas besoin de lancer de rayons, et `rtree` n'est pas installé de toute façon). Le résultat
a été recoupé par une seconde méthode indépendante : deux rendus à **caméra fixe en absolu**, l'un
avec la coque l'autre avec la seule vitre, dont le rapport des boîtes englobantes donne l'ouverture
sans aucun calcul de projection. Les deux concordent à 1 mm près. Attention si on refait cette
mesure par rendu : model-viewer **recadre automatiquement sur les bornes du modèle**, donc un rayon
de caméra en pourcentage donne deux cadrages différents entre les deux passes et le rapport est
faux — il faut un rayon en mètres et un `camera-target` explicite.

### Piège de relevé : les blocs masqués du live (2026-08-12)

Deux fois dans la même journée, un relevé automatique du live a produit du faux contenu :

1. **Négociation de langue.** `q-bot.eu/` redirige vers `/en/` selon `Accept-Language`. Un relevé
   sans en-tête rapporte donc la version anglaise sur les URL françaises. Toujours fixer
   `locale` + `Accept-Language` par langue.
2. **Blocs masqués par un ancêtre.** Tester `display`/`visibility`/`opacity` sur l'élément lui-même
   ne suffit pas : le live garde des sections désactivées dont les enfants ont un style normal.
   C'est ainsi qu'un **« afficheur OLED à très haut contraste »** a été repris et publié alors
   qu'il n'est pas affiché sur la page — signalé par le client, retiré du site entier (blocs
   descriptifs, lignes de fiche technique FR/EN et de la page 3D, métadonnées, et les mentions en
   prose de `commandez`/`order` et de la homepage EN). **Le seul test fiable est
   `element.offsetParent !== null` combiné à la présence du texte dans `document.body.innerText`.**

Règle qui en découle : aucune caractéristique technique ne doit figurer sur le site si elle n'est
pas visible sur le live ou confirmée par le client. En cas de doute, demander plutôt que déduire.

**Passe systématique faite le 2026-08-12.** Inventaire des sections désactivées sur les 11 pages du
live. Attention au faux positif qui domine : une réponse de FAQ repliée est invisible au chargement
mais bien affichée quand le visiteur ouvre l'accordéon — un test naïf sur `innerText` en signale 76,
dont 70 sont des accordéons. Le tri se fait sur **l'ancêtre qui masque** : ignorer ceux sous
`.elementor-tab-content` / `.elementor-accordion` / `.elementor-toggle`, ne retenir que les
`display:none` posés sur une section ou un widget. Restent alors ~5 sections par page, dont
« Copyright @2022 » (ancien pied de page) et une feuille `@font-face` Sendinblue, qui sont du bruit.

Ce qui était désactivé sur le live et présent chez nous, donc supprimé : le hublot OLED (cf.
ci-dessus), la ligne « Une solution fabriquée sur demande, directement dans les locaux de Q-Leap au
Luxembourg. » (et sa traduction) et le tagline « do what you love » de la page À propos. Le reste du
contenu désactivé n'était pas repris chez nous : équipe fictive Colabrio, Lorem Ipsum, « Meet the
Professionals », et la frise datée « L'innovation continue… / Évolutions » — désactivée sur le live
elle aussi, ce qui confirme après coup l'arbitrage du client de garder les cartes `.evolution`.

Deux cas volontairement **conservés** malgré leur désactivation sur le live, parce que le contenu est
publié ailleurs sur le site officiel : la phrase « Compatible avec Selenium, Katalon, Robot
Framework… » (visible dans l'article de blog live) et la section « Q-Bot pour tous les professionnels
de l'IT / Tous types de projets IT » (désactivée sur `/en/`, mais bien affichée sur la homepage FR,
qui fait référence).

### Frise datée vs section « évolution » (2026-08-12)

La homepage a porté successivement les deux. La **frise datée du live** (Février 2022 → Décembre
2023, `.timeline`) avait été remise le 2026-08-12 dans la passe « texte exact du live », puis
**retirée le même jour à la demande du client : elle n'est plus à jour.** Ce sont les trois cartes
`.evolution` qui sont en place (prototype → génération actuelle → roadmap), sans aucune date.
`.timeline` reste dans la feuille de style et dans `PROGRESS` (qui pilote depuis le 2026-08-20 la
colonne vertébrale des cas d'usage), mais aucune
page ne l'utilise. Ne pas « corriger » cet écart avec le live sans demander : c'est un arbitrage
client, pas un oubli.

**La bonne taille ne suffit pas, il faut le bon centre (corrigé le 2026-08-12).** La première version
posait la vitre à 47 × 62 mm — l'ouverture plus 2 mm de recouvrement, donc la bonne taille — mais
laissait le trou à découvert d'un côté. Deux erreurs cumulées, toutes deux invisibles sur un simple
contrôle des dimensions :

1. **Homothétie de centre l'ouverture au lieu d'un recentrage.** `Wl *= s` autour de `(cu,cv)` ne
   déplace le centre de la plaque que de `(1-s)` vers l'ouverture. La plaque du FBX étant centrée en
   `x ≈ 0` alors que la fenêtre est à `x ≈ +12` (décalage réel du modèle, comme le socle du téléphone
   à `x ≈ +9,5`), il restait 6 mm d'écart en `u` et 5 mm en `v` pour 2 mm de recouvrement. Il faut
   mettre à l'échelle autour du centre de **la plaque**, puis translater ce centre sur celui de
   l'ouverture.
2. **Base locale non orthonormée.** La normale de la vitre n'est pas exactement perpendiculaire à X
   (`dn_x ≈ 0,018`, soit 1°) ; prendre `rt = X` tel quel donne une base oblique pour laquelle
   `Wl @ BAS` **n'est pas** l'inverse de `Wv @ BAS.T`. Le retour en coordonnées monde réintroduisait
   un cisaillement et décalait la vitre de 1,4 mm de plus. `rt` est redressé par Gram-Schmidt, avec
   une assertion `BAS @ BAS.T == I`.

Le contrôle qui compte n'est donc pas « la vitre mesure-t-elle la bonne taille » mais **le
recouvrement signé sur les quatre côtés**, exprimé dans la base du script : il doit valoir `LIP`
partout (2,00 / 2,00 / 2,00 / 2,00 aujourd'hui). Un contrôle qui recalcule la base depuis le fichier
patché passe à côté de l'erreur 2 — il faut projeter la plaque patchée dans la base issue de **la
source**.

Ce redimensionnement n'existe que dans `patchglb-site.py`, pas dans `patchglb.py` : les visuels
hors-ligne montrent le produit assemblé, où la taille de la plaque cachée n'a aucun effet.

Conséquences à ne pas oublier :

- **`NIGHT_EXPOSURE` est passé de 0,5 à 0,8** (`main.js` + l'attribut `exposure` des deux pages 3D) :
  le boîtier était gris moyen, il est charbon — à 0,5 il se noyait dans le fond noir.
- **Le sidecar base64 a été régénéré** (`qbot.glb.data.js`, ~6,4 Mo). Sans ça le mode `file://`
  continuerait d'afficher l'ancien modèle. Vérifié : `loaded: true`, animation intacte.
- **La source non texturée est archivée** dans `Documentations/assets-sources/qbot-untextured.glb`
  et c'est *elle* que lit le script. Ne jamais le relancer sur le GLB livré : il le patcherait une
  seconde fois (UV par-dessus UV, matériaux déjà sombres re-assombris).
- Contrôlé après coup : éclatement, insertion du téléphone, jour/nuit, FR et EN, plus le repli
  `file://`. Aucune erreur console.

## Le défaut entre les pas 3 et 4 : c'était le plan coté (2026-08-20)

Signalé trois fois, cherché trois fois sans succès, et trouvé en passant le navigateur
d'analyse en mode fenêtré (cf. la note sur SwiftShader ci-dessus). **La cause était une
correction précédente.**

Le 2026-08-19, pour supprimer les sauts d'annotations, les choix de côté du pas 4 (de quel
côté poser une cote, sur quel coin poser l'étiquette de la feuille) ont été figés sur la
caméra NOMINALE du pas. Conséquence non vue alors : le calque `hud-size` s'allumait dès que
`data-step` passait à 3, c'est-à-dire au premier pixel d'un balayage de **86°**, le plus long
de la séquence. Pendant tout ce balayage, le plan était juste pour un angle qu'on ne regardait
pas encore : constaté à l'image, à 61° de l'angle d'arrivée, **la cote « 15 cm » barre le
boîtier de haut en bas et l'étiquette « FEUILLE A3 » se pose sur sa face avant**.

Correction : le plan n'apparaît que **caméra posée**. `scrolly.js` compare l'angle réel à
l'angle nominal du pas et pose `is-cam-posee` sur la section ; le CSS conditionne le calque à
cette classe. Deux détails :

- **seuil 10°, hystérésis 16°** : sans elle, la dérive au repos (±3,2°) ferait clignoter le
  calque ;
- **la comparaison porte sur l'angle nominal**, pas sur la consigne lissée : c'est l'angle pour
  lequel le plan a été calculé.

Mesuré après : écart 70° puis 28° pendant le balayage, calque à 0 ; à 9,9° la classe tombe et
le calque monte à 0,91 ; à 0,4° il est à 1. Le fondu de 0,55 s du calque fait que le plan se
pose au lieu d'apparaître.

**Sans la classe, l'ancien comportement revient** : le seul risque est que le plan reste caché,
jamais qu'il s'affiche de travers. Et en mouvement réduit la classe est vraie par défaut, donc
rien n'est perdu (la séquence n'y dépasse de toute façon pas le pas 0).

**ET UN SECOND DÉFAUT AU MÊME ENDROIT, MONTRÉ PAR LE CLIENT EN CAPTURE : les repères
d'assemblage restaient sur le boîtier fermé.** Le calque `hud-burst` était allumé sur tout le
pas 3, or l'éclatement s'y ouvre PUIS se referme. À la fin du pas, les traits pointillés ont
une longueur nulle donc ils disparaissent, mais les quatre anneaux restent dessinés, rayon 2,5.
Mesuré : de 0,520 à 0,555 du parcours, quatre ronds teal posés sur le produit assemblé, plus le
fondu de sortie par-dessus.

L'opacité du calque suit désormais l'ouverture réelle (`--sc-burst`, écrite depuis le `kt` de
la boucle de dessin) et non le numéro du pas. Sans transition : la valeur est déjà scrubbée par
le défilement, une transition ne ferait que la mettre en retard. Valeur de repli 0, donc un
moteur muet laisse le calque éteint, jamais allumé de travers. Mesuré après : 0,95 à
l'éclatement maximal, 0,001 puis 0 dès que le boîtier est refermé.

**La leçon est la même dans les deux cas** : sur cette séquence, un calque d'annotations ne
doit pas dépendre du NUMÉRO du pas mais de l'état qu'il annote. Le plan coté dépend de
l'arrivée de la caméra, les repères d'assemblage dépendent de l'ouverture.

Pistes explorées et écartées, pour ne pas les refaire : les coordonnées du calque SVG (aucun
NaN, aucun emballement sur 275 images), l'alpha de la coque (monotone, bond maximal 0,098),
l'ombre portée de model-viewer (forcée à 0, l'agitation du sol est identique : ce sont les
pièces qui bougent), et le halo CSS derrière l'objet, dont le centre est pourtant déplacé à
chaque image — sur le GPU il produit moins de 2 niveaux d'écart entre deux images et le sol
n'a aucune marche de bande.

## Passe d'alignement, et le piège du `vw` (2026-08-20)

Retours client : « le site en 2K est un peu étrange et pas trop responsive », « il y a encore
du texte centré », « les titres des étapes n'ont pas la même taille que les autres titres »,
« les titres et textes des étapes ne sont pas alignés sous le logo Q-Leap ». Tout était exact,
et tout venait de la même faute : **la séquence était posée en unités de FENÊTRE, pas dans le
conteneur du site.**

Mesuré avant correction, à 2560 px : le texte des étapes commençait à x=148 quand le logo et
tous les autres titres sont à x=714, soit **566 px d'écart** ; la scène 3D, collée à droite par
`padding-right: 4vw`, débordait le conteneur de 588 px ; il restait environ 1 500 px de vide
entre les deux colonnes. Et le titre d'étape montait à 42 px contre 36 px pour un titre de
section, alors que ce sont deux `h2`.

Ce qui est en place :

- `--sc-gut` reproduit la gouttière de `.container` (moitié du reste, plus 24 px). Le texte est
  posé à `--sc-gut` moins 28 px, soit le retrait interne (26) plus le liseré (2) : c'est le
  TEXTE qui tombe sur la gouttière, et son liseré teal se place dans la marge, comme les
  marques de section. Écart mesuré : **0 px de 1200 à 3440 px** ;
- la part négative passe en `margin-left` : entre 940 et 1204 px la gouttière vaut 24, donc
  24 − 28 serait un remplissage négatif, refusé, et le texte retombait 4 px trop à droite ;
- la scène s'arrête sur la gouttière droite et son plafond est la place restante, soit 662 px,
  constant par construction. Jeu texte/scène : +42 px partout ;
- le titre d'étape reprend l'échelle des `h2` (`clamp(1.5rem, 3vw, 2.25rem)`), au-dessus comme
  en dessous de 940 px ;
- pastilles et compteur passent de `3vw` du bord de la fenêtre à 72 px à gauche du texte, donc
  dans la marge du conteneur : à 2560 ils étaient 674 px à gauche de tout le contenu.

**ATTENTION AU PIÈGE QUI M'A COÛTÉ DEUX ITÉRATIONS** : un pourcentage dans une propriété
personnalisée se résout sur le bloc conteneur de l'élément qui l'UTILISE, pas de celui qui la
déclare. La scène étant un élément de la grille du plateau, dont la boîte de contenu vaut déjà
« fenêtre moins gouttière », `--sc-gut` y valait 77 px au lieu de 154, et le plafond 739 au lieu
de 662, d'où un recouvrement de 37 à 98 px avec le texte. D'où l'expression dédiée
`--sc-gut-scene`, dérivée algébriquement et documentée sur place.

**Blocs centrés** : le seul restant était la liste de questions des pages commande, centrée par
un `margin: 0 auto` EN LIGNE, invisible à la feuille de style (qui dit pourtant `margin: 0`).
Un contrôle des centrages doit chercher les styles en ligne, et pas seulement les règles. Reste
volontairement centré : le contenu des boutons, et le bouton flottant de la séquence, ancré à la
fenêtre comme tout bouton flottant.

**CETTE NOTE ÉTAIT PÉRIMÉE, CORRIGÉE LE 2026-08-26.** Elle disait le conteneur « plafonné à
1180 px » avec 690 px de marge à 2560, et proposait de l'élargir comme décision de charte. Le
relevé montre qu'il vaut `clamp(1180px, 72vw, 1440px)` : il est FLUIDE, atteint 1440 dès 2000 px
de large, et il l'est uniformément sur toutes les pages (pied de page compris). Il n'y a donc rien
à arbitrer, et surtout : **on ne déduit pas la largeur d'un bloc de cette note.** Elle m'a fait
dimensionner une vignette pour une carte de 398 px alors qu'elle en fait 441 à 2560. On mesure.

## Passe mobile du scrollytelling + modèle compressé (2026-08-19)

Audit mesuré (Playwright, 375×667 / 360×740 / 390×844 / 414×896 / 844×390 en paysage)
puis correction. Rien de tout cela ne se voyait à l'œil sur un écran de bureau.

### Géométrie : une seule grandeur gouverne les deux zones

La scène (`44svh` sous une barre de 84 px) et la carte de texte (calée en bas) étaient
posées **indépendamment** : rien ne garantissait qu'elles ne se croisent pas, et elles se
croisaient — 16 px de recouvrement sur iPhone SE, 89 px en paysage, avec le bas du
boîtier passant sous la carte au pas 2 et la cote « 24 cm » au pas 4.

Désormais `--sc-card-zone` réserve la hauteur du texte et la scène prend le reste
(`--sc-free`). **Cette hauteur est mesurée, pas devinée** : `scrolly.js` relève la plus
haute des quatre cartes au chargement, au redimensionnement et à l'arrivée des polices.
Deux constantes ont été essayées avant et sont retombées fausses (un pourcentage de la
hauteur d'écran donne trop peu sur un petit téléphone, trop sur un grand ; une valeur
fixe casse au premier mot ajouté au texte). Résultat : **zéro recouvrement** sur les
quatre tailles portrait, aux quatre pas, et la scène passe de 371 à 420 px sur iPhone 14.

Trois autres pièges de la même famille, tous mesurés :
- **Le zoom de caméra est un `scale()` CSS** porté par la scène. Sur `100vw` à 1,16 il
  donnait 452 px pour un écran de 390 : 31 px rognés de chaque côté. Sur mobile
  l'amplitude est ramenée de moitié et les dimensions sont divisées par
  `--sc-zoom-max`, si bien que la boîte agrandie coïncide exactement avec sa rangée.
- **`--sc-top: 44px`** et non la hauteur de la barre (72) : la barre se masque au
  défilement vers le bas, lui réserver sa place en permanence coûtait 32 px d'objet.
- **Le paysage doit annuler l'empilement** (`--sc-card-zone: 0`, `grid-template-rows:
  none`), sinon `--sc-free` devient négatif et la scène part à −164 px. Sous 520 px de
  haut la séquence reprend la mise en page deux colonnes du bureau.

### Ce que le mobile avait perdu

- **Aucun moyen de sortir** de 4,2 écrans épinglés : le lien d'évitement mesure 1×1 px
  hors focus, donc n'existe pas sans clavier. Le **même élément** devient une pastille
  visible tant que `body.is-scrolly` est posé. L'intitulé complet fait 180 px et
  débordait : seul le premier mot est visible, le reste masqué visuellement — le nom
  accessible du lien ne change pas.
- **Aucune progression annoncée** : les pastilles (les seules à porter `aria-current`)
  sont masquées sous 900 px et le compteur était `aria-hidden`. Il est maintenant
  `role="status"` avec une phrase (« Étape 2 sur 4 ») doublant la forme chiffrée.
- **Aucun appel à l'action** : le bouton flottant est retiré sous 900 px. Il revient
  **dans la carte du dernier pas** (`.scrolly__step-cta`), où il ne peut recouvrir
  personne, avec le libellé exact de `data-cta-last`.
- **Le bouton « retour en haut » recouvrait le compteur** ([322,772,44×44] contre
  [331,811,41×19]) : masqué pendant la séquence.
- **422 px de défilement à vide** après le dernier texte : `--scrolly-screens: 4.2`.
- Cotes projetées à 11 px → 13 px (la scène à 86vw laisse la marge pour les agrandir).

### `--scrolly-screens` : la hauteur quitte le style en ligne

`<section class="scrolly" style="height: calc(4.5 * 100svh)">` était **inatteignable par
toute requête média**. Sous `prefers-reduced-motion` la section gardait donc 4,5 écrans
pour 1 917 px de contenu : **1 881 px de vide**, mesurés. La hauteur est passée en
variable CSS, remise à `auto` en mouvement réduit (vide : 0 px). Troisième occurrence du
même piège sur ce site (cf. `.spec-item`, les centrages de `commandez`).

### Le modèle passe en Draco : 2 622 → 571 Ko

`gltf-transform draco` (npx, sans installation). **Aucune décimation** — la géométrie,
les 6 matériaux, leurs couleurs de base (que `scrolly.js` vérifie pour identifier la
coque) et le clip « Explode » sont identiques. Contrôle : écart pixel moyen de
0,000 à 0,073/255 sur les quatre pas, **aucun pixel au-delà de 8/255**.

- à 1,5 Mbit/s le modèle est prêt en **4,3 s au lieu de 14,7 s**, page de **1,71 Mo au
  lieu de 3,58 Mo** ;
- `EXT_meshopt_compression` a été essayé d'abord (631 Ko, encore mieux) et **écarté** :
  model-viewer 4.3.1 ne l'accepte pas — `THREE.GLTFLoader: setMeshoptDecoder must be
  called before loading`, et le composant n'expose aucun moyen d'injecter le décodeur ;
- Draco, lui, est décodé nativement, mais **model-viewer va chercher son décodeur sur
  `www.gstatic.com`** (`draco_wasm_wrapper.js` + `draco_decoder.wasm`). Même famille de
  domaine que les polices du site, mais une dépendance de plus : bloquée, le modèle ne
  charge **pas du tout**. D'où le filet ci-dessous. Le décodeur n'a pas été auto-hébergé
  à dessein : ce serait un `fetch` de plus, que le mode `file://` interdit — la variante
  gstatic, elle, fonctionne même en ouvrant le fichier à la main.
- **Le master texturé non compressé est archivé** dans
  `Documentations/assets-sources/qbot-textured-uncompressed.glb`. C'est lui qu'il faut
  recompresser si le modèle change ; ne jamais recompresser le livré.
- **Sidecar régénéré** : `qbot.glb.data.js` tombe de 6,4 Mo à 762 Ko.

### Filet de sécurité : 12 s, puis le repli statique

Nouveau garde-fou dans `scrolly.js` : si `viewer.model` est toujours absent au bout de
12 secondes, l'image de repli prend la place du canevas et l'indicateur de chargement
disparaît. Vérifié en bloquant le décodeur Draco : `data-fallback="modele indisponible"`,
image affichée, séquence toujours parcourable (le pas 3 s'active normalement). Le repli
s'étend aussi désormais aux **connexions lentes** (`effectiveType` 2g, ou 3g sous
1,2 Mbit/s) — seul `saveData` était testé, or il est rarement activé.

Et un **indicateur de chargement** (`.scrolly__loading`) affiche la progression réelle :
sans lui, quinze secondes d'affiche immobile ne se distinguent pas d'une panne.

### En une colonne, l'image suit toujours son texte

Sur deux colonnes, alterner les côtés donne le rythme ; en une colonne cela met deux
images bout à bout. Relevé à 390 px sur la page d'accueil : « La solution » se lit
texte → image et la section LuxTrust juste après image → texte, donc **« t I I t »** —
deux visuels d'affilée sans un mot entre eux. Toutes les autres grilles du site étaient
déjà en texte → image ; la règle (`order: 2` sur `.intro__image` sous 900 px) aligne la
dernière exception. Le bureau est inchangé (`tI It`).


## Le filet de sécurité étranglait la séquence sur téléphone (2026-08-20)

Signalé autrement : « pas de souci entre les pas 3 et 4 sur iPhone, c'est peut-être
l'optimisation ». Il n'y avait rien à voir sur iPhone parce qu'**il n'y avait pas de 3D
du tout**. Sous 1440 px de large, la séquence tombait TOUJOURS sur son image de repli,
sur toutes les liaisons, y compris rapides — relevé : aucune requête `qbot.glb` à 390,
768 et 1024 px, `data-fallback="modele indisponible"` à chaque fois.

Cause : le compte à rebours de 12 s partait du **chargement de la page**, alors que la
balise porte `loading="lazy"`. Sur un écran étroit le hero occupe le premier écran, donc
la scène est hors champ au chargement et model-viewer ne demande même pas le fichier :
le délai expirait avant la première requête. Le filet censé protéger la séquence la
supprimait.

Trois corrections, toutes dans `scrolly.js` sauf la dernière :
- le délai s'arme à l'**arrivée réelle** de la scène à l'écran (IntersectionObserver
  **sans marge** : `rootMargin: '400px'` suffisait à l'armer au chargement sur un
  téléphone, la séquence commençant juste sous le hero) ;
- il est **relancé à chaque `progress`** : 12 s comptent désormais l'absence de progrès,
  pas la durée totale. À 0,7 Mbit/s le modèle arrive en 8 s, sans repli ;
- la balise passe en **`loading="eager"`** : la séquence est le contenu principal de
  l'accueil, pas un supplément.

Contrôlé aux quatre largeurs × trois situations (15 s en haut de page, arrivée sur la
séquence, décodeur Draco injoignable). Le repli ne survient plus que dans le dernier cas.

**Leçon de méthode** : un repli qui se déclenche est indistinguable, à l'œil, d'un repli
qui doit se déclencher. Tout garde-fou de ce genre doit être vérifié dans les deux sens —
« il s'affiche quand il faut » ET « il ne s'affiche pas quand il ne faut pas », aux
largeurs où la mise en page change.

### Ce que le chargement a rendu visible : la carte passait sur le produit

Personne n'avait jamais vu la séquence 3D sur téléphone. Une fois le modèle chargé, la
carte de texte recouvrait le tiers bas du boîtier : **jusqu'à 303 px de recouvrement à
390 px, 243 à 375, 282 à 414**, pendant l'essentiel du parcours. La passe mobile du
2026-08-19 concluait « zéro recouvrement » parce qu'elle ne mesurait qu'aux **quatre
positions de calage** — les seules où la carte est effectivement en bas.

> **Règle de mesure.** Un recouvrement se relève sur un **balayage fin** de tout le
> parcours (ici 81 positions), jamais aux quelques positions canoniques. Et il se compte
> en **deux dimensions** : un relevé par abscisses annonçait « 452 px » pour un trait
> horizontal au ras du bas de l'écran, qui ne touche rien.

La carte est maintenant en **`position: fixed`** dans la zone qui lui est réservée, sous
900 px. Deux choses à ne pas refaire :
- **Ne pas épingler le conteneur des pas.** `nearest()` et `fraction()` lisent la
  position des `.scrolly__step` pour savoir quel pas est actif et où en est
  l'éclatement. Épinglé, tout se figeait : séquence bloquée au pas 1, caméra immobile.
  Seule la carte quitte le flux.
- **`position: sticky` ne peut pas y arriver**, quelle que soit la valeur de `top` ou de
  `bottom` : un élément collant reste dans sa boîte parente, et le pas fait exactement un
  écran de haut. Sa course d'épinglage vaut donc « écran − hauteur de carte » (498 px à
  390) quand la fenêtre où le pas est actif vaut un écran entier (844). Essayé deux fois,
  recouvrements identiques au pixel.

Conséquence à connaître : la dernière hauteur d'écran de la section sert à évacuer la
scène, et une carte fixe ne peut pas partir avec elle — on la retrouvait posée sur le
titre de la section suivante. D'où le drapeau **`is-scrolly-exit`** (posé par `apply()`
quand `p >= 1`, c'est-à-dire pile quand le bloc collant se décroche), qui l'efface. Il
n'est utilisé que sous 900 px : au-dessus, le texte est à côté de la scène et part
normalement avec elle.

Dernier croisement du même effet, corrigé dans la foulée : l'indication de défilement,
calée à 26 px du bas, se retrouvait derrière la carte fixée (96 × 6 px à 390, 96 × 16 px à
360). Elle se pose maintenant au-dessus de la zone de texte, au ras du bord bas de la
scène, là où il n'y a que du fond — le boîtier est centré dans sa zone et ne descend pas
jusque-là (vérifié : 79 à 151 px d'écart avec la carte, et l'indication s'efface dès le
premier geste de défilement).

### Le repère de progression passe à l'horizontale jusqu'à 1300 px

Les pastilles numérotées recouvraient le texte de **940 à 1200 px, 26 px de recouvrement
constant** : le texte se cale sur la gouttière du site, qui tombe à son plancher de 24 px
dès que la fenêtre est plus étroite que le conteneur, et les pastilles font 26 px de
large. Il n'y a pas de place, aucun réglage n'en crée. La forme déjà validée pour le
téléphone — trait fin au ras du bas + numéro du pas — monte donc à 1300 px : elle ne coûte
aucune largeur. Au-delà, les pastilles reviennent et c'est le compteur chiffré qui
s'efface (doublon signalé par le client).

Corrigé au passage : la carte dépassait de l'écran par la gauche (**bord à −4 px de 940 à
1180 px**), emportant son filet teal. Le calage tire la carte de 28 px vers la gauche pour
que le TEXTE tombe sur la gouttière ; les 4 px manquants sont maintenant pris sur la marge
intérieure. **La version calculée (`min(0px, var(--sc-gut) - 28px)` posé sur la carte) est
fausse** : `--sc-gut` contient un pourcentage, et un pourcentage se résout sur l'élément
qui s'en sert — la carte fait 456 px de large, pas la largeur de la section. Troisième
occurrence de ce piège (cf. `--sc-gut-scene`). La borne est fixe (1187 px) parce que le
manque vaut exactement 4 px dès que la fenêtre est plus étroite que le conteneur.

## Les bandes d'outils qui défilaient sont remplacées (2026-08-20)

« Les carrousels sont un peu illisibles cognitivement » — et c'est juste : une liste qui
bouge ne se lit pas, elle se subit. On ne peut ni la parcourir, ni relire un nom qui vient
de passer, ni vérifier si le sien y est, ce qui est exactement la raison d'être de la
section. Le défilement rendait la liste entière *visible*, pas *lisible*.

À la place, `.compat` : une **grille régulière** (`auto-fill`, plancher 190 px), une case
par entrée, les noms alignés en colonnes. Ce qui la tient : un liseré teal sur le bord
gauche de chaque case (le vocabulaire des cartes de la séquence et des titres de partie),
une case qui se soulève de 2 px au survol, et un **trait pointillé** pour l'entrée
fourre-tout — « toute app 2FA Android » n'est pas un produit, c'est une porte ouverte, et
le pointillé le dit sans un mot. Le liseré se dessine une fois à la révélation ; au repos
il est entier.

Appliqué aux quatre bandes du site (`caracteristiques`, `en/technical-specs`,
`commandez`, `en/order`). **Le motif est écarté, pas mis de côté** : le module 17 de
`main.js` (~120 lignes), le bloc CSS « BANDES D'OUTILS », `.tool-tag` et `.tools__list`
sont supprimés — plus une page ne les emploie. C'est l'écart avec `.timeline`, gardée
comme chemin de code sur arbitrage du client.

`.tools__grid` passe en `align-items: start` : les deux colonnes n'ont pas le même nombre
de cases (cinq applications, neuf outils) et, centrées, leurs titres ne tombaient pas sur
la même ligne (89 px d'écart à 1440 px).

## Retours de contenu du 2026-08-20

- **« Feuille A3 » retiré du pas 4** (carte + étiquette dans le plan) : les trois cotes
  portées par le modèle disent déjà l'encombrement, la mention faisait doublon. Le tracé
  de la feuille reste, c'est lui qui donne aux cotes au sol un cadre où se poser. Le titre
  devient « Il ne prend pas votre bureau », et le chiffre-clé la fabrication à Bertrange.
  La page `caracteristiques` garde ses mentions A3, qui viennent du live.
- **La carte « 100 % »** de l'accueil disait « Efficace à 100 % : l'appui arrive sur la
  vraie application, il n'y a rien à reconnaître » — brumeux, parce qu'il faut savoir que
  les robots concurrents lisent l'écran en image pour comprendre l'argument. Devient
  « Zéro faux positif » + « L'appui se fait sur la vraie application. Rien n'est deviné à
  l'image, donc rien ne peut être mal lu. » (FR et EN.)
- **« Éclaté » → « Ouvrir »** sur le curseur de `modele-3d.html` : c'est le terme de la
  CAO, il ne dit pas au visiteur ce qui va se passer. L'anglais garde « Exploded », qui
  est le mot courant dans cette langue.
- **L'étiquette « emplacement du smartphone »** se recentre de 16 unités vers le produit
  (34→24, 22→18, 28→22), sans changer de côté ni de point d'accroche — le verrouillage du
  côté gauche reste, c'est lui qui empêche le libellé de sauter en cours de balayage.

## Pages légales : aucune n'existe dans ce dépôt

Question posée le 2026-08-20 : d'où vient le contenu des pages « conditions de vente » et
« confidentialité » ? Réponse : **de nulle part, il n'y en a pas**. Il n'existe aucun
fichier local ; les pieds de page des 23 pages et la case de consentement du formulaire de
contact **pointent vers le live** (`https://q-bot.eu/conditions-vente/`,
`/confidentialite/`, et les équivalents `/en/`). Rien n'a été inventé, rien n'a été repris
du dossier `Documentations/website`. C'est un arbitrage du 2026-07-09 : un texte juridique
paraphrasé est pire que pas de texte, et l'outil de relevé refuse de reproduire ces pages
mot pour mot. Si un jour ces pages doivent vivre dans le site statique, il faut le texte
fourni par le client, pas une reconstitution.

## Mesures de performance de la séquence (2026-08-20)

Faites parce que la question était posée (« peut-être un souci d'optimisation ? »). Trois
relevés indépendants, tous sur Chromium fenêtré (en headless c'est SwiftShader qui rend,
les temps ne veulent rien dire) :

- **16,7 ms par image** en DPR 1 comme en DPR 2, sur les quatre pas et les trois
  transitions, aucune tâche longue sur le fil principal ;
- **~59 im/s médianes avec le processeur bridé quatre fois** (p95 34-49 ms, aucun
  blocage) ;
- **103 ms de rastérisation** sur toute la traversée (~3 s), soit 0,6 ms par image.

Deux optimisations envisagées et **écartées faute de gain mesurable** : figer les
animations d'ambiance hors écran (0,2 ms par image, soit le bruit entre deux passes
identiques) et arrêter le déplacement du halo `--sc-glow`, écrit à chaque image sur un
dégradé de 4 Mpx (RasterTask identique à 5 ms près). Ne pas y revenir sans un chiffre.

Le différentiel image par image de la traversée 3→4 est propre sur les **deux moteurs** :
écart médian de 1,5/255 entre deux prises consécutives sous Chromium, les deux plus grands
(2,6 et 2,5) tombant sur les moments où la caméra tourne le plus vite ; et 0,08/255 sous
WebKit (installer le navigateur avec `python3 -m playwright install webkit`). Aucun pic,
donc aucun artéfact. Ce qui avait été signalé était bien les deux états corrigés
précédemment (le plan coté qui apparaissait pendant le balayage, les bagues d'éclatement
sur un boîtier fermé).


## La page « cas d'usage » (2026-08-20)

Cinquième page de contenu, reprise de `Documentations/website/use-cases.html` : cinq
situations réelles, chacune en deux volets (le blocage, puis ce que Q-Bot en fait), puis
l'API en trois exemples d'appel et le tableau d'intégration par outil.

`cas-usage.html` et `en/use-cases.html` sont **générées par un script unique** (gabarit
commun, deux jeux de textes). C'est délibéré : les passes d'audit ont reproché plusieurs
fois aux pages écrites l'une après l'autre d'avoir divergé de structure. Le français
n'est pas une traduction littérale (règle du dépôt) ; l'anglais reprend leurs textes mot
pour mot.

**Ce qui a été retiré des autres pages**, puisque ce contenu vit maintenant ici :

- `commandez` / `en/order` : les cinq cas d'usage (environ 4 000 caractères). Le chapeau
  de section reste, avec un lien vers la nouvelle page — une page de commande doit dire le
  prix et ce qui est inclus, pas dérouler cinq scénarios ;
- `caracteristiques` / `en/technical-specs` : l'exemple d'appel unique et le tableau des
  sept outils. Ce qui reste relève d'une fiche technique — les trois points d'entrée et
  les quatre faits d'intégration — plus un lien vers les exemples.

**« Cas d'usage » entre dans la navigation et le pied de page des 25 pages.** Une page sans
entrée de menu n'est atteignable que par le plan du site. Vérifié : la barre tient de 901 à
1440 px sans recouvrement ni débordement (elle porte maintenant quatre entrées, un bouton
et le sélecteur de langue).

### La séquence : deux procédés de linearity.io, pas un fondu enchaîné

Première version signalée comme « pas la folie », et c'était juste : cinq panneaux qui se
succédaient en fondu, sans repère de progression. Refaite autour de deux procédés relevés
chez linearity.io, tous deux au service de ce que la section raconte.

**1. Le tracé qui se dessine au défilement** (leur procédé n°4, un chemin de 7 139 px en
`stroke-dashoffset`). Ici, une colonne vertébrale le long des cinq cas, avec une pastille
numérotée par cas : elle se remplit à mesure qu'on lit et relie les cinq situations en un
seul parcours. C'est la seule chose de la page qui dise « il y en a cinq, tu en as lu
deux ». Elle est **scrubbée par le moteur de mouvement** (`--ucs-p`), donc par le doigt du
lecteur et non par une horloge : c'est le **premier usage réel du tableau `PROGRESS`**
depuis le retrait de `.timeline`, et le modèle de la ligne de lecture est le bon (le bloc
traverse le viewport, seul le schéma est épinglé).

**2. Un seul schéma qui se transforme**, au lieu de cinq diapositives. Le cadre — trois
boîtes, deux liens — ne bouge jamais ; à chaque cas les mots basculent et les deux liens
**se retracent** de haut en bas, décalés de 120 ms, si bien que l'œil suit l'appel qui
redescend. Mesuré au changement de cas : 14 px et 0 px de tracé à 60 ms, 35 et 3 à 140 ms,
44 et 36 à 260 ms, complet à 500 ms.

Cinq points à ne pas défaire :

- **Le retraçage n'existe que grâce à deux noms de keyframes alternés selon la parité du
  cas.** Une animation CSS ne repart pas quand un sélecteur cesse de correspondre : le lien
  est le MÊME élément d'un cas à l'autre, donc `animation` inchangée, donc aucun
  redémarrage. Changer `animation-name` relance l'animation, et deux cas consécutifs sont
  toujours de parités différentes. (Un saut de 0 à 2 ne relance pas : sans conséquence,
  l'état d'arrivée est identique.)
- **Le tracé anime `height`, pas `scaleY`** : sa tête est un disque, une mise à l'échelle
  verticale l'écraserait en ellipse. Deux pixels de large sur quarante de haut, le coût de
  rastérisation est nul.
- **Les libellés d'un même emplacement sont empilés dans une seule cellule de grille**
  (`grid-area: 1 / 1`). La boîte prend donc la hauteur du plus long et ne change plus de
  taille d'un cas à l'autre, sans qu'aucune hauteur ne soit écrite à la main.
- **L'état au repos est l'état complet** : colonne remplie (`var(--ucs-p, 1)`), liens
  tracés, premier cas affiché (`data-uc="0"` est dans le HTML). Vérifié sans JavaScript et
  en mouvement réduit : les cinq cas se lisent, rien ne bouge.
- **Le seuil de la colonne est calculé, pas choisi.** La pastille numérotée fait 24 px et
  se pose à 40 px à gauche du texte : il faut 42 px de gouttière, soit une fenêtre de
  1 216 px pour un conteneur de 1 180 (on prend 1 260 pour le halo). En dessous, un anneau
  simple de 12 px, qui tient dans les 24 px du plancher de gouttière jusqu'à 1 220 px.
  Sous 1 220 px la colonne disparaît : un trait collé au bord de l'écran est du bruit, pas
  un repère. Relevé : pastille à x=114 en 1440, à x=24 en 1260, anneau à x=25 en 1220,
  rien en dessous.

Le numéro vient de `counter()`, donc aucun balisage n'est ajouté et l'ordre reste vrai si
un cas est inséré. La carte que l'on lit prend un liseré teal, pour s'accorder à sa
pastille ; les autres ne sont PAS assombries, un assombrissement coûterait du contraste sur
du texte.

### Le schéma « chemin de l'appel » est retiré, la séquence est épinglée

Troisième forme, et la bonne. Le schéma a été **retiré à la demande du client** (« il
gêne ») : trois boîtes et deux flèches occupaient la moitié de l'écran pour redire ce que
le texte disait déjà. Et le reproche de fond était ailleurs : « la page est sombre et on n'a
pas la sensation d'être scrollytellé ».

Ce qui est en place :

- **la section est épinglée cinq écrans, un cas à l'écran**, et le défilement fait avancer
  la séquence. C'est cela, la sensation qui manquait : les deux formes précédentes
  faisaient défiler cinq cartes sous un panneau qui changeait, ce qui se lit comme une
  page, pas comme un récit ;
- **le mécanisme est celui de l'acte épinglé de la page Caractéristiques** : le moteur de
  mouvement écrit `--ucs-p` (progression de la course de collage) et `data-panel` (le
  numéro du cas), modèle « rail épinglé » de `.pin-modes`. Une seule grandeur gouverne la
  carte affichée, le halo, l'index et le rail, donc rien ne peut se désynchroniser. Le
  module 17 (observateur d'intersection) a été **supprimé**, il n'avait plus d'objet ;
- **le sens de sortie compte** : un cas déjà lu sort par le haut, un cas à venir attend en
  dessous. Vingt combinaisons possibles, dix à écrire, et sans cela la pile se lit comme un
  jeu de cartes qu'on repose au même endroit ;
- **un index de cinq pastilles numérotées dans la gouttière** : on voit les cinq, donc on
  sait où l'on en est. Il demande 26 px plus 16 d'écart, donc il n'apparaît qu'au-delà de
  1 260 px ; en dessous c'est un rail de progression au ras du bas de l'écran épinglé qui
  prend le relais (même arbitrage que sur la séquence 3D, où le client avait signalé le
  doublon entre les deux formes) ;
- **de la lumière** : un halo teal dont la position se déduit de `--ucs-p`, donc sans une
  écriture JavaScript de plus. C'est ce qui répond au « la page est sombre » ;
- **le chiffre-clé est DANS la carte**, pas dans une colonne à part. La version d'avant le
  mettait à droite en très grand : joli, mais il disparaissait sous 940 px (la colonne
  n'existe plus) en emportant une information que la carte ne dit pas (« moins de dix
  secondes »). Dans la carte, il est lu partout, et la scène n'a plus de demi-colonne vide.

Trois pièges rencontrés, tous mesurés :

1. **SANS JAVASCRIPT, QUATRE CAS SUR CINQ ÉTAIENT INVISIBLES.** L'épinglage est du CSS pur
   (`sticky` plus `data-panel` écrit dans le HTML), donc il s'appliquait même quand le
   moteur ne tournait pas : la section restait collée sur le premier cas, pour toujours. Le
   moteur pose désormais une classe **`mx-scrubbed`** sur chaque élément qu'il scrube, et
   toute la mise en scène épinglée en dépend. Sans la classe, la section est une liste.
   C'est la règle du dépôt appliquée à une mise en page, et non plus seulement à une
   animation.
2. **Les règles de repli doivent reprendre `.mx-scrubbed`**, sinon elles ne pèsent pas
   assez lourd : la section gardait ses cinq écrans à 390 px, soit trois écrans et demi de
   vide sous les cartes.
3. **Un `.container` dans un conteneur flex ne s'étire pas.** La scène est un `flex` en
   ligne : `.container` prenait la largeur de son contenu et son `margin: 0 auto` le
   centrait. La carte commençait à 270 px au lieu des 154 de la gouttière, donc plus alignée
   sous le logo. Corrigé par `flex: 1 1 auto`. Relevé après : écart 0 avec le logo à 940,
   1024, 1280, 1440, 1920 et 2560 px.

### La bande d'exemples d'appel qui glisse

Demandé explicitement : le procédé de la section « Everyone creates » de linearity.io, où des
blocs défilent de droite à gauche pendant qu'on descend. Appliqué aux exemples d'appel de la
section « Un appel HTTP, et n'importe quelle chaîne de tests ».

**La course est exactement ce qui dépasse**, donc le rapport au défilement est de un pour un :
la section est haute d'un écran plus le débordement, et la piste se translate de ce même
débordement. On ne détourne pas le défilement, on le réoriente, et la section ne retient pas
le lecteur plus longtemps qu'elle n'a à montrer. Relevé à 1440 : hauteur 2 148 px = 900 d'écran
+ 1 248 de course, piste 2 534 px.

**Tout est en unités de fenêtre, jamais en pourcentage.** Un pourcentage se résout sur le bloc
conteneur de l'élément qui s'en sert : ce piège a déjà coûté trois corrections sur ce dépôt.
Ici gouttière, piste et débordement sont en `vw` et en pixels.

**La première carte part sur la gouttière du site et la dernière s'arrête sur la gouttière
opposée.** Vérifié à 940, 1024, 1280, 1440, 1920 et 2560 px : la carte 1 tombe exactement sur
le logo (écart 0), le bord droit de la dernière carte tombe exactement sur `largeur − gouttière`,
et **aucun débordement horizontal de la page** à aucune largeur.

Deux exemples ont été ajoutés (Robot Framework, JUnit/RestAssured) : à trois cartes il n'y avait
presque rien à faire glisser, et ces deux outils sont déjà annoncés comme compatibles dans le
tableau juste en dessous, avec ces mécanismes exacts.

**Ce qui manquait pour que ce soit fluide et « premium »** (deuxième retour) : une inertie
courte. Le moteur écrit la progression sans lissage, donc la piste suivait le défilement au
pixel ; avec une molette, qui avance par crans, cela se voit comme des saccades. Une
transition de 0,28 s en sortie exponentielle transforme les crans en glissement sans jamais
décrocher du doigt. S'y ajoutent un masque de bords (les cartes se dissolvent au lieu d'être
coupées net, ce qui dit qu'il y a une suite et non un cadre), un halo qui glisse avec la
piste, et un relief de trois pixels sur la carte courante. Pas d'ombre sur cette carte : sur
un fond noir, une grande ombre floue autour d'un cadre sombre se lit comme un rectangle plus
clair, pas comme un relief.

Trois pièges rencontrés, tous corrigés :

- **le masque du média n'a aucun sens sur un objet qui glisse latéralement.** `.code-block` est
  dans la liste `media` du module 4 (masque qui remonte plus passage de lumière) : les cinq
  cartes se révélant au même instant, les cinq éclats se voyaient ensemble, et le masque
  écrêtait les cadres à des hauteurs différentes. Une entrée `plain` placée EN PREMIER dans
  `REVEAL_MAP` gagne, puisqu'un élément n'y prend qu'une variante ;
- **une carte hors du champ n'est jamais « intersectée »**, donc dans le repli à défilement
  horizontal natif (téléphone, mouvement réduit) trois cartes restaient à l'opacité 0 jusqu'à
  ce que le doigt les amène. Signalé par le balayage de non-régression, pas à l'œil. La
  révélation est neutralisée dans ce repli ;
- **sous 940 px et en mouvement réduit, plus d'épinglage du tout** : la bande devient un
  défilement horizontal natif avec accrochage. Épingler une section sur un téléphone est ce
  qui a coûté le plus de corrections sur ce site ; ici le navigateur fait le travail.

Ce qui reste inchangé : l'index du cas courant vient d'un observateur d'intersection à
marges négatives (module 17), pas d'un calcul sur `--ucs-p`. Les deux formules du moteur
divisent une course en parts égales, alors que les pas n'ont pas tous la même hauteur
(78 vh, 62 vh aux extrémités) : l'observateur lit la position réelle des cartes, lui.
Et sous 900 px le schéma disparaît toujours, les cinq cas redevenant une liste.

Contrôlé : 25 pages × (normal, mouvement réduit) × (1440, 390) sans anomalie, 0 défaut de
contraste sur les deux nouvelles pages, un seul `h1`, aucun saut de niveau de titre, aucun
lien interne cassé, hreflang auto-référent des deux côtés, `sitemap.xml` et `llms.txt` à
jour.


## La boule qui dérive, et une passe d'aération (2026-08-20)

### La boule et sa traîne

Demandé d'après linearity.io : « lorsqu'on ne bouge pas de la homepage, il y a dans le fond
une boule, un trail orange qui illumine le site ». Le calque ambiant de ce site
(`body::before/::after`) dérive avec la PROGRESSION dans la page : à l'arrêt il est immobile.
Celui-ci dérive avec le TEMPS.

`.orbz` : trois calques, **une seule animation**, décalée de 2,4 s et de 4,8 s, avec des
tailles et des opacités décroissantes. C'est ce décalage qui fait la traîne, sans une
deuxième trajectoire à écrire. Seul `transform` est animé, donc composité : aucun repeint.
(Le piège est documenté juste au-dessus dans la feuille de style : déplacer le centre d'un
dégradé radial repeint toute la surface et coûtait 14 % des images par seconde sur l'accueil.)

**LES TROIS OPACITÉS SONT UN BUDGET, PAS UN GOÛT.** Les calques se superposent au coeur du
parcours, donc l'opacité résultante vaut `1 − (1−a1)(1−a2)(1−a3)`. Le plafond vient du
contraste : à 30 % de teal sur le noir de la page, `--gray` tombe à 4,67:1, juste au-dessus
du seuil AA, et `--muted` à 3,71, en dessous. D'où 0,21 / 0,065 / 0,03, soit 0,283 au total :
la tête est plus lumineuse qu'un calque unique et le budget tient.

Deux conséquences :

- **le calque ambiant du site est neutralisé là où la boule existe** (`body:has(.orbz)`) :
  sinon les halos s'additionnent et le total repasse au-dessus du plafond. Un seul système de
  fond par page ;
- **deux textes ont changé de gris** parce qu'ils sont posés sur le fond de page, donc sur la
  boule : la note de l'API et le fil d'Ariane passent de `--muted` à `--gray`.

**CE QUI LE RENDAIT INVISIBLE : LES FONDS OPAQUES.** Premier signalement : « je ne vois
aucun halo ». La boule est en `z-index: -1`, donc derrière tout ce qui peint un fond. Relevé
sur la page : l'en-tête de page (320 px de noir plein), la section de l'API (3 001 px de
`#121212`) et le pied de page la masquaient entièrement, soit la moitié de la page dont tout
le haut, là où le visiteur arrive. Sur les pages à boule, ces deux blocs sont donc devenus
translucides : la bande grise garde sa nuance (2,2 % de blanc sur le fond de page donne
`#101010`, à deux points de l'ancien `#121212`) et la boule passe. Le pied de page reste
opaque : c'est la fin de la page.

**PUIS LE HALO A ÉTÉ DEMANDÉ PLUS LUMINEUX ET PLUS FRÉQUENT**, et cela s'est payé :

- **plus lumineux se paie en gris plus clairs.** Un fond plus clair sous un texte gris clair,
  c'est moins de contraste, et il n'y a aucun moyen de contourner cela (un mode de fusion
  éclaircit aussi le fond sous le texte). Le halo est monté à **0,366** d'opacité cumulée, où
  `--gray` d'origine tomberait à 3,9:1. Les deux gris secondaires de CETTE page montent donc
  d'un cran (`--gray: #C9CBCE`, `--muted: #BFC1C4`) : 5,8:1 et 5,2:1 au coeur du halo, et la
  hiérarchie avec les titres (`#E6E7E8`) reste lisible ;
- **plus fréquent, à moitié par la vitesse et à moitié par le parcours** : 24 s au lieu de 34,
  et six étapes au lieu de quatre, donc la boule traverse la fenêtre trois fois par tour au
  lieu d'une. La vitesse apparente reste celle d'une ambiance : les orbes du hero de l'accueil
  avaient dû être ralentis à 22-26 s pour cette raison précise ;
- **la taille fait la présence** autant que l'opacité : 58vw au lieu de 46, soit 835 px sur un
  écran de 1440 au lieu de 660.

**LE PLAFOND EST ATTEINT, ET IL EST FIXÉ PAR LE TEAL SUR LE TEAL.** Demande suivante :
« augmente encore, jusqu'au maximum lisible ». Le facteur limitant n'est pas le gris mais les
libellés de section et les catégories des cas, en `#00CBBE` : à mesure que le fond tend vers
cette même couleur, leur contraste s'effondre deux fois plus vite que celui d'un gris. Calculé :
5,4:1 à 0,30 d'opacité cumulée, **4,5:1 à 0,366**, 3,9:1 à 0,42. Le maximum lisible est donc
0,37, et c'est un calcul, pas un choix. Aller au-delà demanderait d'éclaircir le teal des
libellés (il existe `--teal-tint`), ce qui touche à la charte, ou d'amener les gris secondaires
au niveau des titres, ce qui supprime la hiérarchie. Les deux ont été écartés.

Ce qui reste possible à plafond constant, et qui a été fait : **redistribuer**. Un coeur un peu
moins fort (0,22 au lieu de 0,27), une décroissance beaucoup plus lente (quatre arrêts au lieu
de trois, jusqu'à 84 % du rayon) et une boule plus large (68vw) donnent une surface éclairée
nettement plus grande à luminosité de crête égale. Plus **une traîne le long du bord gauche**,
demandée en plus : une ellipse haute et étroite sur son propre cycle de 38 s, donc jamais en
phase avec les 24 s de la boule — c'est ce qui évite que la page prenne un rythme régulier.
Son opacité (0,09) est calculée pour que le pire recouvrement, coeur de la boule sur la traîne,
vaille 0,363, soit 4,53:1 pour le teal. Elle disparaît sous 700 px : sur un téléphone, une
traîne de bord n'a plus de bord à longer, elle ferait un voile.

Vérifié en forçant le fond de page à la couleur du pire recouvrement sur les 25 pages
(`#065450` là où la boule existe, `#0A3330` ailleurs, qui est le pire cas du calque ambiant) :
**0 défaut de contraste**. C'est la seule façon de contrôler un halo en `position: fixed` — un audit qui
remonte l'arbre des fonds ne le voit pas.

En mouvement réduit la boule ne bouge plus mais **reste allumée** : c'est de la lumière, pas
une animation décorative. Sous 700 px elle est réduite et ralentie (44 s), pour rester un
fond et pas un événement. Le balisage n'existe que sur les deux pages de cas d'usage :
l'accueil a déjà son canevas 3D et ses deux orbes de hero.

### Aération, sur l'échelle de 8 px

Demandé : « aère un peu entre les blocs, utilise les normes d'ergo et d'UX/UI connues ».
Tout reste multiple de 8, et le rythme vertical d'une section se place dans la fourchette
courante de ce type d'interface (80 à 128 px sur écran large) :

| | avant | après |
|---|---|---|
| `--section-py` (large / tablette / téléphone) | 96 / 72 / 56 | **112 / 88 / 64** |
| chapeau de section | 56 | **64** |
| grilles denses (4 et 3 colonnes) | 24 | **32** |
| lignes de fiche technique | 20 | **24** |
| cartes (`.feature-card`, `.product-card`, `.calendly-box`, `.sidebar-card`) | 28 | **32** |
| cas d'usage (marge intérieure / gouttière) | 26-28 / 20-36 | **30-34 / 24-40** |
| matrice de compatibilité | 10 (8 en une colonne) | **14 (12)** |

Effet mesuré à 1440 px : accueil 10 669 → 10 957 px, Caractéristiques 10 215 → 10 619,
commande 6 353 → 6 677, FAQ 2 738 → 2 802. Soit 3 % de hauteur en plus pour un rythme qui
respire.

**La seule contrainte dure que cette passe pouvait casser est la carte de la séquence
épinglée**, qui doit tenir dans un écran. Vérifié à 1440×900, 1280×720, 1024×768, 1440×700 et
1366×640 : la pile fait 352 à 359 px et il reste au minimum 141 px de marge au-dessus comme
en dessous.


## Verre sombre sur les cartes, et le bouton « Copier » sort du code (2026-08-20)

### Le bouton était posé SUR le code

Signalé : les lignes de code passaient sous le bouton « Copier ». C'était structurel, pas un
défaut de marge : le bouton était en `position: absolute` dans le `pre`, donc au-dessus du
texte, **et il défilait avec lui** dès qu'une ligne dépassait. Un rembourrage à droite n'aurait
rien réglé — sur un bloc à défilement horizontal, la ligne repasse sous le bouton dès qu'on
fait glisser.

Le bloc a désormais un **bandeau** : le nom de l'outil à gauche, l'action à droite, le code en
dessous. Le problème disparaît par construction et le bloc a l'allure d'un panneau. Le module
7 bis pose le bouton dans le bandeau quand il en trouve un (`figure > figcaption`), et garde
le coin supérieur droit ailleurs, faute de bandeau où le mettre. Relevé après : recouvrement
de −28 px (donc aucun) sur les cinq blocs.

Deux réglages qu'il a fallu chercher :

- le sélecteur du `pre` transparent doit porter `[data-theme="dark"]`, parce que la règle
  générale du verre en fait autant : à poids égal c'est l'ordre qui tranche, et le bloc du
  verre est écrit plus loin dans le fichier. Sans cela un rectangle plus sombre réapparaissait
  à l'intérieur du cadre ;
- `align-self: stretch` annule le `align-self: start` de la règle de base de `.code-block` :
  dans la colonne flex de la figure, il faisait rétrécir le bloc à la largeur de son texte
  (282 px sur 460) et le verre du cadre débordait autour du code.

### Le verre : sombre, et c'est un calcul

Demandé « un peu de Glassmorphic-Aurora sur le site au global et les blocs de code ». Les
surfaces de carte passent du noir plein au **verre sombre** : fond translucide plus flou
d'arrière-plan, si bien que le halo qui dérive derrière la page traverse les cartes, en flou.

**POURQUOI SOMBRE ET NON CLAIR.** Le glassmorphisme habituel pose du blanc translucide.
Calculé sur ce site : une carte en blanc à 4,5 % posée sur le coeur du halo donne un fond à
`#115C58`, où le teal des catégories tombe à **3,8:1** et le gris sourd à 4,3 — sous le seuil
AA, et ce sont précisément les deux couleurs qui vivent DANS les cartes. Une base sombre à
62 % fait l'inverse : le fond de carte reste à `#0F2A28` au pire, le teal tient **7,5:1** et le
gris sourd 8,4, et l'aurore se voit quand même puisque 38 % du halo passe au travers.

**LE FLOU EST CE QUI FAIT LE VERRE**, pas la transparence : sans lui on verrait le halo net
derrière un voile, ce qui ressemble à une erreur d'opacité. `saturate(130%)` compense la
désaturation du flou. Les blocs de code sont plus opaques (72 %) : on y lit du texte à 13 px
en chasse fixe, c'est la surface la moins tolérante de la page.

Repli explicite en `@supports not (backdrop-filter)` : fond opaque, comme avant. Une carte
translucide sans flou serait moins lisible qu'une carte opaque.

**Contrôles.** Contraste : fond de page ET fond de carte forcés à leur pire composite
(`#065450` / `#0F2A28` là où la boule existe, `#0A3330` / `#101D1C` ailleurs) sur les
25 pages → **0 défaut**. Rendu : médiane 16,7 ms et p95 17,6 ms avec et sans verre sur
`cas-usage`, l'accueil (canevas 3D compris) et `caracteristiques`, donc **aucun coût en
régime**. Une seule image longue apparaît avec le verre (150 ms contre 50) : c'est la
création des couches de flou, une fois, à l'entrée en scène.

## Le prix quitte le site, les rendus IA aussi (2026-08-24)

Deux retours client, traités ensemble : « modifier le prix et/ou l'enlever », et
« changer les images du site, mettre des photos et vidéos, faire des choses plus handmade
et enlever les versions IA ».

### 1. Le tarif n'est plus prononcé, il est retourné en ROI

**ARBITRÉ PAR LE CLIENT LE 2026-08-24, deux décisions.** Le montant disparaît des
40 emplacements où il vivait, et les deux blocs tarifaires de `commandez` / `order`
sont remplacés par un **calculateur de ROI à deux curseurs**. La page, elle, **devient
la page « Démo »** : sans prix, une page « Commandez » se lit comme une page inachevée.

Trois options ont été proposées et écartées, il ne faut pas les ressortir :

- **un calculateur à trois curseurs** (testeurs, minutes, coût horaire), qui donnait un
  résultat en euros. Le client a tranché pour deux ;
- **une carte « ce que ça vous rend »** (0 intervention humaine, les suites tournent la
  nuit, 2FA franchie en moins de 10 s) ;
- **l'ancrage « moins de deux jours de test manuel par mois »**, que j'avais signalé comme
  à écarter : il laisse déduire l'ordre de grandeur, donc il prononce le prix quand même.

**Le calculateur ne montre AUCUN chiffre de Q-Bot.** Il demande deux chiffres au visiteur
(testeurs mobilisés par la 2FA, temps perdu par jour et par personne) et lui rend ce que
la 2FA lui coûte déjà : `testeurs × minutes × 21 jours ouvrés`, en heures puis en journées
de test (`÷ 7 h`). Quatre choses à ne pas défaire :

- **le résultat est en heures et en journées, jamais en euros.** Convertir demanderait un
  coût horaire, donc un troisième curseur (écarté par le client) ou une hypothèse inventée
  de notre part. Le lecteur applique son propre taux s'il le veut : ce sera SON chiffre ;
- **aucun tarif affiché, donc aucune promesse de « rentabilisé en X mois ».** C'est
  précisément ce qui rend le bloc défendable ;
- **la formule est affichée sous le résultat.** Un grand nombre sans son calcul est un
  argument publicitaire ; avec son calcul, c'est une mesure ;
- **les bornes sont plausibles** (1-20 testeurs, 5-120 min). Sans bornes, un visiteur
  atteint des totaux absurdes et le calculateur devient invérifiable.

**L'état au repos est l'état complet** : les valeurs écrites dans le HTML (3 testeurs,
35 min, 36 h 45, 5,3 journées) sont exactement celles que produit le calcul aux positions
par défaut, et `--roi-p` est posée en style en ligne pour que la portion remplie du rail
soit juste elle aussi. Sans JavaScript le bloc se lit correctement, il ne réagit plus.
Module **17** de `main.js` (le numéro était libre : l'ancien module 17, l'observateur des
bandes d'outils, avait été supprimé le 2026-08-20).

Un piège de moteur à connaître : **la portion teal du rail se code deux fois.** Firefox a
`::-moz-range-progress`, qui remplit seul ; WebKit et Chromium n'ont pas d'équivalent, la
portion y est un dégradé sur la piste borné par `--roi-p`, écrite en JavaScript. Les deux
blocs de pseudo-éléments ne peuvent PAS être groupés : un sélecteur inconnu invalide la
déclaration entière pour le moteur qui ne le connaît pas.

Ce qui a été repris ailleurs, parce que le prix y vivait aussi :

- **JSON-LD, 8 pages** : `Offer` perd `price`, `priceCurrency` et tout
  `priceSpecification`, et gagne `"businessFunction": "https://schema.org/LeaseOut"`. Un
  `Offer` sans prix reste valide ; il n'est simplement plus éligible au résultat enrichi,
  ce qui est exactement l'intention. `LeaseOut` remplace l'information au lieu de la
  supprimer : c'est la propriété schema.org qui dit « location, pas vente » ;
- **titres et métadonnées sociales** de `commandez` / `order` (6 champs chacune) ;
- **la FAQ**, question 9 des deux langues. La question « Combien coûte Q-Bot ? » RESTE :
  c'est celle qu'on pose, et la supprimer ne ferait pas disparaître la curiosité. C'est la
  réponse qui change, et elle dit ce qui est vrai : location mensuelle tout compris, sans
  engagement, tarif donné en démonstration. Texte visible et JSON-LD partagent la même
  phrase, donc un seul remplacement corrige les deux ;
- `llms.txt`, où le prix devient **« NOT PUBLISHED, on purpose »** avec la consigne
  explicite de ne pas l'inférer : un agent qui lit ce fichier doit savoir que tout montant
  attribué à Q-Bot est une invention ;
- le **gabarit d'article de `admin/index.html`**, dont la barre latérale affichait le prix ;
- les libellés de navigation des 25 pages : « Commander » / « Order Q-Bot » → « Démo » /
  « Demo », et les appels à l'action des pages contact et 3D. **Les URL ne changent pas**
  (`commandez.html`, `en/order.html`), donc aucun lien cassé, aucun `hreflang` à reprendre.

Contrôle : `grep -rn '850'` ne remonte plus rien hors du sidecar base64 du modèle 3D, et
`document.body.innerText` des 25 pages ne contient plus le montant.

### 2. Les rendus IA sont partis, deux vraies photos les remplacent

Tous les visuels produit du site étaient des rendus génératifs, y compris les deux
« visuels fournis par le client » du 2026-08-18. Le signe est net sur chacun : le mot
**Q-BOT gravé sur le boîtier est illisible ou déformé**, ce qu'aucun rendu de la CAO ne
fait.

**LA SOURCE DES VRAIES PHOTOS EST `Documentations/Brochure Q-Bot-FR.pdf`.** Elle en contient
deux, et personne ne les avait vues : les pages du PDF sont **aplaties en une seule image
raster de 2481 × 3510 (300 dpi)**, donc `get_images()` ne rend que des pages entières et il
faut découper dedans. `pymupdf` suffit ; inutile de demander un rendu à plus de 300 dpi,
c'est la résolution réelle du fichier et au-delà on ne fait qu'agrandir.

| Fichier produit | Découpe | Où |
|---|---|---|
| `qbot-photo-poste.jpg` (1400 × 840) | page 3, x 130-2353 y 286-1404, recadré en 5/3 | hero des deux accueils, section produits de `a-propos` / `about` |
| `qbot-og.jpg` (1200 × 630) | la même, cadre entier ramené en 1,905 | `og:image` / `twitter:image` / JSON-LD des 25 pages |
| `qbot-photo-dock.jpg` (699 × 860) | page 1, x 1566-2225 y 438-1238 | section LuxTrust des accueils, section « Fonctionnement » de `commandez` / `order` |

La photo du poste de travail est **recadrée en 5/3 et non laissée en 1,99** : au ratio
d'origine le cadre du hero ne faisait plus que 266 px de haut dans une colonne de 533, le
premier écran se vidait. En 5/3 le boîtier est deux fois plus grand et l'écran du téléphone
devient lisible ; ce qui sort du cadre est le bord droit du moniteur, qui n'a pas de bordure
visible à cet endroit et se lit donc comme continuant hors champ.

Trois pièges rencontrés sur ces découpes :

- **le liseré teal des angles arrondis.** La carte de la page 1 est posée sur la bande teal
  de la brochure : le recadrage emporte quatre triangles teal. Les repeindre en blanc
  demande un masque **serré ET limité au pourtour**. Un premier essai à seuil large
  (distance somme < 190, sur toute l'image) a **blanchi une partie du logo LuxTrust** du
  téléphone, dont le bleu est à 174 de distance du teal. Le bon réglage est seuil < 90 et
  26 px de marge : 1 211 pixels touchés, logo intact ;
- **la sur-échelle de `.intro__image` rognait la pastille « MADE IN LUXEMBOURG ».** Le cadre
  agrandit son image de 8 % au repos et de 13 % au survol pour masquer ses bords pendant le
  parallaxe, ce qui, sur une photo dont un coin porte une étiquette, coupe l'étiquette. Le
  correctif n'est PAS de désactiver la sur-échelle (le contre-parallaxe interne en a besoin,
  cf. `.intro__image:not(.intro__image--product) img`) mais **d'ajouter la marge qui manque
  dans le fichier** : 20 px à gauche et à droite, 60 px en bas, par **réplication de bord**
  et non par aplat, la marge de la carte étant un dégradé lisse ;
- **une photo à fond clair sur une page noire a besoin d'une vignette.** D'où
  `.hero__shot`, qui reprend le traitement de `.hero__film` (angles arrondis, filet teal,
  vignette intérieure) sans imposer d'`aspect-ratio` : c'est l'image qui donne le sien. Et
  **il ne bouge pas** : ni parallaxe ni inclinaison au pointeur, c'est la leçon déjà écrite
  pour le film (un cadre qui dérive se lit comme un cadre instable).

**Le film produit est de retour dans la page.** `assets/video/qbot-home.mp4` n'était plus
référencé nulle part depuis que le hero avait repris un visuel fixe. Il revient dans la
section « 100 % conçu et développé au Luxembourg », qui passe de bloc de texte pleine
largeur à deux colonnes. **En lecture à la demande, et c'est le point** : zéro octet
transféré tant que le visiteur ne clique pas. En lecture automatique le film ajouterait
2,9 Mo aux 2,4 Mo acceptés le 2026-08-11 pour l'accueil, soit un doublement du poids pour
un film muet de 8,7 s. C'est aussi ce qui rend le **module 14** (garde-fou mouvement
réduit / économiseur de données) sans objet sur cette page : rien ne part tout seul.
L'affiche est une vraie image du film, capturée du film lui-même à 7,4 s.

**IL N'Y A PAS DE BALISE `<video>` DANS LA PAGE, ET C'EST DÉLIBÉRÉ.** Première version :
un `<video preload="none" controls>` sans `autoplay` ni `loop`. Signalé le 2026-08-24 :
chez le client **le film démarrait seul et tournait en boucle**. Irreproductible ici,
mesuré sur les deux moteurs (`paused: true`, `readyState: 0`, `loop: false`,
`autoplay: false` pendant six secondes sous Chromium comme sous WebKit), donc la cause est
un réglage de navigateur ou une extension. Ajouter des attributs n'aurait servi à rien :
l'absence de `autoplay` est déjà la façon la plus explicite de dire non, un booléen absent
ne peut pas l'être davantage.

Ce qui règle la question pour de bon, c'est **qu'il n'y ait rien à démarrer** : le balisage
porte un LIEN vers le fichier, habillé de l'affiche, d'une pastille de lecture et de la
durée. Le **module 18** de `main.js` le remplace par un `<video>` au clic, et **remet
l'affiche à la fin de la lecture**, ce qui exclut aussi la boucle. Trois conséquences :

1. la lecture partant d'un clic, `autoplay` sur l'élément créé est légitime et fonctionne
   partout : c'est un geste utilisateur, aucune politique de lecture automatique ne s'y
   oppose ;
2. la promesse de poids devient structurelle et non plus une indication au navigateur.
   Vérifié : aucune requête vers le `.mp4` avant le clic, sur les deux moteurs ;
3. **sans JavaScript le lien reste un lien** et le film s'ouvre dans le lecteur natif. La
   règle du dépôt (l'état au repos est un état complet) vaut aussi pour un média.

Le focus passe sur le lecteur à sa création et revient sur l'affiche à la fin : sans cela,
un visiteur au clavier active un lien qui disparaît et son focus retombe sur le document.

Un défaut introduit puis corrigé dans la même passe : la mention de durée était en blanc
avec une ombre portée, posée sur le gris CLAIR du rendu, soit **1,2:1**. Une ombre de texte
améliore la perception et ne change rien à la mesure. Elle est désormais sur une pastille
noire à 66 %, ce qui donne **8,43:1** mesuré.

Le cadre `.video__wrapper--film` annule le `max-width: 800px` et le `margin: 0 auto` de la
règle de base : dans une colonne de `.intro__grid`, le centrage empêcherait les deux
colonnes de commencer sur la même ligne de base. Sa vignette est en `pointer-events: none`,
sans quoi elle avalerait les clics destinés aux contrôles de lecture.

**Fichiers supprimés** (aucun n'était plus référencé) : `qbot-hero.webp`,
`qbot-solution.jpg`, `qbot-luxtrust.jpg`, `products-lineup.jpg`, `qbot-video-poster.jpg`,
`QBIllu1.png`. Les masters IA restent archivés sous `Documentations/assets-sources/`
(`qbot-render-a/b/c-source.png`, `qbot-luxtrust-client-source.png`,
`qleap-products-client-source.png`) parce qu'ils documentent ce qui a été fourni : **ne pas
les remettre en ligne.**

**Ce qui reste et n'est PAS de l'IA**, pour ne pas le « corriger » par excès de zèle :
`qbot-specs.jpg` et `qbot-gen-actuelle.webp` sont des rendus de `assets/models/qbot.glb`,
donc de la géométrie authentique (cf. `tools/render/`) ; `qbot-proto-gen1.png` et
`device-photo.jpg` sont de vraies photographies du prototype à portique ;
`qbot-interface.jpg` est une maquette HTML/CSS capturée, signalée comme telle depuis le
2026-08-11 ; les images des articles de blog viennent du live WordPress. Il n'y a plus qu'un
seul visuel de synthèse par page d'accueil, contre trois avant.

### 3. Défaut de contraste trouvé au passage : blanc sur teal, encore

Le balayage de contraste (fonds forcés au pire composite, méthode du 2026-08-20) a remonté
**16 défauts à 2,04:1** sur `commandez` / `order` : les ronds numérotés des sections
« Opérationnel en 4 étapes » et « Comment Q-Bot automatise votre 2FA », en `--white` sur
`--teal`. Antérieurs à cette passe, et c'est exactement le piège documenté depuis le
2026-08-11 (**le teal de charte est une couleur CLAIRE, le blanc plafonne à 2:1 dessus**),
qui avait déjà été corrigé sur la bande newsletter et l'ancienne pastille de prix. Passés au
noir `#001A18` (≈ 11:1), dans la feuille de style pour `.order-step__number` et dans les
huit styles en ligne des deux pages.

Les 18 remontées restantes sont expliquées et laissées : dix boutons « Copier » (artefact de
la sonde, qui compose mal deux couches translucides ; les valeurs réelles donnent ≈ 8:1),
six numéros d'étape encore à venir de la séquence 3D (état inactif volontairement estompé,
exempté par la WCAG) et deux libellés teal des pages de cas d'usage, à 4,3 contre le plafond
de 4,5 calculé pour le halo ; l'écart est celui du modèle, la sonde forçant partout un pire
cas qui ne se produit jamais sur toute la page.

**Contrôles de la passe** : 25 pages × (normal, mouvement réduit). Aucun débordement
horizontal, aucun `.reveal` resté invisible, aucune erreur console, aucune requête en échec,
un seul `h1` par page. Calage vérifié à 1280 / 1440 / 1920 / 2560 px : le titre et les
panneaux du calculateur tombent au pixel sur le logo. Mise en page contrôlée à 375, 390,
768, 900, 901, 1024, 1280, 1920 et 2560 px.

## Étape 1 de l'audit RosoAI : les erreurs de contenu (2026-08-24)

`Documentations/Audit_Q-Bot_Note_Strategique.pdf` (RosoAI, 24 août 2026) est un audit SEO
et visibilité IA en 21 pages. Il est traité par étapes ; celle-ci corrige les erreurs
factuelles, qui ne demandaient aucune décision de contenu neuf. Chaque constat a été
revérifié dans le dépôt avant correction, parce que l'audit a été produit à 8h45 et que la
passe prix / images de l'après-midi l'a partiellement périmé.

**UN POINT DE L'AUDIT EST À ÉCARTER, ET IL FAUT LE SAVOIR.** Sa « faille 4 » demande
d'afficher « 850 €/mois HT » sur la page d'accueil, au motif que le prix n'existait que
dans le JSON-LD. Le client a tranché l'inverse le même jour : le tarif ne doit plus être
prononcé, et il a été retiré du JSON-LD aussi. La prémisse de cette faille n'est donc plus
vraie non plus. **Ne pas la « corriger » en republiant le prix** ; le calculateur de ROI
répond d'ailleurs à la ligne P3 du plan de contenu de l'audit, « Combien coûte l'étape
manuelle d'authentification ? ».

Ce qui a été corrigé :

- **la carte Q-Bot de « À propos » décrivait Q-Guard**, mot pour mot, depuis le commit
  initial. Elle décrit maintenant Q-Bot, alignée sur la carte anglaise (qui, elle, était
  juste) ;
- **l'ancienneté se contredisait** : « plus de 10 ans » à cinq endroits, « plus de 13 ans » à
  un sixième. Tout passe à **« depuis 2012 »** (date confirmée par le client le
  2026-08-24). Une date fixe ne périme pas, un nombre d'années vieillit à chaque janvier.
  L'anglais avait le même défaut plus un oubli : `en/technical-specs.html` disait encore
  « for over 10 years », hors du périmètre où j'avais cherché d'abord ;
- **trois délais de mise en service coexistaient** : « le jour même » dans le hero de la page
  démo, « 24h » dans les trois métadonnées sociales, « 48 à 72 heures » dans le processus et
  dans la FAQ. Tout passe à **48 à 72 heures** (arbitrage client, la valeur la plus prudente
  et déjà la plus présente). **Attention à ne pas confondre avec le délai de réponse de
  l'assistance, « sous 24h ouvrées »** : c'est une autre grandeur, elle est juste, elle reste ;
- **deux sur-promesses en « 100 % »**. La page d'accueil annonçait « Automatiser la double
  authentification dans 100 % des cas de tests » alors que Q-Bot pilote un appareil ANDROID,
  ce que sa propre FAQ dit. Remplacé par le périmètre réel, qui est déjà assez fort :
  « Toutes vos applications Android, y compris LuxTrust, itsme, Microsoft Authenticator et
  Google Authenticator. » Et `en/index.html` promettait encore « 100% effective (perfect
  recognition rate) » ;
- **deux restes du récit caméra que les lots 1 et 2 du 2026-08-19 avaient laissés** :
  « La précision est parfaite, au pixel près » dans la FAQ française (texte visible ET
  JSON-LD) et « une précision parfaite » dans l'aperçu FAQ de l'accueil. Il n'y a plus rien
  à reconnaître, donc plus de précision à revendiquer : c'est le déterminisme qui est
  l'argument. L'anglais avait déjà été repris, le français y avait échappé, **encore une
  fois parce que le motif de contrôle portait sur le vocabulaire anglais**.
- **une coquille dans un titre d'article** : « Qu'est-ce qu'**est** l'authentification à deux
  facteurs ? ». Elle vivait à **huit endroits** et non un seul : le `<title>` de l'article,
  ses trois métadonnées sociales, son `headline` JSON-LD, son `h1`, l'index du blog, les deux
  blocs « articles liés » des autres articles, et `llms.txt`. Corriger le plus visible aurait
  laissé la faute dans l'onglet du navigateur et dans tous les partages.

**`llms.txt` gagne deux faits qui manquaient**, et c'est le fichier que les IA lisent en
premier : le périmètre **énoncé comme une limite** (« drives an ANDROID device, does not
automate 2FA on iOS », avec la consigne de ne jamais écrire « 100% of test cases ») et le
délai de 48 à 72 heures, avec la mise en garde sur les 24 heures du support. L'audit relève
justement que le périmètre Android n'était présenté comme une limite nulle part, et zéro fois
dans ce fichier.

Contrôlé : 65 blocs JSON-LD valides, `document.body.innerText` des 10 pages touchées contient
bien les nouvelles formulations, aucune erreur console, et les quatorze motifs fautifs
remontent tous à zéro occurrence.

## Étape 2 de l'audit : les réponses-capsules (2026-08-24)

La faille 2 de l'audit RosoAI : le site pose des titres formulés en question, ce qui est le
bon format pour être cité, mais aucun n'est suivi d'une réponse autonome de 40 à 60 mots.
Mesuré avant : **26 titres en question, zéro conforme.** L'audit avance que 72,4 % des pages
citées par ChatGPT contiennent une telle réponse.

**SEIZE DE CES VINGT-SIX SONT DES APPELS À L'ACTION**, et il ne faut PAS leur écrire de
capsule : « Prêt à en finir avec la dernière étape manuelle ? », « Vous souhaitez en savoir
plus ? ». Une invitation n'a pas de réponse de cinquante mots, et lui en coller une la
transformerait en paragraphe au milieu d'un bloc de conversion. Restent **dix questions
informatives**, dont huit sont traitées ici.

Les huit capsules sont posées **sans un octet de balisage ni de CSS nouveau** : dans sept cas
sur huit elles remplacent le contenu d'un `.section-subtitle` ou d'un `<p>` existant. C'est
volontaire, l'accroche d'une section n'a aucune raison d'être un fragment décoratif quand elle
peut être la réponse à la question qui la surplombe. Vérifié après : 8 sur 8 entre 42 et
55 mots, 5 lignes à 600 px de mesure, alignées au pixel sur la gouttière du logo.

Deux exclusions assumées : les deux dernières questions informatives sont des **titres de
carte** sur les index de blog, suivis de l'accroche de la carte (25 et 19 mots). Allonger
l'accroche d'une carte à cinquante mots casserait la grille et ne répond pas à l'intention de
l'audit. La question elle-même est traitée là où elle se pose vraiment, dans l'article.

### Les FAQ : la capsule, c'est le PREMIER paragraphe

Les 32 réponses de FAQ ne sont pas des titres, elles ont donc échappé au comptage de l'audit,
mais elles sont le contenu le plus citable du site. Ce qui compte y est différent : c'est le
premier paragraphe qui doit se suffire, parce que c'est lui qui sera recopié. Mesuré sur les
deux langues : la moitié des réponses ouvrent sur moins de 30 mots pour un total qui va
jusqu'à 169.

Deux ont été reprises, les deux plus citables :

- **« Qu'est-ce que Q-Bot ? »**, ouverture à 25 mots pour 100 au total. C'est la question la
  plus citable du site entier. Portée à 51 mots, avec le comment (boîtier sur un bureau,
  téléphone Android en USB, déclenchement par appel HTTP) ;
- **« Pourquoi Q-Bot est le parfait allié des testeurs ? »**, ouverture à 17 mots pour 169, et
  surtout une ouverture qui **ne répondait pas à la question** (elle définissait le métier de
  testeur). Une capsule de 47 mots est posée devant, l'ancienne ouverture devient le deuxième
  paragraphe : rien n'est perdu.

**LE PIÈGE DE LA FAQ, DEUX FOIS DANS LA MÊME PASSE.** Chaque réponse existe en double, texte
visible et `FAQPage` JSON-LD. En français les deux copies partagent la même chaîne, donc un
seul remplacement les tient synchronisées ; **en anglais elles ne partagent RIEN**, parce que
le texte visible porte des `<strong>` et que le JSON-LD a un espacement différent
(« device . » avec une espace avant le point). Il faut donc deux remplacements distincts, et
c'est exactement l'écart qui désynchronise une FAQ si on l'oublie. Contrôle ajouté : un
relevé qui compare, question par question, les 60 premiers caractères du JSON-LD à ceux du
texte rendu. **32 sur 32 alignées.**

Le même fragment de Q1 vit aussi dans l'aperçu FAQ de la page d'accueil française : le
remplacement partagé l'a mis à jour du même coup, ce qui est le comportement voulu.

### Deux défauts trouvés en mesurant, et corrigés

- **LA COQUILLE DE L'ÉTAPE 1 AVAIT UN HUITIÈME EMPLACEMENT, INVISIBLE À MA RECHERCHE.** Le
  `<h2>` du corps de l'article 2FA écrit « Qu’est-ce qu’est » avec des **apostrophes
  typographiques** (U+2019), alors que le titre et les métadonnées les écrivaient droites
  (U+0027). Une recherche de la version droite ne pouvait pas le voir, et annonçait donc zéro
  occurrence restante. C'est la troisième fois que ce dépôt se fait prendre par la même
  famille de piège : le cadratin écrit `&mdash;`, l'emoji écrit `&#128272;`, et maintenant
  l'apostrophe typographique. **Un contrôle de texte doit porter sur toutes les graphies du
  même caractère**, pas seulement sur celle qu'on a tapée.
- **les six encadrés d'article revendiquaient encore du matériel** : « automatiser la 2FA, y
  compris via des dispositifs physiques comme LuxTrust ». Le lot 2 du 2026-08-19 avait retiré
  cette revendication du site et annoncé 0 occurrence ; elle avait survécu dans les barres
  latérales, que sa recherche ne couvrait pas. Ce n'est pas de la prose d'article datée, c'est
  un argument produit, donc il se corrige : « le seul robot du marché à piloter la vraie
  application 2FA sur un téléphone Android resté sur votre réseau ». La formulation garde
  l'exclusivité, que l'audit établit par ailleurs, mais sur le bon objet.

Au passage, le sous-titre « Quels sont les facteurs d'authentification ? » de l'article 2FA
reçoit lui aussi sa capsule, dans les deux langues.

**Ce qui reste ouvert pour une étape 2 bis** : les quatorze autres réponses de FAQ dont
l'ouverture fait moins de 35 mots, dont trois qui font moins de 25 mots au total
(« Puis-je bénéficier d'une assistance technique ? » en fait 7). Ce sont des réponses justes
mais trop courtes pour être reprises telles quelles. À faire quand le client le voudra ; ce
n'est plus une correction de défaut, c'est de la rédaction.

## Étape 3 de l'audit : le nom composé, et l'identité raccordée (2026-08-25)

Les failles 6 et l'axe 3 de l'audit RosoAI. La faille 6 est mesurée, pas supposée : à la
question « Qu'est-ce que Q-Bot ? », une IA décrit le produit **en quatrième position**,
derrière un gestionnaire de file d'attente GitHub, une société britannique de robotique
d'isolation primée par la reine, et l'ancien système de file d'attente de LEGOLAND. Sur
YouTube, les dix premiers résultats pour « Q-Bot » sont tous la société britannique. Il n'y
a pas à changer de nom, il y a à ne jamais l'employer seul.

**CE QUI ÉTAIT DÉJÀ FAIT, ET QUE L'AUDIT DEMANDE POURTANT** : « tu nommes Sylvain Perez sur
le site ». Il l'est déjà, dans le contenu visible des deux FAQ, des deux pages démo et de
quatre articles, y compris comme « créateur de Q-Bot et CEO de Q-Leap ». Ce qui manquait,
c'est uniquement sa présence dans les données structurées. Contrôler avant de corriger a
évité une réécriture inutile.

### Le nom, dans les titres

**Cinq titres portaient « Q-Bot » seul**, sans Q-Leap ni LuxTrust : les deux index de blog
et de cas d'usage, et les deux FAQ. Les quatre autres titres que ma première recherche avait
signalés satisfont en fait la règle **par LuxTrust** (« Caractéristiques techniques de Q-Bot |
Robot 2FA LuxTrust ») : l'audit accepte « Q-Bot by Q-Leap » **ou** « Q-Bot LuxTrust ». Le
prédicat de contrôle est donc « contient Q-Bot ET ni Q-Leap ni LuxTrust », pas « ne contient
pas Q-Leap ». Sans cette nuance on réécrit quatre titres pour rien.

Les six titres d'article, eux, ne contiennent pas « Q-Bot » du tout : rien à qualifier.

**Contrainte dure : 62 caractères d'affichage en recherche.** « Blog QA : tests logiciels,
automatisation, 2FA | Q-Bot by Q-Leap » en fait 63, d'où une formulation raccourcie plutôt
qu'un titre tronqué en SERP. Les métadonnées sociales des cinq pages suivent le titre, sans
quoi le partage et la recherche raconteraient deux choses différentes.

**Deux descriptions repassaient au-dessus de 158 caractères** (163 et 159), dont une que
j'avais moi-même réécrite la veille en retirant le prix. Corrigées. La règle du dépôt vaut
aussi pour mes propres réécritures.

### Le nom, dans les données structurées

Le `Product` des 8 pages qui en portent un s'appelait « Q-Bot ». Il s'appelle désormais
**« Q-Bot by Q-Leap »**, avec `alternateName: "Q-Bot"`. Ce n'est pas une invention marketing :
c'est le lockup de la charte, « Q-BOT / POWERED BY Q-LEAP ». `alternateName` garde le nom
court trouvable.

L'`Organization` des 25 pages gagne cinq choses, toutes vérifiables :

- `legalName: "Q-Leap S.A."` (page de garde de l'audit) ;
- `foundingDate: "2012"` et `foundingLocation` à Bertrange, ce qui ancre l'entité dans le
  temps et dans un lieu. C'était l'incohérence corrigée à l'étape 1, désormais lisible par
  une machine ;
- `founder`, un `Person` nommé Sylvain Perez avec son `jobTitle`. C'est la pièce qui manquait
  pour que le graphe se ferme : le site le nommait en clair, aucune machine ne pouvait le
  relier à l'entreprise ;
- `knowsAbout`, six domaines (test logiciel, automatisation de tests, assurance qualité,
  double authentification, LuxTrust, Selenium). C'est la propriété qui dit à une IA de quoi
  l'entité parle, et elle coûte six lignes.

`alternateName: "Q-Bot"` est **conservé** sur l'Organization, alors qu'il confond en apparence
la société et le produit. C'est délibéré : c'est précisément le lien que l'audit veut voir, et
maintenant que `legalName` est présent, il se lit comme un « également connu sous le nom de »
plutôt que comme une identité.

`sameAs` **reste à un seul compte, et c'est définitif** : le client a confirmé le 2026-08-25
que **LinkedIn est le seul compte actif** (`https://www.linkedin.com/company/q-leap`) et que
les deux autres relevés sur le live en juillet 2026 (`facebook.com/QLeapSa`,
`twitter.com/qleap_sa`) ne le sont plus. **Ne pas les rajouter** : un `sameAs` qui pointe vers
un profil mort est pire que pas de `sameAs`, il casse la confiance dans tout le bloc. La note
de juillet qui les présente comme « les vrais » a été annotée en conséquence, plus haut dans
ce fichier. Il reste une seule chose à ajouter le jour où elle sera fournie : l'URL LinkedIn
de Sylvain Perez, qui donnerait un `sameAs` sur la `Person` et fermerait le dernier maillon
du graphe.

### Et le fichier que les IA lisent en premier

`llms.txt` reçoit une entrée **DISAMBIGUATION** qui nomme les trois homonymes et dit
lequel est le bon, avec la consigne explicite de citer « Q-Bot by Q-Leap » et jamais « Q-Bot »
seul. C'est l'endroit le plus direct pour régler la faille 6 : plutôt que d'espérer qu'une IA
déduise la bonne entité, on le lui écrit. Le fondateur y est nommé aussi.

Contrôlé : 65 blocs JSON-LD valides, 0 titre au-delà de 62 caractères, 0 description au-delà
de 158, 0 titre où « Q-Bot » reste seul, et les 25 pages passent le balayage normal et
mouvement réduit sans anomalie.

## Étape 4 de l'audit : le blog n'est plus figé au 2 mars 2023 (2026-08-25)

La faille 7 de l'audit : les six articles déclarent tous `datePublished: 2023-03-02`, la même
date, ce qui signale un import en masse, et aucun ne déclare de date de modification. Or le
contenu cité par les assistants IA est en moyenne 25,7 % plus frais que la moyenne, et
Perplexity privilégie nettement le contenu de moins de douze mois.

**L'AUDIT SE TROMPE SUR UN POINT, VÉRIFIÉ AVANT DE CORRIGER.** Il affirme que « tes trois
articles français affichent bien leur date en clair et précisent honnêtement que le produit a
évolué depuis. Tes trois articles anglais ne le font pas. » Les six l'ont, en réalité : la note
de transparence a été posée sur tous le 2026-08-19. Contrôlé à l'écran, elle est visible sur
les six. Rien à faire de ce côté.

### Ce qui bloquait vraiment le tampon de date

L'audit prévient, à juste titre, que **modifier une date sans modifier le texte est un signal
trompeur**. Or quatre articles annonçaient encore une feuille de route périmée : « Dans sa
seconde version qui arrivera prochainement, Q-Bot saura également prendre en charge la totalité
des tokens « physiques » du marché ainsi que les smartcard. Enfin, une version dédiée à la
double authentification via une application mobile sera également développée. » Les tokens
physiques sont hors périmètre depuis l'arbitrage du 2026-08-19, et la version smartphone **est**
le produit d'aujourd'hui. Estampiller une date de modification par-dessus une promesse fausse
aurait été pire que ne rien faire.

**ARBITRÉ PAR LE CLIENT LE 2026-08-25 : la promesse devient une livraison tenue.** Les tokens
physiques disparaissent, et l'annonce de la version mobile devient « Cette version dédiée à la
double authentification par application mobile, annoncée ici, est aujourd'hui le produit :
Q-Bot pilote la vraie application 2FA sur un téléphone Android relié en USB. » L'article garde
son récit, le lecteur voit que la feuille de route a été exécutée, et rien de faux ne subsiste.
C'est la première fois qu'on touche à la prose datée des articles ; le reste du vocabulaire
« token » reste la question ouverte notée plus haut dans ce fichier.

**ET LE MOTIF ÉCRIT À LA MAIN N'A PAS COLLÉ, POUR LA MÊME RAISON QU'À L'ÉTAPE 2.** Le français
encadre « physiques » avec des **espaces insécables** (U+00A0), invisibles à la relecture : ma
chaîne retapée ne correspondait à rien, et seule la version anglaise s'est appliquée. Le
correctif est de **lire la chaîne dans le fichier** (`re.search` puis remplacement de la
capture) au lieu de la retaper. Troisième variante du même piège en deux jours, après le
cadratin écrit `&mdash;` et l'apostrophe typographique : **on ne retape pas une chaîne existante
d'un fichier, on l'extrait.**

### Les dates, lisibles par une machine ET par un humain

- `dateModified: "2026-08-25"` dans le `BlogPosting` des six articles ;
- la date de publication visible passe de `<span>` à **`<time datetime="2023-03-02">`**, et une
  quatrième entrée de méta apparaît, « Mis à jour le 25 août 2026 » / « Updated 25 August
  2026 », elle aussi en `<time>`. Le JSON-LD suffirait à un moteur, mais Perplexity et les
  agrégateurs lisent aussi le texte rendu : la date doit être aux deux endroits, et elle doit y
  dire la même chose.
- `llms.txt` gagne un paragraphe en tête de sa section Blog : les six articles datent du
  2023-03-02, ils ont été relus le 2026-08-25, chacun porte une note disant ce qui a changé, et
  **il faut citer les pages techniques plutôt que les articles** pour l'état actuel du produit.
  C'est la consigne la plus utile qu'on puisse laisser à une IA sur du contenu daté.

À 375 et 390 px la ligne de méta passe de deux à trois lignes, sans débordement : 24 px de plus
sur un téléphone pour une information de fraîcheur, l'échange est bon.

### Les comptes sociaux, tranchés définitivement

**Le client a confirmé le 2026-08-25 que LinkedIn est le SEUL compte actif**
(`https://www.linkedin.com/company/q-leap`) et que les deux autres ne le sont plus. La note du
2026-07-09, qui présente `facebook.com/QLeapSa` et `twitter.com/qleap_sa` comme « les vrais
comptes du live », a donc été annotée sur place : **elle est périmée, ces comptes ne doivent pas
revenir** dans `sameAs` ni dans le pied de page. L'URL déclarée garde sa barre oblique finale,
qui est la forme que LinkedIn sert sans redirection ; c'est la même page.

## Étape 5 de l'audit : les quatre pages légales sont dans le site (2026-08-25)

La faille 1 de l'audit RosoAI, son seul P1 dont une partie est **irréversible** : les quatre
pages légales ne répondaient que sur le WordPress, et les 24 pages du nouveau site pointaient
dessus en absolu. Le jour où le WordPress disparaît, elles disparaissent avec lui, et les
52 liens tombent en erreur.

**LA NOTE DU 2026-07-09 EST DONC PÉRIMÉE.** Elle disait que ces pages ne pouvaient pas être
reprises « mot pour mot » parce que l'outil de relevé refusait de reproduire des pages de
politique. Deux choses ont changé : le client a demandé explicitement cette reprise le
2026-08-25, et **ce sont ses propres pages, sur son propre domaine**. Ce n'est pas la reprise
d'un texte tiers, c'est la migration de son contenu. Il n'y avait donc rien à paraphraser.

### La chaîne, en deux scripts

- `tools/fetch-legal.py` relève les quatre pages dans un navigateur réel et écrit
  `tools/legal-source.json`. Deux précautions qui viennent de ce dépôt : l'en-tête
  **`Accept-Language` est fixé par langue** (le live redirige `/` vers `/en/` selon cet
  en-tête, et un relevé sans lui rapporte l'anglais sur les URL françaises), et seuls les
  blocs **visibles** sont retenus (`offsetParent !== null`, la règle apprise sur l'afficheur
  OLED repris par erreur d'une section désactivée) ;
- `tools/gen-legal.py` reconstruit les quatre pages dans le gabarit du site. Elles sont
  générées, pas écrites l'une après l'autre : c'est le même choix que pour les pages de cas
  d'usage, et pour la même raison, deux pages écrites à la main divergent.

Pour reprendre une mise à jour publiée sur le live : relancer les deux, dans cet ordre.

### Ce qui est repris à l'identique, et ce qui ne l'est pas

**Chaque mot.** Le contrôle qui compte n'est pas une relecture : c'est une comparaison
automatisée du texte RENDU de nos pages contre celui du live, bloc par bloc, dans les deux
navigateurs et avec la bonne langue. Relevé : **170 / 50 / 170 / 50 blocs, texte identique sur
les quatre pages, zéro bloc en trop, zéro bloc manquant.**

Trois écarts, et seulement ceux-là :

- **le balisage.** Le live écrit ses sous-titres en `<p><strong>…</strong></p>`, parfois en
  `<span style="font-weight: 600">` : un artefact d'Elementor. Ce sont des titres, ils
  deviennent des `<h2>`. Les mots ne changent pas, la hiérarchie devient valide (0 saut de
  niveau, 1 seul `h1`) et le texte devient citable. Les `<h4>` et `<h5>` des conditions de
  vente deviennent `<h2>` et `<h3>` pour la même raison ;
- **les liens.** `http://www.q-leap.eu` (44 occurrences) passe en `https://q-leap.eu`, même
  cible sans contenu mixte, et les quatre variantes de lien vers la page contact du live
  (`/contact/`, `/en/contact/`, `/en/contact-1/`, `/en/contact-us/`) pointent sur notre page
  locale ;
- **l'habillage** : notre en-tête, notre pied de page, notre fil d'Ariane, plus le bloc d'appel
  à l'action que le live porte aussi.

Aucune balise inattendue dans le contenu : l'inventaire ne trouve que `a`, `strong`, `em` et
`span`.

### L'ADRESSE DES PAGES EST CELLE DU LIVE, ET C'EST LE POINT LE PLUS IMPORTANT

`conditions-vente/index.html` répond sur `https://q-bot.eu/conditions-vente/`, exactement
comme aujourd'hui. Même chose pour `confidentialite/`, `en/privacy/` et
`en/terms-and-conditions-of-sale/`. **GitHub Pages ne sait pas rediriger** (relevé par
l'audit, et c'est exact pour un 301) : garder l'URL est donc le seul moyen de ne casser ni les
liens entrants, ni les partages, ni le référencement acquis, le jour de la bascule. Les deux
niveaux de profondeur (`../` en français, `../../` en anglais) sont ceux de `blog/` et
`en/blog/`, donc l'en-tête et le pied de page de ces gabarits se réutilisent tels quels.

Ne pas « corriger » ces pages en `conditions-vente.html` pour respecter la convention plate du
reste du dépôt : l'écart est volontaire et c'est lui qui préserve les URL.

### Les 52 liens

68 liens repointés en relatif dans 28 fichiers : les 52 des pages existantes, plus les 16 des
pieds de page des quatre nouvelles. Les liens légaux **perdent leur `target="_blank"` et leur
`rel="noopener"`** : c'était juste tant qu'ils sortaient du site, ça n'a plus de sens pour un
lien interne. Contrôle : **30 pages balayées, 0 lien interne cassé.**

Au passage, le pied de page généré par `admin/index.html` pointait ses deux liens légaux sur
`href="#"` : corrigé, il pointe sur les pages réelles.

Et le reste de l'intendance : les quatre URL ajoutées au `sitemap.xml` avec leurs paires
hreflang (28 URL au total), le décompte de `robots.txt` porté de 23 à 28 pages, et la section
Legal de `llms.txt` qui dit désormais que ces pages vivent dans le site et donne leurs dates
de dernière mise à jour.

### Deux divergences du live, reproduites à dessein

- **les dates de mise à jour ne concordent pas** : 7 juillet 2025 en français, 11 juin 2024 en
  anglais. La politique de confidentialité anglaise a donc un an de retard sur la française.
  C'est le contenu du client, il est repris tel quel ; **à lui de trancher s'il faut aligner
  l'anglais**, et c'est une vraie question de conformité, pas de référencement ;
- **la page conditions de vente française finit par « Notre politique générale de vente est en
  cours »**. C'est ce que dit le live. Repris tel quel.

Le pied de page du live anglais porte encore une ancienne adresse (10 rue Mathias Hardt,
L-1717 Luxembourg) et un copyright 2022 : sans effet ici, nos pages utilisent notre pied de
page.

## Le navigateur d'analyse repasse en mode invisible (2026-08-25)

**Demande du client : ne plus ouvrir de fenêtre sur sa machine**, il ne peut pas travailler en
parallèle. La note de méthode du 2026-08-20 avait fait passer tous les contrôles en
`headless=False`, mais elle disait bien pourquoi : le mode invisible rend en SwiftShader, donc
au processeur, et **tout défaut de rendu 3D doit être cherché en mode fenêtré**. Cette raison ne
vaut que pour le rendu GPU.

**Mesuré, pas supposé** : le relevé de contraste sur les 29 pages donne **exactement 18
remontées dans les deux modes**, les mêmes. C'est logique, il lit le DOM et les styles
calculés, pas des pixels. Idem pour le balayage des révélations, les liens internes, la
hiérarchie des titres et les longueurs d'affichage.

**Règle qui en découle.** Mode invisible par défaut pour tout ce qui se mesure dans le DOM.
Mode fenêtré uniquement pour chasser un artefact de rendu 3D (`model-viewer`, la séquence
épinglée de l'accueil), et dans ce cas seulement, en prévenant le client. Le piège de 2026-08-20
reste vrai, il est simplement plus étroit qu'écrit.

Un faux positif rencontré en le vérifiant, qui a coûté une minute : le relevé annonçait
116 défauts en mode invisible. C'était le serveur statique démarré dans le mauvais dossier,
répondant 404 partout, et la sonde mesurait consciencieusement le contraste de la page d'erreur
de `http.server`. **Un contrôle qui remonte soudain six fois plus de défauts mesure autre chose
que ce qu'on croit** : vérifier d'abord que la page servie est la bonne.

## Étape 6 de l'audit : la mise en ligne est outillée, pas déclenchée (2026-08-25)

Trois choses préparées, aucune tirée. **Le site n'est PAS public à l'issue de cette étape** :
lever les verrous se fait en une commande, le jour où le domaine bascule, et pas avant.

### Les 34 redirections des anciennes adresses

L'audit signale que GitHub Pages ne sait pas renvoyer un 301, donc que `/faq/`, `/blog/`,
`/about/` tomberont en erreur. Le relevé du `wp-sitemap.xml` du live donne la vraie liste :
**59 URL publiées**, pas trois.

Classées, et c'est le tri qui compte :

- **15 pages de contenu** avec une correspondance directe (`/about/` → `a-propos.html`,
  `/caracteristiques-techniques/`, `/contact/`, `/faq/`, `/en/about-us/`, `/en/contact-us/`,
  `/en/technical-specifications/` **et son doublon `-2/`**, `/en/f/`, les trois articles, et
  `/video/` + `/en/videos/` puisque le film vit maintenant dans la page d'accueil) ;
- **12 billets de la frise datée**, retirée du site le 2026-08-12. Ils atterrissent sur
  `index.html#evolution-title`, la section qui raconte la même histoire sans les dates devenues
  fausses. Attention, leurs adresses ne disent pas leur contenu : `/qbot-token-luxtrust/` est le
  billet « Juin 2022 » et `/prototype-fonctionnel/` le billet « Mai 2022 ». Il a fallu relever
  leur `<title>` pour les classer, l'URL seule trompe ;
- **7 archives WordPress** (catégories, étiquettes, deux pages d'auteur) → l'index du blog ;
- **une trentaine d'adresses du thème de démonstration** (`/portfolio/…`, `/portfolio-cat/…`,
  `?portfolio-filter=…`) : **volontairement laissées en 404.** Contenu factice jamais remplacé,
  du même lot que l'équipe fictive « Colabrio ». Les rediriger fabriquerait trente fausses
  correspondances, que les moteurs traitent en soft-404 et sanctionnent. Le 404 est le signal
  honnête.

Trois scripts : `tools/redirections_map.py` porte la carte (module à part, parce que deux
scripts la lisent et qu'un nom de fichier à tiret n'est pas importable),
`tools/gen-redirects.py` écrit les pages, `tools/verif-redirections.py` les contrôle.

**Pas de balise `noindex` sur ces pages, et c'est volontaire** : leur seul rôle est de
transmettre un signal, leur demander de ne pas être indexées reviendrait à demander qu'on
l'ignore. Le site reste fermé par `robots.txt` jusqu'à la mise en ligne. C'est la seule
exception à la règle « toutes les pages portent la balise PRÉ-LANCEMENT ».

Chaque page porte **trois** chemins vers la même cible : le `meta refresh`, un lien visible et
un `location.replace`. Le contrôle vérifie que les trois concordent, sinon une page pourrait
rediriger un navigateur et un moteur vers deux endroits différents. Relevé : 34 sur 34
concordantes, 34 sur 34 suivies dans un navigateur et aboutissant sur une page réelle, 0 lien
interne cassé sur l'ensemble du site.

### L'interrupteur

`tools/go-live.py` lève les trois verrous **ensemble**, ce que l'audit demande explicitement :
ouvrir `robots.txt` en laissant les balises `noindex` donne un site explorable mais invisible,
et l'inverse un site indexable que personne n'explore. Fait à la main sur trente fichiers, on
en oublie un, et le symptôme est silencieux.

**La simulation est le comportement par défaut** ; il faut `--appliquer` pour écrire. Ce script
rend le site public, cela ne doit pas pouvoir arriver par une faute de frappe.

Un défaut de mon propre script, trouvé en le contrôlant : `admin/index.html` écrit
`noindex,nofollow` **sans espace**, et mon remplacement littéral le ratait en silence. L'effet
était heureux (le back-office ne doit jamais être indexé) mais accidentel. C'est maintenant
explicite : la balise est cherchée par motif, et `admin/` figure dans une liste `JAMAIS`. Le
piège est le même que le cadratin en entité, l'apostrophe typographique et l'espace insécable :
**quatrième variante en trois jours.**

### LE POINT QUI DEMANDE UNE DÉCISION DU CLIENT

**Le WordPress bloque aujourd'hui TOUS les moteurs de réponse IA** : son `robots.txt` interdit
Amazonbot, anthropic-ai, Applebot-Extended, Bytespider, CCBot, ClaudeBot, FacebookBot,
Google-Extended, GPTBot, meta-externalagent, omgili, omgilibot, PerplexityBot et SentiBot.
Autrement dit, **les robots que la stratégie de visibilité IA vise sont aujourd'hui refoulés à
la porte du domaine**.

**CORRECTION, RELEVÉE PAR LE CLIENT LE 2026-08-25 : ne pas attribuer le 10/100 à ce
`robots.txt`.** L'audit porte sur le NOUVEAU site en migration et il désigne lui-même la cause,
qui est ailleurs : ce site est volontairement fermé aux robots en attendant sa mise en ligne,
et les 10 points existants viennent du site de la maison mère et d'un article de presse de
2023. Le blocage du WordPress est un fait vérifiable et il compte pour la suite, mais en faire
la cause du score était mon inférence, pas un constat de l'audit.

Le `robots.txt` d'ouverture de ce dépôt les autorise. Ce n'est pas une correction de bug, c'est
un **renversement de politique** : autoriser ces robots, c'est accepter que le contenu du site
soit lu par ces modèles, en échange de la possibilité d'être cité. `go-live.py` l'affiche en
clair au moment de l'exécution, et le fichier produit porte le commentaire qui l'explique.
À confirmer par le client avant la bascule.

### Ce qui reste manuel, et dans quel ordre

Le script l'imprime : DNS et HTTPS, **puis vérifier les 52 redirections en ligne**, puis la
Search Console, et **ne supprimer le WordPress qu'après cette vérification** (tant qu'il
répond, une erreur est réparable ; après, l'adresse est perdue).

**L'ENDPOINT DES FORMULAIRES EST EN ATTENTE, ET LE CLIENT A DEMANDÉ QU'ON LUI RAPPELLE.** Le
2026-08-25 : « on voit ça plus tard, rappelle-le moi tant qu'on n'a pas statué, je dois voir
avec mes managers. » Ce n'est donc pas un point de vigilance de fin de projet mais un rappel
actif, à faire en une ligne à la fin de chaque échange jusqu'à ce qu'il tranche. L'explication
complète lui a été donnée ce jour-là (service tiers type Formspree ou Brevo, une URL à coller
dans `--endpoint`, réserves RGPD, plafond de 50 envois par mois sur les offres gratuites) : ne
pas la refaire, juste rappeler que le point est ouvert.

## Passe de disposition, et le trait qui traversait les icônes (2026-08-25)

Trois signalements du client, tous exacts, et une passe mesurée sur les 29 pages pour la suite.

### 1. Le trait de la maquette passait par-dessus les icônes

`tools/render/interface-mockup.html` dessinait le fil de l'indicateur d'étapes en **deux
pseudo-éléments de `.steps`** : un trait continu du centre du premier disque au centre du
dernier. Les disques ont `z-index: 1`, donc en théorie ils le masquaient. En pratique le fond
d'un disque « fait » est **translucide** (`rgba(0,203,190,.10)`) : le trait se voyait au travers
et semblait passer par-dessus l'icône.

Et le reproche de fond était juste au-delà du bug : **ce n'est pas la convention d'un
indicateur d'étapes**, où le trait relie les noeuds sans jamais les traverser. Le fil est donc
devenu **un segment par intervalle**, du bas d'un disque au haut du suivant, plein et teal pour
ce qui est fait, tireté et gris pour ce qui reste. La dernière étape n'en porte pas : il n'y a
rien après elle.

Un détail qui compte : l'arc « en cours » dépasse son disque de 5 px (`inset: -5px`). Le
segment qui arrive sur lui s'arrête 5 px plus tôt (classe `pre-now`) et celui qui en part
démarre 5 px plus tard, sinon les deux traits touchent l'arc et l'ensemble se lit comme un
tracé cassé, ce qui avait déjà été reproché à une version antérieure. Les deux images sont
régénérées par `tools/render/shoot-interface.py`.

### 2. « Connexion internet » ne s'alignait pas, et c'était un plancher pris pour une colonne

`.spec-item__label` portait `min-width: 120px`. C'est un PLANCHER : dès qu'un libellé dépasse
cette largeur, il fixe la sienne, et sa valeur commence plus à droite que toutes les autres.
Mesuré avant correction : deux positions de départ à 1920 et à 768 px côté français, **trois
sur presque toutes les largeurs côté anglais** (« INTERNET CONNECTION » et « MANUFACTURING »).

La largeur ne pouvait pas se régler sur `.spec-item` : chaque ligne est son propre conteneur et
ne sait rien des autres. **C'est la LISTE qui doit porter la mesure**, d'où `subgrid` : la
colonne s'ajuste au libellé le plus long de sa propre liste, sans constante écrite à la main,
et chaque liste garde la sienne (117 px pour la fiche matérielle, 213 px pour les points
d'entrée API). Sous `@supports`, donc un moteur sans subgrid retrouve exactement le
comportement d'avant. Vérifié : **une seule position de départ, 4 pages × 7 largeurs.**

**ET SUR TÉLÉPHONE LA MÊME RÈGLE ÉTOUFFAIT LES VALEURS.** À deux colonnes, la valeur reçoit ce
que laisse le libellé : 170 px pour la fiche matérielle à 390 px de large, et **123 px** pour
la liste API dont les libellés sont des URL en chasse fixe. À 123 px on lit trois mots par
ligne. Sous **560 px** le libellé passe donc au-dessus de sa valeur, qui récupère toute la
largeur (285 à 350 px). Le seuil est calculé : le libellé le plus long fait 203 px et il faut
environ 290 px pour la valeur.

Piège rencontré : le bloc `@media` doit venir **après** le bloc `@supports` dans le fichier.
Les deux ont la même spécificité (0,3,0), c'est donc l'ordre qui tranche, et posé avant il
n'avait aucun effet.

### 3. Le rythme d'un titre suivi d'un bloc était irrégulier

`.section-title` porte 16 px de marge basse, ce qui est juste quand vient son chapeau : le
titre et son chapeau sont une unité de lecture. Quand vient un BLOC de contenu, 16 px le
collent au titre. Relevé sur les 23 pages : **16 px** sur les fiches techniques et les deux
cadres 3D, **28 px** sur l'encadré de l'accueil, **32 px** sur les grilles de produits, et
**16 px en français contre 32 en anglais pour le MÊME bloc de la page contact**.

Une seule valeur désormais, 32 px, par une règle de voisinage (`.section-title + div|ul|ol|form`)
et non par des styles en ligne, dont les deux qui traînaient sur `.products-grid` sont retirés.
Les marges adjacentes fusionnent, donc le total est bien 32 et pas 16 + 32. Vérifié : 10 cas,
une seule valeur.

### 4. Un constant périmé sur le trait des « 4 étapes »

`.order-process::before` reliait le centre du premier rond à celui du dernier avec
`right: calc(25% - 46px)`, une valeur **calculée pour des gouttières de 24 px**. La passe
d'aération du 2026-08-20 les a portées à 32 px : le trait dépassait donc le dernier rond de
6 px et laissait un moignon à droite. La formule est maintenant dérivée et exprimée en fonction
de `--op-gap` (`25% − 0,75 g − 28 px`, démonstration dans le fichier), donc elle suit la
gouttière. Vérifié : **écart 0,0 px aux deux extrémités, 2 pages × 5 largeurs.** Le trait de la
section évolution, lui, était déjà exprimé en fonction de sa gouttière et tombe juste.

### 5. Deux noms pour une classe réservée aux lecteurs d'écran

`.sr-only` vit dans `style.css`, `.visually-hidden` dans `scrolly.css`. Une page qui emploie la
seconde sans charger ce fichier afficherait en clair un texte censé être invisible. Aucune ne le
fait aujourd'hui, mais l'alias est posé dans `style.css` et ferme la porte.

### Ce que la passe n'a PAS trouvé, et les deux sondes qui mentaient

Sonde de disposition sur **29 pages × 5 largeurs** : aucun bloc de texte centré, aucun centrage
par marges automatiques, aucune rangée de frères désalignée, aucun débordement horizontal.

Deux faux positifs coûteux, à ne pas refaire :

- **comparer les abscisses de frères dans une grille à plusieurs colonnes** produit un défaut à
  chaque ligne. Le filtre doit exiger que TOUS les frères partagent la même gouttière, pas
  seulement trois d'entre eux, et identifier une liste par son ÉLÉMENT et non par son nom de
  classe (deux listes de même classe sur une page étaient fusionnées) ;
- **mesurer pendant les révélations échelonnées.** La variante `card` applique un `scale()`
  transitoire : une mesure prise 0,6 s après l'arrivée donnait des largeurs de cartes montant
  de 0,88 px par index, et j'ai pris une grille de garanties parfaitement alignée pour un
  défaut. Trois secondes plus tard, ou en mouvement réduit, tout est à la même abscisse. **Toute
  sonde de disposition doit mesurer en `reduced_motion`**, l'animation n'est pas la mise en page.

## Le film tourne en boucle, et le pied de page s'équilibre (2026-08-25)

### Le film : lecture automatique, boucle, aucune interface

**Demande du client, qui renverse celle de la veille** : « vraiment juste une vidéo loop ». Le
25 août au matin il signalait que le film partait seul et bouclait, et la correction avait été
de retirer la balise `<video>` au profit d'une affiche cliquable. L'après-midi il demande
l'inverse, explicitement. Les deux demandes sont claires, la seconde l'emporte.

Ce qui est en place : `muted loop playsinline`, **aucun `controls`**, et
`pointer-events: none` sur le lecteur. Cette dernière ligne compte : sans contrôles, un
navigateur n'affiche rien au survol, mais un **clic droit** ouvre son menu contextuel, avec
« télécharger » et « boucle ». Ce serait une interface. Il n'y en a plus aucune.

`aria-hidden="true"` et `tabindex="-1"` : c'est une boucle muette, décorative et sans commande.
L'exposer annoncerait à un lecteur d'écran un média que son utilisateur ne peut ni lancer ni
arrêter, et ce que le film montre est déjà dit par le texte de la section.

**LE FICHIER N'EST PAS DANS `src` MAIS DANS `data-film`, ET C'EST TOUT L'INTÉRÊT.** Il pèse
2,9 Mo et la section est à environ 5 000 px du haut de la page. Avec un `src` et `autoplay`, le
navigateur le télécharge dès l'arrivée sur l'accueil, qu'on descende ou non. Le module 18 le
demande quand la section approche, avec **200 px d'avance** (et pas 400 : la leçon du
2026-08-20 sur le filet de la séquence 3D, une marge trop large arme l'observateur dès le
chargement sur un téléphone). Résultat mesuré : **premier écran à 2 095 Ko, inchangé, et
5 380 Ko une fois la section atteinte**, dont 2 959 Ko de film.

Deux autres choses que fait le module 18, et qu'il faut garder :

- **il met la boucle en pause hors champ.** Un `<video>` hors écran continue d'être décodé dans
  plusieurs navigateurs : c'est de la batterie dépensée pour une boucle que personne ne
  regarde. L'observateur n'est donc pas déconnecté après le premier passage ;
- **il ne charge rien du tout** en mouvement réduit, en économiseur de données ou sur connexion
  lente (2g, ou 3g sous 1,2 Mbit/s). L'affiche reste, et c'est une vraie image du film. Une
  boucle décorative de 2,9 Mo n'a pas à s'imposer à quelqu'un qui a demandé le contraire.
  **Sans JavaScript, c'est aussi l'affiche qui reste** : l'état au repos est un état complet.

Contrôlé sur les deux moteurs : aucune requête vers le `.mp4` avant le défilement, puis
`paused: false`, `loop: true`, `controls: false`, `pointer-events: none`, la boucle repart bien
au bout des 8,72 s, pause à la sortie du champ, aucune erreur console.

**Le module 14 est retiré.** Il coupait la lecture automatique pour le mouvement réduit et
l'économiseur de données, mais visait `.hero__film-video`, une classe qu'aucune page ne porte
depuis que le film a quitté le hero. Son garde-fou vit maintenant dans le module 18, là où le
film se trouve. Le numéro n'est pas réattribué.

**Reste ouvert, chiffré** : le film s'affiche dans un cadre de 526 px de large, alors qu'il est
encodé en 1280 × 720, soit 2,4 fois trop. Un réencodage en 960 × 540 économiserait environ
22 % (mesuré le 2026-08-10), en 640 × 360 beaucoup plus, au prix d'un rendu plus mou sur écran
à forte densité. `avconvert` est le seul encodeur présent sur cette machine et il n'a pas de
réglage de débit. À arbitrer si les 2,9 Mo gênent.

### Le pied de page : 4 / 4 / 4

Il valait 6 / 3 / 3, et le client a demandé de l'équilibrer en suggérant lui-même de déplacer
Caractéristiques et Cas d'usage dans la colonne Produit. La répartition retenue :

| Q-Bot | Produit | Contact |
|---|---|---|
| Accueil | Caractéristiques | Nous contacter |
| À propos | Cas d'usage | bot@q-leap.eu |
| Blog | Modèle 3D | +352 20 21 17 |
| FAQ | Démo | q-leap.eu |

La logique : « Q-Bot » garde la marque et ses ressources, « Produit » tout ce qui décrit le
produit, « Contact » les façons de joindre. **Un doublon disparaît au passage** : la page
contact était rangée sous « Produit » avec l'intitulé « Démo gratuite », à deux lignes d'une
entrée « Démo » qui menait ailleurs. Elle est devenue « Nous contacter », dans la colonne
Contact, où on la cherche. Mesuré : trois colonnes de 253 px à 1440, contre 6 / 3 / 3 avant.

Réécrit par script sur les **29 pages**, en relisant dans chaque pied de page la profondeur
(`../`) et l'entrée sans lien qui marque la page courante, plutôt qu'en les redéduisant du
chemin du fichier.

### Trois bugs du gabarit d'article, oubliés par trois passes précédentes

`admin/index.html` génère les articles du blog. Son pied de page avait échappé à des
corrections faites partout ailleurs :

- **`assets/img/logo.png`** dans la barre de navigation ET dans le pied de page. C'est le
  fragment rogné de 128 × 150 px remplacé partout le 2026-07-09 parce qu'il s'affichait en
  sliver invisible. Tout article publié depuis embarquait donc le logo cassé. Passé à
  `logo-baseline-neg.png` ;
- **`tel:+35220211`**, le 7 final manquant : un clic pour appeler qui ne menait nulle part ;
- **`facebook.com/qleap.lu`**, un identifiant signalé comme inventé le 2026-07-09 et retiré du
  site à cette date. Le client a de plus confirmé le 2026-08-25 que **LinkedIn est le seul
  compte actif**. Retiré ;
- et un copyright figé à 2025 quand le site affiche 2026.

Le gabarit adopte au passage la même structure 4 / 4 / 4 et descend ses liens légaux dans la
barre du bas, comme le site.

**Leçon de méthode** : un gabarit qui génère des pages n'est pas vu par un balayage des pages
publiées. Toute passe sitewide doit le traiter explicitement, et il vaut de le vérifier de
temps en temps contre le site qu'il est censé imiter.

## LE FILM NE DÉMARRAIT PAS, ET C'ÉTAIT LE CACHE (2026-08-25)

Signalé par le client juste après la mise en place de la boucle : « elle se lance pas ».
Irreproductible ici, sur les deux moteurs, en serveur local comme en `file://`. La cause
n'était pas dans le code de la vidéo.

**LES 29 PAGES CHARGENT `style.css?v=…` ET `main.js?v=…`, ET CE NUMÉRO ÉTAIT ÉCRIT À LA MAIN.**
Il n'avait pas bougé depuis le commit qui précède toute la session : `style.css?v=2026.46-08-29b`
et `main.js?v=2026.19-08-23`. Or `main.js` a été modifié une dizaine de fois dans la journée.
Chez le client le navigateur servait donc **l'ancien script depuis son cache**, et cet ancien
script cherchait l'affiche cliquable de la veille, qui n'existe plus dans le HTML. Rien ne
démarrait, et rien n'apparaissait dans la console.

**POURQUOI JE NE L'AI PAS VU.** Le serveur de développement ne met rien en cache, et un
navigateur piloté part d'un profil vierge à chaque essai. Les deux environnements dans lesquels
je vérifie sont précisément ceux où ce défaut ne peut pas se produire. C'est la pire catégorie
de bug : invisible côté outillage, systématique côté visiteur qui revient.

Et il ne concernait pas que la vidéo : **tout ce qui a été fait cette session dans `style.css`
et `main.js` ne pouvait pas arriver chez le client** (le calculateur de ROI, le verre, la
colonne des fiches techniques, le pied de page à 4 / 4 / 4, le rythme des titres).

### Le correctif est une empreinte de contenu, pas un numéro à se rappeler

`tools/bump-assets.py` remplace le `?v=` par les huit premiers caractères de l'empreinte
SHA-256 du fichier. Une empreinte change **exactement** quand le fichier change, et jamais
autrement : il n'y a plus rien à se rappeler, aucun moyen d'oublier, et pas d'incrément inutile
qui ferait retélécharger 200 Ko de CSS pour rien.

**À LANCER APRÈS TOUTE MODIFICATION D'UN CSS OU D'UN JS, AVANT DE COMMITER.**

    python3 tools/bump-assets.py

### Le même piège vaut pour les images réécrites en place

Une image dont le contenu change sous un **nom de fichier inchangé** reste servie depuis le
cache. C'est le cas de la maquette d'interface corrigée le même jour : le client voyait encore
le trait qui traversait les icônes. Quatre fichiers réécrits en place cette session sont donc
versionnés eux aussi : `qbot-interface.jpg`, `qbot-interface-en.jpg`, `qbot-og.jpg` et
`qbot-film-poster.jpg`. Une image dont le NOM change (les deux photos ajoutées) n'en a pas
besoin. Pour `qbot-og.jpg`, versionner l'URL est en plus le seul moyen de forcer les réseaux
sociaux à relire l'aperçu.

Le script versionne aussi les références du gabarit d'article de `admin/index.html`, qui reste
donc à jour tant qu'on le relance.

### Une seconde cause, indépendante, trouvée en relisant le module

La balise portait `preload="none"`. Sans `src` c'est sans effet, mais **dès que le module
branche le fichier, cet attribut dit au navigateur de ne rien tamponner**, ce qui contrarie une
lecture automatique. Il est retiré du HTML, et le module met `preload = 'auto'` avant de poser
le `src`.

Le module appelle en outre `load()` explicitement et **retente la lecture à l'événement
`canplay`** : Safari rejette un `play()` appelé dans le même tour de boucle que l'affectation du
`src`, parce qu'aucune donnée n'est encore arrivée. Le `.catch()` avalait ce rejet en silence et
l'affiche restait. Deux tentatives, dont une quand le navigateur dit lui-même qu'il est prêt.

Contrôlé après : lecture et progression du temps vérifiées sur Chromium et WebKit, en français
et en anglais, en serveur local et en `file://`, plus la boucle qui repart et la pause hors
champ.

## Audit de contrôle RosoAI : les cinq chantiers de trente-cinq minutes (2026-08-25)

`Documentations/Audit_Q-Bot_Controle_Note_Strategique.pdf` (second passage, 15 pages) et
`Documentations/Plan_Bascule_Q-Bot.pdf` (13 chantiers, 27 pages) remplacent l'audit du 24 août.
La note passe de 5,6 à 6,2 sur 10, et de 6,0 à 7,3 sur les sept dimensions réellement
auditables : trois des dix mesures portent sur ce que le monde extérieur voit du site, et
derrière un `Disallow: /` volontaire elles ne peuvent rien mesurer. **L'audit ne compte donc
pas la fermeture comme un défaut**, et il ne faut pas la lever pour « débloquer » une note.

**CHAQUE CONSTAT A ÉTÉ REVÉRIFIÉ DANS LE DÉPÔT AVANT CORRECTION.** Ils étaient tous exacts.
Deux corrections à apporter à l'audit lui-même, en revanche :

- il compte **28 pages**, le site en a **29**. La 29ᵉ est `admin/index.html`, qui ne doit
  jamais être indexée (elle figure dans la liste `JAMAIS` de `go-live.py`). Son compte de
  `noindex` et l'inventaire du `sitemap.xml` sont justes sur 28 ;
- son point sur les formulaires est **déjà réglé** : le module 15 de `main.js` porte le repli
  courrier, documenté. L'audit le reconnaît d'ailleurs et corrige son propre constat d'août.
  **Le point endpoint reste ouvert chez les managers du client**, cf. la note du 2026-08-25.

**UN POINT DE L'AUDIT PRÉCÉDENT RESTE À ÉCARTER** : republier le tarif. Le client a tranché
l'inverse le 24 août, et le chantier 2 ci-dessous suit cette décision, pas la « faille 4 ».

### Ce qui a été fait, et l'arbitrage derrière chaque chose

- **les 4 pages légales passent en adresse complète.** Google ignore un cluster `hreflang`
  écrit en relatif : sur ces quatre pages, l'appariement FR/EN ne comptait pas. Détail qui
  compte pour la suite : **`tools/gen-legal.py` écrivait déjà les adresses absolues** ; ce sont
  les fichiers qui ont été repassés en relatif à la main lors de la passe des liens internes du
  25/08. Rien à corriger dans le générateur, une régénération redonne la bonne forme ;
- **le bloc `offers` est retiré des 8 fiches produit** (option B du plan). Un `Offer` sans prix
  ni fourchette est rejeté par Google (« champ obligatoire manquant : prix ») : c'était le seul
  état qui ne rapportait rien. Le `Product` reste valide avec `name`, `description`, `image`,
  `brand` et `manufacturer`. **Ne pas y remettre de prix** sans nouvelle décision du client ;
- **les deux h1 sont ÉCHANGÉS, pas réécrits.** « Curiosité, créativité et analyse. » était le
  seul titre du site sans rapport avec sa page ; il décrit une manière de travailler, donc il
  part sur À propos, et Caractéristiques prend « Les caractéristiques techniques de Q-Bot ».
  C'est l'arbitrage du client : l'échange respecte la règle « texte du live mot pour mot »
  puisque la formule reste publiée, ailleurs. La sur-accroche « L'innovation by Q-Leap ! » reste ;
- **les boutons du hero sont inversés, les LIBELLÉS conservés.** Le plan proposait aussi de les
  réécrire (« Demander une démo gratuite »), écarté par le client : c'est du texte du live ;
- **la 17ᵉ question de la FAQ dit ce que Q-Bot ne fait pas.** « iOS » n'apparaissait **0 fois**
  sur les 29 pages alors que `llms.txt` énonçait la limite noir sur blanc, donc la seule
  formulation publique était derrière la porte fermée. Intitulé « Q-Bot fonctionne-t-il avec
  iOS (iPhone) ? » et non « avec iOS » seul, sur décision du client : les gens cherchent
  « iPhone ». Réponse de 51 mots (FR) et 49 (EN), donc dans la fenêtre de 40 à 60 qui se fait
  citer. **Trois emplacements par langue** : le bloc visible, l'index en tête de page, et le
  `FAQPage`. En oublier un laisse la question hors du sommaire ou hors des données structurées ;
- **`sameAs` passe de 1 à 3 entrées** sur les 29 pages : le LinkedIn de Q-Leap, plus
  `q-leap.eu` et `q-guard.app`. Ce sont ses propres sites, pas des comptes sociaux : la règle du
  25/08 (« LinkedIn est le seul compte actif, ne pas remettre Facebook ni Twitter ») n'est pas
  touchée.

### Les trois dépendances extérieures, et le piège du module local

Le site n'envoie plus **aucune** requête vers un domaine tiers. Trois rapatriements, dont deux
qui avaient un piège chacun.

**1. Roboto est hébergée chez nous.** Elle était appelée chez Google : deux `preconnect` plus
une feuille de style BLOQUANTE sur un domaine tiers. Deux découvertes qui changent la forme de
la solution :

- **Google sert désormais Roboto en police VARIABLE.** Les cinq graisses demandées renvoient le
  MÊME fichier (empreintes MD5 identiques, axe `wght` de 100 à 900 vérifié dans le woff2). Donc
  **4 fichiers et non 10** : latin et latin-ext, en normal variable et en italique statique 400.
  Une italique gras reste synthétisée par le navigateur, exactement comme avant, puisque la
  requête d'origine ne demandait que l'italique 400 ;
- **seuls `latin` et `latin-ext` sont embarqués.** Le site est FR/EN ; le cyrillique, le grec, le
  vietnamien et le mathématique que Google déclare ne seraient jamais téléchargés, mais chaque
  bloc déclaré coûte des octets à lire sur 29 pages.

Les `@font-face` vivent **en tête de `style.css`** et non dans une feuille à part : zéro requête
supplémentaire, et le navigateur connaît déjà l'origine. Un `preload` de la seule face que toute
page utilise (`roboto-latin.woff2`) compense la découverte plus tardive. **L'attribut
`crossorigin` est obligatoire sur ce `preload` même en même origine**, sinon la police est
téléchargée deux fois. Mesuré : 1 seul woff2 par page, 200, Roboto prête sur les 10 pages testées.

**2. La visionneuse 3D est chez nous, SAUF en `file://`, et ce n'est pas une préférence.**
Mesuré sur les deux moteurs : un `<script type="module">` dont le `src` est un fichier local est
REFUSÉ en `file://` (origine « null », et un fichier ne peut porter aucun en-tête CORS), alors
que jsDelivr envoie `*`. Un simple échange aurait donc supprimé la 3D du mode double-clic, que
`qbot.glb.data.js` existe précisément pour préserver. Le choix de la source se fait donc à
l'exécution :

    const local = location.protocol !== 'file:';
    const m = await import(local ? './assets/js/model-viewer-4.3.1.min.js' : '<CDN>');
    if (local) m.ModelViewerElement.dracoDecoderLocation = './assets/js/draco/';

**Le spécificateur d'un `import()` dynamique doit commencer par `./` ou `../`.** Écrit
`'assets/js/…'`, il est pris pour un nom de module nu et rejeté (« Failed to resolve module
specifier »). C'est ce qui a cassé les deux pages de la racine au premier essai, et pas les
pages `en/`, dont le préfixe `../` était déjà valide.

**ET CE CHANGEMENT A CASSÉ LE MODE `file://` D'UNE FAÇON QU'IL FAUT CONNAÎTRE.** `viewer.src = …`
posé sur un `<model-viewer>` pas encore PROMU crée une propriété propre sur l'élément ; quand le
composant est défini ensuite, cette propriété propre **masque l'accesseur du prototype**, le
setter ne s'exécute jamais et le modèle ne charge plus, **sans une ligne d'erreur**. Un `import()`
définit le composant strictement plus tard qu'une balise statique : en `file://` la source est le
CDN, donc un aller-retour réseau, pendant lequel `main.js` (local, instantané) passait devant.
Symptôme mesuré : Chromium ne chargeait plus rien, WebKit s'en sortait par chance
d'ordonnancement. Le pire des défauts, celui qui dépend du moteur. Le chargement `file://` de
`main.js` est donc gardé par `customElements.whenDefined('model-viewer')`, ce qui supprime la
classe entière quel que soit l'ordre. Vérifié après : `loaded: true` et aucune propriété propre
`src`, sur les deux moteurs, en `file://` comme en http.

Le viseur de l'ACCUEIL est un autre cas et n'a pas ce problème : son `src` est un ATTRIBUT du
HTML, jamais réassigné, et il n'a jamais eu de repli base64 (il a son image de repli et le filet
de 12 s de `scrolly.js`). Un `file://` sans modèle sur l'accueil est le comportement documenté,
pas une régression.

**3. Le décodeur Draco aussi.** C'étaient les deux dernières requêtes extérieures
(`draco_wasm_wrapper.js` + `draco_decoder.wasm` chez gstatic, 100 Ko compressés). Même
construction que ci-dessus, par `ModelViewerElement.dracoDecoderLocation`. Attention : le fichier
brut pèse 344 Ko sur le disque pour 100 Ko sur le réseau, l'audit annonçait 40 Ko.

**Le gabarit d'article de `admin/index.html` appelait Inter chez Google** : une police HORS
CHARTE, sur un domaine tiers, dans des articles publics. Repris. C'est la troisième fois que ce
gabarit est oublié par une passe sitewide : **il n'est pas vu par un balayage des pages
publiées, il faut le traiter explicitement.** L'interface du back-office, elle, garde Inter :
elle n'est jamais publique. À signaler : ce gabarit écrit aussi `<meta name="robots"
content="index,follow">`, donc un article généré avant la mise en ligne échapperait au
`noindex` des 29 pages.

### La carte de contact ne se charge qu'au clic

L'iframe Google était servie au chargement : elle dépose ses cookies avant que le visiteur ait
rien demandé, sur un site qui publie une page Confidentialité. **La capture d'écran proposée par
le plan a été écartée** : redistribuer une image de Google Maps hors API sort de ses conditions
d'utilisation, et le chargement au clic règle le même problème sans cette question. Le cadre
porte l'adresse, un bouton, et la mention de ce que le clic déclenche ; le module 19 de
`main.js` crée l'iframe. Mesuré : **0 requête vers Google avant le clic, 22 après**, adresse
lisible sans JavaScript. Le bouton est en noir sur le teal, jamais en blanc : le teal de charte
est une couleur claire, le blanc y plafonne à 2:1.

### Le bandeau de références a été écrit, puis RETIRÉ : aucun client ne sera nommé

Sept références clients de Q-Leap, publiques sur `q-leap.eu/references/`, avaient été mises en
forme dans les deux accueils et laissées **en commentaire** le 2026-08-25, en attendant l'accord
des clients nommés. C'était le levier le plus fort de la dimension « Autorité et marque » de
l'audit RosoAI.

**ARBITRÉ LE 2026-08-26, ET C'EST UN REFUS, PAS UNE ATTENTE.** Réponse de Sylvain Perez : « on a
déjà demandé à des clients mais aucun n'a répondu positivement. On va devoir se passer de
témoignages. »

Le balisage **et** son CSS sont donc **supprimés**, pas remis de côté. La raison est concrète :
un bloc laissé en commentaire finit par être décommenté, et une feuille de style qui garde ses
règles « au cas où » est une invitation à le faire. Publier ces noms sans accord serait un
dommage réel pour le client, pas une imperfection de référencement. Même arbitrage que les bandes
d'outils du 2026-08-20 (« le motif est écarté, pas mis de côté ») ; l'écart avec `.timeline`,
gardée comme chemin de code, est que celle-ci l'a été **sur décision du client**, et ici la
décision est inverse.

**RÈGLE QUI EN DÉCOULE : ne nommer aucun client sur ce site sans un accord écrit, nom par nom.**
`llms.txt` le dit dans ses faits vérifiés, avec la consigne de ne pas en inférer un. Les sept noms
ne sont plus énumérés dans ce fichier non plus : le dépôt est public, ils n'ont plus de raison
d'y figurer.

**Ce qui porte l'autorité de la marque en l'absence de témoignages**, et qui est déjà en place :
le fondateur nommé et relié à son profil (visible et dans le `founder` de toutes les pages), la
citation de presse ITnation sur les deux articles Merkur, `legalName` / `foundingDate` /
`foundingLocation` / `knowsAbout`, et les guides. Ce qui manque et reste hors de ce dépôt : les
annuaires professionnels et les avis sur un comparateur, que l'audit compte aussi dans cette
dimension.

### Le graphe est fermé : Sylvain Perez est relié, et quatre articles sont signés

**URL fournie par le client le 2026-08-25 : `https://www.linkedin.com/in/sylvainperez/`.** Celle
du plan RosoAI (`lu.linkedin.com/in/sylvainperez`) n'avait pas été vérifiée et n'a jamais été
posée : un `sameAs` faux fait plus de mal que pas de `sameAs`.

- **le `founder` de l'`Organization` porte ce `sameAs` sur les 29 pages.** C'était le dernier
  maillon manquant : le site le nommait en clair depuis longtemps, mais aucune machine ne pouvait
  relier ce nom à un profil ;
- **QUATRE articles sur SIX passent à `author: Person`**, avec son `jobTitle` et son `sameAs` :
  les deux articles pédagogiques (2FA, automatisation des tokens) dans chaque langue. **Les deux
  « Merkur » gardent `author: Organization`, et c'est délibéré** : ce sont la reprise d'un article
  paru dans Merkur, le magazine de la Chambre de commerce, le 27.02.2023. Les attribuer
  nominativement dirait quelque chose de faux sur lui ET sur le magazine. Arbitré avec le client,
  qui a suivi cette recommandation. **Ne pas « compléter » les deux derniers par cohérence
  apparente** ;
- **la ligne visible suit le structuré**, sur décision du client : « Sylvain Perez, créateur de
  Q-Bot » / « Sylvain Perez, creator of Q-Bot » remplace « Équipe Q-Leap » / « Q-Leap Team » sur
  les quatre articles signés, et **sur la carte en vedette des deux index de blog**, seule carte
  qui porte une ligne d'auteur (les autres n'en ont pas). Le visible et le JSON-LD qui divergent,
  c'est le défaut qui a déjà coûté des corrections sur les FAQ. Vérifié à 390 px : la ligne de
  méta fait **72 px sur les six articles**, signés ou non, donc le nom plus long n'ajoute aucune
  ligne ;
- `llms.txt` porte la même distinction, avec la consigne explicite de ne pas attribuer l'article
  Merkur à Sylvain Perez.

**Deux gabarits de `admin/index.html` restent en écart, sans effet aujourd'hui** : ses six
entrées d'amorçage portent des slugs qui n'existent plus dans le site (`automatiser-2fa-tests`
et autres) et gardent « Équipe Q-Leap », et son gabarit d'article **n'émet aucun `BlogPosting`
JSON-LD** du tout. Un article généré par le back-office n'aurait donc pas de données
structurées, ni de `noindex` (il écrit `index,follow`). À reprendre le jour où ce back-office
sert vraiment.

### « Depuis 10 ans » sur q-leap.eu : rien à changer chez nous

Point 4 du plan, tranché le 2026-08-25 : le client a demandé de prendre l'année inscrite sur
`q-leap.eu`, qui est le site principal. **Relevé dans un navigateur réel, avec l'en-tête de
langue fixé : `q-leap.eu` n'inscrit AUCUNE année de création.** Son accueil et son À propos
disent « Depuis 10 ans » / « For 10 years », un compte relatif, pas une date. La seule année du
site est son copyright, **« Q-LEAP SA© 2012 – 2026 »**, présent en pied de page.

Donc **2012 est confirmé**, et notre « depuis 2012 » est déjà juste : aucune modification ici. Ce
qui reste faux est le « Depuis 10 ans » de `q-leap.eu` lui-même, qui vaudrait 2016 et contredit
son propre copyright. C'est hors de ce dépôt. Ne pas « aligner » notre site sur ce chiffre : ce
serait remplacer une date exacte par un compte périmé.

### Ce qui reste ouvert

- **le lien Calendly de l'étape 1 de `commandez`/`order`** : la phrase nomme Calendly sans le
  lier, c'est un clic de trop sur la page où le visiteur est le plus près de décider. Reporté
  par le client ;
- **les treize contenus du plan**, dont « Selenium a raison, pour les codes à usage unique ».
  L'audit établit que la niche « automatiser l'authentification LuxTrust » est toujours vide ;
- **le bandeau des sept références**, écrit et en commentaire, en attente de l'accord des
  clients nommés ;
- **le « Depuis 10 ans » de `q-leap.eu`** : hors de ce dépôt, et contredit le copyright de ce
  site-là. À corriger chez eux, pas ici ;
- **la séquence du jour J** (`CNAME`, DNS, HTTPS, puis `go-live.py`, puis Search Console, puis
  seulement la suppression du WordPress). L'ordre est ce qui protège le référencement acquis.
  `tools/go-live.py` existe et lève les trois verrous ensemble ; il n'a PAS été lancé.

### Un piège d'outillage rencontré au passage

**`python3 -m http.server` est mono-fil** : il s'étrangle sur les pages qui portent le modèle 3D
et rend des `Timeout` qui ressemblent à un défaut du site. Les contrôles de cette passe tournent
sur un `ThreadingTCPServer` de quatre lignes. Un balayage qui expire sur les pages 3D et nulle
part ailleurs mesure le serveur, pas la page. Même en threadé, deux navigateurs qui chargent en
parallèle 1 Mo de visionneuse, 571 Ko de modèle et 286 Ko de wasm font dépasser un délai de
13 s : un `loaded: false` isolé se revérifie SEUL avant d'être appelé régression (mesuré ensuite :
chargé à 5 s, aucune requête en échec).

**ET LE BALAYAGE DES RÉVÉLATIONS DOIT PARCOURIR LA PAGE PAR PAS, PAS SAUTER AU BAS.** Une sonde
qui fait un seul `scrollTo(bas)` puis compte les `.reveal` sous 0,9 d'opacité a signalé des
invisibles sur les 28 pages, y compris intouchées et jusqu'à 55 sur `caracteristiques`. Reprise
avec un parcours par pas de 450 px (110 ms par pas, `behavior: 'instant'`), la même sonde donne
**0 partout**. L'observateur d'intersection n'a simplement jamais vu passer les éléments du
milieu de page. C'est la même famille de piège que la note du 2026-08-20 sur `scroll-behavior:
smooth`, et elle ressemble exactement au vrai défaut « un bloc reste invisible ».

## La porte de côté : ce que l'hébergement servait à côté du site (2026-08-25)

`Documentations/Audit_Q-Bot_Controle_Note_Strategique.pdf` (contrôle n°2, 16 pages, 6,2 → 6,5
sur 10) et `Documentations/Plan_Bascule_Q-Bot.pdf` (révision 2, 10 chantiers) remplacent les
versions du matin. Neuf des onze points du matin sont confirmés refermés dans le code. Le
point neuf est ailleurs : **ce que GitHub Pages sert en dehors des 28 pages du plan de site.**

**L'AUDIT SOUS-ESTIME LE SUJET SUR TROIS POINTS, MESURÉS AVANT CORRECTION.**

1. **Le dépôt GitHub est PUBLIC**, et l'audit raisonne comme si le risque n'existait qu'au
   jour J. Relevé sans authentification : `api.github.com/repos/Q-LEAP/qbot-website` répond
   `"private": false`, `raw.githubusercontent.com/.../main/CLAUDE.md` répond 200, et
   `q-leap.github.io/qbot-website/CLAUDE.md` et `/admin/` répondent 200. Le tarif et les sept
   références clients sont donc **déjà lisibles publiquement**, là où le `robots.txt` de
   q-bot.eu n'a aucune prise.
2. **Il n'y a pas six documents hors plan, il y en a davantage.** L'audit a manqué
   `claude.md.txt` (une consigne de développement plus ancienne), **`website 3/website/`** (une
   SECONDE copie des quatre pages de maquette anglaises, différentes de celles de
   `Documentations/website/`, donc huit pages concurrentes et non quatre),
   `Documentations/assets-sources/` (les masters IA que ce fichier dit explicitement de ne pas
   remettre en ligne, et qui sont en ligne), `Screen modèle 3D/` (12 rendus CAO) et `tools/`
   (23 fichiers dont 2 pages HTML).
3. **Le chantier 05 tel qu'écrit se retourne contre le site.** Il fait écrire `hidden` dans le
   HTML de la FAQ, alors que le même audit porte au crédit du site que le texte des réponses
   soit lisible sans JavaScript, « ce qui permet aux moteurs et aux IA de citer tes réponses ».
   Voir la section FAQ ci-dessous.

### Chantier 01 : `_config.yml`, et le workflow qui n'a pas survécu à la journée

**C'est `_config.yml` qui ferme la porte, et lui seul.** GitHub Pages construit ce dépôt avec
Jekyll (il n'y a pas de `.nojekyll`) et aucun fichier du site ne porte d'en-tête YAML ni de
syntaxe Liquid : une liste `exclude` suffit donc, par simple commit, sans aucun réglage et sans
rien déplacer. C'est l'option C du plan, et c'est la seule des trois qui s'applique le jour même.

**UN WORKFLOW A EXISTÉ QUELQUES HEURES, ET IL A ÉTÉ RETIRÉ.** `.github/workflows/pages.yml`
portait la même liste plus un contrôle de chemin ET de contenu qui faisait ÉCHOUER la
publication si un fichier de travail s'y glissait. Il demandait un réglage manuel
(`Settings → Pages → Source : « GitHub Actions »`) qui n'a pas pu être fait, et **tant que la
source reste la branche, les deux déployaient à chaque push sur la même cible, le dernier
arrivé gagnant**. Relevé sur un même commit : branche à 12:30:03, workflow à 12:29:45 — c'était
donc toujours Jekyll qui servait, et le garde-fou ne protégeait rien puisque son artefact était
écrasé dix-huit secondes plus tard. Deux déployeurs pour une cible sont une course, pas une
sécurité. Retiré sur décision du client. **Si on le remet un jour, basculer le réglage dans le
même mouvement**, sinon on recrée la course.

**CONSÉQUENCE À CONNAÎTRE : L'EXCLUSION EST DÉSORMAIS SILENCIEUSE.** Un dossier de travail
ajouté plus tard et oublié dans `_config.yml` part en ligne sans un mot. Le contrôle est une
commande, à passer avant la mise en ligne :
`curl -s -o /dev/null -w '%{http_code}' https://q-bot.eu/CLAUDE.md` doit répondre 404, comme
`/admin/` et `/Documentations/website/`.

**Et passer le dépôt en privé est une décision séparée** : Pages sur un dépôt privé demande un
plan GitHub Pro / Team / Enterprise. Sur le plan gratuit, passer en privé éteint Pages. À
vérifier avant de basculer. Le contenu resterait de toute façon dans l'historique git.

Ce que le workflow a appris avant de partir, et qui vaut pour toute liste d'exclusion ici :

- **`Screen modèle 3D` passait au travers de son exclusion.** macOS stocke le « è » décomposé
  (NFD), Linux composé (NFC) : un motif littéral ne correspond pas des deux côtés. C'est un
  piège de la même famille que le cadratin écrit `&mdash;`, l'apostrophe typographique et
  l'espace insécable, mais au niveau du système de fichiers cette fois. Jekyll, lui, accepte le
  nom tel quel dans `exclude` ; ne pas en conclure que le problème n'existe pas ailleurs.

Contrôlé en ligne après construction : les 11 chemins de travail répondent 404, le site est
entier (accueil, 28 pages, pages légales, 53 relais, modèle 3D, assets).

### Chantier 05 : `hidden` est posé par le script, jamais écrit dans le HTML

Les réponses de FAQ n'étaient repliées que **visuellement** (`max-height: 0` + `overflow:
hidden`) : un lecteur d'écran énonçait les dix-sept d'affilée et les liens d'une réponse fermée
restaient atteignables au clavier. C'est réel et c'était à corriger.

**MAIS L'ATTRIBUT NE DOIT PAS ÊTRE DANS LE HTML.** Écrit en dur, il servirait les 17 réponses
comme contenu masqué à tout le monde, robots compris, et les retirerait du rendu pour un
visiteur sans JavaScript. Posé par le module 3 à l'initialisation, il ne s'applique qu'aux
navigateurs qui savent aussi rouvrir : sans JavaScript on retombe exactement sur l'état d'avant
(déjà `max-height: 0`), pas plus mauvais, et le HTML servi ne contient aucun attribut masquant.
Vérifié : `faq-item__answer" hidden` apparaît **0 fois** dans la source servie, les 17 réponses
y sont.

Trois choses à ne pas défaire dans le module 3 :

- **l'ordre des deux lignes à l'ouverture.** `answer.hidden = false` AVANT
  `answer.scrollHeight` : un élément `hidden` est en `display: none` et mesure zéro, donc
  mesurer d'abord ouvrirait toutes les réponses sur une hauteur nulle. La lecture de
  `scrollHeight` force au passage le calcul de mise en page, ce qui est aussi ce qui fait
  partir la transition de `max-height: 0` au lieu de sauter. Mesuré : 314 px à l'ouverture ;
- **le repli est différé de 480 ms** (transition CSS 0,42 s + marge) et vérifie
  `!item.classList.contains('open')` avant de masquer : sinon une réponse rouverte entre-temps
  se refermerait dans le dos du visiteur ;
- **l'état initial est masqué immédiatement**, sans délai, sinon les 17 réponses restent
  énoncées pendant la demi-seconde qui suit le chargement.

Le balisage reçoit `id` / `aria-controls` / `aria-labelledby` sur les **48 questions des six
pages** qui en portent (`faq`, `en/faq`, `commandez`, `en/order`, `index`, `en/index`), numérotés
par page. Mesuré sur Chromium et WebKit : 17 boutons atteignables au clavier, **0 focus tombant
dans une réponse fermée**, l'ouverture par l'index (module 16) fonctionne toujours.

### Chantier 10 : trois liens sur quatre, et pourquoi

- **L'article Merkur n'est plus atteignable.** Le live WordPress le liait vers
  `corporatenews.lu/fr/archives-shortcut/…/automatiser-l-utilisation-des-tokens-dans-vos-tests-logiciels` ;
  ce domaine **redirige aujourd'hui vers la page d'accueil de `merkur.lu`**, l'article n'y est
  plus. Lier une preuve qui atterrit sur une page d'accueil générique est pire que ne rien
  lier. C'est donc la **reprise ITnation du lendemain** (28.02.2023, vérifiée vivante, Q-Leap
  et Q-Bot nommés) qui est liée, sur les deux articles Merkur. Attention : cet article décrit
  l'ancien récit du token LuxTrust, ce qui est cohérent avec un billet de 2023 portant déjà sa
  note de transparence, mais ne doit pas être repris comme description du produit ;
  `www.corporatenews.lu` ne répond pas du tout, son certificat ne couvre que le domaine nu ;
- **le profil LinkedIn de Sylvain Perez** rejoint ses quatre signatures d'article et les deux
  cartes en vedette des index de blog, là où le JSON-LD le déclarait déjà seul ;
- **ADB, Selenium, Cypress, Playwright, Robot Framework** sont liés à leur documentation
  officielle. Un lien dans un `.spec-item__label` a demandé sa propre règle CSS : le libellé
  est en capitales espacées et en gris sourd, un lien teal souligné y ferait une tache et
  casserait la colonne que `subgrid` aligne. Il garde donc la couleur du libellé et se signale
  par un soulignement pointillé.

**CETTE NOTE ÉTAIT PÉRIMÉE, CORRIGÉE LE 2026-08-26.** Elle disait le lien LinkedIn de
`a-propos.html` / `en/about.html` laissé ouvert, au motif que ces pages ne nomment pas leur
fondateur. Elles le nomment : « [Sylvain Perez](…), fondateur et CEO de Q-Leap » côté français,
et son pendant anglais, tous deux avec le lien vers son profil. Le chantier 10 est donc complet
sur ses quatre points. Leçon : une note qui dit « laissé ouvert » doit être revérifiée avant
d'être citée, pas recopiée.

### Les autres chantiers

- **02** : le modèle d'article de `admin/index.html` écrivait `index,follow`, il passe en
  `noindex, nofollow` avec la marque « PRÉ-LANCEMENT » des 28 autres pages. Sans effet une fois
  le chantier 01 appliqué, puisque `admin/` n'est plus publié ; gardé comme filet ;
- **03** : le script d'atelier de l'éditeur (60 lignes, `localStorage` `qbot_articles`) est
  retiré de `blog.html` et `en/blog.html`. Il remplaçait la liste du blog, donc les seuls liens
  internes vers les trois articles, si le navigateur du visiteur en contenait. Vérifié après :
  1 article en vedette + 2 cartes, les trois liens intacts dans les deux langues ;
- **04** : « via Calendly » et « par téléphone » deviennent cliquables sur `commandez.html` et
  `en/order.html`. Point reporté par le client depuis le 25/08 au matin, repris sur sa demande ;
- **06** : le commentaire de l'index de la FAQ compte dix-sept questions et non plus seize.

### Ce qui reste, et l'ordre du jour J

L'ordre est la seule contrainte dure : **le chantier 01 avant `go-live.py`**. Un moteur qui a vu
un fichier une fois peut le garder longtemps dans ses résultats. Reste ensuite inchangé : CNAME,
DNS, HTTPS, les trois verrous ensemble, Search Console le jour même, vérifier cinq anciennes
adresses, et seulement ensuite supprimer le WordPress.

Hors périmètre de ce dépôt : le « Depuis 10 ans » de `q-leap.eu` (chantier 09), qui contredit le
copyright 2012 de ce site-là.

## Contrôle n°3 : la case cochée qui ne partait nulle part (2026-08-26)

`Documentations/Audit_Q-Bot_Controle3_Note_Strategique.pdf` (16 pages, 6,5 → 6,6 sur 10, et
7,6 → 7,8 sur le périmètre auditable). **`Audit_Q-Bot_Controle_Note_Strategique.pdf` a été
renversé en `…Controle2…` : c'est le MÊME fichier** (empreinte identique), déjà traité le
2026-08-25. Le seul document neuf est le n°3.

Sa méthode a changé, et c'est ce qui le rend utile : au lieu de sonder des adresses choisies à
la main, il a demandé à GitHub la liste des 200 fichiers du dépôt et testé chacun contre ce que
l'hébergement sert. Résultat : **138 fichiers servis, tous légitimes, 62 non servis, et la
liste correspond exactement à `_config.yml`.** Le chantier 01 du 2026-08-25 est donc vérifié,
pas seulement appliqué. Les cinq corrections courtes de la veille sont confirmées refermées,
et l'audit donne raison au dépôt contre sa propre recommandation sur la FAQ (l'attribut
`hidden` posé par le script et jamais écrit dans la page).

**Deux points de l'audit sont à écarter, et il le dit lui-même.** Le dépôt public reste un
arbitrage budgétaire (Pages sur dépôt privé demande un plan payant) : il ne le compte pas comme
un défaut puisqu'il est documenté dans `llms.txt` et en tête de `_config.yml`. Et le « Depuis
10 ans » de `q-leap.eu` est hors de ce dépôt.

### QUATRE FORMULAIRES SUR SIX NE RECUEILLAIENT AUCUN CONSENTEMENT EXPLOITABLE

Le point neuf, et le seul sérieux. Il est antérieur à l'audit précédent, qui ne l'avait pas vu.

**Le cas le plus grave est celui des deux accueils, parce qu'il est invisible.** Le bloc de
consentement était posé juste **après** `</form>` : la case s'affichait, portait sa phrase et
son lien vers la politique de confidentialité, le visiteur la cochait et croyait avoir donné
son accord. Elle n'appartenait à aucun des trois chemins du module 15, ce qui a été mesuré dans
le navigateur avant correction :

- **repli courrier** : le message est composé depuis `form.elements`, la case n'y est pas ;
- **envoi direct** (après branchement) : `new FormData(form)` ne la contient pas ;
- **validation** : `form.checkValidity()` ne la voit pas, et elle n'était pas `required`.

Une case cochée dont l'état ne part nulle part est **pire que pas de case** : ni consentement
recueilli, ni absence de consentement assumée, et aucune trace de ce que le visiteur a accepté.
Les deux index de blog, eux, n'avaient **rien du tout** : un champ e-mail et un bouton, le seul
endroit du site qui demandait une adresse sans dire ce qu'elle devient.

Ce qui est en place, sur les six formulaires :

- le bloc de consentement est **DANS** le `<form>`, et la case est **`required`**. Sans
  `required` le déplacement ne suffit pas : la case part bien, mais vide ;
- les deux index de blog reçoivent le bloc de l'accueil, **mot pour mot**, mention Sendinblue
  comprise. Rien de neuf n'a été rédigé, et les chemins relatifs sont les mêmes
  (`confidentialite/` à la racine, `privacy/` sous `en/`) ;
- **les cases reçoivent un `id`, et le module 15 lit désormais `el.labels`.** C'était le
  troisième défaut : la recherche se faisait par `label[for="…"]` construit à la main, or les
  mentions de consentement du site ont un libellé qui **enveloppe** son champ. Sans `id`, on
  retombait sur l'attribut `name` et le courrier portait « consent : oui » au lieu de la phrase
  acceptée. Pour une trace de consentement c'est la phrase qui a de la valeur, pas le mot.
  `el.labels` reconnaît les deux formes, donc le repli ne dépend plus des `id` ;
- les espaces du libellé sont ramenés à un seul : une mention écrite sur plusieurs lignes de
  source insérait ses retours à la ligne dans le corps du courrier et cassait le « un champ par
  ligne ».

**« AVANT LE BOUTON » N'A PAS ÉTÉ SUIVI À LA LETTRE, ET C'EST DÉLIBÉRÉ.** L'audit demande de
placer le bloc avant le bouton d'envoi. Sur la bande newsletter, le champ et le bouton sont une
**rangée** : insérer le consentement entre les deux le fait passer à la ligne et descend le
bouton sur une troisième ligne, ce qui rallonge une bande dont la compacité a été travaillée
(elle était passée de 450 à 325 px le 2026-08-10). Surtout, l'ordre visuel serait alors champ,
consentement, bouton **à la lecture**, mais champ, bouton, consentement dans le DOM si l'on
compense en CSS : c'est précisément le décalage entre ordre de focus et ordre visuel que
WCAG 2.4.3 interdit. Le bloc est donc posé après la rangée, où **l'ordre de focus et l'ordre de
lecture coïncident** (mesuré : `email → submit → consent`), et `required` rend l'ordre inoffensif.
Vérifié dans le navigateur : envoyer sans cocher est **bloqué**, et le navigateur pose de
lui-même le focus sur la case.

Une seule ligne de CSS était nécessaire : `.newsletter__form .newsletter__consent
{ flex-basis: 100%; margin-top: 2px; }`. La première moitié fait passer le bloc à la ligne au
lieu de rétrécir le champ de saisie (même piège, même correctif que `.form-status` juste
au-dessus) ; la seconde compense les 12 px de `gap` qu'apporte la rangée wrappée, sans quoi la
bande gagnait 12 px de haut. Mesuré à 1440 / 900 / 390 px sur les quatre pages : rangée
préservée, champ toujours à 490 px, consentement à 14 px sous la rangée comme avant, bande
identique (414 px), case de 20 × 20 px dans un libellé cliquable, **0 débordement horizontal**.

Contrôle final : les six formulaires transmettent la case dans les trois chemins, la ligne de
courrier porte la phrase complète dans les deux langues, `go-live.py --endpoint` renseigne
toujours **6 formulaires sur 6** et retire les 6 notes d'attente, et les six pages passent le
balayage (normal et mouvement réduit) sans révélation invisible, sans défaut de contraste sur la
bande, sans débordement et sans erreur console.

### Les deux nombres périmés des scripts, désormais dérivés

`go-live.py` annonçait « VÉRIFIER LES 34 REDIRECTIONS » et « Point de départ : 0 sur 29 » là où
il y en a **52** et **28**. Les scripts, eux, étaient justes : ils lisent la vraie liste. C'était
le texte destiné à l'humain qui avait vieilli, et c'est le pire endroit pour un chiffre faux,
puisqu'il se lit le jour de la bascule.

Ils ne sont plus écrits à la main : `RESTE_MANUEL` est une f-string alimentée par
`len(REDIRECTIONS)` et par le compte de `<loc>` de `sitemap.xml`. Le docstring de
`verif-redirections.py` **ne porte plus de nombre du tout** (un docstring de module ne peut pas
être une f-string) : il renvoie à `redirections_map.py`, et le compte réel est imprimé à
l'exécution. `bump-assets.py` parlait de 29 pages, il y en a 30 (les 28 du plan de site, plus
`404.html` et `admin/index.html`).

### Laissé au client

**La parité des remerciements de l'article sur les tokens.** L'audit mesure −10 % de mots en
anglais sur les 14 paires de pages, ce qui est l'écart naturel entre les deux langues et n'est
pas un défaut. Une seule paire sort de la fourchette, à −31 % : « Remerciements » compte 236 mots
et nomme **14 contributeurs**, « Acknowledgements » en compte 46 et ne nomme que Hubert
Schumacher. Des personnes nommées construisent l'autorité d'une page, et le français le fait
déjà. **ARBITRÉ PAR LE CLIENT LE 2026-08-26 : la version anglaise reste telle quelle.**
L'abrègement est donc voulu. Ne pas y revenir, et ne pas « aligner » l'anglais sur la liste
française au motif de la parité : c'est un choix, pas une traduction abrégée par oubli.

## La newsletter est branchée sur le vrai Brevo du client (2026-08-26)

Question posée : « il y avait pas un formspree ou autre sur le site live ? ». Relevé dans un
navigateur, en-tête `Accept-Language` fixé par langue. Réponse en deux moitiés qui ne se
ressemblent pas.

**LA NEWSLETTER : OUI, UN ENDPOINT BREVO, ET IL RÉPOND ENCORE.**
`https://279f6284.sibforms.com/serve/MUIEAElAEknQ…` (244 caractères), **le même dans les deux
langues**, seul le champ caché `locale` change. Confirmation au passage : notre phrase de
consentement est mot pour mot le libellé `OPT_IN` du live, ce n'était pas une reconstitution.

**LE CONTACT : NON, ET IL N'Y A RIEN À RÉCUPÉRER.** Le live le traite avec **Contact Form 7**,
un plugin *dans* le WordPress (`_wpcf7=3034`), qui **meurt à l'étape 12 de la séquence du jour
J**, quand le WordPress est supprimé. C'est donc le seul endpoint qui reste à fournir, et c'est
lui qui est chez les managers. Le formulaire du live n'a d'ailleurs que 3 champs contre nos 7.

### Ce qui a été mesuré avant de câbler, et une réserve à lever

- **endpoint vivant et CORS ouvert** : POST depuis une autre origine, `type: 'cors'`, HTTP 200,
  `{"success":true}`, réponse lisible. Le `fetch` du module 15 l'atteint donc directement, sans
  navigation ni `mode: 'no-cors'`. Sonde faite **pot de miel REMPLI**, ce que Brevo écarte par
  définition : aucun inscrit créé ;
- **LE CAPTCHA EST TRANCHÉ, ET IL BLOQUE (mesuré le 2026-08-26).** Brevo l'impose côté serveur :
  un envoi sans jeton reçoit **HTTP 400** et
  `{"success":false,"errors":{"g-recaptcha-response":…}}`. Le `{"success":true}` de la première
  sonde était bien le court-circuit du pot de miel, comme soupçonné : simuler le succès est
  précisément ce que fait un pot de miel, et c'est pourquoi une sonde à pot de miel rempli ne
  peut JAMAIS valider un endpoint. Le témoin le montre côte à côte : pot rempli 200, pot vide
  400, même charge par ailleurs. Sitekey du live : `6LfFzw4jAAAAAH1LvdGfzojE7PbpDnCMDqpHKNv5` ;
- **RÉSERVE À LEVER, et c'est le piège des blocs masqués qui remonte.** La section newsletter du
  live est **désactivée** : `display:none` sur sa section Elementor, dans les deux langues, et le
  mot « newsletter » n'apparaît pas du tout dans `document.body.innerText`. La liste Brevo
  derrière cet endpoint n'est donc peut-être plus relevée. Ce n'est pas une raison de ne pas
  câbler (le formulaire existe sur NOTRE site, et le repli courrier n'est pas meilleur), mais
  c'est à confirmer par le client. Ne pas conclure « endpoint vivant » de « HTTP 200 » : les deux
  ne disent pas la même chose.

### Le renommage des champs vit dans le JS, jamais dans le balisage

Brevo impose `EMAIL`, `OPT_IN` **à la valeur « 1 »** (et non le « on » par défaut d'une case sans
attribut `value`), un pot de miel `email_address_check` qui doit partir **vide**, et `locale`.
Son endpoint est déclaré en `application/x-www-form-urlencoded`, **pas en multipart**.

Le site garde `email` et `consent` : ce sont les noms dont dépendent le repli courrier et la
validation, et les renommer dans le HTML enfermerait le balisage dans un fournisseur. La
correspondance est donc une table `PROFILS` du module 15, et le formulaire déclare son profil par
`data-endpoint-kind="brevo"` plus `data-locale`. Sans profil, le comportement d'avant ne change
pas : `FormData` en multipart, ce qu'attendent Formspree et compagnie.

`charge(form)` rend un `URLSearchParams` quand le profil le demande, et **on ne pose pas de
`Content-Type` à la main** : `fetch` le déduit de l'objet. Les deux valeurs restent des en-têtes
autorisés sans pré-vol CORS, ce qui est ce qui permet de lire la réponse.

Le pot de miel est en **`display: none`** (classe `.form-honeypot`) et non en `.visually-hidden` :
la seconde laisse le champ dans l'ordre de tabulation et dans l'arbre d'accessibilité, où il n'a
rien à faire. Un champ en `display:none` **est bien envoyé**, seul `disabled` l'exclurait.

Charge interceptée avant départ, sur les quatre pages :
`EMAIL=…&email_address_check=&OPT_IN=1&locale=fr|en`, en urlencoded. Échec serveur simulé (500) :
message d'erreur affiché et bouton réactivé, donc pas de succès silencieux. Sans cocher la case :
**0 envoi parti**. Mise en page identique au pixel avant/après (bande à 414 px, champ à 490 px),
le pot de miel n'occupe rien.

### Effet de bord, et c'est une correction

`go-live.py --endpoint` posait **la même URL sur les six** formulaires, alors qu'une inscription
newsletter et une demande de démo ne vont pas au même endroit. Les quatre newsletters n'étant plus
vides, il ne touche plus que **les deux contacts**, et retire **2** notes d'attente au lieu de 6.
Vérifié en simulation. Sa documentation, son aide de ligne de commande et son rappel de fin
d'exécution disent désormais lesquels restent. `llms.txt` aussi.

### Conséquence : le repli courrier devient le FILET de l'échec, plus seulement l'état initial

Le refus de Brevo a mis à nu un défaut du module 15 qui existait depuis sa création : un endpoint
qui refuse laissait le visiteur devant « L'envoi a échoué » **et rien d'autre**. Un cul-de-sac,
alors que le site sait parfaitement composer le message. Constaté en vrai par le client sur la
bande newsletter.

`versCourrier()` sert donc maintenant les deux cas : « pas d'endpoint » et « l'endpoint a
refusé ». `T.erreur` n'avait plus d'appelant et a été fusionnée dans le nouveau message, pour que
l'adresse reste écrite noir sur blanc **au cas où aucun logiciel de courrier ne s'ouvre** (un
téléphone sans compte mail ne fait rien d'un `mailto:`). État `info` et non `error` : de son point
de vue, le visiteur a une issue qui fonctionne.

Vérifié en rejouant **la réponse réelle de Brevo** (400 + son corps JSON exact) sur les quatre
pages : message de repli affiché dans les deux langues, bouton réactivé, et le succès 200 continue
d'afficher la confirmation. Le `mailto` lui-même n'est pas interceptable en sonde
(`window.location.href` n'est pas redéfinissable dans Chrome) mais le message affiché est produit
DANS `versCourrier`, juste après la ligne de navigation, et le client a constaté l'ouverture de sa
boîte mail en vrai.

**L'ENDPOINT BREVO EST DONC LAISSÉ EN PLACE alors qu'il refuse aujourd'hui**, et c'est délibéré :
le visiteur retrouve exactement le comportement d'avant (courrier prérempli), et le jour où le
captcha est désactivé sur le formulaire Brevo, les quatre newsletters fonctionnent **sans une
ligne à changer**. Ne pas « corriger » cet état en revidant `data-endpoint`.

Les contournements, dans l'ordre de préférence, si la question revient :

1. **désactiver le reCAPTCHA sur ce formulaire depuis le back-office Brevo.** Notre pot de miel
   reste en place, donc la protection anti-robot ne disparaît pas ;
2. **créer un formulaire Brevo neuf sans captcha** et remplacer l'URL, si le réglage est
   introuvable sur l'ancien ;
3. **implémenter reCAPTCHA sur nos pages : À ÉCARTER.** Cela rouvrirait une requête vers
   `www.google.com` sur quatre pages, alors que la passe du 2026-08-25 a supprimé **toutes** les
   dépendances tierces du site (Roboto, model-viewer, Draco), et cela chargerait un traceur Google
   avant tout consentement, exactement le problème réglé par le chargement au clic de la carte de
   contact. La clé reCAPTCHA est en plus liée à un domaine, donc intestable en local ;
4. **l'API Brevo : À ÉCARTER.** Elle demande une clé d'API, qui n'a rien à faire dans une page
   publique.

## Le formulaire de contact part sur contact@q-leap.eu (2026-08-26)

Demande : « tu peux pas faire un formulaire de contact propre qui pointe vers contact@q-leap.eu
et qui est fonctionnel seul ? »

**LA CONTRAINTE DURE, À REDIRE À CHAQUE FOIS QUE LA QUESTION REVIENT : un site statique ne peut
pas envoyer de courrier.** Il n'y a pas de serveur, donc un formulaire qui part vraiment doit
poster vers quelque chose qui n'est pas ce site. « Fonctionnel seul, sans aucun tiers » n'a
qu'une implémentation possible, le `mailto:`, et c'est exactement ce que fait le module 15. Tout
le reste (Formspree, FormSubmit, Brevo, une fonction serverless) est un relais, donc un
sous-traitant de données, donc une décision du client et pas un choix technique.

**Ce que la demande a révélé : `contact@q-leap.eu` est déjà l'adresse des quatre pages légales**
(reprises du live), alors que les six formulaires partaient sur `bot@q-leap.eu`. Les formulaires
étaient les seuls à ne pas la suivre. Ce n'était donc pas une préférence, c'était une
incohérence.

### La destination est celle du formulaire, plus une constante du script

`data-mailto` sur le `<form>`, `bot@q-leap.eu` par défaut. Les deux formulaires de contact
portent `data-mailto="contact@q-leap.eu"` ; les quatre newsletters gardent le défaut, parce
qu'une inscription et une demande de démo ne vont pas au même endroit. Le message d'échec
contient un jeton `{MAIL}` remplacé à l'exécution, sinon il aurait annoncé l'adresse du script
et non celle du formulaire.

**Le repli sans JavaScript a suivi.** Il promettait `bot@q-leap.eu` dans le `<noscript>` du
formulaire : deux adresses pour un même geste selon que JavaScript tourne ou non. Corrigé sur
les deux pages.

**Les 180 autres `bot@q-leap.eu` du site n'ont PAS été touchés** (métadonnées, JSON-LD, bloc de
coordonnées, pieds de page). C'est l'adresse publiée de Q-Bot, et la changer partout est une
décision éditoriale du client, pas une conséquence de ce lot. À lui arbitrer.

### Deux défauts du courrier corrigés au passage

- **une liste déroulante partait en CODE et non en clair** : le message disait « Sujet : demo »
  là où le visiteur avait lu « Demande de démonstration ». `corps()` prend désormais le libellé
  de l'option choisie. Le destinataire doit lire ce que le visiteur a vu, c'est le même principe
  que le libellé de consentement du 2026-08-26 ;
- **le sujet du courrier ne disait pas le motif.** Il vaut maintenant « Demande via le site
  Q-Bot : Questions tarifaires », donc la demande se trie sans ouvrir le message.

Vérifié sur les deux langues : destination et `<noscript>` concordants, sujet qualifié, et le
corps liste les sept champs dans les mots du formulaire, phrase de consentement comprise.

### Les relais possibles, et pourquoi aucun n'a été branché

À présenter au client, pas à choisir à sa place :

1. **`mailto:` (en place aujourd'hui)** : zéro tiers, zéro compte, aucune donnée qui transite.
   Coût : le visiteur doit appuyer sur « envoyer » dans son logiciel, et un téléphone sans compte
   mail ne fait rien d'un `mailto:` ;
2. **FormSubmit** : `data-endpoint="https://formsubmit.co/contact@q-leap.eu"` suffirait, sans
   compte, avec un seul clic d'activation dans un courrier envoyé à cette adresse. **Mais c'est
   un sous-traitant hors UE**, alors que la politique de confidentialité du site ne nomme que
   Sendinblue. Question de conformité, donc décision du client ;
3. **une fonction serverless (Cloudflare Worker) relayant vers l'API Brevo** : la clé reste côté
   serveur, les données restent chez un fournisseur que le client a déjà. C'est l'architecture
   correcte, elle demande un compte Cloudflare gratuit et une vingtaine de lignes ;
4. **l'API Brevo appelée depuis la page : À ÉCARTER**, elle demande une clé d'API dans une page
   publique.

Le jour où l'un des trois est choisi, c'est **un seul attribut** à renseigner
(`tools/go-live.py --endpoint`), et le repli courrier reste le filet en cas de refus.

### Le bloc de secours : le `mailto:` cesse d'échouer en silence (2026-08-26)

Demande : « fais-moi la solution la plus simple où tu peux tout faire toi sans que je touche ».

**RÉPONSE HONNÊTE, À REDONNER TELLE QUELLE SI LA QUESTION REVIENT : aucun relais ne peut être mis
en place sans le client.** FormSubmit demande un clic de confirmation dans la boîte
`contact@q-leap.eu`, Cloudflare et Formspree demandent un compte. Créer un compte auprès d'un
sous-traitant de données au nom du client n'est pas une décision technique. Ce qui pouvait être
fait seul, c'est rendre fiable le seul chemin qui ne dépend de personne.

**Le défaut réparé était réel et invisible.** Sur un poste sans logiciel de courrier associé
(webmail, téléphone sans compte configuré), un `mailto:` **ne fait rien du tout** : le visiteur a
rempli sept champs, cliqué, et son écran n'a pas bougé. C'est exactement la famille de défauts
que le module 15 avait été écrit pour supprimer, et il en restait un, au bout de la chaîne.

Le message composé est donc désormais aussi **présenté** : un `.form-relay` avec le texte complet
(destinataire, objet, les champs), un bouton de copie, et l'adresse en lien. Rien n'est envoyé,
rien ne quitte la page, aucun tiers n'est appelé : c'est le même texte que le courrier, montré au
lieu d'être seulement passé au système.

Quatre points à ne pas défaire :

- **le bloc est construit par le script, jamais écrit dans les six pages.** C'est un état
  d'exception, il n'a pas à peser sur le balisage servi. Vérifié : `.form-relay` **absent** du
  DOM avant tout envoi, et absent aussi après un succès ;
- **la sélection du texte précède toute tentative de copie.** Si les deux mécanismes échouent
  (contexte non sécurisé, permission refusée), le texte reste sélectionné et il n'y a plus qu'à
  faire Cmd+C. Un plancher, jamais un bouton qui ne fait rien. Ordre : API presse-papier, puis
  `execCommand`, puis la sélection seule ;
- **tout est en `currentColor` et `inherit`.** Ce bloc vit sur la bande newsletter (fond teal,
  texte noir de charte) ET dans la carte du formulaire de contact (fond sombre, texte clair). Une
  couleur écrite en dur serait juste dans l'un et illisible dans l'autre : c'est le défaut relevé
  16 fois par l'audit du 2026-08-11. Mesuré sur les deux fonds : **6,81 à 21:1**, tout passe AA ;
- **la zone de texte garde un fond clair et un texte sombre** dans les deux contextes. C'est un
  champ de formulaire comme ceux au-dessus, et on y lit du texte dense.

Contrôlé : copie réellement présente dans le presse-papier (lue par `clipboard.readText`), les
deux langues, libellé du bouton qui confirme puis revient, cible de 142 × 38 px, 0 débordement
horizontal à 390 px, 0 erreur console. Le contenu copié est autonome : `À`, `Objet`, puis les
champs, donc un collage dans n'importe quel webmail est complet.

### ARBITRÉ PAR LE CLIENT LE 2026-08-26 : pas de sous-traitant tiers pour le contact

« Ne me fais pas passer par des sites tiers pour contact, tant pis ça ouvrira une boîte mail. »

**Le point n'est donc plus ouvert, il est TRANCHÉ.** Les deux formulaires de contact partent par
le logiciel de courrier du visiteur, définitivement. `data-endpoint` reste vide **à dessein**, et
il ne faut ni y remettre une URL, ni traiter cela comme une tâche du jour J, ni le rappeler au
client comme un point en attente. La note `ROSOAI-EN-ATTENTE` de ces deux pages a été remplacée
par la décision, `go-live.py` et `llms.txt` disent désormais que c'est un choix et non un oubli,
et `--endpoint` reste disponible seulement au cas où la décision change.

Ce que ce statut définitif a obligé à traiter, parce qu'un provisoire peut vivre avec un cas
limite et un chemin permanent non :

- **la longueur d'un `mailto:` n'est pas illimitée.** Mesuré sur ce formulaire : une demande de
  1 000 caractères produit une URL de **1 964**, et Outlook comme les gestionnaires Windows
  tronquent vers 2 048. Un message tronqué en silence est précisément le défaut que le module 15
  existe pour supprimer. **On ne dégrade PAS pour autant** : envoyer un objet sans corps
  pénaliserait tout le monde pour protéger une minorité. Le message part entier, et au-delà de
  `MAILTO_MAX` (1900, marge prise sur l'objet, l'adresse et l'encodage du protocole) le visiteur
  est **averti** qu'il doit vérifier, avec le texte copiable juste en dessous. Prévenir plutôt
  que tronquer ;
- **le bouton disait « Envoyer ma demande » alors que le site n'envoie rien.** Il compose un
  message et le passe au logiciel du visiteur. Une ligne `.form-hint` le dit **avant** le clic
  (« En envoyant, votre logiciel de courrier s'ouvre avec le message prérempli »), plutôt que de
  le laisser découvrir après. Même exigence que le `<noscript>` juste en dessous. Le libellé du
  bouton, lui, n'est pas touché : c'est du texte du live.

Contrôlé sur les deux langues : ligne visible avant le clic, message court qui donne l'invite
normale, message long qui déclenche l'avertissement, bloc copiable présent dans les deux cas,
0 débordement, 0 erreur console. Et les notes « endpoint en attente » ne subsistent plus que sur
le sujet des références clients, qui est un autre point, toujours ouvert lui.

## Le premier guide : automatiser une authentification LuxTrust (2026-08-26)

Première page du plan de contenu de l'audit RosoAI, et le P1 qu'il classe en tête : sur
« automatiser l'authentification LuxTrust » il a vérifié qu'aucun contenu concurrent n'occupe la
page de résultats, et c'est le seul sujet sur lequel le nom sort déjà spontanément d'une IA, par
l'article ITnation. Un territoire vide où l'on est déjà nommé.

`automatiser-authentification-luxtrust.html` et `en/automate-luxtrust-authentication.html` sont
**générées par `tools/gen-guide-luxtrust.py`**, un gabarit et deux jeux de textes. Même choix que
`gen-legal.py` et les pages de cas d'usage, pour la même raison : deux pages écrites l'une après
l'autre divergent. **Les slugs portent la requête visée** dans chaque langue, et l'anglaise ne
porte pas un slug français (premier jet corrigé).

**L'HABILLAGE EST EXTRAIT DE `cas-usage.html`, JAMAIS RETAPÉ.** En-tête, barre de navigation, pied
de page et fin de document sont découpés dans la page donneuse, avec deux retouches : l'état
courant du menu est retiré (la nouvelle page n'y figure pas) et l'entrée « Cas d'usage » du pied
de page retrouve son lien. Conséquence utile : si le pied de page change, une régénération suffit.

### Ce que le format applique, et qui vient de l'audit

Le guide, pas la page produit : sur les cinq pages de résultats analysées, c'est le guide qui se
classe, cinq fois sur cinq, et aucune page produit n'apparaît. Les quatre marques du format :

- **chaque `<h2>` est une question, suivie d'une réponse autonome.** Mesuré : **14 capsules sur
  14 dans la fenêtre de 40 à 60 mots** (40 à 53 selon les sections) ;
- **une source vérifiable tous les 150 à 200 mots** : RFC 6238 pour TOTP, la page que Selenium
  consacre à la 2FA, la documentation ADB d'Android, LuxTrust et itsme. Les cinq suivies dans un
  navigateur, toutes en 200 ;
- **une date de mise à jour visible**, en `<time>` sous le chapeau (`.guide-date`) ;
- ~~le courage de dire quand le concurrent gagne~~ : **RETIRÉ SUR DEMANDE DU CLIENT LE
  2026-08-26.** La section « Dans quels cas un robot n'est pas la bonne réponse » envoyait le
  lecteur vers une bibliothèque TOTP gratuite pour Google et Microsoft Authenticator. Le client
  ne veut pas publier un texte qui déconseille son propre produit, et c'est sa décision : **ne
  pas la réintroduire, sur ce guide ni sur les suivants.**
  Ce qui reste de l'exigence d'honnêteté du format, et qui suffit : la section « Qu'est-ce que
  cela n'automatise pas ? » énonce le périmètre COMME UNE LIMITE (Android seulement, pas d'iOS,
  un appareil filaire par boîtier) et la page porte sa mention de non-affiliation à LuxTrust.
  Le guide passe de 7 à 6 sections ; rien n'y renvoyait, donc aucun raccord à reprendre, et le
  fait technique que la section portait (un code TOTP se recalcule depuis un secret partagé) reste
  énoncé dans la première section, où il sert à expliquer pourquoi LuxTrust est différent.
  `llms.txt` a été reprise aussi : elle annonçait cette section noir sur blanc aux assistants IA.

**Deux affirmations à ne jamais retourner.** La page énonce le périmètre **comme une limite**
(Android seulement, pas d'iOS, un appareil filaire par boîtier), et elle porte une mention de
**non-affiliation** : Q-Bot est un produit de Q-Leap S.A., il n'est ni édité, ni distribué, ni
approuvé par LuxTrust. `llms.txt` reprend cette non-affiliation dans ses faits vérifiés, avec la
consigne de ne pas décrire le produit comme un produit ou un partenaire LuxTrust.

**Le `TechArticle` déclare `author: Organization`, pas `Person`.** Le dépôt attribue quatre
articles à Sylvain Perez, mais ce guide n'a pas été relu par lui : signer un texte au nom d'une
personne réelle est une affirmation sur elle. À basculer sur `Person` le jour où il le valide.

### Deux pièges rencontrés dans le générateur, tous deux déjà connus du dépôt

1. **les `hreflang` ne se remplacent PAS par un bloc de trois lignes.** Le donneur anglais les
   écrit dans un autre ordre (`en`, `fr`, `x-default`) : le motif ordonné ne correspondait à rien
   et la page anglaise a été écrite avec les `hreflang` de la page des cas d'usage, **en silence**.
   Le remplacement se fait par attribut. Même famille que le motif multi-lignes qui échouait sur
   `en/technical-specs.html` ;
2. **l'ordre des remplacements compte.** Mon premier correctif renommait les slugs avant de
   toucher au bloc `hreflang`, qui contenait les anciennes URL : le motif ne correspondait plus.
3. le contrôle de cadratin porte sur le document **commentaires retirés** : ceux de l'habillage
   extrait en contiennent encore, et ils ne sont pas lus par le visiteur.

### Intendance, et les liens entrants

Le plan du site passe de 28 à **30 URL** avec leurs paires hreflang, le décompte de `robots.txt`
suit, et `llms.txt` reçoit une section **Guides** qui résume l'argument, y compris le « quand un
robot n'est pas la réponse » : c'est ce qui rend la page citable plutôt que promotionnelle. Deux
mentions de tarif périmées y ont été corrigées au passage (« pricing » sur l'accueil, « Order /
pricing » devenu « Demo request »).

**Quatre liens entrants, pas zéro** : un bouton sur les deux fiches techniques, à côté de celui
des exemples d'appel, et un lien en pleine phrase dans le cas LuxTrust des deux pages de cas
d'usage. **La page n'entre PAS dans la barre de navigation** : elle porte déjà quatre entrées, un
bouton et le sélecteur de langue, et la passe du 2026-08-20 a vérifié qu'elle tient de 901 à
1440 px dans cet état. Une entrée « Guides » se justifiera quand il y en aura deux ou trois.

Contrôles : 1 `h1` par page, 0 saut de niveau, **0 défaut de contraste**, 0 débordement horizontal
à 375 / 390 / 768 / 900 / 1024 / 1440 / 2560 px, 0 révélation restée invisible en normal comme en
mouvement réduit, 0 erreur console, **85 pages balayées et 0 lien interne cassé**, et
**79 blocs JSON-LD valides** dont le nouveau `TechArticle`. Le titre tombe au pixel sur le logo,
au même écart de 7 px que `cas-usage` et `caracteristiques` (c'est la zone d'exclusion du logo,
pas un défaut). Environ 1 300 mots par page.

Note d'outillage : **`luxtrust.com` limite le débit**. Il a répondu `ERR_CONNECTION_REFUSED`
pendant un balayage de liens, puis 200 six secondes plus tard. Un contrôle de liens qui le
signale mort doit être rejoué seul avant qu'on y touche.

### Les sept autres contenus du plan restent à écrire

Trois P1 (celui-ci est le troisième), trois P2, deux P3. Il manque encore la page « Faut-il
désactiver la 2FA en environnement de test ? », la page pilier « Automatiser la double
authentification dans vos tests », et la version itsme de ce guide pour le marché belge.

### Contre-vérification des chantiers 05, 06 et 10 (2026-08-26)

Demandés en correction, et les trois étaient déjà faits. **La cause était ma façon de les
présenter** : dans le tableau de recoupement, j'avais écrit des mesures brutes (« 0 fois dans la
source servie », « 6 cibles distinctes ») là où les autres lignes disaient « fait ». Un zéro se
lit comme un manque. Une ligne de contrôle doit conclure, pas seulement mesurer.

La contre-vérification a quand même valu, parce que mon contrôle d'origine était superficiel
(des comptages `grep`) et que celui-ci exécute les contrôles que le plan prescrit :

- **05, l'accessibilité de la FAQ, vérifié AU CLAVIER sur les six pages à accordéon** et non sur
  la seule page FAQ : `faq`, `en/faq`, `commandez`, `en/order`, `index`, `en/index`. Relevé sur
  **48 questions** : 0 réponse sans `id`, 0 bouton dont `aria-controls` ne désigne pas sa
  réponse, 0 réponse sans `aria-labelledby`, 0 bouton sans `aria-expanded`, **0 réponse fermée
  laissée non masquée**, et **0 focus tombant dans une réponse fermée** (48 boutons atteignables,
  et rien d'autre). L'ouverture donne une hauteur réelle (314 px sur la FAQ française), donc le
  piège de l'ordre des deux lignes n'est pas retombé ;
- **06** : le contrôle que le plan prescrit lui-même, `grep seize faq.html en/faq.html`, ne
  renvoie rien, et `sixteen` non plus côté anglais. Aucun décompte périmé ailleurs dans le dépôt ;
- **10** : les quatre points, page par page. ITnation sur les deux articles Merkur, ADB sur les
  deux fiches techniques, Selenium / Cypress / Playwright sur les deux pages de cas d'usage, et
  le profil de Sylvain Perez sur `a-propos` / `en/about`, **dans le contenu visible** et pas
  seulement dans le JSON-LD.

**Un vrai défaut trouvé au passage, sur la page écrite le même jour.** Le guide LuxTrust nommait
Selenium, Cypress et Playwright et **ne liait que Selenium**, alors que le chantier 10 demande un
lien à la première mention de chacun. Les trois liens sont posés, dans le corps de la section qui
les nomme, dans les deux langues. Le guide compte désormais six sources extérieures.

Et la note du 2026-08-25 qui annonçait le lien LinkedIn « laissé ouvert » a été corrigée sur
place : il avait été posé. Une note qui dit « laissé ouvert » se revérifie avant d'être citée.

## Aucun client ne sera nommé, et le piège d'une suppression de bloc (2026-08-26)

Le bandeau de références est supprimé, cf. la section plus haut : le client a sollicité ses
clients, aucun n'a accepté. Trois choses parties ensemble, le balisage des deux accueils, le bloc
CSS `.trust-strip`, et l'entrée de `llms.txt` qui présentait le point comme ouvert.

**LE PIÈGE QUE CETTE SUPPRESSION M'A COÛTÉ, ET IL VAUT POUR TOUTE SUPPRESSION DE BLOC COMMENTÉ.**
Mon premier motif était, en `re.S` :

    <!--[^\n]*\n(?:.*?)<section class="trust-strip".*?</section>\n-->

Il a accroché **le premier commentaire du document**, celui du `<head>`, et supprimé **239 lignes**
des deux accueils, dont le lien vers la feuille de style. Restauré par `git checkout`. Trois
leçons, dans l'ordre d'utilité :

1. **on borne par une chaîne littérale relevée dans le fichier**, jamais par un `<!--` non ancré
   suivi d'un `.*?`. Ici : trouver le marqueur du bloc (`BANDEAU DE CONFIANCE`), puis remonter au
   `<!-- ═══` qui le précède avec `rindex`. C'est la règle « on n'retape pas, on extrait »
   appliquée aux BORNES et plus seulement au contenu ;
2. **les garde-fous par comptage se sont trompés trois fois de suite**, toujours pour la même
   raison : le commentaire supprimé citait lui-même `style.css` et `</section>`, donc les
   décomptes bougeaient de 2 et non de 1. Un garde-fou doit porter sur des **invariants de
   structure** (la balise de feuille de style est là, `<main>` est là, le document finit par
   `</html>`), pas sur des occurrences de texte ;
3. **et l'invariant doit être insensible à la profondeur** : les pages `en/` écrivent
   `../assets/css/style.css`, donc un invariant écrit en racine échoue sur elles. Même famille que
   les motifs multi-lignes qui échouent sur une seule des deux langues.

Vérifié après : 836 et 766 lignes (25 et 19 retirées), structure intacte, feuille de style
réellement appliquée (Roboto calculée sur `body`), 10 sections par accueil, 1 `h1`, 0 révélation
invisible, 0 débordement, 0 erreur console, et **aucun des sept noms dans
`document.body.innerText`** en normal comme en mouvement réduit.

Note d'environnement : le volume exFAT qui porte ce dépôt s'est **démonté en cours de commande**
pendant cette passe (« Working directory was deleted »), puis est revenu seul. Le commit n'était
pas passé, les fichiers l'étaient : après un incident de ce genre, **vérifier `git log` ET
`git status`** avant de refaire quoi que ce soit, sinon on rejoue des éditions déjà appliquées.

## La photo LuxTrust rétrécit, et le premier prototype change d'image (2026-08-26)

Deux retours du client, et deux natures de problème.

### 1. La photo LuxTrust était agrandie, pas « pixelisée » par hasard

`qbot-photo-dock.jpg` fait **699 x 860 pixels réels, et c'est tout ce qui existe** : elle est
découpée dans la brochure, qui est une image aplitie à 300 dpi. Il n'y a pas de version plus fine
à aller chercher, seulement un agrandissement. Mesuré dans son cadre de colonne, sur un écran à
densité 2 : **x1,63 à 1440 px, x1,94 à 1920, x2,03 à 2560**. Le client voyait donc une vraie
dégradation, pas une impression.

**PREMIER PLAFOND À 320 PX, INSUFFISANT.** Calcul : à densité 2 il faut au plus 699/2 = 349 px
affichés, et `.intro__image` agrandit son contenu de 1,08 au repos (la sur-échelle du parallaxe),
donc 349/1,08 = 323 px de cadre. Cela réglait la densité 2 (x0,99) mais laissait **x1,48 à
densité 3**, et le client a signalé qu'elle était « encore légèrement pixelisée ». La leçon est
qu'un plafond calculé pour densité 2 ne suffit pas : les téléphones et une partie des portables
sont à densité 3, et un zoom navigateur de 125 % produit le même effet.

**PLAFOND RETENU : 216 PX, ET CE NOMBRE TOMBE JUSTE DEUX FOIS.**

1. C'est la demande du client, « la même taille que le bloc texte correspondant ». Le bloc texte
   voisin mesure **286 px de haut** (relevé à 1440 et à 1920 px) ; un cadre de 216 px donne une
   image de 287 px, donc les deux colonnes ont la même hauteur **au pixel près**. À 2560 px le
   texte se resserre à 259 px, l'écart monte à 28 px, ce qui ne se voit pas ;
2. c'est aussi `699 / 3 / 1,08 = 216`, donc la largeur au-delà de laquelle l'image serait encore
   agrandie à **densité 3**. Relevé après : **x0,67 à densité 2 et x1,00 exactement à densité 3**,
   à 1440, 1920 et 2560 px. Il n'y a plus aucun agrandissement nulle part.

Conséquence acceptée : sur téléphone la photo est plus étroite que la colonne de texte. C'est le
prix de sa résolution réelle, et l'afficher plus large ne montre que du détail qui n'existe pas
dans le fichier.

**ET LE CADRE DOIT TOUCHER UNE GOUTTIÈRE.** Un bloc plus étroit que sa colonne ne doit pas
flotter entre les deux bords : mesuré sur les pages Démo, il restait 614 px de marge à gauche et
350 à droite, donc au milieu. La règle du dépôt autorise gauche ou droite et interdit le centre.

**LE SÉLECTEUR PORTE SUR `:last-child`, PAS SUR UN CONTENEUR NOMMÉ**, et c'est ce qui a coûté un
essai : les deux dispositions n'emploient pas la même grille. Les accueils utilisent
`.intro__grid` avec l'image en PREMIER (colonne de gauche), les pages Démo `.split-2` avec
l'image en SECOND (colonne de droite). Un premier essai visait `.intro__grid > …` et ne
s'appliquait donc nulle part où c'était nécessaire, sans erreur. `:last-child` décrit la
position, qui est ce qui compte. Borné au-delà de 768 px, le seuil auquel `.split-2` repasse à
une colonne. Vérifié à 390 / 768 / 769 / 900 / 1440 / 2560 px sur les quatre pages : chaque cadre
touche une gouttière, **aucun cas « au milieu »**, 0 débordement.

Le cadre reste **aligné à gauche** sur la gouttière : c'est la colonne qui garde sa largeur, pas
l'image qui se centre dedans, conformément à la règle du dépôt.

### 2. Le « premier prototype » montrait le second

Arbitré par le client le 2026-08-26 : l'image du portique (`qbot-proto-gen1.png`) est **le second
prototype**, et le premier est celui de la photo de Mathilde Magne publiée dans les articles de
blog. La carte « Génération 1 » des deux accueils montre donc maintenant ce boîtier, détouré.

Trois choses ont changé ensemble, et pas seulement l'image : l'`alt`, le corps de la carte (il
décrivait « un portique motorisé monté à la main, deux axes, un stylet capacitif ») et **le
chapeau de la section**, qui annonçait « Du portique assemblé dans nos locaux… ». Un seul des
trois oublié aurait laissé le texte contredire l'image. Contrôlé : 0 occurrence de « portique »
et de « gantry » sur les deux accueils.

Le nouveau texte ne s'appuie que sur ce qui est vérifiable et déjà publié par le client : « moins
de dix centimètres de côté » et « développé en interne dans les bureaux de Q-Leap » viennent de
l'article de blog qui porte cette photo, et le petit écran en façade est visible dessus. **Aucune
date n'est ajoutée**, conformément au choix de cette section.

`qbot-proto-gen1.png` n'est plus référencé nulle part ; le fichier reste sur le disque, comme le
veut l'usage du dépôt. **Le rail n'a pas gagné de quatrième carte** : sa géométrie est calculée
pour trois étapes (`--evo-fill: 0.5` est le milieu de trois, et pour quatre il faudrait
`index / (n − 1)`), et cela n'a pas été demandé.

### Le détourage : un fond VERT, et un piège de rééchantillonnage

`assets/img/blog/qbot-photo.webp` n'est pas sur fond blanc mais sur un **fond vert de studio**,
`(72, 112, 75)` uniforme sur les quatre bords. Conséquence directe : **une clé de luminance aurait
rendu transparent le texte blanc de l'afficheur**. C'est la teinte qui sépare, par la « verdeur »
`G − max(R, B)` : 37 pour le fond, un 99e centile à 0 pour l'objet.

Deux mesures faites AVANT d'écrire l'outil, et qui ont permis de se passer d'un remplissage par
proximité : aucun pixel de fond n'est isolé dans l'objet (les 245 138 sont tous atteints depuis le
bord, donc un seuil global ne peut pas trouer l'anneau métallique), et rien n'est légitimement
vert dans la photo (le bouton est rouge), donc le dé-débordement peut s'appliquer partout.

**LE PIÈGE, ET IL A COÛTÉ TROIS HYPOTHÈSES FAUSSES.** Un trait vert d'un pixel de large sur 36 de
haut subsistait au bord gauche du boîtier, à alpha 240. J'ai d'abord accusé la compression avec
perte du WebP (faux : le sans-perte coûtait 402 Ko pour rien), puis le sous-échantillonnage de
chrominance qui baverait depuis les pixels transparents (faux aussi : remplir le transparent avec
la couleur moyenne de l'objet n'a rien changé). La mesure étape par étape a donné la réponse :
c'est **Lanczos qui « sonne »**. Verdeur 0 après dé-débordement, 0 après recadrage, puis **255 sur
25 pixels après la réduction**. Bilinéaire et « box » n'ont pas ce défaut mais perdent du piqué.

Le correctif garde Lanczos et **réapplique le dé-débordement après la réduction**. Relevé sur le
fichier livré : verdeur composité **max 4,9, zéro pixel au-delà de 8**, et cela sur fond de carte,
sur fond de page et même sur blanc.

Leçon générale : **une opération de rééchantillonnage peut violer un invariant établi avant
elle.** Un contrôle de détourage doit se faire sur le fichier FINAL, composité sur le fond réel,
et non sur le tableau intermédiaire.

L'outil est versionné dans `tools/render/detourer-proto.py`, sortie
`assets/img/qbot-proto-1-boitier.webp` (760 x 687, 97 Ko, 2,5x le plus grand cadre mesuré).

Contrôles : les quatre pages touchées à 390 / 768 / 900 / 1440 / 2560 px, un seul `h1`, 0
révélation invisible, 0 débordement horizontal, 0 image cassée, 0 défaut de contraste, 0 erreur
console. Faux positif écarté au passage : une sonde qui lit `img.complete` juste après le
défilement signale `qbot-gen-actuelle.webp` comme cassée alors qu'elle est encore en cours de
chargement. **Un contrôle d'image en chargement différé doit attendre, ou lire `naturalWidth`
seulement quand `complete` est vrai.**

## La photo LuxTrust : pleine largeur sur téléphone, et la colonne se resserre (2026-08-26)

Deux retours du client sur le plafonnement de la veille : « remets-la en pleine largeur sur
mobile » et « ça fait un peu vide là ».

**AVANT DE GÉRER LE COMPROMIS, J'AI VÉRIFIÉ QU'IL EXISTAIT.** Les trois pages de la brochure dont
la photo est tirée sont des images **aplaties à 300 dpi**, et la photo n'y est qu'un petit encart
en haut de la page 1. Il n'existe donc aucune version plus fine : 699 x 860 est tout ce qu'il y a,
et la seule variable est la taille d'affichage. C'est ce contrôle qui autorise à arbitrer plutôt
qu'à chercher une meilleure source.

### Le vide : la colonne se resserre sur l'image

Mesuré après le seul plafonnement : 216 px d'image, **310 px de noir**, puis le texte au milieu de
la page. Le client avait raison, et la raison est précise : un écart de cette taille **ENTRE** deux
blocs liés se lit comme un manque, alors que le même espace **APRÈS** le texte se lit comme une
marge. La grille passe donc en `auto 1fr` (ou `1fr auto` selon le côté de l'image), et le vide
entre les deux blocs retombe à la gouttière de la grille : **80 px sur les accueils, 48 px sur les
pages Démo**. Seul le titre gagne en largeur ; le paragraphe garde sa mesure de lecture.

Fait avec `:has()`, donc **sans toucher au balisage des quatre pages**. Sans `:has()`, la grille
reste en deux colonnes égales, c'est-à-dire exactement l'état d'avant : dégradation gracieuse, pas
de mise en page cassée.

**LE PARAGRAPHE N'EST BRIDÉ QUE QUAND L'IMAGE EST À GAUCHE**, et c'est le point non évident. À
droite (pages Démo), le brider recréerait le trou : le reste tomberait entre le texte et l'image.
Leurs quatre paragraphes font 96 à 153 caractères, donc une ligne à pleine largeur, et une ligne
unique n'a pas de problème de mesure.

### Trois erreurs de ma part, toutes trouvées par la mesure

1. **le seuil n'était pas 900 px mais 768.** J'avais écrit `min-width: 901px` en me fiant à une
   note interne parlant de 900 : le relevé montre `.intro__grid` **encore à deux colonnes à
   769 px** (320,5 px chacune). Le plafond ne s'appliquait donc pas entre 769 et 900, où l'image
   restait agrandie 1,49 fois. Les deux grilles passent à une colonne à 768 ;
2. **mon premier sélecteur d'alignement visait le mauvais conteneur.** Les accueils utilisent
   `.intro__grid` (image en PREMIER), les pages Démo `.split-2` (image en SECOND). Une règle
   `.intro__grid > …` ne s'appliquait nulle part où c'était nécessaire, **sans erreur ni trace** ;
3. **la pleine largeur en une colonne donnait x3,34 sur tablette.** Le client demandait la pleine
   largeur « sur mobile » ; à 768 px en une colonne, la colonne monte à 720 px et l'agrandissement
   explose. D'où un plafond de **350 px dans la plage empilée**, qui est **sans effet sur un
   téléphone** (la colonne y fait 342 px, donc pleine largeur comme demandé) et ne mord que
   au-dessus. Autrement dit : la photo garde partout au plus la qualité qu'elle a sur un
   téléphone, jamais moins.

### Relevé final

| largeur | cadre | agrandissement | vide entre blocs | côté |
|---|---|---|---|---|
| 390 px, densité 3 | 342 (pleine largeur) | x1,59 | empilé | gauche |
| 600 et 768 px, densité 3 | 350 | x1,62 | empilé | gauche |
| 769 px et au-delà, densité 3 | 216 | **x1,00** | 80 / 48 px | gauche / droite |
| 1440 et 2560 px, densité 2 | 216 | **x0,67** | 80 / 48 px | gauche / droite |

Chaque cadre touche une gouttière, **aucun cas au milieu**, 0 débordement horizontal sur les
quatre pages aux huit largeurs testées.

**FAUX POSITIF ÉCARTÉ, ET C'EST LE MÊME PIÈGE QUE D'HABITUDE.** Un balayage en lot des 24
combinaisons a signalé jusqu'à 3 révélations restées invisibles. Rejouées isolément, **0 partout**,
y compris à la cadence grossière : ce n'était pas le pas de défilement mais le **délai de repos
final de 350 ms**, trop court pour les révélations échelonnées de la variante `card`, qui durent
plus de 400 ms avec leur décalage. Un balayage de révélations doit laisser **au moins 800 ms** au
repos avant de mesurer, et une remontée doit être rejouée seule avant d'être appelée régression.

## Le texte qui collait le filet, et une passe de lisibilité mesurée (2026-08-26)

Signalé par le client sur les cartes de cas d'usage : le volet « Le blocage » vient coller le
filet de séparation du chiffre-clé.

**LA MARGE ÉTAIT DÉCLARÉE ET N'AVAIT JAMAIS EXISTÉ.** `.usecase__fig` est un `<p>` dans
`.usecase`, et `.usecase p { margin: 0 }` vaut **(0,1,1)** contre **(0,1,0)** pour une classe
seule : le `margin: 20px 0 0` écrit dans la feuille était écrasé depuis toujours. Sélecteur
doublé en `.usecase .usecase__fig`, marge portée à 24 px. Relevé après, dans les deux langues et
aux deux largeurs : **24 px au-dessus du filet, 18 en dessous.**

**Deuxième occurrence du même piège** après `.newsletter .newsletter__legal`, et la passe en a
trouvé deux autres du même genre, invisibles à l'œil :

- **`.evo-card__link`** : la règle groupée de cibles tactiles (`.product-card a,
  .blog-card__title a, .evo-card__link { display: inline-block; padding: 3px 0 }`) lui faisait
  DEUX dégâts d'un coup. Le raccourci `padding: 3px 0` écrasait les 18 px séparant le lien du
  paragraphe, et `display: inline-block` écrasait son `inline-flex`, dont il a besoin pour centrer
  sa flèche. Il est sorti de la règle groupée et ne reçoit plus que la hauteur de cible manquante.
  Mesuré : 45 px de haut, donc au-delà des 24 px de WCAG 2.5.8, et `display: flex` retrouvé ;
- **`.guide-date`** : ma propre règle de la veille, écrasée par `.page-hero p`. Doublée.

### La sonde, et pourquoi la première version mentait

**SONDE A, l'espacement déclaré puis annulé.** On parcourt les RÈGLES une fois (pas les éléments,
sinon c'est quadratique) et, pour chaque règle qui déclare une marge ou un remplissage sur un
sélecteur à classe, on compare la valeur déclarée à la valeur calculée des éléments visés. 15
remontées, dont 4 réelles et 11 surcharges volontaires (requêtes média, cibles tactiles, rails
épinglés). C'est la sonde qui trouve cette famille entière.

**DEUX PIÈGES DE SONDE, ET LE PREMIER M'A FAIT CROIRE À UNE FEUILLE DE STYLE CASSÉE.**

1. **`if (r.cssRules)` est VRAI pour une règle de style ordinaire.** Depuis l'imbrication CSS,
   `CSSStyleRule` porte un `cssRules` vide mais bien présent : un parcours qui teste `cssRules`
   avant `selectorText` saute donc **toutes** les règles de style. Ma sonde annonçait « aucune
   règle ne mentionne cette classe » sur une feuille parfaitement chargée, et j'ai perdu deux
   étapes à vérifier qu'elle n'était pas tronquée. **On teste `selectorText` d'abord.**
2. **une sonde d'espacement doit mesurer du TEXTE, pas des boîtes.** La première version de la
   sonde B comparait le bord d'une carte au rectangle des éléments qu'elle contient : elle
   remontait 20 cas, dont la FAQ, alors que `.faq-item__answer p` porte 20 px de remplissage bas
   et que le texte est à 20 px du filet. Réécrite sur les rectangles réels des nœuds de texte
   (`Range.getClientRects`), elle donne **0 cas sous 8 px** sur 14 pages × 2 largeurs, accordéons
   ouverts.
   Et une sonde qui ne trouve rien doit prouver qu'elle voit quelque chose : relancée à 30 px,
   elle signale bien le `.usecase__fig` corrigé à 24. Sans ce contrôle de vivacité, « 0 défaut »
   ne vaut rien.

### La passe de lisibilité : cinq réglages, pas un redesign

Sonde C sur le texte réellement peint : taille sous 13 px, et interligne sous 1,35 pour du texte
de corps de 8 mots ou plus (les titres et les gros chiffres exclus, un interligne serré y est
voulu).

| Réglage | Avant | Après | Pourquoi |
|---|---|---|---|
| `h3, h4` interligne | 1,15 | **1,3** | à 20 et 16 px, 1,15 donne des lignes de 23 et 18 px, serré dès qu'un titre passe à la ligne, ce qu'il fait souvent dans une carte. Les h1 et h2 gardent 1,15 : à 32-56 px c'est justement ce qu'il faut |
| `.section-label` interligne | 1,15 | **1,45** | capitales espacées ; promue en `<h2>` elle prend l'interligne des titres et deux lignes se touchent presque |
| `.faq-item__question` interligne | 1,20 | **1,4** | un `<button>` n'hérite pas de l'interligne du corps et retombe sur le « normal » du navigateur |
| `.mv-explode__value`, `.faq-index__num` | 11 px | **12 px** | plancher de lisibilité |
| `.code-copy-btn` | 11,5 px | **12 px** | c'est une commande, pas une mention |

Résultat : **plus aucun texte sous 12 px** et un seul interligne à 1,30, qui est le nouveau
plancher. Les 12 px restants sont assumés (mention légale, badge, bouton de nav, code en chasse
fixe, note de la carte).

**UN CAS VÉRIFIÉ COMME VOULU, ET IL FAUT LE SAVOIR** : sous 400 px, `.nav__lang a` est en
`font-size: 0`, donc le code « FR » disparaît et il ne reste que le globe. C'est délibéré et
commenté dans la feuille (le remplissage porte alors la cible tactile de 24 px). Une sonde de
lisibilité le remontera toujours : ce n'est pas un défaut.

Contrôles : la contrainte dure de la carte épinglée est tenue (308 px au plus pour une fenêtre de
640, donc 332 px de marge) aux sept tailles d'écran du contrôle habituel, et **32 vues** (16 pages
× 390 et 1440 px) sans anomalie : un seul `h1`, 0 révélation invisible, 0 débordement, **0 défaut
de contraste**, 0 erreur console.

## Passe accessibilité et visibilité (2026-08-26)

Demandée en clôture. Mesurée sur les **31 pages** (les 30 du plan du site, plus `404.html`), à
1440 et 390 px. **Résultat : aucun défaut réel, sur aucun des deux volets.** Les deux sondes sont
figées dans `tools/audit-a11y.py` et `tools/audit-visibilite.py` : elles ont trouvé de vrais
défauts aujourd'hui et seront rejouées.

### Accessibilité, douze contrôles

Un seul `h1` et aucun saut de niveau sur les 31 pages ; `alt` présent sur toutes les images ; un
nom accessible sur tous les champs, liens et boutons ; **aucune référence ARIA orpheline**
(`aria-labelledby`, `aria-controls`, `aria-describedby`, `for`) ; aucun `aria-hidden` sur un
élément focalisable ; tout `role="list"` a ses `listitem` ; un `main`, un `banner`, un
`contentinfo` par page ; `lang` et `<title>` partout ; aucun tableau sans `th` ni `scope`.

**WCAG 2.5.8 est CALCULÉ, plus invoqué.** Les cibles sous 24 px existent (liens de navigation à
18 px de haut, liens d'outils à 15 px, cases à cocher à 20 px), et la norme les admet par
l'exception d'espacement : un cercle de 24 px de diamètre centré sur la boîte ne doit intersecter
ni une autre cible ni le cercle d'une autre cible sous-dimensionnée. La sonde le calcule
maintenant, sur 8 pages × 2 largeurs : **0 échec**. Marges relevées : 38 à 67 px dans la barre de
navigation, 8 à 28 px pour les cases à cocher. Le seul dépassement (guide LuxTrust à 390 px, deux
liens voisins à −12 px) est un **lien en pleine phrase**, cas que la norme exempte explicitement.

**Deux vérifications qui ne se voient pas dans une sonde de DOM :**

- **le menu mobile fermé est en `display: none`** : 0 lien focalisable, `aria-expanded="false"`,
  et 4 liens focalisables une fois ouvert. Pas de piège de focus, contrairement à ce que la FAQ
  avait avant sa correction ;
- **anneau de focus de 2 à 3 px** sur les huit premiers focalisables, aucun élément sans indicateur.

### Visibilité, dix-sept contrôles

Titre présent, unique et sous 62 caractères sur les 31 pages ; description sous 158 ; `noindex`
partout (pré-lancement) ; canonical absolu et auto-référent ; **hreflang auto-référent, apparié et
avec `x-default`, en absolu** ; les dix champs Open Graph et les quatre Twitter au complet ;
**aucun titre où « Q-Bot » figure seul** (la règle de l'audit RosoAI) ; JSON-LD valide, champs
obligatoires présents par type, et **plus aucun bloc `offers`** ; plan du site sans URL morte,
avec `lastmod` et paires hreflang partout.

Décomptes cohérents : **30 URL au plan du site, 30 annoncées dans `robots.txt`, les 30 présentes
dans `llms.txt`**, et 32 fichiers portant `noindex` (les 30, plus `404.html` et `admin/`, qui
restent hors index pour toujours).

**Les 16 destinations sortantes suivies une par une : 15 en 200.** La seule exception est
`linkedin.com/in/sylvainperez/` en **999**, le code anti-robot de LinkedIn (leur page entreprise
répond 200, ce qui est typique de leur limitation). Ce n'est pas un lien mort mais une URL non
vérifiable par outillage : elle vient du client, elle reste.

### Trois faux positifs à connaître, tous câblés dans les sondes

1. **`aria-hidden` sur un élément qui porte `tabindex="-1"` est légitime** : il n'est pas
   focalisable au clavier. C'est le cas du film décoratif de l'accueil. Sans cette exemption, la
   sonde le signale sur les deux accueils ;
2. **une case à cocher de 20 px dont le LABEL fait 444 × 64 est conforme** : c'est le label qui
   est la cible. Sans exemption, six pages remontent ;
3. **`404.html` n'a ni canonical ni métadonnées sociales, et c'est correct** : une page d'erreur
   ne se canonicalise pas et ne se partage pas. Sans exemption, elle produit à elle seule 15 faux
   constats sur 15.

### Et les deux sondes sont prouvées vivantes

Une sonde qui annonce zéro ne vaut rien sans cette épreuve. Chacune a été rejouée sur un DOM
volontairement cassé : **0 constat sur la page saine, 5 et 6 sur la page cassée**, un par défaut
injecté (second `h1`, `alt` retiré, lien sans nom, `aria-labelledby` orphelin, `role="list"` vide
d'un côté ; titre à 87 caractères, description à 200, canonical retiré, `og:image:alt` retiré,
`Product` incomplet et porteur d'`offers` de l'autre).

### Le poids, et pourquoi le chiffre n'est pas comparable à celui de l'audit

Relevé ici : accueil 3 268 Ko, page 3D 2 865 Ko, médiane 485 Ko. **Ces chiffres sont bruts** :
`python3 -m http.server` ne compresse pas, alors que GitHub Pages le fait. Compressés, les
fichiers texte fondent (`style.css` 225 → 67 Ko, `main.js` 83 → 28, l'accueil 47 → 14) et ce qui
reste est binaire et peu compressible : la visionneuse 1 043 Ko, le modèle 571, le décodeur Draco
279. **Ne pas comparer une mesure faite sur le serveur de test à une mesure faite en ligne**, et
ne pas conclure à une régression de poids sur cette base. Le poids de l'accueil a été accepté par
le client le 2026-08-11.

## Les guides vivent dans le blog (2026-08-26)

**ARBITRÉ PAR LE CLIENT : pas de section `guides/` séparée, tout va dans le blog.** J'avais
proposé `guides/` avec son propre sommaire et une cinquième entrée de menu, au motif que l'index
du blog est chronologique et que ses six billets de 2023 portent une note disant que le produit a
évolué. Le client a tranché l'inverse. C'est donc `blog/` qui accueille les guides, et il n'y a
pas de nouvelle entrée de navigation à créer.

`blog/automatiser-authentification-luxtrust.html` et
`en/blog/automate-luxtrust-authentication.html` remplacent les deux fichiers de racine. Rien ne
pointait dessus de l'extérieur et le site n'est pas public, donc le déplacement ne casse aucune
adresse acquise.

**Comment un guide se distingue d'un billet daté dans l'index** : étiquette « Guide » au lieu de
« Presse » ou « Automatisation », **une date de mise à jour au lieu d'un mois de parution**, et la
carte est posée **en premier** dans la grille, avant les archives. C'est ce qui évite que le
contenu stratégique se noie dans le fond de catalogue.

### La mesure qui a servi à la décision, et qui reste utile

Une cinquième entrée de menu **passe à partir de 1024 px et casse en dessous** : à 901 px le menu
repasse sur deux lignes (relevé avec « Guides » comme avec « Ressources »). Si une entrée doit un
jour être ajoutée, il faut donc **faire basculer le menu hamburger à 1024 px** au lieu de 900. La
mesure qui compte n'est pas la largeur du menu mais les écarts logo → menu et menu → actions, et
le nombre de lignes du menu : une première sonde comparant les bords des enfants de `.nav__inner`
annonçait un recouvrement même dans l'état actuel, qui fonctionne.

### La transformation de profondeur du générateur

Les pages donneuses de l'habillage sont à la racine (FR) et dans `en/` (EN) ; le guide vit un cran
plus bas. Le générateur ne réécrit donc pas l'habillage à la main : `profondeur_plus_un()` préfixe
`../` à tout chemin RELATIF des attributs `href` et `src`, ce qui marche uniformément
(`x.html` → `../x.html`, `../assets/` → `../../assets/`). Les adresses absolues, les ancres,
`mailto:` et `tel:` sont laissées, et le JSON-LD n'est pas touché puisque seuls ces deux attributs
le sont.

**LE GARDE-FOU EST CE QUI REND CETTE MÉCANIQUE SÛRE**, et il a servi deux fois du premier coup :
chaque chemin relatif produit doit désigner un fichier qui existe. Il a attrapé le lien du pied de
page réinjecté APRÈS la transformation (il ne portait donc pas son `../`), et il doit tourner
**quand les deux pages existent**, puisqu'elles se désignent l'une l'autre par le sélecteur de
langue : un contrôle page par page échoue sur la première. Relevé : 19 et 21 chemins relatifs,
tous valides.

### Contrôles

83 pages balayées, **0 lien interne cassé**. Le fil d'Ariane passe désormais par le blog
(`Accueil › Blog › Guide LuxTrust`). Les deux audits d'aujourd'hui repassent à **0 constat** sur
les 31 pages, à 1440 comme à 390 px. 24 vues des pages touchées (index de blog, guides, fiches
techniques) sans anomalie. Et le texte du bloc retiré ne subsiste **nulle part**, ni dans les
pages, ni dans `llms.txt`.

## Les huit guides du blog, et les vignettes carrées (2026-08-26)

### Les vignettes de l'index de blog

Signalé « surabusé » : les images des cartes faisaient **436 px de haut à 1440**, en portrait, et
deux voisines n'avaient pas la même hauteur (436 et 459). La cause est un
`style="width:100%;height:100%;object-fit:cover"` **en ligne** dans le balisage, donc hors
d'atteinte de la feuille de style, et dont le `height:100%` ne résolvait rien dans une carte en
colonne flex : la hauteur retombait sur le rapport de chaque fichier.

Le style sort du balisage, une vraie règle `.blog-card > img` le remplace avec
`aspect-ratio: 1 / 1`. Toutes les vignettes sont carrées et de hauteur identique, et la carte
raccourcit de **19 % à toutes les largeurs** (436 → 354 à 1440, 321 → 261 à 900, 418 → 340 à 390).
Aucun agrandissement nulle part (1,01 au pire à densité 2).

**LA VEDETTE N'EST PAS CONCERNÉE**, sur décision du client : « sauf pour la première qui est plus
grande que les autres, celle-ci peut rester tel quel ». `.blog__featured-img` garde ses 702 × 395.

### Les sept guides restants sont écrits, dans le blog

Le plan de contenu de l'audit RosoAI est complet : **huit guides, deux langues, seize pages**,
générés par `tools/gen-guides.py` (qui remplace `gen-guide-luxtrust.py`).

| Guide | Priorité | Ce qu'il fait |
|---|---|---|
| Automatiser la 2FA dans vos tests | P1 | **la page pilier**, le moyeu du maillage |
| Tester une authentification LuxTrust | P1 | la niche vérifiée vide |
| Faut-il désactiver la 2FA en test ? | P1 | la question tapée avant de connaître le produit |
| Automatiser la 2FA sans clé secrète | P2 | le coeur technique du différenciateur |
| Quel outil pour tester sur appareil réel | P2 | nuage contre réseau, et six questions à poser |
| Sécurité, conformité et données de test | P2 | répond à l'équipe sécurité, pas au testeur |
| Campagnes de nuit bloquées au login | P3 | le symptôme tel qu'il est ressenti |
| Combien coûte l'étape manuelle ? | P3 | le calcul, en heures, jamais en euros |

**LE MAILLAGE EST LA MOITIÉ DU TRAVAIL**, et c'est ce qui les fait exister : la page pilier pointe
vers les sept autres, chacune lui renvoie et renvoie à une ou deux voisines, les quatre pages
produit pointent vers le pilier et vers le guide LuxTrust. Huit guides isolés ne pèsent rien.

**74 capsules, toutes dans la fourchette 40-60 mots.** Quatorze étaient sous 40 au premier jet,
presque toutes anglaises : c'est attendu, l'anglais fait 10 à 15 % de moins que le français, et
c'est une raison de MESURER plutôt que de traduire. Elles ont été allongées avec de l'information,
pas du remplissage.

**Trois règles tenues, vérifiées sur le texte RENDU** et non par un grep : aucun cadratin, aucun
emoji, et **aucun tarif** sur les 24 pages du blog. Le guide sur le coût rend un résultat en
heures et en journées, jamais en euros, et le dit explicitement : convertir demanderait un taux
horaire que nous n'avons pas et que nous n'inventons pas.

**Le comparatif est le guide à surveiller.** Sa règle d'écriture est inscrite dans le générateur :
on nomme des FAMILLES d'outils et des différences d'architecture vérifiables, jamais une limite
prêtée à un fournisseur nommé sans pouvoir la prouver. Sa valeur pour le lecteur est la liste des
six questions à poser, y compris à nous, et notre réponse à la dernière y est écrite : Android
uniquement, pas d'iOS.

### Ce que la génération a appris

- **`tools/gen-index-guides.py` réécrit les cartes des deux index depuis les pages elles-mêmes** :
  titre, accroche et temps de lecture sont RELEVÉS dans la page cible, donc une carte ne peut pas
  mentir sur ce qu'elle ouvre. Onze cartes écrites à la main dans deux langues divergent dès la
  première correction de titre ;
- **`relève()` doit tolérer DEUX structures** : un guide porte `<h1 id="page-title">` et
  `<main id="main">`, un billet daté porte un h1 nu et `<main class="article-body">`. Supposer la
  première casse net sur les billets ;
- **le garde-fou des chemins relatifs doit tourner quand TOUTES les pages existent.** Les guides se
  pointent mutuellement : un contrôle page par page échoue sur la première écrite. Il tourne donc
  en fin de script, sur les seize fichiers, et il a validé 20 à 28 chemins par page ;
- **l'assertion de longueur de description a mordu quatre fois** (159, 163, 161, 163 caractères).
  C'est exactement son rôle : ces quatre descriptions auraient été tronquées en résultat de
  recherche sans que rien ne le signale.

Décomptes finaux : **44 URL au plan du site** (30 + 14), 44 annoncées dans `robots.txt`, 46
fichiers portant `noindex` (les 44, plus `404.html` et `admin/`), 10 cartes par index de blog, et
les huit guides listés dans `llms.txt` avec, pour chacun, ce qu'il ne faut pas en inférer.

Contrôles : **97 pages balayées, 0 lien interne cassé**. Les deux audits sur les **45 pages** à
1440 et 390 px : **0 constat**. 48 vues des pages neuves sans anomalie (un seul `h1`, 0 saut de
niveau, 0 révélation invisible, 0 débordement, 0 défaut de contraste, 0 erreur console).

## Les vignettes des guides : six schémas de charte, deux photos (2026-08-26)

Demande initiale : « trouve des images libres de droit via Google Image ». **Refusé, et la raison
vaut d'être gardée : Google Images est un index, pas une banque d'images libres.** Son filtre de
droits d'usage remonte des métadonnées déclarées par les sites, et Google renvoie lui-même vers la
source pour vérifier la licence. Publier ça sur le site commercial d'une société nommée exposerait
Q-Leap à une réclamation pour une image dont la licence n'a pas été lue. Trois options ont été
proposées à la place ; le client a répondu « tant que c'est cohérent peu m'importe ».

**Retenu : six schémas et deux photos, et le partage n'est pas arbitraire.** Un schéma là où le
sujet est conceptuel, une photo là où le sujet est l'objet :

| Guide | Vignette |
|---|---|
| page pilier | schéma des quatre familles de second facteur |
| LuxTrust | **photo** du téléphone docké affichant une validation LuxTrust |
| désactiver la 2FA en test | schéma des trois voies, avec la troisième marquée |
| sans clé secrète | schéma des deux chemins, avec clé et sans |
| appareil réel | **photo** du boîtier sur un poste de travail |
| sécurité et données | schéma de la frontière du réseau, rien ne sort |
| campagnes de nuit | frise d'exécution qui bute sur la 2FA |
| coût de l'étape manuelle | la formule posée, « jamais des euros » |

Les schémas sont construits par `tools/render/guide-thumbs.html` et capturés par
`tools/render/shoot-guide-thumbs.py`, exactement comme la maquette d'interface : teal et noir de
charte, Roboto servie depuis le dépôt, pictogrammes en SVG au trait, aucun emoji, aucun cadratin.
**Douze fichiers, deux langues**, 15 à 24 Ko chacun.

Deux points de méthode :

- **les libellés sont courts à dessein.** La vignette s'affiche à 354 px : un texte de 40 px dans
  la source y tombe à 18 px. Au-delà de trois mots, plus rien n'est lisible, et cette contrainte
  force la clarté du schéma ;
- **densité 2 puis réduction Lanczos**, pas une capture directe : à densité 1 les diagonales des
  pictogrammes crénellent.

**ET LA TAILLE A ÉTÉ DIMENSIONNÉE DEUX FOIS SUR UNE MAUVAISE RÉFÉRENCE.** J'ai visé 768 px puis
800 px en croyant la carte de blog large de 398 px, chiffre pris sur la carte d'ÉVOLUTION de
l'accueil et conforté par une note périmée disant le conteneur plafonné à 1180. La carte de blog
fait **441 px à 2560**, donc 882 px à densité 2 : la sortie est à **900 px**. Leçon, écrite aussi
sur la note du conteneur plus haut : **on mesure la boîte qu'on remplit, on ne déduit pas sa
largeur d'une note.**

**Les deux doublons de vignettes sont résolus au passage** : `post-2fa.webp` et
`post-tokens.webp` étaient chacune partagées entre un guide et un billet daté. Dix cartes, dix
images distinctes.

Restent trois agrandissements de 1,15 à 1,26 à 2560 en densité 2, sur `qbot-photo-dock.jpg` (699 px,
découpe de brochure) et les deux vignettes d'article (768 px) : **leurs sources ne contiennent pas
plus de pixels**, et 1,26 sur une vignette de 441 px n'a rien à voir avec le 2,03 d'un visuel de
526 px qui avait motivé la correction du 2026-08-26.

Contrôles : les six schémas nets à 1440, 1920 et 2560 px, `alt` descriptif et distinct du titre sur
chaque vignette, 0 image cassée, 0 défaut de contraste, 0 débordement, 0 erreur console sur les
deux index. Les deux audits sur les **45 pages** : 0 constat.

## Contrôle n°4 : le fil qui annonçait une autre page (2026-08-26)

`Documentations/Audit_Q-Bot_Controle4_Note_Strategique.pdf` (17 pages, 6,5 → 6,9 sur 10, et
7,8 → 8,3 sur le périmètre auditable) et `Documentations/Plan_Bascule3_Q-Bot.pdf` (11 chantiers)
remplacent les versions de la veille. Les huit guides sont mesurés et validés : 100 % des titres
de section sont des questions, **76 réponses courtes sur 76** dans la fenêtre de 40 à 60 mots,
parité de traduction de −5 % à +1 %. Sept corrections chiffrées, quatre décisions du client.

**UN POINT DE L'AUDIT DU 24/08 RESTE À ÉCARTER** : republier le tarif. Décision inverse du
client le 2026-08-24, et l'audit n°4 ne la rouvre pas.

### Chantiers 01 et 02 : les deux erreurs visibles

- **les trois articles de 2023 en français annonçaient « 5 signes de couverture insuffisante »**,
  un titre qui n'existe nulle part ailleurs dans le dépôt. Copier-coller de gabarit, en français
  uniquement (les trois pages anglaises étaient justes), **à deux endroits par page** : le fil
  déclaré et le fil affiché. Le libellé est **extrait du `<h1>` du fichier**, jamais retapé
  (règle du dépôt) ;
- **`padel_alerte.py` était servi par le site.** Script personnel, 86 lignes, aucun identifiant
  réel (adresse et mot de passe sont des gabarits), donc aucune fuite. Ce qui compte est ce
  qu'il prouve : `_config.yml` prévient en majuscules que l'exclusion est SILENCIEUSE, et
  personne n'avait passé la commande de contrôle depuis l'arrivée de ce fichier. Il est
  **sorti du suivi git** (`git rm --cached` + `.gitignore`, le fichier reste sur le disque) ET
  inscrit dans `exclude` comme filet. La commande de contrôle de `_config.yml` devient une
  boucle sur les cinq chemins, avec la date à laquelle elle a manqué.

### Le fil d'Ariane : trois défauts, et seul le premier était dans l'audit

1. **les 16 guides ne déclaraient que deux niveaux** (Accueil › Guide) là où le fil affiché en
   montre trois (Accueil › Blog › Guide). Corrigé dans `tools/gen-guides.py`, puis régénéré ;
2. **DÉFAUT NON REPÉRÉ PAR L'AUDIT, TROUVÉ EN MESURANT LES CIBLES** : sur les 8 guides anglais
   et les 2 pages légales anglaises, « Home » et « Blog » du fil AFFICHÉ menaient à l'accueil et
   au blog **français**. `prof` vaut `../../` en anglais, ce qui est la bonne profondeur pour
   les ASSETS et la mauvaise pour ces deux liens : un guide FR vit dans `blog/` et un guide EN
   dans `en/blog/`, donc **`../` est l'accueil de la langue dans les deux cas**. Même erreur
   dans `tools/gen-legal.py` (`fil_url = f'{p}index.html'`). **Le contrôle qui l'attrape n'est
   pas un comptage de niveaux mais la RÉSOLUTION de chaque cible** (`urljoin`) comparée à
   l'`item` du fil déclaré ;
3. **les pages Démo déclaraient encore « Commander » / « Order »** dans leur fil structuré,
   reste du renommage du 2026-08-24, alors que le fil affiché dit « Démo » / « Demo ».

Relevé après : **42 fils comparés, 0 divergence de libellé, 0 divergence de cible**, et la
navigation réelle vérifiée au clic (accueil, blog et logo, depuis un guide FR, un guide EN, les
quatre pages légales).

### Chantier 04 : l'accueil n'a plus qu'une adresse

**140 liens** des 45 pages visaient `index.html` alors que la balise d'adresse officielle
déclare la racine. Aucune perte de classement (la balise fait son travail), mais c'était le seul
endroit du site à ne pas suivre son propre adressage. Remplacés par la forme répertoire
(`./`, `../`, `../../`, `en/`), plus le gabarit d'article de `admin/index.html` (5 liens) et les
cibles relatives des 52 relais.

Trois choses à connaître :

- **le mode `file://` se dégrade, et c'est assumé.** Un `href="./"` ouvert par double-clic donne
  la liste du répertoire, pas la page. Le site le faisait déjà pour ses quatre pages légales
  (`conditions-vente/`), donc le précédent existe ; et le repli `file://` sert le visionneur 3D,
  pas la navigation ;
- **le module 2 de `main.js` n'a rien demandé** : `href.split('/').pop() || 'index.html'` traite
  déjà la forme répertoire, et aucun `.nav__link` ne visait l'accueil ;
- **`profondeur_plus_un()` de `gen-guides.py` a dû être normalisé** : `'../' + './'` donne
  `.././`. Le chemin passe par `posixpath.normpath`, avec réintroduction de la barre finale, qui
  distingue un répertoire d'un fichier et que `normpath` mange.

### Chantier 06 : `lastmod` est dérivé, plus écrit

Six pages modifiées portaient encore la date de la veille. La vraie correction est en amont, et
c'est celle qui a déjà réglé les compteurs « 34 redirections » : **`tools/maj-sitemap.py` dérive
la date de chaque URL du dernier commit qui a touché son fichier**, et prend la date du jour si
le fichier est modifié mais pas encore commité — sans quoi il porterait la date de sa version
précédente, c'est-à-dire exactement le défaut qu'on corrige.

    python3 tools/maj-sitemap.py            # simulation
    python3 tools/maj-sitemap.py --ecrire   # avant de commiter

### Les autres chantiers chiffrés

- **05** : le guide « tester sur appareil réel » ne renvoyait pas à la page centrale, dans
  aucune des deux langues, alors que `llms.txt` affirmait que chacun renvoie en retour. Corrigé
  dans le générateur, donc dans les deux langues d'un coup. Maillage relevé après :
  **page centrale → 7 guides et 7 guides → page centrale, dans les deux langues** ;
- **07** : `llms.txt` annonçait encore 28 pages (deux fois) et la date de la veille. **Ne pas
  toucher** à « All six articles were first published on 2023-03-02 » : elle parle des six
  articles d'archive, pas des guides, et elle est juste.

### Contrôles

`tools/audit-a11y.py` et `tools/audit-visibilite.py` sur les 45 pages : **0 constat**, à 1440
comme à 390 px. 96 pages balayées, **1 597 liens relatifs, 0 cassé**. 52 relais, 0 défaut.
17 pages menées au navigateur en normal et en mouvement réduit : un seul `h1`, 0 révélation
invisible, 0 débordement, 0 erreur console, 0 cadratin, 0 emoji.

### Les quatre décisions du client, non tranchées ici

1. **la newsletter** : Brevo refuse faute de jeton anti-robot, donc les quatre bandes retombent
   sur le courrier. Trois issues (désactiver le captcha chez Brevo, vider `data-endpoint` et
   assumer le courrier en changeant le libellé du bouton, changer de service) — et **une
   question d'abord** : cette liste est-elle encore relevée ? La section newsletter du live est
   désactivée ;
2. **poser les six schémas dans le corps des guides**, pas seulement en vignette d'index ;
3. **signer les guides d'un `Person`** (Sylvain Perez) plutôt que de l'`Organization` ;
4. **le « Depuis 10 ans » de `q-leap.eu`** : cinquième relevé, hors de ce dépôt.

## Les schémas entrent dans les guides, et les guides sont signés (2026-08-27)

Décisions 9 et 10 du plan de bascule 3, tranchées par le client. Les deux se font dans
`tools/gen-guides.py`, donc une fois pour les seize pages.

### La table des vignettes devient une source unique

`tools/vignettes_guides.py` porte, par vignette, son fichier et sa **description d'image**
dans les deux langues. `gen-index-guides.py` et `gen-guides.py` la lisent tous les deux.
Même raison que `redirections_map.py` : la même image apparaît maintenant DEUX fois (la carte
de l'index et la figure du corps), et deux textes alternatifs pour une image divergent à la
première correction, en silence. Preuve que le branchement est fidèle : la régénération des
deux index de blog rend un fichier **identique à l'octet**.

Ce que cette table ne contient pas, à dessein : la **légende**. Une légende n'est pas une
description d'image — elle s'adresse à qui VOIT le schéma, dit ce qu'il faut en retenir, et
un assistant la lit comme du texte. Elle vit donc avec la section qu'elle illustre.

### Six schémas, cinq guides, et la place de chacun

| Schéma | Guide | Section |
|---|---|---|
| `familles-2fa` | page centrale | « Quelles sont les quatre familles de second facteur ? » |
| `trois-voies` | page centrale | « Quelles sont les trois approches possibles ? » |
| `avec-sans-cle` | sans clé secrète | « Que suppose exactement la norme TOTP ? » |
| `rien-ne-sort` | sécurité et données | « Où vont ces données ? » |
| `campagne-bute` | campagnes de nuit | « À quoi ressemble le symptôme dans un rapport ? » |
| `le-calcul` | coût de l'étape manuelle | « Comment se calcule le coût, en heures ? » |

La figure se pose **après la réponse courte**, avant le corps : c'est la réponse qui doit
rester collée à sa question, la figure l'illustre ensuite. Deux guides n'en ont pas (LuxTrust
et appareil réel) : leur vignette d'index est une photo, pas un schéma.

**LA LARGEUR EST CALCULÉE, PAS CHOISIE.** Les schémas sortent en 900 px de
`shoot-guide-thumbs.py` ; à **450 px d'affichage** ils tombent à un agrandissement de **1,00
sur un écran de densité 2**. Mesuré à 390 / 768 / 1440 / 2560 px : 450 px partout sauf sur
téléphone où la colonne fait 342 (1,14 à densité 3, la source n'a pas plus de pixels). Les
afficher plus large ne montrerait que du détail qui n'existe pas dans le fichier — c'est le
défaut corrigé sur la photo LuxTrust la veille. La figure est **alignée à gauche**, jamais
centrée : relevé écart 0 px avec le logo et avec le titre de section, de 1024 à 2560 px.

`prof` et non `../` en dur pour le chemin de l'image : un guide FR vit dans `blog/` et un
guide EN dans `en/blog/`, donc les assets sont à `../` d'un côté et `../../` de l'autre.
**C'est l'inverse du fil d'Ariane**, qui vise l'accueil de la LANGUE et prend `../` partout.
Les deux règles cohabitent dans le même fichier, chacune commentée sur place.

### Les seize guides sont signés, à l'écran comme dans le balisage

`author` passe d'`Organization` à `Person` (Sylvain Perez, son `jobTitle`, son profil), et
**la ligne visible suit** : « Par Sylvain Perez, créateur de Q-Bot. Mis à jour le… » dans le
`.guide-date`, avec la formulation exacte déjà employée sur les quatre articles signés. Un
auteur déclaré qu'on ne lit pas sur la page, c'est le défaut qui a déjà coûté des corrections
sur les FAQ. Relevé : **16 sur 16 alignés**.

**Les deux articles « Merkur » gardent `Organization`, ne pas les « compléter »** : ce sont la
reprise d'un article de presse, les signer nominativement dirait quelque chose de faux sur lui
ET sur le magazine. Vérifié après coup qu'ils sont intacts.

### Un défaut trouvé en mesurant la signature

**Le lien vers le profil de l'auteur n'avait aucune affordance**, ni dans le nouveau
`.guide-date` ni dans le `.article-meta` des quatre articles signés (défaut préexistant) :
couleur identique à celle du paragraphe, aucun soulignement — donc rien, pas même la couleur,
ne disait qu'il y avait un lien. Réglé par le motif déjà retenu pour les libellés de fiche
technique : la couleur du texte reste (c'est elle qui porte le contraste), et un
**soulignement pointillé teal** fait l'affordance. Une seule règle couvre les vingt pages.

### Publication et modification sont deux dates

Retoucher les guides a fait apparaître un défaut de conception : `MAJ_ISO` servait à la fois de
`datePublished` et de `dateModified`, donc toute retouche aurait annoncé un contenu tout neuf.
C'est exactement le signal trompeur contre lequel l'audit RosoAI met en garde. `PUB_ISO` reste
au **2026-08-26**, la date de modification passe au **2026-08-27**.

Et **la carte de l'index LIT désormais cette date dans la page** au lieu de la porter en dur :
elle annonçait le 26 quand la page disait le 27. Même principe que le titre et l'accroche, déjà
relevés dans la page cible, et que le `lastmod` du plan de site. Une assertion échoue si une
page ne porte pas de date lisible.

Deux surcharges MORTES retirées au passage : le guide LuxTrust déclarait son propre `datel`,
écrasé par `dict(LUX_FR, **DATE_FR)`. Sans effet, mais elles laissaient croire que ce guide se
datait à part.

### Contrôles

Les deux audits sur les 45 pages, à 1440 et 390 px : **0 constat**. 72 pages, 1 585 liens
relatifs, **0 cassé**. 121 blocs JSON-LD, **0 invalide**. 25 pages de blog balayées
au navigateur en normal et en mouvement réduit : un seul `h1`, 0 saut de niveau, 0 révélation
invisible, 0 débordement, 0 image cassée, 0 erreur console, 0 cadratin, 0 emoji. Contraste sur
le pire fond composité : ligne d'auteur 13,7:1, légende 8,5:1.

## La date de fondation devient une vraie date (2026-08-27)

Donnée par le client : **Q-Leap a été créée le 5 avril 2012**. Le `foundingDate` de
l'`Organization` des **45 pages** passe de `"2012"` à `"2012-04-05"`, et `llms.txt` suit.
`foundingDate` accepte une Date complète en schema.org, et une date précise est plus
vérifiable qu'une année : c'est l'axe même que l'audit mesure quand il parle d'ancrer
l'entité.

**Le texte VISIBLE ne bouge pas.** Les neuf « depuis 2012 » de la prose et des métadonnées
restent : le jour n'apporte rien à une phrase de présentation, et c'est du texte du live.
La précision sert la machine, pas le lecteur.

Aucun générateur ne porte cette valeur : les guides et les pages légales recopient l'en-tête
de leur page donneuse, donc une régénération reprend la nouvelle date sans rien à changer.

Ce que cela confirme, et qui reste **hors de ce dépôt** : le « Depuis 10 ans » de `q-leap.eu`
situerait la fondation en 2016, à quatre ans de sa propre date. C'est le chantier 11 du plan
de bascule, et il vit dans le WordPress de q-leap.eu.

## Deux points fermés par le client (2026-08-27)

- **La séquence du jour J ne se prépare plus, elle s'exécutera le jour venu.** « On en parlera
  le jour J. » Tout est outillé et vérifié (`tools/go-live.py`, les 52 relais,
  `tools/verif-redirections.py`, la commande de contrôle de `_config.yml`) ; il ne reste qu'à
  la dérouler dans l'ordre, qui est la seule contrainte dure. **Ne plus la remonter comme un
  point ouvert à la fin des échanges** : elle n'attend pas une décision, elle attend une date.
  Le seul point de non-retour reste l'étape 6, supprimer le WordPress avant d'avoir vu les
  52 relais répondre sur le vrai domaine.
- **La maquette « Interface & API » reste** : l'interface réelle est en préproduction et n'est
  pas présentable. Les deux notes qui la donnaient « à remplacer dès qu'une vraie capture
  existe » sont annotées sur place. Le visiteur n'est pas trompé, l'`alt` annonce un schéma.

Reste donc ouvert, et rien d'autre : **Brevo** (chez les managers du client, aucune réponse au
2026-08-27) et le **« Depuis 10 ans » de `q-leap.eu`**, qui vit hors de ce dépôt et contredit
désormais de quatre ans le `foundingDate` du 5 avril 2012.

## Les FAQ se laissent citer, et les articles de 2023 disent leur époque (2026-08-27)

Deux chantiers de rédaction confiés par le client, avec une consigne explicite&nbsp;: « fais en
sorte que ça reste cohérent et pas d'invention de ta part ». **Aucune phrase ajoutée n'est
inventée** : chacune reprend un fait déjà publié ailleurs sur le site, et la source est notée en
regard dans la table d'édition.

### Les 21 ouvertures de FAQ trop courtes

L'audit RosoAI mesure la fenêtre de 40 à 60 mots comme celle où un assistant recopie un
paragraphe au lieu de le résumer. Relevé avant : **11 réponses françaises et 10 anglaises sur 17
ouvraient sous 35 mots**, dont trois qui faisaient moins de 25 mots en tout.

Trois sources d'expansion, dans cet ordre de préférence :

1. **le corps de la réponse elle-même**, dont un paragraphe est absorbé dans l'ouverture puis
   supprimé (Q4, Q6, Q15, Q16). Zéro invention par construction ;
2. **une autre réponse de la même FAQ** (Q7 reprend de Q9 que le tarif est donné en démo ; Q11 et
   Q15 reprennent de Q9 que l'assistance et le remplacement sont inclus) ;
3. **une page du site** (la page démo pour « 48 à 72 heures » et « sous 24h ouvrées », la fiche
   technique pour le stockage local, le guide sécurité pour « tout reste dans le boîtier »).

Après : **16 sur 17 dans la fenêtre, dans les deux langues.** La seule hors fenêtre est la Q3
(66 et 70 mots), et elle est laissée : elle est trop LONGUE, pas trop courte, et c'est du texte
d'origine qu'on ne découpe pas pour atteindre un chiffre.

### Le JSON-LD de la FAQ se dérive du texte rendu, il ne se maintient plus à la main

**Le piège documenté depuis le 2026-08-24 avait encore frappé, et un contrôle l'avait manqué.**
Chaque réponse vit en double, texte visible et `acceptedAnswer.text`. Le contrôle d'alors
comparait les **60 premiers caractères** : la réponse anglaise « What is Q-Bot? » divergeait à
partir du MILIEU de la phrase (« and allow for increased security » côté JSON, « and it increases
the security » côté page) et avait survécu à trois passes.

`tools/sync-faq-jsonld.py` recale les 34 entrées sur le texte réellement rendu. Deux points de
méthode qui font tout :

- **la référence est `innerText`, pas le HTML aplati.** Aplatir le HTML insère une espace à chaque
  balise fermante et produit « +352 20 21 17 . » : c'est exactement l'artefact qu'on retrouvait
  dans **17 entrées** du JSON. Reproduire l'artefact aurait été le figer ;
- **il faut OUVRIR les accordéons avant de lire.** Une réponse repliée est en `max-height: 0` et
  son texte rendu serait vide.

Relevé : 26 entrées recalées sur 34, puis **0 au second passage** (le script est idempotent, ce qui
est le vrai contrôle). Il recale aussi le libellé de la question, qui vit en double lui aussi.

### Les quatre articles « token » : le récit reste, l'époque est nommée

**Le vocabulaire de 2023 n'est PAS réécrit, et c'est délibéré.** Ces articles racontent le
lancement de la première version, celle conçue pour les tokens LuxTrust ; la réécrire ferait dire
à une publication datée autre chose que ce qu'elle a dit. Ce qui manquait, c'est que le lecteur
sache lequel des deux produits il lit.

La note de transparence le dit désormais : « Le vocabulaire de l'époque parle de token et de
récupération de la valeur d'un OTP : c'est la première version de Q-Bot, celle de 2022, conçue
pour les tokens LuxTrust. Le produit a changé depuis (…) il n'y a plus aucune valeur à reconnaître
ni à récupérer. » `llms.txt` porte la même mise en garde, plus une seconde : **le « 100 % des
tests de fonctionnalités » de ces articles est une CITATION du fondateur en 2023**, pas une
revendication d'aujourd'hui, et le périmètre actuel est énoncé comme une limite.

Les deux articles sur la 2FA ne sont pas concernés : leur unique mention d'un OTP est une
définition générale, qui reste juste.

### Trois défauts objectifs trouvés en les relisant

- **le chapeau était DUPLIQUÉ** sur les deux articles « tokens » : le premier paragraphe est la
  première phrase du second, mot pour mot ;
- **deux mots collés** dans les deux articles français : « les systèmes ouapplications » et « du
  réseau de l'entreprise estdemandée » ;
- **et voici pourquoi le doublon avait survécu à toutes les passes : LES DEUX CHAPEAUX NE SONT PAS
  NORMALISÉS PAREIL, DANS LE MÊME FICHIER.** « marché » y est écrit en NFD dans l'un et en NFC dans
  l'autre. Deux chaînes visuellement identiques, différentes à l'octet : `t2.startswith(t1)` répond
  faux, et toute recherche de doublon passe à côté. C'est le même piège que `Screen modèle 3D` dans
  `_config.yml`, mais à l'intérieur d'un fichier de contenu.

  **Règle qui en découle** : sur ce dépôt, toute comparaison de texte se fait après
  `unicodedata.normalize('NFC', …)`, et **on n'écrit jamais une chaîne accentuée à la main dans un
  motif de remplacement** : on l'extrait du fichier, ou on ancre sur de l'ASCII. Trois de mes
  motifs ont échoué en silence avant que je m'en aperçoive.

Les quatre articles retouchés passent leur `dateModified` au 2026-08-27, visible et structuré ;
les deux autres restent au 25, n'ayant pas changé.

### Contrôles

Les deux audits sur les 45 pages, à 1440 et 390 px : **0 constat**. 121 blocs JSON-LD valides.
`sync-faq-jsonld.py` idempotent. 14 pages menées au navigateur, accordéons ouverts, en normal et
en mouvement réduit : un seul `h1`, 0 saut de niveau, 0 révélation invisible, 0 débordement,
0 erreur console, 0 cadratin, 0 emoji, 0 coquille. Vérifié aussi que les aperçus de FAQ des deux
accueils restent cohérents : ce sont des résumés délibérés, pas des copies des réponses.


## Le lot de retours du 2026-08-28, et où il s'arrête

Une liste de quarante-sept retours du client et de son directeur, traitée à sa demande
**un retour = un commit = un push sur `main`**, pour qu'on puisse revenir sur n'importe
lequel sans défaire les autres. Vingt-deux commits, de `e54f4da` à la présente note. La
session s'est arrêtée en cours de route : ce qui suit dit où, et avec quoi reprendre.

### LA MACHINE N'A PAS DE PYTHON, ET C'EST LE PREMIER PIÈGE DE LA REPRISE

Le poste Windows du 2026-08-28 n'a que les alias Microsoft Store : `python3` et `python`
répondent, mais ne lancent rien. **Aucun `tools/*.py` de ce dépôt n'y est exécutable**, ce
qui vise en particulier `bump-assets.py`, `maj-sitemap.py`, `gen-*.py`, `go-live.py` et les
deux audits.

Le plus urgent des cinq a donc un jumeau Node, `tools/bump-assets.mjs`, au comportement
identique. **Les deux fichiers doivent rester d'accord** ; si l'un change, changer l'autre.

    node tools/bump-assets.mjs      # après TOUTE modification d'un CSS ou d'un JS

Ne pas sauter cette commande : c'est exactement le défaut du 2026-08-25, où le client
servait l'ancien script depuis son cache et où rien du travail de la journée n'arrivait
chez lui.

Sur un poste qui a Python, les scripts d'origine redeviennent utilisables et restent la
référence pour tout le reste (plan du site, audits, générateurs).

### LE PIÈGE CRLF, RENCONTRÉ DEUX FOIS DANS LA MÊME JOURNÉE

L'arbre de travail est en **CRLF** (`core.autocrlf`). Pour une expression régulière
JavaScript, **le retour chariot est un terminateur de ligne** : l'ancre de début de ligne en
mode multiligne matche donc AUSSI entre le retour chariot et le saut de ligne. Conséquences
observées, toutes deux invisibles à la relecture :

1. une réindentation `replace(/^[ \t]*/gm, …)` a inséré son indentation en **fin** de ligne,
   laissant des espaces traînants sur chaque ligne réécrite ;
2. une suppression de ligne `replace(/^\s*- admin\/.*\r?\n/m, '')` dans `_config.yml` a mangé
   le saut de ligne de la ligne PRÉCÉDENTE : `- tools/` s'est retrouvé aspiré dans le
   commentaire de `- Documentations/`, **et le dossier `tools/` a cessé d'être exclu de la
   publication** pendant quelques commits. Réparé le jour même.

Règle : on découpe explicitement sur `/\r?\n/`, on ne s'ancre pas en début de ligne pour
supprimer ou réindenter. Et la commande de contrôle de `_config.yml` doit être passée après
toute modification de ce fichier, parce que l'exclusion est silencieuse par construction.

Au passage, quatrième et cinquième variantes du piège « on n'retape pas une chaîne, on
l'extrait » : l'**espace insécable écrite en entité** `&nbsp;` là où l'on tapait U+00A0, et
l'**apostrophe droite** là où l'on tapait la typographique. Après le cadratin en `&mdash;`,
l'emoji en `&#128272;` et le NFD de « marché », cela fait cinq.

### Ce qui est fait, et qu'il ne faut pas défaire

Chaque point ci-dessous est un arbitrage du client, pas un choix technique :

- **le blog est supprimé en entier**, index, six articles de 2023 et huit guides, soit
  vingt-quatre pages. Les onze relais d'anciennes adresses WordPress ne sont PAS supprimés :
  ils renvoient à l'accueil de leur langue, suivant la règle « plus aucune 404 » du
  2026-08-25. Le levier de visibilité IA que portaient les guides disparaît avec eux, le
  client en a été informé avant d'exécuter ;
- **la page Modèle 3D est supprimée**, mais **la séquence 3D épinglée de l'accueil reste** :
  c'est un autre objet, elle vit dans `index.html` et `assets/js/scrolly.js` ;
- **le back-office `admin/` est supprimé** : c'était un éditeur d'articles de blog ;
- **la navigation** : Accueil, Caractéristiques, Cas d'usage, FAQ. « À propos » et
  « Contact » sortent du menu et restent dans le pied de page. La barre ne se masque plus au
  défilement ;
- **le logo est le mot-symbole seul**, sans « powered by Q-Leap », et le produit s'appelle
  « Q-Bot » partout, y compris dans les métadonnées. Le nom long survit comme
  `alternateName` du `Product` ;
- **les cotes sont 20 × 11 × 15 cm** et **la feuille A3 a disparu du site**. La feuille au
  sol de la séquence 3D est passée en A4 à l'échelle réelle ;
- **la fiche technique tient en huit lignes**, sous le titre du nano ordinateur, sur deux
  colonnes. La section « Spécifications techniques » n'existe plus ;
- **les cinq cas d'usage ne sont plus épinglés**, ils se lisent les uns sous les autres ;
- **le fil d'Ariane visible est retiré** des seize pages qui le portaient. Le
  `BreadcrumbList` des données structurées reste, il n'était pas affiché, il est lu ;
- **l'aperçu FAQ quitte l'accueil** ;
- **les images ne s'agrandissent plus au survol** ;
- **le rail de progression de la section évolution est retiré**, et sa troisième carte porte
  un vrai visuel NFC au lieu d'un cadre en pointillés ;
- **tous les boutons de démonstration disent « Réserver une démo »** / « Book a demo » ;
- **l'encre des boutons teal est `#231F20`** et non du noir pur. Mesuré : 8,0:1 sur le teal,
  5,4:1 sur le teal foncé. **Ne pas l'éclaircir davantage sans mesurer** : le teal de charte
  est une couleur claire, le blanc y plafonne à 2,04:1 ;
- **« Q-Bot » est marqué insécable** dans le texte rendu, par une classe `.nb`. Le trait
  insécable U+2011 a été écarté à dessein : il ferait de « Q-Bot » deux chaînes différentes
  pour un moteur de recherche.

### Ce qui reste à faire

**ANNOTÉ LE 2026-08-31 : trois des quatre points ci-dessous sont refermés.** Voir la
section « La reprise du 2026-08-31 » en fin de fichier pour le détail. En résumé :
le ton est fait sur les treize pages, la homepage bis est écrite, la retouche photo a
été tentée et écartée. Ne reste que la page de réservation, toujours bloquée.

**Le ton. FAIT le 2026-08-31**, sur les six pages françaises puis les sept anglaises.
Le périmètre annoncé ici, vingt-deux pages, était périmé : le blog est parti le
2026-08-28, il restait treize pages de contenu. Les quatre pages légales sont hors
périmètre, c'est du texte client repris mot pour mot. Restent volontairement en
l'état, dans les DEUX langues : « Tous types de projets IT » et « Tous types
d'applications », qui viennent mot pour mot du WordPress. Demander avant d'y toucher.

**La homepage bis. FAITE le 2026-08-31** : « accueil-bis.html » et
« en/home-bis.html », générées par « tools/gen-accueil-bis.py ». Hors plan du site,
hors robots, non liées, et inscrites dans la liste « JAMAIS » de « go-live.py » sans
quoi le jour J aurait publié un accueil en double. À soumettre au client pour qu'il
compare.

**La retouche de la photo du poste de travail. FERMÉE PAR LE CLIENT le 2026-08-31 :
« on oublie pour la photo du poste de travail ».** Ce n'est donc plus un point à
reprendre, et il ne faut ni la retenter, ni proposer une nouvelle photo ou un rendu.
Ce qui suit reste écrit pour la raison de fond, qui vaut au-delà de ce cas.

Tentée et écartée avant cette décision, la photo est intacte. Deux raisons, et la seconde est de principe. D'abord la prémisse
de cette note ne se reproduit pas : le téléphone penche en arrière dans son socle,
donc ses arêtes longues convergent en perspective (mesuré −24° à gauche, −19° à
droite) et aucune n'est comparable à la verticale de l'image, si bien que je ne
retrouve ni les 3,4° ni les 1,1° annoncés. Ensuite, et c'est la vraie objection :
UNE ROTATION 2D NE CORRIGE PAS UNE ORIENTATION 3D. Elle ne réoriente pas l'objet,
elle rompt l'accord de perspective entre le téléphone et son socle, ce qui se voit
immédiatement (dans un sens le téléphone semble basculer hors de son berceau). Les
deux sens ont été rendus à 2,5° autour du point d'assise, avec bouchage n'empruntant
que des pixels sombres du socle : le raccord est propre, et le résultat n'est pas
meilleur que l'original. Si l'assise gêne vraiment le client, la sortie est une
nouvelle photo ou un rendu depuis « assets/models/qbot.glb », pas une retouche.

**La page de réservation. FAITE le 2026-08-31**, l'URL ayant été fournie ce jour-là :
« reservation.html » et « en/booking.html », le formulaire de contact conservé sur sa
page. Voir la section « La réservation a sa page » plus bas. Le seul point encore en
attente de ce côté est le Bookings ANGLAIS, la page Microsoft ne se traduisant pas ;
le marqueur « BOOKINGS-EN-A-VENIR » de « en/booking.html » le signale, et il n'y aura
qu'une URL à remplacer.

### Ce qui est à discuter avec Marie

Le client a demandé que tout ce qui touche à Marie soit fait, et soumis à discussion avec
elle quand il la verra. Relèvent de ce lot : la reprise du ton sur l'ensemble du site, le
contenu de la page Démo à reprendre pour la homepage bis, et la mise en avant de l'équipe.

### Contrôles disponibles sans Python

Un balayage de liens internes, de longueurs de titre et de comptage de `h1` a été écrit en
Node pendant cette session et tourne en une seconde sur l'ensemble du dépôt. Dernier relevé :
**71 pages, 402 références internes, 0 cassée, aucun titre au-delà de 62 caractères, un seul
`h1` par page de contenu**. Les deux audits complets (`audit-a11y.py`, `audit-visibilite.py`)
n'ont PAS pu être rejoués sur ce poste : à repasser depuis un poste avec Python avant toute
mise en ligne.


## La reprise du 2026-08-31 : le ton, et deux défauts en ligne

Session de reprise après la série du 2026-08-28, faite depuis un autre poste. Trois des
quatre chantiers ouverts sont refermés, et deux défauts qui étaient EN LIGNE ont été
trouvés en chemin, dont un que le client subissait sans le savoir.

### Le registre professionnel, sur les treize pages

Le périmètre annoncé par la note de reprise, « vingt-deux pages », était périmé : le blog
est parti le 2026-08-28, il reste **six pages de contenu en français et sept en anglais**.
Les quatre pages légales sont hors périmètre, c'est du texte client repris mot pour mot.

**La règle, telle que l'accueil validé la définit** : pas de point d'exclamation, un titre
descriptif plutôt qu'un impératif ou une question rhétorique, un fait vérifiable plutôt
qu'une appréciation, aucun anglicisme marketing, et on nomme ce que le produit fait au lieu
d'une métaphore.

**LES TITRES EN QUESTION SONT CONSERVÉS, ET CE N'EST PAS UNE INCOHÉRENCE.** « Comment Q-Bot
automatise votre 2FA ? », « Pourquoi la location ? » et les dix-sept questions de la FAQ
portent chacune une réponse autonome de 40 à 60 mots : c'est la forme citable que l'audit
RosoAI mesure. Seule l'unique question rhétorique SANS réponse avait été reprise, sur
l'accueil. Ne pas « finir le travail » en supprimant les autres.

**« Onboarding » reste en anglais et part en français**, parce que c'est un anglicisme
inutile dans une langue et du vocabulaire natif dans l'autre. Même chose pour
« Absolutely » en tête d'une réponse de FAQ, qui reflète le « Absolument » français. Un
balayage de registre les remontera toujours : ce sont des conservations, pas des oublis.

**L'accueil anglais était resté en arrière de l'accueil français**, qui avait été validé
seul le 2026-08-28. Les deux disaient donc deux choses différentes au même endroit. Seize
reformulations pour les remettre au même niveau, dont le titre du hero : « Stop babysitting
2FA. Start shipping faster. » devient le miroir de la formule française. C'est bien ce
registre parlé que le directeur visait.

**Neuf fautes trouvées en relisant, qui ne relèvent pas du ton** : « le marché
Luxembourgeois » (un adjectif de nationalité ne prend pas la majuscule), « cliquez sur ce
lien et accéder à son agenda » (infinitif au lieu d'un impératif), « La compilation passe ou
échoue » (calque de *build*, dans un paragraphe qui parle d'une campagne ; l'anglais dit
bien « pipeline »), « plus sur l'absence d'un humain » (négation perdue, sens inversé),
« X c'est une équipe » (construction orale), et côté anglais trois calques du français dont
« The unique solution », où « unique » ne veut pas dire « seul », plus « specialized » seule
graphie américaine d'un site qui écrit « optimised », et « his live agenda » qui présumait
le genre de l'interlocuteur.

**Leçon de méthode : chaque remplacement porte une assertion.** L'utilitaire employé exige
qu'une chaîne corresponde exactement une fois et n'écrit RIEN sinon. Il a mordu du premier
coup, sur un « Plug & Play&nbsp;: » retapé là où le fichier écrit une espace ASCII. C'est la
sixième variante du piège « on n'retape pas une chaîne, on l'extrait ».

### LES EMPREINTES D'ACTIFS ÉTAIENT PÉRIMÉES, POUR LA DEUXIÈME FOIS

Treize commits du 2026-08-28 ont modifié `style.css`, `main.js` ou `scrolly.js` **sans que
le versionneur soit lancé**. Les pages publiées déclaraient `style.css?v=030c006d` quand le
fichier réel vaut `171826db`. Le navigateur d'un visiteur déjà venu servait donc l'ancienne
feuille et l'ancien script : rien de ce que cette session avait fait en CSS ou en JS ne
pouvait l'atteindre.

**Le contrôle qui l'attrape en une seconde** : relancer le versionneur et vérifier qu'il
n'annonce AUCUNE page à mettre à jour. S'il a quelque chose à écrire alors que rien n'a
changé depuis le dernier commit, c'est qu'il n'a pas été lancé au bon moment.

    node tools/bump-assets.mjs      # ou la version .py, les deux doivent rester d'accord

C'est trouvé par accident, en constatant qu'un « bump » sur un arbre revenu à sa version
commitée modifiait quand même dix-neuf pages.

### UN SPAN DANS UN CONTENEUR FLEX DEVIENT UN ÉLÉMENT FLEX

Défaut en ligne depuis `ab2d870`, et parfaitement visible : les questions de FAQ se lisaient
**« What is · · · Q-Bot · · · ? »**, étalées sur toute la largeur du bouton. Mesuré à
1440 px dans un bouton de 758 px : « What is » à x=179, « Q-Bot » à x=425, « ? » à x=661.
Vingt-six boutons, quatre pages, deux langues.

La cause est une règle de Flexbox, pas une faute de frappe : un élément placé dans un
conteneur flex est **blocifié**, donc devient un élément flex à part entière. Depuis que
« Q-Bot » est entouré d'un `<span class="nb">`, la question n'était plus un texte mais TROIS
éléments, que le `justify-content: space-between` du bouton écartait au maximum. Le span ne
demandait que `white-space: nowrap` ; c'est le conteneur qui l'a transformé.

**RÈGLE QUI EN DÉCOULE, et elle vaut pour tout ajout futur de `.nb`** : avant de poser un
span dans du texte, vérifier que son parent n'est pas `display: flex` ou `grid`. La sonde
tient en une ligne et doit être rejouée après tout ajout :

    [...document.querySelectorAll('.nb')].filter(x => /flex|grid/.test(getComputedStyle(x.parentElement).display)).length

Le correctif porte sur le CONTENEUR, jamais sur le span. `.faq-item__question` cesse d'être
un flex : bloc simple, icône positionnée en absolu, centrage vertical par `top: 50%` et
`translateY(-50%)`, et l'état ouvert devient `translateY(-50%) rotate(45deg)`, sans quoi la
rotation perdait le centrage. C'est un correctif CSS et non un emballage des vingt-six
libellés, parce qu'un futur ajout de question oublierait l'emballage et ne peut pas oublier
une règle. La liste tarifaire, elle, garde son flex (il porte le retrait d'une puce qui passe
à la ligne) et c'est son texte qui est emballé.

**Ce défaut cassait aussi un outil du dépôt.** `tools/sync-faq-jsonld.py` annonçait
vingt-cinq entrées à recaler et ses recalages étaient FAUX : il voulait écrire
`'How do I use\nQ-Bot\n?'` dans les données structurées, parce que `innerText` insère un
saut de ligne autour d'un élément de niveau bloc. **Un outil dont les corrections empirent le
fichier mesure autre chose que ce qu'on croit** : ne pas lancer `--ecrire` sur la foi du
nombre. Après correction il retombe à une divergence réelle, un « Demander une démo » resté
dans le JSON-LD alors que le bouton dit « Réserver une démo » depuis le 2026-08-28.

### La photo du poste de travail : tentée, écartée

Voir la note de reprise annotée. Le résumé qui compte : **une rotation 2D ne corrige pas une
orientation 3D**, elle rompt l'accord de perspective entre l'objet et son support. La photo
est intacte, et la sortie, si l'assise gêne vraiment, est une nouvelle photo ou un rendu
depuis `assets/models/qbot.glb`, pas une retouche.

### La homepage bis

`accueil-bis.html` et `en/home-bis.html`, générées par `tools/gen-accueil-bis.py`. Six
sections reprises de la page Démo, le hero et l'appel final venant de l'accueil. 6 268 px
contre 10 632 pour l'accueil actuel.

**Hors plan du site, hors robots, non liées**, et, ce qui n'allait pas de soi, **inscrites
dans la liste `JAMAIS` de `go-live.py`**, qui énumère par `glob` sur le disque et non depuis
le plan du site : sans cela le jour J leur aurait retiré leur `noindex` et le site se serait
retrouvé avec deux accueils indexables. Conséquence heureuse de leur absence du plan : les
deux audits énumérant leurs pages depuis `sitemap.xml`, elles en sont exclues d'office.

Deux pièges à connaître si on refait ce genre d'assemblage :

- **l'alternance des fonds ne survit pas à un réordonnancement** des sections, et deux fonds
  gris côte à côte suffisent à casser le rythme de la page. Elle est recalculée en partant de
  la fin ;
- **ne pas retirer `scrolly.css`** sous prétexte que la séquence 3D n'est pas reprise : cette
  feuille porte aussi `main .section-label` et `.visually-hidden`, et la retirer aurait changé
  l'aspect de tous les libellés de section, donc de la maquette même qu'on compare.


## La réservation : une page, une fenêtre, et un agenda Microsoft (2026-08-31)

Suite de la même journée. L'URL du Bookings a été fournie, ce qui a débloqué le
dernier chantier ouvert de la note de reprise, puis le client a fait évoluer la forme
deux fois. État final, et ce qu'il ne faut pas défaire.

### Ce qui existe

`reservation.html` et `en/booking.html`, **générées** par `tools/gen-reservation.py`
depuis l'habillage de la page contact, qui garde son formulaire. Elles sont les
SEULES pages à porter le lien Microsoft Bookings.

`tools/bookings_conf.py` est la **source unique** de l'URL et des libellés de la
fenêtre. Le bouton de la barre de navigation porte les mêmes attributs sur les
23 pages : sans source unique, un changement d'agenda en laisserait forcément une
derrière. **Pour changer d'agenda**, la marche à suivre est en tête du module :

    python3 tools/gen-reservation.py
    python3 tools/maj-nav-booking.py
    python3 tools/gen-accueil-bis.py
    node tools/bump-assets.mjs

### L'agenda s'ouvre dans une fenêtre, et pourquoi pas dans la page

Mesuré : le contenu de Bookings fait **1 523 px de haut à 1 130 px de large et
1 838 px à 342 px**. Inséré dans le flux, il imposait soit un défilement imbriqué qui
capture la molette, soit 4,7 écrans de panneau blanc sur un téléphone. Dans une
fenêtre dédiée, un défilement interne est attendu et non subi.

C'est un **`<dialog>` natif**, et c'est ce qui rend le module 20 court : piège de
focus, touche Échap, fond assombri et retour du focus sur le bouton d'origine sont
donnés par le navigateur. Deux pièges :

- **un `<dialog>` auquel on fixe des dimensions perd le centrage** : il faut lui
  redonner `inset: 0` et `margin: auto`, sinon la fenêtre se colle en haut à gauche ;
- `showModal()` n'empêche pas partout la page de défiler derrière, d'où le
  verrouillage explicite de `overflow` et sa restitution à la fermeture.

**BOOKINGS N'ACCEPTE L'ENCADREMENT QUE DEPUIS UNE PAGE HTTPS** (`frame-ancestors
https:`). Donc **cet encadrement ne se vérifie PAS sur `http://127.0.0.1` ni en
`file://`** : il faut un serveur https local avec un certificat auto-signé et
Playwright lancé avec `ignore_https_errors`. `*.pem` et `*.key` sont dans
`.gitignore` pour cette raison. Le module n'ARME donc le bouton que si la page est en
https et que `<dialog>` existe ; sinon le CSS montre le lien externe comme action
principale, et le bouton de la barre reste un simple lien vers la page de réservation.

L'iframe est **détruite à la fermeture** : dans une fenêtre fermée elle continuerait
de faire tourner les scripts de Microsoft. Rouvrir ne coûte qu'une seconde.

### Deux faux positifs qui m'ont coûté six essais

- **UN IFRAME INJECTÉ HORS DU CHAMP VISIBLE NE SE CHARGE PAS** en navigateur
  invisible. J'ai conclu tour à tour à un refus CSP, à un problème d'URL, puis à
  `main.js`, avant de constater qu'un iframe nu placé en position fixe et visible se
  chargeait parfaitement. Un contrôle d'encadrement doit garder le cadre AU CENTRE de
  la fenêtre pendant l'attente ;
- **Microsoft étrangle les essais répétés** : une même vérification a donné 195
  requêtes, puis 1, puis 157 après une pause. Un échec isolé se rejoue avant d'être
  appelé défaut.

Mesure utile au passage : l'agenda peint **0,28 s après son événement `load`**, soit
1,0 s après la navigation. Aucune attente minimale longue ne se justifie donc dans
l'indicateur de chargement ; il n'a qu'un plancher de 400 ms contre le clignotement.

### La direction artistique de la fenêtre

Toutes les valeurs sont reprises d'un élément existant : le filet
`rgba(0, 203, 190, 0.22)` et le halo `0 0 60px rgba(0, 203, 190, 0.10)` viennent du
cadre du film du hero, le filet dégradé sous le bandeau est celui de la barre de
navigation, le survol de la croix est celui des boutons primaires. La boîte est
sombre (`#101010`) pour que l'attente se lise sur une surface du site.

**Inscrire `.booking-modal__box` dans la liste générique des surfaces sombres
écraserait la bordure teal** : `[data-theme="dark"] .x` (0,2,0) passe devant la règle
de base (0,1,0). D'où une règle dédiée qui repose les DEUX propriétés. Même piège que
`.booking-box`.

**Le contenu de l'agenda vient d'une autre origine : aucune règle du site ne
l'atteint.** Son bandeau ardoise, son fond clair et le rectangle blanc derrière le
logo se règlent dans le back-office Bookings, pas ici.

### La boucle du boîtier en action

`assets/video/qbot-action.mp4`, 4,6 s en 960x540 pour 2,60 Mo, extrait du film
`QBV1.2.12.mp4` fourni le 2026-08-31. Placée dans la section « Déclenchement » des
deux fiches techniques, et dans la homepage bis à la place de la photo fixe du
téléphone docké.

**L'EXTRAIT EST 39,0 à 43,6 s PARCE QUE C'EST LE SEUL SEGMENT SANS INCRUSTATION.**
Celles du film sont en anglais, et le même fichier sert les deux langues.

**Le module 18 est généralisé** : il gérait un film, il en gère plusieurs. Ne pas en
écrire un second, le site garde un seul mécanisme avec tous ses garde-fous (fichier
demandé à l'approche de la section, pause hors champ, rien du tout en mouvement
réduit, économiseur de données ou connexion lente).

**PÉRIMÉ, VOIR LA SECTION FFMPEG CI-DESSUS.** Le film entier est dans le dépôt
depuis le 2026-08-31 (décision du client), en 1280x720 pour 4,95 Mo, et c'est ffmpeg
qui l'a encodé. Ce qui suit décrit l'état d'avant, quand `avconvert` était la seule
voie ; le raisonnement sur le poids reste juste, ses chiffres non.

**Le film ENTIER n'était pas dans le dépôt, et c'était une décision en attente du
client.** Mesuré : même trimé (10 à 46 s) et rabaissé en 640x360, il pèse 9,78 Mo,
parce qu'`avconvert` est le seul encodeur de cette machine et qu'il n'a AUCUN réglage
de débit. Le poids des pages étant un arbitrage du client depuis le 2026-08-11, dix
mégaoctets de plus ne se posent pas sans lui demander. Le master de 94,6 Mo n'est pas
archivé non plus : il vit dans `/Volumes/CCCOMA_X64F/Q-Bot/Version/`.

**La piste audio reste dans le fichier** : aucun outil ici ne peut la retirer (ni
ffmpeg, ni MP4Box, ni pyobjc). Le silence vient de `muted`, sans contrôles et avec
`pointer-events: none`, donc irréversible pour le visiteur. Dette d'environ 0,3 Mo à
solder le jour où `ffmpeg -an` sera disponible.

### FFMPEG EST DISPONIBLE, ET CELA CHANGE TOUT LE TRAVAIL VIDÉO

**`avconvert` n'est plus la seule voie, et il ne faut plus s'en servir pour encoder.**
Autorisé par le client le 2026-08-31. Il n'y a ni `brew` ni `port` sur cette machine,
mais un **binaire statique arm64** suffit, et il ne s'installe nulle part : on le pose
dans le dossier de travail, rien à désinstaller, aucun `PATH` touché.

    curl -sSL -o ff.zip https://www.osxexperts.net/ffmpeg9arm.zip
    unzip -q ff.zip -d ffbin/ && xattr -d com.apple.quarantine ffbin/ffmpeg
    ffbin/ffmpeg -version        # 9.0, libx264, natif arm64

**L'ÉCART AVEC `avconvert` EST D'UN FACTEUR CINQ, ET IL FAUT LE SAVOIR.** Le film
produit, 50,9 s :

| outil | réglage | résultat |
|---|---|---|
| avconvert | Preset960x540 | 960x540, **24,7 Mo** |
| avconvert | Preset640x480 | 640x360, 13,0 Mo |
| ffmpeg | libx264 CRF 20 | **1280x720, 4,95 Mo** |
| ffmpeg | libx264 CRF 22 | 1280x720, 3,57 Mo |

Autrement dit : `avconvert` donnait cinq fois plus lourd pour une résolution
INFÉRIEURE, parce qu'il n'a aucun réglage de débit et applique un débit fixe quel que
soit le contenu. Sur ce film dont un tiers est du texte statique sur fond noir, la
différence est énorme. Vérifié à la taille réelle du cadre (542 px) : source, ancien
encodage et nouveau sont **indiscernables**.

La commande employée, et le modèle pour les suivantes :

    ffbin/ffmpeg -i source.mp4 -an \
      -vf "scale=1280:720:flags=lanczos" -c:v libx264 -preset slow -crf 20 \
      -pix_fmt yuv420p -profile:v high -level 4.0 -movflags +faststart sortie.mp4

Trois options qui ne sont pas décoratives : **`-an` retire réellement la piste
audio** (le client veut le site sans le son, et jusqu'ici on ne pouvait que la couper
par `muted` en gardant ses octets) ; **`-movflags +faststart`** met l'index en tête
pour que la lecture démarre sans attendre le fichier entier ; **`-pix_fmt yuv420p`**
est ce qui rend le fichier lisible partout.

**PIÈGE DE SHELL RENCONTRÉ** : en zsh, `scale=$2:$3:flags=lanczos` perd le `:fl`
derrière un paramètre positionnel, et ffmpeg reçoit `540ags`. Il faut accolader,
`scale=${2}:${3}:flags=lanczos`.

**ET UN PIÈGE DE MÉTHODE, LE MIEN** : dans la même passe, un remplacement écrit SANS
assertion a échoué en silence sur le docstring d'un générateur, et je ne m'en suis
aperçu qu'en relisant le fichier. C'est la règle du dépôt, et elle vaut aussi quand on
croit la chaîne triviale : **toute substitution porte une assertion, et on extrait la
chaîne du fichier au lieu de la retaper.**

### NOTE D'OUTILLAGE VIDÉO, et elle vaut pour tout travail de ce genre ici

**Le Chromium de Playwright NE DÉCODE PAS le H.264.** Ses images reviennent toutes à
zéro et l'on conclut à tort que le film est noir. C'est **WebKit** qui décode, sur les
codecs du système. Et une toile ne rend ses pixels que si la page et la vidéo ont la
MÊME origine, sinon `getImageData` lève une erreur de sécurité : il faut servir une
page depuis le dossier de la vidéo.


## L'audit RosoAI vit HORS de ce dépôt, et il en est au contrôle n°6 (2026-08-31)

Ce fichier ne le disait nulle part, et deux défauts du contrôle n°5 sont restés quatre
jours en ligne pour cette raison. Le dispositif est dans
`/Volumes/CCCOMA_X64F/Roso SEO Squad - q-bot.eu` : onze agents en markdown, un
orchestrateur, et les livrables du client dans `audit-livrables/q-bot/`. L'état vit dans
`audit_state.json` et porte le **commit audité**, ce qui permet de mesurer le delta d'un
contrôle au suivant. Le périmètre est le NOUVEAU site en préproduction,
`https://q-leap.github.io/qbot-website/` ; le live `q-bot.eu` est un héritage à migrer.

**Contrôle n°6, commit `ec1ee15` : 6,4/10 à périmètre comparable, 8,9/10 sur le périmètre
auditable.** Les deux notes bougent en sens inverse, et c'est tout le sujet : la qualité
technique est au plus haut, la surface de contenu citable au plus bas.

### Le garde-fou à rejouer à chaque passage, parce que c'est lui qui trouve

**Ne pas vérifier que les exclusions répondent 404. Énumérer tout ce que l'hébergement
répond en 200, et vérifier que tout y a sa place.** C'est cette inversion qui a trouvé la
CAO du produit encore servie, et elle tient en quelques lignes : `git ls-files`, une
requête par fichier, puis on écarte les pages, les relais et les actifs employés. Passée
le 2026-08-31 sur 226 fichiers : 150 servis, 76 non servis, deux intrus.

### Ce que le contrôle n°6 a fait corriger, et qui vaut d'être retenu

- **Le dessin industriel du produit était servi en 200**, `assets/3d/Q-Leap Box_v3-08.obj`
  pour 32 257 622 octets. Sorti du suivi git ET de `_config.yml`, les fichiers restant sur
  le disque pour la chaîne du GLB. **L'historique git les contient toujours** et le dépôt
  est public : les en retirer vraiment demande une réécriture d'historique, décision du
  client.
- **Les 4 pages légales appelaient Google Fonts** pour une police déjà servie en local, sur
  la page de politique de confidentialité elle-même. Elles étaient les seules pages du site
  à appeler un tiers ; il n'en reste aucune. Et `gen-legal.py` les réintroduisait, tout en
  portant **deux empreintes d'actifs écrites à la main** qui rejouaient la panne de cache
  du 2026-08-25.
- **Les deux outils d'audit annonçaient « aucun défaut » sans avoir rien mesuré.** Lancés
  sans serveur local, ils affichaient des `TIMEOUT` puis la même conclusion qu'un contrôle
  réussi. Ils sortent désormais en **code 2** avec la marche à suivre, et leur ligne de
  résultat dit « N page(s) lue(s) sur M ». Un garde-fou qui ne crie pas ne protège pas.

### La régression, et c'est une décision du client

La suppression du blog et des 8 guides le 2026-08-28 fait passer le site de 44 à 20 pages,
de 90 H2 en forme de question à **10**, et de 74 capsules-réponses à **4**. Les 34 réponses
de FAQ sont la seule surface citable substantielle qui reste, et elles sont intactes.

Ce n'est pas un défaut d'exécution et il ne faut pas le traiter comme tel. Mais c'est la
seule vraie question ouverte : assumer une plaquette de 20 pages dont l'autorité repose sur
l'entité et la FAQ, ou remettre trois ou quatre pages piliers sans blog. `gen-guides.py`
est encore dans le dépôt.

### Les six autres points ouverts

4 Mo d'actifs orphelins encore servis (surtout les vignettes des guides et du blog
supprimés) · le texte des 4 pages légales qui décrit encore le WordPress, à faire relire
par qui l'a écrit · l'historique git qui contient la CAO · un Bookings en anglais, la page
Microsoft ne se traduisant pas · les incrustations anglaises du film sur les pages
françaises · `a-propos.html` à −20,1 % de parité, seule paire hors bande.


## Le ménage du contrôle n°6, et un outil qui ne pouvait plus servir (2026-09-01)

Reprise des points mécaniques laissés ouverts par l'audit RosoAI n°6. Les trois points
qui demandent une décision du client sont écartés ici, pas oubliés : le socle de contenu
citable (le blog supprimé a emporté 70 des 74 capsules), le texte des quatre pages légales
qui décrit encore le WordPress, et l'historique git qui contient toujours la CAO.

### Les actifs que plus aucune page ne cite quittent l'hébergement

33 fichiers, **4,89 Mo servis pour rien** : les 12 vignettes des guides et les 5 du blog
supprimés le 2026-08-28, les 10 visuels des générations précédentes du produit (dont
`device-comparison.png`, 2,45 Mo à lui seul) et 6 logos ou icônes sans emploi. Ils restent
sur le disque et dans git, conformément à l'usage du dépôt ; c'est `_config.yml` qui cesse
de les proposer.

**LE CONTRÔLE SE FAIT DANS LES DEUX SENS, et le second est celui qu'on oublie.** Le
premier énumère tout ce qui est servi et vérifie que chaque fichier y a sa place (c'est
l'inversion qui avait trouvé la CAO). Le second part des pages : aucune source servie
(HTML, CSS, JS, `llms.txt`, `sitemap.xml`) ne doit citer un actif exclu. **Exclure un actif
employé casse la page exactement aussi silencieusement que l'oubli d'exclure.** Relevé
après : 128 fichiers servis, 85 sources lues, **0 référence vers un actif exclu, 0 actif
servi sans référence**.

Faux positif écarté au passage : `git ls-files` **met entre guillemets et échappe en octal**
tout chemin non ASCII, si bien qu'une sonde qui compare ses lignes à la liste d'exclusion
signale `Screen modèle 3D/` comme servi alors qu'il répond 404. Vérifié en ligne. Le nom est
en NFC des deux côtés (`c3 a8`), le piège documenté le 2026-08-26 ne s'est pas reproduit.

### `maj-nav-booking.py` ne reconnaissait plus AUCUNE des 23 pages

Le défaut le plus sérieux de la passe, et il était invisible parce que le script ne se
plaignait pas. Son motif exigeait des attributs **à valeur** (`data-booking-src="…"`), or le
bouton équipé porte d'abord `data-booking-open`, qui est un attribut **nu**. Une fois les
23 pages équipées, il n'en reconnaissait donc plus une seule : **la « source unique » de
`bookings_conf.py` n'en était plus une**, et le jour où l'agenda change d'URL la commande
annoncée en tête du fichier n'aurait rien mis à jour, sans une ligne d'erreur.

Deuxième défaut au même endroit : le motif n'était **pas borné à la barre de navigation**.
Sur `faq.html` il attrapait un appel à l'action du CORPS de la page, qui porte le même
libellé et la même classe. Le script annonçait « 1 bouton équipé » en visant le mauvais
élément. La recherche est désormais bornée à `nav__actions` → `</nav>`.

**L'épreuve de vivacité est ce qui prouve le correctif**, et elle vaut pour tout outil de ce
genre : on change l'URL dans `bookings_conf.py`, on relance en simulation, on doit lire
**23 boutons équipés** ; on restaure, on relance, on doit lire **0, et 23 « déjà à jour »**.
Un outil idempotent qui n'a jamais été vu écrire n'est pas prouvé, il est muet.

### Deux comptes écrits à la main, et deux jumeaux qui divergeaient

- `go-live.py` annonçait « les quatre newsletters » dans le rappel du jour J. Il n'y en a
  plus que **deux** depuis que les deux index de blog ont été supprimés. Les deux nombres se
  dérivent maintenant des pages, comme `NB_REDIRECTIONS` et `NB_PAGES` avant eux. Troisième
  fois que ce fichier se fait prendre par un chiffre écrit à la main dans le texte destiné à
  l'humain, qui est le pire endroit pour un chiffre faux ;
- `bump-assets.py` et `bump-assets.mjs` **ne comptaient pas les mêmes pages** (23 contre 24),
  alors que leur en-tête dit qu'ils doivent rester d'accord. La cause est un
  `en/._about.html`, fork de ressources macOS créé par toute écriture sur ce volume exFAT :
  `glob` de Python ignore les noms cachés, `readdirSync` non. Le jumeau Node les saute
  désormais. Ces fichiers sont déjà couverts par `.gitignore`, donc jamais commités.

### La page À propos anglaise dit enfin le périmètre

Seule paire hors bande de parité, **−20,1 %**. Deux ajouts, **aucune phrase écrite pour la
première fois ici** :

- la carte Q-Leap reprend la phrase que le français porte depuis toujours, et que le
  sous-titre anglais de cette même carte (« Consultancy & Training ») annonçait déjà ;
- la carte Q-Bot disait « drives the real 2FA app on **a real device** ». Le reste du site
  anglais énonce le périmètre **comme une limite** (Android, USB), et c'est une règle du
  dépôt : la formulation est reprise mot pour mot de `en/index.html` et `en/use-cases.html`.

Résultat : **−12,9 %**, dans la bande naturelle de 10 à 15 %. **La carte Q-Guard reste
volontairement divergente** : son texte anglais est celui du live, distinct du français par
une décision documentée du 2026-07-09. Ne pas l'aligner par souci de symétrie.

### Contrôles

`audit-a11y.py` à 1440 et 390 px et `audit-visibilite.py` : **21 pages lues sur 21, 0
constat**. 75 pages, 738 liens relatifs, **0 cassé**. 52 relais, 0 défaut.
`sync-faq-jsonld.py` idempotent (34 comparées, 0 recalée). `maj-sitemap.py` sans écart.
Les deux versionneurs d'actifs à 0 page à mettre à jour, donc les empreintes servies sont
celles des fichiers. Les deux pages À propos menées au navigateur en normal et en mouvement
réduit, à 1440 et 390 px : un seul `h1`, 0 révélation invisible, 0 débordement, 0 image
cassée, 0 erreur console, et 0 `.nb` dans un conteneur flex.


## Les politiques de confidentialité décrivent enfin ce site (2026-09-01)

Quatre arbitrages du client sur les points laissés ouverts par le contrôle n°6, dont trois
qui ferment un point pour de bon. À ne pas rouvrir aux passages suivants.

### 1. LE SOCLE DE CONTENU NE REVIENT PAS. C'EST UN REFUS, PAS UNE ATTENTE

« Mon directeur veut pas. » La suppression du blog et des huit guides le 2026-08-28 a fait
passer le site de 74 capsules-réponses à 4 et de 90 titres en question à 10 ; l'audit
proposait de remettre trois ou quatre pages piliers sans blog. **C'est non.** Le site
assume d'être une plaquette technique de 20 pages dont l'autorité repose sur l'entité (le
fondateur nommé et relié, `legalName`, `foundingDate` au jour près, `knowsAbout`, la
citation de presse) et sur les 34 réponses de FAQ, qui sont intactes et de bonne facture.

`tools/gen-guides.py`, `gen-index-guides.py` et `vignettes_guides.py` restent dans le
dépôt : ce sont des outils, pas du contenu publié, et ils ne risquent pas d'être
« décommentés » par accident comme l'était le bandeau de références. **Ne pas reproposer de
remettre des guides**, et ne pas compter la baisse de surface citable comme un défaut : elle
est le résultat d'une décision informée, prise deux fois.

### 2. LES DEUX POLITIQUES DE CONFIDENTIALITÉ SONT REPRISES

« Fix ça en fonction du nouveau site. » Elles décrivaient le WordPress qu'elles remplacent.
Mesuré avant reprise sur les 21 pages : **0 `document.cookie`, 0 balise d'analytics,
0 requête vers un tiers au chargement**, aucun compte client, aucune commande, et un
hébergement GitHub Pages. Le texte, lui, annonçait des cookies « sous réserve de vos
choix », des scripts et pixels tiers, un traitement « notamment par Google Analytics » et
des serveurs « exclusivement situés au sein de l'Union européenne ».

**UNE POLITIQUE QUI ANNONCE PLUS DE COLLECTE QU'IL N'Y EN A N'EST PAS PRUDENTE, ELLE EST
FAUSSE**, et sur ce point le sens de la correction est agréable : la nouvelle version
collecte moins, il suffisait de le dire.

**Les écarts avec le live sont ÉNUMÉRÉS dans `tools/gen-legal.py`, et nulle part ailleurs** :
`SECTIONS_AMENDEES` pour les sections remplacées ou supprimées, `RETOUCHES` pour les
corrections ponctuelles, chacune avec sa raison **et son assertion**. Si le live est relevé
à nouveau et que le texte visé a bougé, le script s'arrête au lieu de remplacer le mauvais
paragraphe ou de laisser tomber l'amendement en silence. Quatre sections reprises
(cookies, contenus tiers, appareils mobiles, lieu de stockage) et neuf retouches, dont
l'adresse du siège anglaise restée à Mathias Hardt, trois « Q-LEAP NV » pour une SA, une
phrase dupliquée et `bot.q-leap.eu`. **Les conditions de vente ne sont pas touchées** :
elles décrivent le contrat de location, pas le site.

Effet de bord voulu : les deux politiques portent désormais la même date, ce qui referme
l'année de retard de l'anglais signalée depuis le 2026-08-25.

**L'ADRESSE DU SIÈGE DES CONDITIONS DE VENTE EST CORRIGÉE AUSSI (2026-09-01, confirmé par
le client).** Leur clause de définitions donnait encore « L-1717 Luxembourg, 10 rue Mathias
Hardt », une seule fois par page et non deux comme je l'avais d'abord annoncé. Ce n'est pas
un écart de migration mais un fait d'état civil : le numéro RCS y est le même (B.167.970),
le `PostalAddress` des 23 pages, le `foundingLocation` et les deux politiques disent
Bertrange, et **le pied de page FRANÇAIS du live dit Bertrange lui aussi** — seul son pied
de page anglais est resté en arrière. Contrôlé après : **0 occurrence de « Mathias Hardt »
et de « L-1717 » sur le site entier**. Les conditions de vente ne portent pas de date de
mise à jour (le live n'en a pas), il n'y en avait donc aucune à avancer.

**La liste des finalités perd « Analyser le volume et l'historique de votre utilisation de
nos services » (2026-09-01, décision du client).** Le site ne mesure ni volume ni historique
de navigation, et il n'a aucun moyen de le faire. Les deux listes tombent à six items.

**PIÈGE DE LA SUPPRESSION D'UN ITEM DE LISTE** : le vidage du `<ul>` en cours n'a de sens
que si l'amendement a quelque chose à écrire à la place. Sans cette condition, un item retiré
au MILIEU d'une liste la ferme et la suivante en rouvre une seconde : le texte rendu est le
même, la sémantique et la puce ne le sont pas. Le contrôle est de compter les `<ul>` et leurs
enfants, pas de relire le texte — relevé après : deux listes de 6 et 4 items dans les deux
langues, comme avant, l'item en moins.

**Il ne reste plus rien à arbitrer sur ces quatre pages.**

### 3. ON NE RÉÉCRIT PAS L'HISTOIRE GIT, ET C'EST UNE MESURE QUI LE DIT

« Fais ce qui est le plus logique. » Mesuré : `assets/models/qbot.glb`, **servi
publiquement** et téléchargeable en un clic depuis la séquence 3D de l'accueil, porte
**191 214 triangles contre 199 322 pour le FBX**, soit 96 % de la géométrie aux soudures de
sommets près. **La forme du boîtier est donc déjà publiée, à dessein.** Une réécriture
d'historique coûterait un `push --force`, ne supprimerait rien de github.com sans passer par
leur support (les objets déréférencés restent joignables par leur empreinte) et ne
retirerait pas de la vue ce qu'elle prétend protéger.

Ce que l'exclusion du 2026-08-31 a réglé reste réel et acquis : 37 Mo de **CAO éditable**
téléchargeables depuis le site du produit. La seule décision qui irait plus loin est le
passage du dépôt en privé, qui demande un plan GitHub payant. Le raisonnement est écrit dans
`.gitignore`, à côté de la ligne d'exclusion, pour que le point cesse d'être rouvert.

### 4. LE BOOKINGS ANGLAIS EST REPORTÉ

« Plus tard la version anglaise. » Le marqueur `BOOKINGS-EN-A-VENIR` de `en/booking.html`
reste, il n'y aura qu'une URL à remplacer. Les incrustations anglaises du film sur les pages
françaises restent aussi : c'est une propriété du fichier fourni.

### `gen-legal.py` était MORT depuis trois jours, et il aurait fait cinq régressions

Trouvé en voulant l'utiliser. Il extrayait son habillage de `blog/innovation-merkur.html` et
`en/blog/innovation-merkur.html`, **supprimés le 2026-08-28** : il s'arrêtait sur une
`ValueError`. Et une fois réparé naïvement, une régénération aurait défait cinq passes
sitewide, toutes silencieusement :

1. le **fil d'Ariane visible**, retiré du site le 2026-08-28, revenait sur les quatre pages
   légales et sur elles seules ;
2. l'**appel à l'action** disait encore « Vous souhaitez en savoir plus ? » et « Prendre
   rendez-vous » là où le site dit « Voir Q-Bot en action » et « Réserver une démo » ;
3. `og:site_name` revenait à « Q-Bot by Q-Leap », alors que le produit s'appelle « Q-Bot »
   partout depuis le 2026-08-28 ;
4. les **36 `<span class="nb">Q-Bot</span>`** des deux politiques disparaissaient ;
5. le pied de page du gabarit marque SA PROPRE entrée comme courante : « À propos »
   arrivait sur les quatre pages légales en texte mort au lieu d'un lien.

**LA LEÇON EST GÉNÉRALE : UN GÉNÉRATEUR QUI N'A PAS TOURNÉ DEPUIS UNE PASSE SITEWIDE EST
UNE RÉGRESSION EN ATTENTE.** Le contrôle qui les a toutes attrapées est le même à chaque
fois : régénérer, puis **comparer au fichier d'avant**, et n'accepter que les écarts qu'on
sait nommer. Les libellés qui vieillissent sont donc **extraits d'une page du site** plutôt
qu'écrits dans le script, et les bornes d'extraction sont structurelles (`<header class="nav"`)
et non des commentaires de bandeau : `a-propos.html` porte ses bandeaux « ======= », pas
`en/about.html`, et un découpage par commentaire marchait sur une langue et échouait sur
l'autre.

**Et un piège d'outillage à connaître** : `bump-assets` remplace le paramètre `?v=` **partout
dans le fichier, commentaires compris**. Le commentaire du gabarit citait un chemin versionné
en exemple : il en est ressorti en bouillie (« style.css?v=f17ca7a1'empreinte réelle »). Ne
jamais écrire d'exemple de chemin versionné dans une page.

### Contrôles

`gen-legal.py` **idempotent** (deux exécutions, même empreinte MD5). Les deux audits sur les
21 pages à 1440 et 390 px : **0 constat**. 75 pages, 738 liens relatifs, 0 cassé. 52 relais,
0 défaut. `sync-faq-jsonld.py` idempotent, `maj-sitemap.py` sans écart, `maj-nav-booking.py`
à 23 « déjà à jour » APRÈS régénération, donc les attributs de la fenêtre de réservation ont
survécu. Les quatre pages légales menées au navigateur en normal et en mouvement réduit, à
1440 et 390 px : un seul `h1`, 0 révélation invisible, 0 débordement, 0 erreur console,
**0 cadratin, 0 emoji**, 0 `.nb` dans un conteneur flex, et plus aucun fil d'Ariane visible.
Contrôlé enfin qu'aucune des formules retirées ne subsiste : 0 « Google Analytics »,
0 « bot.q-leap.eu », 0 « Q-LEAP NV », 0 « Mathias Hardt » et 0 « exclusivement situés » dans
les deux politiques.


## Contrôle n°7 : les outils étaient l'angle mort des six contrôles précédents (2026-09-01)

Contrôle demandé par le client sur `https://q-leap.github.io/qbot-website/`, au commit
`c844ff0`, dix commits après le n°6. Le livrable vit hors du dépôt, dans
`audit-livrables/q-bot/Analyse_Controle_7_Post_Corrections.md`.

**Le site est mesuré sans un seul défaut**, et les quatre points ouverts du n°6 qui
dépendaient de nous sont refermés. Le fait de ce passage est ailleurs : **six contrôles
successifs ont mesuré les PAGES et jamais les OUTILS qui les fabriquent.** Quatre des
quatorze scripts étaient cassés ou dangereux, tous silencieusement.

### `gen-guides.py` a recréé les seize pages de guides, et je l'ai déclenché moi-même

Le plus sérieux, et ce n'est pas une hypothèse : une simple boucle « est-ce que les outils
tournent encore ? » a lancé `gen-guides.py` **sans argument**, et il a écrit les huit guides
français et les huit anglais avant d'échouer sur son garde-fou de fin. Le contrôle suivant a
compté 39 pages au lieu de 23, et il a fallu retirer les seize fichiers un par un.

**Un générateur sans mode simulation devient une arme chargée le jour où son contenu est
retiré à dessein.** Le blog a été supprimé le 2026-08-28 et son retour refusé par le
directeur le 2026-09-01 : `gen-guides.py` et `gen-index-guides.py` refusent donc désormais
de s'exécuter sans `--republier-le-blog`, en disant pourquoi et en sortant en code 2. Le
drapeau existe parce que la décision peut changer ; il est explicite parce qu'elle ne doit
pas changer par accident.

### `fetch-legal.py` : les deux bouts de la chaîne ne se parlaient pas

Il écrivait `legal/plein.json`, dans un dossier qui n'existe pas, quand `gen-legal.py` lit
`tools/legal-source.json`. La chaîne documentée en tête des deux fichiers échouait donc au
premier pas, et aurait de toute façon écrit à côté. Il lançait en outre le navigateur en
mode **fenêtré**, contre la règle du 2026-08-25, pour une lecture de DOM qui n'en a aucun
besoin, et il écrasait le relevé sans sauvegarde.

**Et il a une date de péremption** : il relève le WordPress, qui disparaît à la bascule.
Après quoi `tools/legal-source.json` est le seul exemplaire du texte d'origine, ce qui
compte d'autant plus que `gen-legal.py` en dérive maintenant un texte amendé. D'où la
sauvegarde `.avant` et l'assertion sur la taille du relevé.

### Ce que le contrôle a mesuré, et qui est propre

21 pages lues en ligne, au rendu : **un seul `h1` partout, 0 saut de niveau, 73 images
0 sans `alt`, 21 titres distincts de 26 à 58 caractères, 21 descriptions distinctes de 100 à
156, 49 blocs JSON-LD sans erreur, 0 `offers`, 60 balises `hreflang` auto-référentes et
réciproques, 0 requête vers un tiers, 0 erreur console, 0 requête en échec.** Les 224
fichiers suivis testés un par un contre l'hébergement : **115 servis, 109 non servis, et
aucun actif servi sans référence** — le ménage du matin tient. Balayage des révélations sur
21 pages × 3 vues (1440, 390, mouvement réduit) **en ligne** : aucune anomalie.

**La FAQ, seule surface citable substantielle depuis la suppression du blog, est en bon
état** : 17 réponses par langue, **16 ouvertures sur 17 dans la fenêtre de 40 à 60 mots**,
aucune sous 35 mots, la seule hors fenêtre étant trop LONGUE (66 et 70 mots).

**Le poids ne se compare pas d'un contrôle à l'autre sur le premier écran** : la valeur
dépend du moment où l'on arrête de compter, et l'accueil charge son modèle 3D en `eager`.
Seule la page parcourue est stable : accueil 5,01 Mo, `caracteristiques` 5,36 Mo, tout le
reste sous 0,25 Mo.


## Retours du 2026-09-01 : le vocabulaire, le visuel de « La solution », le rythme

Quatre retours du client, plus une question laissée ouverte pour Sylvain Perez.

### « Authentification forte » devient « authentification 2FA »

Six occurrences, quatre fichiers, deux langues : les deux titres de hero, les deux
variantes d'accueil, et les deux phrases sur les projets RPA. Contrôle : **0 occurrence
de « authentification forte » et de « strong authentication » sur tout le site.**

**L'ANGLAIS NE DIT PAS « 2FA AUTHENTICATION »**, qui est un pléonasme : le titre devient
« 2FA no longer blocks your tests. » C'est la règle du dépôt appliquée à l'envers de son
sens habituel — le français rend l'intention, l'anglais dit ce qui se dit en anglais.

**CE QUE CE REMPLACEMENT COÛTE, ET IL FAUT LE SAVOIR** : « authentification forte » est le
terme réglementaire français (DSP2), donc une requête réelle, et il ne figure plus nulle
part. « 2FA » est cité 66 fois côté français, « double authentification » 12 fois,
« authentification à deux facteurs » **une seule fois**. Le site est donc très fort sur le
sigle et faible sur les deux formulations longues, qui sont celles que tape quelqu'un qui
ne connaît pas encore le produit. À arbitrer par le client : réintroduire « authentification
forte » une fois, dans une réponse de FAQ, ne contredirait pas le titre du hero.

### Le visuel de « La solution » montre enfin le mécanisme

La section s'intitule « Automatiser la double authentification (2FA) » et montrait un rendu
du boîtier : **le titre parle d'un mécanisme, l'image montrait un objet**, déjà visible
trois fois sur la page (hero, séquence 3D, feuille de route).

**REMPLACÉ LE JOUR MÊME par un visuel fourni par le client**, voir la section suivante.
Le schéma reste dans git et son outillage aussi, mais il est exclu de l'hébergement : la
règle du jour est qu'aucun actif servi n'est sans référence. Il se remet en place en
changeant un `src`.

`assets/img/qbot-2fa-flux.jpg` (+ `-en`) est un **schéma** construit en HTML puis capturé,
dans le langage de `tools/render/guide-thumbs.html` : chaîne de tests → appel HTTP
(`GET /scenarios/:id/execute`) → Q-Bot et son téléphone Android → appuis dans la vraie
application 2FA → le test continue. Aucune licence tierce, aucune image générée, et
l'alternative textuelle dit « Schéma », donc rien n'est présenté pour ce qu'il n'est pas.
Régénéré par `tools/render/shoot-solution-visual.py`.

**NOUVEAU MODIFICATEUR `.intro__image--schema`, ET IL EST OBLIGATOIRE ICI.** Le cadre
sur-dimensionne son image de 8 % au repos, marge dont le contre-parallaxe interne a besoin
sur une PHOTO. Sur un schéma dont le libellé teal est posé à 5,8 % du bord, cette
sur-échelle le rogne. La classe la ramène à 1 et retire le contre-parallaxe dans `main.js`,
exactement comme `--product`. Même famille que la pastille « MADE IN LUXEMBOURG » rognée le
2026-08-26 : **une image dont un bord porte de l'information ne se sur-cadre pas.**

**ET LA PREMIÈRE MESURE DU CADRE ÉTAIT FAUSSE.** J'avais relevé 741 px de large à 2560 px :
c'était la boîte TRANSFORMÉE, lue avant la fin de la révélation, la variante « média »
partant à `--media-scale + 0.05`. **`getBoundingClientRect()` inclut la transformation** ;
il faut `offsetWidth`, ou mesurer une fois la révélation finie. La vraie boîte fait
656 × 492 px. Relevé après : rapport source/affiché de 1,14 au plus serré, **0 rognage**.

### Le rythme entre « La solution » et la séquence : 484 → 420 px

Deux leviers, mesurés avant et après :

- **`.scrolly__step` : `padding-top` de 96 à 48 px.** Le contenu étant CENTRÉ dans le pas,
  ce retrait le repousse de la MOITIÉ de sa valeur : la première carte descendait de 48 px
  sans raison. Elle reste largement sous la barre de navigation ;
- **la section qui précède la séquence perd 40 px de remplissage bas** (112 → 72). Le rythme
  de 112 px vaut entre deux blocs de TEXTE ; ici la suivante ouvre sur une scène 3D sombre
  et vide, et les 112 px s'ajoutent à ce vide au lieu de séparer deux choses.

**Deux pièges, tous deux silencieux :**

1. **la séquence n'est PAS le frère immédiat de la section** : le lien d'évitement « sortir
   de la séquence » est inséré entre les deux. Écrit `.section:has(+ .scrolly)`, la règle ne
   correspondait à rien, sans erreur, comme tout sélecteur qui ne matche pas. Le contrôle
   qui l'attrape est `element.matches(...)` dans le navigateur, pas la lecture du CSS ;
2. **borné à `min-width: 901px`, et ce n'est pas une précaution de principe** : sur téléphone
   `--section-py` vaut 64 px, donc une valeur fixe de 72 px AUGMENTERAIT l'écart de 8 px.

**ET J'AI MESURÉ TOUTE LA GÉOMÉTRIE EN MOUVEMENT RÉDUIT AVANT DE M'EN APERCEVOIR.** La note
du 2026-08-25 dit qu'une sonde de disposition doit mesurer en `reduced_motion`, parce que les
révélations échelonnées faussent les largeurs. **Cette règle ne vaut PAS pour la séquence
épinglée** : le mouvement réduit y change la mise en page elle-même (la scène cesse d'être
collante, `--scrolly-screens` retombe à `auto`, `.scrolly__step` reçoit son propre
remplissage). Toute mesure de cette section se fait en mouvement NORMAL, révélations
attendues.

### Une passe sur les mots-clés

Relevé sur le texte rendu des 16 pages du plan. FR : **2FA 66 · téléphone 42 · robot 23 ·
LuxTrust 21 · Android 17 · double authentification 12 · Selenium 11 · automatisation des
tests 7 · authentification à deux facteurs 1.** EN : **2FA 67 · phone 31 · robot 24 ·
LuxTrust 23 · Android 20 · two-factor authentication 13 · test automation 8.**

Deux titres ne contenaient pas le mot-clé du produit et le portent désormais, sur les quatre
pages concernées (titre, `og:title` et `twitter:title` ensemble, la règle du dépôt étant que
les métadonnées sociales suivent le titre) : les deux FAQ et les deux pages de cas d'usage.
Tous restent sous 62 caractères et distincts. **Les autres titres n'ont pas été touchés** :
ils portent déjà « 2FA » ou « LuxTrust », et réécrire un titre qui fonctionne pour y caser un
mot de plus se paie en lisibilité.

**Ce que la passe recommande et qui n'est PAS fait**, parce que c'est de la rédaction et non
une correction : la famille longue (« double authentification », « authentification à deux
facteurs ») est sous-représentée en français au regard du sigle, et c'est elle que tape
quelqu'un qui ne connaît pas encore le produit.

**Faux positif à connaître** : `accueil-bis.html` porte un titre de 69 caractères. C'est la
maquette de comparaison, hors plan du site et `noindex` ; les audits l'ignorent puisqu'ils
énumèrent depuis `sitemap.xml`. Ce n'est pas un défaut.

### ~~LAISSÉ OUVERT~~ TRANCHÉ LE MÊME JOUR : « Android » devient « smartphone »

**Voir la section suivante : le client a tranché après avoir lu ce qui suit.**

#### Ce qui était sur la table

Le client signale que le périmètre Android est un frein commercial et demande de voir avec
Sylvain s'il ne faut pas dire simplement « smartphone ». **Rien n'a été changé**, et voici ce
que cette conversation doit peser, parce que le site a déjà tranché l'inverse deux fois :

- l'étape 1 de l'audit RosoAI (2026-08-24) a **retiré** « automatiser la 2FA dans 100 % des
  cas de tests » précisément parce que Q-Bot pilote un appareil Android ;
- la question 17 de la FAQ, ajoutée le 2026-08-25 sur décision du client, s'intitule
  « Q-Bot fonctionne-t-il avec iOS (iPhone) ? » et répond non ;
- `llms.txt` énonce la limite noir sur blanc et interdit d'écrire « 100 % of test cases » ;
- « Android » est cité 17 fois côté français et 20 côté anglais.

Dire « smartphone » sans qualifier ne serait donc pas un adoucissement de formulation mais
**une promesse que le produit ne tient pas**, et elle contredirait une réponse de FAQ à deux
clics de là. Deux formulations tiennent les deux bouts, si l'objectif est d'ouvrir sans
mentir : « un vrai smartphone (Android) » en accroche, la limite restant énoncée dans la FAQ
et la fiche technique ; ou l'inverse, garder « Android » et rendre la limite moins frontale
en la déplaçant plus bas dans la page. La décision est au client, pas ici.


## Le visuel de « La solution » : celui du client, et deux réserves (2026-09-01)

Le schéma construit le matin est remplacé par une image fournie par le client :
`assets/img/qbot-2fa-dock.jpg`, le boîtier sur un bureau, un smartphone Android inséré,
une demande de validation 2FA à l'écran.

**Recadrée au carré (1086 × 1086, de 300 à 1386 sur l'original de 1086 × 1448) parce que le
sujet est presque carré** : le boîtier occupe 950 px de large pour 960 de haut, donc un
cadrage en 4/3 coupe soit le haut du téléphone soit le bas du boîtier. Le cadre n'impose
aucun rapport, il prend celui de l'image ; à 1440 px la colonne d'image fait 526 × 526
contre 479 px de texte, les deux colonnes sont donc équilibrées. Agrandissement mesuré :
1,03 à 1440 px, 0,83 à 2560 px, **aucun agrandissement au-delà de 1,03**.

**DEUX RÉSERVES SIGNALÉES AU CLIENT, ET ELLES SONT DANS LE COMMENTAIRE DE LA PAGE :**

1. **c'est une image de synthèse**, ce que le dépôt avait écarté le 2026-08-24 en retirant
   tous les rendus IA. La signature habituelle est présente : la ligne gravée sous
   « Q-BOT » est illisible, du texte qui imite du texte. Elle est minuscule à la taille
   d'affichage, mais elle est là. Remise **sur demande explicite du client**, donc la note
   du 2026-08-24 (« ne pas les remettre en ligne ») connaît ici son exception, décidée par
   le propriétaire des images ;
2. **l'écran du téléphone montre une validation LuxTrust inventée**, citant MyGuichet, un
   service réel de l'État luxembourgeois. Le site déclare par ailleurs, dans `llms.txt` et
   dans le guide LuxTrust, n'avoir **aucun lien** avec LuxTrust. C'est le point qui mérite
   un avis de Sylvain Perez, pas la question du rendu.

**Le modificateur `.intro__image--schema` est retiré**, faute d'emploi : une classe CSS
morte et un `:not()` qui ne filtre rien sont exactement ce qu'un audit relève. **La leçon
qu'il portait reste vraie et doit être réappliquée si un schéma revient dans un
`.intro__image`** : le cadre sur-dimensionne son contenu de 8 %, marge dont le
contre-parallaxe a besoin sur une PHOTO ; sur un schéma dont un libellé est posé près du
bord, elle le rogne. Il faut alors `--media-scale: 1` **et** sortir l'image de la table du
contre-parallaxe dans `main.js`.


## L'image tient dans la colonne de texte, et la carte se cale en haut (2026-09-01)

Deux derniers réglages demandés par le client sur la même section.

### `.intro__image--fit` : la hauteur de l'image est celle du texte

Demandé : « que l'image tienne entre LA SOLUTION et En savoir plus ». Mesuré avant : l'image
carrée dépassait la colonne de texte de **47 px à 1440 et de 233 px à 2560**, la colonne de
texte se raccourcissant quand la fenêtre s'élargit alors que l'image, elle, s'élargit.

**LE MÉCANISME EST DE SORTIR L'IMAGE DU CALCUL DE LA RANGÉE.** En `position: absolute` elle
ne compte plus dans la hauteur de la grille : la rangée est dictée par le TEXTE seul, et le
cadre en prend la hauteur. Relevé après : **image et texte à la même hauteur au pixel près à
901, 1024, 1280, 1440, 1920 et 2560 px** (516, 495, 480, 480, 423, 423).

Quatre points à ne pas défaire :

- **`align-self: stretch` est OBLIGATOIRE et explicite.** `.intro__grid` est en
  `align-items: center` : sans cette ligne le cadre n'est pas étiré et, son contenu étant
  hors flux, **il tombe à 0 px de haut** et l'image disparaît. Constaté ;
- **deux plafonds, aucune taille imposée.** Écrit `height: 100%` avec un `max-width` qui
  mord, la boîte devenait 387 × 516 et **l'image était écrasée** : mesuré à 901 et 1024 px,
  où la colonne est plus étroite que la rangée n'est haute. Avec `max-width` et `max-height`
  et des dimensions automatiques, le navigateur choisit la contrainte qui s'applique et
  garde le carré ;
- **le rayon et l'ombre passent sur l'IMAGE**, pas sur le cadre : celui-ci est plus large
  qu'elle dès que le texte est court, et son ombre dessinerait une boîte autour du vide.
  Même raison que sur `.specs__image` ;
- **`--media-scale: 1` et sortie de la table du contre-parallaxe**, comme la variante
  « produit » : à 1,08 une image dimensionnée au pixel près déborde de son cadre.

L'image est collée à **droite**, donc sur la gouttière, jamais centrée dans sa colonne.
Sous 901 px elle reprend le flux et la pleine largeur : il n'y a plus de rangée à suivre.

### La carte de séquence se cale en haut de son pas

L'écart « LA SOLUTION » → « LE PRODUIT » a été resserré **trois fois dans la journée** :
484 px à l'origine, 420, 380, puis **197 px** (194 aux autres largeurs), le client ayant
donné 200 comme cible.

Les deux premiers pas jouaient sur des remplissages. Le troisième change le principe :
`align-content` passe de `center` à `start`. **Centrée, la carte dépendait de la hauteur de
la fenêtre et arrivait à environ 300 px du haut de son pas** — c'était l'essentiel de
l'écart, et aucun réglage de remplissage ne pouvait l'atteindre. Calée en haut, l'écart est
écrit noir sur blanc dans `padding-top` (164 px) et ne bouge plus avec la fenêtre.

Effet de bord accepté : la carte se lit désormais en regard du HAUT de la scène, ce qui est
cohérent (c'est là que le produit commence), et les pastilles numérotées passent sous elle
au lieu d'être à côté. Vérifié que la carte reste sous la barre de navigation (164 > 72) et
qu'elle tient dans l'écran aux cinq tailles du contrôle habituel, la plus serrée étant
1366 × 640 avec 183 px de marge.


## « Android » devient « smartphone », sauf là où ça deviendrait faux (2026-09-01)

**Décision du client**, prise après lui avoir remonté ce que le site avait déjà tranché deux
fois. Elle est appliquée : **80 remplacements dans 22 fichiers**, plus une correction isolée.
Décompte final sur le balisage servi : **16 « Android » contre 94 « smartphone »**.

### La règle de coupe : la prose change, le fait reste

Un remplacement en bloc aurait produit des phrases **fausses** et une **contradiction interne
à deux clics d'écart**. Le mot a donc été retiré partout où il n'était qu'une façon de nommer
l'appareil, et gardé partout où il porte le fait. Les seize occurrences restantes, une par
une, sont toutes de la seconde catégorie :

| Ce qui reste | Pourquoi on ne peut pas y toucher |
|---|---|
| « ADB, l'outil standard d'**Android** » (×2, + le lien vers `developer.android.com`) | ADB **est** l'outil d'Android. « L'outil standard de smartphone » ne veut rien dire |
| « Toute app 2FA **Android** » / « Any **Android** 2FA app » (×4) | c'est la liste de compatibilité. « Toute app 2FA sur smartphone » est faux, iOS est exclu |
| « n'importe quelle application qui tourne sous **Android** » et « installée sur **Android** » (×4, texte visible et JSON-LD, deux langues) | c'est l'énoncé du périmètre dans la FAQ |
| « la vraie limite : que le second facteur passe par une application **Android** » (×2) | c'est la phrase qui ÉNONCE la limite |

**LE CAS QUI TRANCHE LA QUESTION EST LA RÉPONSE 17 DE LA FAQ**, « Q-Bot fonctionne-t-il avec
iOS (iPhone) ? », qui répond non. Traduite en bloc, elle serait devenue : « Non […] Q-Bot
pilote un vrai smartphone […] il fonctionne avec n'importe quelle application 2FA installée
sur smartphone. » Elle se contredit elle-même en trois lignes. Dans sa forme actuelle elle
dit « smartphone » puis nomme Android comme la plateforme des applications, et le « non »
tient toujours. Vérifié à l'écran, dans les deux langues.

### `llms.txt` porte désormais l'avertissement, et c'est indispensable

Un moteur de réponse qui lit les pages y voit maintenant « smartphone » sans plateforme
nommée, et pourrait en déduire iOS. Le fichier dit donc explicitement que la formulation est
**un choix commercial et non un élargissement du périmètre**, que « any smartphone » n'est
jamais une revendication valable, et qu'il ne faut inférer aucun support iPhone du mot
« smartphone » où qu'il apparaisse sur le site.

### Ce que cette décision coûte, pour mémoire

Le site avait tranché l'inverse deux fois : l'étape 1 de l'audit RosoAI avait **retiré** une
sur-promesse pour cette raison exacte, et la question 17 avait été **ajoutée** sur décision du
client le 2026-08-25. Le périmètre n'a pas changé, seule sa mise en avant a changé : il n'est
plus annoncé en accroche, il est énoncé dans la FAQ, la fiche technique et la liste de
compatibilité. **Si un jour la question « pourquoi mon iPhone ne marche pas » remonte du
terrain, c'est ici qu'il faudra revenir.**


## Ce que le web dit de Q-Bot, et qui n'est plus vrai (2026-09-01)

Relevé aux outils gratuits, à la demande du client : recherche en direct et lecture de pages.
Aucun volume, aucune difficulté, aucun backlink — ces données n'existent pas sans un outil
payant ou sans la Search Console, et **il ne faut jamais en inventer**.

### La niche française est occupée par un article de presse de 2023, et par un blog

Sur « automatiser authentification LuxTrust tests automatisés », le seul résultat du sujet est
la **reprise ITnation de l'article Merkur**. Elle décrit l'ANCIEN produit : récupération de la
valeur de l'OTP, token LuxTrust, moins de dix secondes. C'est donc ce récit-là que le moteur
résume quand on cherche le sujet.

**ET LA NICHE N'EST PLUS TOUT À FAIT VIDE**, contrairement à ce que l'audit initial avait
établi : `latavernedutesteur.fr` publie depuis août 2024 une **série de trois articles** sur
« l'automatisation de tests dans un environnement sécurisé avec de l'authentification
multi-facteur », en français, signée Jonathan Bernales. C'est le concurrent éditorial le plus
proche, et il est francophone.

### Le web décrit encore l'actionneur et la caméra

Une recherche de marque produit ce résumé : « le bouton du token est poussé par un actionneur
piloté logiciellement, le code est capturé par une caméra ». C'est le récit retiré du site le
2026-08-19. Il vit sur des pages tierces qui ne sont pas dans ce dépôt : `krishworkstech.com`
(portfolio du sous-traitant), `3dprint.lu` (le partenaire d'impression), l'article ITnation,
et une page d'inscription webinaire sur le **propre Odoo de Q-Leap**. **Corriger le site ne
corrige pas ces pages-là**, et ce sont elles qui alimentent les résumés des moteurs tant que
`q-bot.eu` est fermé.

### La fiche annuaire existe, et elle annonce les deux revendications retirées

L'audit RosoAI notait « fiche G2/Capterra toujours absente ». **Il en existe une**, sur
Ministry of Testing, et sa description est, mot pour mot :

> Automate the use of tokens on 100% of your tests.

Soit le vocabulaire du token (retiré le 2026-08-19) **et** le « 100 % » (retiré le
2026-08-24), dans la même phrase. Elle pointe en outre vers `bot.q-leap.eu`.

### Le point qui entre dans la séquence du jour J

`https://bot.q-leap.eu/` répond **301 vers `https://q-bot.eu/`**, et cette redirection est
servie par le WordPress. Elle n'est pas décorative : c'est l'adresse que porte la fiche
annuaire. **Le jour où le WordPress est supprimé, ce lien tombe.** C'est désormais l'étape 4
de `tools/go-live.py`, avant la suppression du WordPress, avec la commande de contrôle.

### Ce que la SERP anglaise oppose, et ce qu'elle ne dit pas

Deux pages occupent le sujet. **Perforce / Perfecto** (« The Essential Guide to Automated 2FA
& MFA Testing », mis à jour le 27/11/2024, ~1 200 mots) tient le format que l'audit RosoAI
recommande : titres en question, réponse encadrée en tête de section, et un aveu utile
(« l'automatisation de ces fonctionnalités n'est pas complètement possible avec Appium »).
Sa réponse est un **parc d'appareils réels dans le nuage**. Un article Medium tient l'autre
moitié du sujet, la **clé secrète TOTP** ; sa page refuse d'être lue par outillage (HTTP 403),
donc on n'en sait que ce que le moteur en résume.

**Et la documentation officielle de Selenium déconseille d'automatiser la 2FA**, en proposant
un jeton de test dédié. C'est la position la plus citée du domaine, et c'est exactement la
pratique contre laquelle Q-Bot se positionne : un jeton de test ne teste pas le vrai parcours.

**Aucune de ces pages ne parle de piloter un appareil physique posé sur le bureau, hors
nuage.** C'est l'angle que personne n'occupe. Ce n'est pas une recommandation de publier — le
retour du contenu a été refusé par le directeur du client le 2026-09-01 — c'est le relevé de
ce qui est vacant, pour le jour où la question se reposera.


## Le titre du hero, refait d'après les concurrents réels (2026-09-01)

Demandé par le client : « on peut avoir une meilleure catch phrase », en regardant les
concurrents, en restant pro et premium, et en pesant le référencement.

### Ce que disent vraiment les concurrents, relevé sur leurs pages

| | Titre de leur page d'accueil |
|---|---|
| mabl | « Don't build tests, build trust » |
| Sauce Labs | « Verify AI-generated code at the pace it's written. » |
| Kobiton | « Mobile App Testing on Real Devices » |
| BrowserStack | « Everything you need for testing » |
| Katalon | « The AI platform for software quality » |
| Mailosaur | « Preview, test, and trust every customer touchpoint » |
| Perfecto | « Perfecto AI: Smarter App Testing for Enterprise Teams » |

**Deux familles, et il faut choisir laquelle** : ceux qui déclarent la CATÉGORIE, mot-clé
compris (Kobiton, Katalon, BrowserStack) et ceux qui posent une PROMESSE sans aucun mot-clé
(mabl, Sauce Labs). Les premiers sont trouvables, les seconds sont mémorables.

**ET LE MARCHÉ ENTIER DIT « IA » EN CE MOMENT** : Perfecto AI, la plateforme IA de Katalon,
les agents de BrowserStack, ceux de mabl, le code généré par IA de Sauce Labs. Q-Bot est
exactement l'inverse, et c'est vrai : du matériel, une vraie application, rien de deviné.
C'est un contre-pied qui se tient tout seul.

### Ce qui n'allait pas dans l'ancien titre

« L'authentification 2FA ne bloque plus vos tests. Vos campagnes vont au bout. »

- **c'était une négation** : il fallait déjà connaître le problème pour sentir la promesse ;
- **il ne portait pas le verbe de la requête.** On cherche « automatiser », il disait
  « ne bloque plus » ;
- la seconde phrase ne disait rien de vérifiable : au bout de quoi ?

### Le titre retenu, et pourquoi ces mots-là

> **Vos tests automatisés passent la double authentification.**
> *Sans clé secrète.*

- **il est affirmatif** et il tient en une proposition ;
- **il porte les deux expressions longues que le relevé disait faibles** : « tests
  automatisés » et « double authentification ». Le sigle « 2FA », lui, est déjà cité 68 fois
  et vit dans le `<title>` : les deux se complètent au lieu de se répéter ;
- **« sans clé secrète » est le différenciateur le plus tranchant, et il est sourcé.** Le
  relevé de SERP du même jour montre que la méthode dominante pour automatiser la 2FA est la
  clé secrète TOTP partagée, et que la documentation Selenium recommande carrément un jeton de
  test dédié. Trois mots suffisent donc à dire ce que Q-Bot fait autrement, à un lecteur qui
  est du métier.

**LE POIDS SEO D'UN TITRE DE HERO EST RÉEL MAIS SECONDAIRE, et il ne faut pas le surestimer.**
Le `<title>` et le contenu de la page pèsent davantage ; un `h1` aide à comprendre la
structure, ce n'est pas un levier de classement à lui seul. Et pour CE site, tant qu'il est en
`noindex`, sa valeur de référencement est **nulle**. Ce qui compte vraiment ici est autre
chose : c'est la phrase qu'un moteur de réponse citera en premier, donc elle doit être
**autonome, affirmative et vérifiable**. C'est ce critère qui a tranché, pas le comptage de
mots-clés.

**Coût de mise en page : zéro.** Mesuré avant/après en remplaçant le titre dans le navigateur :
**exactement la même hauteur** à 1440 px (5 lignes en français, 4 en anglais) et **37 px de
MOINS** à 390 px. Une version plus longue avait été écrite d'abord (« Sans clé secrète, sans
simulateur, sans personne devant l'écran. ») : elle montait à 8 lignes et 515 px, et faisait
gonfler le hero de 193 px. Un titre de hero se mesure, il ne se juge pas sur le papier.

L'anglais n'est pas la traduction du français, comme toujours ici, mais les deux portent la
même structure : « Your automated tests get past two-factor authentication. No shared
secret. » — « get past » est la formulation que les gens emploient réellement dans les forums
et les articles anglophones sur le sujet.


## Les listes de faits s'alignent, et la cause n'était pas la phrase (2026-09-01)

Signalé par le client sur une puce de `caracteristiques` : « moyen de changer la phrase pour
que ça rentre en une ligne ? Comme ça tous les points sont espacés de la même manière. »

**LA PHRASE N'ÉTAIT QU'UNE MOITIÉ DE LA CAUSE.** `.api-facts--deux` est une grille à DEUX
colonnes, et **une rangée de grille prend la hauteur de sa plus haute cellule** : la puce
longue passait sur deux lignes et entraînait sa VOISINE avec elle. Un point trop long en
abîmait donc deux, et raccourcir la seule phrase signalée ne suffisait pas — mesuré :
après ce seul raccourci, la liste passait de « toutes à 48 px » (uniforme par accident, tout
tenait sur deux lignes) à `[48, 48, 24, 24, 48, 48]`, c'est-à-dire **pire qu'avant**.

Trois choses ont donc été faites ensemble :

- **quatre puces raccourcies** dans la première liste et **une** dans la seconde, à 70
  caractères au plus. Budget mesuré, pas estimé : dans une cellule de 544 px, 70 caractères
  tiennent, 79 ne tiennent plus. On teste les candidats **dans le navigateur** en remplaçant
  le contenu de la puce, on ne compte pas les caractères sur le papier ;
- **la liste passe à une colonne sous 1200 px** au lieu de 760. Entre 1024 et 1199 la cellule
  tombait à 466 px et deux puces débordaient ; en une colonne l'item dispose de 1132 px et
  tout tient. Le seuil de 760 px ne servait à rien dans cette bande ;
- **une puce a retrouvé son sens au passage.** Elle listait « Selenium, Cypress, Playwright,
  Robot Framework, JUnit et de simples scripts shell » — 97 caractères, et surtout un
  DOUBLON : la grille de compatibilité, à quelques centaines de pixels plus bas sur la même
  page, liste déjà ces outils et six autres. Le fait que cette puce devait porter est celui
  de la section API, « compatible HTTP ». Elle dit désormais « Compatible avec toute chaîne
  capable d'un appel HTTP », ce qui est plus court, plus fort et non redondant.

Relevé après : **listes uniformes à 600, 768, 901, 1024, 1100, 1200, 1280, 1440, 1600, 1920
et 2560 px**, dans les deux langues. Reste 390 px, où une puce sur six tient sur une ligne
quand les autres en prennent deux : dans une colonne de 342 px c'est inévitable, et rallonger
une phrase pour égaliser des pixels serait pire que l'inégalité.

## Les quatre retours du 2026-09-02 : l'accueil s'allège, le film arrive

Lot de retours du client et de sa responsable communication, traité à la convention du
2026-08-28 : **un retour, un commit, un push**. Rien de ce lot n'est un défaut mesuré,
tout est un arbitrage éditorial, et deux points ferment des questions ouvertes depuis
des semaines.

### 1. La section « évolution » quitte l'accueil

« J'ai une réserve sur l'évolution de Q-Bot (pas utile sur la homepage). » Les trois
cartes (V1, génération actuelle, NFC) partent des deux accueils.

**Le bloc CSS est GARDÉ, comme `.timeline`**, parce que l'objection porte sur la PLACE et
non sur le motif : trois états du produit ont leur sens sur « À propos », pas sur la page
où le visiteur découvre le produit. **Une seule de ses classes reste employée ailleurs :
`.evo-card__link`**, qui sert de style de lien fléché sur les deux fiches techniques. La
retirer en croyant faire du ménage casserait ces liens.

**CE QUI PARTAIT AVEC LA SECTION, ET QU'IL FALLAIT SUIVRE.** Les douze relais des billets
de la frise datée visaient `index.html#evolution-title`. L'ancre n'existe plus, et une
ancre morte fait atterrir le visiteur en haut de page **sans le dire** : ils visent
maintenant l'accueil de leur langue, comme les autres archives. Les 52 relais regénérés,
vérifiés, 0 défaut. Et les deux visuels devenus orphelins sont exclus de la publication.

### 2. La newsletter tient en une ligne du pied de page

« La section newsletter prend trop d'importance sur la homepage, comme si c'était l'info
principale. On peut le mettre subtilement avec une phrase et un bouton discret dans le
footer. » Puis, et c'est la moitié qui décide de la forme : « à ce stade là, l'emailing on
n'est pas près d'en avoir un, d'autres priorités marketing ; ce qu'il nous faut c'est du
lead. »

**PAS DE FORMULAIRE, ET TROIS RAISONS CONCORDANTES** plutôt qu'un champ e-mail :

1. un champ dans le pied de page demanderait la case de consentement et sa mention
   Sendinblue sur les **23 pages**, pour un programme d'emailing qui n'existe pas ;
2. **l'endpoint Brevo du client REFUSE les envois** faute de jeton anti-robot (mesuré le
   2026-08-26, HTTP 400) : les formulaires retombaient **déjà** sur le courrier du
   visiteur. Le lien fait donc directement ce que le formulaire finissait par faire ;
3. une demande écrite par le visiteur lui-même est un consentement explicite et daté,
   sans case à cocher et sans sous-traitant.

La phrase est celle du live, mot pour mot, dans les deux langues. Le bouton est en teal
SUR le noir et jamais l'inverse (le teal de charte est une couleur claire : du blanc
dessus plafonne à 2,04:1). L'enveloppe dit le mécanisme avant le clic.

**LE POINT BREVO EST DONC FERMÉ**, après être resté ouvert chez les managers du client
depuis le 2026-08-26. Le compte de newsletters de `go-live.py` tombe à 0 et son rappel du
jour J ne demande plus de désactiver le reCAPTCHA ; `llms.txt` dit qu'aucun formulaire
d'inscription n'existe, pour qu'une IA n'en annonce pas un. **Ne pas rouvrir le sujet.**
Le CSS de la bande et le profil Brevo du module 15 sont gardés et annotés : ils portent
une correspondance de champs relevée chez le client, qui ne se redevine pas.

### 3. Le film de démonstration entre dans les deux accueils, avec ses commandes

« La vidéo Q-Bot qu'on a fait, ne doit-on pas la trouver sur le site, homepage ? C'est un
bon moyen de comprendre ce que fait Q-Bot et plus facilement que la lecture du contenu. »

Le film produit (`qbot-demo.mp4`, QBV1.2.12, 50,9 s) ne vivait que sur la fiche technique.
L'accueil portait `qbot-home.mp4`, une boucle muette de 8,7 s dans la moitié d'une
colonne, décorative et sans titre : c'est pourquoi personne ne « trouvait » le film. Il a
maintenant sa section, « Q-Bot en action », pleine largeur du conteneur.

**TROIS ÉCARTS AVEC LA BOUCLE DE LA FICHE TECHNIQUE**, et ils tiennent tous à ce que ce
film-ci est un CONTENU et non un décor :

1. il porte **`controls`**. Cinquante secondes qu'on ne peut ni arrêter, ni reprendre, ni
   rejouer se subissent ; celui-là sert à comprendre, donc il se pilote. D'où le
   modificateur **`.video__wrapper--playable`**, qui rend au lecteur les `pointer-events`
   que `--film` coupe. Règle posée APRÈS celle de `--film` : même spécificité (0,2,0),
   c'est l'ordre qui tranche ;
2. il n'est plus `aria-hidden` : il porte un nom accessible et sa section a un titre ;
3. il tient toute la largeur, aligné sur le titre.

Il reste `muted` et `loop` : la piste audio a été **retirée du fichier** (ffmpeg `-an`),
il n'y a donc rien à couper, et `muted` est ce qui autorise le démarrage automatique.

**ET LE MODULE 18 NE REDÉMARRE PLUS UN FILM QUE LE VISITEUR A ARRÊTÉ.** Sortir du champ
puis revenir relançait la lecture par-dessus sa décision. Le discriminant ne demande aucun
drapeau autour de notre propre appel : **le module ne met en pause que HORS champ, donc une
pause survenue DANS le champ vient forcément du visiteur.**

La section « 100 % conçu et développé au Luxembourg » passe en texte seul (ses deux
paragraphes extraits du fichier, pas retapés), à la mesure de lecture de
`.section-subtitle` et alignée sur la gouttière.

Poids : le premier écran ne change pas (**0 requête vers le `.mp4`** avant que la section
approche, sur les deux moteurs), et la page atteinte passe de 2,9 à 4,95 Mo de film.
L'ancienne boucle et son affiche sont exclues, et `qbot-film-poster.jpg` sort des **deux**
versionneurs d'actifs, qui doivent rester d'accord.

**Rappel de méthode, il a servi ici** : le Chromium de Playwright ne décode pas le H.264,
seul **WebKit** prouve la lecture. Relevé sur les deux : 0 requête au chargement, 1 à
l'approche, lecture en cours en vue, pause respectée au retour dans le champ.

### 4. La fiche technique s'ouvre sur une image

« Adapter le visuel au contenu, ici aussi, pour les sections. Manque quelque chose de
visuel au démarrage. Section : Un format pensé pour un poste de travail. »

Le défaut était structurel : le `.specs__grid` de cette section est une grille à **deux
colonnes et n'avait qu'un enfant**, donc la moitié droite était vide, juste sous un
en-tête de page qui n'a pas de visuel non plus. Deux blocs de texte pour ouvrir une fiche
produit. Elle porte désormais `qbot-photo-poste.jpg`, qui montre exactement ce que dit le
titre (le boîtier sur un bureau, à côté d'un clavier) et donne l'échelle que les trois
cotes chiffrent à côté. `.specs__image` et non `.intro__image` : c'est le cadre de la
section voisine, et surtout il ne sur-dimensionne pas son contenu.

**CE QUI RESTE UN ÉCART, ET IL DEMANDE UNE PHOTO QUE NOUS N'AVONS PAS.** La section « Un
nano-ordinateur de la taille d'une carte de crédit » montre `qbot-specs.jpg`, le boîtier
FERMÉ, alors qu'elle parle de ce qu'il y a dedans. Aucun visuel du dépôt ne peut corriger
cela : le GLB ne contient **aucune électronique** (coque, plateau, petite pièce, embase,
vitre), donc même une vue éclatée montrerait une coque vide, ce qui serait pire qu'un
écart. Il faut une photo du boîtier ouvert ou de la carte, à demander au client.

**Le schéma `qbot-2fa-flux.jpg` a été envisagé pour la section API et écarté, mesures en
main** : son contenu correspond au mot près (« un appel HTTP, et n'importe quelle chaîne
de tests »), mais il a été dessiné pour un cadre de 656 px. Dans une demi-colonne de
566 px ses sous-libellés tombent à **environ 10 px**. Le remettre en service demande de le
redessiner à la taille où il s'affichera, pas de le poser plus petit. C'est la règle des
vignettes du 2026-08-26 : on mesure la boîte qu'on remplit.

### Un reste trouvé par le contrôle des actifs, et la note qui mentait

Le contrôle « aucun actif servi sans référence » a remonté **`logo-baseline.png`**, et la
note d'à côté dans `_config.yml` disait précisément « attention, celui-là n'en est pas, le
JSON-LD `Organization.logo` le cite encore ». Ce n'est plus vrai depuis le changement de
logo du 2026-08-28 : les 21 pages pointent sur `logo-qbot.png`. **Une note qui dit
« attention, celui-là sert » se revérifie avant d'être citée**, comme celles qui disent
« laissé ouvert ».

Les six actifs qui restent hors du relevé sont cités par une URL **absolue** (JSON-LD,
`og:image`) ou chargés depuis une chaîne JavaScript (model-viewer, Draco, le sidecar
base64) : une sonde qui ne lit que `href`, `src` et `poster` ne peut pas les voir. Ne pas
les exclure sur la foi de ce relevé.

### 5. Le film réencodé : 4,95 → 2,02 Mo, et la résolution ne bouge pas

« Réencode la vidéo plus légère. » 59 % de moins, **depuis le master 1920x1080 et
jamais depuis le livré** (réencoder un encodage empile deux fois les pertes) : ffmpeg,
libx264, preset slow, **CRF 26**, `-an`, faststart.

**LA RÉSOLUTION NE BAISSE PAS, ET C'EST LE POINT.** Depuis que le film occupe toute la
largeur du conteneur de l'accueil, il s'affiche à 1132 px à 1440 et jusqu'à 1392 px sur
un large écran : descendre en 960x540 se verrait. C'est le CRF qui monte, pas la taille.

**LE CHOIX N'A PAS ÉTÉ FAIT À L'ŒIL**, et le tableau vaut d'être gardé pour la
prochaine fois :

| encodage | poids | SSIM | PSNR |
|---|---|---|---|
| CRF 20 (le livré d'avant) | 4,95 Mo | 0,9958 | 49,5 dB |
| CRF 24 | 2,64 Mo | 0,9940 | 47,2 dB |
| **CRF 26 (retenu)** | **2,02 Mo** | 0,9928 | 46,0 dB |
| CRF 28 | 1,59 Mo | 0,9914 | 44,8 dB |

Mesurés contre le master ramené en 720p. Puis les **trois zones à risque comparées au
pixel à la taille d'affichage réelle** : les incrustations de texte, un dégradé lisse du
rendu CAO (le pire cas pour une bande de compression) et le grain du bois des plans
réels. Indiscernables, **y compris à CRF 28** ; CRF 26 est retenu pour garder de la
marge sur cinquante secondes.

Effet de bord heureux : le film est désormais **plus léger que la boucle décorative de
2,9 Mo** qu'il a remplacée, donc l'accueil parcouru pèse moins qu'avant son arrivée.

**ET LE FILM REJOINT LES DEUX VERSIONNEURS D'ACTIFS.** Réécrit en place sous le même
nom, il serait resté servi depuis le cache du visiteur : c'est exactement le défaut du
2026-08-25, et **un média de 2 Mo en est le pire candidat**. Les deux jumeaux (`.py` et
`.mjs`) doivent rester d'accord, ils le sont.

### 6. La fiche technique montre le boîtier réel, pris dans le film

Réponse du client à la question laissée ouverte au point 4 : « pour l'image tu peux
prendre un screenshot d'une vidéo ou une image qui montre le Q-Bot. »

**LE FILM CONTIENT DES PLANS RÉELS, et personne ne les avait regardés.** Ses cinquante
secondes se décomposent en : logo, rendu CAO (t≈2-10), **prises de vue réelles du
boîtier en fonctionnement sur un bureau (t≈16-28)**, une capture d'écran de navigateur,
puis l'écran « supports major 2FA apps ». À t=23,0 s on voit le boîtier entier, le
smartphone inséré affichant une demande de validation LuxTrust, et le moniteur derrière
avec la page d'authentification eAccess et son QR code.

C'est cette image, recadrée 1340 x 1050 depuis le master et non retouchée
(`qbot-film-boitier.jpg`), qui remplace le rendu du GLB dans la section « Un
nano-ordinateur de la taille d'une carte de crédit ». Le rendu **reste servi** : les deux
pages FAQ l'emploient dans leur en-tête, il n'est donc pas devenu orphelin.

Trois choses à savoir :

- **la validation LuxTrust qu'on y voit est RÉELLE**, pas une maquette. C'est la
  différence avec la réserve notée le 2026-09-01 sur le visuel fourni de l'accueil, dont
  l'écran de téléphone était inventé : ici l'écran est celui de l'app, filmé ;
- **aucune donnée personnelle n'est lisible** : identifiant de session éphémère, aucun
  nom, aucune adresse autre que celle publiée sur le mur du bureau. À revérifier sur
  toute nouvelle image tirée de ce film, qui montre de vraies sessions ;
- **le cadrage et la compression ont été choisis sur des essais rendus côte à côte** :
  deux cadrages (le large, qui rapetissait tout, contre le serré retenu) et quatre
  qualités JPEG. q=4 (111 Ko) est indistinguable de q=2 (170 Ko) au zoom 2x sur le texte
  le plus fin du moniteur, PSNR 44,5 dB entre les deux.

**Le film est donc une banque d'images**, et c'est utile à savoir : la prochaine fois
qu'un visuel manque, extraire une image de `QBV1.2.12.mp4` coûte une commande. Le master
vit hors du dépôt, dans `/Volumes/CCCOMA_X64F/Q-Bot/Version/`.

**Ce qui reste vrai malgré tout** : aucune image ne montre l'INTÉRIEUR du boîtier, ni le
Raspberry Pi. Le film ne l'ouvre jamais. Si la section doit un jour montrer sa carte, il
faudra une photo prise chez Q-Leap.

## Ce qui restait corrigeable de l'audit, et le point qui n'existait pas (2026-09-02)

Question du client : « comment améliorer la note de 6 de l'audit ? », puis « corrige ce qui
est corrigeable ». Le dispositif RosoAI vit hors du dépôt et en est au **contrôle n°8**
(2026-09-01, commit `8beec51`) : **6,5/10 à périmètre comparable, 9,2/10 sur le périmètre
auditable**. Les deux notes n'ont pas bougé depuis le n°7.

**L'ARITHMÉTIQUE, PARCE QU'ELLE DÉCIDE DE TOUT.** La note comparable est la moyenne de dix
dimensions. Sept sont entre 8 et 9,5. **Trois sont à 4, 4 et 3 : l'écart concurrentiel, le
plan de visibilité IA et la visibilité IA mesurée (10/100).** Ce sont exactement celles qui
mesurent ce que le monde extérieur voit, et **aucune ne peut bouger tant que le site répond
`Disallow: /` avec `noindex` partout et qu'aucune propriété Search Console n'existe**.
L'audit ne compte pas cette fermeture comme un défaut et chiffre lui-même la note atteignable
le jour de la bascule : **7,4/10 sans écrire une ligne de contenu**. Le second levier, le
socle de contenu, a été **refusé par le directeur du client le 2026-09-01** : sans lui le
plafond du comparable est autour de 7,5. Ne pas rouvrir ces deux sujets de soi-même.

### 1. LE POINT QUE J'AVAIS ANNONCÉ N'EXISTAIT PAS

J'avais lu dans l'audit « 10 H2 en question, 4 capsules » et j'en avais conclu, devant le
client, que **six titres en question manquaient de réponse autonome**. Mesuré avant de
corriger : **12 titres en question sur les 20 pages, dont 6 appels à l'action et 6 déjà dans
la fenêtre de 40 à 60 mots. Zéro hors fenêtre.** Les « 4 capsules » de l'audit sont les 4 H2
informatifs, tous pourvus ; les 6 autres H2 sont des « Prêt à… » / « Ready to… », et la règle
du 2026-08-24 dit de **ne PAS leur écrire de capsule** (une invitation n'a pas de réponse de
cinquante mots).

Il n'y avait donc rien à faire, et c'est la même leçon que le LinkedIn « laissé ouvert » ou
que la note sur `logo-baseline.png` : **un chiffre d'audit se remesure avant d'être transformé
en tâche.** Le contrôle est dans `sonde_capsules.py` (jetable) : pour chaque titre finissant
par « ? », le paragraphe qui suit dans l'ordre du document, son compte de mots, et un drapeau
« appel à l'action » posé sur la présence d'un `.btn` dans le même bloc.

### 2. La formulation longue revient en français, une fois par page

Relevé du n°8, remesuré ici sur le texte rendu, accordéons ouverts : « 2FA » sortait **71
fois** côté français, « double authentification » **20**, et « authentification à deux
facteurs » **UNE SEULE FOIS**, repliée dans une réponse de FAQ. C'est pourtant la formulation
que tape quelqu'un qui ne connaît pas encore le produit, et c'est une conséquence non voulue
du remplacement d'« authentification forte » demandé la veille.

Cinq insertions françaises, une par page, plus une anglaise pour la parité : le chapeau du
hero (le titre garde « double authentification », le chapeau porte l'autre forme), le chapeau
de l'éditeur de scénarios, celui de la page cas d'usage, la réponse-capsule « Comment Q-Bot
automatise votre 2FA ? » et la réponse Q1 de la FAQ.

**Ce qui n'est pas touché est la moitié du travail** : aucun titre ni sous-titre repris du
WordPress n'est reformulé, les cinq phrases éditées ont toutes été écrites par ce dépôt, et
**les métadonnées ne bougent pas** (la description de l'accueil est à 152 caractères sur 158 ;
la formule longue la ferait déborder, et « double authentification » y reste un synonyme
juste).

Relevé après : **1 → 6 occurrences** sur 5 des 8 pages, « 2FA » inchangé à 71, et la capsule
de la page Démo passe de 45 à **48 mots**, donc reste dans la fenêtre. Le JSON-LD de la FAQ
suit par `sync-faq-jsonld.py` (1 entrée recalée, 0 au second passage) : sans lui, la réponse
visible et sa copie structurée auraient divergé.

### 3. Le visuel de « La solution » n'est plus une image de synthèse

Seul point ouvert du n°8, et **il ne pouvait pas être trouvé par une mesure** : le visuel
fourni le 2026-09-01 montrait une validation LuxTrust **inventée** citant MyGuichet, un
service réel de l'État, sur un site qui déclare n'avoir aucun lien avec LuxTrust.
« MyGuichet » apparaît 0 fois dans la source des 21 pages, le mot était dans les pixels.

Remplacé par une image du film (t = 23,0 s), recadrée au carré 820 x 820 : **la scène est
réelle et la validation LuxTrust l'est aussi**. Le problème disparaît par la source, pas par
une retouche. Cadrage choisi sur cinq essais rendus côte à côte ; le carré serré garde le
boîtier au premier plan, ce qui le distingue de l'image de la fiche technique, tirée du **même
instant** mais en plan large.

**UN PLAFOND DE LARGEUR ÉTAIT NÉCESSAIRE EN UNE COLONNE**, et le nombre est calculé : source
820 px, donc **410 px** est la largeur au-delà de laquelle un écran de densité 2 agrandit.
Sans lui, la colonne de 720 px d'une tablette donnait **1,76**. Sur un téléphone la colonne
fait 342 px, le plafond ne mord pas et l'image reste en pleine largeur, comme le client l'a
demandé pour la photo LuxTrust le 2026-08-26. Même arbitrage, même calcul.

### Ce qui reste, et qui n'est PAS dans ce dépôt

Quatre leviers de la dimension « autorité », tous hors du code, à faire par le client ou chez
des tiers :

- **la fiche Ministry of Testing** annonce encore « Automate the use of tokens on 100% of your
  tests », soit les deux revendications retirées du site, et pointe vers `bot.q-leap.eu`, qui
  meurt avec le WordPress ;
- **quatre pages tierces décrivent encore l'actionneur et la caméra** (portfolio du
  sous-traitant, 3dprint.lu, l'article ITnation, une page webinaire sur l'Odoo de Q-Leap).
  Ce sont elles qui alimentent les résumés des IA pendant que `q-bot.eu` est fermé, et la
  dernière est corrigeable par le client ;
- **aucun annuaire professionnel, aucun avis sur un comparateur** ;
- **le « Depuis 10 ans » de `q-leap.eu`**, qui contredit de quatre ans le `foundingDate` du
  5 avril 2012.

## Le lot de review du 2026-09-02 : plus clair, moins répétitif, plus défendable

Brief de review en 26 points, traité en six lots, un lot par commit. L'objectif
annoncé n'était pas du wording : rendre le site plus clair, plus crédible
techniquement, moins répétitif, et aligné sur un parcours (je découvre le problème,
je comprends le produit, je comprends le fonctionnement, je vérifie, je réserve).
Le message différenciant à faire ressortir : **automatiser la 2FA sans la
contourner.**

### Ce que la homepage est devenue

Ordre demandé et appliqué : hero, solution, produit (la séquence 3D), **comment ça
fonctionne**, trois avantages, cas d'usage, compatibilité, vidéo, Made in
Luxembourg, CTA final.

- **La section « Comment ça fonctionne » est neuve** : cinq étapes, le texte du
  brief mot pour mot, avec le composant à ronds numérotés de la page Démo. La
  variante à cinq colonnes redérive la formule du trait de liaison exactement
  comme celle à quatre (`20 % − 0,8 g − rond/2`), et le trait s'arrête au pixel
  sur le centre du cinquième rond.
- **Le message « sans code » y est la seconde moitié**, en quatre lignes à coche.
  Le brief le veut sur la homepage mais interdit d'y recopier la fiche technique.
- **Trois avantages, plus quatre.** Partent « Mise en service immédiate » (fausse :
  il faut construire ses scénarios) et « Deux accès ».
- **Les deux blocs « pour qui » fusionnent** en « Conçu pour les équipes QA et
  d'automatisation ». « À qui s'adresse Q-Bot ? » puis « Tous types de projets IT »
  puis « Tous types d'applications » disaient trois fois la même chose, en plus
  large à chaque fois. Ces deux derniers titres venaient du WordPress et étaient
  conservés à ce titre depuis le 2026-08-31 ; **la review autorise explicitement
  leur fusion**, c'est donc un arbitrage et non une entorse à la règle du live.
- **La section LuxTrust devient la section Compatibilité**, avec la grille
  `.compat` déjà employée sur la fiche technique. Un seul endroit fait foi.

### Les trois formulations qui n'étaient pas défendables

| Avant | Après | Pourquoi |
|---|---|---|
| « Zéro faux positif » | « Exécution déterministe » | un zéro absolu ne se démontre pas ; un appui prédéfini rejoué à l'identique se décrit |
| « Rien n'est deviné à l'image » | « sans reconnaissance visuelle de l'interface **pendant l'exécution** » | les captures servent bien à CONSTRUIRE les scénarios : la nuance est demandée, et l'ancienne phrase laissait croire l'inverse |
| « API simple et sécurisée » | l'API REST s'appelle depuis la chaîne de tests, sans SDK ni agent | **une API sans jeton n'est pas sécurisée par nature** |

**LE POINT SÉCURITÉ EST LE PLUS DÉLICAT DU LOT, et il se joue sur ce qu'on
n'écrit pas.** Les documents fournis par le client disent trois choses, et
seulement trois : auto-hébergé sur le réseau local, aucun jeton ni clé d'API
requis, aucun appel externe ni connexion internet pendant les tests. **Rien sur
l'authentification de l'API, les ACL, l'isolation réseau ou le contrôle des
appels.** La note de la page « comment ça marche » annonçait « aucun jeton
d'authentification, aucune limite de débit » comme des AVANTAGES : elle dit
maintenant « l'API n'attend aucune clé : le contrôle d'accès est celui de votre
réseau », ce qui est vrai et renvoie la question là où elle se décide. Ne pas
enrichir cette ligne sans information du client.

### La page « Cas d'usage » devient « Comment ça marche »

Elle ouvrait sur cinq cas détaillés sans avoir dit une fois ce que fait le
produit. Structure demandée et appliquée : comment ça marche (cinq étapes), dans
quels cas l'utiliser (les cinq cas, qui couvraient déjà la liste du brief), deux
modes de déclenchement.

**L'ADRESSE NE CHANGE PAS** (`cas-usage.html`, `en/use-cases.html`) : elle est citée
par le plan du site, les paires hreflang, les canoniques et les 52 relais.
Renommer le fichier coûterait tout cela pour rien. Seuls le libellé de
navigation, le titre, le h1 et la structure changent.

**Les deux modes de déclenchement ont DÉMÉNAGÉ depuis la fiche technique**, avec
leur film, et la section est placée AVANT la bande d'exemples d'API : l'API est
l'un des deux modes, elle ne peut pas être détaillée avant d'être annoncée.

### La fiche technique en est enfin une

Six catégories (Matériel, Smartphone, Interface, API, Données et réseau,
Déploiement) plus la Compatibilité, qui garde sa section parce qu'elle a des
sous-listes. La section « Un nano-ordinateur… » disparaît : sa prose et ses huit
lignes sont absorbées, catégorie par catégorie.

**Trois composants réutilisés, aucun créé** : `tools__grid`, `compat__head`,
`specs__list` / `spec-item`. Le design global n'est pas touché, comme demandé.

### Le pied de page et la navigation

Partent : la ligne newsletter (posée le matin même, retirée par ce brief),
« Conditions de vente » et « Réservation ». « Nous contacter » monte dans la
colonne Q-Bot, « Cas d'usage » vise la section `#cas`, les mentions Q-Leap
deviennent cliquables. La FAQ quitte la barre de navigation et reste au pied de
page.

**LES DEUX PAGES NE SONT PAS SUPPRIMÉES, et c'est une lecture à assumer.** Le
brief liste ces entrées sous le titre « FOOTER / NAVIGATION ». `conditions-vente/`
répond à l'adresse exacte du WordPress qu'elle remplace, ce qui préserve les liens
entrants le jour de la bascule ; `reservation.html` porte l'agenda Microsoft
Bookings que le bouton de la barre de navigation ouvre depuis les 23 pages. Les
deux restent au plan du site.

**Deux questions de FAQ ajoutées** (la clé secrète, la connexion internet) parce
que la réponse est documentée. Deux autres de la liste du brief ne sont PAS
écrites : « plusieurs équipes » et « deux tests en même temps » demandent une
information produit que personne n'a fournie.

### LE DÉFAUT LE PLUS INSTRUCTIF DU LOT : deux mots collés, et une règle CSS disparue

« 1 appelpar verrou 2FA dans la chaîne » et « 0intervention humaine, à toute
heure », signalés à la review comme des coquilles. **Ce n'en était pas.** Le
balisage est correct depuis toujours (`<b>0</b><span>intervention…</span>`) ;
c'est le bloc `.usecase__fig` qui avait été **supprimé par erreur le 2026-08-28**,
avec le CSS de l'épinglage des cas d'usage, alors que les dix paragraphes qui
l'emploient sont restés dans les deux pages. Sans mise en forme, les deux
éléments restent en ligne et se collent, à l'écran comme au copier-coller.

**Deux audits automatisés sont passés sur ces pages depuis, sans rien voir.** Ils
mesurent le contraste, les titres, les cibles tactiles, les liens : jamais si le
texte rendu **se lit**. C'est un lecteur humain qui l'a vu. Un retrait de mise en
page ne se contrôle pas sur « la page s'affiche encore ».

Et le correctif est dans la feuille de style, jamais dans le balisage : ajouter une
espace entre les deux balises masquerait le symptôme (elle est mangée par le
`display: flex` de la ligne) sans rendre au chiffre sa taille.

### Quatre pièges de spécificité et de sonde, dans le même lot

1. **`.features__grid--3` écrit seul pèse (0,1,0)**, exactement comme les deux
   requêtes média qui rabattent `.features__grid` plus bas dans le fichier : à
   poids égal l'ordre tranche, elles gagnaient, et la grille tombait à une colonne
   dès 768 px. **Un nom de classe à tirets reste UNE classe.** Sélecteur doublé.
2. **`.order-process--5` ne doit PAS être doublé**, et c'est l'inverse : à poids
   égal, l'ordre du fichier donne exactement la cascade voulue (la variante gagne
   sur la base, les requêtes gagnent sur la variante). Doubler aurait figé cinq
   colonnes sur un téléphone.
3. **Deux insertions ont atterri au mauvais endroit faute de bornes** : les
   questions de FAQ dans le bloc `Organization`, dont le JSON finit par le même
   motif que le `FAQPage` et qui vient AVANT dans la page (le document restait
   valide, il disait n'importe quoi : **un contrôle de validité JSON ne voit pas
   ce genre d'erreur**), puis les blocs visibles avant la liste, parce que le
   marqueur de fin choisi apparaissait d'abord à la fin du page-hero.
4. **`api-title` CONTIENT `pi-title`** : un contrôle de reste porte sur l'attribut
   entier, jamais sur un fragment de nom.

Et deux pièges de sonde typographique : `innerText` d'un noeud **cloné** n'est pas
mis en page, donc il rend l'indentation du source (2 355 faux positifs) ; il faut
masquer les blocs de code dans le document vivant. Et un filtre de noms propres
doit porter sur le **voisinage**, pas sur la capture, sinon « with LuxTrust » se
capture en « hLuxT » et ne ressemble à aucun nom connu.

### Ce que ce lot n'a pas fait, faute de matière

- **aucun nouveau modèle 3D ni nouvelle photo** n'existe dans le dépôt : la
  séquence 3D et les visuels restent ceux d'avant, comme le brief le demande dans
  ce cas ;
- **aucune information de sécurité API** au-delà des trois faits documentés ;
- **pas de logo « Made in Luxembourg »** : le brief demande de remplacer le
  pictogramme de lieu du pied de page par ce logo, qui n'existe nulle part dans le
  dépôt et qui est une marque déposée. Le pictogramme reste.

## Les retours du soir du 2026-09-02 : deux pages en moins, des photos, un carrousel

Suite du lot de review, à mesure que le client répondait. Six commits, un par
demande. Deux fils s'y croisent : ses instructions directes, et **quatre documents
Word** trouvés dans le même envoi que les photos, qui donnent la structure et les
textes de trois pages (`Q-Bot — À propos.docx`, `— Fonctionnement.docx`,
`— Caractéristiques techniques.docx`, `Correction FAQ.docx`).

### Les deux pages sont supprimées, et ce qui les tenait

« Oui supprime les pages Conditions de vente et Réservation. » Quatre fichiers.
Trois conséquences qu'il fallait suivre :

- **la fenêtre Microsoft Bookings est conservée**, parce qu'elle ne vivait pas
  dans la page supprimée : elle s'ouvre depuis le bouton de la barre de
  navigation, porté par des attributs `data-booking-*`. Ce bouton gardait
  `reservation.html` comme repli sans JavaScript ; il pointe désormais sur la page
  contact. **Et le motif de `maj-nav-booking.py` a dû être élargi**, sinon la
  « source unique » de l'agenda ne l'était plus : il ne reconnaissait que
  `reservation.html` et `booking.html` comme cible, et aurait annoncé « 0 bouton
  équipé » sans erreur le jour d'un changement d'agenda ;
- **les deux adresses légales ne tombent pas en 404** : `conditions-vente/`
  répondait à l'adresse exacte du WordPress, donc elles relaient vers l'accueil
  de leur langue, comme les archives du blog. La page de réservation, jamais
  publiée sur le live et jamais indexée, n'a pas de relais ;
- **deux générateurs auraient ressuscité les pages** au prochain lancement.
  `gen-reservation.py` est supprimé ; `gen-legal.py` et `fetch-legal.py` perdent
  leurs entrées « conditions de vente », avec la note qui dit où retrouver le
  texte (`tools/legal-source.json` le garde).

### Les six photos, triées

Masters dans `Documentations/assets-sources/`, copies web dans `assets/img/`,
**réencodées, ce qui retire les métadonnées du téléphone** (une photo de téléphone
peut porter des coordonnées de localisation).

| Fichier | Ce qu'elle montre | Où |
|---|---|---|
| `qbot-photo-ecran.jpg` | le boîtier, le moniteur et le téléphone affichant tous deux le fond d'écran Q-Bot | « La solution », deux accueils |
| `qleap-equipe-dev` / `-revue` / `-poste` / `-duo`, `qleap-locaux` | l'équipe et les bureaux de Bertrange | carrousel de « À propos » |

**Un cadre a dû être créé pour une photo verticale.** `.intro__image--fit` cale la
hauteur de l'image sur celle de la COLONNE DE TEXTE : juste pour une photo en
paysage, absurde pour une verticale devant un texte court. Mesuré : 298 px de
large côté français et **163 côté anglais**, où le texte est plus court. Une photo
de 163 px ne montre rien. `.intro__image--portrait` fait l'inverse : c'est
l'image qui donne la mesure, 420 px au plus, posée sur la gouttière.

### « On parle bien de smartphone dans la homepage, le but est de eyecatch »

**Cela prend le pas sur le point 12 du brief de review**, qui demandait mot pour
mot « compatible avec les applications 2FA Android ». Les deux mentions d'Android
de la homepage partent. Le périmètre reste énoncé **là où il porte un fait** : la
fiche technique (ligne « Système : Android »), la page « comment ça marche »
(ADB est l'outil d'Android) et la question 17 de la FAQ, qui répond sur iOS.
C'est l'arbitrage du 2026-09-01, repris. `llms.txt` porte déjà la mise en garde
qui va avec : ne rien inférer d'un support iOS du mot « smartphone ».

### La page « À propos » suit son document

Structure, titres et textes du docx : « Q-Bot, conçu par des experts du test
logiciel », « né d'un besoin concret », « Conçu et développé au Luxembourg »,
« Découvrez Q-Leap » (**deux** cartes, pas trois : « le visiteur se trouve déjà
sur le site Q-Bot »), un seul CTA. Sont partis « Curiosité, créativité et
analyse. », la section « Nous investissons dans les technologies
d'automatisation » et les deux « leader sur le marché luxembourgeois » (« si
l'affirmation est conservée, elle doit pouvoir être étayée »).

### Le carrousel, et pourquoi il n'avance pas tout seul

« Mets pas de photo à Q-Bot, conçu par des experts du test logiciel » puis « fais
un carrousel en dessous de Conçu et développé au Luxembourg ».

**Il fonctionne sans JavaScript** : la piste est un défilement horizontal natif
avec accrochage. Le module 21 n'ajoute que les flèches, les pastilles et leur
état. Trois décisions de mécanique, toutes prises après mesure :

1. **l'état se lit sur la position réelle de la piste**, jamais sur un compteur
   interne : le défilement peut venir du doigt, de la molette ou de la barre, et
   un index maison se désynchronise au premier de ces gestes ;
2. **une pastille = un DÉPART, et celles sans départ sont masquées.** Avec cinq
   photos et trois visibles il n'y a que trois positions au large, quatre à 900 px
   et cinq sur téléphone : le compte se déduit de la course réelle, à chaque
   redimensionnement. Le modèle « vue centrée » a été essayé et écarté, il
   décalait l'allumage d'un cran par rapport au clic ;
3. **la cible d'une pastille fait 24 x 24 px et seul son point en fait 8.** Le
   premier essai posait l'aire cliquable en `::before` : l'audit d'accessibilité
   l'a refusé, et il avait raison, **WCAG 2.5.8 mesure la boîte de la cible** et
   relevait « 8x8, marge -12 » sur les cinq.

**Il n'avance pas tout seul, à dessein.** Le client avait fait retirer les bandes
d'outils défilantes le 2026-08-20 (« les carrousels sont un peu illisibles
cognitivement ») : ce qui les rendait illisibles était le défilement automatique,
pas le motif. Un défilement automatique demanderait de surcroît un bouton de
pause (WCAG 2.2.2).

### La page unique devient une page de découverte

« Cas d'usage → Fonctionnement → Intégration → API, sections beaucoup plus
compactes, accordéons pour les exemples de code, et **surtout un CTA avant
d'arriver à la documentation**. »

L'ordre est celui-là, et le CTA est bien AVANT les exemples d'appel : le visiteur
qui veut réserver n'a plus à traverser du code pour trouver le bouton. Les cinq
blocs « le blocage / avec Q-Bot » (2 100 caractères) deviennent **quatre cartes
courtes**, au texte du document « Fonctionnement ». Les cinq exemples d'appel
deviennent des **accordéons**, avec le composant de la FAQ : aucun composant neuf,
et le module 3 apporte `hidden`, les `aria-controls` et la mesure de hauteur.

L'adresse ne change pas, l'ancre `#cas` du pied de page non plus. La bande qui
glissait latéralement quitte la page ; son CSS et ses deux entrées de script sont
gardés et annotés, comme `.timeline`.

### CINQ FOIS LE MÊME PIÈGE DANS UN SEUL LOT, ET IL FAUT LE RETENIR

Toutes mes suppressions bornées par un motif répété ont mordu trop large, et
**deux fois elles ont emporté deux sections entières** (restaurées par
`git checkout`) :

- une carte bornée en remontant à « l'ouverture d'article la plus proche » :
  `rindex` l'a trouvée deux sections plus haut ;
- une puce cherchée avec `.*?` **et** `re.S` : en DOTALL un `.*?` traverse les
  lignes ET les sections ;
- `'      </ol>'` et `'    </div>'` sont des **sous-motifs** de leurs versions
  plus indentées, donc `count()` mentait et `index()` tombait au mauvais endroit
  (trois occurrences distinctes, dont l'insertion des questions de FAQ) ;
- et deux contrôles de reste ont crié sur mes propres commentaires, qui citent à
  dessein ce qui vient d'être retiré.

**Ce qui les a tous attrapés est la même chose** : une assertion de STRUCTURE
avant d'écrire, comparant le nombre de sections et de titres de niveau 2 avant et
après. Sans elle, deux pages partaient au commit avec deux sections en moins.
Règle : on borne sur une chaîne unique ou sur un motif tempéré (`(?!\s*</?tag)`),
jamais sur un tag répété ; un motif de ligne s'écrit `[^\n]*` sans DOTALL ; une
borne d'indentation porte son saut de ligne ; et un contrôle de reste vise
l'attribut (`class="x"`), pas le mot.
## Passe ergonomie du 2026-09-03 : six défauts, tous mesurés

Passe demandée en clôture du lot de retours du 2026-09-02. Les deux audits du dépôt
(`audit-a11y.py`, `audit-visibilite.py`) donnaient **0 constat sur 17 pages, à 1440 comme à
390 px**, avant comme après. Les six défauts trouvés sont hors de leur champ : ils mesurent
le DOM et les métadonnées, pas la géométrie de lecture ni le résultat d'un clic.

### 1. AUCUNE ANCRE NE RÉSERVAIT LA PLACE DE LA BARRE

`scroll-padding-top` n'existait nulle part, et `scroll-margin-top` non plus. La barre est
collante et haute de **72 px à toutes les largeurs** (relevé de 375 à 2560 px), donc elle
occulte en permanence le haut de la zone de défilement.

Mesuré au clic, pas déduit : un clic dans l'index de la FAQ sur « Combien coûte Q-Bot ? »
amenait la question à **0 px du haut de la fenêtre**, donc entièrement derrière la barre.
Le visiteur cliquait un intitulé et atterrissait au milieu de la réponse. Même effet à
l'arrivée directe sur `cas-usage.html#cas`, que 17 pieds de page visent.

Le correctif est **une déclaration sur la zone de défilement**, dérivée d'un jeton `--nav-h`
neuf qui remplace les trois `72px` écrits en dur (hauteur de `.nav__inner`, `top` du menu
déroulant, décalage d'ancre). Pas de `scroll-margin` sur les cibles : il y a 19 questions
par langue, cinq exemples d'appel, les pas de la séquence et les sections à ancre, et une
ancre écrite plus tard n'aurait pas la règle.

**ET UNE COURSE AVEC LA RÉVÉLATION RESTAIT, VISIBLE DANS L'INDEX DE LA FAQ SEULEMENT.** Le
calage d'ancre se calcule sur la boîte VISUELLE, transformations comprises. La variante
« carte » du module 4 part de `translateY(30px)` : le navigateur croyait la question 30 px
plus bas, calait d'autant trop bas, puis la révélation la faisait remonter sous la barre.
**La signature du défaut est qu'il n'existait pas en mouvement réduit** ; c'est ce qui l'a
identifié. Le module 16 pose donc la révélation de sa cible, sans animer, avant de laisser
le navigateur caler.

Relevé après : **56 ancres cliquées sur 14 pages**, à 1440 et 390 px, toutes à 16 px sous la
barre, et le même calage en mouvement normal comme réduit.

### 2. LES PLAFONDS DE LECTURE ÉTAIENT EN PIXELS POUR UNE CIBLE EN CARACTÈRES

Le bloc « PLAFONDS DE LECTURE » de la feuille de style se donne pour cible 80 caractères par
ligne. Il ne la tenait pas, et personne ne l'avait vérifié : la valeur était écrite en
pixels, ce qui n'est juste que pour UNE taille de police.

| bloc | avant | après |
|---|---|---|
| réponse de FAQ (15 px) | 758 px, **93 car.** | 658 px, 79 car. |
| réponse de FAQ, EN | 758 px, 89 car. | 658 px, 80 car. |
| politique de confidentialité (16 px) | 780 px, **99 car.** | 629 px, 81 car. |
| politique, EN | 780 px, 98 car. | 629 px, 79 car. |

D'où le `ch`, et ce n'est pas une coquetterie d'unité : `.container > p` porte de la prose à
15 px (86 car. à 760 px) et à 17 px (77 car. à la même largeur), donc **aucune valeur en
pixels ne convient aux deux**. En `ch` le plafond suit la police.

**LES DEUX VALEURS DIFFÈRENT PARCE QUE LA PROSE DIFFÈRE** : le registre juridique a des mots
plus longs, donc moins d'espaces, donc plus de caractères pour la même largeur. À 78ch les
politiques remonteraient à 90 car. On mesure chaque contexte, on ne déduit pas l'un de
l'autre.

Sur les pages légales le plafond va au CONTENEUR et non à ses paragraphes, contrairement aux
réponses de FAQ : leurs `h2` portent un filet bas, et le poser sur les seuls paragraphes
laisserait ce filet dépasser le texte de 150 px.

`.section-subtitle` est vérifiée saine et n'a pas bougé : 600 px à 17 px donne 64 à 68 car.

**Piège de sonde à connaître** : mesurer une largeur de ligne en posant un `max-width` EN
LIGNE ne marche pas ici, le style calculé ne bouge pas (constaté même avec `!important`).
Il faut **injecter une règle** (`add_style_tag`), ce qui est de toute façon ce qu'on va
écrire dans la feuille.

### 3. LE TABLEAU D'INTÉGRATION AVAIT LAISSÉ UNE LIGNE ET UN DÉBORDEMENT

Les cinq exemples d'appel sont devenus des accordéons le 2026-09-02 et les six lignes du
tableau « L'appel, selon votre outil » ont été retirées à cette occasion. La suppression a
laissé son titre, l'ouverture de sa grille et **une** ligne, Selenium, qui redit l'accordéon
juste au-dessus.

La note finale se retrouvait donc **élément de grille** dans `.specs__list`. Large de 760 px
par son propre plafond de lecture, elle imposait sa largeur à la colonne des libellés :
**débordement horizontal de 289 px à 601 px de large, 122 px à 768 px, 30 px à 860 px**, dans
les deux langues. La page défilait latéralement sur une tablette. Et un `<div>` restait
ouvert dans `<main>` (50 ouverts pour 49 fermés).

C'est le sixième cas de la famille des cinq pièges du 2026-09-02, et **le contrôle qui
l'attrape est une assertion de STRUCTURE** (le compte des `<div>` de `<main>`), pas une
relecture.

### 4. LES FLÈCHES DU CARROUSEL NE BOUCLAIENT PAS, SON CONTENU SI

Elles se grisaient aux extrémités, convention d'un bandeau qui a un début et une fin. Celui-ci
tourne depuis le 2026-09-02 : la flèche « suivante » restait grisée six secondes devant un
carrousel qui allait avancer de lui-même. **Un contrôle ne doit pas dire indisponible ce que
le contenu fait tout seul.**

Second effet, celui qui se mesure : un bouton désactivé sort de l'ordre de tabulation, donc le
carrousel offrait **5 arrêts au clavier au départ, 6 au milieu, 5 au bout**. Sa forme changeait
sous le doigt de qui le parcourt. Après : 6 aux trois positions.

`tour()` faisait déjà exactement ce que la flèche « suivante » fait maintenant : les deux
partagent la même fonction. Au passage, « suivante » bornait sur le nombre de PHOTOS quand le
nombre de POSITIONS est plus petit (cinq photos, trois départs au large) ; ça marchait par le
clampage de la piste, donc par accident.

### 5. LA MESURE DU CHAPEAU DE PAGE ÉTAIT DÉCLARÉE PUIS ANNULÉE

`.page-hero p { max-width: 560px }` porte même un commentaire disant que la mesure de lecture
est conservée. Elle ne l'était pas : ce sélecteur pèse (0,1,1), **exactement comme
`.container > p`**, qui est écrit plus loin dans le fichier ; à poids égal l'ordre tranche.
Relevé : **745 px au lieu de 560 sur 10 pages sur 14**, jusqu'à 98 caractères par ligne sur la
politique de confidentialité anglaise. Les quatre pages qui tombaient juste le devaient à un
style en ligne ou à une autre règle.

**Quatrième occurrence de cette famille** après `.usecase__fig`, `.newsletter__legal` et
`.evo-card__link` : une propriété déclarée, puis annulée pour TOUS les éléments qu'elle vise.
La sonde qui les trouve est celle du 2026-08-26, ici étendue aux plafonds de largeur et à la
taille de police. Après : 560 px, 75 caractères au pire sur un chapeau de plus d'une ligne.

### 6. LES LISTES D'UNE RÉPONSE DE FAQ ÉTAIENT D'UN POINT PLUS GRANDES QUE SES PARAGRAPHES

Seuls les `p` recevaient les 15 px de la réponse. Dans une même réponse : **15 px et
interligne 25,5 pour le paragraphe, 16 px et 27,2 pour la liste juste en dessous.** Deux
tailles pour une seule prose, et 96 caractères par ligne au lieu de 79, puisque le plafond en
`ch` suit la police.

Le retrait est calculé et non choisi : les `ul` du site ne portent pas de puce
(`list-style: none` global), donc leur texte s'aligne sur celui du paragraphe (relevé 179 px
de part et d'autre) ; un `ol` prend 20 px de plus pour la gouttière de ses numéros.

**DEUX STYLES EN LIGNE SONT PARTIS AVEC, tous deux invisibles à la feuille de style :**

- `.faq__list` était forcée à `800px` sur les deux pages Démo quand la feuille dit 760, donc le
  même composant avait deux largeurs selon la page ;
- l'espacement entre items de liste vivait dans un style en ligne posé sur **une seule des
  deux langues** : 6 px côté français, 0 côté anglais, pour la même réponse. Il est passé dans
  la feuille, les deux langues sont identiques.

**Cinquième fois que ce dépôt se fait prendre par un style en ligne**, après les centrages de
`commandez` (2026-08-20), les vignettes de blog (2026-08-26) et les fonds clairs de
`.spec-item` (2026-07-09). Une sonde de mise en page doit lire les styles EN LIGNE, pas
seulement les règles.

### Ce qui a été mesuré et laissé tel quel

Pour ne pas le rouvrir à chaque passe :

- **les formulaires n'ont rien à corriger** : `autocomplete` juste sur les sept champs,
  `type="email"` et `type="tel"` en place ;
- **le menu déroulant est sain au clavier** : Échap le ferme, un clic dehors le ferme, le
  focus reste sur le bouton, la tabulation va du menu à la barre puis à la page. Pas de piège
  de focus, ce qui est correct pour un menu déroulant (ce n'est pas une fenêtre modale) ;
- **le rythme vertical est uniforme** : 68 écarts titre vers bloc relevés, deux valeurs
  seulement, 16 px (titre plus son chapeau, une unité de lecture) et 32 px (titre puis bloc) ;
- **aucune collision de texte** sur 11 largeurs x 9 pages, mesurée sur les rectangles réels
  des nœuds de texte et non sur les boîtes ;
- **aucun texte sous 12 px, aucun interligne sous 1,30** : la passe du 2026-08-26 tient ;
- **le motif des volets « le blocage / avec Q-Bot » est devenu du CSS mort**, et il est
  **gardé, annoté sur place**, comme `.timeline` et `.video__wrapper` : de toute la famille
  `.usecase*`, seule `.usecase__cat` subsiste dans le balisage (huit fois, sur les deux pages
  « Comment ça marche »), les cinq volets ayant laissé la place à quatre cartes courtes le
  2026-09-02. Conséquence à connaître : **le correctif du 2026-09-02 sur `.usecase__fig`
  (les deux mots collés) porte sur du balisage qui a disparu le même jour, au commit
  suivant.** Il reste juste, il ne s'applique plus à rien. Le supprimer est une décision du
  client, pas d'une passe d'ergonomie ;
- **les agrandissements d'images restants sont la limite des fichiers**. Les cinq photos du
  carrousel montent à 1,17 en densité 2 à 2560 px, et **leurs masters font 768 x 1024, comme
  ce qui est publié** : il n'y a pas plus de pixels à aller chercher. Même situation pour
  `qbot-photo-ecran.jpg`. Précédent du 2026-08-26 : on cape quand l'agrandissement dépasse
  1,5, on accepte à 1,17. **Vérifier le master avant de proposer un recadrage.**

### Sondes de cette passe

Jetables, dans le bac à sable, mais leur méthode vaut : `ergo.py` (ancres non réservées,
caractères par ligne, typo, rangées de grille, gouttière, rythme), `larg.py` (débordement et
collisions de texte sur 11 largeurs), `ancres.py` (chaque lien d'ancre cliqué pour de vrai),
`sondeA.py` (déclaré puis annulé, celle du 2026-08-26 étendue aux largeurs et aux polices),
`img.py` (agrandissement aux densités 2 et 3), `menu.py` (menu au clavier), `car2/car3.py`
(boucle et défilement automatique du carrousel).

**`sondeA.py` sort 60 lignes dont 2 vraies**, et il faut le savoir avant de la relancer : un
interligne sans unité se calcule en pixels, un `ch` ou un `clamp()` aussi, un `inline-flex`
posé sur un élément flex devient `flex` par blocification, et un `display: none` levé par une
requête média est une intention. Le tri se fait à la main. Les deux vraies étaient les
défauts 5 et 6 ci-dessus.

**ET UNE SONDE QUI OUVRE LES ACCORDÉONS EN CLIQUANT TOUS LES BOUTONS EN FERME LA MOITIÉ** : un
clic sur une question déjà ouverte la referme. Le dernier constat de mesure de lecture qui
subsistait était un `li` de boîte nulle, mesuré dans une réponse repliée. Pour ouvrir sans
refermer, il faut cliquer les seuls boutons dont `aria-expanded` vaut `false`.

**Deux d'entre elles ont d'abord menti**, et les deux raisons sont générales : une sonde de
rangées de grille signale `.tools__grid` comme irrégulière alors que son `align-items: start`
est voulu (deux colonnes de longueurs différentes, arbitrage du 2026-08-20), et une sonde de
gouttière signale chaque cellule de grille si elle ne se limite pas aux vrais en-têtes de
section.
## La 20e question de la FAQ : plusieurs demandes à la fois (2026-09-03)

Information donnée par le client, et elle referme un point laissé ouvert le 2026-09-02 : le brief
de review demandait cette question, elle n'avait pas été écrite faute de savoir ce que fait le
produit. Réponse du client : « Q-Bot les traite un à un en fonction de l'arrivée des demandes. »

La question est ajoutée aux DEUX FAQ, en **position 20**, comme les questions 18 et 19 du
2026-09-02 : on ajoute en queue plutôt qu'en milieu de liste, ce qui évite toute renumérotation
et donc toute ancre cassée. Elle ne va PAS sur `commandez` / `en/order`, qui portent quatre
questions de conversion et non la liste complète, exactement comme les deux précédentes.

Trois emplacements par langue, et en oublier un sort la question du sommaire ou des données
structurées : le bloc visible, l'index en tête de page, le `FAQPage`. **L'entrée JSON-LD est
CLONÉE de la dernière question et seules ses deux chaînes sont remplacées**, parce que les deux
langues n'indentent pas ce bloc pareil (12 espaces côté anglais, 10 côté français) : un gabarit
retapé à la main s'applique à l'une et échoue en silence sur l'autre. Contrôle :
`tools/sync-faq-jsonld.py` compare **40 entrées et n'en recale aucune**, donc le texte visible et
sa copie structurée sont identiques dans les deux langues.

Le fait ajouté est le SEUL que le client ait donné, et rien n'est extrapolé au-delà de ce que le
site publie déjà : « un appareil filaire par boîtier » vient du guide LuxTrust, donc « deux
scénarios ne s'exécutent jamais en parallèle » est une conséquence et non une invention. Réponses
de 51 mots en français et 52 en anglais, dans la fenêtre de 40 à 60 mots qui se fait citer.
`llms.txt` porte le même fait avec sa mise en garde : ne pas décrire Q-Bot comme exécutant des
scénarios en parallèle, ne pas inférer un nombre de sessions simultanées.

**Et le commentaire de l'index ne compte plus les questions.** Il annonçait « dix-sept » alors que
la page en portait 19 : le décompte a valu 16, puis 17, puis 19, puis 20, et il a déjà fallu le
corriger une fois (chantier 06 de l'audit de contrôle n°2). Il est reformulé sans nombre, donc il
ne peut plus périmer.
