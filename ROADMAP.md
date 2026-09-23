# Ce qui reste à faire

État au 22 septembre 2026 : **v2.0.0 livrée**. Ce que chaque version contient est
dans [CHANGELOG.md](CHANGELOG.md), pourquoi elle est faite ainsi dans
[docs/design.md](docs/design.md), et ce que la source fait réellement dans
[docs/findings.md](docs/findings.md).

Ce fichier ne garde que l'avenir. Il rétrécit à chaque version, voir la section
« Cycle de vie des fichiers » de [CLAUDE.md](CLAUDE.md).

## L'outil de rééchantillonnage

**C'est ce que la demande d'origine réclamait vraiment.** La v1 livre la donnée
native, qui est le socle dont toute grille se déduit, mais elle ne répond pas
encore à la question posée : une chronique à pas régulier, utilisable pour
étudier les éclusées. Le pas visé est de quinze minutes, une heure au plus, et
le même d'un bout à l'autre.

L'interpolation côté serveur, `Qln` avec un pas choisi, est fermée : la mesure
montre qu'elle perd 78 % des points de rupture de la série validée.

### Le cadre, tel qu'il se dessine au 23 septembre

Trois choses ont changé la manière de poser le problème. Les références sont
dans [docs/references.md](docs/references.md).

- **On agrège, on n'échantillonne pas.** Nos collègues hydrologues le demandent,
  et la norme de l'OMM le définit : la valeur d'un pas est la moyenne pondérée
  par le temps, c'est-à-dire l'intégrale de la courbe par la méthode des
  trapèzes, les bornes interpolées étant marquées. Lire la courbe à des instants
  fixes est écarté, c'est ce qui prétendrait à une information absente.
- **Pour le validé, le critère est la tolérance, pas le pas.** Si la série
  validée est élaguée comme l'était la Banque Hydro, à 5 % du débit, un écart de
  trois heures entre deux points est une courbe certifiée et non un trou, et
  l'intégrer sur quinze minutes ne crée rien. La règle « le pas agrégé doit
  dépasser le pas de l'instrument » vaut pour le brut.
- **Personne en aval ne tranchera l'hydrologie à notre place.** L'équipe
  demandeuse n'a pas à arbitrer ces questions : le travail est de livrer des
  produits définis, documentés, vérifiés et rattachés à la littérature, chacun
  avec ce qu'il vaut, et non de résoudre parfaitement leur problème. Le format
  est le parquet, comme le reste.

Une grille régulière entre quinze minutes et une heure, dont la méthode est
écrite et justifiée, est l'objectif.

### La direction retenue pour le brut, le 23 septembre

**Un pas de sortie n'est rempli que s'il est porté par la mesure** : aucun
écart entre deux points bruts voisins qui le chevauche ne dépasse sa durée. Le
critère se juge pas par pas, sans découper la chronique en régimes, et c'est ce
qui garantit qu'on n'agrège jamais plus fin que ce que le capteur a enregistré.
Le constat qui le fonde, et ce qu'il garde sur le jeu de test à 15, 30 et
60 minutes, est dans [docs/findings.md](docs/findings.md), section « Ce que
chaque pas de sortie garde du brut ». Il en découle trois choses à construire :

1. **Une table de support par station, année et pas candidat**, la part de la
   chronique que chaque pas garde. C'est elle qui justifie auprès de l'équipe
   demandeuse le pas retenu : elle montre ce qu'on garde, ce qu'on perd, et
   pourquoi un pas plus fin aurait inventé de la donnée.
2. **Le choix du pas pour un ensemble de stations**, par optimisation sur cette
   table : parmi les pas candidats, celui qui maximise la donnée gardée sur
   l'ensemble, sous la contrainte d'un même pas partout. Le critère exact reste
   à écrire, total de pas gardés, ou nombre de station-années au-dessus d'un
   seuil, et il se discute sur les éclusées.
3. **L'agrégation elle-même**, l'intégrale par les trapèzes sur chaque pas
   porté, avec le minimum et le maximum, et un pas vide sinon.

La série validée, qui seule existe avant 2013, relève d'une autre logique,
celle de la tolérance. Si la voie du validé est retenue, voir le point d'étape
plus bas, ce critère ne vaut plus que pour la queue brute de `most_valid`, et la
table de support porte, pour la partie validée, les jours certifiés par
`QIXnJ` et la densité du validé.

### Les produits envisagés

| produit | définition | à quoi il sert |
|---|---|---|
| natif | la chronique servie, déjà livrée | l'indicateur de Courret, qui prend un pas variable |
| moyenne | intégrale trapézoïdale sur le pas, divisée par sa durée | l'entrée de `hydropeak`, l'usage courant |
| minimum et maximum | extrêmes instantanés dans le pas, bornes comprises | garder l'amplitude que la moyenne aplatit |

Chaque pas porterait la part de sa durée réellement couverte et le plus grand
écart entre deux points utilisés, et resterait vide là où la chronique est
discontinue.

### Ce qui est en place

- **`hydroportail/aggregate.py`**, l'agrégation d'une série sur des pas
  réguliers : moyenne par intégrale, minimum et maximum bornes comprises, plus
  grand écart entre points voisins et drapeau `mesure_suffisante`. Testé, et
  vérifié
  contre le `QmnH` d'HydroPortail, qu'il reproduit à l'arrondi près. Il n'est
  encore branché sur aucune commande. Ses deux dernières colonnes ont été
  renommées parce qu'on les lisait mal : `plus_grand_ecart_min`, le plus grand
  écart en minutes entre deux points voisins qui touche le pas, et
  `mesure_suffisante`, vrai quand cet écart ne dépasse pas la durée du pas.
- **`explore/`**, deux scripts de figures, hors de l'outil, installés par
  `pip install -e ".[explore]"` et écrivant dans `data/_exploration/` :
  `plot_days.py`, quelques journées à 15 et 60 minutes en PNG et PDF, et
  `plot_year.py`, une station et une année à parcourir dans le navigateur, brut
  et validé côte à côte.

### Ce que les journées d'exemple ont montré, le 23 septembre

Quatre journées du jeu de test, tracées par `explore/plot_days.py`. Ce sont des
exemples choisis, pas une mesure, mais ils orientent la suite :

- **le pic résiste, le gradient non.** Sur un front de dix minutes à Moûtiers,
  la moyenne à 15 minutes garde le pic à 0,5 % près mais perd 60 % du gradient
  maximal, celle à 60 minutes 84 %. Sur la montée de deux heures de l'Ain, 15
  minutes garde presque tout ;
- **le maximum du pas garde le pic intact**, ce qui justifie de livrer le trio
  moyenne, minimum et maximum plutôt que la moyenne seule ;
- **agréger au pas natif lisse déjà** : à Embrun, brut à 15 minutes, la moyenne
  à 15 minutes est celle des deux points qui bornent le pas, et perd un quart du
  gradient. Le pas de sortie doit dépasser le pas natif, pas seulement l'égaler ;
- **un artefact du brut devient une fausse éclusée.** Un point isolé à
  298 m³/s entre deux valeurs à 16,3 donne une moyenne de 63 m³/s sur son pas.
  Le producteur l'a marqué douteux et la validation l'a retiré, voir
  [docs/findings.md](docs/findings.md).

### Ce qu'il faut mesurer avant de figer quoi que ce soit

Sur le jeu de test d'abord, qui est fixe et suffit à voir ce qui est
atteignable, puis sur les éclusées. Chaque résultat ira dans
[docs/findings.md](docs/findings.md).

Une première est faite : **`QmnH`, le débit moyen horaire d'HydroPortail, est
l'intégrale par la méthode des trapèzes** de la série `most_valid`, validé ou
pré-validé compris, sur l'heure qui suit son horodatage. Le producteur agrège
donc déjà comme nos collègues le demandent, y compris sur une courbe élaguée à
un point toutes les trois heures, et `QmnH` devient la référence contre
laquelle vérifier notre propre calcul au pas horaire. Il n'existe pas en brut
et ne descend pas sous l'heure : ce n'est pas un produit.

1. **Ce que coûte l'agrégation, en chiffres.** Les journées ont montré le
   mécanisme ; reste le bilan sur toute la période brute, séparément selon le
   pas d'origine, de cinq à soixante minutes : perte de gradient maximal et
   d'amplitude à 15, 30 et 60 minutes, puis nombre d'éclusées détectées selon
   les critères de Courret.
2. **Les points douteux du brut.** Combien sont marqués `q = 12`, combien sont
   des artefacts isolés comme celui de W283201001, et ce que la validation en
   fait. C'est ce qui décidera s'il faut les écarter avant d'agréger.
3. **Le validé tient-il les fronts ?** Mesuré, voir
   [docs/findings.md](docs/findings.md) : agrégé à quinze minutes, il garde les
   pics partout, et les gradients à 94 % ou plus au-delà de vingt-cinq points
   par jour, aux deux tiers à dix ou moins. Reste à départager, dans les
   gradients que le brut a de plus, le signal perdu du bruit retiré.
4. **Le code `c` et les trous.** Mesuré : `c` ne marque pas les trous, la carte
   `QIXnJ` si, sans ambiguïté. Un long écart du validé est un segment certifié
   si ses jours y figurent, un trou sinon.

### Le choix de la source : où en est le raisonnement, le 23 septembre

Point d'étape, pour ne pas mélanger brut et validé au gré des besoins. Trois
voies, confrontées à la littérature de
[docs/references.md](docs/references.md) et à nos constats :

| voie | pour | contre, et risque |
|---|---|---|
| **A. le validé** (`most_valid`) | la chronique que le producteur publie comme définitive ; artefacts retirés ; profonde ; c'est sur elle que Courret a calé ses seuils | élaguée : les gradients s'atténuent là où elle est clairsemée ; sa queue récente est du brut provisoire |
| B. le brut | dense, pas élagué | provisoire au sens de l'OMM ; artefacts, dont certains non marqués, qui deviennent de fausses éclusées ; commence en 2013, à 60 minutes par endroits ; ses gradients bruités ne se comparent pas aux seuils de Courret |
| C. le meilleur des deux, pas par pas | le plus d'information apparente | une chronique dont la nature change sans cesse ; aucune référence ne le fait, et la v1 l'a déjà refusé point par point |

**La voie A est celle vers laquelle tout converge**, et c'est la proposition à
trancher :

- **la source est `most_valid`**, telle que le producteur l'arbitre, avec pour
  chaque pas le statut dont il vient, pour que la queue provisoire se voie ;
- **le brut n'est pas une source mais un témoin** : il sert à mesurer ce que le
  validé garde, jamais à le compléter ;
- **ce qui dit si un pas est rempli dépend du statut.** Sur la partie validée,
  la carte `QIXnJ` : un jour certifié se remplit, un trou reste vide. Sur la
  queue brute, l'écart entre points voisins, comme mesuré sur le brut ;
- **ce qui dit jusqu'où croire les fronts est la densité du validé**, points
  par jour, que la mesure 3 relie au gradient gardé.

Les risques qu'on accepte ainsi, et qu'il faut écrire dans la notice : des
gradients sous-estimés d'un tiers environ les jours où le validé compte moins
de dix points, et une queue récente de nature différente, provisoire. Ce qui
reste à trancher avec cette voie : la période ancienne, les relevés d'échelle
qui ne sont pas une courbe élaguée, et le pas de sortie, que la densité du
validé et la table de support aideront à choisir.

### Ce qui reste ouvert après ces mesures

- **Le statut qui sert de source.** Voir le point d'étape ci-dessus : la voie
  du validé est proposée, elle reste à trancher.
- **La période ancienne.** Les relevés d'échelle, une lecture par jour, ne sont
  pas une courbe élaguée : il faudra une limite, par date ou par écart entre
  points.
- **Quinze minutes ou une heure.** Le brut récent soutient quinze minutes ; le
  validé, là où il est dense, aussi. Rien n'interdit de livrer
  les deux pas.
- **Des figures dans le processus.** Celles d'`explore/` ont servi à comprendre ;
  une version par station, la couverture et quelques journées en PDF, la
  chronique entière à parcourir en HTML, aiderait à choisir le pas et à le
  justifier auprès de l'équipe demandeuse. À décider une fois la méthode
  figée : ce qu'elles montrent, et si elles accompagnent le livrable.
- **L'incertitude.** Une question à poser à Benjamin Renard : que devient
  l'incertitude quand on intègre une courbe élaguée à une tolérance donnée.

## Les questions ouvertes

### La campagne des éclusées

Le cas `2026-09_eclusees-rmc` est prêt : sa liste est traduite, ses arbitrages
sont posés et ses 47 stations sont inventoriées. Ce que la traduction et
l'inventaire ont donné est mesuré dans [docs/findings.md](docs/findings.md), section « Ce
qu'une liste réelle a donné » ; comment les trois stations ambiguës ont été
tranchées est dans l'`arbitrations.csv` du cas, avec le motif de chacune.

Il reste à lancer le téléchargement, qui ne dépend d'aucune réponse puisqu'il
rapatrie la donnée native dont toute grille se déduira :

```bash
python download_hydroportail.py --case 2026-09_eclusees-rmc
```

Trois points à soumettre à l'équipe demandeuse, aucun ne bloque le
téléchargement :

1. **Les quatre codes sans station.** Deux sont des absences établies, l'Arc à
   Saint-Michel et l'Eau d'Olle à Allemond, qui ne portent aucun débit
   instantané. Les deux autres, la Romanche à Livet-et-Gavet et le Rhône à
   Ruffieux, ne sont pas conclus : le service refuse de servir une de leurs
   stations, et une station non sondée ne prouve rien.
2. **L'écart entre 51 et les 68 stations annoncées**, toujours inexpliqué.
3. **Le `coverage.csv` du cas**, à rendre pour qu'elle choisisse ses stations
   et sa période. Dix-neuf lignes de `resolved-stations.csv` restent signalées,
   pour information et non pour décision : un site qui porte plusieurs stations
   dont une seule s'appelle comme lui, ou une soeur refusée par le service qui
   ne changeait rien.

**La règle qui s'est dégagée des arbitrages vaut pour les cas suivants : la
donnée prime sur l'exploitant demandé.** Quand la station nommée ne publie pas
d'instantané et qu'une autre du même point en publie, on prend celle qui en
publie et on le signale.

### Le réseau RRSE

Son code n'a pas été identifié dans `code_sandre_reseau_station`, dont les
valeurs sont opaques. À reprendre si le besoin s'en fait sentir.

### Le signal de révision des courbes de tarage

Pour une éventuelle mise à jour incrémentale : le JSON porte un champ
`correctionCurves`, vide sur tous les essais. S'il expose un jour les courbes et
leurs dates, il donne le signal qui manque. Les empreintes SHA-256 par station,
posées en v1, rendent en attendant mesurable ce qui a bougé dans le passé.

## Améliorations d'usage, repérées et non engagées

Aucune n'est nécessaire à la campagne, toutes feraient gagner du temps à qui
doit choisir des stations.

### Une frise de couverture, là où elle aide à voir

Un tableau de chiffres dit combien de jours une station porte, jamais la forme
de sa chronique. Une ligne par station, un caractère par année, montre d'un coup
d'oeil ce qu'aucune colonne ne montre : un remplacement de station, une
publication qui passe du continu à l'épisodique, un trou de dix ans.

```
Bourne a St-Just       2003                        2026
  W334000102   3241 j  ++#         +#####+...+.
  W334000101     64 j                        ++

#  annee pleine     +  30 a 300 jours     .  quelques jours
```

C'est ce qui a rendu les trois arbitrages évidents en quelques secondes. La
place naturelle est le résumé de `--inventory` et le rapport de
`prepare_list.py`, pas les CSV, qui restent des données.

**Le motif dépasse ce dépôt.** `get-data-hubeau-onde` et
`get-data-vigieau-secheresse` ont le même problème, une couverture qu'aucun
tableau ne montre : des campagnes de terrain par département et par année pour
l'un, des arrêtés par zone et par année pour l'autre. Si la frise se révèle
utile ici, elle est à reprendre là-bas.

### Ramener les champs de texte du référentiel

`commentaire_station`, `commentaire_influence_locale_station` et
`descriptif_station` portent le récit du producteur : pourquoi une station
existe, ce qu'elle vaut, par quoi elle a été remplacée. C'est là qu'était la
réponse pour le Verdon à Vinon, où le producteur écrit lui-même que le capteur
de l'ancienne station était sous le pont et ses hauteurs toutes douteuses, et
qu'il en a installé une autre 20 m en amont pour cette raison.

Les afficher au moins sur les lignes signalées éviterait de refaire l'enquête à
la main. Les ajouter à `stations.csv` serait plus utile encore, mais c'est un
changement du format livré, donc une décision de version : ce sont des textes
libres et longs, dont il faudrait choisir la place et la troncature.

### Un dictionnaire du produit agrégé

Chaque colonne du produit agrégé demandera une définition d'une phrase, lisible
par qui n'a pas suivi sa construction, comme `schema.py` en donne déjà pour la
table native dans le `datapackage.json`. Les premiers noms se sont avérés
ambigus à la lecture ; les définitions se relisent avec un regard extérieur
avant la livraison.

### Changer de pas dans les pages d'exploration

Les pages de `explore/plot_year.py` sont faites pour un pas à la fois. Un
sélecteur entre 15, 30 et 60 minutes sur la même page permettrait de voir
directement ce que chaque pas garde. Utile si ces pages deviennent un outil de
décision, sinon superflu.

## Ce qui est tranché, et qu'on ne rouvre pas

Le raisonnement de chacun est dans [docs/design.md](docs/design.md). Cette liste n'est là
que pour éviter de les rediscuter par oubli.

- **Une seule table de faits**, pas de chronique séparée : ce serait une vue, et
  le README porte la ligne qui la produit.
- **Une table de couverture station x année x statut**, parce qu'un pas médian
  unique par station dit le contraire de la vérité aux deux bouts.
- **On prend tout.** La variabilité de quantité et de qualité est le principe de
  la donnée hydrométrique, pas un défaut à corriger ni une limite à excuser.
- **`--statuses raw`**, pas `brut` : un nom de paramètre de la source se recopie.
- **Pas de compte HydroPortail**, le gain est illusoire sous gzip.
- **Pas de hauteur d'eau**, seulement le débit.
- **Pas de fusion par horodatage** entre niveaux de statut.
- **Pas de filtrage de qualité par défaut**, jamais.
- **Pas d'incrémental** tant qu'aucun signal de révision n'est exposé.
