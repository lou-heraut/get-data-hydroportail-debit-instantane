# Ce qui reste à faire

État au 23 septembre 2026 : **v2.0.0 livrée**, et la méthode du
rééchantillonnage tranchée sans être encore un produit. Ce que chaque version
contient est dans [CHANGELOG.md](CHANGELOG.md), pourquoi elle est faite ainsi
dans [docs/design.md](docs/design.md), ce qu'on a constaté dans
[docs/findings.md](docs/findings.md) et ce qu'on a lu dans
[docs/references.md](docs/references.md).

Ce fichier ne garde que l'avenir. Il rétrécit à chaque version, voir la section
« Cycle de vie des fichiers » de [CLAUDE.md](CLAUDE.md).

## L'outil de rééchantillonnage

**C'est ce que la demande d'origine réclamait vraiment** : une chronique à pas
régulier, quinze minutes visées, une heure au plus, le même d'un bout à
l'autre, pour étudier les éclusées. La v2.0.0 livre la donnée native dont elle
se déduit.

**La méthode est tranchée**, et elle est dans
[docs/design.md](docs/design.md), section « Le rééchantillonnage : ce qui est
tranché » : on agrège par l'intégrale sans jamais échantillonner, chaque pas
porte sa moyenne, son minimum et son maximum, les valeurs viennent de
`most_valid` et jamais du brut là où le validé existe, et le brut dit le pas de
l'instrument et ce que le validé a perdu. Les faits qui la fondent sont dans
[docs/findings.md](docs/findings.md), la littérature dans
[docs/references.md](docs/references.md). Ce qui suit est ce qui reste.

### Ce qui existe déjà

- `hydroportail/aggregate.py` agrège une série sur des pas réguliers, testé et
  vérifié contre le `QmnH` d'HydroPortail. Il n'est branché sur aucune
  commande.
- `explore/` porte les scripts qui refont chaque mesure de la session du
  23 septembre et les figures qui ont servi à comprendre, hors de l'outil ;
  leur liste est dans [CLAUDE.md](CLAUDE.md).

### À construire, dans cet ordre

1. **La table de support**, par station, année et pas candidat, 15, 30 et
   60 minutes : la part des pas remplis selon les règles de `design.md`, jours
   certifiés par `QIXnJ` sur la partie validée, écart entre points sur la queue
   brute, et pas de l'instrument lu dans le brut ; avec la densité du validé.
   C'est elle qui justifiera auprès de l'équipe demandeuse le pas retenu : ce
   qu'on garde, ce qu'on perd, et pourquoi un pas plus fin aurait inventé de la
   donnée. `explore/raw_support.py` en fait déjà la partie brute.
2. **Le choix du pas pour un ensemble de stations**, par optimisation sur cette
   table, sous la contrainte d'un même pas partout. Le critère reste à écrire :
   total de pas remplis, ou nombre de station-années au-dessus d'un seuil.
3. **Le produit** : une table parquet par station, ses colonnes, leur
   dictionnaire, son `datapackage.json`, et une commande qui le fabrique à
   partir de ce que `download_hydroportail.py` a téléchargé.
4. **La notice**, qui dit la méthode, les références, et les risques acceptés
   que `design.md` énumère.

### À mesurer encore

- **Le signal et le bruit dans les gradients du brut.** Le validé garde les
  gradients à 94 % ou plus au-delà de vingt-cinq points par jour, aux deux
  tiers à dix ou moins ; mais une part de ce que le brut a en plus est du bruit
  ou un artefact que la validation retire à raison. Tant qu'on ne sait pas les
  départager, l'atténuation annoncée est un majorant.
- **Les mêmes mesures sur les éclusées.** Tout a été mesuré sur les huit
  stations du jeu de test. Les seuils de densité, la part des pas à 5 % près et
  la carte `QIXnJ` comme détecteur de trous sont à confirmer sur les 47
  stations du cas, qui sont celles de la demande. Les scripts d'`explore/` se
  relancent sur un autre cas en changeant `CASE` dans `explore/common.py`.
- **Les points douteux du brut** : combien sont marqués `q = 12`, combien
  d'artefacts ne le sont pas. Ils ne comptent plus pour les valeurs, puisque
  celles-ci viennent du validé, mais ils comptent pour la queue brute récente.
- **Agréger au pas natif.** À Embrun, brut à quinze minutes, la moyenne à
  quinze minutes perd déjà un quart du gradient d'une journée d'exemple. Faut-il
  exiger un pas de sortie strictement plus grand que celui de l'instrument, ou
  seulement pas plus petit ? Le critère actuel accepte l'égalité.

### À trancher

- **La période ancienne.** Avant les années soixante, et jusqu'en 1901 sur
  certaines stations, la série est faite de relevés d'échelle, une lecture par
  jour à sept heures : ce n'est pas une courbe élaguée, et une grille à quinze
  minutes y serait fictive. Il faut une limite, par date, par densité ou par
  code de méthode.
- **Quinze minutes ou une heure**, ou les deux livrés. Le brut récent et le
  validé dense soutiennent quinze minutes ; la table de support dira où.
- **Des figures dans le processus.** Celles d'`explore/` ont servi à
  comprendre. Une version par station, la couverture et quelques journées en
  PDF, la chronique à parcourir en HTML, aiderait à choisir le pas et à le
  justifier. À décider une fois le produit défini.
- **L'incertitude.** Une question à poser à Benjamin Renard, INRAE RiverLy :
  que devient l'incertitude quand on intègre une courbe élaguée à une tolérance
  donnée, et cette tolérance doit-elle entrer dans l'incertitude publiée ?

## Les questions ouvertes

### La campagne des éclusées

Le cas `2026-09_eclusees-rmc` est prêt : sa liste est traduite, ses arbitrages
sont posés et ses 47 stations sont inventoriées. Ce que la traduction et
l'inventaire ont donné est mesuré dans [docs/findings.md](docs/findings.md), section « Ce
qu'une liste réelle a donné » ; comment les trois stations ambiguës ont été
tranchées est dans l'`arbitrations.csv` du cas, avec le motif de chacune.

Le téléchargement a été lancé le 23 septembre et tournait encore à la fin de
la session. S'il n'est pas allé au bout, la même commande le reprend, le cache
ne redemandant rien de ce qu'il a déjà :

```bash
python download_hydroportail.py --case 2026-09_eclusees-rmc
```

On le sait fini quand `data/2026-09_eclusees-rmc/` porte son `coverage.csv`
complet et son `datapackage.json` ; il se contrôle ensuite comme le jeu de
test, par `check_hydroportail.py --case 2026-09_eclusees-rmc`. Un
téléchargement de ce cas coupé net le 23 septembre à la station 12 a repris
sans perte. Il s'est arrêté une seconde fois à la station 29, sur un délai
dépassé, voir ci-dessous, et a été relancé.

### Un délai dépassé arrête toute la campagne

Le 23 septembre, sur l'Isère à Grenoble, W141001001, une fenêtre `most_valid`
commençant en juillet 2009 est restée sans réponse au-delà des 600 secondes de
`REQUEST_TIMEOUT`. `requests` lève alors une exception que `_request` convertit
en `APIError`, qui arrête la campagne entière, 28 stations sur 47 faites.

Or l'outil sait déjà qu'une passerelle qui n'en finit pas de répondre étouffe
le plus souvent sous la taille de la réponse : après plusieurs 504, il lève
`TooManyPoints`, et la fenêtre est coupée en deux. Un délai de lecture dépassé
est très probablement le même symptôme, et appelle le même remède plutôt qu'un
arrêt. À corriger dans `hydroportail/api.py`, en ne traitant ainsi que le
délai de lecture, pas l'échec de connexion, qui reste une vraie panne, et à
vérifier sur cette station.

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
- **On agrège par l'intégrale, on n'échantillonne jamais**, et chaque pas porte
  sa moyenne, son minimum et son maximum.
- **Les valeurs viennent du validé**, jamais du brut là où le validé existe ; le
  brut dit le pas de l'instrument et ce que le validé a perdu.
- **Les trous du validé se lisent sur la carte `QIXnJ`**, pas sur l'écart entre
  points ni sur le code `c`.
