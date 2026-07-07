# Intégration gameplay — attaques basses depuis accroupissement

## Problème à corriger

Dans le modèle de contrôle actuel, `↓ + poing` ou `↓ + pied` signifie généralement : attaque basse.

Mais après l'ajout de l'accroupissement, `↓` peut aussi signifier que le personnage est déjà dans l'état `CROUCH` ou `CROUCH_WALK`. Dans ce cas, l'animation `punch_low` ou `kick_low` debout devient moins cohérente : le personnage semble sortir de l'accroupissement pour faire une attaque basse, puis revenir baissé.

## Règle recommandée

Séparer deux cas :

```text
attaque basse depuis debout      -> punch_low / kick_low
attaque basse depuis accroupi    -> crouch_punch_low / crouch_kick_low
```

La hauteur d'attaque reste `low` dans les deux cas. Ce qui change est seulement la pose source.

## Pseudo-code

```python
def resolve_attack_animation(fighter, attack):
    if attack.height == "low" and fighter.is_crouching:
        if attack.kind == "punch":
            return "crouch_punch_low"
        if attack.kind == "kick":
            return "crouch_kick_low"

    return f"{attack.kind}_{attack.height}"
```

## États concernés

Utilise ces animations si le personnage est dans l'un des états suivants au moment où l'attaque est déclenchée :

```text
CROUCH
CROUCH_WALK
BLOCK_LOW, si tu autorises un contre rapide depuis garde basse
```

Évite ces animations si le personnage est en l'air, en hitstun, en blockstun ou en recovery.

## Hurtbox

Pendant `crouch_punch_low`, garde une hurtbox basse compacte :

```python
height_multiplier = 0.50
width_multiplier = 1.08
```

Pendant `crouch_kick_low`, élargis légèrement la hurtbox car la jambe est tendue :

```python
height_multiplier = 0.50
width_multiplier = 1.18
```

## Hitbox suggérée

### crouch_punch_low

```python
hitbox = {
    "x_offset": 34,
    "y_offset": -55,
    "width": 52,
    "height": 24,
    "height_band": "low",
}
```

### crouch_kick_low

```python
hitbox = {
    "x_offset": 50,
    "y_offset": -20,
    "width": 70,
    "height": 20,
    "height_band": "low",
}
```

Les offsets supposent une ancre aux pieds. Ajuste selon ton système exact de rectangles.

## Logique de priorité

Si tu veux un comportement type fighting game :

- le coup de poing accroupi est rapide et interrompt bien, mais a peu de portée ;
- le coup de pied accroupi est un balayage plus lent, plus long, et peut toucher un personnage debout ou accroupi ;
- le coup de pied accroupi peut être une bonne réponse aux projectiles si le joueur s'est déjà baissé.
