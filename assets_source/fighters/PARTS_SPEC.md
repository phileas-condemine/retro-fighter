# Image specification — v2 cutout parts (ChatGPT/DALL-E)

What `blender/pipeline.py` expects on disk, generated from
`blender/parts_spec.py` (the actual source of truth the pipeline reads —
if the two ever disagree, trust the code). Deliver these as **separate PNG
files**, not a single contact sheet — a sheet is fine as an intermediate
step if that's how your generation tool works, but each part needs to end
up as its own transparent, cleanly-cropped file before it's usable.

## Where files go

```text
assets_source/fighters/rose_kunoichi_v2/parts/<part_name>.png
assets_source/fighters/shinobi_v2/parts/<part_name>.png
```

Exact filenames matter — `blender/pipeline.py` looks for them by name (see
the table below). A reference sheet (whole-character, for your own visual
consistency while generating parts, not consumed by the pipeline) goes in
`references/` next to `parts/`.

## Global constraints (every part, both characters)

- **Transparent background.** No ground, no shadow, no scene.
- **Character facing right.** Every part drawn as it appears when the
  character faces the right edge of the screen (the game mirrors the whole
  sprite horizontally for the other facing — see `assets/fighters/CONTRACT.md`
  — so never draw a left-facing variant).
- **Consistent art style and proportions across every part of one
  character.** They'll be recomposited into one body — a torso and an arm
  drawn at even slightly different stylization/scale will look wrong
  glued together.
- **"Front" vs "back" = near/far from camera, not anatomical left/right.**
  In a side-on 2D fighter, "front arm/leg" is the one closer to the
  viewer (drawn slightly larger/lower in the stack), "back" is the far one
  (partially behind the torso). This matches how the existing LD/HD packs
  are already organized.
- **Minimal overlapping fabric/hair across joints.** The current HD
  reference art (`assets/fighters/hd/*/frames/idle_000.png`) has flowing
  sashes and hair crossing over multiple body parts, which look great as a
  single image but can't be cut into independent limb pieces. For cutout
  parts specifically: keep loose cloth/hair *within* the part it belongs to
  (e.g. the sash lives entirely on the `accessory_main` piece, doesn't
  drape across the torso or thigh pieces too).
- **Resolution**: generate large (1024px+ tall) and let it be downscaled —
  working at higher resolution than the 256px final output gives cleaner
  edges after compositing.
- **No drop shadow, no outline glow, no background gradient baked into the
  part** — the game draws its own ground shadow.

## Character style (keep consistent with the existing packs — see
`assets/fighters/ld/*/PACK_README.md` and the HD reference frames)

**Rose Kunoichi** (`rose_kunoichi_v2`): adult kunoichi, pink/rose hair in a
high ponytail with a couple of loose strands framing the face, fair skin.
Black and dark-purple fitted combat outfit (long-sleeve tunic/jacket,
wrapped sleeve detail), pink sash tied at the waist trailing to one side,
dark fitted trousers, black knee-high boots with pink/magenta trim, black
arm wraps. Sword hilt visible at the hip is optional (skip it if it
complicates the pelvis/thigh split — it's not used by the game). Palette:
black + dark purple base, pink/magenta accents (hair, sash, trim).

**Shinobi** (`shinobi_v2`): **locked from a real reference image** (this
replaces an earlier "white-haired" guess made before any reference
existed) — see `shinobi_v2/references/reference_full.png` and
`shinobi_v2/PARTS_PROMPTS.md` for exact per-part prompts already written
against it. Black spiky messy hair, black lower-face mask/scarf, tan bare
skin on shoulders/upper arms, black segmented armor with gold/bronze trim,
brown leather chest bandolier and waist utility belt with pouches +
shuriken charm, purple waist sash with tattered trailing ends, black
tattered hakama-style pants, black armored greaves with gold chevron trim,
open ninja sandals with bare tan toes.

## Parts list

Phase 1 = needed now (idle/walk/punch_mid vertical slice). Phase 2 = add
later, once phase 1 renders correctly in-game — don't block on these.

| File | Phase | Description |
|---|---|---|
| `hair_back.png` | 1 | Back half of the hairstyle, behind the head/torso silhouette. |
| `upper_arm_back.png` | 1 | Upper arm (shoulder to elbow), far arm. |
| `forearm_back.png` | 1 | Forearm (elbow to wrist), far arm. |
| `hand_back.png` | 1 | Hand, far arm, relaxed/open — no fist variant needed yet. |
| `thigh_back.png` | 1 | Thigh (hip to knee), far leg. |
| `shin_back.png` | 1 | Shin (knee to ankle), far leg. |
| `boot_back.png` | 1 | Boot/foot, far leg. |
| `pelvis.png` | 1 | Hips/waist, belt line. The sash/scarf anchors here but is its own separate piece. |
| `accessory_main.png` | 1 | The character's signature trailing cloth (Rose: pink sash; Shinobi: dark green scarf), hanging from the waist, as its own isolated piece. |
| `torso.png` | 1 | Chest/torso including neck — the main body silhouette. |
| `thigh_front.png` | 1 | Thigh (hip to knee), near leg. |
| `shin_front.png` | 1 | Shin (knee to ankle), near leg. |
| `boot_front.png` | 1 | Boot/foot, near leg. |
| `head.png` | 1 | Head and face, **no hair** (hair is separate front/back pieces). |
| `hair_front.png` | 1 | Front half of the hairstyle, over the forehead/face edges. |
| `upper_arm_front.png` | 1 | Upper arm (shoulder to elbow), near arm. |
| `forearm_front.png` | 1 | Forearm (elbow to wrist), near arm. |
| `hand_front_open.png` | 1 | Hand, near arm, relaxed/open (idle, walk). |
| `hand_front_fist.png` | 1 | Hand, near arm, closed fist (punches). Same wrist angle/scale as `hand_front_open` — the pipeline swaps between them, they must line up. |
| `hand_back_fist.png` | 2 | Hand, far arm, closed fist. |
| `hair_strand_front.png` | 2 | A loose strand of hair for idle secondary motion. |
| `hair_strand_back.png` | 2 | A second loose strand, behind the silhouette. |

19 phase-1 files per character (38 total for both). Each limb piece
(`*_front`/`*_back` arms and legs) should have a little extra length beyond
the visible joint on both ends — the rig overlaps adjacent parts slightly
to hide the seam, so a part cropped exactly to its "logical" segment will
show gaps once posed.

## Ready-to-paste prompts

Generate one reference sheet first (for your own consistency check), then
the parts — in a couple of batches if your tool limits how much it puts in
one image; splitting by body region (head/torso, arms, legs) tends to work
better than requesting all 19 at once.

### Reference sheet (once per character)

```text
Create a clean 2D game character reference image for [Rose Kunoichi / a
shinobi ninja], side view facing right, full body visible, transparent
background, no shadow, no text, no duplicate poses. [insert the character
style paragraph above]. Athletic neutral fighting stance: torso upright,
arms slightly away from the body, legs comfortably apart, feet flat,
readable silhouette, illustrated game-sprite style with clean line work,
consistent proportions suitable for cutting into separate body-part pieces
for animation rigging.
```

### Parts sheet (repeat per body region if needed)

```text
Create isolated cutout body parts for the exact same character as this
reference [attach reference sheet], transparent background, no shadow, no
text, no outline glow. Each part on its own, clearly separated, same
scale and art style as the reference. Parts needed: [list the phase-1
filenames relevant to this batch, using the plain description column
above instead of the filename]. Front = the side closer to the viewer,
back = the far side, partially hidden behind the torso in the reference
pose. Keep hair and cloth accessories contained within their own piece,
not draped across neighboring body parts.
```

Crop/clean each generated part down to its own transparent PNG before
dropping it into `parts/` — this is expected manual cleanup, not something
the pipeline does for you.
