# Prochaines étapes recommandées

## Priorité 1 — Fiabiliser et équilibrer le gameplay

- Ajuster les dégâts et portées après quelques parties.
- Vérifier que les kicks ne dominent pas trop les poings.
- Rendre les coups bas utiles sans les rendre trop forts.
- Ajouter un léger recul côté attaquant quand un coup est bloqué.
- Ajouter un délai de retournement si les combattants se croisent.

## Priorité 2 — Améliorer le feedback

- Ajouter un flash visuel sur hit.
- Ajouter un flash différent sur block.
- Ajouter un freeze-frame très court sur gros hit.
- Ajouter un effet de poussière au sol pendant les déplacements.
- Ajouter un effet de saut/atterrissage.
- Le pack audio fournit aussi des sons `common/` (whoosh, impacts) et `voice_only/` par personnage, non utilisés pour l'instant : ils permettraient de mixer séparément voix/whoosh/impact plutôt que les fichiers `ready_to_use` déjà composés.

## Priorité 3 — Sprites : finitions

Les personnages utilisent désormais les packs `rose_kunoichi` (joueur) et `shinobi` (CPU) sous `assets/fighters/` (voir `retro_fighter/sprites.py`). Reste à faire :

- Synchroniser précisément les frames graphiques avec les frames actives de hitbox (actuellement l'animation joue sur son propre timing, indépendant des frames startup/active/recovery de `attacks.py`).
- Ajouter des hitboxes/hurtboxes dessinées par frame plutôt que les rectangles abstraits actuels.
- Ajouter un écran de sélection de personnage (les deux packs sont prêts, l'assignation joueur/CPU est actuellement fixe).

## Priorité 4 — Étendre les mécaniques de combat

- Ajouter les inputs directionnels avancés :
  - avant + poing ;
  - bas + avant + poing ;
  - quart de cercle ;
  - charge arrière puis avant.
- Ajouter les combos simples.
- Ajouter les lancers.
- Ajouter les cross-ups ou les désactiver explicitement (le double saut permet déjà de croiser l'adversaire).
- Régler plus finement l'attaque à distance : cooldown/jauge dédiée pour limiter le spam, punition si esquivée (voir `assets/extension_pack_docs/docs/TUNING_NOTES.md`).
- Élargir la largeur de hurtbox en accroupi et pendant les attaques basses accroupies (`width_multiplier` des packs, non implémenté — actuellement seule la hauteur change).
- Envisager de différencier `crouch_punch_low`/`crouch_kick_low` des attaques basses debout comme de vrais coups distincts (dégâts/vitesse/portée propres) plutôt qu'un simple changement de pose — chiffres suggérés dans `assets/extension_pack_docs/crouch_low_attacks/docs/HITBOX_TUNING.md`.

## Priorité 5 — Structurer le jeu complet

- Écran titre final.
- Sélection de personnage.
- Plusieurs rounds.
- Score.
- Écran de victoire.
- Options de clavier.
- Support manette.
- Mode deux joueurs local.

## Priorité 6 — IA avancée

- Ajouter une IA à états : neutral, approach, defend, punish, pressure, retreat.
- Ajouter une mémoire courte des habitudes du joueur.
- Faire varier la probabilité de blocage selon les patterns du joueur.
- Empêcher l'IA difficile d'être trop parfaite : temps de réaction minimal, erreurs humaines.
- Ajouter un mode entraînement avec affichage des coups réussis.

## Priorité 7 — Outillage développeur

- Ajouter tests unitaires sur les hitboxes.
- Ajouter tests unitaires sur les frames startup/active/recovery.
- Ajouter un mode debug plus complet :
  - frame courante de l'attaque ;
  - état exact ;
  - distance ;
  - avantage après block/hit.
- Ajouter un fichier JSON/YAML de configuration pour les attaques.
- Ajouter un éditeur simple d'attaque pour équilibrer sans modifier le code.

## Roadmap courte proposée

1. Jouer 10 minutes au prototype et noter les coups trop forts/faibles.
2. Corriger l'équilibrage dans `attacks.py` et `projectiles.py`.
3. Ajouter feedback hit/block.
4. Ajouter mode deux joueurs local.
