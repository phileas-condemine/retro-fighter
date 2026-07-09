"""Canonical list of cutout body parts expected per fighter, and which joint
(see rig_config.py) each one is attached to.

This is the single source of truth for three things that all need to agree
on the same names:
  - what ChatGPT/DALL-E needs to generate (see ../assets_source/fighters/PARTS_SPEC.md,
    generated from this file);
  - what blender/pipeline.py looks for on disk when building a rig;
  - what blender/make_placeholder_parts.py generates for pipeline testing
    before real art exists.

No bpy import here on purpose: this module is plain data, usable from a
regular Python interpreter (docs generation, placeholder generation, unit
tests) without Blender.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PartSpec:
    name: str  # file stem, e.g. "torso" -> parts/torso.png
    joint: str  # joint name in rig_config.JOINTS this part is attached to
    z_index: int  # draw order within the scene (higher = closer to camera)
    aspect: str  # "limb" (tall rectangle) or "blob" (roughly square) -- only
    # used to size sane placeholder art; real art can be any shape as long
    # as the character's silhouette reads correctly once composited.
    phase: int  # 1 = required for the idle/walk/punch_mid vertical slice,
    # 2 = added once phase 1 is validated (see retro_fighter_v2_blender_sprite_pipeline.md 6.1)
    description: str  # what to actually draw, used to generate the image spec
    # How much of the part's plane maps to its joint's `length` (see
    # pipeline.py's add_part_plane: plane_h = joint.length / coverage) --
    # None uses the pipeline's own default. Lower = bigger plane = more
    # overlap into neighboring parts (hides seams) but also a longer visual
    # "reach" for the same rotation angle. Two different problems pull this
    # in opposite directions: torso/head/pelvis/hair had visible gaps at
    # their seams (neck, before the fix below) that wanted a LOWER value,
    # while limbs (arms/legs) that actually rotate got visibly exaggerated,
    # over-dramatic swings from that same lower value applied globally --
    # a real crouch/kick pose swung much further than the authored angle
    # implied once every limb plane got ~20% longer. Per-part overrides let
    # the torso/head cluster keep the extra overlap without inflating how
    # far a rotating limb appears to swing.
    coverage: float | None = None
    # Extra multiplier on plane WIDTH only, independent of coverage/height.
    # Needed because coverage/plane_h controls both the part's size AND how
    # far its plane extends from the joint origin in one direction (see
    # add_part_plane) -- cranking coverage down to widen a part also makes
    # it reach further past its joint (e.g. torso's collar growing tall
    # enough to swallow the head), which isn't what "make it wider" means.
    # width_scale only touches plane_w, leaving the anchor/reach unchanged.
    width_scale: float = 1.0
    # Horizontal recentering, as a fraction of plane_w. The pipeline always
    # maps the source image's geometric center to the joint's local X=0 --
    # fine as long as the art's actual attachment point (e.g. a boot's
    # ankle opening) sits at the horizontal center of its canvas, but not
    # every generated part is cropped that evenly (boot_front/boot_back's
    # ankle opening sits ~22-24% of the image width left of center, which
    # only became visible once a lower `coverage` enlarged the boot plane
    # enough to make the gap obvious). Rather than hand-edit/re-crop the
    # source art (risking clipping the toe, which extends to the canvas
    # edge in the bounding box), a positive value shifts the whole plane
    # right in the joint's local frame by that fraction of plane_w, pulling
    # an off-center-left attachment point back under the parent joint.
    anchor_offset_x: float = 0.0
    # Vertical counterpart to anchor_offset_x, as a fraction of plane_h.
    # Positive shifts the plane UP (+Z) in the joint's local frame. Needed
    # for hair_front/hair_back: both attach to the "head" joint, but their
    # art's natural "attaches to the skull here" point isn't necessarily at
    # the vertical center of their canvas either (ChatGPT's review flagged
    # the assembled hair as sitting too high/vertical -- ponytail rooted
    # above the skull instead of behind it, fringe not low enough over the
    # forehead) -- same class of anchor-mismatch bug as the boots, just on
    # the other axis.
    anchor_offset_z: float = 0.0


# Ordered back-to-front (z_index ascending) so the default draw order in
# build_cutout_scene.py already looks right without extra config: back limbs
# and hair behind the torso, front limbs and hair in front of it.
PARTS: list[PartSpec] = [
    # Re-derived from scratch after direct user feedback comparing an
    # in-game screenshot against the reference sheet: the previous
    # calibration (coverage=0.26, anchor_offset_z=-0.20 -- chasing the
    # earlier top-clipping bug) squashed the whole ponytail into a short,
    # bunched "poof" that cuts off around the shoulder blades, nothing like
    # the reference's long cascade flowing down past the hip. The two
    # constraints (don't clip the canvas top, DO flow down to roughly
    # hip/upper-thigh height) can't both be hit by sliding one anchor
    # fraction around on the OLD undersized plane -- solved simultaneously
    # instead: with plane_top = head_z + plane_h*(1+off) and
    # plane_bottom = head_z + plane_h*off, picked a safe top (world Z~2.3,
    # a comfortable margin inside the camera's visible top at Z~2.62 for
    # the current target_height_px=155) and a hip-height bottom (world
    # Z~0.6), which gives plane_h=1.70 and off=-0.6 -- a much taller plane,
    # shifted much further down, so the flowing tail actually reads instead
    # of being cropped away. Attaches to the dedicated "hair_back" joint
    # (see rig_config.py) instead of "head" directly so it can carry its
    # own independent sway animation (see animation_defs.py's idle) without
    # that motion rotating the face.
    # Re-derived from scratch for the new tail-only art (see head's own
    # comment above for why the split changed). Geometry solved so the
    # tail's TOP edge meets the tie point baked into the new head asset
    # (estimated at world Z~2.25, ~15% down from the head plane's own top)
    # and its bottom still flows to roughly hip height (Z~0.6), matching
    # the previous flowing-length target.
    # anchor_offset_x=-0.19: even without a poof section, the tail's TOP
    # rows (near the tie/attachment point) still aren't centered in the
    # source canvas -- pixel check found the opaque content's horizontal
    # center sits ~450px into a 655px-wide image (vs the true center at
    # 328px), i.e. biased toward the canvas's right half. Same convention
    # as before: canvas-right maps to local +X (toward the face), so an
    # uncorrected mapping pushed the tail's attachment forward past the
    # head's own hair silhouette instead of tucking behind it -- visible
    # as a hard rectangular edge (the plane's own crop boundary) cutting
    # into the forehead/bangs area. Confirmed by re-rendering with
    # hair_back hidden entirely: the artifact disappeared, isolating it to
    # this part. Shifted negative (backward) to tuck the attachment point
    # behind the head instead of poking out front-side.
    # Re-derived again after the head plane shrank drastically (see head's
    # own comment below): hair_back attaches to its own joint at the same
    # fixed world origin as "head" (Z=1.62, see rig_config.py), independent
    # of how big the head's PLANE is -- but the tail's calibration target
    # (its top edge = the tie point baked into head.png, a fixed pixel
    # position within that image) was expressed as a fraction of the OLD,
    # oversized head plane's own height, so shrinking the head plane without
    # re-deriving this left the tail's attachment point floating way above
    # the now-much-smaller head. Recomputed the tie point's world Z using
    # the same ~13.5% "down from the head plane's top" fraction against the
    # NEW head plane (coverage=0.90 below) -- landing at world Z~1.83 -- and
    # re-solved coverage/anchor_offset_z the same way as before (tail top at
    # the tie point, tail bottom at hip height, Z~0.6).
    # Re-derived once more (same tie-point-tracking method as before) since
    # head's plane grew again -- see head's own comment below (this time a
    # deliberate 2x user-requested enlargement, not a fine calibration nudge).
    PartSpec("hair_back", "hair_back", 10, "blob", 1, "Flowing ponytail tail only, from the tie point down past the hip -- no poof, no tie, no head content.", coverage=0.183, anchor_offset_z=-0.667, anchor_offset_x=-0.19),
    # coverage/anchor_offset_z/width_scale added per direct user feedback
    # ("trou en haut à gauche du vêtement"): torso.png draws a literal bare-
    # shoulder cutout (a pink-ringed armhole revealing fishnet) for the far
    # shoulder, centered at approx world (x=-0.17, z=1.64) -- almost exactly
    # this joint's own local X, but a good ~0.2 BU ABOVE this joint's origin
    # (Z=1.53), which is also this part's plane's TOP edge by construction
    # (direction=-1 -- a limb plane can never extend above its own joint).
    # Confirmed by isolating: the gap exactly matches the hole's upper
    # portion the unmodified plane couldn't reach. Fixed by both lowering
    # coverage (taller plane) and a positive anchor_offset_z (shifts the
    # plane up relative to the joint) together, instead of moving the joint
    # itself -- moving the joint would drag forearm_back/hand_back's actual
    # attachment point up with it and break the front/back shoulder-height
    # symmetry; PartSpec anchors only affect the rendered plane, not the
    # kinematic chain. Solved so the plane's new top reaches Z~1.75 (just
    # past the hole's top) while its bottom still overlaps forearm_back's
    # own top (~Z1.18) by about the same margin as before. width_scale=1.15
    # widens the plane enough to span the hole's ~0.17 BU width (it was
    # already close to horizontally centered on the hole -- no anchor_offset_x
    # needed).
    # Dialed back again per the same fresh-eyes critique: the armhole-filling
    # fix (above) reads as convincing in isolation but an independent review
    # called it out unprompted as "a big orange ball attached to the side of
    # the upper torso... too spherical and detached." Shrinking width_scale
    # and pulling anchor_offset_z back down (still enough to keep the hole
    # filled, just less bulbous/raised) to make it read more like a shoulder
    # cap than an attached sphere.
    # width_scale pulled back to 1.0 (no extra width at all) per a second
    # independent fresh-eyes read that STILL called this "a floating black
    # ball / disk" even after the previous dial-back -- two rounds of
    # feedback in a row flagged roundness/detachment, not hole-visibility,
    # so the extra width was fighting the wrong problem. A narrower plane
    # reads more like a limb silhouette and less like an attached sphere,
    # at the cost of a thin sliver of the armhole cutout staying visible at
    # the very top -- acceptable since the torso art already shows fishnet
    # through that cutout by design, so a small gap there reads as the
    # costume's own cutout rather than a rendering bug.
    PartSpec("upper_arm_back", "upper_arm_back", 11, "limb", 1, "Upper arm (shoulder to elbow) of the far arm.", coverage=0.80, anchor_offset_z=0.15, width_scale=1.0),
    # width_scale added per the same fresh-eyes critique that flagged the
    # punch pose's arm as "long and thin compared with the body" / "fist
    # small relative to the shoulder/torso mass" -- arms never got the
    # thickness pass the legs did earlier this session (see thigh/shin/boot
    # comments above), so once those bulked up the arms read thin by
    # comparison. Applied to both arms for left/right consistency.
    PartSpec("forearm_back", "forearm_back", 12, "limb", 1, "Forearm (elbow to wrist) of the far arm.", width_scale=1.3),
    # anchor_offset_x added per direct user feedback ("main pas alignée avec
    # avant-bras"): hand_back.png's wrist band isn't centered in its own
    # canvas (the fingers splay toward +X/front, pulling the bbox center
    # that way) -- pixel check found the wrist band's own center sits at
    # ~15% of plane_w to the left (-X) of the image's geometric center,
    # which is what anchor_offset_x=0 maps to the joint. Same class of fix
    # as boot_front/back's ankle-opening offset.
    # width_scale bumped further per a second independent review still
    # calling hands/fists undersized ("15-25% larger") relative to the
    # now-bulked-up body.
    PartSpec("hand_back", "hand_back", 13, "blob", 1, "Hand of the far arm, relaxed/open, no fist variant needed for phase 1.", coverage=0.70, anchor_offset_x=0.15, width_scale=1.55),
    # width_scale added per direct user feedback ("cuisses, mollets et pieds
    # tout fin, ce n'est pas réaliste"): thigh/shin/boot planes were sized
    # purely from coverage (which controls reach/overlap, tuned for seam-
    # hiding and rotation-arc feel -- see this file's coverage docstring),
    # never for on-screen thickness, so they ended up much narrower than the
    # torso's own width_scale=1.5 bulk-up -- reading as pencil-thin next to
    # it. width_scale only touches plane width, leaving reach/overlap
    # unchanged.
    PartSpec("thigh_back", "thigh_back", 10, "limb", 1, "Thigh (hip to knee) of the far leg.", width_scale=1.5),
    # width_scale bumped further -- a second independent review flagged the
    # thigh-to-calf taper as too aggressive ("thighs bulky, calves/ankles
    # thin... makes the legs look lumpy").
    PartSpec("shin_back", "shin_back", 11, "limb", 1, "Shin (knee to ankle) of the far leg.", width_scale=1.55),
    # coverage/width_scale bumped further per fresh-eyes critique: "boots/
    # feet are too small and delicate for such a heavy lower body... makes
    # the character feel top-heavy and less grounded" -- called out
    # independently of the thigh/shin widening (this session's earlier
    # width_scale=1.15 wasn't enough once the thighs/shins got their own
    # bump too).
    # coverage/width_scale bumped again -- a second independent review still
    # called feet "very small and pointy... weakens groundedness".
    PartSpec("boot_back", "boot_back", 12, "blob", 1, "Boot/foot of the far leg.", coverage=0.30, anchor_offset_x=0.30, width_scale=1.55),
    # torso is now the WHOLE shoulders-to-buttocks block in one rigid piece
    # (chest, belly, hips, buttocks, neck, shoulder caps) -- there's no
    # animation that bends the spine independently from the hips, so a
    # separate "pelvis" visual part (as used in an earlier iteration) was
    # just an extra seam for no articulation benefit; see rig_config.py's
    # torso joint comment for the matching pivot change. z_index=15 is
    # deliberately LOWER than accessory_main below (15 < 21) -- the sash is
    # worn outside/over the torso, so it must draw on top of (closer to
    # camera than) the torso's hem, not the other way around. coverage=0.60
    # keeps the seam-overlap fix only (no extra height) -- pushing coverage
    # lower to also make the torso bigger overall swelled the collar tall
    # enough to grow past the neck and swallow the head, since a part's
    # plane extends from its joint origin in ONE direction (see
    # add_part_plane), not centered on the visible art. width_scale widens
    # the silhouette (the "too narrow/small" complaint) without that side
    # effect.
    # coverage bumped 0.60 -> 0.70 relative to the earlier chest-only torso:
    # coverage's overshoot is proportional to the joint's length (plane_h =
    # length/coverage), and this piece's length grew 0.40 -> 0.55 once it
    # absorbed the old pelvis's span (see rig_config.py). Keeping coverage
    # at 0.60 would've scaled the overshoot up by the same ~40%, inflating
    # the whole plane (and therefore the art) well past the actual
    # shoulder-to-hip content -- 0.70 keeps roughly the same ABSOLUTE
    # overlap in world units as the old torso had, instead of the same
    # proportion of a now-larger length.
    # width_scale reduced 1.6 -> 1.5 per ChatGPT's P1 ranking ("Torso+hips
    # may now be too wide/heavy" / "still too busy/over-heavy in motion").
    # The original 1.6 bump chased an earlier complaint that the torso read
    # too narrow/small; 1.5 keeps most of that overlap-with-thighs/arms fix
    # while pulling back from the overcorrection.
    # Reduced again 1.5 -> 1.4 per ChatGPT's read of the post-limb-thickening
    # batch ("torso/hip heavy", "slightly chunky/crowded in idle/walk"): once
    # the legs also got their own width_scale bump (see thigh/shin below,
    # fixing the user's separate "pencil-thin legs" complaint), the torso's
    # existing 1.5 read as competing bulk rather than the "narrow/small" gap
    # it was originally chasing.
    PartSpec("torso", "torso", 15, "blob", 1,
             "Full torso block: chest, belly, hips, and buttocks in one piece, including the neck and short sleeveless shoulder caps. No arms/sleeves (separate rig pieces cover those). Ends at the top of the thighs.",
             coverage=0.70, width_scale=1.55),
    # "pelvis" joint itself is kept in rig_config.py as a purely structural
    # (never independently rotated) anchor for the thighs and torso -- it
    # has no PartSpec of its own anymore, since torso's art now covers that
    # whole region. accessory_main (the sash) still attaches to the pelvis
    # joint since it hangs from the waist regardless of the torso/hip merge.
    PartSpec("accessory_main", "pelvis", 21, "limb", 1,
             "The character's signature trailing cloth/accessory (Rose: pink sash; Shinobi: dark green scarf), hanging from the waist."),
    PartSpec("thigh_front", "thigh_front", 23, "limb", 1, "Thigh (hip to knee) of the near leg.", width_scale=1.5),
    PartSpec("shin_front", "shin_front", 24, "limb", 1, "Shin (knee to ankle) of the near leg.", width_scale=1.55),
    PartSpec("boot_front", "boot_front", 25, "blob", 1, "Boot/foot of the near leg.", coverage=0.30, anchor_offset_x=0.30, width_scale=1.55),
    # Regenerated per direct user feedback: three independently-anchored
    # hair/head pieces (bald head + separate front bangs + separate back
    # poof/tail) was a repeated source of misalignment all session. The
    # fixed hair (bangs, side volume, crown, tie) is now baked directly into
    # this single head asset -- hair_front no longer exists as a separate
    # part, and hair_back (below) is now just the flowing tail, attached
    # starting from this asset's own crown/tie point.
    # coverage/anchor_offset_z re-derived empirically (not just from a flat
    # px-scale match): a first pass tried to preserve the OLD bald head's
    # exact px-to-BU scale, but that ignores where the chin/face actually
    # sits within the new, much-taller image (the poof adds height ABOVE
    # the face, it doesn't shrink the face within the frame) -- naively
    # scaling by total image height way overshot the plane's top edge.
    # Solved instead for keeping the chin at the same absolute world-Z as
    # the old calibration while accounting for the poof's added height
    # above the hairline; verified by rendering and comparing against the
    # last known-good idle frame before this change.
    # coverage/anchor_offset_z re-derived again per direct user feedback
    # ("la tête est bien plus jolie maintenant, mais elle est énorme par
    # rapport au reste du corps"): the previous calibration (coverage=0.34)
    # was solved for keeping the CHIN at the right world-Z, but never
    # actually checked the resulting overall SIZE -- coverage=0.34 makes
    # plane_h=length/coverage=0.82 BU, and since this asset's opaque content
    # fills ~97% of its own canvas (a tight 15px crop, see the source-art
    # comment history), that plane_h basically *is* the rendered head's
    # height -- 43% of CHARACTER_HEIGHT=1.9, roughly a 1:2.3 head-to-body
    # ratio (a toddler/chibi proportion, not the "réaliste" the user asked
    # for). Re-solved for a ~1:6.3 ratio instead (content height ~0.30 BU,
    # coverage=0.90 -> plane_h=0.31), then re-solved anchor_offset_z the
    # same way as before (keep the chin at the same world-Z this was last
    # calibrated against) against the new, much shorter plane.
    # coverage/anchor_offset_z nudged back up per an independent, history-free
    # ChatGPT read (fresh chat, no prior context, asked to critique these
    # frames cold): the previous correction for "head too big" overshot --
    # a fresh pair of eyes called the head "slightly too small" (~5-12%
    # under-scaled) now that the shoulders/torso/thighs all got bulkier too,
    # and explicitly said not to shrink it further. Bumped content height
    # back up by ~7% (coverage 0.90 -> 0.84) and re-solved anchor_offset_z
    # the same way as before (keep the chin at the same calibrated world-Z).
    # Doubled again per explicit direct user instruction ("la tete doit etre
    # agrandie x2") overriding the ChatGPT reads above -- the user is the
    # final authority on the in-game look, not the AI reviewers, and this is
    # an unambiguous, deliberate 2x sizing call rather than a fine calibration
    # tweak. content height doubled (coverage 0.84 -> 0.42), anchor_offset_z
    # re-solved the same way (keep the chin at the same calibrated world-Z).
    PartSpec("head", "head", 30, "blob", 1, "Head and face with all fixed hair (bangs, side volume, crown, tie) baked in -- no flowing ponytail tail.", coverage=0.42, anchor_offset_z=-0.10),
    # width_scale added -- see forearm_back's matching comment above.
    PartSpec("upper_arm_front", "upper_arm_front", 32, "limb", 1, "Upper arm (shoulder to elbow) of the near arm.", width_scale=1.3),
    PartSpec("forearm_front", "forearm_front", 33, "limb", 1, "Forearm (elbow to wrist) of the near arm.", width_scale=1.3),
    # anchor_offset_x added per direct user feedback ("main pas alignée avec
    # avant-bras") -- see hand_back's matching comment above; same
    # off-center-wrist issue measured independently on this asset.
    PartSpec("hand_front_open", "hand_front", 34, "blob", 1, "Hand of the near arm, relaxed/open (idle, walk).", coverage=0.70, anchor_offset_x=0.15, width_scale=1.55),
    PartSpec("hand_front_fist", "hand_front", 34, "blob", 1, "Hand of the near arm, closed fist (punches).", coverage=0.70, anchor_offset_x=0.14, width_scale=1.55),
    # Phase 2: not needed to validate the pipeline, add once phase 1 renders correctly in-game.
    PartSpec("hand_back_fist", "hand_back", 13, "blob", 2, "Hand of the far arm, closed fist (needed once back-arm punches/guards are added)."),
    PartSpec("hair_strand_front", "head", 35, "limb", 2, "A loose strand of hair for idle secondary motion."),
    PartSpec("hair_strand_back", "head", 9, "limb", 2, "A second loose strand/tail of hair, behind the silhouette."),
]


def phase(n: int) -> list[PartSpec]:
    return [p for p in PARTS if p.phase <= n]


def by_name(name: str) -> PartSpec:
    for p in PARTS:
        if p.name == name:
            return p
    raise KeyError(f"no part named {name!r} in PARTS")
