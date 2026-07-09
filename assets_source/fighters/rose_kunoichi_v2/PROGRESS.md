# Rose Kunoichi v2 — progress tracker

Structure copiable telle quelle pour `shinobi_v2/PROGRESS.md` (voir
`HOW_TO_GENERATE_V2_SPRITES.md`'s "Répéter pour un autre personnage").

## Parts (phase 1 — 19/19 générées)

Générées via ChatGPT (3 lots, fond vert + chroma-key local), voir
`PARTS_PROMPTS.md` pour les prompts exacts utilisés.

- [x] head.png
- [x] hair_front.png
- [x] hair_back.png
- [x] torso.png
- [x] pelvis.png
- [x] accessory_main.png (sash)
- [x] upper_arm_back.png
- [x] forearm_back.png
- [x] hand_back.png
- [x] upper_arm_front.png
- [x] forearm_front.png
- [x] hand_front_open.png
- [x] hand_front_fist.png (généré séparément, recadré à la même proportion de poignet que hand_front_open — voir guide)
- [x] thigh_back.png
- [x] shin_back.png
- [x] boot_back.png
- [x] thigh_front.png
- [x] shin_front.png
- [x] boot_front.png

## Parts (phase 2 — 0/3, non générées)

Non nécessaires tant qu'aucune animation authored ne les requiert (voir
`PARTS_SPEC.md`) :
- [ ] hand_back_fist.png
- [ ] hair_strand_front.png
- [ ] hair_strand_back.png

## Rig (`blender/rig_config.py`, `blender/pipeline.py`)

- [x] Rendu de base validé avec les vraies proportions de Rose (pas de
      retuning de `coverage`/joint `length` nécessaire — les valeurs
      génériques ont donné un résultat lisible du premier coup)
- [x] Extension `root_offset` sur `Keyframe` pour les poses accroupies
      (translation du bassin en plus de la rotation des jambes)

## Animations (22/22 rendues — parité complète avec le moteur + dash)

Toutes dans `blender/animation_defs.py`, rendues dans
`assets/fighters/v2/rose_kunoichi/`. `validate_manifest.py --reference ld`
: 0 erreur, 0 avertissement.

- [x] idle, walk (vertical slice initiale)
- [x] dash (pose dédiée, pas un repli sur walk — voir `CONTRACT.md`)
- [x] jump, double_jump_salto
- [x] crouch_idle, crouch_walk
- [x] punch_high, punch_mid, punch_low
- [x] kick_high, kick_mid, kick_low
- [x] crouch_punch_low, crouch_kick_low
- [x] block_high, block_mid, block_low
- [x] hitstun, ko
- [x] ranged_charge, ranged_throw

## Validé en jeu (headless)

- [x] `validate_manifest.py` propre
- [x] Contact sheet (plusieurs frames par animation) inspectée visuellement
      — silhouettes lisibles, pas de membre disloqué
- [x] Match complet headless avec `Renderer.set_graphics_variant("v2")` —
      Rose s'affiche correctement en v2 (pieds ancrés, ombre alignée),
      l'adversaire (Shinobi, pas encore de pack v2) retombe proprement sur
      LD sans crasher

## Aspérités connues (acceptées, pas des blocages)

- `ko` : le rig ne translate que par rotation de joints (pas de translation
  du bassin vers l'avant), donc la pose finale est un affaissement/
  trébuchement plutôt qu'un effondrement complet à plat au sol. Rotation du
  torse volontairement plafonnée (~48°) pour éviter que les membres
  paraissent se détacher visuellement — voir le guide, étape 7.
- Les poses de `animation_defs.py` sont un premier passage (angles choisis
  pour prouver que la pose se lit correctement), pas finement calibrées —
  `blender/README.md` documentait déjà cette attente pour idle/walk/
  punch_mid, elle s'applique pareillement aux 19 animations ajoutées ici.
