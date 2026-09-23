# get-data-hydroportail-debit-instantane

Téléchargement des chroniques de **débit instantané** depuis HydroPortail, et
restructuration en un jeu de tables documenté, utilisable pour la recherche.

HydroPortail est la seule source à diffuser ces chroniques sur tout leur
historique. L'API Hub'Eau, qui sert la plupart des besoins en données de débit
françaises, ne donne l'instantané que sur un mois glissant et ne descend pas
sous le pas journalier au delà. Le besoin d'origine est l'analyse des cours
d'eau à éclusées, qui demande de voir la variation infra-horaire du débit, donc
précisément ce que le pas journalier efface.

## Sommaire

- [Installation](#installation)
- [Télécharger](#télécharger)
- [À quoi ressemblent les données](#à-quoi-ressemblent-les-données)
- [Deux façons de lire](#deux-façons-de-lire-selon-ce-quon-a-sous-la-main)
- [Relire les données en Python](#relire-les-données-en-python)
- [Relire les données en R](#relire-les-données-en-r)
- [Ce qu'il faut savoir avant d'analyser](#ce-quil-faut-savoir-avant-danalyser)
- [Utiliser la source avec ménagement](#utiliser-la-source-avec-ménagement)
- [Pour aller plus loin](#pour-aller-plus-loin)
- [Citer](#citer)
- [Licence](#licence)

## Installation

```bash
git clone https://github.com/lou-heraut/get-data-hydroportail-debit-instantane
cd get-data-hydroportail-debit-instantane
python3 -m venv .python_env
source .python_env/bin/activate
pip install -e .
```

Python 3.10 ou plus, avec `requests`, `pandas` et `pyarrow`. La validation
facultative du `datapackage.json` demande `frictionless` :
`pip install -e ".[validation]"`.

## Télécharger

**Tout part d'un cas.** Un cas est une liste de stations et la raison qui la
justifie : `cases/<case>/stations.txt` porte un code par ligne, et ses
tables sortiront sous `data/<case>/`. Le dépôt en contient deux,
`2026-09_test-set` et `2026-09_eclusees-rmc` ; en créer un est un dossier et
un fichier texte.

**Commencez toujours par l'inventaire.** Une requête rapide par station, sans
toucher aux chroniques, qui dit ce que ces codes contiennent réellement :

```bash
python download_hydroportail.py --case 2026-09_test-set --inventory
```

```
10 station(s), dont 8 portant un débit instantané.
  V271201001  L'Ain à Pont-d'Ain                    1981-01-01 à 2026-09-20  16699 j  100 %
  V720001002  Le Rhône à Tarascon - DREAL           1994-12-01 à 2026-09-20  11217 j   97 %
  W107403001  L'Arc à Aiguebelle                    2011-06-02 à 2026-09-14   3264 j   58 %
  W103000301  L'Arc à Saint-Michel-de-Maurienne [La aucun débit instantané
  ...
```

Puis le téléchargement proprement dit :

```bash
# les deux passes, brut et chronique arbitrée par le producteur
python download_hydroportail.py --case 2026-09_test-set

# la chronique arbitrée seule : dix fois plus légère, suffit à beaucoup d'usages
python download_hydroportail.py --case 2026-09_test-set --statuses most_valid

# quelques stations hors de tout cas, pour regarder
python download_hydroportail.py --case bac-a-sable --inventory \
    --stations V720001002 W011001001
```

Comptez environ **trois minutes et 6 Mo par station**, pour les deux passes sur
une chronique de quarante ans.

Un `Makefile` sert de pense-bête pour ce qui se fait souvent : `make` seul liste
ce qu'il sait faire, `make telecharger` lance la campagne détachée du terminal,
`make etat` dit où elle en est, `make suivi` la regarde défiler.

### Suivre un téléchargement

Chaque fenêtre est annoncée quand elle arrive, avec l'avancement dans la station
et une estimation du temps restant :

```
Téléchargement de 8 station(s), passes raw et most_valid.
  [1/8] V720001002  Le Rhône à Tarascon - DREAL      1994-12-01 à 2026-09-20
        raw         1994-12-01 -> 1995-11-30     30 287 pts     2 %
        raw         1995-12-01 -> 1999-03-19    112 635 pts     7 %
        ...
        most_valid  2019-06-22 -> 2026-09-20    114 544 pts   100 %
        2 825 465 lignes, 14.73 Mo, 4 min 51 s
  reste environ 22 min pour 7 station(s)
```

La largeur des fenêtres n'est pas fixe : elle suit la densité observée, si bien
qu'une année dense et seize années éparses coûtent la même requête.
L'avancement est donc mesuré sur la période couverte, pas sur le nombre de
fenêtres.

Une interruption ne fait rien perdre : les réponses déjà reçues sont gardées
dans `.cache/` et ne sont pas redemandées. Relancer la même commande reprend
où elle s'était arrêtée, sans coûter une seule requête pour ce qui est déjà là.
`--quiet` n'affiche que les erreurs.

## À quoi ressemblent les données

```
data/
├── .cache/               cache des reponses recues, partage par tous les cas
├── 2026-09_test-set/
│   ├── measurements/            un fichier parquet par station, la table de faits
│   ├── stations.csv        identite et couverture reelle, une ligne par code
│   ├── coverage.csv      station x annee x statut, de quoi choisir
│   ├── ref_codes.csv       le sens des quatre codes de qualite
│   └── datapackage.json    schema, provenance, empreintes SHA-256
└── 2026-09_eclusees-rmc/
    └── ...
```

**Un cas, un jeu de données, un datapackage.** Le cache, lui, est commun :
une station rapatriée pour une demande ne l'est jamais deux fois. C'est aussi
ce qui rend « j'ai utilisé le jeu `2026-09_eclusees-rmc` en v1.1.0 » exact.

### `measurements/`, la table de faits

**Une ligne par point publié**, et rien d'autre :

```
code_station  date_obs                   debit_m3s  statut  qualification  methode  continuite  most_valid
V720001002    2024-03-01 01:55:00+00:00     2170.0       4             16        8           0       False
V720001002    2024-03-01 01:55:00+00:00     2170.0      16             20       10           0        True
V720001002    2024-03-01 02:00:00+00:00     2170.0       4             16        8           0       False
V720001002    2024-03-01 02:05:00+00:00     2170.0       4             16        8           0       False
```

Les deux premières lignes sont **le même instant en deux versions**, la brute et
la validée. Ce n'est pas un doublon : c'est ce que la source publie, et les deux
valeurs diffèrent souvent. Sur mars 2024 à Tarascon, 196 des 481 horodatages
validés portent une valeur différente de leur version brute.

`most_valid` dit si le point vient de la passe que le producteur arbitre. **Il
ne se déduit pas du statut** : sur les périodes récentes où rien de mieux
n'existe, cette passe rend le point brut lui-même, et la ligne porte alors
`statut = 4` et `most_valid` vrai.

Un fichier par station, `code_station` restant une vraie colonne à l'intérieur :
un fichier se lit et se transmet seul, et le dossier entier s'ouvre d'un coup
comme un jeu unique.

### `stations.csv`

Une ligne par code demandé, **y compris ceux qui ne portent aucun débit**.
L'identité vient de Hub'Eau, la couverture est mesurée :

```
code_station            V720001002       porte_debit             True
libelle_station         Le Rhône à ...   date_debut_instantane   1994-12-01
code_site               V7200010         date_fin_instantane     2026-09-20
stations_soeurs         V720001001;...   jours_avec_donnees      11217
station_debit_du_site                    taux_couverture         0.9656
```

`date_debut_instantane` est souvent **bien postérieure** à l'ouverture de la
station, parce que le référentiel date la station et non l'archivage de sa
chronique fine. L'Isère à Moûtiers est ouverte depuis 1903 et son instantané
commence en 1981 ; le Drac au Pont-de-Claix est ouvert depuis 1904 et le sien
commence en 2019. C'est `date_debut_instantane` qui dit ce qu'on peut
réellement demander.

Quand une station ne porte aucun débit, `station_debit_du_site` indique celle de
son site qui en porte, s'il y en a une. Le cas n'est pas rare et **une liste
fournie par un tiers ne peut pas être prise au mot** : sur le site de l'Arc à
Aiguebelle, la station au nom le plus évident n'a qu'une couverture de 58 %, et
c'est une voisine qui porte la série continue.

### `coverage.csv`

**La table qui sert à décider quoi analyser.** Une ligne par station, année et
statut :

```
code_station  annee  statut  jours  nb_points  intervalle_median_min  intervalle_p90_min
W011001001     1981      16    360       3495                  100.0               302.0
W011001001     2010      16    365      15690                   13.0                77.0
W011001001     2020       4    366      86202                    6.0                 6.0
W011001001     2024       4    366     105087                    5.0                 5.0
W011001001     2024      16    366      62297                    5.0                15.0
```

Se lit ainsi : à Moûtiers, **1981 ne décrit aucune variation infra-horaire**,
avec un point toutes les 100 minutes en médiane et 302 dans le pire décile,
tandis que 2024 la décrit parfaitement, en brut comme en validé.

Les trois indicateurs se lisent ensemble. La médiane seule ment : elle ne dit
rien d'une année dont un tiers manque, ce que `jours` révèle, ni d'une série qui
alterne rafales et silences, ce que le p90 révèle.

Les colonnes `nb_points`, `intervalle_median_min` et `intervalle_p90_min`
restent **vides tant que la chronique n'a pas été téléchargée**. Vide veut dire
« pas encore mesuré », jamais « mesuré à zéro ». Un inventaire seul produit donc
un fichier partiellement rempli, ce qui est l'état vrai des choses et se
transmet tel quel à qui doit choisir ses stations.

### `ref_codes.csv`

Le sens des quatre codes, tiré des nomenclatures Sandre 510, 515, 512 et 923 :

```
type,code,libelle,definition
s,4,Brute,"Donnée non traitée, telle qu'acquise"
q,12,Douteuse,Le producteur signale cette valeur comme suspecte
q,20,Bonne,
m,10,EXP,"Expertisée, issue du jugement d'un hydromètre"
```

## Deux façons de lire, selon ce qu'on a sous la main

`measurements/` est un dossier de fichiers parquet, un par station. Cela se lit de
deux manières, et il est utile de savoir laquelle on veut :

| ce qu'on a | ce qu'on lit | avec quoi |
|---|---|---|
| **un fichier** | une station | la fonction de lecture habituelle |
| **le dossier** | toutes les stations, comme une seule table | la notion de *dataset* d'Arrow |

Un fichier isolé se lit et se transmet seul, sans rien savoir du reste : on peut
en envoyer un par courriel. Le dossier, lui, forme un **dataset** au sens
d'Apache Arrow, c'est à dire un jeu logique composé de plusieurs fichiers qui
partagent le même schéma. Ce n'est pas un bricolage, c'est une notion de la
bibliothèque, disponible en Python comme en R.

L'intérêt n'est pas seulement de tout ouvrir d'un coup. Le format parquet range
dans chaque fichier le minimum et le maximum de chaque colonne ; comme
`code_station` y est constante, filtrer sur elle permet à Arrow d'écarter les
autres fichiers sans les ouvrir. Un filtre sur une station coûte donc
exactement le prix de son fichier.

## Relire les données en Python

```python
import pandas as pd

jeu = "data/2026-09_test-set"

# une station : un fichier, qui se lit seul
serie = pd.read_parquet(f"{jeu}/measurements/W011001001.parquet")

# toutes les stations : le dossier s'ouvre comme une table unique
measurements = pd.read_parquet(f"{jeu}/measurements/")
```

**La chronique propre**, c'est à dire la donnée telle que le producteur
l'arbitre, tient en une ligne :

```python
chronique = measurements[measurements.most_valid]
```

C'est l'objet qui convient à la plupart des usages hydrologiques : homogène par
blocs, validé sur le passé consolidé, brut seulement là où rien de mieux
n'existe encore. Le reste de `measurements` sert à qui a besoin de descendre au
signal brut, et `coverage.csv` dit si on en a besoin.

```python
# le signal brut seul, a 5 minutes sur les annees recentes
brut = measurements[measurements.statut == 4]

# ecarter les points que le producteur signale comme douteux
sur = measurements[measurements.qualification != 12]

# une station, une annee
extrait = measurements[(measurements.code_station == "W011001001")
                  & (measurements.date_obs.dt.year == 2024)]
```

Pour ne pas tout charger en mémoire, `pyarrow.dataset` donne la lecture
paresseuse, qui n'ouvre que les fichiers nécessaires :

```python
import pyarrow.dataset as ds
import pyarrow.compute as pc

table = ds.dataset(f"{jeu}/measurements/", format="parquet")
serie = table.to_table(filter=pc.field("code_station") == "W011001001").to_pandas()
```

## Relire les données en R

**`read_parquet` lit un fichier, `open_dataset` lit un dossier.** C'est la seule
subtilité, et elle vaut d'être connue : appeler `read_parquet` sur le dossier
échoue.

```r
library(arrow)
library(dplyr)

jeu <- "data/2026-09_test-set"

# une station : un fichier
serie <- read_parquet(file.path(jeu, "measurements/W011001001.parquet"))

# toutes les stations : un dataset, qui ne charge rien tant qu'on ne collecte pas
measurements <- open_dataset(file.path(jeu, "measurements/"))
nrow(measurements)

# la chronique propre, arbitree par le producteur
chronique <- measurements |> filter(most_valid) |> collect()

# une seule station : seul son fichier est lu
extrait <- measurements |> filter(code_station == "W011001001") |> collect()

# les codes de station gardent leurs lettres et leurs zeros
couverture <- read.csv(file.path(jeu, "coverage.csv"),
                       colClasses = c(code_station = "character"))
```

## Ce qu'il faut savoir avant d'analyser

**Aucun filtrage de qualité n'est appliqué par défaut, et il n'y en aura pas.**
Le jeu sort complet, avec ses horodatages répétés et ses quatre codes, parce que
l'expertise croisée au besoin est seule à pouvoir trancher ce qui est
utilisable. Ce qui suit dit ce qu'on peut en faire.

### `qualification = 12` veut dire « douteuse »

C'est **le seul drapeau de qualité porté par chaque point**, et il n'est pas
rare : sur septembre 2026 à Tarascon, 2 018 des 5 754 points bruts le portent,
soit 35 %. Une analyse qui les avale sans le savoir travaille sur des valeurs
que le producteur lui-même signale comme suspectes.

### Brut et validé diffèrent en nature, pas seulement en qualité

La série brute est un **échantillonnage régulier**, à 5 minutes sur les années
récentes, mais non corrigé. La série validée est une **courbe à points de
rupture** : ce n'est pas la série brute dont on aurait gardé les bons points,
c'est la courbe que l'hydromètre certifie, stockée par ses inflexions. La lire
sans interpoler entre ses points la sous-échantillonne sans le dire.

Conséquence pour qui étudie les variations rapides : **l'hydromètre a élagué
selon ce qui l'intéressait**, qui n'est pas forcément la variation infra-horaire.
À Tarascon la courbe validée a un pas médian de 70 minutes en mars 2024 ; à
Moûtiers elle a 5 055 points pour 8 906 bruts sur le même mois. Cela se décide
station par station et année par année, d'où `coverage.csv`.

### Mélanger les statuts par période a un sens, par horodatage non

C'est ce que fait le producteur dans la passe `most_valid` : il retient le
meilleur niveau disponible **sur chaque période**, le passé consolidé en validé,
la période intermédiaire en pré-validé, le récent en brut. Sur 21 mois à
Tarascon, 2 seulement mélangent deux statuts.

Prendre au contraire le meilleur statut **de chaque point** produirait à
Tarascon en mars 2024 une série de 8 928 points dont 481 corrigés et 8 447 non
corrigés : ni brute, ni validée, avec des discontinuités là où les deux
alternent. Cet objet n'a pas de signification, et ce dépôt ne le produit pas.

### Descendre d'un cran est légitime

C'est même l'usage principal de `measurements/` : prendre la chronique arbitrée en
général, et le brut sur les périodes où la résolution validée ne suffit pas.
`coverage.csv` est là pour dire où est la frontière.

### Deux limites de la source

Le brut **ne remonte qu'à 2013 ou 2014** sur la plupart des stations, alors que
le validé peut aller jusqu'aux années 1970. Et la résolution varie d'un facteur
vingt au cours de la vie d'une station, sans progresser régulièrement.

Ce ne sont pas des défauts de cette source ni de cet outil : c'est la nature de
la donnée hydrométrique, dont la quantité et la qualité dépendent des moyens et
des priorités des services qui la produisent.

## Utiliser la source avec ménagement

HydroPortail est **un service public gratuit et sans contrepartie**, dont la
capacité est finie et partagée avec tous ses autres usagers. Le logiciel prend
ses précautions, une requête à la fois, compression systématique, temporisation
indexée sur le temps de réponse du serveur et fenêtres dimensionnées pour rester
loin de ce qu'il ne sait pas produire. Elles ne valent que si l'usage suit :

- **lancer les campagnes longues la nuit ou le week-end.** Une extraction de 68
  stations dure environ deux heures et demie ;
- **ne jamais lancer plusieurs exécutions en parallèle** pour aller plus vite :
  cela annule d'un coup toutes les précautions du code ;
- **commencer par `--inventory`**, qui montre ce qui existe sans rien
  télécharger de lourd, puis ne prendre que le nécessaire avec `--statuses` ;
- **garder le cache `.cache/`**, qui évite de redemander ce qui a déjà été
  donné.

Pour se signaler nommément avant une campagne longue, une variable
d'environnement facultative ajoute un contact aux requêtes :

```bash
export HYDROPORTAIL_CONTACT="prenom.nom@exemple.fr"
```

## Vérifier le jeu produit

```bash
python check_hydroportail.py
```

Cinq contrôles, dont le plus important est la non-perte : tout point servi par
HydroPortail doit se retrouver dans `measurements/`, ce qui se vérifie en relisant
les réponses brutes du cache sans repasser par le code qui les a assemblées. Les
autres recoupent les valeurs avec Hub'Eau, vérifient que les nomenclatures n'ont
pas bougé, et que l'intégrité référentielle tient.

## Pour aller plus loin

| fichier | ce qu'il contient |
|---|---|
| [docs/findings.md](docs/findings.md) | ce que HydroPortail, Hub'Eau et le Sandre font réellement, mesuré |
| [docs/references.md](docs/references.md) | ce que la littérature en dit, lu et non mesuré |
| [docs/design.md](docs/design.md) | pourquoi le jeu est construit ainsi |
| [ROADMAP.md](ROADMAP.md) | ce qui reste à faire |
| [CHANGELOG.md](CHANGELOG.md) | ce que chaque version a apporté |
| [CLAUDE.md](CLAUDE.md) | les conventions du dépôt et les pièges à ne pas « corriger » |

`docs/findings.md` est le plus utile à qui veut réutiliser la source ailleurs :
il documente une route publique mais non documentée, ses limites réelles, et les
quatre nomenclatures Sandre qui donnent leur sens aux codes de qualité.

Ce dépôt suit la convention `get-data-<plateforme>-<jeu de données>` et reprend
la structure de ses voisins,
[get-data-hubeau-onde](https://github.com/lou-heraut/get-data-hubeau-onde), les
observations d'écoulement des petits cours d'eau, et
[get-data-vigieau-secheresse](https://github.com/lou-heraut/get-data-vigieau-secheresse),
les arrêtés de restriction d'eau.

## Citer

Voir [CITATION.cff](CITATION.cff). Pensez à citer les données séparément du
logiciel :

> SCHAPI, Banque Hydro, diffusée par HydroPortail, <https://hydro.eaufrance.fr/>

## Licence

Le code est en **GPL-3.0-or-later**.

Les données hydrométriques ne le sont pas : elles sont produites et diffusées
par le SCHAPI et les services de l'État via HydroPortail et Hub'Eau, sous leurs
propres conditions.
