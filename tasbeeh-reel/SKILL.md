---
name: tasbeeh-reel
description: Create polished Arabic-English Islamic Tasbeeh counter Instagram Reels with animated prayer beads, customizable Dhikr, adjustable repetition speed, a royal (queenly) colour palette with a simple illustrated background chosen at random on every run (mosque, lantern, Quran with beads, geometric star), optional background images, audio taken from the reference reels, synchronized to every count, and a library of four reference reels (references/) that set the design quality bar. Use whenever the user asks for a tasbeeh, dhikr, zikr, SubhanAllah, Alhamdulillah, istighfar or prayer-bead counter video, reel, short or story, and when the user says to make it like the reference reels or asks for a better design, ending or motion.
---

# /tasbeeh-reel

Create a complete vertical Instagram Reel showing an animated Tasbeeh counter.

## Default creative specification

- Format: vertical Instagram Reel, 1080 × 1920, H.264 MP4.
- Visual style: elegant animated Tasbeeh beads on a royal background (deep purple, burgundy, royal blue, midnight violet or amethyst) with warm gold accents, a thin gold double border, and soft glow.
- Background: simple and different on every run. The renderer randomly picks one royal palette and one illustrated scene (see "Royal backgrounds").
- Language: Arabic plus English translation or transliteration.
- Default Dhikr: `سُبْحَانَ اللَّهِ` — `Glory be to Allah`.
- Default target: 33 repetitions (the traditional Tasbeeh count). Use `--target` for anything else.
- Default repetition interval: 1 second.
- Default duration: calculated automatically (33 seconds at 1 s per count).
- Default frame rate: 30 FPS.
- Show a clear repetition count and progress indicator.
- Default audio: `sounds/reference-click.mp3` (the click sound from reference reel 3), with one click synchronized to every count.
- Default audio volume: 65%.
- Use a calm, respectful presentation.
- Include an end card showing the completed count and `Alhamdulillah`.

## Customization

Every run can use different Dhikr text, count, repetition speed, background, and sound.

### Pick a dhikr from the library

`references/ADHKAR.md` holds the seven recommended adhkar (Arabic, transliteration, meaning) supplied by the user. Pick one with `--dhikr`; it fills the Arabic, a transliteration line and the meaning:

```bash
--dhikr 5                 # number 1-7
--dhikr istighfar         # or a name: subhanallah, alhamdulillah, akbar, tahlil, istighfar, bihamdihi, hawqala
```

When the user names one of these adhkar, or asks for "the list" or "all seven", use `--dhikr` instead of retyping the text. For a set of several reels, render one per number. `--arabic`, `--translation` and `--transliteration` override the library. With no dhikr options the default is number 1, SubhanAllah. Anything not in the library is typed by the user, exactly as given.

### Change the Dhikr

Use:

```bash
--arabic "الْحَمْدُ لِلَّهِ"
--translation "Alhamdulillah"
--transliteration "Alhamdulillah"   # optional extra line
```

Preserve the exact Arabic and English wording supplied by the user.

### Animated rain-on-flower reel

```bash
--scene rain-flower        # or --background "rain flower"
```

Rain falls continuously; on every count one drop lands on the flower with a ripple and a soft glow, and the flower grows and opens as the count rises (full bloom at the target). The count is shown in a ring that fills. Works with any palette, `--verse`, and the synced click sound. Not used by random runs; ask for it by name.

### Add a verse at the bottom

Optional. Shows a gold Arabic verse with a source line under the progress bar on every frame:

```bash
--verse "«وَاسْتَغْفِرُوا اللَّهَ إِنَّ اللَّهَ غَفُورٌ رَحِيمٌ»" \
--verse-source "[البقرة:199]"
```

Use only text and source the user supplied (or that you can clearly source). Use « » as quote marks, because the Quran brackets ﴿ ﴾ are missing from the fonts and draw as empty boxes. Long verses shrink to fit one line. With a verse, `ALHAMDULILLAH` after the last count moves slightly lower.

### Change the count

Use:

```bash
--target 33
```

The default is 33 repetitions.

### Adjust repetition speed

Use `--count-interval` to control the time between repetitions.

```bash
--count-interval 1.5
```

Examples:

| Interval | Target | Video duration |
|---|---:|---:|
| 0.5 seconds | 33 | 16.5 seconds |
| 1 second | 33 | 33 seconds |
| 1.4 seconds | 33 | 46.2 seconds |
| 1.5 seconds | 33 | 49.5 seconds |
| 2 seconds | 33 | 66 seconds |

The total video duration is calculated automatically:

`duration = target × count-interval`

The interval must be greater than zero.

Do not use `--duration`. The renderer calculates the duration from the target and repetition interval.

### Royal backgrounds (random on every run)

Every execution picks a **new random look** unless told otherwise: one royal palette plus one simple illustrated scene. The scenes are original vector-style motifs drawn in code, inspired by classic Islamic illustration. They are kept low-contrast so the beads, count and Dhikr stay readable.

| Palette | Mood |
|---|---|
| `royal-purple` | Deep imperial purple with gold |
| `burgundy` | Rich crimson/wine with gold |
| `royal-blue` | Sapphire blue with gold |
| `midnight-violet` | Dark violet night with gold |
| `amethyst` | Lighter plum/magenta with gold |

| Scene | What it shows |
|---|---|
| `mosque` | Mosque skyline silhouette with domes and minarets, crescent moon |
| `lantern` | Two gold Ramadan lanterns hanging from the top |
| `quran` | Open Quran on a folding stand with prayer beads, one hanging lantern |
| `star` | Large eight-pointed geometric star, crescent, row of small stars |
| `rain-flower` | **Animated, opt-in** (never picked at random): clouds, falling rain, a flower that grows and opens with the count, a drop that lands on it at every count with ripples, and a ring counter instead of the beads |

All scenes share a faint geometric star behind the counter, tiny stars, and a thin gold border.

Default (random palette and scene):

```bash
python scripts/render.py
```

Choose explicitly:

```bash
--palette royal-purple
--scene mosque
```

Or steer with natural language; keywords pick the palette and/or scene and anything unspecified stays random:

```bash
--background "purple mosque"
--background "blue lantern"
--background "burgundy quran"
```

Every run prints its choice, for example `Background: palette=royal-blue, scene=mosque, seed=48213907`. Report this to the user. To recreate the same look later, or to keep a look they liked, pass the seed:

```bash
--seed 48213907
```

Preview a look quickly without rendering a video (saves one PNG and exits):

```bash
python scripts/render.py --preview look.png
```

When the user does not ask for a particular background, let the renderer choose at random; do not pin a palette or scene "to be safe", because variety on each execution is the intended behaviour. When they ask for a different colour that is not royal (for example green), explain that the skill uses royal palettes and offer `--background-image` for anything else.

Exact custom scene: supply an image.

```bash
--background-image "/path/to/background.png"
```

A supplied image takes priority over the random scenes. A random royal palette is still used for the text and bead colours, so choose `--palette` to match the image if needed.

### Change the sound

Default:

```bash
--sound sounds/reference-click.mp3
```

Use another MP3:

```bash
--sound "/path/to/another-effect.mp3"
```

Disable audio:

```bash
--no-audio
```

Adjust volume:

```bash
--volume 0.4
```

The default volume is 0.65.

### Sound is synchronized with the counter

By default (`--sound-mode sync`) the sound follows the counter: one bead click plays on the exact frame where the number changes, for every repetition, at any `--count-interval`. The bundled `sounds/reference-click.mp3` is the audio of reference reel 3 (clicks over a quiet bed), so the renderer filters out the bed, cuts the clicks out of the file, and places one on each count. The old `counter-sound.mp3` has been removed. A custom MP3 works the same way:

- A long file with clear clicks: the clicks are cut out and used in turn.
- A short file (1.5 seconds or less): used whole as the click for every count.
- A long file with no clear clicks: a soft built-in bead tick is used instead, and the renderer prints a note.

`--volume` applies to the clicks. In a test render, every click landed within 2 ms of its count (the first click at time zero is about one frame late).

To play the MP3 as one continuous soundtrack instead, which is not tied to the counter and is looped or trimmed to the video length, use:

```bash
--sound-mode loop
```

## Reference reels (design quality bar)

`references/` holds four finished Tasbeeh reels the user collected as examples of the quality they want: a glass jar that fills with gold beads, a burning landscape that turns into a forest, a gold rosary loop with a tassel, and a night mosque skyline with a moving red bead and "+1" pops. They are compressed copies in `references/videos/`, with keyframe sheets in `references/frames/`.

Read `references/STYLE-GUIDE.md` (short) when:

- the user says "like the references", "as in my examples", or asks for a more polished design, a better ending card, more motion, or a hero visual that changes with the count;
- you are changing the renderer's visuals or adding a feature;
- you need to explain what the references do that the renderer does not do yet (the guide has a comparison table).

Do not read it, or watch any video, for a plain "make me a reel" request; the renderer's normal behaviour is enough. When you do need to look, view the keyframe sheets in `references/frames/` first and open a video file only if a sheet cannot answer the question.

Rules that matter:

- The references are for inspiration. Do not copy their artwork, logos, wordmarks or creators' handles, and never put another creator's name on a new Reel. Use a credit line only if the user gives you the text.
- Ending cards with a hadith or Quran verse need text and source from the user, or text you can clearly source and show with its reference. Never invent, paraphrase or misattribute religious text.
- The current renderer does not yet reproduce the references' signature elements (ring counter, transliteration line, progress-driven hero object, "+1" pop, hook text, ending card). If the user wants one, say it is not built yet, then add it to `scripts/render.py` as an optional flag, test it with `--preview`, and document it here, rather than approximating it silently.

## Example commands

### Default Reel

```bash
python scripts/render.py
```

### Custom Dhikr

```bash
python scripts/render.py \
  --arabic "الْحَمْدُ لِلَّهِ" \
  --translation "Alhamdulillah"
```

### Slow Tasbeeh

```bash
python scripts/render.py \
  --target 100 \
  --count-interval 1.5
```

Produces a 150-second video (100 counts).

### Very slow Tasbeeh

```bash
python scripts/render.py \
  --target 100 \
  --count-interval 2
```

Produces a 200-second video (100 counts).

### Custom Dhikr with a chosen royal look

```bash
python scripts/render.py \
  --arabic "اللَّهُ أَكْبَرُ" \
  --translation "Allahu Akbar" \
  --target 100 \
  --count-interval 1.5 \
  --background "royal blue lantern"
```

### Custom Dhikr, palette, scene, speed, and sound

```bash
python scripts/render.py \
  --arabic "سُبْحَانَ اللَّهِ" \
  --translation "SubhanAllah" \
  --target 100 \
  --count-interval 1.5 \
  --palette royal-purple --scene mosque \
  --sound sounds/reference-click.mp3 \
  --volume 0.65 \
  --output tasbeeh-reel.mp4
```

### Use an uploaded background image and another MP3

```bash
python scripts/render.py \
  --arabic "الْحَمْدُ لِلَّهِ" \
  --translation "Alhamdulillah" \
  --target 100 \
  --count-interval 1.4 \
  --background-image "/path/to/my-background.png" \
  --sound "/path/to/my-sound.mp3" \
  --output tasbeeh-reel.mp4
```

## Rendering workflow

1. Check that Python 3, Pillow, and FFmpeg are available.
2. Install Pillow if needed:

   ```bash
   python -m pip install Pillow
   ```

3. Ensure FFmpeg is installed and available in PATH.
4. Ensure `sounds/reference-click.mp3` is available in the skill directory, unless another audio file is specified. Sound is synchronized to the counter by default; use `--sound-mode loop` only if the user asks for a continuous soundtrack.
5. Determine the requested Dhikr, target count, repetition interval, background preferences (palette/scene only if the user asked), and audio settings.
6. Calculate the expected duration as `target × count-interval`.
7. Run `scripts/render.py` with the appropriate arguments.
8. Verify that the MP4 exists and is non-empty.
9. If the user asked for the reference look, apply the guidance from `references/STYLE-GUIDE.md` and tell them which reference elements the renderer can and cannot do yet.
10. Report the exact output path, repetition interval, target count, video duration, and the palette, scene and seed the renderer printed.

## Rendering notes

- `scripts/render.py` draws frames with Pillow and encodes them using FFmpeg.
- The default target is 33 repetitions.
- The default interval is 1 second per repetition.
- Video duration is automatically calculated from the target and interval.
- The counter advances according to elapsed video time.
- The active bead advances with the count.
- Arabic text uses a system Arabic font when available.
- Backgrounds are drawn with Pillow: a vertical royal gradient, a soft glow, a gold border, tiny stars, then one scene motif. A fresh random palette and scene is chosen each run; the seed is printed so a look can be repeated.
- Skyline and Quran scenes are dark silhouettes kept below the progress bar, so the gold completion text stays readable.
- Audio is built as a click track exactly as long as the video: one click per count, placed on the frame where the count changes (FFmpeg decodes the MP3; the mixing is plain Python). `--sound-mode loop` restores the old continuous soundtrack.
- Never claim that an MP4 was successfully rendered unless the output file was verified.
- Do not add unrequested religious quotations or copyrighted music.
