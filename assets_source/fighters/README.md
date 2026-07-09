# Sources graphiques v2 (Blender)

Ce dossier contient la **matière première** de la pipeline v2 décrite dans
`retro_fighter_v2_blender_sprite_pipeline.md` : références générées par
ChatGPT, morceaux découpés (parts), fichiers `.blend`, définitions
d'animation. Rien ici n'est chargé par le jeu à l'exécution — c'est un espace
de travail, pas un asset runtime (voir `pygbag.ini`, qui l'exclut du build
web pour ne pas alourdir le téléchargement).

La sortie **exécutable** (frames PNG + `manifest.json` consommés par
`retro_fighter/sprites.py`) va dans `assets/fighters/v2/<fighter_id>/` — pas
dans un dossier séparé par personnage (`rose_kunoichi_v2/` à la racine de
`assets/fighters/`) comme suggéré dans une version antérieure du plan : depuis
le mode HD, `assets/fighters/` est déjà organisé par variante graphique
(`ld/`, `hd/`), donc v2 s'ajoute naturellement comme une troisième variante du
même `fighter_id` (`rose_kunoichi`, `shinobi`), plutôt que comme un nouveau
personnage. Ça évite de dupliquer les mappings audio (`AUDIO_CHARACTER_ALIASES`)
et projectile (`FIGHTER_PROJECTILE_ID`), qui sont indexés par `fighter_id` et
n'ont aucune raison de changer entre variantes graphiques du même personnage.

## Structure attendue par personnage

```text
assets_source/fighters/<fighter_id>_v2/
  references/     # planches de référence générées (ChatGPT), notes de style
  parts/          # morceaux PNG découpés et nettoyés (tête, torse, bras, ...)
  rig/            # non utilisé par la pipeline actuelle (voir ../../blender/README.md)
  animations/     # non utilisé par la pipeline actuelle (voir ../../blender/animation_defs.py)
```

**`PARTS_SPEC.md`** (ce dossier) est la spec exacte à donner à ChatGPT/DALL-E :
liste précise des fichiers attendus dans `parts/`, contraintes techniques,
description de style par personnage, prompts prêts à copier-coller. C'est le
document à jour — `retro_fighter_v2_blender_sprite_pipeline.md` (racine du
repo) reste la vision d'ensemble mais certains détails (chemins, `rig/` et
`animations/` en JSON) ont été remplacés par une implémentation plus simple,
voir `../../blender/README.md`.

## État actuel

Squelette vide, prêt à recevoir les sources de `rose_kunoichi_v2` et
`shinobi_v2`. La pipeline Blender elle-même (`../../blender/`) est écrite,
installée et testée de bout en bout avec des pièces factices — il ne manque
que les vraies images (voir `PARTS_SPEC.md`).
