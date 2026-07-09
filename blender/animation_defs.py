"""Vertical-slice animation definitions (idle, walk, punch_mid), per
retro_fighter_v2_blender_sprite_pipeline.md section 6.1.

Keyframes are sparse (only bones that move away from rest are listed);
blender/pipeline.py interpolates between them with Blender's own F-curves,
then bakes one render per output frame at the animation's fps. Rotations
are Euler XYZ in degrees, in each bone's local space, relative to rest pose
(0,0,0) -- these are first-pass values meant to prove the rig mechanism
(a placeholder part visibly swings when its bone rotates), not final,
hand-tuned poses; expect to re-tune once real character art is in place
and the proportions/silhouette are actually visible.

No bpy import here: plain data, read by blender/pipeline.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Keyframe:
    frame: int
    pose: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    hand_front_pose: str = "open"  # "open" or "fist" -- toggles which hand_front_* part is visible
    # Root joint LOCATION offset (Blender units, same space as rig_config.Joint.offset),
    # on top of its rest position (0,0,0). Bending the legs via rotation alone shortens
    # the hip-to-ankle distance, lifting the feet off the ground; a crouch keyframe pairs
    # that leg bend with a matching negative-Z root_offset so the feet stay planted while
    # the hips actually lower. Not automatic IK -- the animator picks a value that matches
    # the leg bend in the same keyframe. Defaults to no translation (every non-crouch
    # animation is unaffected).
    root_offset: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class AnimationDef:
    name: str
    fps: int
    loop: bool
    keyframes: list[Keyframe]

    @property
    def frame_count(self) -> int:
        # One rendered frame per output frame at `fps`, spanning the full
        # keyframe range (loop animations render up to but excluding the
        # last keyframe, since it's a duplicate of frame 0 for a clean loop).
        last = self.keyframes[-1].frame
        return last if self.loop else last + 1


ANIMATIONS: dict[str, AnimationDef] = {
    # hair_back sway added per direct user request ("tu pourrais animer sa
    # queue de cheval pour que ses cheveux aient un petit mouvement régulier
    # comme s'il y avait un vent léger"): hair_back now has its own joint
    # (see rig_config.py) separate from "head", specifically so it can carry
    # this kind of independent secondary motion without also swinging the
    # face. A gentle +3/-3 degree rock over the same breathing-cycle
    # keyframes reads as a light, regular wind sway without being large
    # enough to look like a snap or a flourish.
    "idle": AnimationDef(
        name="idle", fps=6, loop=True,
        keyframes=[
            Keyframe(0, {"hair_back": (0, 3, 0)}),
            Keyframe(6, {
                "torso": (2, 0, 0),
                "upper_arm_front": (0, -4, 0),
                "upper_arm_back": (0, 4, 0),
                "hair_back": (0, -3, 0),
            }),
            Keyframe(12, {"hair_back": (0, 3, 0)}),  # == frame 0, closes the loop
        ],
    ),
    "walk": AnimationDef(
        name="walk", fps=10, loop=True,
        keyframes=[
            Keyframe(0, {
                "thigh_front": (0, -25, 0), "shin_front": (0, 15, 0),
                "thigh_back": (0, 25, 0), "shin_back": (0, 0, 0),
                "upper_arm_front": (0, 20, 0), "upper_arm_back": (0, -20, 0),
                "hair_back": (0, 4, 0),
            }),
            # Passing pose: was a fully empty {} (every joint snaps to 0,
            # identical to standing idle), which is what a static picked
            # frame from this exact point looked like when reviewed --
            # walk's scissor extremes (frame 0/8) read fine on their own,
            # but the passing frame needs its own slight mid-stride bend
            # and a small downward root dip (real gait has a brief low
            # point as weight transfers between legs) so it doesn't read
            # as a dead stop mid-loop.
            # thigh angles kept at exactly 0 (not a small nonzero value) --
            # even a few degrees of thigh rotation here reopens the
            # torso/thigh hip-seam gap (its bottom-edge fill was only
            # verified gap-free at 0 and at the >=25deg range used by the
            # scissor keyframes, not in between); shin/arm/root_offset
            # still carry the "not a dead stop" distinction from idle.
            Keyframe(4, {
                "shin_front": (0, 8, 0), "shin_back": (0, 8, 0),
                "upper_arm_front": (0, 3, 0), "upper_arm_back": (0, -3, 0),
                "hair_back": (0, 0, 0),
            }, root_offset=(0.0, 0.0, -0.03)),
            Keyframe(8, {
                "thigh_front": (0, 25, 0), "shin_front": (0, 0, 0),
                "thigh_back": (0, -25, 0), "shin_back": (0, 15, 0),
                "upper_arm_front": (0, -20, 0), "upper_arm_back": (0, 20, 0),
                "hair_back": (0, -4, 0),
            }),
            Keyframe(12, {
                "shin_front": (0, 8, 0), "shin_back": (0, 8, 0),
                "upper_arm_front": (0, -3, 0), "upper_arm_back": (0, 3, 0),
                "hair_back": (0, 0, 0),
            }, root_offset=(0.0, 0.0, -0.03)),  # passing pose (mirrored)
            Keyframe(16, {
                "thigh_front": (0, -25, 0), "shin_front": (0, 15, 0),
                "thigh_back": (0, 25, 0), "shin_back": (0, 0, 0),
                "upper_arm_front": (0, 20, 0), "upper_arm_back": (0, -20, 0),
                "hair_back": (0, 4, 0),
            }),  # == frame 0, closes the loop
        ],
    ),
    # upper_arm/forearm angles solved via 2-link IK (fist position relative
    # to the shoulder joint, upper_arm length 0.35 + forearm length 0.30)
    # rather than picked by eye: chamber and active both target the SAME
    # height (z=-0.18), only the forward reach (x) changes, so the fist
    # travels in a straight line instead of arcing up over the shoulder --
    # the original hand-picked angles let the fist rise well above shoulder
    # height at full extension, reading as a looping/circular swing instead
    # of a jab. See HOW_TO_GENERATE_V2_SPRITES.md for the solver.
    # Every angle below is the negation of the original IK solve (see
    # HOW_TO_GENERATE_V2_SPRITES.md): the solver assumed positive rotation
    # swings toward +X (character-forward, since the rig faces +X), but the
    # real render swings the OPPOSITE way -- punches/kicks were extending
    # backward (screen-left) instead of forward (screen-right, matching the
    # character's facing). Negating every angle in a 2-link chain mirrors
    # the reach to the other X side while leaving height unchanged (sin is
    # odd, cos is even), so the straight-line-at-constant-height property is
    # preserved, just aimed the correct direction.
    "punch_mid": AnimationDef(
        name="punch_mid", fps=15, loop=False,
        keyframes=[
            Keyframe(0, {"upper_arm_front": (0, 10, 0)}, hand_front_pose="open"),
            Keyframe(2, {"upper_arm_front": (0, 35, 0), "forearm_front": (0, -146, 0)}, hand_front_pose="fist"),  # chamber: fist tucked near ribs
            Keyframe(4, {"upper_arm_front": (0, -54, 0), "forearm_front": (0, -42, 0)}, hand_front_pose="fist"),  # active: extended straight out, same height as chamber
            Keyframe(7, {"upper_arm_front": (0, -13, 0), "forearm_front": (0, -125, 0)}, hand_front_pose="fist"),  # recovery: partway back to chambered
            Keyframe(9, {}, hand_front_pose="open"),  # back to idle-ish
        ],
    ),

    # -- Full-parity set (blender/README.md's "next steps") -- placeholder-grade
    # like the vertical slice above: proves the pose reads correctly, not
    # hand-tuned. punch_mid's startup/active/recovery shape and the HD pack's
    # per-animation fps/frame-count (see assets/fighters/hd/rose_kunoichi/
    # manifest.json's source_mapping) are used as pacing/target-height
    # references even though the art source differs.

    # Redesigned per ChatGPT's P1 ranking ("still reads like tilted
    # standing/floating rather than a clear jump frame"): the old values
    # were too small in magnitude on both keyframes to read as either a real
    # coil or a real tuck -- thigh=-15 is barely more bent than idle, and
    # the airborne frame's thigh=25/shin=35 use the wrong shin sign for a
    # tuck (kick_mid's proven chamber pose folds the shin the OPPOSITE way,
    # shin negative, to pull the heel up toward the seat -- see kick_mid's
    # "chamber, knee up" keyframe). Reused that chamber shape (thigh
    # positive + shin sharply negative) on both legs for a real airborne
    # tuck, deepened the takeoff coil to something crouch-adjacent, and
    # added root_offset (down on the coil, slightly up on the airborne
    # frame) since leg-bend alone shortens the hip-to-ankle reach and a
    # coil without a matching offset doesn't read as "loading up".
    "jump": AnimationDef(
        name="jump", fps=10, loop=False,
        keyframes=[
            Keyframe(0, {
                "torso": (0, 5, 0),
                "thigh_front": (0, -50, 0), "shin_front": (0, 45, 0),
                "thigh_back": (0, 30, 0), "shin_back": (0, 20, 0),
                "upper_arm_front": (0, 35, 0), "upper_arm_back": (0, 30, 0),
            }, root_offset=(0.0, 0.0, -0.15)),  # coiled takeoff crouch, arms swung back for windup
            # Deepened per ChatGPT's P1 follow-up ("arms don't yet give a super
            # strong jump intent silhouette" / "torso still reads mannequin-
            # stable"): pushed the torso arch further back and threw the arms
            # higher/wider (an explosive reaching silhouette instead of a
            # modest bent-elbow lift) and tightened the leg tuck slightly more.
            # Leg tuck re-derived per direct user feedback ("ses genoux ne se
            # plient pas dans le bon sens"): the old thigh=60/shin=-80 combo
            # reused the KICK chamber shape, which raises the KNEE but doesn't
            # actually pull the FOOT up -- forward-kinematics check showed the
            # foot only ended up 0.65 BU below the hip, barely different from a
            # standing leg's -0.88, i.e. only a shallow knee bend, not a tuck
            # (a real "knees pulled to the chest" airborne tuck needs the SHIN
            # folded back tight against the thigh, not re-extended toward the
            # ground). thigh=100/shin=-140 pulled the foot to only 0.22 BU
            # below the hip, a genuinely compact tuck -- but the user then
            # flagged the knees swinging the wrong way (toward screen-left,
            # -X, i.e. BEHIND the character, when they should tuck up in
            # FRONT of the body toward +X, matching the character's own
            # facing direction). That +100/-140 pair is the same "chamber"
            # shape kick_mid's windup uses, which deliberately cocks the knee
            # up-and-BACK before a kick snaps forward -- correct for a kick
            # windup, wrong for a jump tuck, which should pull the knees
            # forward/up, not backward/up. Since cos is even and sin is odd,
            # negating BOTH angles (thigh=-100, shin=+140) mirrors the whole
            # leg's swing direction while leaving the height (foot_z, built
            # from cosines) completely unchanged -- verified via the same FK
            # formula: still 0.22 BU below the hip, but now +0.22 BU
            # FORWARD of the hip instead of behind it.
            Keyframe(3, {
                "torso": (0, -15, 0),
                "thigh_front": (0, -100, 0), "shin_front": (0, 140, 0),
                "thigh_back": (0, -100, 0), "shin_back": (0, 140, 0),
                "upper_arm_front": (0, -50, 0), "upper_arm_back": (0, -45, 0),
            }, root_offset=(0.0, 0.0, 0.08)),  # airborne, both legs tucked tight and forward, arms thrown up
        ],
    ),
    # Redesigned per ChatGPT's P1 ranking ("still lacks strong salto logic;
    # body/limbs need a clearer tuck/rotation/follow-through"): the old
    # version only ever leaned the torso (-15 to -40 degrees) while the legs
    # tucked -- torso alone can't sell a somersault since it's a small
    # fraction of a full rotation, and torso's own art isn't designed to
    # rotate independently far past that without the neck/hip seams
    # visibly gapping. The rig has a "root" joint (see rig_config.py) that
    # sits above the whole chain purely for this kind of whole-body
    # rotation -- rotating IT instead spins the entire character rigidly
    # (torso, head, hair, limbs all inherit it via the parent chain) for an
    # actual visible flip, while the existing leg tuck still sells "tucked
    # into a ball" on top of that rotation. Spins a full -340 degrees across
    # the 3 keyframes (not a full -360) so the landing frame is caught
    # slightly before completing the rotation, reading as "about to land"
    # rather than a perfect loop back to the start pose.
    # root_offset here is NOT a crouch-style ground offset -- Blender
    # composes an object's transform as world = T + R(local), i.e. rotation
    # always pivots around the PARENT's own local origin (root's local
    # origin sits at the character's feet, z=0) and translation (root_offset)
    # just slides the whole already-rotated result afterward. A first attempt
    # using a flat root_offset=(0,0,1.0) tried to "move the pivot" but
    # actually just translated the whole spinning body up by a constant 1.0,
    # producing a rotation that still pivoted around the feet -- confirmed by
    # a fully blank -180-degree keyframe (the head swung below the visible
    # frame) and a head clipped off-frame even at the barely-rotated 0-degree
    # keyframe. Rotating around an arbitrary point C_pivot requires a
    # DIFFERENT root_offset at every keyframe: world = C_pivot + R(theta) *
    # (local - C_pivot), which for a joint offset directly at C_pivot
    # (pelvis sits at local (0,0,1.0), chosen as the pivot -- roughly the
    # body's center of mass) simplifies to root_offset(theta) = C_pivot -
    # R(theta) * C_pivot = (-sin(theta), 0, 1.0 - cos(theta)) for a pivot
    # height of 1.0. Computed numerically per keyframe below; this keeps the
    # pelvis fixed at world (0,0,1.0) at every rotation angle, so the
    # character spins in place instead of cartwheeling through the floor.
    #
    # A second attempt that only computed this offset at 3 sparse keyframes
    # (0/2/4) still drifted badly on the RENDERED in-between frames (1, 3):
    # Blender's F-curve interpolates rotation and location as independent
    # curves, but the pivot-preserving offset is a NONLINEAR (sin/cos)
    # function of the rotation angle -- linearly interpolating location
    # while the angle sweeps 160 degrees between keyframes diverges sharply
    # from the true curve partway through (frame 1 came out with the head
    # cropped off-frame again). Fixed by keyframing every rendered frame
    # (0-4) individually, each with its own exact rotation angle and exactly
    # matching offset, plus linearly-interpolated pose values so the leg
    # tuck/torso lean still progress smoothly across the added frames.
    "double_jump_salto": AnimationDef(
        name="double_jump_salto", fps=12, loop=False,
        keyframes=[
            Keyframe(0, {
                "root": (0, -20, 0),
                "torso": (0, -15, 0),
                "thigh_front": (0, 30, 0), "shin_front": (0, 55, 0),
                "thigh_back": (0, 30, 0), "shin_back": (0, 55, 0),
            }, root_offset=(0.342, 0.0, 0.0603)),
            Keyframe(1, {
                "root": (0, -90, 0),
                "torso": (0, -27.5, 0),
                "thigh_front": (0, 37.5, 0), "shin_front": (0, 62.5, 0),
                "thigh_back": (0, 37.5, 0), "shin_back": (0, 62.5, 0),
            }, root_offset=(1.0, 0.0, 1.0)),
            Keyframe(2, {
                "root": (0, -180, 0),
                "torso": (0, -40, 0),
                "thigh_front": (0, 45, 0), "shin_front": (0, 70, 0),
                "thigh_back": (0, 45, 0), "shin_back": (0, 70, 0),
            }, root_offset=(0.0, 0.0, 2.0)),  # tightest tuck, mid-salto, upside-down at the rotation's halfway point
            Keyframe(3, {
                "root": (0, -260, 0),
                "torso": (0, -27.5, 0),
                "thigh_front": (0, 30, 0), "shin_front": (0, 45, 0),
                "thigh_back": (0, 30, 0), "shin_back": (0, 45, 0),
            }, root_offset=(-0.9848, 0.0, 1.1736)),
            Keyframe(4, {
                "root": (0, -340, 0),
                "torso": (0, -15, 0),
                "thigh_front": (0, 15, 0), "shin_front": (0, 20, 0),
                "thigh_back": (0, 15, 0), "shin_back": (0, 20, 0),
            }, root_offset=(-0.342, 0.0, 0.0603)),  # opening back up, near-complete rotation, about to land
        ],
    ),
    # Thigh/shin angles picked by solving for the shin rotation that brings
    # the ankle back to roughly directly under the hip given the thigh's
    # forward bend (ankle_x = 0.48*sin(thigh) + 0.40*sin(thigh+shin) = 0) --
    # a first attempt that let shin under- or over-cancel thigh left the
    # ankle well forward or behind of the hip, which combined with the
    # torso's own forward lean made the whole silhouette (head to feet)
    # read as one continuous rigid diagonal line instead of a bend at the
    # hip. root_offset is the matching hip-to-ankle vertical shortening
    # (standing straight-leg drop 0.88 minus the bent-leg drop) needed to
    # keep the feet planted at the same ground line as standing.
    # Angles below came from an external visual review (ChatGPT, comparing a
    # render of the previous attempt against the HD reference crouch_idle_000
    # frame) after two rounds of self-directed trig tuning both still read as
    # "reclining diagonally" rather than a crouch despite being kinematically
    # correct (feet pixel-verified at the right ground position). Two things
    # were actually wrong, not just imprecise:
    #  1. torso's sign convention here is OPPOSITE thigh's: a negative torso
    #     value (previously used assuming it meant "forward lean", copying
    #     thigh's convention) actually pitches the torso BACKWARD. Confirmed
    #     by the external review reading the old render as a "backward
    #     recline" -- this file's other torso uses (idle's small +2, punch's
    #     small -8/-10/-18) never exposed this because the magnitude was too
    #     small to visibly matter; a static held crouch pose is exactly the
    #     case where a moderate-magnitude sign error becomes obvious.
    #  2. the knee bend was far too shallow (~20-40 degrees of flexion) for a
    #     crouch, which wants ~80-110 degrees -- thighs need to swing much
    #     further (front thigh close to horizontal) with the shin counter-
    #     rotating sharply, not just a modest forward tilt.
    # Front/back legs are deliberately asymmetric (front knee high and
    # forward, back leg tucked under/back) rather than a symmetric squat,
    # matching the reference; both legs' shin compensation was solved (see
    # HOW_TO_GENERATE_V2_SPRITES.md) to land at the SAME ankle height so one
    # shared root_offset plants both feet instead of one floating.
    # Kneeling-lunge crouch, per ChatGPT's angle correction after my own
    # two self-directed attempts both tangled the legs (see
    # HOW_TO_GENERATE_V2_SPRITES.md): front shin must stay near-VERTICAL in
    # world space (world angle = thigh+shin ~= 0-10 deg) so the planted
    # front leg reads as a 90 deg lunge instead of collapsing backward under
    # the body, and the back thigh needs real negative (backward) sweep
    # (~-30 deg, not near 0) so the rear knee clears the pelvis instead of
    # tangling with the front leg. root_offset derived by forward-kinematics
    # (front ankle should land at the same ground height as standing idle).
    # Leg angles negated from ChatGPT's original numbers -- confirmed
    # in-render that its stated convention (positive thigh_front = knee
    # toward +X/forward) was backward for THIS rig: the lunge leg planted
    # screen-left while the character faces +X/right. Negating every
    # thigh/shin value mirrors the whole leg pose across the vertical axis
    # (world_angle = thigh+shin, so negating both terms negates the total),
    # which flips the silhouette without changing which leg (front/back) is
    # doing what, since the thigh_front/thigh_back joints' own +X/-X rest
    # offsets (see rig_config.py) already encode which side is which. torso
    # is untouched -- only the legs were reported backward.
    "crouch_idle": AnimationDef(
        name="crouch_idle", fps=6, loop=True,
        keyframes=[
            Keyframe(0, {
                "torso": (0, 7, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 58, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 20, 0),
                "hair_back": (0, 3, 0),
            }, root_offset=(0.0, 0.0, -0.24)),
            Keyframe(8, {
                "torso": (0, 5, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 57, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
                "hair_back": (0, -3, 0),
            }, root_offset=(0.0, 0.0, -0.235)),  # subtle sway, same crouch depth
            Keyframe(16, {
                "torso": (0, 7, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 58, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 20, 0),
                "hair_back": (0, 3, 0),
            }, root_offset=(0.0, 0.0, -0.24)),  # == frame 0, closes the loop
        ],
    ),
    # Same kneeling-lunge base as crouch_idle, alternating which leg leads
    # each half-step (front-leads / back-leads), plus a "passing" mid-stride
    # frame (ChatGPT's suggestion) where both legs pull toward a shallower,
    # more symmetric bend -- without it, interpolating straight between the
    # front-leads and back-leads extremes makes the legs visibly cross/swap
    # through each other mid-transition instead of passing cleanly.
    "crouch_walk": AnimationDef(
        name="crouch_walk", fps=8, loop=True,
        keyframes=[
            Keyframe(0, {
                "torso": (0, 6, 0),
                "thigh_front": (0, -55, 0), "shin_front": (0, 54, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
            }, root_offset=(0.0, 0.0, -0.24)),  # front leg leads
            Keyframe(3, {
                "torso": (0, 6, 0),
                "thigh_front": (0, -35, 0), "shin_front": (0, 65, 0),
                "thigh_back": (0, -15, 0), "shin_back": (0, 70, 0),
            }, root_offset=(0.0, 0.0, -0.19)),  # passing, shallower to avoid leg crossing
            Keyframe(6, {
                "torso": (0, 6, 0),
                "thigh_front": (0, 28, 0), "shin_front": (0, 19, 0),
                "thigh_back": (0, -55, 0), "shin_back": (0, 54, 0),
            }, root_offset=(0.0, 0.0, -0.24)),  # back leg leads
            Keyframe(9, {
                "torso": (0, 6, 0),
                "thigh_front": (0, -35, 0), "shin_front": (0, 65, 0),
                "thigh_back": (0, -15, 0), "shin_back": (0, 70, 0),
            }, root_offset=(0.0, 0.0, -0.19)),  # passing again
            Keyframe(12, {
                "torso": (0, 6, 0),
                "thigh_front": (0, -55, 0), "shin_front": (0, 54, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
            }, root_offset=(0.0, 0.0, -0.24)),  # == frame 0, closes the loop
        ],
    ),
    # Same IK-solved straight-line approach as punch_mid (see its comment),
    # targeting head height instead of chest height.
    # Active frame re-targeted per direct user feedback against an in-game
    # screenshot ("le coup de poing visage doit toucher le visage"): absolute-
    # position check (shoulder sits at world Z=1.53, hand_z = shoulder_z -
    # upper_arm_len*cos(t1) - forearm_len*cos(t1+t2) - hand_len*cos(t1+t2))
    # showed the old -56/-64 combo only reached world Z=1.57, barely above
    # the shoulder and well short of the face (~1.75-1.8). The new -105/0
    # (a much higher raise, fully straight arm) reaches Z=1.74 -- actually
    # at face height instead of just "aimed toward" it.
    "punch_high": AnimationDef(
        name="punch_high", fps=15, loop=False,
        keyframes=[
            Keyframe(0, {"upper_arm_front": (0, 10, 0)}, hand_front_pose="open"),
            Keyframe(2, {"upper_arm_front": (0, -4, 0), "forearm_front": (0, -171, 0)}, hand_front_pose="fist"),  # chamber, raised near shoulder
            Keyframe(4, {"upper_arm_front": (0, -105, 0), "forearm_front": (0, 0, 0)}, hand_front_pose="fist"),  # active, straight punch to face height
            Keyframe(7, {"upper_arm_front": (0, -28, 0), "forearm_front": (0, -135, 0)}, hand_front_pose="fist"),  # recovery
            Keyframe(9, {}, hand_front_pose="open"),
        ],
    ),
    # Same IK-solved straight-line approach, targeting stomach height.
    # Active frame's target height dropped further per ChatGPT's P1 ranking
    # ("not distinct enough from mid; lower the attack line") -- forward-
    # kinematics check (same chain math as the leg fixes) showed the old
    # -35/-48 combo landed the fist ~0.48 BU above a hanging arm's rest
    # height, only ~0.19 BU below punch_mid's own ~0.66 BU -- not much
    # separation on a ~1.9 BU tall character. The new -20/-35 combo (less
    # shoulder lift, less forearm unfold) drops the target to ~0.22 BU above
    # rest -- close to hip/stomach height and now ~0.44 BU below punch_mid,
    # more than double the old gap.
    "punch_low": AnimationDef(
        name="punch_low", fps=14, loop=False,
        keyframes=[
            Keyframe(0, {"upper_arm_front": (0, 10, 0)}, hand_front_pose="open"),
            Keyframe(2, {"upper_arm_front": (0, 35, 0), "forearm_front": (0, -119, 0)}, hand_front_pose="fist"),  # chamber, low
            Keyframe(4, {"upper_arm_front": (0, -20, 0), "forearm_front": (0, -35, 0), "torso": (0, -12, 0)}, hand_front_pose="fist"),  # active, body punch
            Keyframe(7, {"upper_arm_front": (0, 0, 0), "forearm_front": (0, -111, 0)}, hand_front_pose="fist"),  # recovery
            Keyframe(9, {}, hand_front_pose="open"),
        ],
    ),
    # Kick angles are similarly mirrored (negated) from their original
    # hand-picked values -- same "was extending backward, not forward" bug
    # as the punches above, confirmed visually (the kicking leg swung
    # screen-left while the character faces screen-right).
    # Active frame re-targeted per direct user feedback against an in-game
    # screenshot ("le coup de pied moyen doit toucher le ventre"):
    # absolute-position check (hip sits at world Z=1.0, foot_z = hip_z -
    # thigh_len*cos(t1) - shin_len*cos(t1+t2)) showed the old -55/-10 combo
    # only reached world Z=0.56 -- well below the belt, nowhere near the
    # stomach (~1.1-1.25). A near-straight leg at thigh=-100 reaches Z=1.15,
    # genuinely stomach height.
    "kick_mid": AnimationDef(
        name="kick_mid", fps=13, loop=False,
        keyframes=[
            Keyframe(0, {}),
            Keyframe(2, {"thigh_front": (0, 50, 0), "shin_front": (0, -70, 0)}),  # chamber, knee up
            Keyframe(4, {"thigh_front": (0, -100, 0), "shin_front": (0, 0, 0), "torso": (0, -10, 0)}),  # active, extended to stomach height
            Keyframe(6, {"thigh_front": (0, -60, 0), "shin_front": (0, -20, 0)}),
            Keyframe(9, {}),  # recovery back to idle-ish
        ],
    ),
    "kick_high": AnimationDef(
        name="kick_high", fps=13, loop=False,
        keyframes=[
            Keyframe(0, {}),
            Keyframe(2, {"thigh_front": (0, 70, 0), "shin_front": (0, -80, 0)}),  # chamber, knee high
            # active, re-targeted a second time per direct user feedback against an
            # in-game screenshot ("le coup de pied visage doit toucher le visage"):
            # the earlier -85/0 fix only reached hip height (world Z~0.92) --
            # ChatGPT's read of "controlled high side kick, good enough to lock" was
            # graded against the OLD -75/-15 baseline, but the user's actual bar is
            # literal face contact (~Z 1.75-1.8), which a hip-pivoted 2-link leg
            # (0.48+0.40=0.88 BU reach from a hip at Z=1.0) can only approach by
            # swinging well PAST horizontal, toward vertical. thigh=-125 (shin still
            # fully straight) reaches world Z=1.50 -- upper chest/lower face, a real
            # head-height kick without going all the way to a physically-extreme
            # vertical needle kick. root_offset carries over unchanged (still needed
            # for the same right-edge clearance as before -- the extra height doesn't
            # reduce the forward reach that was causing the clipping).
            Keyframe(4, {"thigh_front": (0, -125, 0), "shin_front": (0, 0, 0), "torso": (0, -18, 0)}, root_offset=(-0.15, 0.0, 0.0)),  # active, face-height extension
            Keyframe(6, {"thigh_front": (0, -60, 0), "shin_front": (0, -25, 0)}),
            Keyframe(9, {}),
        ],
    ),
    "kick_low": AnimationDef(
        name="kick_low", fps=12, loop=False,
        keyframes=[
            Keyframe(0, {}),
            Keyframe(2, {"thigh_front": (0, 25, 0), "shin_front": (0, -45, 0)}),  # chamber, shin level
            Keyframe(4, {"thigh_front": (0, -30, 0), "shin_front": (0, -5, 0)}),  # active, low sweep
            Keyframe(6, {"thigh_front": (0, -15, 0), "shin_front": (0, -15, 0)}),
            Keyframe(8, {}),
        ],
    ),
    # Same corrected crouch base as crouch_idle (see its comment) plus an
    # arm/leg strike layered on top.
    # Active frame redesigned per ChatGPT review: the old active pose
    # (upper_arm_front 10->50, forearm 0->10) barely moved -- only ~40deg of
    # swing total, versus standing punch_mid's ~90deg chamber-to-active
    # swing -- so the silhouette read as "stance-led" rather than
    # punch-led. Now uses the same forward-reach convention as the standing
    # punches (negative = forward extension) with comparable magnitude.
    "crouch_punch_low": AnimationDef(
        name="crouch_punch_low", fps=14, loop=False,
        keyframes=[
            Keyframe(0, {
                "torso": (0, 7, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 58, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
                "upper_arm_front": (0, 20, 0),
            }, root_offset=(0.0, 0.0, -0.24), hand_front_pose="open"),
            Keyframe(2, {
                "torso": (0, 3, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 58, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
                "upper_arm_front": (0, -50, 0), "forearm_front": (0, -40, 0),
            }, root_offset=(0.0, 0.0, -0.24), hand_front_pose="fist"),  # active, strong forward thrust
            Keyframe(5, {
                "torso": (0, 7, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 58, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
            }, root_offset=(0.0, 0.0, -0.24), hand_front_pose="open"),  # recovery, back to crouch_idle
        ],
    ),
    # Base crouch on the BACK leg only (it stays in the tucked crouch_idle
    # role throughout); the FRONT leg's thigh/shin are overridden by the low
    # sweeping kick itself instead of the crouch's "high forward knee" role,
    # since both can't own the front leg at once.
    "crouch_kick_low": AnimationDef(
        name="crouch_kick_low", fps=12, loop=False,
        keyframes=[
            Keyframe(0, {
                "torso": (0, 7, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 58, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
            }, root_offset=(0.0, 0.0, -0.24)),
            Keyframe(2, {
                "torso": (0, 5, 0),
                "thigh_front": (0, -45, 0), "shin_front": (0, 0, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
            }, root_offset=(0.0, 0.0, -0.24)),  # active, low sweeping kick -- ChatGPT's P0 review flagged the
            # previous values (thigh=-15, shin=-70) as reading "airborne / jump-like rather than a grounded low
            # kick": that combo swings the SHIN's absolute angle to ~-85deg (near horizontal, hip height), which
            # actually LIFTS the foot ~0.14 BU above its crouch-pose height despite looking like a big sweep on
            # paper. Solved with forward-kinematics math (not trial and error): foot_z = -thigh_len*cos(theta1) -
            # shin_len*cos(theta1+theta2) relative to the hip: solving for the (theta1, theta2) pair that keeps
            # foot_z equal to the base crouch's foot_z while maximizing forward reach lands near
            # (thigh=-45, shin=0) -- a nearly straight leg swept forward at the hip, staying at ~ground height
            # instead of arcing upward, while shin=0 also reads as a cleaner straight-leg sweep silhouette.
            Keyframe(5, {
                "torso": (0, 7, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 58, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
            }, root_offset=(0.0, 0.0, -0.24)),  # recovery, back to crouch_idle
        ],
    ),
    # Redesigned per ChatGPT review: the old values (-40/-30) left the
    # forearms reaching outward instead of covering the head -- upper arms
    # now lift much higher (elbows up near shoulder/head height) and the
    # forearms fold sharply back so the fists land near the head, giving a
    # compact crossed-guard silhouette instead of "arms held out in space".
    "block_high": AnimationDef(
        name="block_high", fps=6, loop=True,
        keyframes=[
            Keyframe(0, {
                "upper_arm_front": (0, -70, 0), "forearm_front": (0, -110, 0),
                "upper_arm_back": (0, -60, 0), "forearm_back": (0, -95, 0),
            }),
            Keyframe(10, {
                "upper_arm_front": (0, -72, 0), "forearm_front": (0, -110, 0),
                "upper_arm_back": (0, -62, 0), "forearm_back": (0, -95, 0),
            }),  # tiny sway so it doesn't read as a frozen frame
            Keyframe(20, {
                "upper_arm_front": (0, -70, 0), "forearm_front": (0, -110, 0),
                "upper_arm_back": (0, -60, 0), "forearm_back": (0, -95, 0),
            }),
        ],
    ),
    # Redesigned per ChatGPT review: old values (-5/-20) were too close to
    # neutral idle to read as a distinct guard at all. Bigger fold brings
    # both fists together in front of the chest/centerline.
    "block_mid": AnimationDef(
        name="block_mid", fps=6, loop=True,
        keyframes=[
            Keyframe(0, {
                "upper_arm_front": (0, 20, 0), "forearm_front": (0, -140, 0),
                "upper_arm_back": (0, 16, 0), "forearm_back": (0, -125, 0),
            }),
            Keyframe(10, {
                "upper_arm_front": (0, 22, 0), "forearm_front": (0, -140, 0),
                "upper_arm_back": (0, 18, 0), "forearm_back": (0, -125, 0),
            }),
            Keyframe(20, {
                "upper_arm_front": (0, 20, 0), "forearm_front": (0, -140, 0),
                "upper_arm_back": (0, 16, 0), "forearm_back": (0, -125, 0),
            }),
        ],
    ),
    # Same corrected crouch base as crouch_idle (see its comment). Arm fold
    # deepened per ChatGPT review -- old values (15/-15) barely bent the
    # elbow, reading as passive hanging rather than actively guarding the
    # low line; both arms now fold down toward the legs/shins.
    # Legs/torso/root_offset reuse crouch_idle's exact values (already
    # validated as reading as a settled crouch, not a lunge) -- ChatGPT's P0
    # batch-2 review flagged block_low as reading like "a low evasive lunge"
    # rather than a held guard despite that, and pinned the cause on the
    # arms: "not clearly presenting a low-line shield". Deepened the fold
    # (35/-65 -> 45/-115ish) using the same chamber logic that worked for
    # block_mid, just aimed lower so the fists tuck near the hip/thigh
    # instead of the ribs, presenting a barrier across the low line.
    "block_low": AnimationDef(
        name="block_low", fps=6, loop=True,
        keyframes=[
            Keyframe(0, {
                "torso": (0, 7, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 58, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
                "upper_arm_front": (0, 45, 0), "forearm_front": (0, -115, 0),
                "upper_arm_back": (0, 40, 0), "forearm_back": (0, -100, 0),
            }, root_offset=(0.0, 0.0, -0.24)),
            Keyframe(10, {
                "torso": (0, 5, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 58, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
                "upper_arm_front": (0, 43, 0), "forearm_front": (0, -115, 0),
                "upper_arm_back": (0, 38, 0), "forearm_back": (0, -100, 0),
            }, root_offset=(0.0, 0.0, -0.24)),
            Keyframe(20, {
                "torso": (0, 7, 0),
                "thigh_front": (0, -60, 0), "shin_front": (0, 58, 0),
                "thigh_back": (0, 28, 0), "shin_back": (0, 19, 0),
                "upper_arm_front": (0, 45, 0), "forearm_front": (0, -115, 0),
                "upper_arm_back": (0, 40, 0), "forearm_back": (0, -100, 0),
            }, root_offset=(0.0, 0.0, -0.24)),
        ],
    ),
    # Asymmetric arm reaction added per ChatGPT's P1 ranking ("could use
    # sharper asymmetry/recoil"): both arms flailing identically read as too
    # clean/choreographed for a hit reaction -- a real impact throws the
    # limbs unevenly. Front arm (closer to camera, presumably nearer the
    # point of impact) flings up further than the back arm, and a forearm
    # fling was added on the front arm only.
    "hitstun": AnimationDef(
        name="hitstun", fps=8, loop=False,
        keyframes=[
            Keyframe(0, {
                "torso": (0, 22, 0), "head": (0, 18, 0),
                "upper_arm_front": (0, 38, 0), "forearm_front": (0, -25, 0),
                "upper_arm_back": (0, 18, 0),
            }),  # snapped back by the hit, front arm flung up harder than the back
            Keyframe(3, {
                "torso": (0, 10, 0), "head": (0, 8, 0),
                "upper_arm_front": (0, 15, 0), "forearm_front": (0, -8, 0),
                "upper_arm_back": (0, 15, 0),
            }),  # settling back
        ],
    ),
    "ko": AnimationDef(
        name="ko", fps=7, loop=False,
        keyframes=[
            Keyframe(0, {"torso": (0, 20, 0), "head": (0, 12, 0)}),  # staggered
            Keyframe(3, {
                "torso": (0, 35, 0), "head": (0, 18, 0),
                "thigh_front": (0, -12, 0), "thigh_back": (0, -10, 0),
            }, root_offset=(0.0, 0.0, -0.08)),  # knees buckling
            Keyframe(6, {
                "torso": (0, 48, 0), "head": (0, 22, 0),
                "thigh_front": (0, -18, 0), "thigh_back": (0, -15, 0),
            }, root_offset=(0.0, 0.0, -0.16)),  # settled, slumped forward
            # Known rough edge (see blender/README.md): the rig only rotates
            # joints, it doesn't translate the pelvis forward as the torso
            # pitches down, so this settles into a slump rather than lying
            # fully supine -- kept deliberately modest (torso capped well
            # short of 90 degrees) since a larger pitch swings the head/arms
            # silhouette far enough from the hip to read as disconnected
            # body parts rather than a collapse. Acceptable first pass per
            # the pipeline's own scope (a real lay-flat collapse needs
            # pelvis translation, not just rotation, matching the same
            # limitation crouch worked around).
        ],
    ),
    # Redesigned per ChatGPT review: the old fold (20-25/30-35, both arms
    # nearly symmetric and barely bent) read as "one arm drawn backward" /
    # an ambiguous windup rather than gathering energy. Uses the same
    # chamber logic as punch_mid's fist-tucked-near-ribs pose (positive
    # upper_arm + large negative forearm fold) on BOTH arms so the hands
    # visibly converge in front of the torso -- a clear single focal point
    # to read as "charging", instead of two independently-drifting limbs.
    "ranged_charge": AnimationDef(
        name="ranged_charge", fps=10, loop=False,
        keyframes=[
            Keyframe(0, {
                "upper_arm_front": (0, 25, 0), "forearm_front": (0, -90, 0),
                "upper_arm_back": (0, 25, 0), "forearm_back": (0, -90, 0),
                "torso": (0, 8, 0),
            }),  # both hands cupped together in front of the torso
            Keyframe(4, {
                "upper_arm_front": (0, 28, 0), "forearm_front": (0, -95, 0),
                "upper_arm_back": (0, 28, 0), "forearm_back": (0, -95, 0),
                "torso": (0, 10, 0),
            }),  # tiny charging sway, hands stay together
        ],
    ),
    # Startup now matches ranged_charge's cupped-hands pose (visual
    # continuity from charge into throw); release keeps the old strong
    # forward thrust (projectile spawns here), and a follow-through frame
    # was added since a single release frame with no aftermath read as
    # "presenting/pointing" rather than a committed throw.
    # Release/follow-through torso strengthened and re-signed per ChatGPT's
    # P1 ranking ("readable... but still a bit soft/polite; needs stronger
    # follow-through") and the dash sign-convention fix: torso's negative
    # direction pitches BACKWARD on this rig, so the old release/follow-
    # through (-10/-5) was leaning slightly away from the throw, just like
    # dash's original bug -- masked here by the arm's own forward extension
    # dominating the read (same reason punch/kick actives got away with a
    # small negative torso), but not helping the "soft" complaint either.
    # Flipped both to positive (forward commit) and pushed the magnitude up,
    # plus fully extended the forearm at release instead of leaving it
    # slightly folded, for a more decisive, less "presenting" throw.
    "ranged_throw": AnimationDef(
        name="ranged_throw", fps=12, loop=False,
        keyframes=[
            Keyframe(0, {
                "upper_arm_front": (0, 25, 0), "forearm_front": (0, -90, 0),
                "torso": (0, 8, 0),
            }),  # startup, same as ranged_charge's held pose
            Keyframe(3, {
                "upper_arm_front": (0, -80, 0), "forearm_front": (0, 0, 0),
                "torso": (0, 15, 0),
            }),  # release, arm thrust forward (projectile spawns here, see CONTRACT.md's projectile_spawn_frame)
            Keyframe(5, {
                "upper_arm_front": (0, -70, 0), "forearm_front": (0, 10, 0),
                "torso": (0, 8, 0),
            }),  # follow-through, arm relaxing past full extension
        ],
    ),

    # Not one of CONTRACT.md's 20 engine keys -- a 21st, optional pose only
    # used when Renderer.animation_key() finds "dash" in a pack's animations
    # (see renderer.py and CONTRACT.md's dash note). LD/HD lack this key and
    # keep falling back to "walk". A low forward lean with the lead leg
    # extended and low, distinct from walk's upright scissor-step, so a dash
    # actually reads differently from a fast walk instead of just reusing it.
    # Redesigned per ChatGPT's P1 ranking ("still reads more like falling/
    # leaning than driving forward"): the leg angles here were never run
    # through the "negate every leg rotation" sign-convention fix this
    # session applied to the crouch family (see crouch_idle/crouch_walk's
    # history) -- thigh_front=+35 actually swings the LEAD leg BACKWARD
    # (negative = forward, established and validated via kick_mid/kick_low's
    # active frames), and thigh_back=-30 swings the TRAIL leg backward too
    # instead of extending it behind for a push-off. Both legs ended up
    # bunched near the body facing the wrong way, which reads as a stumble,
    # not a stride. Negated every thigh/shin value to actually plant a
    # forward-reaching lead leg and a backward-extended push-off trail leg.
    # Also gave the arms real counter-swing (front-arm-back /
    # back-arm-forward, flipping upper_arm_back negative) instead of both
    # arms drifting the same direction, which read as static/lifeless.
    # Second pass per ChatGPT's P1 follow-up: the leg-direction fix cleared
    # the "clearly broken" read, but it still felt like "a leaning/gliding
    # stride" rather than "a decisive forward burst" -- deepened the
    # forward lean (-18/-20 -> -26/-28) and stride reach on both legs, and
    # added a small downward root_offset to compress the stance lower to
    # the ground (a sprinter's low drive posture, not an upright glide).
    # Third pass: ChatGPT's round-2 read was that the chest/head STILL
    # leaned backward despite the legs clearly driving forward -- this
    # matches a sign-convention risk flagged in an old comment elsewhere in
    # this file (see the abandoned kneeling-lunge crouch notes): torso's
    # negative direction pitches it BACKWARD, not forward. Punch/kick
    # actives got away with a small negative torso (-8 to -18) because the
    # dominant read there is the extending limb, and a slight backward
    # counter-lean during a strike even looks natural (real strikers
    # counterbalance a big kick that way) -- but a SUSTAINED, LARGE
    # negative torso on a driving dash has no extending limb to mask it,
    # so the backward pitch reads as exactly what it is. Flipped torso
    # positive (matching crouch_idle's validated forward-lean convention)
    # and replaced the straight-armed reach with a bent-elbow pumping
    # cycle (forearm fold + closed fists) for an athletic sprint drive
    # instead of open hands reaching forward.
    # Back (trailing) leg's shin sign fixed per direct user feedback ("même
    # problème avec le dash, les genoux partent dans la mauvaise
    # direction"), same root cause as jump's tuck: shin_back=-55 relative to
    # thigh_back=+40 is an OPPOSITE-sign fold, the same "chamber" shape
    # kick_mid's windup uses (thigh lifts, shin reverses sharply) -- correct
    # for curling a heel up toward the glute before a kick, wrong for a
    # trailing push-off leg, which should keep swinging in the SAME
    # rotational sense as the thigh (like the front leg's own thigh=-45/
    # shin=-15, both negative, continuing the same direction). FK check
    # confirms the old opposite-sign version left the trailing foot low and
    # only slightly behind the hip (z=-0.75, x=-0.21) -- barely swept back at
    # all -- while the same-sign fix lifts it to a proper sprint-stride
    # trail (z=-0.60, x=-0.64), symmetric with the front leg's own reach.
    "dash": AnimationDef(
        name="dash", fps=12, loop=True,
        keyframes=[
            Keyframe(0, {
                "torso": (0, 25, 0),
                "thigh_front": (0, -45, 0), "shin_front": (0, -15, 0),
                "thigh_back": (0, 40, 0), "shin_back": (0, 15, 0),
                "upper_arm_front": (0, 45, 0), "forearm_front": (0, -75, 0),
                "upper_arm_back": (0, -35, 0), "forearm_back": (0, -70, 0),
            }, root_offset=(0.0, 0.0, -0.08), hand_front_pose="fist"),  # lead leg extended low and forward, trail leg swept back, arms pumping
            Keyframe(5, {
                "torso": (0, 22, 0),
                "thigh_front": (0, -30, 0), "shin_front": (0, -25, 0),
                "thigh_back": (0, 22, 0), "shin_back": (0, 8, 0),
                "upper_arm_front": (0, 15, 0), "forearm_front": (0, -65, 0),
                "upper_arm_back": (0, 15, 0), "forearm_back": (0, -65, 0),
            }, root_offset=(0.0, 0.0, -0.05), hand_front_pose="fist"),  # passing pose, legs under the body, arms crossing through neutral
            Keyframe(10, {
                "torso": (0, 25, 0),
                "thigh_front": (0, -45, 0), "shin_front": (0, -15, 0),
                "thigh_back": (0, 40, 0), "shin_back": (0, 15, 0),
                "upper_arm_front": (0, 45, 0), "forearm_front": (0, -75, 0),
                "upper_arm_back": (0, -35, 0), "forearm_back": (0, -70, 0),
            }, root_offset=(0.0, 0.0, -0.08), hand_front_pose="fist"),  # == frame 0, closes the loop
        ],
    ),
}
