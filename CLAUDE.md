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
assets/js/main.js           ← Single script: nav, FAQ accordion, scroll reveal, counters, back-to-top, 3D viewer controls
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

**JS architecture** (main.js, 6 independent modules in one file):
1. Nav sticky shadow + mobile toggle (hamburger → X via `aria-expanded` CSS selector)
2. Active nav link detection (pathname-based)
3. FAQ accordion with dynamic `scrollHeight` (no hardcoded max-height)
4. Scroll reveal: `.reveal` class added by JS → `.is-visible` via `IntersectionObserver`; double-RAF prevents FOUC; stagger via `--stagger-i` CSS custom property
5. Stats counter: `IntersectionObserver` + `requestAnimationFrame` on `[data-count]` elements
6. Back-to-top FAB (injected by JS)

## Reference site

**https://q-bot.eu/** is always the source of truth.

Before any modification:
1. Compare the local page against the live WordPress page.
2. Identify visual and behavioural differences.
3. Document the gaps.
4. Fix the gaps — never the other way around.

**Never reword marketing copy.** Titles, subtitles, body text and button labels must match the original word for word.

## Animation rules

- Prefer native CSS animations and transitions.
- Use GSAP only when CSS cannot achieve the required effect.
- Never remove an animation to simplify code.

Target behaviours to preserve:
- Hero: sequential `fadeInUp` entrance (label → title → desc → CTAs → image), then continuous `float` on the product image.
- Page hero (sub-pages): `fadeInUp` entrance on label, h1, p.
- Scroll reveal: `.reveal` → `.is-visible` with per-sibling stagger (`--stagger-i`, capped at 5).
- FAQ accordion: smooth `max-height` transition driven by `scrollHeight`.
- Mobile nav: hamburger animates to X; menu slides down (`menuSlideDown` keyframe).
- `prefers-reduced-motion` media query disables all animations.

## Known placeholders to replace

| File | Placeholder | What to replace with |
|------|-------------|----------------------|
| `index.html`, `en/index.html` | `VIDEO_ID` in YouTube `<iframe>` | Actual YouTube video ID |
| `index.html`, `en/index.html`, newsletter `<form>` | Static `<form action="#">` | Sendinblue/Brevo embed code |

## SEO/GEO/UX audit (2026-07-09)

A full pass against the live site turned up several real bugs, not just stylistic gaps — fixed directly rather than just documented:

- **Sitewide broken logo**: `assets/img/logo.png` (128×150) was only ever a tiny cropped icon fragment (confirmed against the live site's own asset library) but was squished into a 120×40/110×36 wordmark slot in every page's nav + footer + JSON-LD `Organization.logo` — rendered as a barely-visible sliver. Replaced everywhere with `assets/img/logo-baseline.png` (300×128, byte-identical to the live site's actual footer logo asset), at the correct aspect ratio. Also fixed `.nav__logo img` CSS (`height: 80px` inside a `72px`-tall `.nav__inner` — logo was overflowing its own bar, just never noticed because it was invisible).
- **a-propos.html**: `logo-qleap.png`, `logo-qguard.png`, `products-lineup.jpg` were referenced but never existed (permanent broken-image icons) — downloaded the real assets from the live WordPress media library and wired them in, with `object-fit: contain` added to `.product-card__icon` (was hard-cropping/squishing wide logos into a 48×48 square). `qleap-office.jpg` turned out to reference an image that doesn't exist on the live page at all (that section is text-only there) — removed the image slot rather than substitute an unrelated stock photo. "Découvrir Q-Guard" (`href="#"`) → `https://q-guard.app/`; the Q-BOT product card's own CTA now points to the real `https://calendly.com/q-bot/30min` used live (was `contact.html`).
- **Wrong social links sitewide**: footer icons + every page's JSON-LD `sameAs` had invented/outdated handles (`facebook.com/qleap.lu`, `twitter.com/qleap_lu`) instead of the live site's real ones (`facebook.com/QLeapSa`, `twitter.com/qleap_sa`).
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
