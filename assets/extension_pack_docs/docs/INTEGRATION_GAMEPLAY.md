# Intégration gameplay — accroupissement, projectile, salto

## 1. Accroupissement

### Intention

Quand le joueur maintient `DOWN` au sol, le combattant passe en état `CROUCH`. Sa hauteur visuelle et sa hurtbox sont réduites d'environ 50 %. Cela lui permet d'éviter les projectiles tirés à hauteur d'épaules.

Quand `DOWN + LEFT/RIGHT` est maintenu, il passe en `CROUCH_WALK` et se déplace lentement.

### Paramètres recommandés

```python
CROUCH_HEIGHT_MULTIPLIER = 0.50
CROUCH_WALK_SPEED_MULTIPLIER = 0.42
```

### Hurtbox

Il ne faut pas simplement réduire la hauteur depuis le centre. Il faut garder les pieds au sol :

```text
avant : hurtbox = x, y, width, height
après : bottom identique, height = height * 0.50
```

Ainsi le personnage devient vraiment bas et passe sous la ligne d'épaule.

### Animation

```python
if fighter.state == CROUCH:
    anim = "crouch_idle"
elif fighter.state == CROUCH_WALK:
    anim = "crouch_walk"
```

## 2. Attaque à distance

### Intention

Chaque personnage gagne une attaque spéciale simple à distance :

- `shinobi` : shuriken métallique, rapide, dégâts modérés ;
- `rose_kunoichi` : boule d'énergie rose/cyan, un peu plus lente, plus visible, dégâts légèrement supérieurs.

### États recommandés

```text
RANGED_STARTUP          -> ranged_charge
RANGED_ACTIVE_RECOVERY  -> ranged_throw
```

Tu peux enchaîner automatiquement :

```text
ranged_charge terminé -> ranged_throw
ranged_throw frame 3  -> spawn projectile
ranged_throw terminé  -> idle/walk
```

### Spawn projectile

Les manifests utilisent :

```json
{"x": 88, "y": -104}
```

Cela signifie :

```python
spawn_x = fighter.x + facing_sign * 88
spawn_y = fighter.ground_y - 104
```

Cette ligne correspond à un tir **à hauteur d'épaules / haut du corps** dans des frames 256×256 avec ancre `{x: 128, y: 214}`.

### Collision

Le projectile peut toucher si sa hitbox intersecte la hurtbox de l'adversaire.

Mais il doit rater dans deux cas :

```python
if target.state in (CROUCH, CROUCH_WALK):
    miss

if target.state == DOUBLE_JUMP and target.y is high enough:
    miss
```

### Blocage

Le projectile est à hauteur d'épaules. Je recommande :

```text
block_high : bloque
block_mid  : bloque
block_low  : ne bloque pas
crouch     : esquive sans blocage
```

## 3. Double saut / salto

### Intention

Le premier saut garde ton animation `jump` existante. Le second saut utilise `double_jump_salto`.

### Déclenchement

```python
if jump_pressed and not fighter.is_grounded and not fighter.double_jump_used:
    fighter.state = DOUBLE_JUMP
    fighter.vy = -520
    fighter.double_jump_used = True
```

### Reset

```python
if fighter.is_grounded:
    fighter.double_jump_used = False
```

### Interaction projectile

Le salto évite un projectile à hauteur d'épaules seulement si le personnage est suffisamment haut. Évite une invincibilité gratuite permanente.

Condition simple :

```python
if target.state == DOUBLE_JUMP and target.y < target.ground_y - 90:
    projectile_misses = True
```

Ajuste `90` selon ton système de coordonnées.

## 4. Priorités d'intégration

1. Charger les nouveaux manifests d'extension.
2. Ajouter les 5 nouvelles animations au resolver.
3. Ajouter `CROUCH` et `CROUCH_WALK` avec hurtbox réduite.
4. Ajouter une classe `Projectile` et une liste `projectiles` dans la boucle de jeu.
5. Déclencher `ranged_charge` puis `ranged_throw`.
6. Spawner le projectile à la frame 3 de `ranged_throw`.
7. Tester trois cas : debout touché, accroupi esquive, double saut esquive.
