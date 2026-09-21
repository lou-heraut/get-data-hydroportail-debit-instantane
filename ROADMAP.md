# Ce qui reste à faire

État au 21 septembre 2026 : **v1.0.0 livrée**. Ce que cette version contient est
dans [CHANGELOG.md](CHANGELOG.md), pourquoi elle est faite ainsi dans
[DESIGN.md](DESIGN.md), et ce que la source fait réellement dans
[SOURCE.md](SOURCE.md).

Ce fichier ne garde que l'avenir. Il rétrécit à chaque version, voir la section
« Cycle de vie des fichiers » de [CLAUDE.md](CLAUDE.md).

## L'outil de rééchantillonnage

**C'est ce que la demande d'origine réclamait vraiment.** La v1 livre la donnée
native, qui est le socle dont toute grille se déduit, mais elle ne répond pas
encore à la question posée : une chronique à pas régulier, d'une heure ou moins,
utilisable pour étudier les éclusées.

Le point de départ a changé en cours de route. On comptait sur l'interpolation
côté serveur, `Qln` avec un pas choisi ; la mesure montre qu'elle perd 78 % des
points de rupture de la série validée, donc qu'elle dégrade la donnée au lieu de
la servir. Cette voie est fermée.

**Ce sera un outil paramétrable et non une grille figée**, ce qui évite
d'enfermer un choix scientifique dans un fichier et laisse l'analyste assumer le
sien. Quatre points demandent un arbitrage qui n'est pas technique :

1. **La loi d'interpolation.** Linéaire par défaut, mais l'hydrogramme d'éclusée
   a des fronts raides ; une interpolation linéaire sur un pas de deux heures
   arrondit les angles et biaise toute métrique de gradient.
2. **Le seuil au delà duquel on renonce à interpoler**, à confronter à la
   distribution réelle des écarts, que `couverture.csv` donne désormais station
   par station et année par année.
3. **Les modalités d'application du seuil** : coupe franche laissant la grille
   vide, ou marquage conservant la valeur avec un indicateur de confiance.
4. **Ce qu'on publie à côté de la valeur.** L'idiome des dépôts voisins veut
   qu'une colonne dérivée s'accompagne d'une colonne qui dit jusqu'où la croire.
   Ici ce serait l'écart en minutes à la mesure réelle la plus proche.

`QmnH`, le débit moyen horaire, reste à écarter pour ce sujet : une moyenne
lisse précisément les montées et descentes qui font l'éclusée.

## Les questions ouvertes

### La liste des 68 stations

En attente. Tout a été vérifié sur dix stations choisies pour couvrir les cas
limites, ce qui est solide, mais une vraie liste réserve des surprises : des
codes de site glissés parmi les codes de station, des stations sans débit, des
chroniques plus courtes qu'annoncé.

Le premier geste est `--inventaire` sur les 68 codes, immédiat et sans
téléchargement lourd. Le `couverture.csv` partiellement rempli qui en sort se
transmet tel quel à la demandeuse, pour qu'elle choisisse ses stations avant
qu'on engage les heures de téléchargement.

### Le réseau RRSE

Son code n'a pas été identifié dans `code_sandre_reseau_station`, dont les
valeurs sont opaques. À reprendre si le besoin s'en fait sentir.

### Le signal de révision des courbes de tarage

Pour une éventuelle mise à jour incrémentale : le JSON porte un champ
`correctionCurves`, vide sur tous les essais. S'il expose un jour les courbes et
leurs dates, il donne le signal qui manque. Les empreintes SHA-256 par station,
posées en v1, rendent en attendant mesurable ce qui a bougé dans le passé.

## Ce qui est tranché, et qu'on ne rouvre pas

Le raisonnement de chacun est dans [DESIGN.md](DESIGN.md). Cette liste n'est là
que pour éviter de les rediscuter par oubli.

- **Une seule table de faits**, pas de chronique séparée : ce serait une vue, et
  le README porte la ligne qui la produit.
- **Une table de couverture station x année x statut**, parce qu'un pas médian
  unique par station dit le contraire de la vérité aux deux bouts.
- **On prend tout.** La variabilité de quantité et de qualité est le principe de
  la donnée hydrométrique, pas un défaut à corriger ni une limite à excuser.
- **`--statuts raw`**, pas `brut` : un nom de paramètre de la source se recopie.
- **Pas de compte HydroPortail**, le gain est illusoire sous gzip.
- **Pas de hauteur d'eau**, seulement le débit.
- **Pas de fusion par horodatage** entre niveaux de statut.
- **Pas de filtrage de qualité par défaut**, jamais.
- **Pas d'incrémental** tant qu'aucun signal de révision n'est exposé.
