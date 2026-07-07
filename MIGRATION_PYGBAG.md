# Guide de migration du jeu Pygame vers Pygbag + GitHub Pages

## 1. Objectif

L’objectif est de rendre le jeu Pygame jouable dans un navigateur via une URL publique GitHub Pages, tout en conservant le développement local en Python/Pygame.

La cible recommandée est :

```text
Développement local :
python run_game.py

Build web :
python -m pygbag --build .

Déploiement :
GitHub Actions → GitHub Pages
```

Pygbag est l’outil le plus adapté pour ce cas d’usage : il package un jeu Python/Pygame-ce en WebAssembly afin de le faire tourner dans un navigateur moderne. La documentation officielle indique que Pygbag sert à empaqueter des jeux Python 3 utilisant notamment `pygame-ce`, puis à les publier sur Internet.

---

## 2. Principe général

Un jeu Pygame desktop classique fonctionne avec une boucle bloquante :

```python
while running:
    handle_events()
    update()
    draw()
    pygame.display.flip()
    clock.tick(60)
```

Pour le navigateur, il faut rendre la boucle compatible avec l’event loop WebAssembly/navigateur :

```python
import asyncio

async def main():
    while True:
        handle_events()
        update()
        draw()
        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

asyncio.run(main())
```

Pygbag demande un fichier `main.py`, une fonction `async def main()`, et un `await asyncio.sleep(0)` dans la boucle principale afin de rendre la main au navigateur entre deux frames.

---

## 3. Arborescence cible du repo

Si le jeu est déjà à la racine du repo GitHub, viser cette structure :

```text
retro-fighter/
  main.py
  run_game.py
  requirements.txt
  src/
    game.py
    fighter.py
    renderer.py
    audio.py
    ai.py
    attacks.py
    projectiles.py
    ...
  assets/
    fighters/
    projectiles/
    audio/
    backgrounds/
    fonts/
  docs/
    MIGRATION_PYGBAG_GITHUB_PAGES.md
  .github/
    workflows/
      deploy-pygbag-pages.yml
```

Si le jeu est dans un sous-dossier, par exemple :

```text
repo/
  retro_fighter_project/
    main.py
    src/
    assets/
```

alors adapter les commandes de build avec :

```bash
python -m pygbag --build retro_fighter_project
```

---

## 4. Créer un point d’entrée web `main.py`

### Situation probable actuelle

Le projet local a probablement un point d’entrée du type :

```text
run_game.py
```

qui fait quelque chose comme :

```python
from src.game import Game

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
```

Pour Pygbag, le fichier contenant la boucle principale doit s’appeler `main.py`. La documentation Pygbag indique explicitement que le fichier avec la boucle de jeu doit être nommé `main.py`.

### Nouveau `main.py`

Créer un fichier `main.py` à la racine du projet :

```python
import asyncio
import pygame

from src.game import Game


async def main():
    pygame.init()
    game = Game()

    while game.running:
        game.handle_events()
        game.update()
        game.draw()

        pygame.display.flip()
        game.clock.tick(game.target_fps)

        # Obligatoire pour Pygbag / navigateur.
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 5. Adapter la classe `Game`

L’idéal est que `Game` ne contienne plus une méthode `run()` avec une boucle infinie interne. À la place, elle doit exposer trois méthodes appelées depuis `main.py` :

```python
class Game:
    def __init__(self):
        self.running = True
        self.target_fps = 60
        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((1280, 720))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # Gestion clavier, menus, pause, etc.
            self.handle_event(event)

    def update(self):
        dt = self.clock.get_time() / 1000.0

        # IA
        # physique
        # projectiles
        # collisions
        # animations
        # timers
        self.update_gameplay(dt)

    def draw(self):
        self.draw_background()
        self.draw_fighters()
        self.draw_projectiles()
        self.draw_ui()
```

### À éviter

Éviter ce modèle pour la version web :

```python
class Game:
    def run(self):
        while self.running:
            ...
```

Ce modèle fonctionne en desktop, mais il rend la migration web moins propre parce que la boucle est enfermée dans la classe.

### Variante acceptable

Si on veut garder `run_game.py` pour le desktop, on peut créer une méthode `tick()` :

```python
class Game:
    def tick(self):
        self.handle_events()
        self.update()
        self.draw()
        pygame.display.flip()
        self.clock.tick(self.target_fps)
```

Puis :

```python
# main.py, version web
import asyncio
import pygame
from src.game import Game

async def main():
    pygame.init()
    game = Game()

    while game.running:
        game.tick()
        await asyncio.sleep(0)

    pygame.quit()

asyncio.run(main())
```

Et :

```python
# run_game.py, version desktop
import pygame
from src.game import Game

def main():
    pygame.init()
    game = Game()

    while game.running:
        game.tick()

    pygame.quit()

if __name__ == "__main__":
    main()
```

C’est probablement le meilleur compromis pour ton projet.

---

## 6. Adapter les chemins d’assets

Tous les assets doivent être dans le dossier du projet, sinon Pygbag ne les embarquera pas dans le build web. La documentation Pygbag précise que les images, polices et sons doivent être placés dans le dossier du projet pour être packagés.

### Créer un helper de chemins

Ajouter `src/paths.py` :

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"


def asset_path(*parts: str) -> str:
    return str(ASSETS_DIR.joinpath(*parts))
```

Utilisation :

```python
from src.paths import asset_path

image = pygame.image.load(asset_path("fighters", "shinobi", "idle.png")).convert_alpha()
sound = pygame.mixer.Sound(asset_path("audio", "fighters", "common", "punch_hit.ogg"))
```

### Attention aux chemins Windows

Ne jamais écrire :

```python
"assets\\fighters\\shinobi\\idle.png"
```

Préférer :

```python
"assets/fighters/shinobi/idle.png"
```

ou utiliser `pathlib`. La documentation Pygbag recommande explicitement d’utiliser `/` plutôt que `\` dans les chemins.

---

## 7. Convertir les sons en OGG

Pour la version web, convertir les sons en `.ogg`.

Pygbag recommande que tous les fichiers audio soient au format OGG, compressés, et non en WAV/AIFF/M4A/MP3.

### Commande de conversion

Avec `ffmpeg` :

```bash
ffmpeg -i input.wav -ar 44100 -ac 1 -c:a libvorbis -q:a 5 output.ogg
```

Pour convertir tout un dossier sous Linux/macOS/Git Bash :

```bash
find assets/audio -name "*.wav" -print0 | while IFS= read -r -d '' file; do
  ffmpeg -y -i "$file" -ar 44100 -ac 1 -c:a libvorbis -q:a 5 "${file%.wav}.ogg"
done
```

Pour PowerShell :

```powershell
Get-ChildItem assets/audio -Recurse -Filter *.wav | ForEach-Object {
    $out = $_.FullName -replace "\.wav$", ".ogg"
    ffmpeg -y -i $_.FullName -ar 44100 -ac 1 -c:a libvorbis -q:a 5 $out
}
```

### Support desktop + web

Si on veut garder les WAV en local mais utiliser les OGG dans le navigateur :

```python
import sys
import pygame

def load_sound(base_path_without_ext: str) -> pygame.mixer.Sound:
    if sys.platform == "emscripten":
        return pygame.mixer.Sound(base_path_without_ext + ".ogg")
    return pygame.mixer.Sound(base_path_without_ext + ".wav")
```

Pygbag documente précisément cette logique conditionnelle avec `sys.platform == "emscripten"` pour charger un `.ogg` côté web et un autre format côté desktop.

---

## 8. Optimiser les images

Pour le web, éviter les très nombreux fichiers PNG non compressés si possible.

Actions recommandées :

```text
1. Garder les sprites en PNG transparents.
2. Regrouper les frames en spritesheets plutôt qu’en milliers de fichiers isolés.
3. Compresser les PNG avec oxipng, pngquant ou équivalent.
4. Éviter les BMP et formats bruts.
5. Garder une taille de canvas raisonnable : 1280×720 maximum pour une V1 web.
```

Pygbag recommande d’éviter les formats bruts comme BMP et d’utiliser des formats web comme PNG, WEBP ou JPG.

Exemples :

```bash
oxipng -o 4 -r assets/fighters
```

ou :

```bash
pngquant --quality=70-95 --ext .png --force assets/fighters/**/*.png
```

---

## 9. Gérer l’audio navigateur

Les navigateurs bloquent souvent l’audio avant une interaction utilisateur. Il faut donc prévoir un écran initial :

```text
CLICK / PRESS ENTER TO START
```

Puis initialiser ou débloquer l’audio après cette interaction.

Exemple simple :

```python
class Game:
    def __init__(self):
        self.started = False
        self.audio_unlocked = False

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if not self.started:
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    self.started = True
                    self.unlock_audio()
                return

            self.handle_gameplay_event(event)

    def unlock_audio(self):
        if self.audio_unlocked:
            return

        # Jouer un son silencieux ou très court peut aider à initialiser le mixer.
        # À adapter selon ton AudioManager.
        self.audio_unlocked = True
```

La documentation Pygbag indique qu’après le chargement, l’utilisateur doit pouvoir cliquer l’écran pour démarrer le jeu.

---

## 10. Garder le style pixel-art

Pour éviter que le navigateur lisse les pixels lors du scaling du canvas, ajouter dans `main.py` :

```python
import sys

if sys.platform == "emscripten":
    import platform
    platform.window.canvas.style.imageRendering = "pixelated"
```

Pygbag documente cette option pour conserver un rendu pixelisé côté navigateur.

---

## 11. Supprimer ou isoler les dépendances non compatibles web

Le jeu doit éviter :

```text
- accès fichiers hors dossier projet ;
- tkinter ;
- multiprocessing ;
- appels réseau synchrones ;
- chemins absolus locaux ;
- modules Python non disponibles dans le runtime WebAssembly ;
- dépendances lourdes inutiles comme numpy/pandas si elles ne sont pas nécessaires.
```

Pygbag recommande d’éviter les opérations I/O, GUI ou web via la bibliothèque standard CPython lorsqu’elles sont synchrones ou dépendantes de la plateforme.

Pour un jeu de combat Pygame, l’idéal est de rester sur :

```text
pygame-ce
json
math
random
dataclasses
enum
pathlib
typing
```

---

## 12. Installer Pygbag localement

Créer ou activer l’environnement virtuel :

```bash
python -m venv .venv
```

Windows PowerShell :

```powershell
.venv\Scripts\Activate.ps1
```

Linux/macOS/Git Bash :

```bash
source .venv/bin/activate
```

Installer :

```bash
python -m pip install --upgrade pip
python -m pip install pygbag
```

La documentation Pygbag donne la commande `pip install pygbag --user --upgrade`, et PyPI indique que Pygbag package et exécute du Python/Pygame-ce WebAssembly dans les navigateurs modernes.

---

## 13. Tester localement dans le navigateur

Depuis le dossier parent du jeu :

```bash
python -m pygbag .
```

ou, si le jeu est dans un sous-dossier :

```bash
python -m pygbag retro_fighter_project
```

Puis ouvrir :

```text
http://localhost:8000
```

La documentation Pygbag indique que la commande standard est `pygbag folder_name`, ou `python -m pygbag folder_name` si la commande `pygbag` n’est pas reconnue.

---

## 14. Build statique local

Pour générer les fichiers web sans lancer le serveur local :

```bash
python -m pygbag --build .
```

Le build produit normalement :

```text
build/
  web/
    index.html
    ...
```

Vérifier que `build/web/index.html` existe.

Ajouter éventuellement :

```bash
touch build/web/.nojekyll
```

Le fichier `.nojekyll` évite que GitHub Pages essaie de traiter le site comme un site Jekyll.

---

## 15. Configurer GitHub Pages

Dans GitHub :

```text
Repository
→ Settings
→ Pages
→ Build and deployment
→ Source: GitHub Actions
```

GitHub documente le déploiement Pages via GitHub Actions avec `actions/upload-pages-artifact` pour uploader les fichiers statiques, puis `actions/deploy-pages` pour déployer l’artefact.

---

## 16. Ajouter le workflow GitHub Actions

Créer :

```text
.github/workflows/deploy-pygbag-pages.yml
```

Contenu recommandé :

```yaml
name: Deploy Pygbag game to GitHub Pages

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "github-pages"
  cancel-in-progress: true

jobs:
  build:
    name: Build Pygbag web package
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Pygbag
        run: |
          python -m pip install --upgrade pip
          python -m pip install pygbag

      - name: Build web version
        run: |
          python -m pygbag --build --app_name "Retro Fighter" --title "Retro Fighter" .

      - name: Disable Jekyll
        run: |
          touch build/web/.nojekyll

      - name: Upload GitHub Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: build/web

  deploy:
    name: Deploy to GitHub Pages
    needs: build
    runs-on: ubuntu-latest

    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Deploy
        id: deployment
        uses: actions/deploy-pages@v4
```

Si le jeu n’est pas à la racine du repo, remplacer :

```yaml
python -m pygbag --build --app_name "Retro Fighter" --title "Retro Fighter" .
```

par :

```yaml
python -m pygbag --build --app_name "Retro Fighter" --title "Retro Fighter" retro_fighter_project
```

et remplacer :

```yaml
path: build/web
```

par :

```yaml
path: retro_fighter_project/build/web
```

---

## 17. Variante officielle Pygbag avec branche `gh-pages`

La documentation Pygbag fournit aussi une procédure GitHub Pages basée sur un fichier `.github/workflows/pygbag.yml`. Cette action crée une branche `gh-pages`, puis il faut configurer GitHub Pages pour publier depuis cette branche.

Cette approche fonctionne, mais pour un repo GitHub moderne, je recommande plutôt le workflow précédent avec :

```text
actions/upload-pages-artifact
actions/deploy-pages
Source: GitHub Actions
```

C’est plus aligné avec le modèle actuel de GitHub Pages.

---

## 18. Adapter `.gitignore`

Ajouter :

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
.env

# Pygbag outputs
build/
dist/
*-pygbag.*

# Optional desktop-only audio sources
*.wav
*.mp3

# Keep web-ready audio
!assets/**/*.ogg
```

Attention : si tu veux versionner les WAV source pour le desktop ou pour la production audio, ne pas ignorer globalement `*.wav`. Dans ce cas, préférer :

```gitignore
build/
dist/
*-pygbag.*
```

Pygbag liste aussi des ajouts utiles de `.gitignore`, dont `/build`, `/dist`, `*.pyc`, `*.wav`, `*.mp3` et `*-pygbag.???`.

---

## 19. Checklist de migration du code

### Boucle principale

```text
[ ] Il existe un main.py à la racine du jeu.
[ ] main.py importe asyncio.
[ ] La boucle principale est dans async def main().
[ ] La boucle contient await asyncio.sleep(0).
[ ] asyncio.run(main()) est appelé à la fin.
[ ] Aucune logique importante n’est placée après asyncio.run(main()).
```

### Assets

```text
[ ] Tous les assets sont sous assets/.
[ ] Aucun chemin absolu local.
[ ] Aucun asset chargé depuis ../ en dehors du projet.
[ ] Les chemins utilisent pathlib ou /.
[ ] Les images sont en PNG/WEBP/JPG, pas en BMP.
[ ] Les sons web sont en OGG.
```

### Audio

```text
[ ] Le jeu a un écran initial click/press key to start.
[ ] Le mixer n’est pas supposé actif avant interaction utilisateur.
[ ] Les sons WAV desktop ont une alternative OGG web.
[ ] Les volumes sont réglés plus bas côté navigateur.
```

### Performance

```text
[ ] Les sprites sont préchargés au démarrage.
[ ] Les sons sont préchargés au démarrage.
[ ] Aucune image n’est chargée à chaque frame.
[ ] Aucun son n’est chargé à chaque frame.
[ ] Les collisions utilisent des rects simples.
[ ] Les hitboxes debug peuvent être désactivées.
```

### GitHub Pages

```text
[ ] Le repo est public ou GitHub Pages est disponible sur le plan utilisé.
[ ] Settings → Pages → Source = GitHub Actions.
[ ] Le workflow deploy-pygbag-pages.yml existe.
[ ] Le workflow réussit sur main.
[ ] L’URL GitHub Pages charge index.html.
[ ] Le jeu démarre après clic/clavier.
```

---

## 20. Checklist de test navigateur

Tester au minimum :

```text
[ ] Chrome / Edge desktop
[ ] Firefox desktop
[ ] Chrome Android si pertinent
[ ] Safari iOS si pertinent
```

Tests gameplay :

```text
[ ] Menu principal
[ ] Sélection IA
[ ] Déplacement gauche/droite
[ ] Saut
[ ] Double saut / salto
[ ] Accroupissement
[ ] Déplacement accroupi
[ ] Coup de poing haut/milieu/bas
[ ] Coup de pied haut/milieu/bas
[ ] Attaques basses accroupies
[ ] Blocage haut/milieu/bas
[ ] Shuriken
[ ] Boule d’énergie rose
[ ] Collision projectile contre personnage debout
[ ] Esquive projectile en accroupissement
[ ] Esquive projectile en double saut
[ ] Sons de coup
[ ] Sons de saut
[ ] Sons de salto
[ ] Sons de landing
[ ] Sons de projectile
[ ] Fin de round
[ ] Restart
```

---

## 21. Problèmes probables et corrections

### Écran cyan ou chargement long

Cause probable :

```text
Premier chargement du runtime WebAssembly/Python.
```

Action :

```text
Attendre, ouvrir la console navigateur, vérifier les erreurs réseau.
```

Pygbag signale que le premier chargement peut prendre du temps, puis être accéléré par le cache local.

### ModuleNotFoundError

Cause probable :

```text
Dépendance Python non disponible côté WebAssembly.
```

Action :

```text
Supprimer la dépendance, la remplacer, ou l’isoler avec sys.platform != "emscripten".
```

Pygbag indique que certains imports conditionnels doivent être faits avec `importlib` pour éviter que Pygbag détecte un import incompatible.

### Son qui ne joue pas

Causes probables :

```text
- fichier non OGG ;
- audio lancé avant interaction utilisateur ;
- chemin incorrect ;
- volume trop bas ;
- asset non embarqué.
```

Actions :

```text
- vérifier que le fichier est dans assets/ ;
- convertir en OGG ;
- déclencher le premier son après clic ou touche ;
- ouvrir la console navigateur.
```

### Images manquantes

Causes probables :

```text
- chemin Windows avec backslash ;
- casse différente entre Windows et Linux ;
- fichier hors dossier projet ;
- manifest JSON pointant vers un ancien nom.
```

Actions :

```text
- vérifier la casse exacte ;
- utiliser pathlib ;
- standardiser les chemins en / ;
- vérifier que tout est dans assets/.
```

### Jeu bloqué / page figée

Cause probable :

```text
Boucle bloquante sans await asyncio.sleep(0).
```

Action :

```text
S’assurer que toutes les boucles longues rendent la main au navigateur.
```

---

## 22. Commandes récapitulatives

### Local desktop

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_game.py
```

Sous Windows PowerShell :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_game.py
```

### Local web

```bash
python -m pip install pygbag
python -m pygbag .
```

Puis ouvrir :

```text
http://localhost:8000
```

### Build web statique

```bash
python -m pygbag --build .
```

### Déploiement

```bash
git add .
git commit -m "Add Pygbag web deployment"
git push origin main
```

Puis :

```text
GitHub → Actions → Deploy Pygbag game to GitHub Pages
```

URL attendue :

```text
https://<username>.github.io/<repo-name>/
```

---

## 23. Plan de migration recommandé

### Étape 1 — Préparer le code

```text
1. Créer main.py.
2. Extraire Game.tick().
3. Garder run_game.py pour le desktop.
4. Vérifier que le jeu fonctionne toujours localement.
```

### Étape 2 — Nettoyer les assets

```text
1. Mettre tous les assets dans assets/.
2. Convertir les sons en OGG.
3. Compresser les PNG.
4. Vérifier tous les chemins.
```

### Étape 3 — Tester Pygbag localement

```text
1. Installer pygbag.
2. Lancer python -m pygbag .
3. Corriger les erreurs console.
4. Tester tout le gameplay.
```

### Étape 4 — Déployer GitHub Pages

```text
1. Ajouter le workflow GitHub Actions.
2. Configurer Pages en mode GitHub Actions.
3. Pousser sur main.
4. Vérifier l’URL publique.
```

### Étape 5 — Stabiliser

```text
1. Réduire le poids du build.
2. Optimiser le préchargement.
3. Ajouter un écran de chargement.
4. Ajouter une page d’instructions clavier.
5. Documenter les limitations navigateur.
```

---

## 24. Décision finale

Pour ce jeu, la bonne stratégie est :

```text
Conserver Pygame-ce pour le développement local.
Ajouter un point d’entrée main.py compatible Pygbag.
Utiliser Pygbag pour générer le build WebAssembly.
Déployer build/web via GitHub Actions vers GitHub Pages.
```

Ce choix permet de garder la base Python/Pygame existante tout en obtenant une version jouable en ligne.
