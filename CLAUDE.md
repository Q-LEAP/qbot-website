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
  **Ce n'est pas une capture du produit** : c'est un schéma, à remplacer dès qu'une vraie capture
  existe. Dessinée à la taille réelle d'affichage (600 px) puis capturée en DPR 2 — une première
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
3. Le visuel « Interface & API » est une **maquette**, pas une capture du produit — à remplacer
   dès qu'une vraie capture existe.
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

**Ce qui n'est PAS traité** : le conteneur reste plafonné à 1180 px, donc à 2560 il y a 690 px de
marge de chaque côté. L'élargir est une décision de charte qui toucherait les 23 pages ; à
arbitrer avec le client.

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

### Le bandeau de références est écrit, et volontairement inactif

Les sept références (Cargolux, POST Luxembourg, CFL, LuxairGroup, Ekonoo, LuxairTours, Alac)
sont publiques sur `q-leap.eu/references/` et n'apparaissaient nulle part ici : c'est le levier
le plus fort de la dimension « Autorité et marque » (5,5/10). **Le client a demandé de le
préparer sans le publier**, l'accord des clients nommés n'étant pas encore obtenu. Le balisage
est donc dans les deux accueils, **entouré d'un commentaire HTML**, et `.trust-strip` est déjà
dans `style.css`. Pour l'activer : retirer la ligne d'ouverture et celle de fermeture. Vérifié :
0 `.trust-strip` rendu, « Cargolux » absent de `document.body.innerText`, un seul `h1`.

Deux choses à ne pas changer en l'activant :

- **la formulation est « Q-Leap accompagne les équipes qualité de… », PAS « ils utilisent
  Q-Bot ».** Ce sont les clients de Q-Leap. La première phrase est exacte et défendable, la
  seconde ne le serait pas, et c'est cette exactitude qui la rend citable plutôt que suspecte ;
- **les noms sont du TEXTE, pas des logos.** Un nom dans une image est invisible pour un moteur
  comme pour une IA, et c'est la lecture par les machines qui est l'objet du bandeau.

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
- **le courage de dire quand le concurrent gagne.** C'est la section « Dans quels cas un robot
  n'est pas la bonne réponse », qui envoie le lecteur vers une bibliothèque TOTP gratuite pour
  Google et Microsoft Authenticator. Ce n'est pas de la modestie : une comparaison qui gagne sur
  tous les critères n'est crue par personne, ni par un acheteur ni par un modèle. C'est aussi
  l'arbitrage de contenu de l'audit, qui demande d'arrêter de mettre ces deux applications en
  avant comme argument principal, la valeur étant maximale là où il n'existe aucune clé à
  récupérer.

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
