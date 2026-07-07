# Fusion des manifests

Chaque personnage possède un fichier :

```text
assets/fighters/<fighter_id>/extension_manifest.json
```

Il faut fusionner `animations_to_add` dans le manifest principal du personnage.

Exemple :

```python
base_manifest["animations"].update(extension_manifest["animations_to_add"])
```

Animations ajoutées :

```text
crouch_punch_low
crouch_kick_low
```

Ce pack ne remplace pas les animations `punch_low` et `kick_low` existantes. Elles restent utiles lorsque l'attaque basse est lancée depuis une posture debout.
