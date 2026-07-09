# Générer un pack v2 (parts ChatGPT + rig Blender)

Ce document couvre le pipeline **v2** : ChatGPT génère un jeu fixe de
**morceaux de personnage découpés** (19 fichiers phase-1) une seule fois, puis
`blender/` les rig et anime pour produire toutes les animations. C'est
l'inverse du pipeline documenté dans `HOW_TO_GENERATE_IMAGES.md`
("planches d'animation entières") — ce dernier reste la référence pour tout
ce qui est mécanique de navigateur/Playwright (upload de fichiers, bouton de
téléchargement mort, zoom avant validation, etc.), pas dupliqué ici.

Validé de bout en bout sur `rose_kunoichi` : 19 parts générées, rig posé,
22 animations rendues, pack complet (0 erreur/0 avertissement à
`validate_manifest.py --reference ld`), testé en jeu réel (headless).

## Vue d'ensemble

```text
1. Écrire/adapter assets_source/fighters/<fighter>_v2/PARTS_PROMPTS.md
   (mirror de shinobi_v2, adapté au style du personnage)
2. Générer les parts par lot (3 lots : tête/torse, bras/mains, jambes/bottes)
   sur fond VERT (#00FF00), pas "transparent" (voir piège ci-dessous)
3. Chroma-key + découpe locale de chaque planche en fichiers individuels
4. python blender/run_pipeline.py --fighter <id> --parts-dir ... --out ...
5. Valider (tools/sprites/validate_manifest.py), inspecter visuellement
   (zoom + contact sheet), ajuster rig_config.py / animation_defs.py
6. Renderer.set_graphics_variant("v2") pour un test en jeu réel headless
```

## Étape 1 — Prompts par lot, pas par pièce individuelle

Générer les 19 parts une par une (19 messages ChatGPT séparés) serait lent et
ferait dériver le style d'un message à l'autre. À la place, demander **une
planche par lot** (3 lots : tête/hair/torso/pelvis/sash ; bras/mains ; jambes/
bottes), chaque planche contenant plusieurs pièces isolées côte à côte —
même logique que `HOW_TO_GENERATE_IMAGES.md`'s "une planche, pas N images".

Utiliser les **frames HD existantes** du personnage (`idle_000.png`,
`punch_mid_000.png`, `walk_000.png`, `block_mid_000.png`) comme référence de
style/proportions plutôt que de générer une planche de référence dédiée — un
personnage déjà établi (ayant déjà un pack LD/HD validé) n'a pas besoin de ce
verrouillage initial, contrairement à un personnage entièrement nouveau
(voir `shinobi_v2/PARTS_PROMPTS.md` qui, lui, verrouille depuis une image de
référence dédiée générée une fois).

**Rappeler "pose neutre" dans CHAQUE prompt de lot.** Les références montrent
la garde de combat dynamique du personnage ; chaque morceau doit être dessiné
droit/neutre (bras le long du corps, jambe verticale) pour que le rig puisse
le reposer ensuite — sinon la pose de la référence se retrouve figée dans
chaque pièce. Piège identique à celui documenté dans
`HOW_TO_GENERATE_IMAGES.md` pour les planches d'animation, mais qui joue ici
dans l'autre sens (on demande une "pièce", pas une "pose").

## Piège critique : "fond transparent" ne donne PAS un vrai canal alpha

Demander à ChatGPT un "fond transparent" pour une pièce détourée produit une
image PNG **opaque en RGB**, avec un **motif de damier gris/blanc peint dans
les pixels eux-mêmes** — pas une vraie transparence. Ça se voit dans l'aperçu
ChatGPT (qui affiche l'image sur son propre damier de fond, masquant le
problème), mais se confirme en inspectant le fichier téléchargé :

```bash
py -c "from PIL import Image; im = Image.open('fichier.png'); print(im.mode)"
# affiche 'RGB', pas 'RGBA' -> pas de vraie transparence
```

**Solution : demander un fond vert uni (`#00FF00`), pas transparent**,
exactement la même technique que `HOW_TO_GENERATE_IMAGES.md` utilise déjà
pour les planches d'animation — puis chroma-key en local avec
`tools/sprites/chroma_key.py` :

```bash
py tools/sprites/chroma_key.py planche_verte.png planche_keyed.png
```

Vérifier ensuite la transparence réelle (alpha=0 en dehors du sujet) avant de
continuer, pas seulement visuellement — le viewer d'image de certains outils
ne respecte pas toujours le canal alpha correctement à l'affichage; composer
sur un damier généré localement pour confirmer :

```python
# voir tools/sprites/chroma_key.py pour la fonction chroma_key elle-même ;
# composer le résultat sur un damier gris/blanc généré en local (Pillow)
# avant de faire confiance visuellement à la transparence.
```

## Étape 2 — Découper une planche en pièces individuelles

`tools/sprites/split_grid_parts.py` détecte les composantes connexes de
pixels non-transparents (pas une grille naïve à cellules égales — une
planche générée ne s'aligne pas forcément sur une grille parfaite, et des
lignes adjacentes peuvent se chevaucher légèrement) :

```bash
py tools/sprites/split_grid_parts.py planche_keyed.png parts/ \
    --names "head,hair_front,hair_back,torso,pelvis,accessory_main" \
    --pad 12 --rows 2
```

Le regroupement en lignes se fait par les **plus gros écarts de centre-Y**
entre pièces triées (pas un seuil fixe en pixels) : des pièces d'une même
ligne peuvent avoir des étendues verticales très différentes (une écharpe qui
pend bas vs. un torse compact), donc un seuil fixe sur `y0` classe parfois
une pièce dans la mauvaise ligne. Toujours vérifier l'ordre en sortie contre
l'aperçu visuel de la planche avant de faire confiance aux noms de fichiers.

### Piège vécu : un script de debug ad hoc peut écraser un fichier déjà bon

En corrigeant un problème d'échelle sur `hand_front_fist.png` (voir plus
bas), un script ponctuel de recadrage proportionnel a réutilisé les noms
`hand_back`/`hand_front_open` pour ses résultats de test **sans dilation**
(donc avec des doigts fragmentés en mini-blobs) et les a sauvegardés
directement dans `parts/`, écrasant silencieusement les bons fichiers produits
plus tôt par `split_grid_parts.py`. Le bug n'a été détecté que bien plus
tard, en rendu Blender (`hand_back.png` faisait 79×31px — clairement un
fragment, pas une main). **Toujours regarder la taille en pixels de chaque
fichier avant de faire confiance à un script de recadrage ponctuel**, et
préférer sauvegarder les résultats d'expérimentation sous un nom temporaire
(`_test.png`) avant de les promouvoir vers `parts/`.

## Étape 3 — Pièces interchangeables (ex. main ouverte/poing) : même cadrage

`blender/pipeline.py` mappe l'image ENTIÈRE d'une pièce sur le plan qui
représente son joint, ancré au pivot du joint (pas de recentrage automatique
par pièce). Deux pièces censées être interchangeables au même joint
(`hand_front_open.png` / `hand_front_fist.png`) doivent donc avoir le poignet
positionné à la **même fraction de hauteur depuis le haut de l'image**, sinon
la main "saute" visuellement quand le jeu bascule entre les deux.

Si les deux images viennent de générations séparées (zoom différent), ne pas
se contenter d'un pad fixe en pixels — calculer le pad comme une **fraction
de la hauteur brute** de chaque image, avec la même fraction pour les deux :

```python
pad_frac = 12 / 243  # pad pixel / hauteur brute de la version qui marche déjà
pad = round(hauteur_brute_de_lautre_image * pad_frac)
```

## Étape 4 — Lancer la pipeline

```bash
python blender/run_pipeline.py --fighter rose_kunoichi \
    --parts-dir assets_source/fighters/rose_kunoichi_v2/parts \
    --out assets/fighters/v2/rose_kunoichi \
    --anims idle,walk,dash,jump,double_jump_salto,crouch_idle,crouch_walk,punch_high,punch_mid,punch_low,kick_high,kick_mid,kick_low,crouch_punch_low,crouch_kick_low,block_high,block_mid,block_low,hitstun,ko,ranged_charge,ranged_throw
```

Puis valider :

```bash
py tools/sprites/validate_manifest.py assets/fighters/v2/rose_kunoichi --reference assets/fighters/ld/rose_kunoichi
```

## Étape 5 — Inspecter visuellement (zoom, pas juste un coup d'œil)

Même règle que `HOW_TO_GENERATE_IMAGES.md`'s étape 3 : ne jamais faire
confiance à un rendu 256×256 à l'œil nu, toujours zoomer (×3 minimum) :

```python
from PIL import Image
im = Image.open("assets/fighters/v2/<fighter>/frames/idle_000.png")
im.resize((im.width*3, im.height*3), Image.LANCZOS).save("zoom.png")
```

Pour balayer plusieurs animations d'un coup, construire une planche de
contact (quelques frames par animation, en grille) plutôt que d'ouvrir
chaque fichier un par un — beaucoup plus rapide pour repérer un membre
disloqué ou une silhouette illisible sur l'ensemble du pack.

### Piège vécu : un fichier de pièce corrompu peut produire un objet flottant sans rapport

Après le premier rendu complet, un disque plat rose/noir flottait à hauteur
de hanche, détaché du corps. Le diagnostic par élimination (masquer/renommer
des fichiers `.png` en `.png.hide` un par un, un groupe de joints à la fois,
puis relancer un rendu `idle` minimal à chaque fois) a fini par isoler
`hand_back.png` — c'était le fichier corrompu 79×31px du piège de l'étape 2.
**La forme, la couleur et la position bizarres d'un artefact ne donnent
presque jamais d'indice fiable sur quelle pièce est en cause** — un plan
Blender mal dimensionné ou mal tourné ne ressemble à rien d'anatomiquement
reconnaissable une fois affiché à plat. Isoler par élimination binaire
(cacher la moitié des pièces suspectes, observer si le défaut disparaît) est
bien plus rapide que d'essayer de deviner depuis l'image rendue.

## Étape 6 — Accroupissement : translation du bassin, pas seulement rotation

Plier les jambes par rotation seule (sans bouger le bassin) lève les pieds
du sol au lieu de faire s'accroupir le personnage — la distance hanche-
cheville se raccourcit mécaniquement. `Keyframe.root_offset` (voir
`blender/animation_defs.py`) permet de translater le joint racine vers le
bas pour compenser, en plus de la rotation des cuisses/tibias.

**Ne pas calculer la valeur par pure trigonométrie à la main** — les
approximations de rotation composée (cuisse puis tibia, chacun dans le
référentiel local du parent) sont difficiles à vérifier sans un rendu
interactif. Plus rapide et plus fiable : essayer une valeur raisonnable,
**mesurer le résultat rendu par pixels** (bbox du canal alpha), comparer au
point d'ancrage attendu, corriger par un calcul de correction linéaire
simple :

```python
from PIL import Image
import numpy as np
im = Image.open("frame.png").convert("RGBA")
a = np.array(im.split()[-1])
ys, xs = np.where(a > 10)
print("pieds (y max):", ys.max(), "attendu ~anchor.y")
```

### Piège critique : les pieds au bon endroit ne veulent pas dire une pose correcte

Une première correction (pieds vérifiés pixel-perfect à `anchor.y`) donnait
quand même un personnage qui **lit visuellement comme allongé en diagonale**,
pas accroupi — malgré une cinématique mathématiquement juste. La mesure de
pixels ne valide que l'ancrage, jamais la lisibilité de la silhouette
elle-même ; il faut zoomer et regarder la pose entière, pas seulement le bas
du cadre. Deux essais successifs d'ajustement d'angles à la main n'ont rien
donné de mieux — le vrai problème n'était pas une question de précision mais
de **deux erreurs qualitatives** :

1. **Le signe du pitch du torse était inversé.** Une valeur négative (choisie
   en supposant, par analogie avec la convention des cuisses où négatif
   avance le genou, que négatif = "penché en avant") faisait en réalité
   pencher le torse **en arrière**. Rien ne l'avait révélé avant, parce que
   les autres usages du torse dans ce fichier (léger balancement idle, légère
   inclinaison pendant un coup de poing) utilisaient des magnitudes trop
   petites pour que l'erreur de signe soit visible — une pose statique tenue
   (l'accroupissement) est justement le cas où une erreur de signe modérée
   saute aux yeux.
2. **Le pli du genou était beaucoup trop faible** (~20-40° de flexion réelle)
   pour un accroupissement, qui en réclame ~80-110°. Une cuisse à peine
   inclinée + un tibia qui prolonge presque la même diagonale donne un membre
   qui "pend" au lieu de plier franchement au genou.

**Solution qui a marché : demander une évaluation visuelle externe.** Envoyer
le rendu actuel + une image de référence (ici la frame HD existante) à
ChatGPT avec une question ciblée ("qu'est-ce qui cloche concrètement, en
degrés, articulation par articulation ?") a produit un diagnostic quantitatif
précis (torse : ~45-60° en avant au lieu de ~10-25° en arrière ; genou :
angle interne ~80-95° au lieu de ~140-160°) qui a débloqué la pose au premier
essai suivant. Utile quand on tourne en rond sur un problème "ça n'a pas l'air
juste mais je ne sais pas pourquoi" après plusieurs itérations sans progrès
visible — un œil extérieur (même artificiel) détecte des erreurs qualitatives
(mauvais sens de rotation, mauvaise articulation qui devrait porter le
mouvement) qu'une correction purement numérique/pixel ne révèle pas.

**Piège annexe : une jambe pliée profondément a une cheville plus haute
qu'une jambe peu pliée**, donc les DEUX jambes d'un accroupissement
asymétrique (genou avant haut, jambe arrière repliée) doivent être résolues
pour atterrir à la **même hauteur de cheville** avant de choisir un
`root_offset` commun — sinon une des deux jambes flotte ou s'enfonce, quel
que soit l'offset choisi (un seul offset ne peut planter qu'une profondeur à
la fois).

Une première tentative à `root_offset=(0,0,-0.30)` a enfoncé les pieds
22px trop bas dans le sol (mesuré, pas juste "à l'œil") ; corrigé à `-0.10`
en appliquant le ratio pixels→BU de la caméra (`target_height_px / CHARACTER_
HEIGHT`), qui a ramené les pieds exactement à `anchor.y`.

## Étape 7 — KO et autres poses extrêmes : garder la rotation modeste

Une première version de `ko` pivotait le torse à 85° pour simuler
l'effondrement. Rendu : la tête et les bras se retrouvaient visuellement
détachés du bassin/jambes (qui, eux, ne pivotent pas — le rig ne fait que
tourner les joints, il ne translate pas le bassin vers l'avant à mesure que
le torse plonge). **Un membre pivoté au-delà d'un certain angle, dans un rig
FK sans translation compensatoire, cesse de lire comme "un corps qui
s'effondre" et commence à lire comme "des pièces qui volent en éclats".**
Plafonner la rotation (torse capé à ~48° au lieu de 85°) donne un
affaissement/trébuchement crédible plutôt qu'un collapse complet parfait —
compromis accepté explicitement par `blender/README.md`, pas un blocage.

## Étape 8 — Câbler `v2` dans le moteur pour un vrai test en jeu

`Renderer.sprite_sets["v2"]` se construit **uniquement pour les personnages
qui ont déjà un `manifest.json` v2** (sinon `FighterSpriteSet.__init__`
lève une exception au chargement — un personnage sans pack v2, comme
`shinobi` tant qu'il n'a pas encore été traité, ne doit pas faire planter la
construction du `Renderer`). `Renderer.set_graphics_variant("v2")` force le
rendu v2 indépendamment du toggle LD/HD existant ; `draw_fighter` retombe
sur HD/LD pour tout personnage absent de `sprite_sets["v2"]`.

Test headless (même schéma que `HOW_TO_GENERATE_IMAGES.md`'s étape 10) :

```python
game = Game()
game.start_match("sparring")
game.renderer.set_graphics_variant("v2")
# ... boucler quelques frames, game.renderer.draw(game), pygame.image.save(...)
```

## Répéter pour un autre personnage (ex. Shinobi)

`rig_config.py`/`animation_defs.py` sont déjà génériques (character-agnostic)
— répéter ce pipeline pour un nouveau personnage devrait se limiter à :
1. Écrire/adapter son `PARTS_PROMPTS.md` (déjà fait pour `shinobi_v2`).
2. Générer les 19 parts phase-1 (étapes 1-3 ci-dessus).
3. Lancer la pipeline (étape 4) — pas de nouveau travail de rig/animation
   attendu, sauf si ses proportions réelles nécessitent des overrides dans
   `rig_config.py` une fois les vraies pièces visibles.
