# Notes de tuning

## Accroupissement

- Si l'accroupissement est trop fort visuellement, passe `height_multiplier` de `0.50` à `0.58`.
- Si les projectiles touchent encore trop souvent, baisse la ligne de hurtbox accroupie ou monte légèrement le projectile.
- Si le déplacement accroupi est trop utile, réduis `CROUCH_WALK_SPEED_MULTIPLIER` de `0.42` à `0.35`.

## Projectiles

Réglages de départ :

```python
shuriken.speed = 560
shuriken.damage = 8
rose_energy_ball.speed = 455
rose_energy_ball.damage = 10
```

Pour éviter un jeu trop défensif :

- donne une récupération longue à l'attaque à distance ;
- rends l'attaque punissable si elle est esquivée par accroupissement ;
- limite le spam avec un cooldown ou une jauge spéciale.

## Double saut

Le salto ne doit pas être une invincibilité totale. Il doit éviter le projectile parce que la hurtbox passe au-dessus, pas parce que le personnage devient intouchable.

Réglage recommandé :

```python
DOUBLE_JUMP_VELOCITY = -520
PROJECTILE_AVOID_Y_DELTA = 90
```

## IA

Pour l'IA :

- facile : projectile rarement, ne réagit pas au projectile adverse ;
- moyen : utilise projectile si distance > 180 px ;
- difficile : projectile si l'adversaire marche vers elle/lui, s'accroupit contre projectile adverse, double jump occasionnellement.
