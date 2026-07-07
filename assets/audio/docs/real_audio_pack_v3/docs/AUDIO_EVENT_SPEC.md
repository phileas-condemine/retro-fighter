# Spécification des événements audio

## Événements communs

| Event | Usage | Source recommandée |
|---|---|---|
| `punch_hit` | impact quand un coup de poing touche | Kenney Impact Sounds `impactPunch_medium/heavy` |
| `kick_hit` | impact plus lourd quand un coup de pied touche | Kenney Impact Sounds `impactPunch_heavy` + `impactSoft_heavy` |
| `block_impact` | impact bloqué | Kenney `impactMetal_medium`, `impactWood_heavy` |
| `jump_whoosh` | décollage / saut simple | Kenney Retro `jump`, RPG `cloth` |
| `double_jump_whoosh` | salto / double saut | Kenney Digital `phaseJump`, RPG `cloth` |
| `landing` | réception au sol | Kenney footsteps + fall |
| `attack_whoosh` | mouvement rapide de bras/jambe | Kenney RPG `knifeSlice`, `cloth` |
| `shuriken_draw` | préparation projectile shinobi | Kenney RPG `drawKnife` |
| `shuriken_throw` | lancer shuriken | Kenney RPG `knifeSlice` |
| `shuriken_hit` | shuriken touche/bloqué | Kenney metal light |
| `rose_energy_charge` | charge énergie rose | Kenney Digital `powerUp`, `phaserUp` |
| `rose_energy_throw` | envoi boule rose | Kenney Digital `laser` |
| `rose_energy_hit` | boule rose touche | Kenney Digital `zap` |

## Événements voix par personnage

Pour chaque personnage :

- `punch` : effort court de poing.
- `kick` : effort plus marqué.
- `jump` : souffle/grunt de saut.
- `double_jump` : effort plus aérien/salto.
- `landing` : petite expiration ou impact vocal discret.
- `block` : petit effort serré.
- `hurt` : douleur courte.
- `projectile_throw` : cri d’attaque ou mot de sort.

## Déclenchement recommandé

- Au démarrage d’une attaque : voix + `attack_whoosh` si le mouvement est visible.
- Au contact : `punch_hit` ou `kick_hit`.
- Si bloqué : `block_impact` + éventuelle voix `block` du défenseur.
- Saut simple : voix `jump` + `jump_whoosh`.
- Double saut/salto : voix `double_jump` + `double_jump_whoosh`.
- Atterrissage : `landing` commun + voix `landing` si chute forte.
- Projectile shinobi : voix `projectile_throw` + `shuriken_throw`.
- Projectile rose : voix `projectile_throw` + `rose_energy_charge` puis `rose_energy_throw`.
