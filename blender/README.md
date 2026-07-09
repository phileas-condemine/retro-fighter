# Blender v2 sprite pipeline

Automates `retro_fighter_v2_blender_sprite_pipeline.md`: rig a character
from cutout part PNGs, pose it, render transparent frames, and write a
`manifest.json` compatible with `retro_fighter/sprites.py` — the same
contract LD and HD packs already follow (see `assets/fighters/CONTRACT.md`).

**Status: validated end-to-end with real character art.** `rose_kunoichi` has
a complete v2 pack — see the "Status" section below for the full picture and
`assets_source/fighters/rose_kunoichi_v2/PROGRESS.md` for the itemized
checklist. `shinobi` doesn't have a v2 pack yet, but needs no pipeline
changes to get one (see "Next steps" below). The mechanism itself (rig
assembly, per-joint FK posing, rendering, manifest export, loading back
through the real game's `FighterSpriteSet`) is also still exercised against
placeholder art by `make_placeholder_parts.py` for quick pipeline-change
sanity checks that don't need a real render.

## Requirements

- Blender 4.5 LTS, installed via `winget install --id BlenderFoundation.Blender.LTS.4.5 --exact`
  (already done on this machine). `find_blender.py` locates it automatically
  (checks `BLENDER_EXE` env var, then PATH, then the default Windows install
  location) — nothing to hardcode.
- Pillow, for `make_placeholder_parts.py` only (dev-only tool, not a project
  dependency — see the same caveat in `tools/sprites/validate_manifest.py`).

## Running it

```bash
python blender/run_pipeline.py \
    --fighter rose_kunoichi \
    --parts-dir assets_source/fighters/rose_kunoichi_v2/parts \
    --out assets/fighters/v2/rose_kunoichi \
    --anims idle,walk,punch_mid
```

`run_pipeline.py` is a thin wrapper: it finds Blender, resolves `--parts-dir`/
`--out` to absolute paths (relative paths handed straight to Blender's own
CLI have been observed to resolve inconsistently against a freshly-reset,
unsaved scene), and forwards everything else to `pipeline.py`, which is the
actual Blender automation (must run *inside* Blender's Python via `-b
--python`, not a plain interpreter — `run_pipeline.py` handles that).

Output: `assets/fighters/v2/<fighter_id>/{manifest.json, frames/*.png}` —
validate it the same way as any other pack:

```bash
python tools/sprites/validate_manifest.py assets/fighters/v2/rose_kunoichi --reference assets/fighters/ld/rose_kunoichi
```

## Testing the pipeline without real art

```bash
python blender/make_placeholder_parts.py --out blender/test_fixtures/rose_kunoichi_v2/parts
python blender/run_pipeline.py --fighter rose_kunoichi \
    --parts-dir blender/test_fixtures/rose_kunoichi_v2/parts \
    --out blender/test_fixtures/rose_kunoichi_v2/output \
    --anims idle,walk,punch_mid
```

`blender/test_fixtures/` is gitignored (fully regenerable from the two
commands above) — use it to sanity-check a pipeline change before pointing
it at real art.

## How the rig works (and one deliberate deviation from the plan doc)

`retro_fighter_v2_blender_sprite_pipeline.md` (section 7.2) suggests a
native Blender **Armature** with bones, parts parented via `parent_type=
'BONE'`. This pipeline uses a plain **Empty-object parent chain** instead
(see `rig_config.py`'s docstring for the full reasoning) — scripting bone
parenting correctly requires computing `matrix_parent_inverse` by hand or
objects silently snap to the wrong transform, which is exactly the kind of
error that's invisible until you're staring at Blender's UI, which this
headless pipeline never does. Object-to-object parenting has no such
footgun: a child's transform is always correct relative to its parent by
construction. For "option A" rigid-part rigging (which is what the plan doc
itself recommends starting with, before any mesh deformation), an Empty
chain gives the identical posable result — full forward kinematics, each
joint parented to the next, rotating a parent swings everything below it.

Layout of the core files:

| File | Contents |
|---|---|
| `parts_spec.py` | Canonical list of expected part files, which joint each attaches to, phase 1 (required) vs phase 2 (nice-to-have). No `bpy` — plain data. |
| `rig_config.py` | The joint chain: parent/offset/length/direction per joint. No `bpy`. |
| `animation_defs.py` | All 22 animations' keyframe poses (sparse: only bones that move away from rest are listed). No `bpy`. |
| `pipeline.py` | The actual Blender automation — reads the three files above, builds the rig, poses it, renders, writes the manifest. Requires `bpy`. |
| `find_blender.py` | Locates the Blender executable. No `bpy`. |
| `run_pipeline.py` | CLI convenience wrapper around `blender -b --python pipeline.py --`. No `bpy`. |
| `make_placeholder_parts.py` | Generates dummy part PNGs for testing. No `bpy`. |

Everything except `pipeline.py` itself runs under a plain `python`
interpreter — only `pipeline.py` needs to execute inside Blender.

## Status: real art integrated for `rose_kunoichi`

`rose_kunoichi` has a complete v2 pack: all 19 phase-1 parts generated
(ChatGPT, green-screen + local chroma-key — see
`HOW_TO_GENERATE_V2_SPRITES.md`, the full walkthrough including the pitfalls
actually hit), all 22 animations rendered (the engine's 20 keys from
`assets/fighters/CONTRACT.md` plus `hitstun`/`ko`/`crouch_punch_low`/
`crouch_kick_low` plus `dash`), 0 errors/0 warnings from
`tools/sprites/validate_manifest.py --reference ld`, and validated in a real
headless match via `Renderer.set_graphics_variant("v2")` (see
`assets_source/fighters/rose_kunoichi_v2/PROGRESS.md` for the itemized
checklist). `shinobi` does not have a v2 pack yet — `Renderer.sprite_sets["v2"]`
is built conditionally per fighter_id and falls back to HD/LD for any
fighter without one, so this doesn't block anything.

## Known rough edges (expected — first pass, not finely hand-tuned)

- **Part-to-joint sizing used the generic `coverage = 0.85` heuristic
  unmodified** (`pipeline.py`'s `add_part_plane`) — it turned out to already
  read correctly against Rose's real proportions without per-part overrides,
  so `parts_spec.py` has none. A future character (Shinobi) may still need
  one if its proportions differ enough.
- **Animation poses in `animation_defs.py` are a first pass**, chosen to
  read correctly at a glance (checked via zoomed single frames and a
  multi-animation contact sheet), not frame-by-frame hand-tuned against
  real gameplay footage.
- **`ko`'s torso pitch is deliberately capped well short of a full supine
  collapse** (~48°, not 90°+) — the rig only rotates joints, it doesn't
  translate the pelvis forward as the torso pitches down, and a larger
  pitch made the head/arms silhouette visually detach from the hips/legs
  instead of reading as a collapse. See `HOW_TO_GENERATE_V2_SPRITES.md`'s
  step 7 for the before/after.
- **No mesh deformation** (plan doc's "option B") — joints are rigid, so
  sharp bends (e.g. a deeply bent knee) show a visible seam between parts
  rather than a smooth joint. Acceptable per the plan doc's own
  recommendation to start with option A.
- `Keyframe.root_offset` (added for crouch — see `animation_defs.py`) is a
  manually-picked translation per keyframe, not solved automatically; it
  only cancels out the leg-bend-induced foot lift for the specific bend
  angles used in that keyframe, not any arbitrary future pose.

## Next steps

1. **Shinobi v2** (not started): `shinobi_v2/PARTS_PROMPTS.md` already
   exists. Generate its 19 phase-1 parts the same way (green-screen +
   chroma-key, see `HOW_TO_GENERATE_V2_SPRITES.md`), run
   `blender/run_pipeline.py` against them, and validate — no rig/animation
   rework is expected (`rig_config.py`/`animation_defs.py` are
   character-agnostic) unless Shinobi's proportions need per-part
   `rig_config.py` overrides once real art makes them visible.
2. **Phase 2 parts** (`hand_back_fist`, `hair_strand_front`,
   `hair_strand_back`) — only generate if an animation actually ends up
   needing them (e.g. a two-handed guard); nothing currently does.
3. Optionally hand-tune `animation_defs.py`'s rotation values against real
   gameplay footage now that the full pack renders end-to-end — the current
   values are first-pass, chosen to prove each pose reads correctly, not
   frame-by-frame polished.
