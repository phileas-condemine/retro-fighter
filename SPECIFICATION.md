# Spécification — Retro Fighter

## 1. Objectif

Créer un prototype local en Python d'un jeu de combat 2D rétro-gaming, jouable au clavier, avec un adversaire contrôlé par ordinateur.

La version actuelle vise à valider les mécaniques fondamentales : déplacement, attaque, blocage, hauteur, hitstun, portée, timing, IA et interface de combat.

## 2. Périmètre de la première version

### Inclus

- Un joueur humain.
- Un adversaire IA.
- Une arène 2D fixe.
- Deux barres de vie.
- Un timer de round.
- Menu de sélection de difficulté IA.
- Combattants représentés par des sprites (packs `rose_kunoichi` et `shinobi`, voir `assets/fighters/`), avec une variante graphique HD alternative (bêta), voir 5.6.
- Attaques à trois hauteurs.
- Blocages à trois hauteurs.
- Saut, avec double saut (salto) permettant de passer par-dessus l'adversaire.
- Accroupissement (hurtbox réduite, esquive coups hauts et projectiles à hauteur d'épaules).
- Attaque à distance par personnage (shuriken / boule d'énergie), voir `retro_fighter/projectiles.py`.
- Déplacement latéral.
- Dash (double appui gauche/droite), voir 4.9.
- Debug hitboxes/hurtboxes.

### Non inclus dans cette version

- Combos avancés.
- Inputs de type quart de cercle.
- Super jauge.
- Menu complet de jeu final.
- Multijoueur local à deux joueurs.
- Manettes.

## 3. Contrôles

Le joueur humain utilise (touches données en AZERTY ; `Q` devient `A` en QWERTY, le reste est identique sur les deux layouts puisque S/D/F occupent la même position physique) :

- Flèche gauche/droite : déplacement.
- Flèche haut/bas : modificateur de hauteur.
- `Q` (`A` en QWERTY) : coup de poing.
- `S` : coup de pied.
- `D` : blocage.
- `Espace` : saut (en l'air : double saut/salto).
- `F` : attaque à distance.

La hauteur vaut :

- `haut` si la flèche haut est maintenue ;
- `bas` si la flèche bas est maintenue ;
- `milieu` sinon.

Cela s'applique aux attaques et au blocage. Au sol, sans attaque ni blocage, maintenir `bas` seul déclenche l'accroupissement plutôt qu'un simple modificateur de hauteur.

## 4. Système de combat

### 4.1 États d'un combattant

Chaque combattant est piloté par une machine à états finis :

- `idle` : immobile.
- `walk` : déplacement latéral.
- `jump` : en l'air (premier saut).
- `double_jump` : second saut, animation de salto.
- `crouch` / `crouch_walk` : accroupi, immobile ou en déplacement lent.
- `attack` : attaque en cours.
- `ranged_attack` : attaque à distance en cours (charge puis lancer).
- `block` : blocage maintenu.
- `blockstun` : interruption courte après blocage correct.
- `hitstun` : interruption après coup reçu.
- `ko` : plus de points de vie.

### 4.2 Attaques

Il existe deux familles d'attaque :

- `punch` : rapide, courte portée, dégâts modestes.
- `kick` : plus lente, meilleure portée, dégâts plus élevés.

Chaque famille est déclinée en :

- `high` ;
- `mid` ;
- `low`.

Une attaque possède :

- `startup_frames` : délai avant impact possible ;
- `active_frames` : fenêtre pendant laquelle elle peut toucher ;
- `recovery_frames` : délai après l'attaque (avant fatigue — voir 4.10) ;
- `damage` ;
- `range_px` ;
- `blockstun_frames` : interruption du défenseur si bloqué ;
- `hitstun_frames` : interruption du défenseur si touché (pas bloqué).

`hitstun_frames` est propre à chaque coup (poing : 16 frames ≈ 0,27s ; pied : 26 frames ≈ 0,43s) — voir 4.10 pour pourquoi ce n'est plus une durée fixe globale. Seules les attaques à distance utilisent encore une durée fixe (`HITSTUN_FRAMES` dans `config.py`, 0,5s), n'ayant pas cette distinction poing/pied.

### 4.3 Hitbox et hurtbox

Chaque combattant a une hurtbox corporelle.

Pendant les frames actives d'une attaque, une hitbox est créée devant le combattant, à la hauteur correspondant à l'attaque.

Si la hitbox croise la hurtbox adverse :

1. Le coup touche si l'adversaire ne bloque pas à la bonne hauteur.
2. Le coup est bloqué si l'adversaire maintient le blocage à la même hauteur.
3. En cas de hit, l'attaque adverse est interrompue par `hitstun`.
4. En cas de blocage correct, l'adversaire subit un `blockstun` mais aucun dégât.

### 4.4 Simultanéité

Si deux attaques touchent exactement sur la même frame, les deux coups sont appliqués. Sinon, le premier coup actif interrompt l'autre personnage.

### 4.5 Blocage

Le blocage est maintenu avec `D`.

La hauteur du blocage est déterminée par haut/bas/neutre :

- `↑ + D` : blocage haut ;
- `D` seul : blocage milieu ;
- `↓ + D` : blocage bas.

Un blocage correct annule entièrement les dégâts.

### 4.6 Accroupissement

Maintenir `↓` seul (au sol, sans attaque ni blocage) passe en `crouch` ; ajouter `←`/`→` passe en `crouch_walk` (déplacement à vitesse réduite, `CROUCH_WALK_SPEED_MULTIPLIER`).

La hurtbox est réduite à `CROUCH_HEIGHT_MULTIPLIER` (50 %) de sa hauteur normale, les pieds restant ancrés au sol (seul le haut descend). Cette seule réduction géométrique suffit à esquiver les attaques hautes et les projectiles à hauteur d'épaules, sans règle de collision spéciale.

Cette réduction reste active pendant un coup de poing/pied bas lancé depuis l'accroupi (`ActiveAttack.started_crouching`, voir 4.2) : `Fighter.hurtbox` vérifie aussi ce cas, pas seulement `state in (CROUCH, CROUCH_WALK)`. Avant ce correctif, le passage à `state=ATTACK` pendant l'attaque faisait perdre la réduction de hurtbox alors que le personnage reste visuellement accroupi (animation `crouch_punch_low`/`crouch_kick_low`) — un projectile à hauteur d'épaules qui aurait dû être esquivé touchait quand même pendant toute la durée du coup. Un coup bas lancé **depuis debout** (`↓` pressé le même appui que l'attaque, sans avoir été accroupi la frame d'avant) n'a pas ce bénéfice : c'est une frappe basse rapide, pas un accroupissement, la hurtbox reste pleine hauteur.

### 4.7 Double saut et salto

Une fois en l'air après le premier saut, appuyer à nouveau sur `Espace` déclenche un second saut (`double_jump`), avec une pose de salto pendant une durée fixe avant de revenir à la pose de saut normale. Cette hauteur/durée supplémentaire permet de passer par-dessus l'adversaire (inversion des côtés) ou d'esquiver un projectile à hauteur d'épaules si le combattant est monté assez haut (`PROJECTILE_AVOID_Y_DELTA`).

Le blocage de collision corps à corps (`resolve_body_collision` dans `game.py`, qui maintient normalement un écartement minimal entre les deux combattants) est désactivé tant que l'un des deux combattants n'a pas les pieds au sol. Exiger un non-chevauchement strict des rectangles pleine hauteur (132 px) ne laissait qu'une marge de quelques pixels au-dessus du sommet du salto dans le pire cas de timing, rendant la fenêtre de franchissement extrêmement étroite. En désactivant le blocage dès qu'un combattant est en l'air (simple saut ou salto), franchir l'adversaire redevient fiable sans dépendre d'un timing pixel-perfect.

Pendant un `double_jump`, le déplacement latéral utilise `DOUBLE_JUMP_AIR_CONTROL_SPEED` (plus rapide que le contrôle aérien normal `AIR_CONTROL_SPEED`, et même que la marche `WALK_SPEED`), le temps que dure la pose de salto (`DOUBLE_JUMP_POSE_FRAMES`). Sans ce coup de vitesse, le déplacement aérien standard était trop lent pour franchir l'adversaire avant d'atterrir, même une fois la collision désactivée en l'air.

### 4.8 Attaque à distance

Touche `F`. Chaque personnage lance son propre projectile (`retro_fighter/projectiles.py`) : shuriken pour `shinobi`, boule d'énergie pour `rose_kunoichi`. L'action se déroule en deux temps visuels (`ranged_charge` puis `ranged_throw`), le projectile étant lancé à une frame précise du lancer, à hauteur d'épaules.

Résolution des collisions projectile/adversaire :

1. Accroupi : esquive (géométrie de hurtbox, voir 4.6).
2. En `double_jump` suffisamment haut : esquive.
3. Blocage haut ou milieu : bloqué, 0 dégât.
4. Sinon : touche, hitstun standard (`HITSTUN_FRAMES`).

### 4.9 Dash

Un double appui sur `←`/`→` (deuxième pression dans la fenêtre `DASH_INPUT_WINDOW_FRAMES`, 0,25 s) déclenche un état `dash` dédié : vitesse fixe `DASH_SPEED` (≈3,5x `WALK_SPEED`) pendant `DASH_DURATION_FRAMES` (≈0,16 s), dans la direction appuyée, indépendamment de l'orientation du personnage. Le dash n'est disponible qu'au sol, depuis `idle`/`walk`, et un cooldown `DASH_COOLDOWN_FRAMES` (0,5 s) empêche de l'enchaîner en boucle. Comme les autres actions engagées (attaque, saut), il se déroule jusqu'au bout sans annulation anticipée, mais reste interrompu par une touche subie comme n'importe quel autre état. Aucun sprite dédié : le rendu réutilise l'animation `walk` (voir `Renderer.animation_key`) pendant que le corps se déplace vite. Réservé au joueur humain (`HumanController`) ; l'IA ne l'utilise pas.

### 4.10 Endurance (stamina) et fatigue

**Problème corrigé.** Avant ce système, `HITSTUN_FRAMES` était une constante globale (0,5s = 30 frames) appliquée à toute attaque qui touchait, poing ou pied. Or un cycle complet de pied (`startup_frames + active_frames + recovery_frames`) ne durait qu'environ 27-29 frames — *plus court* que le hitstun qu'il infligeait. Résultat : dès qu'un combattant acculé dans un coin (sans place pour reculer) se faisait toucher une fois, l'attaquant avait toujours fini de récupérer avant que le défenseur ne sorte du hitstun, et pouvait relancer un coup indéfiniment — un enchaînement imparable, quel que soit le niveau du joueur. Le passage à un `hitstun_frames` propre à chaque attaque (4.2) plus courant que son propre cycle attaque+récupération règle déjà la majorité du problème ; l'endurance ajoute une seconde ligne de défense qui s'aggrave avec l'agressivité soutenue.

**Mécanique.** Chaque combattant a `Fighter.stamina` (flottant, 0 à `MAX_STAMINA`=100) :

- coûte `STAMINA_COST_PUNCH` (6) pour un poing, `STAMINA_COST_KICK` (16) pour un pied, `STAMINA_COST_RANGED` (12) pour une attaque à distance — prélevé au lancement du coup (`Fighter.start_attack`/`start_ranged_attack`) ;
- coûte `STAMINA_COST_BLOCK` (8) au défenseur à chaque coup ou projectile effectivement bloqué (`Fighter.receive_attack`/`receive_projectile_hit`) ;
- se régénère de `STAMINA_REGEN_PER_FRAME` (0,35/frame) uniquement quand l'état n'est ni `ATTACK`, ni `RANGED_ATTACK`, ni `HITSTUN`, ni `BLOCKSTUN` — un blocage maintenu sans subir de coup compte comme neutre et régénère ;
- toujours bornée à `[0, MAX_STAMINA]`.

**Effet (fatigue).** La stamina ne bloque aucune action directement. À chaque lancement d'attaque, `Fighter.start_attack` calcule une pénalité de récupération proportionnelle à la fatigue déjà accumulée *avant* ce coup :

```
extra_recovery = round(recovery_frames * FATIGUE_MAX_RECOVERY_PENALTY * (1 - stamina/MAX_STAMINA))
```

À pleine stamina, `extra_recovery=0` (aucun changement). À stamina nulle, la récupération est doublée (`FATIGUE_MAX_RECOVERY_PENALTY=1.0`, un coefficient heuristique à recalibrer via les logs de combat comme les valeurs de `attacks.py`). Cette pénalité est figée sur l'`ActiveAttack` au moment du lancement (`extra_recovery_frames`) et s'ajoute à `total_frames` pour déterminer la fin réelle du coup (`ActiveAttack.is_finished`) — le `startup`/`active` (donc le timing du hit) ne change pas, seule la traîne de récupération s'allonge.

Un attaquant qui enchaîne les pieds sans relâche épuise vite sa stamina (16/coup) et voit sa propre récupération grimper à chaque coup suivant, ouvrant une fenêtre de plus en plus large pour le défenseur — y compris acculé dans un coin. Les poings, moins coûteux (6/coup), gardent leur identité de coup rapide et « sûr », au prix de moins de dégâts/portée (4.2).

Le défenseur qui bloque beaucoup s'épuise aussi (8/blocage) : sa propre offense sera plus lente une fois la stamina basse, même s'il n'a pas attaqué — la fatigue s'applique au prochain coup lancé, quelle que soit la cause de la dépense.

**Interface.** Une jauge de stamina (bleue) est affichée sous chaque barre de vie (`Renderer.draw_health_bar`). Le journal de combat (`combat_log.py`) inclut la stamina courante de l'attaquant/du défenseur et la pénalité de fatigue (`fatigue+Nf`) dans le détail des lignes `attaque`/`blocage`/`tir_distance`, pour permettre le même type d'analyse a posteriori que le rééquilibrage des poings.

L'IA n'a aucune conscience de la stamina dans ses décisions (`ai.py` inchangé) : elle y est simplement soumise comme le joueur, au niveau mécanique.

## 5. IA

L'adversaire utilise une IA déterministe/règles avec aléas contrôlés.

### 5.1 Sparring

- Ne bouge pas.
- N'attaque pas.
- Ne bloque pas.
- Sert à tester les coups, les hauteurs et les portées.

### 5.2 Facile

- Réagit lentement.
- Attaque de façon peu fréquente.
- Gère mal les distances.
- Se trompe souvent de hauteur de blocage.
- Utilise rarement l'attaque à distance.

### 5.3 Moyen

- Maintient une distance approximative.
- Alterne poings et pieds.
- Bloque parfois à la bonne hauteur.
- Peut reculer ou sauter dans certaines situations.
- Utilise l'attaque à distance quand la distance dépasse ~180 px.

### 5.4 Difficile

- Réagit plus vite.
- Maintient mieux sa portée de pied.
- Punit les attaques ratées ou en recovery.
- Varie mieux les hauteurs.
- Bloque souvent correctement.
- S'accroupit en réaction à une attaque à distance adverse en vol.

### 5.5 Mode démo (IA vs IA)

Touche `Tab` (menu ou en match) : bascule `Game.demo_mode`. Quand actif, le combattant `PLAYER` est piloté par une seconde instance d'`AIController` (`Game.player_ai_controller`) au lieu du clavier, réglée sur le même niveau de difficulté que l'adversaire (`Game.ai_mode`). Les deux instances d'IA sont indépendantes (chacune garde son propre cooldown/état de décision) : à difficulté égale, les deux combattants ne se comportent donc pas de façon parfaitement symétrique.

En mode démo, les noms affichés (`Fighter.name`) passent de `PLAYER`/`CPU` à `CPU 1`/`CPU 2` (mis à jour dans `Game.reset_round()`), ce qui se répercute automatiquement dans les barres de vie, le journal de combat et le message de victoire.

### 5.6 Mode graphique LD / HD (bêta) / V2 (bêta)

Touche `G` (menu ou en match) : fait avancer `Game.graphics_variant` dans le
cycle `"ld" -> "hd" -> "v2" -> "ld"` (`Game.cycle_graphics_variant()`),
propagé à `Renderer.set_graphics_variant()`. Contrairement au mode démo,
c'est un pur changement d'affichage (`Renderer.sprite_sets[graphics_variant]
[fighter.fighter_id]`) : aucune remise à zéro du round n'est nécessaire, le
`fighter_id` logique (utilisé pour le son et les projectiles) ne change pas,
seul le pack de sprites lu change.

Les trois variantes sont préchargées au démarrage (`Renderer.__init__`),
donc basculer avec `G` est instantané. Le pack HD (`assets/fighters/hd/`,
généré par VLM à partir de planches de référence) est un *proof of concept*
avec 46 images par personnage sur les ~100 prévues à terme : `punch_low`,
`kick_low` et `block_low` n'existent pas encore côté HD (les versions
accroupies `crouch_punch_low`/`crouch_kick_low` si). `FighterSpriteSet.
get_frame()` retombe sur `idle` pour toute clé manquante — la logique de
dégâts/hitbox/timing de l'attaque reste inchangée, seule la pose affichée
est temporairement l'idle. Le pack shinobi HD est assemblé à partir de deux
sources : un manifest de base (`manifest.json`) et un manifest d'extension
(`extension_manifest_high_actions.json`, actions hautes) fusionnés par le
même mécanisme que les packs LD.

Le pack V2 (`assets/fighters/v2/`, pipeline Blender-rigged — voir
`blender/README.md`) n'existe pour l'instant que pour `rose_kunoichi` (pack
complet, parité totale avec les 20+1 clés du moteur). `Renderer.sprite_sets["v2"]`
ne construit un `FighterSpriteSet` que pour les `fighter_id` ayant
effectivement un `manifest.json` v2 sur disque ; `draw_fighter()` retombe en
cascade sur HD puis LD pour tout personnage sans pack v2 (aujourd'hui
`shinobi`), donc appuyer sur `G` jusqu'à V2 n'affecte visuellement que
Rose — l'adversaire reste en HD/LD sans planter.

## 6. Architecture logicielle

### `game.py`

Responsabilités :

- boucle principale ;
- gestion menu/pause/reset ;
- orchestration joueur + IA, avec bascule optionnelle en mode démo (IA vs IA) ;
- application des collisions et dégâts (mêlée et projectiles) ;
- spawn/déplacement/collision des projectiles ;
- tirage aléatoire de l'arène de fond à chaque nouveau round ;
- condition de fin de round ;
- alimentation du journal de combat chronologique (déplacements, sauts, accroupissements, attaques avec issue, dégâts, esquives, résultat) à chaque évènement pertinent, écrit sur disque à la fin de chaque combat.

### `fighter.py`

Responsabilités :

- état du combattant ;
- mouvement, dash ;
- saut, double saut/salto ;
- accroupissement (hurtbox réduite) ;
- attaque, attaque à distance ;
- hitstun (propre à chaque coup)/blockstun ;
- endurance (stamina) : coût par coup/blocage, régénération neutre, pénalité de fatigue sur la récupération (4.10) ;
- calcul hitbox/hurtbox ;
- réception des coups (mêlée et projectiles).

### `attacks.py`

Responsabilités :

- définition data-driven des attaques ;
- paramètres d'équilibrage ;
- bandes verticales haut/milieu/bas.

### `projectiles.py`

Responsabilités :

- définition data-driven des attaques à distance (dégâts, vitesse, timing, hitbox) ;
- association personnage → projectile.

### `ai.py`

Responsabilités :

- choix des actions adverses ;
- comportement par difficulté ;
- spacing ;
- blocage, esquive (accroupissement) des projectiles ;
- usage de l'attaque à distance ;
- punition des attaques adverses.

### `input_manager.py`

Responsabilités :

- conversion clavier vers commandes de combat ;
- abstraction commune humain/IA.

### `sprites.py`

Responsabilités :

- chargement des packs de sprites (`assets/fighters/<ld|hd>/<id>/`) et fusion des manifests d'extension ;
- chargement des sprites de projectiles (`assets/projectiles/`) ;
- lecture des animations (fps, boucle) et mise en cache du flip horizontal ;
- repli automatique sur l'animation `idle` pour toute clé absente du manifest actif (utilisé par le pack HD, encore incomplet — voir 5.6) ;
- lissage inter-images : `AnimationClip.frame_at()` retourne un fondu enchaîné (alpha-dissolve) entre l'image courante et la suivante au lieu d'un cut sec, proportionnel à la progression vers l'image suivante (y compris au bouclage fin→début d'une animation en loop). Ce n'est pas une interpolation de mouvement (les poses ne se déplacent pas, elles se surimpriment en fondu), mais ça adoucit le rendu des animations à peu d'images clés (packs HD notamment). Les images fondues sont des surfaces temporaires : non mises en cache par id() (fuite/collision garantie sinon), retournées telles quelles à chaque appel.

### `audio.py`

Responsabilités :

- chargement des sons par personnage et des sons communs (`assets/audio/`, clés `fighters`/`common` de `pygame_audio_mapping.json`) ;
- lecture superposée voix personnage + son commun (impact/whoosh/projectile) par évènement, pour un retour cohérent même quand la voix réelle d'un évènement manque encore pour un personnage ;
- sélection aléatoire d'une variation par évènement.

### `renderer.py`

Responsabilités :

- dessin du décor (arène tirée au hasard via `stages.py`, avec repli sur l'ancien décor procédural si l'arène est indisponible) ;
- dessin des combattants ;
- UI ;
- hitboxes de debug ;
- menu et overlays.

### `stages.py`

Responsabilités :

- chargement du manifest des arènes (`assets/backgrounds/arena_manifest.json`) ;
- mise en cache et redimensionnement des images d'arène (Pygame) ;
- tolérance aux manifests/fichiers manquants (retombe sur `None`/`False`, jamais d'exception).

### `combat_log.py`

Responsabilités :

- collecte des évènements du combat en cours (`CombatLogger.log()`), avec temps écoulé, personnage, action, distance à l'adversaire, succès/échec, dégâts ;
- écriture d'un fichier par combat sous `logs/` à la fin du round (KO, temps écoulé, ou reset manuel), nommé avec l'horodatage de son début ;
- tolérant : un combat qui n'a jamais démarré, ou une erreur d'écriture (système de fichiers en lecture seule, par exemple sous le build web), ne lève jamais d'exception — le jeu continue silencieusement sans journal dans ce cas.

## 7. Principes de conception

- Garder le gameplay indépendant des assets graphiques.
- Paramétrer les attaques dans un fichier dédié.
- Utiliser une machine à états simple et explicite.
- Construire d'abord un jeu jouable avec des rectangles.
- Ajouter le pixel-art seulement après validation du gameplay.
