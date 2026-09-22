# Journal des versions

Format [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versionnage
[sémantique](https://semver.org/lang/fr/). Le troisième chiffre pour une
correction, le deuxième pour un ajout qui ne casse rien, le premier quand le
format des données livrées change.

## [2.0.0] - 2026-09-22

Une règle de langue, et tout ce qui ne la respectait pas.

### La règle

**Le français est la langue de la documentation, et de ce dont le sujet est
français par nature ; tout le reste est de la structure, et la structure est en
anglais.** Ce qu'on tape est une instruction à une machine ; ce qu'on lit est de
la prose adressée à quelqu'un, et ceux à qui elle s'adresse lisent le français.
Elle est écrite dans `CLAUDE.md`.

La donnée est le cas particulier, et il se déduit de la même règle plutôt que de
lui échapper : les noms de colonnes viennent d'un service français pour des
hydrologues français, `code_station` et `date_obs` sont les noms de Hub'Eau et
non une traduction, donc ils ne bougent pas. Pas plus que `raw` et `most_valid`,
qui viennent d'HydroPortail en anglais.

### Ce qui change

Les dossiers, les fichiers, les options et les noms de fonctions passent à
l'anglais. Le nom d'un cas suit en revanche l'intitulé de la demande, donc
`2026-09_eclusees-rmc` reste tel quel, quand le jeu de test, qui n'a pas
d'intitulé extérieur, devient `2026-09_test-set`.

```
ressources/                 ->  cases/
donnees_hydroportail/       ->  data/
  .sources/                 ->    .cache/
  <cas>/mesures/            ->    <case>/measurements/
  <cas>/couverture.csv      ->    <case>/coverage.csv
liste-recue.xlsx            ->  received-list.xlsx
stations-demandees.csv      ->  resolved-stations.csv
arbitrages.csv              ->  arbitrations.csv
verifier_hydroportail.py    ->  check_hydroportail.py
preparer_liste.py           ->  prepare_list.py
--cas --racine --fichier    ->  --case --root --file
--inventaire --statuts      ->  --inventory --statuses
--silencieux, les-deux      ->  --quiet, both
```

### Incompatibilité

Tout chemin et toute commande écrits pour une version antérieure sont à reprendre.
Le schéma des tables, lui, n'a pas bougé d'une colonne : ce sont les noms des
fichiers qui les portent qui changent, et le nom de la table `couverture` qui
devient `coverage` dans le datapackage.

Les cinq contrôles passent sur le jeu de test après renommage, et son
datapackage reste valide.

## [1.1.0] - 2026-09-22

Un dépôt qui ne télécharge jamais tout ne produit pas un jeu de données, mais
autant de petits jeux que de demandes. Cette version leur donne un nom, une
place et une identité.

### Les cas

**Un cas est une liste de stations et la raison qui la justifie.** Il porte le
même nom des deux côtés : `ressources/<cas>/` dit ce qu'on veut,
`donnees_hydroportail/<cas>/` porte ce qu'on a obtenu, avec son propre
`datapackage.json`. « J'ai utilisé le jeu `2026-09_eclusees-rmc` en v1.1.0 »
désigne désormais quelque chose d'exact.

Le contrat entre les deux tient en un fichier, `ressources/<cas>/stations.txt`,
un code par ligne. Peu importe par quel chemin la liste est arrivée, un tableur
traduit ou dix codes écrits à la main.

Les trois scripts prennent un `--cas`, et `--racine` pour qui range ailleurs.
Le dépôt naît avec deux cas : `2026-09_jeu-de-test`, les dix stations qui
couvrent les cas limites, et `2026-09_eclusees-rmc`, la demande en cours.

**Le cache des réponses monte à la racine**, au dessus des cas. Une station
rapatriée pour une demande ne l'est plus jamais pour la suivante, ce qui compte
double sur un service public et gratuit.

### Ce qui a été corrigé

**Une station refusée n'emporte plus la campagne.** Un HTTP 500 en famille
journalière ne veut pas dire « fenêtre trop large » mais « je ne sais pas servir
cette station » : le code ne découpe plus la fenêtre quinze fois pour aboutir au
même échec, il lève `UnservedStation`. Un 404 devient `UnknownStation`, parce
que Hub'Eau référence des stations que la route des séries ignore. Dans les deux
cas l'inventaire note la station, la laisse hors des tables plutôt que de la
déclarer sans débit, et continue.

### Ce qui a été ajouté

`preparer_liste.py` traduit une liste de codes reçue en codes de station
vérifiés : les codes de site sont résolus par Hub'Eau, chaque candidate est
sondée par la carte de couverture, et la table produite dit comment chaque
station a été retenue et ce qui demande un regard humain. Les choix qu'un script
ne peut pas faire seul vivent dans un `arbitrages.csv` typé, avec leur motif.

### Incompatibilité

Les tables ne sortent plus à la racine du dossier de données mais dans le
sous-dossier de leur cas, et les fonctions `read`, `read_tables` et `summary`
n'ont plus de dossier par défaut. Le schéma des tables, lui, n'a pas bougé.

## [1.0.0] - 2026-09-21

Première version. Elle rapatrie les chroniques de débit instantané telles
qu'HydroPortail les diffuse, à leur pas natif, et les livre avec de quoi savoir
ce qu'on manipule.

### Ce que la version contient

Une **table de faits**, une ligne par point publié, avec les quatre codes de
qualité du Sandre conservés par point. Un horodatage publié à deux niveaux de
validation donne deux lignes, ce qui est la stricte vérité de ce que la source
diffuse. Un fichier parquet par station, lisible seul ou comme un jeu unique.

Un **inventaire** qui dit ce que des codes de station contiennent réellement
sans télécharger de chronique, à raison d'une requête rapide chacun. Il repose
sur les résumés journaliers que le producteur calcule depuis l'instantané, et
qui n'existent donc que là où celui-ci existe.

Une **table de couverture** par station, année et statut, portant les jours de
données, le nombre de points, le pas médian et son neuvième décile. C'est elle
qui répond à la question qui commande toute analyse de variation rapide : cette
station, cette année là, décrit-elle ce que je cherche.

Un **datapackage** Frictionless valide, avec une empreinte SHA-256 par station.
Cette granularité est voulue : au passage suivant, une station dont l'empreinte
a bougé est une station dont le passé a été réécrit, ce que fait une révision de
courbe de tarage et qu'aucune logique fondée sur les dates n'attraperait.

Un **vérificateur** qui contrôle qu'aucun point servi ne manque, recoupe les
valeurs avec Hub'Eau, vérifie que les nomenclatures n'ont pas bougé et que
l'intégrité référentielle tient.

### Ce qu'elle ne fait pas, délibérément

**Aucun filtrage de qualité par défaut.** Le jeu sort complet et le README dit
ce qu'on peut en faire ; l'expertise croisée au besoin est seule à pouvoir
trancher ce qui est utilisable.

**Aucune fusion des statuts par horodatage.** Mélanger les niveaux de validation
par période a un sens, c'est ce que fait le producteur ; les mélanger point par
point produirait un objet qui n'est ni brut ni validé et qui n'a pas de
signification.

**Aucune mise à jour incrémentale.** Un débit est calculé depuis une hauteur par
une courbe de tarage, et une révision de cette courbe réécrit le passé : une
reprise fondée sur les dates manquerait ces corrections en silence. Les
empreintes posées ici rendront la question mesurable plus tard.

**Aucun rééchantillonnage à pas régulier.** La question est statistique avant
d'être technique, et l'interpolation côté serveur s'est révélée perdre 78 % des
points de rupture d'une série validée. Voir [ROADMAP.md](ROADMAP.md).

### Mesuré sur le jeu de test

Dix stations choisies pour couvrir les cas plutôt que pour représenter le
réseau, dont deux sans débit instantané et une à la couverture trouée.

```
8 stations portant du debit   8 447 816 lignes   47 Mo   ~5,5 o/ligne
duree                         24 min 51 s        soit ~3 min par station
memoire au pic                1,58 Go            une station a la fois
les cinq controles            passent
```
