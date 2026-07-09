# Retro Fighter v2 — plan de pipeline sprites avec Blender

**Objectif :** préparer une v2 du jeu en gardant l’approche actuelle côté runtime : **Pygame reste le moteur de jeu**, les personnages restent consommés sous forme de **frames PNG transparentes + `manifest.json`**, mais la production des sprites passe par une **usine Blender** à partir d’images 2D générées par ChatGPT.

La meilleure option retenue ici est l’**option 1 : personnage découpé en parties**, c’est-à-dire un personnage source produit non pas comme 100 images d’animation indépendantes, mais comme un **kit de morceaux articulables** : tête, torse, bras, jambes, cheveux, accessoires, etc.

---

## 1. Décision d’architecture

### 1.1 Ce qui reste dans Pygame

Pygame doit rester responsable de :

- la boucle de jeu ;
- les inputs ;
- la machine à états des combattants ;
- l’IA ;
- les collisions ;
- les hitboxes / hurtboxes ;
- les projectiles ;
- les barres de vie ;
- le menu ;
- le build web via Pygbag.

Le moteur n’a pas besoin de connaître Blender. Il doit seulement charger les sprites exportés.

### 1.2 Ce qui passe dans Blender

Blender devient une **usine de production d’assets** :

1. importer les morceaux PNG d’un personnage ;
2. construire une scène 2D / pseudo-2D ;
3. créer un squelette / rig ;
4. poser des animations ;
5. rendre des frames PNG transparentes ;
6. générer un `manifest.json` compatible avec le format actuel du repo ;
7. éventuellement générer aussi des métadonnées de frame : événements, points d’impact, hitboxes suggérées, points de spawn projectiles.

### 1.3 Ce qu’il ne faut pas faire

Ne pas générer directement toutes les frames finales avec ChatGPT image par image.

Le problème actuel vient de là : chaque image est belle isolément, mais les proportions, la pose, la tête, les membres, le costume et le centre de gravité changent légèrement d’une frame à l’autre. L’animation devient donc agitée, même avec peu de frames.

La v2 doit inverser le raisonnement :

> ChatGPT génère le **personnage source** et ses morceaux ; Blender génère les **frames animées cohérentes**.

---

## 2. Contrat actuel du repo à conserver

Le repo actuel consomme déjà des packs de sprites sous `assets/fighters/<fighter_id>/`.

Le contrat existant à conserver :

```text
assets/fighters/<fighter_id>/
  manifest.json
  frames/
    idle_000.png
    idle_001.png
    ...
  sheets/
    idle.png
    walk.png
    ...
  extension_manifest*.json
  extension_frames/
  extension_sheets/
```

Le format courant utilise notamment :

```json
{
  "fighter_id": "rose_kunoichi",
  "display_name": "Rose Kunoichi",
  "frame_width": 256,
  "frame_height": 256,
  "anchor": { "x": 128, "y": 214 },
  "facing": "right",
  "animations": {
    "idle": {
      "frames": ["frames/idle_000.png", "frames/idle_001.png"],
      "fps": 8,
      "loop": true
    }
  }
}
```

Le loader actuel fusionne aussi les fichiers `extension_manifest*.json`. Pour une v2, il est possible soit de :

- continuer avec `manifest.json` + `extension_manifest*.json`, pour compatibilité maximale ;
- soit produire un seul `manifest.json` consolidé pour le fighter v2.

**Recommandation :** pour la v2, produire un dossier séparé, par exemple :

```text
assets/fighters/rose_kunoichi_v2/
assets/fighters/shinobi_v2/
```

Cela permet de comparer v1 et v2 sans casser le prototype.

---

## 3. Nouvelle structure proposée du repo

Ajouter une séparation claire entre les **sources graphiques** et les **assets runtime**.

```text
retro-fighter/
  assets/
    fighters/
      rose_kunoichi/
      shinobi/
      rose_kunoichi_v2/          # export généré par Blender
      shinobi_v2/                # export généré par Blender

  assets_source/
    fighters/
      rose_kunoichi_v2/
        references/
          rose_full_reference.png
          rose_palette.png
          rose_model_notes.md
        parts/
          head.png
          hair_front.png
          hair_back.png
          torso.png
          pelvis.png
          upper_arm_front.png
          upper_arm_back.png
          forearm_front.png
          forearm_back.png
          hand_front_fist.png
          hand_back_fist.png
          thigh_front.png
          thigh_back.png
          shin_front.png
          shin_back.png
          boot_front.png
          boot_back.png
          sash.png
          energy_core.png
        rig/
          rose_kunoichi_v2.blend
          rig_config.json
        animations/
          idle.json
          walk.json
          punch_mid.json

      shinobi_v2/
        references/
        parts/
        rig/
        animations/

  tools/
    blender/
      README.md
      build_cutout_scene.py
      create_rig.py
      apply_animation.py
      export_sprite_pack.py
      render_contact_sheet.py
      validate_export.py

    sprites/
      validate_manifest.py
      build_sheets.py
      compare_v1_v2_contact_sheets.py
```

Important : `assets/fighters/...` doit rester la sortie exécutable par le jeu. `assets_source/...` peut être exclu du build web si trop lourd.

---

## 4. Images à ajouter si on part sur l’option 1

L’option 1 demande moins de frames finales générées à la main, mais plus d’images sources structurées.

### 4.1 Minimum viable par personnage

Pour chaque personnage, il faut ajouter environ **25 à 35 PNG sources** propres, transparentes, découpées et cohérentes.

Ces images ne sont pas des frames d’animation. Ce sont les morceaux du puppet / rig.

| Catégorie | Images à produire | Commentaire |
|---|---:|---|
| Référence globale | 1 à 3 | Design final, vue de profil / 3⁄4 côté, pose neutre. |
| Palette / style | 1 | Optionnel mais utile pour stabiliser les générations suivantes. |
| Tête / cheveux | 4 à 8 | Tête, visage, cheveux avant, cheveux arrière, mèches secondaires. |
| Buste | 3 à 5 | Torse, bassin, cou, éventuellement poitrine/épaule séparées. |
| Bras | 8 à 12 | Bras avant/arrière, avant-bras avant/arrière, mains ouvertes, poings. |
| Jambes | 8 à 12 | Cuisses, tibias, bottes/pieds avant/arrière. |
| Accessoires | 2 à 8 | Sash, foulard, arme, fourreau, ruban, pièces flottantes. |
| Effets propres au personnage | 1 à 5 | Main lumineuse, aura, noyau projectile, shuriken, etc. |

**Total réaliste :**

- strict minimum : environ 25 images source par personnage ;
- confortable : 35 à 45 images source par personnage ;
- très propre : 50+ images si on veut des variantes de mains, pieds, cheveux, accessoires et déformations.

### 4.2 Nommage recommandé des parties

Utiliser des noms sémantiques stables.

```text
parts/
  root_shadow.png
  pelvis.png
  torso.png
  neck.png
  head.png
  face.png
  hair_front.png
  hair_back.png
  hair_strand_front_01.png
  hair_strand_back_01.png

  upper_arm_front.png
  forearm_front.png
  hand_front_open.png
  hand_front_fist.png
  hand_front_magic.png

  upper_arm_back.png
  forearm_back.png
  hand_back_open.png
  hand_back_fist.png

  thigh_front.png
  shin_front.png
  boot_front.png
  foot_front.png

  thigh_back.png
  shin_back.png
  boot_back.png
  foot_back.png

  sash_front.png
  sash_back.png
  weapon.png
  projectile_core.png
```

Dans un jeu de combat vu de côté, il vaut mieux raisonner en **front/back limb** plutôt qu’en gauche/droite anatomique. Le personnage est dessiné facing right, puis Pygame peut continuer à faire le flip horizontal comme aujourd’hui.

---

## 5. Spécification des images source à générer avec ChatGPT

### 5.1 Contraintes communes

Pour chaque personnage source :

- fond transparent ;
- personnage facing right ;
- style cohérent avec la v1 ;
- proportions stables ;
- pas d’ombre portée intégrée dans les morceaux ;
- contour propre ;
- résolution supérieure à la sortie finale, par exemple 1024 px de haut pour travailler confortablement ;
- toutes les pièces doivent correspondre au même design ;
- articulations masquées par le style quand possible : manches, gants, bottes, ceinture, protections.

### 5.2 Pose source recommandée

Ne pas utiliser une vraie T-pose rigide. Pour un jeu de combat 2D stylisé, viser une **pose neutre articulable** :

- buste droit mais dynamique ;
- bras légèrement écartés du corps ;
- jambes séparées ;
- pieds visibles ;
- silhouette facing right ;
- mains lisibles ;
- genoux et coudes suffisamment dégagés pour découper les segments.

### 5.3 Prompt type pour générer la référence globale

```text
Create a clean 2D game character reference sheet for an original retro fighting game character.
Side-facing right, athletic stance, transparent background, full body visible, consistent proportions, readable silhouette, high-quality illustrated sprite style, designed for 2D cutout rigging.
The character must have separated readable body zones: head, hair, torso, pelvis, upper arms, forearms, hands, thighs, shins, boots, accessories.
No background, no ground shadow, no text, no duplicated character, no animation frames.
```

### 5.4 Prompt type pour générer les parties séparées

```text
Create a technical cutout parts sheet for the same character, transparent background.
Separate each body part clearly with spacing: head, hair front, hair back, torso, pelvis, front upper arm, front forearm, front hand open, front hand fist, back upper arm, back forearm, back hand open, back hand fist, front thigh, front shin, front boot, back thigh, back shin, back boot, sash, accessory.
All parts must belong to the exact same character design and scale, facing right, clean edges, no background, no shadows, no labels.
```

Dans la pratique, il faudra probablement produire plusieurs planches et découper/nettoyer les parties. Le but n’est pas que ChatGPT livre un rig parfait directement, mais qu’il livre une matière première cohérente.

---

## 6. Liste des animations à produire en v2

### 6.1 Vertical slice recommandé

Ne pas commencer par toutes les animations. Commencer par un seul fighter, par exemple `rose_kunoichi_v2`, avec :

| Animation | Frames cibles | Priorité | Objectif |
|---|---:|---:|---|
| `idle` | 8 | P0 | Prouver la stabilité du rig. |
| `walk` | 8 | P0 | Prouver un cycle lisible. |
| `punch_mid` | 6 | P0 | Prouver une attaque synchronisable avec la hitbox. |

Ce premier lot permet de valider :

- le rendu transparent ;
- le cadrage 256×256 ;
- l’ancrage au sol ;
- le flip horizontal ;
- le manifeste ;
- la compatibilité avec Pygame ;
- le ressenti visuel dans une vraie partie.

### 6.2 Pack complet cible par fighter

Une fois la verticale validée, viser ce pack :

| Animation | Frames v2 cibles | FPS suggéré | Loop | Notes |
|---|---:|---:|---|---|
| `idle` | 8 | 8 | oui | Respiration très subtile, stable. |
| `walk` | 8 | 10-12 | oui | Cycle contact/down/passing/up miroir. |
| `jump` | 6 | 10 | non | Décollage, montée, apex, descente. |
| `crouch_idle` | 4 | 7 | oui | Position basse sans compression verticale. |
| `crouch_walk` | 6 | 8 | oui | Duck walk lisible, pieds au sol. |
| `punch_high` | 6 | 15-18 | non | Startup / active / recovery. |
| `punch_mid` | 6 | 15-18 | non | Prioritaire. |
| `punch_low` | 6 | 15-18 | non | À distinguer visuellement du mid. |
| `kick_high` | 8 | 13-16 | non | Plus ample, recovery visible. |
| `kick_mid` | 8 | 13-16 | non | Front kick / side kick. |
| `kick_low` | 8 | 13-16 | non | Balayage bas. |
| `block_high` | 2 | 4 | oui | Pose tenue + micro variation. |
| `block_mid` | 2 | 4 | oui | Pose tenue + micro variation. |
| `block_low` | 2 | 4 | oui | Pose tenue + micro variation. |
| `hitstun` | 3 | 8 | non | Impact + recul. |
| `ko` | 8 | 8 | non | Chute + pose finale. |
| `ranged_charge` | 4 | 10 | non | Préparation projectile. |
| `ranged_throw` | 6 | 14 | non | Frame de spawn explicite. |
| `double_jump_salto` | 8 | 16 | non | Rotation compacte, non compressée. |
| `crouch_punch_low` | 6 | 15-18 | non | Attaque basse accroupie. |
| `crouch_kick_low` | 8 | 13-16 | non | Balayage accroupi. |

Cela donne environ **123 frames rendues par Blender par fighter**, mais ces frames ne sont plus générées une par une par IA : elles sont dérivées d’un rig stable.

---

## 7. Spécification Blender

### 7.1 Scène Blender

La scène Blender doit être configurée comme un atelier de rendu 2D :

- caméra orthographique ;
- fond transparent ;
- résolution de rendu : 256×256 pour compatibilité immédiate ;
- éventuellement rendu en 512×512 puis downscale propre vers 256×256 ;
- origine logique : pieds au sol ;
- personnage authored facing right ;
- frame de sortie alignée sur l’anchor `{ x: 128, y: 214 }`.

### 7.2 Rig 2D

Deux approches possibles :

#### A. Parenting simple par pièce

Chaque morceau PNG est un plan texturé parenté à un os.

Avantages :

- simple ;
- robuste ;
- très scriptable ;
- suffisant pour une première v2.

Inconvénients :

- articulations parfois visibles ;
- moins souple pour les déformations.

#### B. Mesh + armature + déformations

Les morceaux sont convertis en meshes déformables.

Avantages :

- meilleure fluidité ;
- bras/jambes peuvent se courber légèrement ;
- plus proche d’un vrai rig 2D.

Inconvénients :

- plus complexe ;
- plus long à automatiser ;
- plus difficile à générer proprement.

**Recommandation :** commencer en A, puis passer certains morceaux critiques en B si nécessaire.

### 7.3 Os minimaux

```text
root
  pelvis
    torso
      neck
        head
          hair_front
          hair_back
      shoulder_front
        upper_arm_front
          forearm_front
            hand_front
      shoulder_back
        upper_arm_back
          forearm_back
            hand_back
    hip_front
      thigh_front
        shin_front
          foot_front
    hip_back
      thigh_back
        shin_back
          foot_back
    sash
```

### 7.4 Points techniques à stocker

Dans `rig_config.json` :

```json
{
  "fighter_id": "rose_kunoichi_v2",
  "frame_width": 256,
  "frame_height": 256,
  "anchor": { "x": 128, "y": 214 },
  "facing": "right",
  "scale": 1.0,
  "parts": {
    "torso": { "file": "parts/torso.png", "bone": "torso", "z_index": 20 },
    "head": { "file": "parts/head.png", "bone": "head", "z_index": 40 }
  }
}
```

---

## 8. Export Blender vers pack Pygame

### 8.1 Commande cible

À terme, l’export doit pouvoir se lancer en ligne de commande :

```bash
blender -b assets_source/fighters/rose_kunoichi_v2/rig/rose_kunoichi_v2.blend \
  -P tools/blender/export_sprite_pack.py -- \
  --fighter rose_kunoichi_v2 \
  --out assets/fighters/rose_kunoichi_v2
```

### 8.2 Sortie attendue

```text
assets/fighters/rose_kunoichi_v2/
  manifest.json
  frames/
    idle_000.png
    idle_001.png
    ...
    punch_mid_000.png
    punch_mid_001.png
  sheets/
    idle.png
    walk.png
    punch_mid.png
  animation_events.json
  hitbox_suggestions.json
  preview_contact_sheet.png
```

### 8.3 `manifest.json` cible

Le manifeste doit rester compatible avec `FighterSpriteSet` :

```json
{
  "fighter_id": "rose_kunoichi_v2",
  "display_name": "Rose Kunoichi v2",
  "version": "0.2.0",
  "frame_width": 256,
  "frame_height": 256,
  "anchor": { "x": 128, "y": 214 },
  "facing": "right",
  "format": "blender-rendered transparent PNG frames plus horizontal spritesheets",
  "animations": {
    "idle": {
      "frames": [
        "frames/idle_000.png",
        "frames/idle_001.png"
      ],
      "sheet": "sheets/idle.png",
      "frame_count": 8,
      "fps": 8,
      "loop": true,
      "gameplay_state_hint": "idle"
    }
  }
}
```

### 8.4 `animation_events.json` proposé

Aujourd’hui, les timings de combat sont définis côté code dans `attacks.py`. Pour la v2, il faut commencer à réconcilier les timings gameplay et les frames visuelles.

Créer un fichier séparé :

```json
{
  "punch_mid": {
    "startup_visual_frames": [0, 1],
    "active_visual_frames": [2, 3],
    "recovery_visual_frames": [4, 5],
    "hit_fx_frame": 3,
    "sound_frame": 2
  },
  "ranged_throw": {
    "projectile_spawn_frame": 3,
    "spawn_offset_from_anchor": { "x": 88, "y": -104 }
  }
}
```

Dans un premier temps, Pygame peut ignorer ce fichier. Ensuite, on pourra l’utiliser pour aligner les VFX, sons, projectiles et hitboxes.

---

## 9. Modifications de code à prévoir dans Retro Fighter

### 9.1 Modification minimale

Pour tester un fighter v2, changer seulement l’identifiant du fighter au moment de l’instanciation :

```python
self.player = Fighter(
    "PLAYER",
    x=260,
    color=COLOR_BLUE,
    fighter_id="rose_kunoichi_v2",
    is_human=True,
)
```

Si le dossier `assets/fighters/rose_kunoichi_v2/manifest.json` respecte le contrat existant, le loader devrait pouvoir le charger avec peu ou pas de modification.

### 9.2 Modification recommandée dans `sprites.py`

Ajouter des garde-fous :

- vérifier que chaque frame existe ;
- vérifier que toutes les frames ont la même dimension ;
- warning si une animation attendue manque ;
- log du fighter chargé ;
- fallback clair vers `idle` seulement si nécessaire.

### 9.3 Ajout recommandé : validation de pack

Créer :

```text
tools/sprites/validate_manifest.py
```

Contrôles :

- `manifest.json` valide ;
- toutes les frames listées existent ;
- toutes les frames sont en RGBA ;
- dimensions 256×256 ;
- anchor présent ;
- animations minimales présentes ;
- pas de chemins absolus ;
- pas de fichiers inutiles dans le build web.

### 9.4 Ajout recommandé : sélection de fighter par config

Au lieu de modifier `game.py` à chaque test, ajouter une config :

```python
PLAYER_FIGHTER_ID = "rose_kunoichi_v2"
ENEMY_FIGHTER_ID = "shinobi"
```

ou un fichier :

```text
assets/fighters/current_fighters.json
```

Cela permettra de basculer v1/v2 rapidement.

---

## 10. Synchronisation animation / gameplay

C’est le point à traiter sérieusement en v2.

Actuellement, les attaques ont une définition gameplay du type :

```text
startup_frames + active_frames + recovery_frames
```

Mais les animations sprites ont aussi leur propre `fps` et leur propre nombre de frames. Il faut éviter que :

- le coup touche alors que le bras n’est pas encore tendu ;
- le projectile parte avant la frame de lancer ;
- le recovery gameplay se termine alors que l’animation semble encore ouverte ;
- les block/hit effects soient mal calés.

### 10.1 Règle simple pour la v2

Pour chaque attaque :

- une ou deux frames d’anticipation ;
- une ou deux frames actives visuellement très lisibles ;
- deux ou trois frames de recovery ;
- `hit_fx_frame` = frame visuelle la plus étendue ;
- active gameplay doit recouvrir la frame visuelle d’impact.

### 10.2 Deux options d’implémentation

#### Option simple

Conserver les timings gameplay de `attacks.py`, et ajuster les animations pour que l’impact visuel tombe à peu près au bon moment.

Avantage : aucune refonte gameplay.

#### Option propre

Déplacer une partie des timings dans un fichier data commun, par exemple :

```text
assets/fighters/rose_kunoichi_v2/combat_profile.json
```

Ce fichier pourrait contenir :

- startup ;
- active ;
- recovery ;
- range ;
- hitbox par frame ;
- hurtbox override ;
- offsets de projectile.

Avantage : vraie pipeline data-driven.

**Recommandation :** commencer simple, mais générer déjà `animation_events.json` pour préparer la suite.

---

## 11. Backlog en PRs

### PR 1 — Préparer le repo pour la pipeline v2

Objectif : aucun changement visuel, seulement préparer l’espace de travail.

À faire :

- ajouter `assets_source/` ;
- ajouter `tools/blender/README.md` ;
- ajouter `tools/sprites/validate_manifest.py` ;
- documenter le contrat `assets/fighters/<fighter_id>/manifest.json` ;
- ajouter une config pour choisir `PLAYER_FIGHTER_ID` et `ENEMY_FIGHTER_ID`.

Critère de succès : le jeu tourne exactement comme avant.

### PR 2 — Produire les images source Rose v2

Objectif : créer les sources cutout de `rose_kunoichi_v2`.

À faire :

- générer la référence globale ;
- générer la planche de morceaux ;
- découper/nettoyer les PNG ;
- placer les images dans `assets_source/fighters/rose_kunoichi_v2/parts/` ;
- ajouter `rose_model_notes.md` ;
- définir `rig_config.json`.

Critère de succès : tous les morceaux sont cohérents et assemblables en pose neutre.

### PR 3 — Prototype Blender vertical slice

Objectif : rendre `idle`, `walk`, `punch_mid` depuis Blender.

À faire :

- créer `rose_kunoichi_v2.blend` ;
- créer les os principaux ;
- parent les morceaux aux os ;
- créer `idle`, `walk`, `punch_mid` ;
- exporter les frames PNG ;
- générer `manifest.json` ;
- générer `preview_contact_sheet.png`.

Critère de succès : le jeu charge `rose_kunoichi_v2` et les trois animations sont lisibles en match.

### PR 4 — Pack complet Rose v2

Objectif : remplacer toutes les animations utiles de Rose.

À faire :

- compléter les animations de base ;
- compléter crouch / ranged / salto ;
- compléter hitstun / KO ;
- générer les sheets ;
- ajouter les métadonnées d’events ;
- valider l’intégration Pygame.

Critère de succès : Rose v2 est jouable sans fallback visuel important.

### PR 5 — Shinobi v2

Objectif : appliquer le même pipeline au deuxième personnage.

À faire :

- générer les images source Shinobi ;
- créer le rig ;
- exporter le pack complet ;
- intégrer comme CPU ;
- comparer les tailles / anchors / lisibilité avec Rose.

Critère de succès : match complet Rose v2 vs Shinobi v2.

### PR 6 — Synchronisation animation / combat

Objectif : améliorer le lien entre frames visuelles et frames actives.

À faire :

- lire `animation_events.json` ;
- caler les sons ;
- caler les hit sparks ;
- caler les projectiles ;
- éventuellement ajouter hitboxes/hurtboxes par frame.

Critère de succès : les coups semblent toucher exactement quand le sprite le montre.

---

## 12. Checklist qualité pour chaque export

### 12.1 Qualité image

- [ ] fond transparent ;
- [ ] pas de pixels parasites ;
- [ ] personnage toujours à la même échelle ;
- [ ] pieds alignés sur l’anchor ;
- [ ] silhouette lisible à taille réelle ;
- [ ] pas de changement de costume entre frames ;
- [ ] pas de tremblement de tête ou de buste en idle ;
- [ ] pas de saut brutal de centre de gravité.

### 12.2 Qualité animation

- [ ] `idle` sobre ;
- [ ] `walk` cyclique ;
- [ ] attacks avec anticipation / impact / recovery ;
- [ ] `block` lisible ;
- [ ] `hitstun` instantanément compréhensible ;
- [ ] `ko` finit sur une frame stable ;
- [ ] `double_jump_salto` ressemble à un mouvement articulé, pas à une image compressée.

### 12.3 Qualité intégration

- [ ] toutes les animations listées dans `manifest.json` existent ;
- [ ] toutes les frames font 256×256 ;
- [ ] toutes les frames sont RGBA ;
- [ ] `anchor` constant ;
- [ ] le flip horizontal fonctionne ;
- [ ] le personnage ne glisse pas visuellement au sol ;
- [ ] les projectiles partent de la bonne position ;
- [ ] le build web n’embarque pas les fichiers source Blender inutilement.

---

## 13. Risques et mitigations

| Risque | Symptôme | Mitigation |
|---|---|---|
| Articulations visibles | Bras/jambes semblent découpés | Ajouter gants, manches, genouillères, overlap de sprites. |
| Animation trop “marionnette” | Mouvement fluide mais cheap | Ajouter poses clés fortes, squash/stretch léger, VFX. |
| Trop de pièces | Rig difficile à maintenir | Commencer avec 25-30 pièces max. |
| Trop peu de pièces | Mouvements limités | Ajouter uniquement les variantes nécessaires. |
| Personnage trop grand dans 256×256 | Coupures visuelles | Rendre en 512 puis downscale/crop contrôlé. |
| Anchor instable | Pieds qui glissent | Fixer l’origine au sol dans Blender et valider par script. |
| Pygbag trop lourd | Web build lent | Exclure `assets_source/` et `.blend` du build. |
| Timings incohérents | Le hit ne correspond pas au sprite | Introduire `animation_events.json`. |

---

## 14. Recommandation finale

La meilleure v2 n’est pas une migration de moteur.

La meilleure v2 est :

```text
ChatGPT image generation
  -> personnage 2D découpé en parties
  -> Blender rig 2D / pseudo-2D
  -> rendu automatique PNG transparent
  -> manifest compatible avec assets/fighters/
  -> Pygame garde le gameplay
```

À court terme, viser uniquement :

```text
rose_kunoichi_v2:
  idle: 8 frames
  walk: 8 frames
  punch_mid: 6 frames
```

Si cette verticale donne une animation stable, lisible et agréable en jeu, alors la pipeline est validée et le reste devient un travail de production, pas une incertitude technique.

---

## 15. Première todo-list opérationnelle

1. Créer `assets_source/fighters/rose_kunoichi_v2/`.
2. Générer une référence globale propre de Rose, facing right.
3. Générer une planche de parties séparées.
4. Découper/nettoyer 25-35 PNG dans `parts/`.
5. Créer `rig_config.json`.
6. Créer un premier fichier Blender avec pose neutre reconstruite.
7. Script Blender : exporter une seule frame `idle_000.png`.
8. Script Blender : exporter `idle` 8 frames.
9. Générer un `manifest.json` minimal.
10. Brancher temporairement `fighter_id="rose_kunoichi_v2"` dans le jeu.
11. Vérifier anchor, échelle, sol, flip.
12. Ajouter `walk`.
13. Ajouter `punch_mid`.
14. Jouer une minute et comparer v1/v2.
15. Décider si la pipeline est validée avant de produire tout le pack.
