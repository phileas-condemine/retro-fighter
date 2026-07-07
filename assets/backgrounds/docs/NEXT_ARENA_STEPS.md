# Prochaines améliorations arènes

## V2 — arènes plus grandes

Créer des fonds 2048 × 576 ou 3072 × 576 pour permettre :

```text
- scrolling horizontal ;
- caméra centrée entre les deux combattants ;
- limites d'arène plus larges ;
- davantage de variation visuelle pendant le combat.
```

## V3 — parallaxe

Découper chaque arène en couches :

```text
background_sky.png
background_far.png
background_mid.png
foreground_floor.png
foreground_overlay.png
```

Puis déplacer chaque couche à une vitesse différente selon la caméra.

## V4 — animation légère

Ajouter des overlays animés :

```text
- neige qui tombe ;
- brouillard ;
- flammes/lave ;
- feuilles de bambou ;
- poussière de sable.
```

Cela peut se faire avec de petites particules Pygame plutôt qu'avec des vidéos.

## V5 — sélection d'arène dans le menu

Ajouter un vrai sous-menu :

```text
Mode IA
Arène
Personnage joueur
Personnage CPU
Démarrer
```
