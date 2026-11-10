# Reference reels: style guide

Four finished Tasbeeh reels collected by the user as the quality bar for new Reels. They are 9:16, 2 to 2.7 minutes long, and each counts to 100 (the skill's default is now 33). The files here are compressed copies (432×768) kept for design study.

**Use them for inspiration only.** Learn the layout, pacing and ideas. Do not copy their artwork, characters, logos, wordmarks or the creators' handles (each video carries someone else's branding), and do not put another creator's name on a new Reel. Build original visuals in the same spirit.

## Contents

- Quick index
- What all four share (the pattern to aim for)
- Per-reference notes
- Pacing and sound
- Gap between the references and `scripts/render.py`
- Rules for using them

## Quick index

| # | Video | Look | Hero object that shows progress | Ending |
|---|---|---|---|---|
| 1 | `videos/ref-1-glass-jar-fills-with-beads.mp4` (161 s) | Deep emerald, gold | Glass jar under a hanging lamp cap; a gold bead drops in for each count and the pile grows | Hadith card: gold Arabic, English translation, source line |
| 2 | `videos/ref-2-fire-to-forest-story.mp4` (119 s) | Dusk, orange to green | Burning hills turn into a green forest with a river as the count rises | Short Quran verse, then an app promo (do not copy the promo) |
| 3 | `videos/ref-3-rosary-loop-with-tassel.mp4` (144 s) | Dark teal, gold | A closed rosary loop with a tassel; beads light up around the loop | Number turns gold at 100 |
| 4 | `videos/ref-4-night-mosque-bead-string.mp4` (142 s) | Night blue, red accent | A wavy string of beads with one red bead that moves; "+1" pops with a ripple | Ring completes in red at 100 |

Keyframe sheets (7 frames across each video, left to right in time): `frames/ref-N-...-keyframes.jpg`. `frames/end-cards-hook-and-plus-one.jpg` shows the hook text, end cards and the "+1" pop at full size. Look at a sheet when you need the exact feel of one reference; the table above is enough otherwise.

## What all four share

1. **One hero object tells the progress story.** The picture changes with the count (a jar fills, a forest grows, beads light up). The number is never the only feedback.
2. **A very clear count.** Big number with "/100" or "of 100" (reference 3 also writes it in Arabic-Indic digits: ١٢ من ١٠٠). In 1, 2 and 4 a thin ring around the number fills as the count rises.
3. **Typographic stack:** large Arabic dhikr (top third, or inside the rosary loop in 3), then a transliteration line, then the English meaning in smaller, lighter type. Arabic is the largest and brightest element.
4. **Calm, restricted palette:** dark background, one warm accent (gold or orange-red), soft glow. No busy clutter around the text.
5. **Quiet motion:** small, smooth changes on each count. Nothing flashes or shakes.
6. **A designed ending.** Either a card with a hadith or verse plus its source (1, 2) or a clear "complete" state at 100: gold number (3) or finished red ring with a ripple (4).
7. **Small credit line** near the top or bottom edge, low contrast, never competing with the dhikr.

## Per-reference notes

**1: glass jar.** Emerald gradient with a faint dome outline and tiny stars. Title block at the top (Arabic, transliteration, English). Ring counter below it. Gold beads fall one at a time into the jar and settle in a pyramid; a soft glow brightens near the pile. At the end the jar dims and a hadith card fades in: small honorific line, three lines of gold Arabic, English quote in italic serif, source line in small caps ("Sahih al-Bukhari 6405").

**2: fire to forest.** Opens with a hook line over the dark scene ("One drop of water for every Astaghfirullah."). The count starts after the hook. A bead arc crosses the scene; as the count rises the flames go out, trees and a river appear, and the sky goes from ember red to dawn. Ends on a Quran verse, then a product promo (skip the promo).

**3: rosary loop.** Cleanest layout. A closed gold rosary with a tassel frames the text: Arabic dhikr, transliteration, big serif number, Arabic count line. A glowing bead travels around the loop. At 0 the text is dim; at 100 the number turns gold. Handle at the top in small type.

**4: night mosque.** Star field, crescent moon, mosque skyline silhouette along the bottom with a palm and minarets, soft teal glow behind the skyline. Arabic dhikr in the upper third. A wavy string of silver beads crosses the middle; one red bead marks the current count and each count pops a small "+1" with expanding ring ripples. The ring counter sits on the skyline.

## Pacing and sound

Measured from the files:

| Ref | Seconds per count | Audio |
|---|---|---|
| 1 | about 1.5 | ambient bed with irregular soft transients |
| 2 | about 1.0 (after a roughly 3 s hook) | ambience and effects, irregular |
| 3 | 1.4, exact | a single click on every count, perfectly regular |
| 4 | about 1.4 | ambient bed with irregular transients |

So 1.4 to 1.5 seconds per count is the typical calm pace, which is what `--count-interval 1.5` gives. The default sound is now reference 3's own audio (`sounds/reference-click.mp3`), placed one click per count by `--sound-mode sync`. Total length is roughly 100 counts × 1.4 to 1.5 s, plus a few seconds for the ending.

## Gap between the references and `scripts/render.py`

The renderer draws one gold bead circle, a centre counter, the dhikr and a progress bar over a royal gradient with one illustrated scene. Things the references do that it does not do yet:

| Idea | In reference | In renderer |
|---|---|---|
| Ring that fills around the number | 1, 2, 4 | Only in `--scene rain-flower` |
| Transliteration line | 1, 2, 3 | Yes: `--dhikr` or `--transliteration` |
| Hero object that changes with progress (jar, forest, light) | all | Only `--scene rain-flower` (flower opens as drops land); other scenes light up beads |
| Moving highlighted bead with "+1" pop and ripple | 4 | No |
| Hook text before the count starts | 2 | No |
| Ending card with hadith or verse and source | 1, 2 | No (only "ALHAMDULILLAH" after 100) |
| Small credit or handle line | 1, 3, 4 | No |
| Arabic-Indic count line (١٢ من ١٠٠) | 3 | No |

When the user asks for one of these, add it to `scripts/render.py` as an optional flag with a sensible default (use the skill-creator workflow, test with `--preview`), and update `SKILL.md`. Do not add them silently to every Reel.

## Rules for using them

- Consult this guide when the user says "like the references", asks for a new design idea, a better ending, or more motion, or when you are changing the renderer's visuals. For a plain "make me a reel" request, the existing renderer behaviour is enough; do not watch the videos.
- Watching: look at the keyframe sheets first. Only open a video file if a sheet does not answer the question.
- Hadith and Quran text on an ending card must come from the user, or be clearly sourced and checked, and shown with its reference. Never invent, paraphrase or misattribute religious text. When unsure, leave the card out and say so.
- Do not copy another creator's handle or brand. If the user wants a credit line, use the text they give you.
