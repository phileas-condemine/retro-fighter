# Notes de tuning hitbox / hurtbox

## Philosophie

Les attaques basses depuis accroupissement doivent être plus cohérentes visuellement, mais elles peuvent aussi enrichir le gameplay.

## Crouch punch low

Rôle : petit jab bas, rapide, peu punitif.

Paramètres suggérés :

```python
damage = 5
startup_frames = 2
active_frames = [2, 3]
recovery_frames = 1
range = 52
interrupt_power = "light"
```

## Crouch kick low

Rôle : balayage bas, meilleure portée, plus de recovery.

Paramètres suggérés :

```python
damage = 8
startup_frames = 3
active_frames = [3, 4]
recovery_frames = 2
range = 70
interrupt_power = "medium"
can_trip = True  # optionnel, à implémenter plus tard
```

## Interaction avec projectiles

Ce pack complète le pack `crouch_projectile_salto_v2` :

- `crouch_idle` et `crouch_walk` permettent d'éviter les projectiles à hauteur d'épaule ;
- `crouch_punch_low` et `crouch_kick_low` permettent d'attaquer sans remonter visuellement ;
- le double saut / salto reste l'autre moyen d'esquive verticale.
