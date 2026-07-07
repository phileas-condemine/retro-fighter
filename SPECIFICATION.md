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
- Combattants représentés par des sprites (packs `rose_kunoichi` et `shinobi`, voir `assets/fighters/`).
- Attaques à trois hauteurs.
- Blocages à trois hauteurs.
- Saut, avec double saut (salto) permettant de passer par-dessus l'adversaire.
- Accroupissement (hurtbox réduite, esquive coups hauts et projectiles à hauteur d'épaules).
- Attaque à distance par personnage (shuriken / boule d'énergie), voir `retro_fighter/projectiles.py`.
- Déplacement latéral.
- Debug hitboxes/hurtboxes.

### Non inclus dans cette version

- Combos avancés.
- Inputs de type quart de cercle.
- Super jauge.
- Menu complet de jeu final.
- Multijoueur local à deux joueurs.
- Manettes.

## 3. Contrôles

Le joueur humain utilise :

- Flèche gauche/droite : déplacement.
- Flèche haut/bas : modificateur de hauteur.
- `J` : coup de poing.
- `K` : coup de pied.
- `L` : blocage.
- `Espace` : saut (en l'air : double saut/salto).
- `U` : attaque à distance.

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
- `recovery_frames` : délai après l'attaque ;
- `damage` ;
- `range_px` ;
- `blockstun_frames`.

Le hitstun n'est pas propre à chaque attaque : toute attaque non bloquée qui touche inflige la même durée fixe de hitstun (`HITSTUN_FRAMES`, 0,5 seconde à 60 FPS).

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

Le blocage est maintenu avec `L`.

La hauteur du blocage est déterminée par haut/bas/neutre :

- `↑ + L` : blocage haut ;
- `L` seul : blocage milieu ;
- `↓ + L` : blocage bas.

Un blocage correct annule entièrement les dégâts.

### 4.6 Accroupissement

Maintenir `↓` seul (au sol, sans attaque ni blocage) passe en `crouch` ; ajouter `←`/`→` passe en `crouch_walk` (déplacement à vitesse réduite, `CROUCH_WALK_SPEED_MULTIPLIER`).

La hurtbox est réduite à `CROUCH_HEIGHT_MULTIPLIER` (50 %) de sa hauteur normale, les pieds restant ancrés au sol (seul le haut descend). Cette seule réduction géométrique suffit à esquiver les attaques hautes et les projectiles à hauteur d'épaules, sans règle de collision spéciale.

### 4.7 Double saut et salto

Une fois en l'air après le premier saut, appuyer à nouveau sur `Espace` déclenche un second saut (`double_jump`), avec une pose de salto pendant une durée fixe avant de revenir à la pose de saut normale. Cette hauteur/durée supplémentaire permet de passer par-dessus l'adversaire (inversion des côtés) ou d'esquiver un projectile à hauteur d'épaules si le combattant est monté assez haut (`PROJECTILE_AVOID_Y_DELTA`).

Le blocage de collision corps à corps (`resolve_body_collision` dans `game.py`, qui maintient normalement un écartement minimal entre les deux combattants) est désactivé tant que l'un des deux combattants n'a pas les pieds au sol. Exiger un non-chevauchement strict des rectangles pleine hauteur (132 px) ne laissait qu'une marge de quelques pixels au-dessus du sommet du salto dans le pire cas de timing, rendant la fenêtre de franchissement extrêmement étroite. En désactivant le blocage dès qu'un combattant est en l'air (simple saut ou salto), franchir l'adversaire redevient fiable sans dépendre d'un timing pixel-perfect.

Pendant un `double_jump`, le déplacement latéral utilise `DOUBLE_JUMP_AIR_CONTROL_SPEED` (plus rapide que le contrôle aérien normal `AIR_CONTROL_SPEED`, et même que la marche `WALK_SPEED`), le temps que dure la pose de salto (`DOUBLE_JUMP_POSE_FRAMES`). Sans ce coup de vitesse, le déplacement aérien standard était trop lent pour franchir l'adversaire avant d'atterrir, même une fois la collision désactivée en l'air.

### 4.8 Attaque à distance

Touche `U`. Chaque personnage lance son propre projectile (`retro_fighter/projectiles.py`) : shuriken pour `shinobi`, boule d'énergie pour `rose_kunoichi`. L'action se déroule en deux temps visuels (`ranged_charge` puis `ranged_throw`), le projectile étant lancé à une frame précise du lancer, à hauteur d'épaules.

Résolution des collisions projectile/adversaire :

1. Accroupi : esquive (géométrie de hurtbox, voir 4.6).
2. En `double_jump` suffisamment haut : esquive.
3. Blocage haut ou milieu : bloqué, 0 dégât.
4. Sinon : touche, hitstun standard (`HITSTUN_FRAMES`).

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

## 6. Architecture logicielle

### `game.py`

Responsabilités :

- boucle principale ;
- gestion menu/pause/reset ;
- orchestration joueur + IA ;
- application des collisions et dégâts (mêlée et projectiles) ;
- spawn/déplacement/collision des projectiles ;
- condition de fin de round.

### `fighter.py`

Responsabilités :

- état du combattant ;
- mouvement ;
- saut, double saut/salto ;
- accroupissement (hurtbox réduite) ;
- attaque, attaque à distance ;
- hitstun/blockstun ;
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

- chargement des packs de sprites (`assets/fighters/`) et fusion des manifests d'extension ;
- chargement des sprites de projectiles (`assets/projectiles/`) ;
- lecture des animations (fps, boucle) et mise en cache du flip horizontal.

### `audio.py`

Responsabilités :

- chargement des sons par personnage et des sons communs (`assets/audio/`, clés `fighters`/`common` de `pygame_audio_mapping.json`) ;
- lecture superposée voix personnage + son commun (impact/whoosh/projectile) par évènement, pour un retour cohérent même quand la voix réelle d'un évènement manque encore pour un personnage ;
- sélection aléatoire d'une variation par évènement.

### `renderer.py`

Responsabilités :

- dessin du décor ;
- dessin des combattants ;
- UI ;
- hitboxes de debug ;
- menu et overlays.

## 7. Principes de conception

- Garder le gameplay indépendant des assets graphiques.
- Paramétrer les attaques dans un fichier dédié.
- Utiliser une machine à états simple et explicite.
- Construire d'abord un jeu jouable avec des rectangles.
- Ajouter le pixel-art seulement après validation du gameplay.
