# Rose Kunoichi v2 — per-part prompts

**Correction learned during Batch A generation:** asking ChatGPT's image tool
for a "transparent background" does NOT produce real alpha transparency —
it bakes a literal gray/white checkerboard pattern into the opaque RGB
pixels instead (confirmed by inspecting the downloaded PNG: `RGB`, no `A`
channel, and the checker pattern is visible when the file is opened outside
the ChatGPT UI). This is the exact same failure mode
`HOW_TO_GENERATE_IMAGES.md` already solved for whole-animation boards: ask
for a **solid green background (`#00FF00`)** instead, then chroma-key +
despill locally (or have ChatGPT's code interpreter do it, same as the
existing pipeline). Every prompt below has been written with this in mind —
if you see "transparent background" in an older draft of this file, treat it
as the bug this note describes, not a valid instruction to send.

Unlike `shinobi_v2` (which needed a freshly generated `reference_full.png`
before any part could be prompted), Rose's design is already established and
validated across two prior HD pack generations. Style/proportions lock comes
straight from the **existing HD frames** instead of a new reference sheet:

- `assets/fighters/hd/rose_kunoichi/frames/idle_000.png` — standing guard,
  clearest full-body silhouette, front and back arm both visible.
- `assets/fighters/hd/rose_kunoichi/frames/punch_mid_000.png` — same guard
  from a slightly different angle, useful cross-check for the torso/hip line.
- `assets/fighters/hd/rose_kunoichi/frames/walk_000.png` — legs slightly
  apart, useful for checking the boot/trouser silhouette from both sides.
- `assets/fighters/hd/rose_kunoichi/frames/block_mid_000.png` — arms raised
  in front, useful for the forearm/hand wrap detail.

Attach all four to every prompt below (not just one) — several small
generations drifting from a single reference is exactly the failure mode
`HOW_TO_GENERATE_IMAGES.md` documents for whole-animation boards; the parts
pipeline only avoids that if every part stays visually locked to the same
multi-angle reference set.

Style paragraph (from `assets_source/fighters/PARTS_SPEC.md`, repeated here
for convenience): adult kunoichi, pink/rose hair in a high ponytail with a
couple of loose strands framing the face, fair skin. Black and dark-purple
fitted combat outfit (long-sleeve tunic/jacket, wrapped sleeve detail), pink
sash tied at the waist trailing to one side, dark fitted trousers, black
knee-high boots with pink/magenta trim, black arm wraps. Palette: black +
dark purple base, pink/magenta accents (hair, sash, trim).

**Critical rule for every prompt below: neutral pose only.** The reference
frames show a bent-knee fighting guard — use them strictly for style, color,
material and proportion. Every individual limb part must be drawn straight
and hanging/standing neutral (not bent, raised, or striding), otherwise the
rig can't repose it. This is the exact mistake `HOW_TO_GENERATE_IMAGES.md`
documents for whole-animation boards (asking for "idle" and getting a
relaxed rest pose instead of a combat guard) — here it runs the other
direction: asking for a "part" and getting the reference's dynamic guard
pose baked into an individual limb instead of a straight neutral one.

Common suffix for every prompt (not repeated below): *"Solid flat green
(#00FF00) background, no gradient, no shadow, no ground, no text, no other
body parts, isolated single piece only, same art style/proportions/lighting
as the reference frames, character facing right."* Chroma-key + despill
locally after download (or via ChatGPT's code interpreter, same as
`HOW_TO_GENERATE_IMAGES.md` step 4) — do not ask for "transparent
background" directly, see the correction note at the top of this file.

Generate in three batches by body region (per `PARTS_SPEC.md`'s
recommendation — 19 parts in one request degrades consistency); each batch
below is one ChatGPT message with all four reference frames attached.

---

## Batch A — head, hair, torso, pelvis, sash

### 1. `head.png` — attaches to: head

> Generate ONLY the bare head and face, WITHOUT any hair: face shape, fair
> skin, visible eyes with a focused combat expression, ears. Do NOT include
> any hair at all (front fringe or back ponytail mass — both are separate
> pieces), do NOT include the neck or torso below. Same head angle as the
> reference frames, facing right.

### 2. `hair_front.png` — attaches to: head

> Generate ONLY the front portion of the hairstyle: the loose pink/rose
> strands framing the forehead and face, matching the reference frames'
> texture and color. Do NOT include the face/eyes underneath, do NOT include
> the back ponytail mass (separate piece) — front strands only.

### 3. `hair_back.png` — attaches to: head

> Generate ONLY the back half of the hairstyle — the high ponytail mass that
> would be hidden behind the head and upper neck when viewed from the side.
> Same pink/rose color and texture as the reference frames. Do NOT include
> the face, ears, forehead, or the front hair strands (separate piece) —
> hair silhouette only.

### 4. `torso.png` — attaches to: torso

> Generate ONLY the chest/torso: the black and dark-purple fitted long-sleeve
> tunic/jacket with its wrapped sleeve detail, exactly matching the reference
> frames. Include the neck but NOT the head, face, or hair. Do NOT include
> the arms, do NOT include the waist sash/belt or anything below the
> waistline. Upright neutral posture, not the reference's bent-knee guard.

### 5. `pelvis.png` — attaches to: pelvis

> Generate ONLY a narrow hip/waist band: the dark fitted trouser waistline
> and belt line, exactly as in the reference frames. Do NOT include the pink
> sash (separate piece), do NOT include the torso/chest above, do NOT
> include the thighs or trousers below — just the waist band itself.

### 6. `accessory_main.png` — attaches to: pelvis

> Generate ONLY the pink sash: the full waist sash tied at the hip with its
> trailing tail hanging/flowing to one side, exactly matching the reference
> frames' pink/magenta color, knot, and fabric flow. Show it laid out on its
> own (as if removed from the body, not wrapped around a torso) — do NOT
> include the belt, trousers, or any other clothing.

---

## Batch B — arms and hands

### 7. `upper_arm_back.png` — attaches to: upper_arm_back

> Generate ONLY the upper arm (shoulder to elbow) of the FAR arm — the arm
> that would be partially hidden behind the torso in a side view. Arm
> hanging straight down at the character's side, NOT raised or in a guard
> position. Same black arm-wrap material as the reference frames. Do NOT
> include the shoulder seam of the jacket above, do NOT include anything
> below the elbow, do NOT include the hand.

### 8. `forearm_back.png` — attaches to: forearm_back

> Generate ONLY the forearm (elbow to wrist) of the FAR arm, held straight
> (elbow not bent). Same black arm-wrap wrapping detail as the reference
> frames. Do NOT include the upper arm above the elbow, do NOT include the
> hand/fingers.

### 9. `hand_back.png` — attaches to: hand_back

> Generate ONLY the hand of the FAR arm, relaxed and slightly open (fingers
> gently curled, not a fist, not fully spread). Fair skin matching the
> reference frames, no glove. Do NOT include any wrist wrap — cut off
> exactly at the wrist.

### 10. `upper_arm_front.png` — attaches to: upper_arm_front

> Generate ONLY the upper arm (shoulder to elbow) of the NEAR arm, hanging
> straight down at the character's side — NOT raised or in a guard position
> like the reference frames. Same black arm-wrap material and jacket
> shoulder seam as the reference. Do NOT include anything below the elbow or
> the hand.

### 11. `forearm_front.png` — attaches to: forearm_front

> Generate ONLY the forearm (elbow to wrist) of the NEAR arm, held straight
> (not bent). Same black arm-wrap wrapping detail as the reference frames.
> Do NOT include the upper arm above the elbow or the hand.

### 12. `hand_front_open.png` — attaches to: hand_front

> Generate ONLY the hand of the NEAR arm, relaxed and open with fingers
> gently extended — fair skin, no glove, matching the reference frames. Do
> NOT include any forearm/wrist wrap — cut off exactly at the wrist.

### 13. `hand_front_fist.png` — attaches to: hand_front

> Generate ONLY the hand of the NEAR arm as a closed fist, same fair skin
> tone as `hand_front_open`. Do NOT include any forearm/wrist wrap.
> **Important:** frame the wrist edge at the same position/scale/angle as
> `hand_front_open.png` so the two are interchangeable without the hand
> appearing to jump position when the pipeline swaps between them.

---

## Batch C — legs and boots

### 14. `thigh_back.png` — attaches to: thigh_back

> Generate ONLY the thigh (hip to knee) of the FAR leg, straight and
> vertical, standing neutral (NOT striding/bent like the reference frames'
> stance). Covered by the same dark fitted trouser fabric as the reference.
> Do NOT include the hip/waist area above, do NOT include the knee or shin
> below.

### 15. `shin_back.png` — attaches to: shin_back

> Generate ONLY the shin (knee to ankle) of the FAR leg, straight and
> vertical. Same dark fitted trouser fabric tucked into the boot top, as in
> the reference frames. Do NOT include the thigh above the knee, do NOT
> include the foot/boot below the ankle.

### 16. `boot_back.png` — attaches to: boot_back

> Generate ONLY the foot of the FAR leg: the black knee-high boot with
> pink/magenta trim, exactly matching the reference frames' footwear. Frame
> it with the ankle/top of the boot shaft at the TOP of the image and the
> toe pointing to the right. Do NOT include the shin/trouser above the boot
> shaft.

### 17. `thigh_front.png` — attaches to: thigh_front

> Generate ONLY the thigh (hip to knee) of the NEAR leg — the leg closer to
> the camera — straight and vertical, standing neutral. Same dark fitted
> trouser fabric as the reference frames. Do NOT include the hip above or
> the knee/shin below.

### 18. `shin_front.png` — attaches to: shin_front

> Generate ONLY the shin (knee to ankle) of the NEAR leg, straight and
> vertical. Same dark fitted trouser fabric tucked into the boot top as the
> reference frames. Do NOT include the thigh above or the foot below.

### 19. `boot_front.png` — attaches to: boot_front

> Generate ONLY the foot of the NEAR leg: same black knee-high boot with
> pink/magenta trim as the reference frames. Ankle/boot shaft top at the top
> of the image, toe pointing right. Do NOT include the shin/trouser above
> the boot shaft.

---

## After generating

Crop/clean each result to its own transparent PNG named exactly as above,
drop into `assets_source/fighters/rose_kunoichi_v2/parts/`. Don't worry
about getting the aspect ratio pixel-perfect against `PARTS_SPEC.md`'s
guidance — `blender/pipeline.py` reads each image's actual size and scales
accordingly. Each limb piece should keep a little extra length beyond its
"logical" joint boundary on both ends (per `PARTS_SPEC.md`) so the rig has
room to overlap adjacent parts and hide the seam once posed.

Phase 2 (`hand_back_fist.png`, `hair_strand_front.png`,
`hair_strand_back.png`) is intentionally not in any batch above — generate
only if an authored animation in `blender/animation_defs.py` actually needs
it (see the v2 plan, Stage 4).
