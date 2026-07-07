# V2 — Correction des poses accroupies et du salto

Cette version remplace les frames problématiques de la V1.

## Problème en V1

Les frames `crouch_idle` et `crouch_walk` étaient obtenues par compression verticale du sprite source. Le résultat donnait l'impression que le personnage était aplati, pas qu'il s'accroupissait.

Certaines frames de `double_jump_salto` combinaient rotation et ajustement de taille, ce qui pouvait donner l'impression que le personnage rétrécissait.

## Correction en V2

### Accroupissement

Les frames accroupies ont été reconstruites avec une pose articulée :

- pieds conservés au sol ;
- genoux fortement pliés ;
- bassin abaissé ;
- tête abaissée ;
- torse, tête, bras et jambes gardant leurs volumes habituels ;
- aucun scaling vertical du personnage.

Le rendu doit donc se lire comme un vrai crouch / duck walk, pas comme une image écrasée.

### Salto / double saut

Le salto est maintenant construit avec une pose compacte :

- genoux ramenés vers le torse ;
- pieds et bras regroupés ;
- rotation de cette pose groupée ;
- aucune réduction d'échelle de l'image.

Le personnage paraît plus compact parce qu'il se met en boule, pas parce que le sprite est réduit.

## Conséquences gameplay

Les règles de hurtbox ne changent pas :

```python
CROUCH_HEIGHT_MULTIPLIER = 0.50
CROUCH_WALK_SPEED_MULTIPLIER = 0.42
```

Mais visuellement, le basculement vers `CROUCH` est désormais beaucoup plus crédible.
