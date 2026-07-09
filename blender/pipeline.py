"""Blender automation entry point: rig + pose + render + export a fighter's
v2 sprite pack in one headless invocation.

Run with Blender itself (not a plain Python interpreter -- this needs bpy):

    blender -b --python blender/pipeline.py -- \
        --fighter rose_kunoichi \
        --parts-dir assets_source/fighters/rose_kunoichi_v2/parts \
        --out assets/fighters/v2/rose_kunoichi \
        --anims idle,walk,punch_mid

See blender/README.md for the full explanation of the rig approach (plain
Empty-object FK chain, not a native Armature -- see rig_config.py's
docstring for why) and current status.
"""
from __future__ import annotations

import argparse
import json
import sys
from math import radians
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import animation_defs  # noqa: E402
import parts_spec  # noqa: E402
import rig_config  # noqa: E402


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--fighter", required=True, help="fighter_id, e.g. rose_kunoichi")
    parser.add_argument("--parts-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="assets/fighters/v2/<fighter_id>")
    parser.add_argument("--anims", default="idle,walk,punch_mid")
    parser.add_argument("--resolution", type=int, default=256)
    parser.add_argument("--anchor-x", type=int, default=128)
    parser.add_argument("--anchor-y", type=int, default=214)
    return parser.parse_args(argv)


def reset_scene(resolution: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.film_transparent = True
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    # Standard (not the Blender 4.x default AgX/Filmic): those view
    # transforms roll off/desaturate highlights, which -- combined with
    # antialiasing blending an opaque emission color against transparent
    # background at a silhouette edge -- produces a visible pale fringe
    # along high-contrast edges (most noticeable as a halo around the
    # skin-toned head). Standard is a flat sRGB curve with no such rolloff.
    scene.view_settings.view_transform = "Standard"
    scene.frame_start = 0
    return scene


def build_joint_empties() -> dict[str, "bpy.types.Object"]:
    """Creates one Empty per rig_config.JOINTS entry, parented into the
    same chain, each positioned at its rest-pose offset from its parent
    (see rig_config.py's docstring for why Empties instead of an Armature).
    """
    empties: dict[str, "bpy.types.Object"] = {}
    for joint in rig_config.JOINTS:
        empty = bpy.data.objects.new(f"joint_{joint.name}", None)
        empty.empty_display_type = "PLAIN_AXES"
        empty.empty_display_size = 0.05
        bpy.context.collection.objects.link(empty)
        empty.location = joint.offset
        if joint.parent:
            empty.parent = empties[joint.parent]
        empties[joint.name] = empty
    return empties


def make_material(image_path: Path) -> tuple["bpy.types.Material", "bpy.types.Image"]:
    img = bpy.data.images.load(str(image_path))
    img.alpha_mode = "STRAIGHT"
    mat = bpy.data.materials.new(name=f"mat_{image_path.stem}")
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    nodes = mat.node_tree
    nodes.nodes.clear()
    out = nodes.nodes.new("ShaderNodeOutputMaterial")
    mix = nodes.nodes.new("ShaderNodeMixShader")
    transparent = nodes.nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.nodes.new("ShaderNodeEmission")
    tex = nodes.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    # Image Texture nodes default extension="REPEAT": UV samples that land
    # even slightly outside [0,1] (routine during multisample antialiasing
    # at a plane's silhouette edge) wrap around to the texture's OPPOSITE
    # edge instead of returning nothing. Since every source PNG has a
    # transparent-but-not-color-zero border from chroma-keying (RGB still
    # near-green, only alpha zeroed), a wrapped sample can pull in that
    # leftover green-ish color and, after the material's alpha-driven Mix
    # Shader, show up as a faint stray-colored fringe along the silhouette.
    # CLIP makes out-of-range samples fully transparent instead of wrapping.
    tex.extension = "CLIP"
    nodes.links.new(tex.outputs["Color"], emission.inputs["Color"])
    nodes.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nodes.links.new(transparent.outputs["BSDF"], mix.inputs[1])
    nodes.links.new(emission.outputs["Emission"], mix.inputs[2])
    nodes.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat, img


def add_part_plane(part: "parts_spec.PartSpec", image_path: Path, joints: dict) -> "bpy.types.Object":
    """A flat plane textured with `image_path`, sized so the attached
    joint's `length` maps to `coverage` of the image's height (leaving a
    little overlap padding at each end for the next part to hide the
    seam), attached to its joint so it inherits that joint's rotation.
    """
    mat, img = make_material(image_path)
    joint = rig_config.by_name(part.joint)
    # Default tuned for rotating limbs (arms/legs): a lower value closes
    # seam gaps (see parts_spec.PartSpec.coverage) but also makes the same
    # rotation angle sweep a visibly longer arc, which reads as exaggerated
    # for anything that actually rotates a lot (a kick, a crouch). Static/
    # rarely-rotated parts (torso/head/pelvis/hair) override to a lower
    # value for more overlap without that downside.
    coverage = part.coverage if part.coverage is not None else 0.85
    length = max(joint.length, 0.08)  # non-limb joints (torso/pelvis/head) still need a plausible plane size
    img_w, img_h = img.size
    aspect = img_w / max(img_h, 1)
    plane_h = length / coverage
    plane_w = plane_h * aspect * part.width_scale

    bpy.ops.mesh.primitive_plane_add(size=1.0)
    plane = bpy.context.active_object
    plane.name = f"part_{part.name}"
    plane.data.materials.append(mat)
    # Default plane is in local XY, normal +Z. Rotate it upright into the
    # local XZ plane with its normal toward -Y (the camera sits on -Y
    # looking toward +Y, see build_camera below) so it's actually visible.
    plane.rotation_euler = (radians(90), 0, 0)
    # The raw plane primitive's extent is in local X/Y (Z=0 for every
    # vertex); scale must size X (width) and Y (which becomes world Z,
    # "up", after the rotation above) -- scaling Z here would be a no-op
    # since the flat geometry has no Z extent to scale in the first place.
    plane.scale = (plane_w, plane_h, 1.0)
    # Shift the plane by half its height, in whichever direction this
    # joint's segment actually extends (see rig_config.Joint.direction),
    # so it covers the joint-to-child segment instead of being centered on
    # the joint origin (which would straddle it half on the wrong side).
    #
    # The Y (depth, camera-facing) offset is what actually determines draw
    # order: without it every part sits at local Y=0 and Blender's
    # transparent-object sort has no reliable distance to sort by, so
    # occlusion between parts (e.g. the belt vs. the torso) ends up
    # arbitrary instead of matching parts_spec.PART's z_index. The camera
    # sits at Y=-5 looking toward +Y (see build_camera), so *smaller* Y is
    # *closer* to the camera -- higher z_index (by convention "closer to
    # camera") must map to a more negative Y. This is set in local space,
    # which stays a pure Y offset in world space regardless of pose since
    # every joint only ever rotates around Y (see rig_config.py's
    # docstring) -- rotating around Y can't tilt a Y-axis offset into X/Z.
    # Magnitude is arbitrary for an orthographic camera (it only affects
    # sort order, never apparent screen position/scale), so it's picked
    # large enough to dominate the incidental Y components already present
    # in some joints' rest offsets (e.g. left/right arm separation, up to
    # ~0.06) rather than fight with them.
    depth_y = -part.z_index * 0.01
    plane.location = (
        part.anchor_offset_x * plane_w,
        depth_y,
        joint.direction * plane_h / 2.0 + part.anchor_offset_z * plane_h,
    )

    plane.parent = joints[part.joint]
    return plane


def set_hand_visibility(parts_objs: dict[str, "bpy.types.Object"], frame: int, hand_pose: str) -> None:
    for name, hidden in (("hand_front_open", hand_pose != "open"), ("hand_front_fist", hand_pose != "fist")):
        obj = parts_objs.get(name)
        if obj is None:
            continue
        obj.hide_render = hidden
        obj.keyframe_insert(data_path="hide_render", frame=frame)


def apply_animation_keyframes(anim: "animation_defs.AnimationDef", joints: dict, parts_objs: dict) -> None:
    # main() reuses the same joints/parts_objs across every --anims entry in
    # one Blender session. Without this, keyframe_insert() below only ever
    # *adds* points to each object's existing Action -- a frame number left
    # over from a PREVIOUS animation (e.g. double_jump_salto's frame 4) that
    # the CURRENT animation's own keyframes don't happen to redefine stays
    # in the fcurve and gets sampled during this animation's render, visibly
    # corrupting poses (this is what produced the "character goes flying"
    # frames reported after the fact -- crouch_idle/kick_mid inheriting
    # rotation values from whichever animation rendered right before them).
    # Clearing animation_data before every animation guarantees each one
    # starts from a blank Action with only its own keyframes.
    for joint in joints.values():
        joint.animation_data_clear()
        joint.rotation_euler = (0.0, 0.0, 0.0)
    for part in parts_objs.values():
        part.animation_data_clear()
    root = joints["root"]
    root.location = (0.0, 0.0, 0.0)
    for kf in anim.keyframes:
        for joint_name, joint in joints.items():
            pose = kf.pose.get(joint_name)
            joint.rotation_euler = tuple(radians(d) for d in pose) if pose else (0.0, 0.0, 0.0)
            joint.keyframe_insert(data_path="rotation_euler", frame=kf.frame)
        root.location = kf.root_offset
        root.keyframe_insert(data_path="location", frame=kf.frame)
        set_hand_visibility(parts_objs, kf.frame, kf.hand_front_pose)
    for joint in joints.values():
        if joint.animation_data and joint.animation_data.action:
            for fcurve in joint.animation_data.action.fcurves:
                for kp in fcurve.keyframe_points:
                    kp.interpolation = "LINEAR"


def build_camera(resolution: int, anchor_x: int, anchor_y: int) -> None:
    """Orthographic camera framing the character so it renders at roughly
    the same scale/anchor convention as the existing ld/hd packs (256x256
    canvas, ~205px standing height, anchor near the feet) -- see
    assets/fighters/CONTRACT.md.
    """
    # Was 205 to match the HD pack's ~205px standing height (see CONTRACT.md),
    # then 195 for a first hair-margin pass. Reduced further per ChatGPT's
    # final validation pass: the ponytail (now a bigger, taller silhouette
    # element than the loose-strand placeholder this was first tuned
    # against) was pixel-confirmed touching row 0 -- genuinely clipped, not
    # just close -- in idle/walk/dash/punch_high/kick_mid and others.
    # Root-caused via parts_spec math: hair_back's plane (coverage=0.20 on
    # the head joint's 0.28 length -> plane_h=1.4) reached world Z=2.74,
    # 44% TALLER than CHARACTER_HEIGHT=1.9 -- a genuinely oversized plane,
    # not just a framing-margin problem. Paired this moderate camera
    # reduction with directly tightening hair_back's plane size (see its
    # PartSpec) rather than shrinking the camera alone all the way to
    # accommodate the full oversized plane, which would have visibly
    # shrunk the whole character just to fit one part. The `anchor` field
    # in the manifest (not a fixed pixel height) is what downstream code
    # uses to place the sprite, so this is safe and doesn't break
    # CONTRACT.md.
    target_height_px = 155.0
    ortho_scale = rig_config.CHARACTER_HEIGHT * resolution / target_height_px
    bpy.ops.object.camera_add(location=(0.0, -5.0, rig_config.CHARACTER_HEIGHT / 2.0),
                               rotation=(radians(90), 0.0, 0.0))
    camera = bpy.context.active_object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho_scale
    # Pin ortho_scale to the vertical extent unambiguously -- with the
    # default AUTO sensor fit, ortho_scale's meaning depends on the
    # camera sensor's aspect ratio (36x24mm by default) rather than the
    # render resolution, which threw off the anchor math below.
    camera.data.sensor_fit = "VERTICAL"
    bpy.context.scene.camera = camera

    # Vertical framing: put the character's feet at anchor_y/resolution
    # fraction down from the top of frame, matching ld/hd's anchor=(128,214)
    # in a 256px canvas (feet sit near the bottom with a little margin).
    frame_half_height = ortho_scale / 2.0
    feet_from_bottom_frac = 1.0 - (anchor_y / resolution)
    camera_center_z = rig_config.CHARACTER_HEIGHT / 2.0
    feet_z = 0.0
    # Solve for camera Z so that feet_z lands at feet_from_bottom_frac up
    # from the bottom of the ortho view.
    desired_camera_z = feet_z + frame_half_height - feet_from_bottom_frac * (frame_half_height * 2.0)
    camera.location.z = desired_camera_z


def build_world_light() -> None:
    # Flat 2D cutout art: emission shaders already carry their own "lit"
    # color, so no scene lighting is needed (and none should be added --
    # a light would be irrelevant to an Emission-shader material anyway).
    pass


def render_animation(anim: "animation_defs.AnimationDef", out_dir: Path, fighter_prefix: str) -> list[dict]:
    scene = bpy.context.scene
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_paths = []
    for i in range(anim.frame_count):
        scene.frame_set(i)
        out_path = frames_dir / f"{anim.name}_{i:03d}.png"
        scene.render.filepath = str(out_path)
        bpy.ops.render.render(write_still=True)
        frame_paths.append(f"frames/{anim.name}_{i:03d}.png")
        print(f"  rendered {out_path.name}")
    return frame_paths


def write_manifest(out_dir: Path, fighter: str, anchor_x: int, anchor_y: int,
                    anim_frames: dict[str, list[str]]) -> None:
    manifest = {
        "fighter_id": fighter,
        "version": "2.0.0",
        "frame_width": bpy.context.scene.render.resolution_x,
        "frame_height": bpy.context.scene.render.resolution_y,
        "anchor": {"x": anchor_x, "y": anchor_y},
        "facing": "right",
        "format": "blender-rendered transparent PNG frames (v2 cutout pipeline)",
        "animations": {},
    }
    for name, frames in anim_frames.items():
        anim = animation_defs.ANIMATIONS[name]
        manifest["animations"][name] = {
            "frames": frames,
            "frame_count": len(frames),
            "fps": anim.fps,
            "loop": anim.loop,
        }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    print(f"=== v2 pipeline: fighter={args.fighter} parts_dir={args.parts_dir} out={args.out} ===")

    reset_scene(args.resolution)
    joints = build_joint_empties()

    parts_objs: dict[str, "bpy.types.Object"] = {}
    missing = []
    for part in parts_spec.PARTS:
        image_path = args.parts_dir / f"{part.name}.png"
        if not image_path.exists():
            missing.append(part.name)
            continue
        parts_objs[part.name] = add_part_plane(part, image_path, joints)
    if missing:
        print(f"WARNING: {len(missing)} part(s) missing from {args.parts_dir}, skipped: {missing}")

    build_camera(args.resolution, args.anchor_x, args.anchor_y)
    build_world_light()

    requested_anims = [a.strip() for a in args.anims.split(",") if a.strip()]
    anim_frames: dict[str, list[str]] = {}
    args.out.mkdir(parents=True, exist_ok=True)
    for anim_name in requested_anims:
        anim = animation_defs.ANIMATIONS[anim_name]
        print(f"--- animating & rendering '{anim_name}' ({anim.frame_count} frames @ {anim.fps}fps) ---")
        apply_animation_keyframes(anim, joints, parts_objs)
        anim_frames[anim_name] = render_animation(anim, args.out, args.fighter)

    write_manifest(args.out, args.fighter, args.anchor_x, args.anchor_y, anim_frames)
    print(f"=== done: {args.out} ({sum(len(f) for f in anim_frames.values())} frames total) ===")


if __name__ == "__main__":
    main()
