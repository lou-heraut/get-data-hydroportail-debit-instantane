# Notes pour Claude Code

## Par où commencer

Trois fichiers, trois objectifs distincts. Les lire dans cet ordre avant de
toucher à quoi que ce soit :

| fichier | ce qu'il contient | à quelle question il répond |
|---|---|---|
| [SOURCE.md](SOURCE.md) | les faits mesurés sur HydroPortail, Hub'Eau et Sandre | qu'est-ce que la source fait réellement ? |
| [DESIGN.md](DESIGN.md) | les choix de conception et leurs raisons | qu'est-ce qu'on construit, et pourquoi ainsi ? |
| [ROADMAP.md](ROADMAP.md) | phases, arbitrages en attente, journal | qu'est-ce qui reste à faire et à trancher ? |

**La règle de non-répétition est volontaire.** Un fait mesuré vit dans
`SOURCE.md` et nulle part ailleurs ; une décision vit dans `DESIGN.md` et cite
le fait sans le recopier. Si tu ajoutes quelque chose, respecte ce partage
plutôt que de tout redire au même endroit. Le `README.md` viendra en phase 6 et
s'adressera aux utilisateurs, pas aux développeurs.

Chaque affirmation chiffrée de ces fichiers est une **mesure** faite sur le
service réel, pas une estimation ni une lecture de documentation. Ne pas en
ajouter sans avoir vérifié, et ne pas en retirer sans avoir mesuré le contraire.

## État

**Aucun code au 21 septembre 2026.** Quatre arbitrages attendent une décision
avant que la première ligne soit écrite, parce que chacun change la forme du
produit livré : voir la section « Les arbitrages en attente » de
[ROADMAP.md](ROADMAP.md). Ne pas les trancher à la place du responsable du
projet.

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
- **Ne pas augmenter `step` pour élargir une fenêtre.** `step` ne
  sous-échantillonne rien, il ne sert qu'au compteur de quota : un grand pas
  fait donc accepter une requête que le serveur ne sait pas produire. Viser
  environ 100 000 points par réponse.
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

À compléter quand le code existera. La forme attendue, reprise des voisins :

```bash
python download_hydroportail.py --inventaire    # la carte QIXnJ, quelques requetes
python download_hydroportail.py --stations <jeu de test>
python -c "from frictionless import Package; print(Package('donnees_hydroportail/datapackage.json').validate().valid)"
```

Le jeu de test de dix stations et les volumes attendus station par station sont
dans [SOURCE.md](SOURCE.md). Ils servent de valeurs de référence : un écart
important signale soit une régression, soit une évolution du service, et les
deux méritent d'être compris avant d'être acceptés.

## Licence

Le code est en GPL-3.0-or-later ; **les données hydrométriques ne le sont pas**
(données publiques diffusées par HydroPortail et Hub'Eau, SCHAPI et OFB). Ne pas
laisser un texte suggérer le contraire.
