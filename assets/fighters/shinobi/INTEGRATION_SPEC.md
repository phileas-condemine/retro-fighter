# Spécification d'intégration — personnage Shinobi

## Objectif
Remplacer le rendu géométrique du prototype par un rendu sprite animé sans modifier la logique centrale du jeu.

## Décision technique
Le moteur de combat conserve ses états et timings. Le renderer ne dessine plus des rectangles : il sélectionne une animation et affiche la frame correspondante.

## Convention de nommage
Les animations suivent la convention :

- `idle`
- `walk`
- `jump`
- `punch_high`, `punch_mid`, `punch_low`
- `kick_high`, `kick_mid`, `kick_low`
- `block_high`, `block_mid`, `block_low`
- `hitstun`
- `ko`

Cette convention correspond directement aux actions déjà prévues dans le prototype.

## Ancre
L'ancre est le point de contact au sol, placé à `x=128`, `y=214` dans chaque frame 256 × 256. Le renderer doit positionner le sprite ainsi :

```python
screen_x = fighter.x - anchor_x
screen_y = fighter.ground_y - anchor_y - fighter.vertical_offset
```

## Animation
Chaque animation a un FPS propre. Pour un prototype, il est acceptable de lier l'index de frame au `state_frame` du combattant.

## Hitboxes
Première intégration : conserver les hitboxes abstraites existantes.

Deuxième intégration : ajouter dans `manifest.json` des rectangles par frame :

```json
"hitboxes": {
  "punch_mid_002": [{"x": 160, "y": 120, "w": 55, "h": 25, "height": "mid"}]
}
```

## Effets séparés
À terme, les effets de coup ne devraient pas être inclus dans les frames du personnage. Ils devraient devenir des sprites séparés pour faciliter la synchronisation, la couleur, le scaling et la réutilisation.
