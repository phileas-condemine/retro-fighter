# Format `arena_manifest.json`

Le manifest principal se trouve ici :

```text
assets/backgrounds/arena_manifest.json
```

Exemple d'entrée :

```json
{
  "id": "snow_mountain_temple",
  "name": "Temple des neiges",
  "theme": "Montagne enneigée / temple glacé",
  "file": "assets/backgrounds/arenas/snow_mountain_temple.png",
  "original": "assets/backgrounds/originals/snow_mountain_temple_original_1672x941.png",
  "palette": ["cold", "blue", "snow", "red banners"],
  "suggested_music": "cold_wind_temple_loop"
}
```

Champs utilisés par `code/stages.py` :

```text
id
name
file
theme
suggested_music
```

Les autres champs sont informatifs.
