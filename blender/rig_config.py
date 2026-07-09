"""Default humanoid joint chain shared by both fighters (2D cutout rig,
option A from retro_fighter_v2_blender_sprite_pipeline.md 7.2 -- each part
is a flat textured plane, rigidly attached to a joint, no mesh deformation).

Implementation note (deviation from the guide): rather than a Blender
Armature/Bone datablock, joints are plain Empty objects in a parent chain.
Blender's native "parent to Bone" attachment requires manually computing
`matrix_parent_inverse` correctly or objects silently jump to the wrong
place -- fragile to script blind, and this project has no interactive
Blender session to eyeball-fix it in. Plain object parenting has none of
that: a child's transform is always correctly relative to its parent by
construction. Since this rig only ever needs rigid per-limb rotation (no
mesh skinning/deformation -- that's the guide's "option B", explicitly a
later nice-to-have), an Empty chain gives the exact same posable result as
an Armature would for option A, with much less fragile code.

Units are Blender units (BU), not pixels: feet at z=0, standing character
~1.9 BU tall, character facing +X (right), camera looks down +Y from -Y
(see pipeline.py). `offset` is the translation from the PARENT joint's
origin to this joint's origin, expressed in the parent's local space (so it
naturally follows the parent's rotation once posed -- that's what makes
this forward kinematics). `length` is only used to size the part plane
attached at this joint (see parts_spec.py): the plane extends `length`
along the joint's local -Z from its origin.

Every joint rotates only around its local Y axis (the camera's view axis)
-- this is a 2D side-view rig, not a general 3D one, so in-plane swinging
is all that's ever needed or supported.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Joint:
    name: str
    parent: str | None
    offset: tuple[float, float, float]
    length: float
    # +1: the attached part extends UP (+Z) from this joint's origin (the
    # spine: pelvis/torso/neck/head, where offsets to children point up).
    # -1: the part extends DOWN (-Z), away from the body (every limb
    # segment: shoulder->elbow->wrist, hip->knee->ankle, all offset down).
    direction: float = -1.0


CHARACTER_HEIGHT = 1.9  # BU, feet (z=0) to top of head

JOINTS: list[Joint] = [
    Joint("root", None, (0.0, 0.0, 0.0), 0.0),
    # pelvis stays a purely structural (never-rotated, except root_offset
    # translation) anchor: both thighs and torso branch from it. torso's
    # offset is (0,0,0) -- same origin as pelvis, not above it -- because
    # torso's art now covers the WHOLE shoulders-to-buttocks block in one
    # rigid piece (see parts_spec.py's torso comment): there's no animation
    # that bends the spine independently from the hips, so a separate
    # "pelvis" visual part just meant an extra seam for no articulation
    # benefit. length=0.55 (was 0.40) absorbs what used to be the pelvis
    # part's own 0.15 span, since torso's plane now has to reach all the way
    # down to the same origin the thighs attach to.
    Joint("pelvis", "root", (0.0, 0.0, 1.00), 0.15, direction=1.0),
    Joint("torso", "pelvis", (0.0, 0.0, 0.0), 0.55, direction=1.0),
    Joint("neck", "torso", (0.0, 0.0, 0.55), 0.07, direction=1.0),
    Joint("head", "neck", (0.0, 0.0, 0.07), 0.28, direction=1.0),
    # Dedicated pivot for hair_back (the ponytail), same origin as head
    # (offset (0,0,0) -- it's not a separate physical attachment point, just
    # an independent rotation channel) so the ponytail can sway on its own
    # animation curve (a light idle wind motion) without that motion also
    # rotating the head/face art, and without the head's own rotation
    # (turning to face a strike, etc.) needing to double as the hair's only
    # source of motion. length=0.28 matches head's own, purely to keep the
    # existing plane-size math (parts_spec's coverage/anchor_offset_z) it
    # was tuned against unchanged when this joint replaced "head" as
    # hair_back's attachment point.
    Joint("hair_back", "head", (0.0, 0.0, 0.0), 0.28, direction=1.0),

    # Shoulder offset z bumped 0.35 -> 0.50 to compensate for torso's origin
    # moving down by 0.15 (see above) -- keeps the shoulder joints at the
    # same physical height as before, since only the torso's own pivot/plane
    # moved, not the actual character proportions.
    # x/z further adjusted 0.20/0.50 -> 0.17/0.53 per ChatGPT's review of
    # the rendered set: the shoulder attachment read as "detached puppet
    # arm" / "plugged into a hole" in guard and ranged poses -- moving the
    # arm root up and inward seats it closer to the torso's actual armhole
    # instead of floating outboard of it.
    Joint("upper_arm_front", "torso", (0.17, 0.05, 0.53), 0.35),
    Joint("forearm_front", "upper_arm_front", (0.0, 0.0, -0.35), 0.30),
    Joint("hand_front", "forearm_front", (0.0, 0.0, -0.30), 0.17),

    Joint("upper_arm_back", "torso", (-0.17, -0.05, 0.53), 0.35),
    Joint("forearm_back", "upper_arm_back", (0.0, 0.0, -0.35), 0.30),
    Joint("hand_back", "forearm_back", (0.0, 0.0, -0.30), 0.17),

    Joint("thigh_front", "pelvis", (0.08, 0.05, 0.0), 0.48),
    Joint("shin_front", "thigh_front", (0.0, 0.0, -0.48), 0.40),
    Joint("boot_front", "shin_front", (0.0, 0.0, -0.40), 0.12),

    Joint("thigh_back", "pelvis", (-0.08, -0.05, 0.0), 0.48),
    Joint("shin_back", "thigh_back", (0.0, 0.0, -0.48), 0.40),
    Joint("boot_back", "shin_back", (0.0, 0.0, -0.40), 0.12),
]


def by_name(name: str) -> Joint:
    for j in JOINTS:
        if j.name == name:
            return j
    raise KeyError(f"no joint named {name!r} in JOINTS")


def world_origin(name: str) -> tuple[float, float, float]:
    """Rest-pose world position of a joint's origin, by walking up the
    parent chain and summing offsets. Used to size/place non-animated parts
    (torso, pelvis, head, hair, accessories) without needing Blender."""
    joint = by_name(name)
    if joint.parent is None:
        return joint.offset
    parent_origin = world_origin(joint.parent)
    return tuple(p + o for p, o in zip(parent_origin, joint.offset))
