# Fusion des manifests

Les fichiers `extension_manifest.json` sont conçus comme des patches à ajouter aux manifests existants.

## Exemple

Manifest existant :

```json
{
  "fighter_id": "shinobi",
  "animations": {
    "idle": {...},
    "walk": {...}
  }
}
```

Extension :

```json
{
  "fighter_id": "shinobi",
  "animations_to_add": {
    "crouch_idle": {...},
    "ranged_throw": {...}
  }
}
```

Fusion minimale :

```python
base_manifest["animations"].update(extension_manifest["animations_to_add"])
```

## Chemins

Les animations de l'extension utilisent des chemins relatifs au dossier du fighter :

```text
assets/fighters/shinobi/extension_frames/crouch_idle_000.png
assets/fighters/shinobi/extension_sheets/crouch_idle.png
```

Tu peux soit :

1. garder `manifest.json` et `extension_manifest.json` séparés ;
2. fusionner les animations au chargement ;
3. créer un nouveau manifest consolidé.

## Recommandation

Pour un prototype, fais la fusion au chargement :

```python
manifest = load_json("assets/fighters/shinobi/manifest.json")
ext = load_json("assets/fighters/shinobi/extension_manifest.json")
manifest["animations"].update(ext["animations_to_add"])
```

Cela permet d'ajouter/enlever l'extension sans casser le pack de base.
