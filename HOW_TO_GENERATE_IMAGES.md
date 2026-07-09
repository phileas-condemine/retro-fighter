# Générer des frames de sprite avec ChatGPT + Playwright

Ce document décrit un pipeline **validé de bout en bout** (généré, découpé,
intégré, testé en jeu) pour produire de nouvelles frames d'animation HD à
partir de ChatGPT, en pilotant le navigateur via le MCP Playwright plutôt
qu'en demandant à l'utilisateur de copier/coller des images à la main.

Utilisé la première fois pour regénérer l'`idle` de `rose_kunoichi` (3 →
10 frames) — en deux passes : la première planche était visuellement
propre mais montrait la mauvaise pose (voir le piège de l'étape 1), la
seconde correction a donné le résultat final. Réutilisé ensuite pour
corriger `kick_mid`, `punch_high`/`punch_mid` (mauvaise hauteur de cible)
et pour regénérer `walk` (3 → 20 frames, voir "Cas des animations à plus
de 10 frames" plus bas pour la technique en deux planches — depuis
remplacée pour `walk`, voir plus bas). Le `walk` 20 frames a ensuite dû
être entièrement refait en 60 frames/6 planches car il "jouait des
claquettes" en jeu (voir "Planches chaînées séquentiellement" plus bas) —
la bonne technique dépend de si l'animation a besoin de plus de *densité*
sur un mouvement déjà capturé, ou d'un vrai mouvement continu supplémentaire.
Le pipeline
Blender v2 (`retro_fighter_v2_blender_sprite_pipeline.md`)
reste l'objectif long terme pour des animations *cohérentes* (rig +
squelette), mais tant qu'il n'est pas mûr, cette méthode ChatGPT-only donne
des résultats propres pour une **pose statique/idle** ou une **boucle de
déplacement** (variations subtiles, pas de vraie physique) en quelques
minutes.

Réutilisé ensuite pour `rose_kunoichi` HD afin de créer un `dash` dédié
(inexistant jusque-là — `dash` retombait sur le cycle `walk`, voir
`assets/fighters/CONTRACT.md`), regénérer `double_jump_salto` (3 frames qui
ne lisaient pas comme une vraie rotation → 6 frames, une rotation continue),
et corriger `block_low`/`crouch_block` (pose fausse + clé jamais lue par le
moteur, voir pièges dédiés plus bas).

## Vue d'ensemble

```text
1. Ouvrir ChatGPT dans un navigateur automatisé (déjà connecté)
2. Fournir les frames existantes du personnage comme référence de style
3. Demander UNE planche (grille) contenant toutes les poses, fond vert
4. Vérifier visuellement la planche avant de continuer
5. Demander à ChatGPT (outil code/Python) de découper, chroma-key, zipper
6. Télécharger le zip via Playwright
7. Recomposer chaque frame sur le canevas standard du pack (256×256, ancrage figé)
8. Mettre à jour manifest.json
9. Valider avec tools/sprites/validate_manifest.py
10. Rejouer l'animation en tête (headless) pour vérifier avant de committer
```

## Prérequis : Playwright MCP branché sur le vrai profil Edge

Par défaut, le serveur MCP `playwright` de ce poste (`~/.claude.json` →
`mcpServers.playwright`) lance Edge avec un profil **isolé** dédié à
l'automatisation (`--user-data-dir C:\Users\phile\.playwright-mcp-profile`).
Ce profil n'est **pas connecté** à ChatGPT.

Deux options, à choisir selon le contexte :

- **Rester sur le profil isolé** (le plus simple) : se connecter une fois à
  la main dans la fenêtre automatisée qui s'ouvre — la session persiste
  ensuite dans ce profil pour toutes les automatisations futures. Aucun
  risque, aucun redémarrage nécessaire.
- **Basculer sur le vrai profil Edge** (celui où l'utilisateur est déjà
  connecté au quotidien) : éditer `~/.claude.json`, remplacer
  `--user-data-dir` par
  `C:\Users\phile\AppData\Local\Microsoft\Edge\User Data`. **Deux
  contraintes à annoncer avant de le faire** :
  1. Chromium verrouille le dossier de profil : **toutes les fenêtres Edge
     de l'utilisateur doivent être fermées** avant que Playwright puisse
     l'ouvrir (sinon erreur de profil déjà utilisé, ou double-lancement
     silencieux qui ne fait rien).
  2. Le changement ne prend effet qu'après **redémarrage de la session/
     extension Claude Code** — modifier le fichier ne suffit pas tant que
     le process MCP tourne encore avec les anciens arguments.
  C'est un changement de config **global** (partagé entre tous les projets
  utilisant ce même serveur MCP) : toujours demander confirmation avant de
  le faire, ne pas le faire "en silence" en pensant que ça n'affecte que le
  projet courant.

Vérifier que la connexion a fonctionné avant d'aller plus loin (snapshot de
la page d'accueil ChatGPT : doit afficher le nom du compte, pas de bouton
"Se connecter").

### Piège : le profil isolé peut rester verrouillé par une instance Edge orpheline

Si `browser_navigate` échoue avec `Browser is already in use for
...\.playwright-mcp-profile`, ce n'est pas forcément une vraie session en
cours — une fenêtre Edge lancée par une session Claude Code précédente peut
être restée ouverte (ou son process orphelin après une fin de session
brutale) et garder le verrou du profil. Vérifier lequel avant de tuer quoi
que ce soit (ne jamais tuer des `msedge.exe` au hasard, l'utilisateur peut
avoir son navigateur perso ouvert en parallèle) :

```powershell
Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" |
  Where-Object { $_.CommandLine -like '*playwright-mcp-profile*' } |
  Select-Object ProcessId, CommandLine
```

Tuer uniquement le process principal trouvé par ce filtre (`Stop-Process -Id
<pid> -Force`) — c'est nécessairement une instance du profil d'automatisation
dédié, jamais le profil Edge personnel de l'utilisateur (chemins différents).
Ses processus enfants (gpu/renderer/crashpad) se terminent avec lui. Aucune
perte pour l'utilisateur : ce profil ne sert qu'à l'automatisation, la
session ChatGPT reste sur disque et se recharge au prochain lancement.

## Étape 1 — Fournir le contexte à ChatGPT

Ouvrir `https://chatgpt.com/`, démarrer un nouveau chat, joindre en pièces
jointes les frames **déjà en place** pour l'animation à enrichir/remplacer
(ex. `frames/idle_000.png` à `idle_002.png`) : elles servent de référence de
style (couleurs, costume, cheveux, arme) pour que la nouvelle génération
reste cohérente avec le personnage existant.

### Piège : le nom d'une clé d'animation ne décrit pas sa pose

Générer `idle` a produit la première fois une pose "au repos", bras
relâchés le long du corps — visuellement fausse pour un jeu de combat :
l'`idle` d'un fighting game est la **garde de combat** (genoux fléchis,
poids bas, poings/mains prêts à hauteur de garde, léger balancement en
jaugeant l'adversaire), jamais une pose détendue. Le nom de la clé
(`idle`, `walk`, ...) ne suffit pas à transmettre cette intention au
modèle — il faut la décrire en langage corporel concret (`"knees bent,
weight low, fists up near guard height"`, pas juste `"idle stance"`), et
surtout **joindre en référence d'autres animations déjà correctes du même
personnage** qui montrent la posture attendue (ici `block_mid_000.png`,
`punch_mid_000.png`, `walk_000.png` : toutes montrent la vraie posture de
combat du personnage) plutôt que de se fier aux 2-3 frames de l'animation
qu'on est justement en train de corriger. Un rappel visuel vaut mieux
qu'une description abstraite. Si un doute existe sur ce que la pose est
censée représenter dans le jeu, le demander à l'utilisateur **avant** de
lancer la génération plutôt qu'après coup.

**Piège chemins de fichiers (`browser_file_upload`)** : le outil vérifie que
le chemin est dans les racines autorisées par une comparaison de **préfixe
de chaîne, sensible à la casse**. Un chemin par ailleurs correct peut être
rejeté avec `File access denied: ... is outside allowed roots` simplement
parce que la lettre de lecteur est en majuscule (`C:\Users\...`) alors que
la racine autorisée listée dans le message d'erreur est en minuscule
(`c:\Users\...`, ou l'inverse). **Solution : copier exactement la casse de
la racine indiquée dans le message d'erreur**, ne pas supposer que
`C:\` et `c:\` sont interchangeables ici.

## Étape 2 — Demander UNE planche, pas N images séparées

Demander des images séparées une par une donne des personnages qui dérivent
légèrement à chaque appel (morphologie, teinte, cadrage). Demander **une
seule planche/grille** (ex. 5 colonnes × 2 lignes pour 10 poses) force le
modèle à garder la cohérence sur toute la planche en un seul rendu.

Points à inclure explicitement dans le prompt (chacun a son importance) :

- **Fond vert uni** (`#00FF00` ou équivalent), sans dégradé ni ombre portée
  sur le fond → nécessaire pour un chroma-key propre à l'étape suivante.
- **Même costume/couleurs/style que les références jointes**, dans chaque
  panneau.
- **Même cadrage/échelle/hauteur du personnage** dans chaque panneau (sinon
  le retraitement de l'étape 7 devra corriger des échelles différentes par
  frame, ce qui est faisable mais display un travail inutile).
- **Aucun texte, aucun numéro, aucun label** sur l'image.
- Pour une boucle (`idle`, `walk`...), préciser que la **dernière pose doit
  boucler proprement sur la première** (ex. "panel 10 flows back into panel
  1 for a seamless loop").
- Les séparateurs fins entre panneaux sont acceptés (faciles à rogner
  ensuite) — ne pas exiger un montage sans aucune séparation, ça complique
  le découpage automatique sans bénéfice.

## Cas des animations à plus de 10 frames (ex. `walk` en 20 frames)

Une seule planche reste lisible pour le modèle jusqu'à ~10 panneaux (5×2) ;
au-delà, chaque panneau devient trop petit et la cohérence se dégrade. Pour
une boucle qui a besoin de plus de frames (ex. une marche fluide en 20
frames), ne pas essayer de tout faire tenir dans une planche géante — faire
**deux planches en deux passes, dans le même chat** :

1. **Round 1 (grossier)** : demander la planche habituelle de 10 panneaux
   couvrant l'intégralité du cycle (les 10 poses-clés, la dernière bouclant
   sur la première comme d'habitude). La valider visuellement comme
   n'importe quelle planche (voir étape 3).
2. **Round 2 (intercalaire)** : dans le message suivant, demander une
   **deuxième** planche de 10 panneaux contenant la pose **à mi-chemin**
   entre chaque paire consécutive de la première planche — panneau 1 =
   milieu(round1-panneau1, round1-panneau2), ..., et **le dernier panneau
   du round 2 doit être le milieu entre le dernier et le premier panneau du
   round 1** (c'est celui qui referme la boucle). Être explicite sur cette
   correspondance panneau-par-panneau dans le prompt, ChatGPT n'a pas
   besoin de deviner.
3. **Assembler en local** en intercalant : round1-P1, round2-P1, round1-P2,
   round2-P2, ..., round1-P10, round2-P10 → 20 frames dans l'ordre final,
   round2-P10 bouclant bien sur round1-P1.

Pour une découpe/despill efficace, demander à ChatGPT de traiter **les deux
planches en une seule fois** une fois les deux validées (même message,
mêmes étapes de chroma-key/despill que d'habitude), en nommant les deux
jeux différemment (ex. `walk_a_00..09` et `walk_b_00..09`) plutôt que de
lui faire deviner l'ordre final intercalé — l'intercalage se fait de façon
fiable en local, pas dans le prompt.

### Piège : les deux planches n'ont pas forcément le même zoom

Même en demandant explicitement le "même cadrage" dans les deux prompts,
les deux planches sont deux générations d'image indépendantes et peuvent
avoir un niveau de zoom légèrement différent (silhouette globalement ~5%
plus petite ou plus grande d'une planche à l'autre). Si l'échelle fixe de
l'étape 7 est calculée une fois pour tout le lot, ce décalage produit un
clignotement de taille toutes les deux frames une fois les deux jeux
intercalés. **Calculer l'échelle fixe séparément pour chaque planche**
(sur sa propre frame de référence neutre, ex. `walk_a_00` et `walk_b_00`),
pas une seule fois pour l'ensemble — chaque jeu est alors normalisé
indépendamment vers la même hauteur cible, ce qui absorbe le décalage de
zoom entre les deux générations.

### Piège : le modèle revient à une démarche normale si on ne le précise pas

Demander une "marche" sans plus de détails donne une démarche humaine
normale (jambes qui alternent laquelle est devant). Pour un jeu de combat,
la marche est en général un **pas chassé/shuffle de boxeur** : le pied
avant reste toujours le pied avant, le pied arrière reste toujours le pied
arrière (ils ne se croisent jamais) — le pied avant glisse d'abord vers
l'avant, puis le pied arrière le rattrape. Décrire ce mécanisme
explicitement dans le prompt (quel pied reste devant, dans quel ordre
chaque pied bouge) plutôt que de simplement dire "marche" ou "walk cycle".

### La technique "grossier + intercalaire" ne suffit pas pour un vrai mouvement de pied

Le `walk` 20 frames produit avec la technique round1/round2 ci-dessus a
donné, une fois en jeu, l'impression que le personnage "joue des
claquettes" : l'écart entre les jambes ne changeait presque pas d'une
frame à l'autre, mais le pied passait brutalement de "à plat au sol" à
"fléchi sur le talon". Cause : 10 poses-clés + leurs milieux ne capturent
pas les **sous-phases mécaniques réelles** du pied (levée du talon,
décollage des orteils, phase aérienne jambe pliée, attaque du talon,
déroulé talon→orteils, transfert de poids) — seulement une position
grossière du corps entier. Densifier par interpolation de *position*
n'ajoute pas l'articulation du pied qui n'existait pas dans les 10 poses
de départ.

**Remplacé par la technique de planches chaînées séquentiellement**
ci-dessous (utilisée pour refaire ce même `walk` en 60 frames/6 planches),
qui décrit et génère chaque sous-phase mécanique explicitement plutôt que
de les interpoler après coup.

## Planches chaînées séquentiellement (animations à mouvement réel, > 10 frames)

Pour une animation qui a besoin de plusieurs dizaines de frames de **vrai
mouvement continu** (pas juste plus de densité sur un mouvement déjà
capturé), générer les planches **dans l'ordre chronologique strict**, une
par une dans le même chat, chaque planche continuant exactement où la
précédente s'est arrêtée :

1. Découper le mouvement complet en sous-phases mécaniques réelles avant
   d'écrire le moindre prompt (ex. pour un pas chassé : levée du talon
   avant → décollage des orteils → balancement aérien genou plié → attaque
   du talon → déroulé/transfert de poids → répéter pour le pied arrière).
   Une planche de 10 panneaux par sous-phase donne un mouvement qui reste
   lisible et cohérent panneau par panneau.
2. Pour la planche N (N > 1), joindre en pièce jointe le **dernier panneau
   réellement extrait/traité de la planche N-1** (l'image finale
   chroma-keyée du zip téléchargé, pas une simple capture d'écran rognée)
   comme référence explicite de continuité : "ce panneau est le point de
   départ exact de la planche suivante".
3. Décrire dans le prompt la sous-phase de cette planche précisément (quel
   pied bouge, dans quel sens, la posture du reste du corps) et rappeler
   que le pied avant/arrière ne changent jamais de rôle.
4. Valider chaque planche visuellement (étape 3 habituelle) avant de
   passer à la suivante — une planche fausse contamine toutes les
   suivantes si on ne la corrige pas tout de suite.

### Piège : le modèle peut ignorer une sous-phase et répéter une pose statique

Une planche censée montrer "le pied avant qui se balance en l'air vers
l'avant" a d'abord reproduit une posture large statique quasi identique
sur les 10 panneaux (les deux pieds au sol, rien en l'air) — le modèle
n'a pas compris qu'il fallait une jambe réellement en suspension. Symptôme
détectable en zoomant spécifiquement sur la zone des pieds sur toute la
largeur de la planche (pas juste un panneau) : si les pieds sont à la même
position dans presque tous les panneaux, la planche est à refaire.

**Solution qui a fonctionné** : dire explicitement à ChatGPT que la
planche qu'il vient de produire est fausse et doit être refaite, et
joindre une **référence visuelle concrète de la silhouette attendue**
plutôt qu'une description de plus. Ici, l'ancienne frame `walk_001.png`
(remplacée en tout début de cette même session, donc récupérable via
`git show HEAD:chemin/vers/walk_001.png > fichier_temp.png`) montrait déjà
une jambe avant pliée et levée — jointe en pièce jointe avec la précision
"copie uniquement la silhouette de cette jambe, ignore sa jambe arrière et
ses bras", elle a débloqué la génération dès le premier essai suivant.
Réutiliser proactivement la même référence pour la planche symétrique
(le pied arrière qui rattrape) a évité de refaire l'erreur une seconde
fois.

**Une ancienne frame supprimée/remplacée reste une ressource valide** tant
qu'elle montre clairement UN détail utile (une silhouette, un angle) — même
si le reste de cette vieille frame est le bug qu'on est justement en train
de corriger. Le préciser explicitement dans le prompt ("ignore X, Y de
cette référence") évite que le modèle ne réintroduise le défaut d'origine
en même temps que le détail utile.

### Piège critique : valider CHAQUE planche de cette façon, pas seulement celle qui semble louche

Sur les 6 planches d'un `walk` 60 frames, la moitié (les 3 planches
correspondant aux sous-phases *subtiles* — lever de talon, décollage des
orteils, atterrissage/stabilisation) se sont révélées être des quasi-
doublons de la même pose statique, malgré un rendu qui semblait correct en
aperçu rapide (screenshot non zoomé) et malgré tout le travail de
recalcul d'échelle fait en aval. Le bug n'a été repéré qu'après coup, sur
un signalement de l'utilisateur ("elle joue des claquettes"), en
construisant une planche de contact zoomée de **toutes** les images
brutes des 6 planches (pas juste celle qu'on soupçonnait) et en comparant
un crop serré sur les pieds pour chacune.

**Leçon : ne jamais faire confiance à une planche sur la seule base d'un
aperçu rapide, même si elle "a l'air" de contenir du mouvement.** Avant
d'enchaîner sur le découpage/recomposage, construire systématiquement,
pour CHAQUE planche générée (pas juste celles qui semblent suspectes), une
bande de crops serrés sur la zone qui est censée bouger (les pieds pour
une marche) sur toute la largeur de la planche — si les 10 panneaux se
ressemblent presque tous, la planche est un quasi-doublon même si le
rendu global "a l'air" différent d'un panneau à l'autre (couleurs de fond,
compression JPEG, artefacts mineurs peuvent donner une fausse impression
de variété à un coup d'œil rapide). Les sous-phases *subtiles* (un
mouvement de cheville, un roulis pied/talon) sont statistiquement les plus
à risque de ce piège — une planche montrant un grand mouvement de jambe
en l'air a beaucoup moins tendance à collapser vers un doublon.

**Solution qui a fonctionné à chaque fois** : signaler explicitement à
ChatGPT que "tous les panneaux sont quasi identiques" et lui redemander en
insistant sur l'exagération de la différence entre panneaux consécutifs
("il vaut mieux que ce soit légèrement trop rapide/dramatique que de
répéter la même pose"). Pour les planches où même cette insistance ne
suffit pas (parce que la pose de départ et la pose d'arrivée se
ressemblent déjà beaucoup, ce qui ne donne au modèle aucune raison
évidente de varier) : **exagérer le MILIEU du mouvement** plutôt que les
extrémités — demander explicitement une pose intermédiaire nettement
différente des deux bouts (ex. un creux/accroupissement marqué au milieu
d'un atterrissage) donne au modèle un vrai point d'ancrage visuel à
distinguer, même si ce point milieu est physiquement un peu exagéré par
rapport à un geste réel.

### Piège : la dérive d'échelle s'accumule planche par planche, même avec une image de continuité

Le chaînage par référence (point 2 ci-dessus) garantit la continuité de
*pose*, pas l'échelle : chaque planche reste une génération d'image
indépendante, et un écart de zoom de quelques % par rapport à la planche
précédente est courant même quand le personnage est visiblement "à la
bonne taille" sur un aperçu rapide. Sur 5-6 planches chaînées, ces petits
écarts s'accumulent et deviennent visibles en fin de séquence si on ne les
corrige pas.

**Solution : chaîner les ratios de hauteur de bbox au lieu de mesurer une
échelle fixe par planche indépendamment.** Pour chaque frontière entre la
planche N-1 et la planche N, mesurer le ratio entre la hauteur de bbox du
dernier panneau de N-1 et celle du premier panneau de N, puis multiplier
ce ratio à l'échelle cumulée précédente :

```powershell
# k1 = 1.0 (planche de référence)
# k(N) = k(N-1) * hauteur(dernier panneau de N-1) / hauteur(premier panneau de N)
# échelle finale de la planche N = échelle de base * k(N)
```

Vérifier ensuite **visuellement** (pas seulement numériquement) au moins
une frontière à fort écart mesuré, en juxtaposant les deux images natives
côte à côte (pas de screenshot downscalé) avant de faire confiance à la
correction pour tout le lot.

### Piège : une planche peut avoir sa PROPRE dérive d'échelle interne

Une planche dont le dernier panneau est explicitement ancré sur une pose
de référence absolue externe (ex. "le dernier panneau doit correspondre
exactement à `walk_000.png` pour boucler proprement") peut dériver en
échelle **à l'intérieur d'elle-même** entre son premier et son dernier
panneau, même si le chaînage planche-à-planche (piège précédent) a été
appliqué correctement au panneau 1. Symptôme : mesurer la hauteur de bbox
brute de chaque panneau de la planche révèle une vraie cassure (pas un
dégradé progressif) — ex. panneaux 1-5 tous ~400px, panneaux 6-10 tous
~346px — ce qui indique que le modèle a changé de zoom en cours de
génération plutôt qu'un mouvement de pose naturel.

**Ne pas corriger ça en interpolant l'échelle linéairement d'un panneau à
l'autre** : comme la hauteur brute source elle-même a une cassure nette
(pas un dégradé), multiplier par une échelle croissante produit un creux
visible (la hauteur composée finale monte, redescend, puis remonte).

**Solution qui fonctionne : interpoler directement la hauteur de sortie
cible** (pas l'échelle) de façon linéaire entre la valeur de continuité
avec la planche précédente (premier panneau) et la valeur de clôture de
boucle voulue (dernier panneau), puis calculer l'échelle de chaque panneau
individuellement à partir de sa propre bbox pour atteindre cette hauteur
cible :

```powershell
# targetH(i) = hauteurDépart + (hauteurArrivée - hauteurDépart) * i / (n-1)
# scale(i) = targetH(i) / bbox_hauteur_brute(panneau i)
```

Cette approche garantit une croissance/décroissance visuelle strictement
monotone quel que soit le comportement erratique de la source, au prix de
ne plus respecter une "échelle fixe unique par planche" pour cette planche
en particulier — acceptable puisque le but (mouvement fluide à l'écran)
prime sur la pureté de la méthode.

### Correctif : la cassure interne se produit presque toujours exactement à la frontière de ligne (panneau 5/6)

En reprenant ce même `walk` une seconde fois (60 frames, 6 planches), la
"dérive interne" ci-dessus s'est reproduite sur DEUX autres planches qui
n'avaient pourtant aucun ancrage sur une référence absolue externe — donc
la cause n'est pas spécifique à ce cas de figure. Mesurer la hauteur de
bbox brute des 10 panneaux d'une planche 5×2 révèle typiquement deux
plateaux nets **exactement alignés sur la frontière ligne 1/ligne 2**
(ex. panneaux 0-4 tous ~409px, panneaux 5-9 tous ~364px) plutôt qu'un
dégradé continu : ChatGPT rend parfois les deux lignes d'une planche 5×2 à
deux échelles de caméra légèrement différentes, indépendamment de tout
ancrage externe.

**Diagnostic rapide : la vraie question à se poser est "la cassure
coïncide-t-elle exactement avec la frontière de ligne (index 4→5), et
les deux moitiés sont-elles chacune plates (même hauteur brute répétée),
ou bien est-ce un dégradé progressif cohérent avec un mouvement réel du
personnage (ex. un accroupissement volontaire) ?**

- Si c'est un **plateau net aligné sur la frontière de ligne** → artefact
  de rendu, pas du mouvement réel. Le corriger avec une **échelle fixe en
  deux morceaux** (une pour les panneaux 0-4, une pour les panneaux 5-9),
  chaque moitié chaînée en continuité (la première depuis la planche
  précédente comme d'habitude, la seconde depuis le ratio de hauteur brute
  entre le panneau 4 et le panneau 5 de la MÊME planche) :

  ```python
  scale_a = planche_precedente_scale * h(planche_prec, 9) / h(planche, 0)
  scale_b = scale_a * h(planche, 4) / h(planche, 5)
  # scale_a pour les panneaux 0-4, scale_b pour les panneaux 5-9
  ```

  Ça élimine le saut à la frontière tout en respectant la variation de
  pose naturelle à l'intérieur de chaque moitié.
- Si la variation est un **dégradé progressif** (montée puis descente, ou
  creux au milieu qui ne s'aligne pas pile sur la frontière de ligne) →
  c'est probablement du vrai mouvement volontaire (ex. un accroupissement
  demandé explicitement dans le prompt) qu'il ne faut PAS corriger — une
  planche `walk` demandant explicitement un creux/accroupissement au
  milieu a montré exactement ce dégradé cohérent (creux centré sur les
  panneaux 4-5, remontée symétrique de part et d'autre) sans jamais
  nécessiter de correction : dans ce cas une échelle fixe unique pour
  toute la planche suffit, le creux mesuré dans la bbox EST le mouvement
  voulu.

Toujours mesurer et regarder les deux avant de choisir une correction —
appliquer la correction "artefact de rendu" à un vrai mouvement l'annule
purement et simplement (aplati une pose recherchée), et l'inverse laisse
un vrai saut de taille visible en jeu.

## Étape 3 — Vérifier AVANT de continuer

Ne jamais enchaîner directement sur la découpe : un `browser_take_screenshot`
classique downscale l'image et cache les défauts (bordures verdâtres,
proportions qui dérivent d'un panneau à l'autre, pose qui casse la
silhouette). Faire un zoom réel avant de valider :

```powershell
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile($screenshotPath)
$rect = New-Object System.Drawing.Rectangle(x, y, w, h)   # zone de la planche à l'écran
$bmp = New-Object System.Drawing.Bitmap($rect.Width, $rect.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.DrawImage($img, (New-Object System.Drawing.Rectangle(0,0,$rect.Width,$rect.Height)), $rect, [System.Drawing.GraphicsUnit]::Pixel)
$bmp2 = New-Object System.Drawing.Bitmap($bmp, [int]($rect.Width*1.8), [int]($rect.Height*1.8))  # upscale pour l'inspection
$bmp2.Save("$env:TEMP\claude\board_crop.png", [System.Drawing.Imaging.ImageFormat]::Png)
```

puis relire ce fichier recadré avec l'outil `Read` (qui affiche les images).
Si la planche ne convient pas (poses trop différentes, costume qui dérive,
fond non uniforme), le redemander **dans le même chat** (garde le contexte
et les références) avant de passer à l'étape suivante — c'est le moment
le moins cher pour itérer, bien avant le découpage/l'intégration.

## Étape 4 — Découpe, chroma-key, despill, zip

Une fois la planche validée, demander dans le **même message suivant** (pas
un nouveau chat, pour que ChatGPT réutilise l'image qu'il vient de générer)
d'utiliser son outil Python/code interpreter pour :

1. Charger la planche générée.
2. La découper en panneaux individuels (rogner strictement les bords/
   séparateurs de chaque panneau).
3. Chroma-key du fond vert → transparence RGBA, avec **despill** (nettoyer
   la frange verdâtre residuelle sur les bords de la silhouette — sans ça,
   les frames ont un liseré vert visible une fois posées sur un autre fond).
4. Exporter les fichiers avec un nommage explicite (`idle_00.png` ...
   `idle_09.png`, ordre de lecture gauche→droite puis haut→bas).
5. Les empaqueter dans un zip et donner un lien de téléchargement.

### Piège : le lien de téléchargement n'est parfois qu'un texte mort

Symptôme observé : ChatGPT répond "Download the ... frames" mais l'élément
n'est qu'un `<p>` de texte, sans lien/bouton cliquable (vérifiable via un
`browser_snapshot` : s'il apparaît en `generic`/`paragraph` sans rôle
`button`/`link`, ce n'est pas cliquable). Le bouton "arrêter la réponse"
peut aussi rester affiché indéfiniment sans que rien ne se passe — le
message n'est en réalité jamais retombé dans un état "terminé" côté client.

**Solution qui a fonctionné à tous les coups : recharger complètement la
page** (`location.reload()` ou F5, pas juste renaviguer côté client) plutôt
que d'attendre ou de redemander dans le chat. Après rechargement, le même
message affiche correctement un vrai bouton "Download ..." cliquable.
Toujours vérifier via snapshot que l'élément a bien un rôle `button`/`link`
avant d'essayer de cliquer dessus.

## Étape 5 — Télécharger et inspecter

Cliquer sur le bouton de téléchargement déclenche un vrai téléchargement de
fichier : Playwright l'enregistre automatiquement dans
`.playwright-mcp/<nom-du-fichier>.zip` à la racine du projet (dossier
gitignored — voir `.gitignore`). Extraire et inspecter avant d'aller plus
loin :

```bash
unzip -l ".playwright-mcp/mon_zip.zip"                       # vérifier les 10 fichiers attendus
unzip -o ".playwright-mcp/mon_zip.zip" -d ".playwright-mcp/extract"
file ".playwright-mcp/extract/"*.png                          # doit être RGBA (transparence réelle)
```

Puis relire 2-3 frames avec l'outil `Read` pour confirmer visuellement :
fond bien transparent, pas de liseré vert résiduel, pas de reste de la
ligne de séparation entre panneaux collée sur un bord.

## Étape 6 — Comprendre les conventions du pack AVANT d'intégrer

**Ne pas coller les nouvelles images telles quelles dans `frames/`.** Elles
sortent de ChatGPT à une résolution et un cadrage qui n'ont aucune raison de
correspondre au canevas attendu par le moteur. Lire d'abord
`assets/fighters/CONTRACT.md` :

- Canevas fixe : **256×256**, RGBA, même taille pour toutes les frames d'un
  pack.
- **Un seul point d'ancrage `{x, y}` par `fighter_id`**, identique entre
  toutes les variantes (`ld`/`hd`) — aligné sur les pieds au sol du
  personnage. Aujourd'hui `128, 214` pour les deux personnages. Si les
  nouvelles frames ne respectent pas cet ancrage, le personnage "saute"
  visuellement en changeant d'animation ou de variante graphique.

Mesurer ensuite, sur une frame **existante et correcte** du même
`fighter_id` (n'importe quelle animation, pas forcément celle qu'on
remplace), la position réelle de la silhouette dans le canevas 256×256 pour
en déduire la hauteur cible et le point de pied. Sans Pillow/ImageMagick
disponibles sur ce poste (`python`/`python3` pointent vers les stubs
Windows Store, pas un vrai interpréteur — voir note plus bas), on peut le
faire en PowerShell :

```powershell
Add-Type -AssemblyName System.Drawing
function Get-BBox($img, $thresh, $margin) {
  $minX=$img.Width; $maxX=-1; $minY=$img.Height; $maxY=-1
  for ($y=$margin; $y -lt $img.Height-$margin; $y++) {
    for ($x=$margin; $x -lt $img.Width-$margin; $x++) {
      if ($img.GetPixel($x,$y).A -gt $thresh) {
        if ($x -lt $minX) { $minX=$x }; if ($x -gt $maxX) { $maxX=$x }
        if ($y -lt $minY) { $minY=$y }; if ($y -gt $maxY) { $maxY=$y }
      }
    }
  }
  return @{minX=$minX;maxX=$maxX;minY=$minY;maxY=$maxY}
}
$img = New-Object System.Drawing.Bitmap("assets/fighters/hd/<fighter_id>/frames/<une_frame_correcte>.png")
Get-BBox $img 128 4   # seuil 128 (pas 10 : voir piège ci-dessous), marge 4px -> minX/maxX/minY/maxY réels
```

Sur `rose_kunoichi` HD : bas de la silhouette à `y=213` (pieds), hauteur
~197px, centrée horizontalement à `x=128` — cohérent avec l'ancrage
`(128, 214)` du manifest (`maxY + 1 == anchor.y`).

### Piège : un pixel de bordure opaque fausse la bbox des nouvelles frames

Le despill de ChatGPT laisse parfois, sur un ou deux bords d'un panneau
découpé, une **colonne/ligne d'1 pixel entièrement opaque** (couleur
pâle/verdâtre résiduelle, alpha ≈ 255) — un reste du bord du panneau
d'origine mal recadré, invisible à l'œil sur un aperçu normal. Une bbox
calculée avec `alpha > seuil` sur l'image entière capture ce pixel et
étend `minX`/`maxX`/`minY`/`maxY` jusqu'au bord de l'image, ce qui fausse
ensuite l'échelle et/ou le centrage calculés à l'étape 7 (silhouette
mesurée plus large/haute qu'elle ne l'est réellement). **Symptôme qui doit
alerter : une bbox dont `minX` ou `minY` vaut exactement 0**, ou dont
`maxX`/`maxY` vaut exactement `largeur-1`/`hauteur-1` — la silhouette
réelle a presque toujours une marge avant le bord du crop.

Deux vérifications simples avant de faire confiance à une bbox :

1. **Toujours exclure une petite marge (3-5px) des bords** avant de
   scanner (paramètre `$margin` dans `Get-BBox` ci-dessous) — l'artefact
   d'1px disparaît, la vraie silhouette n'est jamais si près du bord.
   **Une marge de 4-5px ne suffit pas toujours** : rencontré sur
   `block_low`/`block_mid` (correction du blocage bas/moyen de
   `rose_kunoichi`) un artefact qui s'étendait jusqu'à exactement 4px du
   bord — `minX`/`minY` tombaient pile sur la limite de la marge par
   défaut au lieu de 0. Si `minX`/`minY` (ou `maxX`/`maxY`) tombe
   exactement sur la valeur de `$margin` utilisée, c'est le même signal
   d'alerte que tomber sur 0 — augmenter la marge (10px a suffi) et
   re-mesurer jusqu'à ce que le résultat se stabilise (immobile en
   augmentant encore la marge).
2. **Visualiser le canal alpha en niveaux de gris** avant de calculer quoi
   que ce soit dessus (silhouette blanche nette sur fond noir attendue) :

```powershell
$out = New-Object System.Drawing.Bitmap($img.Width, $img.Height)
for ($y=0; $y -lt $img.Height; $y++) {
  for ($x=0; $x -lt $img.Width; $x++) {
    $a = $img.GetPixel($x,$y).A
    $out.SetPixel($x,$y, [System.Drawing.Color]::FromArgb(255,$a,$a,$a))
  }
}
$out.Save("$env:TEMP\claude\alpha_check.png", [System.Drawing.Imaging.ImageFormat]::Png)
```

puis relire ce fichier avec `Read` — un fond bien noir et une silhouette
bien blanche confirment un chroma-key propre ; ne pas se contenter des
chiffres bruts de `Get-BBox` sans ce contrôle visuel une fois par lot.

## Étape 7 — Recomposer chaque frame sur le canevas standard

Pour chaque nouvelle image : mesurer sa propre bbox (rognage du fond
transparent), calculer le facteur d'échelle pour ramener sa hauteur à la
hauteur cible mesurée à l'étape 6, puis la coller sur un nouveau canevas
256×256 transparent avec le bas de la bbox aligné sur `anchor.y` et le
centre horizontal sur `anchor.x`.

```powershell
$targetHeight = 197   # mesuré à l'étape précédente
$footY = 214          # anchor.y du manifest ; destY = footY - hauteur mise à l'échelle
$centerX = 128         # anchor.x du manifest

# ... pour chaque image source :
#   bbox = Get-BBox $src
#   scale = $targetHeight / bbox.height
#   newW/newH = bbox.width/height * scale
#   destX = round($centerX - newW/2) ; destY = $footY - newH
#   dessiner (InterpolationMode HighQualityBicubic) la sous-région bbox du
#   source, mise à l'échelle, sur un bitmap 256x256 Format32bppArgb neuf
```

Voir le script complet utilisé pour `rose_kunoichi` dans l'historique de
commit qui a introduit ce document — il est directement réutilisable en
changeant juste les chemins/le préfixe de nom de fichier.

### Piège : une échelle par frame casse les animations à pose non-statique

Pour une pose statique (`idle`), mesurer la bbox de chaque frame séparément
et en déduire une échelle individuelle fonctionne, car la silhouette a
toujours à peu près la même hauteur d'une frame à l'autre. **Ce n'est plus
vrai dès qu'un membre bouge fort** (un coup de pied, par exemple) : sur les
frames d'extension complète, le buste se penche en arrière et la hauteur
totale de la bbox (tête → pied) diminue naturellement de 10-15% par rapport
à la pose debout — recalculer une échelle par frame agrandirait alors le
personnage à tort pendant l'extension, donnant un effet de zoom qui pulse au
lieu d'un vrai mouvement de jambe.

**Solution : calculer l'échelle UNE seule fois**, à partir d'une frame de
référence en pose neutre/debout de la même série (ex. la première frame,
garde debout), puis appliquer cette **même échelle fixe** à la bbox propre
de chaque frame (bbox différente par frame, échelle identique pour toutes) :

```powershell
$refImg = New-Object System.Drawing.Bitmap((Join-Path $srcDir "kick_mid_00.png"))
$refB = Get-BBox $refImg 128 4
$scale = $targetHeight / ($refB.maxY - $refB.minY + 1)   # calculé une fois
$refImg.Dispose()
# ... puis pour chaque frame : $newW/$newH = bbox.width/height * $scale (le même $scale)
```

Le pied au sol reste aligné sur `anchor.y` dans tous les cas puisque
`destY = footY - newHeight` est recalculé par frame — seule l'échelle est
partagée, pas la position.

### Piège : une animation aérienne (sans contact au sol) n'a pas de "pied" à ancrer

`destY = footY - newHeight` (pied aligné sur `anchor.y`) suppose un
personnage debout/au sol. Pour une pose qui tourne en l'air sur elle-même
(ex. `double_jump_salto`, un salto/front-flip complet), il n'existe aucun
point "pied" stable d'une frame à l'autre — en pleine inversion, ce sont les
cheveux ou les mains qui occupent le bas du cadrage, pas les pieds. Utiliser
la même formule que pour une pose au sol produirait un décalage vertical
erratique frame par frame (le personnage semblerait sauter/descendre selon
que la pose est repliée ou étendue), alors qu'en jeu c'est la physique du
saut (`fighter.y`) qui gère déjà la hauteur réelle — le sprite n'a besoin
que d'une position *relative* stable.

**Convention utilisée pour `double_jump_salto`** (déjà en place dans les 3
frames originales du pack, mesurée avant de la reproduire) : ancrer le
**haut** de la bbox à une position Y fixe (`y=36` pour ce pack) plutôt que le
bas, centré horizontalement comme d'habitude (`x=128`), avec une échelle
unique dérivée d'une frame de référence (voir piège précédent). Un ancrage
par le haut lit visuellement mieux qu'un ancrage par le bas pendant une
rotation, parce que la tête/le haut du corps reste la partie la plus stable
d'un tuck (repli) tout du long, alors que "le bas" change de sens (pieds →
mains → cheveux → pieds) au fil de la rotation.

**Vérifier laquelle des deux conventions s'applique avant de composer une
nouvelle animation** : mesurer la bbox des frames *existantes* de cette même
clé d'animation dans le canevas 256×256 (si elles existent déjà) — un
`minY` identique sur toutes les frames avec un `maxY` qui varie signale un
ancrage par le haut (aérien) ; un `maxY` figé juste sous `anchor.y` avec un
`minY` qui varie signale un ancrage par le pied (au sol). Ne pas supposer
que toutes les animations du pack suivent la même règle.

**Remarque pour la prochaine fois** : `py -c "import PIL"` fonctionne sur ce
poste (Pillow est installé au niveau de l'interpréteur global, contrairement
à `python`/`python3` qui sont des stubs Windows Store inertes) — un script
Python + Pillow ferait la même chose que le PowerShell ci-dessus, sans doute
plus lisible. Non testé pour cette tâche (le PowerShell a été fait en
premier et validé), mais à essayer en priorité la prochaine fois pour éviter
`Get-Pixel` pixel-par-pixel qui est lent sur de grandes images.

## Étape 8 — Mettre à jour `manifest.json`

Mettre à jour uniquement les clés **réellement lues par le moteur**
(`FighterSpriteSet.__init__` dans `retro_fighter/sprites.py`) :
`animations.<clé>.frames` (liste ordonnée), `frame_count` (cosmétique mais
autant la garder juste), `fps`, `loop`. Les autres clés (`sheet`,
`source_mapping`, `notes`...) ne sont jamais lues par le jeu — les mettre à
jour reste utile pour la traçabilité humaine, mais ce n'est pas bloquant si
le temps manque.

### Piège critique : une clé d'animation peut exister dans le manifest sans jamais être lue en jeu

Le nom d'une clé dans `animations.<clé>` n'est pertinent que si
`Renderer.animation_key()` (`retro_fighter/renderer.py`) produit
effectivement cette chaîne pour un état de combat donné. Trouvé sur
`rose_kunoichi` HD : la clé s'appelait `crouch_block` dans le manifest, mais
`animation_key()` retourne `f"block_{fighter.block_level}"` (soit
`block_low`) pour un personnage accroupi qui bloque — `crouch_block` n'était
donc **jamais** atteint, et `FighterSpriteSet.get_frame()` retombait
silencieusement sur `idle` à chaque fois (aucune erreur, juste la mauvaise
pose affichée). Soigner l'image d'une clé morte ne change rien au jeu tant
que le nom de clé ne correspond pas.

**Avant de faire confiance à une clé, vérifier concrètement quelle chaîne
`animation_key()` produit** pour l'état de combat visé (grep `retro_fighter/
states.py` pour l'enum `FighterState` et `renderer.py` pour les
cas spéciaux comme `block_{level}` ou le fallback `dash`/`walk`) — ne pas
supposer que le nom "logique" de la pose (ex. `crouch_block`) est la clé
réellement utilisée. L'étape 10 (rejeu headless) est la seule vérification
qui aurait détecté ce problème — `validate_manifest.py` ne le voit pas
puisque la clé morte est un JSON par ailleurs valide.

## Étape 9 — Valider

```bash
py tools/sprites/validate_manifest.py assets/fighters/hd/<fighter_id>
```

(`py`, pas `python`/`python3`, pour la même raison qu'à l'étape 6). Vérifie
JSON valide, toutes les frames listées existent, tailles cohérentes entre
frames d'une même animation, `anchor` présent. Ne vérifie **pas** la
position du personnage dans le canevas (une frame mal recentrée passe la
validation sans erreur) — d'où l'importance de l'étape 10.

## Étape 10 — Rejouer l'animation en tête (headless), avant de committer

Il n'existe pas de skill dédiée "lancer le jeu" dans ce repo, mais
`scripts/record_demo.py` montre le pattern à réutiliser : forcer
`SDL_VIDEODRIVER=dummy` / `SDL_AUDIODRIVER=dummy` **avant** d'importer
`pygame`, puis piloter `retro_fighter.game.Game` directement (pas besoin de
fenêtre réelle ni de clavier) et sauvegarder des captures avec
`pygame.image.save`.

Deux pièges à connaître :

- **Le venv du projet a `pygame`, pas l'interpréteur global** :
  `./.venv/Scripts/python.exe mon_script.py`, pas `py mon_script.py`.
- **Le pack HD n'est pas affiché par défaut** : `Game()` démarre en mode LD
  (silhouettes simples). Appeler explicitement
  `game.renderer.set_graphics_variant("hd")` (ou `"v2"` pour le pack
  Blender-rigged, voir `HOW_TO_GENERATE_V2_SPRITES.md`) après
  `game.start_match(...)` pour voir réellement le pack qu'on vient de
  modifier — sinon on valide silencieusement le mauvais pack.

Script minimal (à adapter, cf. le script utilisé pour `idle` dans
l'historique de commit) :

```python
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import sys; from pathlib import Path
sys.path.insert(0, str(Path(r"c:\...\retro_fighter_project")))
import pygame
from retro_fighter.game import Game
from retro_fighter.input_manager import Command
from retro_fighter.config import FPS, ROUND_TIME_SECONDS

game = Game()
game.start_match("sparring")   # l'IA sparring ne fait rien, pratique pour figer une pose
game.renderer.set_graphics_variant("hd")   # sinon on regarde le pack LD par erreur

empty = Command()
for i in range(30):
    game.frame += 1
    game.round_time_remaining = ROUND_TIME_SECONDS - (game.frame - game.round_start_frame) / FPS
    game.player.update(empty, game.enemy); game.enemy.update(empty, game.player)
    game.spawn_projectiles(); game.update_projectiles()
    game.resolve_body_collision(); game.apply_hits(); game.check_round_over()
    if i % 3 == 0:
        game.renderer.draw(game); pygame.display.flip()
        pygame.image.save(game.screen, f"out/tick_{i:03d}.png")
```

Relire quelques captures réparties sur un cycle complet de l'animation
(fps × durée du cycle = nombre de frames à parcourir) : le personnage doit
rester parfaitement immobile au sol (pas de flottement ni de glissement
d'un pixel à l'autre) pendant que la pose change subtilement.

## Nettoyage avant de committer

- Ne pas laisser de dossier de sauvegarde manuel des anciennes frames
  (`frames_backup_*`) : git suit déjà l'historique des fichiers modifiés,
  un tel dossier est redondant et pollue le diff. `git status`/`git diff`
  suffisent pour comparer avant/après.
- `.playwright-mcp/` (captures, snapshots, zips téléchargés) est gitignored
  — pas besoin de le nettoyer à la main, mais vérifier qu'aucun fichier de
  ce dossier n'a été accidentellement `git add`é.

## Checklist des pièges à ne pas reproduire

- [ ] Si `browser_navigate` échoue avec "Browser is already in use for
      ...\.playwright-mcp-profile", chercher le process orphelin AVANT
      d'agir (`Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" |
      Where-Object { $_.CommandLine -like '*playwright-mcp-profile*' }`) et
      ne tuer que celui-là — jamais de `msedge.exe` au hasard, l'utilisateur
      peut avoir son navigateur perso ouvert en parallèle.
- [ ] Le profil Playwright par défaut n'est **pas connecté** à ChatGPT —
      vérifier avant d'uploader quoi que ce soit, ne pas juste supposer.
- [ ] Basculer sur le vrai profil Edge = fermer Edge + redémarrer la
      session Claude Code ; **toujours demander confirmation**, c'est un
      changement de config global.
- [ ] `browser_file_upload` : faire correspondre **exactement** la casse de
      la lettre de lecteur à celle indiquée dans "Allowed roots" en cas
      d'erreur `outside allowed roots`.
- [ ] Demander **une planche unique**, pas des images séparées, pour la
      cohérence du personnage.
- [ ] Zoomer réellement (PowerShell crop + upscale, pas juste le screenshot
      brut) avant de valider une planche.
- [ ] Un bouton "Download ..." qui apparaît comme texte brut (pas de rôle
      `button`/`link` dans le snapshot) = recharger la page entière, ne pas
      attendre ni redemander.
- [ ] Ne jamais coller des frames générées directement dans `frames/` sans
      les recomposer sur le canevas 256×256 à l'ancrage attendu — sinon le
      personnage saute visuellement au changement d'animation/variante.
- [ ] `python`/`python3` sont des stubs Windows Store inertes sur ce poste ;
      utiliser `py` pour un interpréteur global (Pillow y est installé), et
      `./.venv/Scripts/python.exe` pour tout ce qui a besoin de `pygame`.
- [ ] Le pack HD ne s'affiche pas par défaut dans le moteur — appeler
      `game.renderer.set_graphics_variant("hd")` avant de vérifier visuellement.
- [ ] `validate_manifest.py` ne vérifie pas le positionnement dans le
      canevas — une frame mal recentrée passe la validation sans erreur,
      seule une vérification visuelle en jeu le révèle.
- [ ] Le nom d'une clé d'animation (`idle`, `walk`...) ne décrit pas la
      pose attendue — la décrire en langage corporel concret et joindre
      en référence d'**autres animations déjà correctes** du même
      personnage (pas seulement les frames qu'on est en train de
      remplacer), surtout pour une pose de combat qui doit rester "prête
      à agir" (genoux fléchis, garde haute) et non "au repos".
- [ ] Une bbox dont `minX`/`minY` vaut 0 (ou touche le bord) est suspecte :
      un pixel de bordure opaque résiduel du despill peut fausser toute la
      mesure. Toujours exclure une marge de quelques pixels des bords avant
      de scanner, et visualiser le canal alpha en niveaux de gris une fois
      par lot pour confirmer un chroma-key propre avant de faire confiance
      aux chiffres.
- [ ] Pour une animation où un membre s'étend fortement (coup de pied/poing
      en extension complète), ne PAS recalculer une échelle par frame — le
      buste qui se penche en arrière réduit la hauteur de bbox et ferait
      "zoomer" le personnage à tort. Calculer l'échelle une seule fois sur
      une frame debout/neutre de la série, l'appliquer à toutes.
- [ ] Au-delà de 10 frames, faire deux planches de 10 (grossière puis
      intercalaire) plutôt qu'une planche géante illisible — voir "Cas des
      animations à plus de 10 frames".
- [ ] Deux planches générées séparément peuvent avoir un zoom légèrement
      différent même avec "same framing" dans le prompt : calculer l'échelle
      fixe **séparément pour chaque planche** (sur sa propre frame neutre),
      jamais une seule échelle pour tout le lot combiné.
- [ ] Demander une "marche"/"walk" sans préciser le mécanisme donne une
      démarche humaine normale (jambes qui alternent). Pour un personnage de
      combat, décrire explicitement le pas chassé de boxeur : quel pied
      reste devant en permanence, dans quel ordre chaque pied bouge.
- [ ] La technique "10 poses-clés + 10 intercalaires" densifie une position
      déjà capturée mais n'ajoute pas l'articulation du pied qui n'existait
      pas dans les poses de départ (symptôme : "claquettes", écart de jambes
      figé mais angle du pied qui saute). Pour un vrai mouvement continu sur
      plusieurs dizaines de frames, découper le mouvement en sous-phases
      mécaniques réelles et générer des planches chaînées séquentiellement
      (chaque planche référence le dernier panneau réel de la précédente) —
      voir "Planches chaînées séquentiellement" plus haut.
- [ ] Une planche qui ignore une sous-phase demandée (ex. jambe censée être
      en l'air, mais reproduit une pose statique large sur les 10 panneaux)
      se détecte en zoomant spécifiquement sur la zone concernée (les pieds)
      sur toute la largeur de la planche. À refaire avec une référence
      visuelle concrète jointe (silhouette seule, pas juste une description
      texte) plutôt qu'une simple reformulation du prompt.
- [ ] Une ancienne frame remplacée/supprimée reste récupérable via
      `git show HEAD:chemin > fichier_temp` et reste une référence visuelle
      valide pour UN détail précis (une silhouette, un angle), même si le
      reste de cette vieille frame est le bug qu'on corrige — préciser
      explicitement dans le prompt ce qu'il faut ignorer de cette référence.
- [ ] Le chaînage par image de continuité garantit la pose, pas l'échelle :
      chaîner les ratios de hauteur de bbox planche-à-planche (pas une
      échelle indépendante par planche) pour absorber la dérive de zoom qui
      s'accumule sur 5-6 planches, et vérifier visuellement au moins la
      frontière à plus fort écart avant de faire confiance à la correction.
- [ ] Une planche ancrée explicitement sur une pose de référence absolue
      externe pour son dernier panneau (ex. clôture de boucle) peut dériver
      en échelle en interne (cassure nette entre premier et dernier panneau,
      pas un dégradé). Ne pas interpoler l'échelle linéairement (ça produit
      un creux visible) ; interpoler la hauteur de sortie cible directement
      et recalculer l'échelle par panneau à partir de sa propre bbox brute.
- [ ] Ne jamais faire confiance à une planche sur un simple aperçu rapide —
      construire systématiquement, pour CHAQUE planche (pas seulement celle
      qui semble louche), une bande de crops serrés sur la zone censée
      bouger, sur toute sa largeur. Les sous-phases *subtiles* (lever de
      talon, roulis pied/cheville) collapsent vers un quasi-doublon bien
      plus souvent que les grands mouvements de membre — c'est précisément
      le genre de bug qui passe inaperçu sur un aperçu non zoomé et qui ne
      se corrige par aucun recalcul d'échelle en aval, puisqu'il n'y a
      simplement pas de vraie variation à exploiter.
- [ ] Pour redébloquer une planche qui reproduit une pose quasi-statique :
      d'abord exagérer la différence entre panneaux consécutifs ; si les
      poses de départ/arrivée demandées se ressemblent déjà trop pour que
      le modèle ait une raison de varier, exagérer plutôt le MILIEU du
      mouvement (une pose intermédiaire nettement différente des deux
      bouts, ex. un creux/accroupissement marqué) pour lui donner un vrai
      point d'ancrage visuel.
- [ ] Une cassure d'échelle interne à une planche qui coïncide EXACTEMENT
      avec la frontière de ligne (panneau 5/6 d'une grille 5×2) et forme
      deux plateaux plats est un artefact de rendu (les deux lignes
      rendues à deux zooms différents), pas du mouvement réel — même sans
      ancrage sur une référence externe absolue. Le corriger avec une
      échelle fixe en deux morceaux (une par ligne, chaînées en continuité
      à la frontière), à ne pas confondre avec un vrai dégradé de pose
      (ex. un accroupissement volontaire) qu'il ne faut surtout pas aplatir.
- [ ] Une animation sans contact au sol (saut/salto en pleine rotation) n'a
      pas de "pied" stable à ancrer sur `anchor.y` — mesurer les frames
      existantes de cette clé pour savoir si le pack ancre par le haut
      (`minY` fixe, convention aérienne) ou par le pied (`maxY` fixe juste
      sous `anchor.y`, convention au sol) avant de composer de nouvelles
      frames, ne pas supposer que toutes les animations suivent la même
      règle.
- [ ] Une clé ajoutée/renommée dans `animations.<clé>` du manifest peut être
      un JSON parfaitement valide (passe `validate_manifest.py`) tout en
      n'étant **jamais lue en jeu** si elle ne correspond pas exactement à
      ce que `Renderer.animation_key()` produit pour l'état de combat visé
      (ex. `crouch_block` vs la vraie clé lue `block_low`, dérivée de
      `f"block_{{fighter.block_level}}"`). Toujours vérifier la chaîne
      réellement produite par `animation_key()` (grep `states.py` +
      `renderer.py`) avant de faire confiance au nom "logique" de la pose —
      seul le rejeu headless (étape 10) aurait détecté ce genre de clé
      morte.
