# Sources optionnelles à télécharger manuellement

## Freesound

Ces sources peuvent améliorer les voix mais nécessitent souvent une connexion Freesound :

1. `Female Grunts For Games` — SkyRaeVoicing — CC-BY 3.0
   - Usage : grunts de combat féminin.
   - À couper en plusieurs clips courts : punch, kick, hurt, projectile_throw.

2. `Girl Taking Damage` — mvVoiceActing — CC0
   - Usage : variations de hurt féminines.

3. `rpg - cute girl battle sounds.wav` — mvVoiceActing — CC0
   - Usage : voix féminines plus anime/RPG ; à utiliser seulement si le style convient.

Place les fichiers téléchargés dans `downloads/manual/`, puis lance :

```bash
python scripts/download_and_prepare_audio.py --prepare-manual
```

Le script ne découpe pas automatiquement les longs fichiers Freesound avec précision artistique. Le plus propre est de les couper dans Audacity en clips de 0,2 à 0,8 s.
