# Notes pour Claude Code

## Par où commencer

[README.md](README.md) présente le dépôt en deux minutes. Pour y travailler, il
faut les quatre fichiers ci-dessous, à lire dans cet ordre avant de toucher à
quoi que ce soit. Trois sont dans `docs/`, qui porte ce que l'on sait et
pourquoi on fait ainsi, **on constate, on lit, on décide** ; la racine ne garde
que ce qu'on trouve dans tout dépôt.

| fichier | ce qu'il contient | à quelle question il répond |
|---|---|---|
| [docs/findings.md](docs/findings.md) | ce que nous avons constaté, mesuré sur HydroPortail, Hub'Eau, Sandre et la donnée | qu'est-ce que la source fait réellement ? |
| [docs/design.md](docs/design.md) | les choix de conception et leurs raisons | qu'est-ce qu'on construit, et pourquoi ainsi ? |
| [ROADMAP.md](ROADMAP.md) | phases, questions ouvertes, journal | qu'est-ce qui reste à faire ? |
| [docs/references.md](docs/references.md) | la littérature et les documentations lues, avec leurs passages | qu'ont établi les autres ? |

**La règle de non-répétition est volontaire.** Un fait mesuré vit dans
`docs/findings.md` et nulle part ailleurs ; une décision vit dans
`docs/design.md` et cite le fait sans le recopier. Si tu ajoutes quelque chose, respecte ce partage
plutôt que de tout redire au même endroit.

**Le README et `docs/design.md` ne disent pas la même chose** et ne se
remplacent pas : le README dit comment se servir de l'outil et de ses données,
`docs/design.md` dit pourquoi ils sont faits ainsi. Quand une règle est énoncée
dans le README, sa justification reste dans `docs/design.md` et sa mesure dans
`docs/findings.md`, avec un lien plutôt qu'une redite.

Chaque affirmation chiffrée de ces fichiers, `docs/references.md` excepté, est
une **mesure** faite sur le service réel, pas une estimation ni une lecture de
documentation. `docs/references.md` est justement ce qu'on a lu : une hypothèse
de travail tant que la mesure ne l'a pas confirmée dans `docs/findings.md`. Ne
pas en ajouter sans avoir vérifié, et ne pas en retirer sans avoir mesuré le
contraire. **C'est pourquoi constats et références ne se fusionnent pas** : un
constat se refait et devient faux si le service change, une référence reste
vraie de ce qu'elle décrivait.

## Cycle de vie des fichiers

Cette section est la pratique de développement du dépôt. Elle est écrite pour
être reprise telle quelle dans les dépôts voisins.

### À quoi sert chaque fichier

Une phrase chacun, et c'est ce qui décide où une information doit aller :

| fichier | ce qu'il est |
|---|---|
| `docs/findings.md` | ce que nous avons constaté, mesuré sur le service et sur la donnée |
| `docs/design.md` | ce que nous avons décidé, et pourquoi |
| `ROADMAP.md` | ce que nous n'avons pas encore fait |
| `docs/references.md` | ce que d'autres ont établi, lu et non mesuré |
| `CHANGELOG.md` | ce que nous avons livré, version par version |
| `README.md` | ce dont un utilisateur a besoin pour s'en servir |
| `CLAUDE.md` | comment on travaille ici, et ce qu'il ne faut pas casser |

Si une information ne rentre dans aucun des sept, c'est probablement qu'elle
appartient à un commentaire dans le code ou à un message de commit.

### Les cas, un dossier chacun

**Un cas est une liste de stations et la raison qui la justifie.** Le plus
souvent une demande reçue, parfois un jeu qu'on s'est donné, comme le jeu de
test. Il porte le même nom des deux côtés : `cases/<case>/` dit ce qu'on
veut, `data/<case>/` porte ce qu'on a obtenu. C'est ce qui trace
le chemin de la demande au résultat, et ce qui donne à chaque petit jeu son
datapackage et sa version.

Le nom est `aaaa-mm_sujet`, pour qu'un simple listing soit trié par ordre
d'arrivée. À l'intérieur les noms ne portent pas de date, puisque le dossier la
porte.

| fichier | ce qu'il est |
|---|---|
| `README.md` | le besoin en deux phrases, et ce que contient le dossier |
| `stations.txt` | **le contrat** : un code par ligne, ce que le téléchargement lira |
| `liste-recue.*` | ce que le demandeur a transmis, jamais retouché |
| `resolved-stations.csv` | ce que `prepare_list.py` en tire |
| `arbitrations.csv` | les choix que le script ne peut pas faire seul |

Seuls `README.md` et `stations.txt` sont obligatoires : un cas qu'on se donne
soi-même n'a ni liste reçue, ni traduction, ni arbitrage.

**Ce qui est vrai pour cette demande reste ici ; ce qui est vrai en soi monte
dans `docs/findings.md`.** Qu'un producteur déclare une de ses stations défaillante est
un fait, il vaut pour tout le monde et se mesure une fois. Que l'on préfère pour
autant la chronique longue à la station neuve est une décision propre à une
étude, et elle vit dans son `arbitrations.csv`, avec son motif, parce que la
même situation se trancherait autrement pour une autre question.

**Aucune information personnelle dans ces fichiers**, ni nom, ni adresse, ni
citation de courriel : le dépôt est public, et un besoin s'énonce sans cela.

La colonne `cas` d'`arbitrations.csv` prend une valeur d'un vocabulaire court, qui
dit à qui arrive avec sa propre liste s'il est dans une situation connue. Le
script refuse une valeur hors de cette liste, sans quoi le vocabulaire dériverait
en champ libre :

| valeur | situation |
|---|---|
| `remplacement` | une station en remplace une autre au même point, et les deux publient un temps |
| `deux-exploitants` | deux stations à la même section, chacune sa courbe de tarage, donc des débits différents |
| `qualite-declaree` | le producteur signale lui-même une des stations comme défaillante |

### La roadmap ne s'accumule jamais

Un fichier qui ne fait que grossir est un journal, pas une feuille de route, et
il redevient illisible. **Ce qui est fait en sort.** La roadmap doit rétrécir à
chaque version, pas grandir.

```
en cours de route
  une mesure              ->  docs/findings.md     et nulle part ailleurs
  une reference lue       ->  docs/references.md   avec le passage, et ce qu'on en tire
  une decision prise      ->  docs/design.md       cite la mesure, ne la recopie pas
  un revirement           ->  ROADMAP.md           journal, tant qu'il est frais

a la livraison d'une version
  les phases faites       ->  CHANGELOG.md         sous ## [x.y.z] - date
  le raisonnement stable  ->  docs/design.md       puis l'entree de journal disparait
  ce qui reste            ->  ROADMAP.md           qui ne garde que l'avenir
```

Le journal de `ROADMAP.md` est une **zone d'attente, pas une archive**. Une
entrée qui explique pourquoi on a changé d'avis a sa place tant que c'est frais ;
dès que la décision est stable, son raisonnement appartient à `docs/design.md`
ou au README, et l'entrée se supprime. Les messages de commit gardent la trace fine,
c'est leur rôle, et ils sont écrits pour ça.

### Les versions, et pourquoi on ne se contente pas de dater

Trois gestes au moment de livrer, pas un de plus :

1. La version bouge dans `SCRIPT_VERSION`, qui est la source unique de vérité,
   et de là dans `pyproject.toml` et `CITATION.cff`.
2. `CHANGELOG.md` reçoit une section `## [x.y.z] - aaaa-mm-jj`, en prose, qui
   dit ce que la version apporte. Format
   [Keep a Changelog](https://keepachangelog.com/fr/).
3. `git tag vx.y.z && git push --tags`.

**Dater les fichiers à la place serait plus simple mais ne marcherait pas.** Git
date déjà tout, et le vrai besoin est ailleurs : ces dépôts produisent des jeux
de données citables, avec un `CITATION.cff` et un `datapackage.json` qui portent
un numéro de version. « J'ai utilisé la v1.1.0 » doit désigner quelque chose de
reproductible, ce qu'une date de fichier ne fait pas. Le numéro de version
n'est donc pas de la cérémonie, c'est ce qui rend le jeu de données rattachable
à l'outil qui l'a produit.

La numérotation reste simple et ne mérite aucune discussion : le troisième
chiffre pour une correction, le deuxième pour un ajout qui ne casse rien, le
premier quand le format des données livrées change.

### Ce que Claude fait sans qu'on le lui demande

La rotation est à l'initiative de l'assistant, pas de l'utilisateur. Sans
attendre qu'on le demande :

- proposer la rotation quand une phase de la roadmap est finie, plutôt que de
  laisser la roadmap enfler ;
- signaler quand une entrée de journal a fait son temps et que son raisonnement
  devrait passer dans `docs/design.md` ;
- proposer une version quand ce qui a été livré en mérite une ;
- refuser d'ajouter une information dans le fichier le plus proche si sa place
  est ailleurs, et dire où elle va.

## État

**v2.0.0 livrée le 22 septembre 2026**, taguée et poussée. L'outil télécharge,
inventorie, écrit son datapackage et se contrôle lui-même, et ce qu'il produit
est découpé en cas. Ce que chaque version apporte est dans
[CHANGELOG.md](CHANGELOG.md), ce qui a été fait depuis sous « Non publié ».

Deux cas existent. `2026-09_test-set`, les dix stations qui couvrent les cas
limites, est téléchargé en entier et ses cinq contrôles passent : c'est sur lui
que tourne la procédure de vérification ci-dessous, et sur lui qu'ont été
faites toutes les mesures du rééchantillonnage. `2026-09_eclusees-rmc`, la
demande en cours, a sa liste traduite, ses arbitrages posés et ses 47 stations
inventoriées ; **son téléchargement a été lancé le 23 septembre** et tournait
encore à la fin de la session. S'il n'est pas allé au bout, la même commande le
reprend sans rien redemander, voir [ROADMAP.md](ROADMAP.md).

**Le chantier en cours est le rééchantillonnage**, ce que la demande d'origine
réclamait vraiment : une chronique à pas régulier, quinze minutes visées, une
heure au plus. La session du 23 septembre en a tranché la méthode, avec celui
qui porte la demande, et elle est dans [docs/design.md](docs/design.md),
section « Le rééchantillonnage : ce qui est tranché ». En une phrase : **on
agrège par l'intégrale, sans jamais échantillonner ; les valeurs viennent du
validé ; le brut dit le pas de l'instrument et ce que le validé a perdu.** Le
calcul existe, `hydroportail/aggregate.py`, testé et vérifié contre le `QmnH`
d'HydroPortail, mais il n'est branché sur aucune commande.

### Pour reprendre

Lire, dans cet ordre, la section du rééchantillonnage de
[docs/design.md](docs/design.md), puis celle de [ROADMAP.md](ROADMAP.md), qui
dit ce qui reste dans l'ordre où le faire : la table de support, le choix du
pas, le produit, la notice. Les constats qui fondent la méthode sont dans
[docs/findings.md](docs/findings.md), de « `QmnH` est l'intégrale de la
courbe » à « Agrégé, le validé garde les pics », et de « Le pas du brut change »
à « Ce que chaque pas de sortie garde du brut » ; la littérature dans
[docs/references.md](docs/references.md).

**Ne pas rouvrir sans fait nouveau** ce que `design.md` tranche : agréger et non
échantillonner, les valeurs du validé et jamais du brut là où le validé existe,
la carte `QIXnJ` pour les trous du validé. Chacun de ces choix a été discuté,
mesuré et confronté à la littérature. Ce qui reste ouvert l'est explicitement
dans la roadmap, et la plupart de ces questions sont scientifiques avant d'être
techniques : les poser, avec les options et une recommandation, plutôt que de
les trancher seul.

**Les équipes qui reçoivent les données ne sont pas hydrologues.** Elles
n'arbitrent pas la méthode ; on leur livre des produits définis, documentés et
vérifiés, avec de quoi justifier les choix, et le format est le parquet.

### Les scripts d'exploration

`explore/` est hors de l'outil. Ses dépendances sont une option du paquet,
`pip install -e ".[explore]"`, et tout s'y lance depuis la racine du dépôt,
sur le cas nommé par `CASE` dans `explore/common.py`. Chaque script refait une
mesure de `docs/findings.md`, qui le cite :

| script | ce qu'il fait | requêtes |
|---|---|---|
| `raw_support.py` | part des pas de chaque année portés par le brut, à 15, 30 et 60 min | aucune |
| `compare_valid_raw.py` | ce que le validé garde du brut, agrégés sur les mêmes pas | aucune |
| `validated_gaps.py` | trous et segments certifiés du validé, code `c` contre carte `QIXnJ` | aucune |
| `probe_qmnh.py` | `QmnH` d'HydroPortail contre notre agrégation au pas horaire | une |
| `plot_days.py` | quelques journées à 15 et 60 min, en PNG et PDF | aucune |
| `plot_year.py` | une station et une année à parcourir dans le navigateur | aucune |

Les figures s'écrivent dans `data/_exploration/`, ignoré par git.

## Contexte

Dépôt d'une famille : convention de nommage `get-data-<plateforme>-<jeu de
données>`. Les voisins dans le dossier parent, `get-data-hubeau-onde` et
`get-data-vigieau-secheresse`, sont les modèles dont ce dépôt reprend la
structure, le `datapackage.json` et le ton du README. Autre voisin :
`safran-fairy`.

Particularité par rapport aux deux autres : **la source n'est pas une API
contractuelle** mais le canal interne d'une page web, publique et sans
authentification. Elle peut changer sans préavis, d'où son isolement dans
`hydroportail/api.py`.

## Interaction

Ne pas utiliser le widget de questions à choix multiples (outil
`AskUserQuestion`, les options cliquables). Les arbitrages se posent en texte
dans la réponse : les options, celle qui est recommandée, ce qui les distingue,
puis la réponse arrive en prose. Le reproche ne porte pas sur la mise en forme
mais sur le format d'échange : réponses figées alors qu'aucune n'est forcément
la bonne, et impossibilité de tout avoir sous les yeux. Les tableaux, schémas et
maquettes ASCII qui accompagnaient ces options sont au contraire bienvenus,
directement dans le texte.

## Conventions

### Quelle langue, où

*Cette section est écrite pour être reprise telle quelle dans les dépôts
voisins.*

**Le français est la langue de la documentation, et de ce dont le sujet est
français par nature.** Tout le reste est de la structure, et la structure est en
anglais.

| en anglais | en français |
|---|---|
| noms de fonctions, de variables, de modules | messages affichés, aide des commandes |
| noms de fichiers et de dossiers | README, ROADMAP, CHANGELOG, tout `docs/` |
| cibles de Makefile, options de ligne de commande | messages de commit, `AUTHORS.md` |
| | noms de colonnes, hérités d'une source française |

Ce qu'on tape est une instruction à une machine, et l'anglais est la langue des
machines. Ce qu'on lit est de la prose adressée à quelqu'un, et ceux à qui elle
s'adresse lisent le français.

**La donnée est le cas particulier, et il se déduit de la même règle.** Les noms
de colonnes viennent d'un service français, pour des hydrologues français :
`code_station` et `date_obs` sont les noms de Hub'Eau, pas une traduction que
nous aurions faite. Ils ne se traduisent donc jamais, pas plus que les valeurs
anglaises d'HydroPortail, `raw` et `most_valid`, qui se recopient telles quelles.
La règle est la traçabilité, pas une préférence de langue. Le détail est dans la
section « Conventions d'écriture » de [docs/design.md](docs/design.md).

Le README, les commits et `AUTHORS.md` s'écrivent en prose, pas en listes à
puces télégraphiques.

### Renommer sans casser

*Écrit après avoir cassé trois fois le même jour. Également transposable.*

Un renommage d'identifiants à coups de `sed` abîme la prose et laisse des
références orphelines : le mot `mesures` est un nom de table dans le code et un
mot français dans un commentaire, et rien ne les distingue pour une expression
régulière. **Le repérage passe donc par le lexer**, `tokenize` de la
bibliothèque standard, qui sait ce qui est un identifiant et ce qui est une
chaîne ou un commentaire. Trois précautions valent d'être redites :

- **un nom précédé d'un point ne se renomme pas.** `row.code_station` est un nom
  de colonne venu de la source, pas une variable à nous ;
- **un renommage qui ferait entrer en collision deux noms distincts du même
  fichier se refuse**, plutôt que de fusionner silencieusement deux variables.
  L'outil les signale et on choisit un autre nom ;
- **les lignes de continuation se réalignent après coup.** Un nom plus court
  décale tout ce qui était aligné sur une parenthèse ouvrante, et le compilateur
  n'en dit rien.

**Les tests unitaires ne suffisent pas à valider un renommage** : ils ne portent
ici que sur les fonctions pures, et le premier renommage incomplet a laissé
passer un `NameError` dans la fonction de téléchargement. Le contrôle minimal
est de rejouer une station entièrement en cache, qui exerce tout le chemin
d'écriture sans coûter une requête :

```bash
python download_hydroportail.py --case _smoke --stations W107403003 --root data
python -c "from frictionless import Package; \
    print(Package('data/_smoke/datapackage.json').validate().valid)"
rm -rf data/_smoke
```

### Rédaction

- **Aucun tiret cadratin** (`—`) ni demi-cadratin (`–`) dans les textes. Il n'y
  en a pas une seule occurrence dans le dépôt, c'est délibéré : deux-points,
  virgule, parenthèses ou point font le travail.
- Typographie française : guillemets `«  »`, espace avant `: ; ! ?`, nombres
  groupés par milliers avec une espace (`105 209`), virgule décimale (`0,92 Mo`).
- Pas de superlatifs ni de formules d'annonce.
- En-tête SPDX en tête de chaque fichier Python :
  `# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>` puis
  `# SPDX-License-Identifier: GPL-3.0-or-later`.
- Version unique de vérité : `SCRIPT_VERSION` dans `hydroportail/schema.py`,
  réexportée par `hydroportail/__init__.py`. La faire bouger implique
  `pyproject.toml` et `CITATION.cff`.

## Environnement

Debian/Ubuntu bloque `pip install` en système (PEP 668). Le venv du projet sera
`.python_env/`, à activer avant toute commande :

```bash
source .python_env/bin/activate
```

`data/` est ignoré par git : les données se régénèrent. Un
sous-dossier par cas y porte les tables, et `data/.cache/` le
cache des réponses reçues, commun à tous les cas et supprimable au prix d'un
retéléchargement.

Les scripts d'`explore/` ont leur propre option de dépendances, voir « Les
scripts d'exploration » plus haut.

## Pièges à ne pas « corriger »

Ces valeurs et comportements sont mesurés sur le service réel. Les changer casse
le téléchargement en silence, ou fait tomber HydroPortail. Le détail et les
chiffres sont dans [docs/findings.md](docs/findings.md).

- **Un HTTP 500 veut dire « fenêtre trop large », pas « serveur en panne ».** Y
  répondre par un recul exponentiel et plusieurs tentatives ferait replanter le
  service autant de fois. La bonne réaction est de **couper la fenêtre en
  deux**. Le recul exponentiel reste correct pour 429 et 503.
- **Sauf en famille journalière, où un 500 veut dire « je ne sais pas servir
  cette station ».** La largeur ne peut pas être en cause, toute la vie d'une
  station y tenant en 46 000 points : découper coûte quinze requêtes pour
  aboutir au même échec. Le code lève `UnservedStation`, et l'appelant note la
  station et passe à la suivante plutôt que d'arrêter la campagne.
- **`step` ne veut pas dire la même chose selon la famille de grandeur.** En
  instantané c'est un bouton de quota qui ne change rien à ce qui revient. En
  journalier c'est le « n » du nom : `QIXnJ` avec `step=20` rend les maxima sur
  vingt jours, soit un vingtième des lignes, **sans que rien ne le signale**.
  Hors famille instantanée, `step` reste à 1. L'erreur a déjà été commise et
  n'a été vue que grâce à une valeur de référence. **`QmnH` fait exception
  dans la famille instantanée** : son `step` est aussi le « n », et
  `_step_for` le traiterait à tort comme un quota.
- **`step` est borné à 1..30**, ce qui plafonne une fenêtre à 10 416 jours.
- **Ne jamais déduire la fenêtre du quota.** L'ordre est : estimer les points
  attendus, en déduire la fenêtre en visant environ 100 000 points, puis mettre
  `step` au minimum qui fasse accepter cette fenêtre. Pris à l'envers, le quota
  laisse passer 19 ans de brut que le serveur ne sait pas produire. `step` est
  un bouton de quota, la protection est l'estimation.
- **gzip est obligatoire**, facteur 55 sur la bande passante.
- **Une requête à la fois, jamais de parallélisme.**
- **L'unité des valeurs est `series.unit`, pas `unitQ`.** `unitQ` vaut `m3`
  alors que les données sont en litres par seconde. Les confondre donne un
  facteur 1 000.
- **Les codes `s`, `q`, `m`, `c` sont les nomenclatures Sandre 510, 515, 512 et
  923**, et surtout pas celles dont le titre correspond le mieux (507, 508, 72),
  qui ne contiennent pas les bonnes valeurs. Apparier sur les codes, vérifier
  contre les libellés de Hub'Eau.
- **`m = 10` veut dire « expertisée »**, pas « vrai point de mesure ».
  **`q = 12` veut dire « douteuse »**, et c'est fréquent.
- **Interroger les stations, jamais les sites.** Le site rend la série de sa
  station de référence sans dire laquelle.
- **Une sonde ponctuelle ne peut pas établir qu'une station n'a pas de débit.**
  Utiliser la carte de couverture `QIXnJ`. L'erreur a déjà été commise une fois
  sur W107403001.
- **Le code `c` ne dit pas de façon fiable si un écart est un trou.** Certains
  producteurs le marquent, d'autres jamais. Pour les trous du validé, lire la
  carte `QIXnJ` : un long écart y est entièrement présent, segment certifié, ou
  entièrement absent, trou.
- **Un long écart dans la série validée n'est pas un manque.** C'est un segment
  que le producteur certifie à sa tolérance d'élagage près. Le critère d'écart
  entre points, juste pour le brut, ne décide pas seul sur le validé.
- **Le pas du brut n'est pas cinq minutes partout.** Il se resserre par paliers,
  de soixante à cinq minutes entre 2013 et 2022 sur certaines stations, et reste
  à quinze sur d'autres. Le lire dans `coverage.csv`, ne jamais le supposer.
- **Le brut n'est jamais une source de valeurs là où le validé existe.** Il est
  provisoire, et certains de ses artefacts ne sont pas marqués douteux : un
  point isolé à 298 m³/s entre deux valeurs à 16,3 devient une fausse éclusée.
- **Dédoublonner sur la ligne entière**, pas sur `(code_station, date_obs,
  statut)` : deux niveaux portent toujours deux `statut` différents, mais pas
  toujours deux `qualification` différentes.

## Vérifications après modification

Dans cet ordre, du plus rapide au plus long :

```bash
source .python_env/bin/activate
pytest                                          # les fonctions pures, instantane
python download_hydroportail.py --case 2026-09_test-set --inventory
```

Le `Makefile` abrège ce qui se répète, `make tests`, `make controler`,
`make etat` ; il tient lieu de pense-bête et `make` seul le déroule.

Les dix codes ne sont pas recopiés ici : ils sont dans
`cases/2026-09_test-set/stations.txt`, et ce que chacun illustre dans
[docs/findings.md](docs/findings.md).

Attendu sur ces dix stations, et **en croissance d'un jour par jour** pour
celles qui sont en service :

```
W011001001  16684 j  1981-01-01 a 2026-09-20  100 %
W283201001   2510 j  2019-11-01 a 2026-09-20  100 %
V271201001  16699 j  1981-01-01 a 2026-09-20  100 %
V720001002  11217 j  1994-12-01 a 2026-09-20   97 %
X031001001   5691 j  2010-04-03 a 2026-09-20   95 %
Y532501001  19460 j  1970-12-24 a 2026-04-12   96 %   fermee, ne bouge plus
W107403003   1886 j  2021-07-16 a 2026-09-20  100 %
W107403001   3264 j  2011-06-02 a 2026-09-14   58 %   couverture trouee
W103000301      0    aucun debit instantane
V031661301      0    aucun debit instantane
coverage.csv : 240 lignes, statuts {4: 14, 8: 8, 12: 29, 16: 189}
```

Et après téléchargement des deux passes sur ces mêmes dix stations, environ
25 minutes et 1,6 Go de mémoire au pic :

```
8 fichiers parquet, 8 447 816 lignes, 47 Mo, environ 5,5 octets par ligne
V720001002 : 2 825 465 lignes dont 111 286 pour la seule annee 2024
coverage.csv : 343 lignes, statuts {4: 113, 8: 10, 12: 29, 16: 191}
```

Puis les contrôles, qui doivent tous passer :

```bash
python check_hydroportail.py --case 2026-09_test-set
python -c "from frictionless import Package; print(Package('data/2026-09_test-set/datapackage.json').validate().valid)"
```

```
non-perte          8 447 816 points servis, tous presents
recoupement        ecart maximal 0,000000 m3/s avec Hub'Eau
inclusion          pre_validated_and_validated contenue dans most_valid
codes              tous decrits par ref_codes.csv
integrite          aucune ligne de couverture orpheline
```

**Un écart n'est jamais anodin.** C'est cette table qui a révélé que `step`
changeait de sens d'une famille de grandeurs à l'autre : le code rendait 728
jours au lieu de 16 684 sans lever la moindre erreur. Un écart signale soit une
régression, soit une évolution du service, et les deux méritent d'être compris
avant d'être acceptés.

## Licence

Le code est en GPL-3.0-or-later ; **les données hydrométriques ne le sont pas**
(données publiques diffusées par HydroPortail et Hub'Eau, SCHAPI et OFB). Ne pas
laisser un texte suggérer le contraire.
