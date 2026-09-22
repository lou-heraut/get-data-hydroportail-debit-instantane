# Notes pour Claude Code

## Par où commencer

[README.md](README.md) présente le dépôt en deux minutes. Pour y travailler, il
faut les trois fichiers ci-dessous, à lire dans cet ordre avant de toucher à
quoi que ce soit :

| fichier | ce qu'il contient | à quelle question il répond |
|---|---|---|
| [SOURCE.md](SOURCE.md) | les faits mesurés sur HydroPortail, Hub'Eau et Sandre | qu'est-ce que la source fait réellement ? |
| [DESIGN.md](DESIGN.md) | les choix de conception et leurs raisons | qu'est-ce qu'on construit, et pourquoi ainsi ? |
| [ROADMAP.md](ROADMAP.md) | phases, questions ouvertes, journal | qu'est-ce qui reste à faire ? |

**La règle de non-répétition est volontaire.** Un fait mesuré vit dans
`SOURCE.md` et nulle part ailleurs ; une décision vit dans `DESIGN.md` et cite
le fait sans le recopier. Si tu ajoutes quelque chose, respecte ce partage
plutôt que de tout redire au même endroit.

**Le README et `DESIGN.md` ne disent pas la même chose** et ne se remplacent
pas : le README dit comment se servir de l'outil et de ses données, `DESIGN.md`
dit pourquoi ils sont faits ainsi. Quand une règle est énoncée dans le README,
sa justification reste dans `DESIGN.md` et sa mesure dans `SOURCE.md`, avec un
lien plutôt qu'une redite.

Chaque affirmation chiffrée de ces fichiers est une **mesure** faite sur le
service réel, pas une estimation ni une lecture de documentation. Ne pas en
ajouter sans avoir vérifié, et ne pas en retirer sans avoir mesuré le contraire.

## Cycle de vie des fichiers

Cette section est la pratique de développement du dépôt. Elle est écrite pour
être reprise telle quelle dans les dépôts voisins.

### À quoi sert chaque fichier

Une phrase chacun, et c'est ce qui décide où une information doit aller :

| fichier | ce qu'il est |
|---|---|
| `SOURCE.md` | ce qui est vrai indépendamment de nous, mesuré sur le service |
| `DESIGN.md` | ce que nous avons décidé, et pourquoi |
| `ROADMAP.md` | ce que nous n'avons pas encore fait |
| `CHANGELOG.md` | ce que nous avons livré, version par version |
| `README.md` | ce dont un utilisateur a besoin pour s'en servir |
| `CLAUDE.md` | comment on travaille ici, et ce qu'il ne faut pas casser |

Si une information ne rentre dans aucun des six, c'est probablement qu'elle
appartient à un commentaire dans le code ou à un message de commit.

### Les demandes, un dossier par cas

`ressources/` garde la trace des demandes reçues : un sous-dossier par cas,
nommé `aaaa-mm_sujet` pour qu'un simple listing soit trié par ordre d'arrivée. À
l'intérieur les noms ne portent pas de date, puisque le dossier la porte.

| fichier | ce qu'il est |
|---|---|
| `README.md` | le besoin en deux phrases, et ce que contient le dossier |
| `liste-recue.*` | ce que le demandeur a transmis, jamais retouché |
| `stations-demandees.csv` | ce que `preparer_liste.py` en tire |
| `arbitrages.csv` | les choix que le script ne peut pas faire seul |

**Ce qui est vrai pour cette demande reste ici ; ce qui est vrai en soi monte
dans `SOURCE.md`.** Qu'un producteur déclare une de ses stations défaillante est
un fait, il vaut pour tout le monde et se mesure une fois. Que l'on préfère pour
autant la chronique longue à la station neuve est une décision propre à une
étude, et elle vit dans son `arbitrages.csv`, avec son motif, parce que la
même situation se trancherait autrement pour une autre question.

**Aucune information personnelle dans ces fichiers**, ni nom, ni adresse, ni
citation de courriel : le dépôt est public, et un besoin s'énonce sans cela.

La colonne `cas` d'`arbitrages.csv` prend une valeur d'un vocabulaire court, qui
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
  une mesure              ->  SOURCE.md       et nulle part ailleurs
  une decision prise      ->  DESIGN.md       cite la mesure, ne la recopie pas
  un revirement           ->  ROADMAP.md      journal, tant qu'il est frais

a la livraison d'une version
  les phases faites       ->  CHANGELOG.md    sous ## [x.y.z] - date
  le raisonnement stable  ->  DESIGN.md       puis l'entree de journal disparait
  ce qui reste            ->  ROADMAP.md      qui ne garde que l'avenir
```

Le journal de `ROADMAP.md` est une **zone d'attente, pas une archive**. Une
entrée qui explique pourquoi on a changé d'avis a sa place tant que c'est frais ;
dès que la décision est stable, son raisonnement appartient à `DESIGN.md` ou au
README, et l'entrée se supprime. Les messages de commit gardent la trace fine,
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
  devrait passer dans `DESIGN.md` ;
- proposer une version quand ce qui a été livré en mérite une ;
- refuser d'ajouter une information dans le fichier le plus proche si sa place
  est ailleurs, et dire où elle va.

## État

**v1.0.0 livrée le 21 septembre 2026**, taguée et poussée. L'outil télécharge,
inventorie, écrit son datapackage et se contrôle lui-même ; le jeu de test de
dix stations a été passé en entier et les cinq contrôles passent. Ce que cette
version contient est dans [CHANGELOG.md](CHANGELOG.md).

Ce n'est donc pas un chantier en cours : les modifications sont a priori des
corrections ciblées, et la liste de ce qui est arrêté et ne se rediscute pas est
en fin de [ROADMAP.md](ROADMAP.md).

La liste des stations est arrivée le 22 septembre 2026, avec la précision du pas
de temps attendu. Ses 51 codes, dont 45 codes de site, sont normalisés et
traduits en codes de station par `preparer_liste.py`, dans le dossier de demande
`ressources/2026-09_eclusees-rmc/`. Le chantier courant est de trancher les
lignes que ce fichier signale, puis d'inventorier. Restent ouverts, et **pas à
trancher seul**, les arbitrages de l'outil de rééchantillonnage, qui est ce que
la demande d'origine réclamait vraiment. Tout est décrit dans
[ROADMAP.md](ROADMAP.md).

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

- **Code et commentaires en anglais, messages affichés en français.** Les noms
  de colonnes ne sont jamais traduits depuis leur source, y compris les noms de
  paramètres anglais d'HydroPortail comme `raw` et `most_valid` : la règle est
  la traçabilité, pas une préférence de langue. Le détail est dans la section
  « Conventions d'écriture » de [DESIGN.md](DESIGN.md).
- README, commits, `AUTHORS.md` en français, en prose, pas en listes à puces
  télégraphiques.

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

`donnees_hydroportail/` sera ignoré par git : les données se régénèrent. Le
sous-dossier `donnees_hydroportail/.sources/` est le cache des réponses reçues,
supprimable au prix d'un retéléchargement.

## Pièges à ne pas « corriger »

Ces valeurs et comportements sont mesurés sur le service réel. Les changer casse
le téléchargement en silence, ou fait tomber HydroPortail. Le détail et les
chiffres sont dans [SOURCE.md](SOURCE.md).

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
  n'a été vue que grâce à une valeur de référence.
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
- **Dédoublonner sur la ligne entière**, pas sur `(code_station, date_obs,
  statut)` : deux niveaux portent toujours deux `statut` différents, mais pas
  toujours deux `qualification` différentes.

## Vérifications après modification

Dans cet ordre, du plus rapide au plus long :

```bash
source .python_env/bin/activate
pytest                                          # les fonctions pures, instantane
python download_hydroportail.py --inventaire --stations \
  W011001001 W283201001 V271201001 V720001002 X031001001 \
  Y532501001 W107403003 W107403001 W103000301 V031661301
```

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
couverture.csv : 240 lignes, statuts {4: 14, 8: 8, 12: 29, 16: 189}
```

Et après téléchargement des deux passes sur ces mêmes dix stations, environ
25 minutes et 1,6 Go de mémoire au pic :

```
8 fichiers parquet, 8 447 816 lignes, 47 Mo, environ 5,5 octets par ligne
V720001002 : 2 825 465 lignes dont 111 286 pour la seule annee 2024
couverture.csv : 343 lignes, statuts {4: 113, 8: 10, 12: 29, 16: 191}
```

Puis les contrôles, qui doivent tous passer :

```bash
python verifier_hydroportail.py
python -c "from frictionless import Package; print(Package('donnees_hydroportail/datapackage.json').validate().valid)"
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
