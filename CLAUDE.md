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
`--tl-p` stayed 0 and the trait was simply absent). `PROGRESS` no longer matches anything on any
page — `.timeline` is used by none — but it is kept as the code path for a scrubbed progression.

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
`.timeline` reste dans la feuille de style et dans `PROGRESS` comme chemin de code, mais aucune
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
