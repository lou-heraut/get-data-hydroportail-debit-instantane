# get-data-hydroportail-debit-instantane

Téléchargement des chroniques de **débit instantané** depuis HydroPortail, et
restructuration en un jeu de tables documenté, utilisable pour la recherche.

> **État : en conception, aucun code à ce jour.** La source a été instruite et
> les choix de conception sont arrêtés. Ce README décrit ce que le dépôt
> contient aujourd'hui, c'est à dire sa documentation ; il deviendra le mode
> d'emploi du logiciel quand celui-ci existera.

## Pourquoi ce dépôt existe

L'API Hub'Eau hydrométrie, qui sert la plupart des besoins en données de débit
français, **ne donne accès à aucune chronique instantanée historique** : son
endpoint temps réel ne remonte qu'à un mois glissant, et son endpoint historique
ne descend pas sous le pas journalier.

La chronique instantanée complète, à quelques minutes de pas, n'existe que sur
[HydroPortail](https://hydro.eaufrance.fr). Ce dépôt la rapatrie proprement,
avec ses codes de qualité, sa couverture réelle mesurée station par station, et
les métadonnées qui permettent de savoir ce qu'on manipule.

Le besoin d'origine est l'analyse des cours d'eau à éclusées, qui demande de
voir la variation infra-horaire du débit, donc précisément ce que le pas
journalier efface.

## Ce que le logiciel livrera

```
donnees_hydroportail/
├── stations.csv       une ligne par code demande, identite et bornes reelles
├── couverture.csv     station x annee x statut : de quoi choisir avant d'analyser
├── ref_codes.csv      le vocabulaire des codes de qualite, engendre depuis le Sandre
├── mesures/           la table de faits, un fichier parquet par station
└── datapackage.json   schema, provenance, empreintes sha256
```

Une seule table de faits, **une ligne par point publié**, avec les quatre codes
de qualité du Sandre conservés tels quels. Aucun filtrage n'est appliqué par
défaut : le logiciel livre de quoi décider, et laisse le chercheur décider.

## Utiliser la source avec ménagement

HydroPortail est **un service public gratuit et sans contrepartie**, dont la
capacité est finie et partagée avec tous ses autres usagers. Le logiciel prend
ses précautions (une requête à la fois, compression, temporisation adaptative,
fenêtres dimensionnées), mais elles ne valent que si l'usage suit :

- **lancer les campagnes longues la nuit ou le week-end.** Une extraction
  complète de 68 stations dure environ deux heures et demie ;
- **ne jamais lancer plusieurs exécutions en parallèle** pour aller plus vite :
  cela annule d'un coup toutes les précautions du code ;
- **commencer par `--inventaire`**, qui montre ce qui existe sans rien
  télécharger de lourd, puis ne prendre que le nécessaire avec `--statuts` ;
- **garder le cache `.sources/`**, qui évite de redemander ce qui a déjà été
  donné.

## Où lire quoi

| fichier | ce qu'il contient |
|---|---|
| [SOURCE.md](SOURCE.md) | ce que HydroPortail, Hub'Eau et le Sandre font réellement, mesuré |
| [DESIGN.md](DESIGN.md) | ce qui est construit, et pourquoi ainsi |
| [ROADMAP.md](ROADMAP.md) | ce qui reste à faire |
| [CLAUDE.md](CLAUDE.md) | les conventions du dépôt et les pièges à ne pas « corriger » |

`SOURCE.md` est le plus utile à qui veut réutiliser la source ailleurs : il
documente une route publique mais non documentée, ses limites réelles, et les
quatre nomenclatures Sandre qui donnent leur sens aux codes de qualité.

## Famille

Ce dépôt suit la convention `get-data-<plateforme>-<jeu de données>` et reprend
la structure de ses voisins :

- [get-data-hubeau-onde](https://github.com/lou-heraut/get-data-hubeau-onde),
  les observations d'écoulement des petits cours d'eau ;
- [get-data-vigieau-secheresse](https://github.com/lou-heraut/get-data-vigieau-secheresse),
  les arrêtés de restriction d'eau.

## Licence

Le code est en **GPL-3.0-or-later**.

Les données hydrométriques ne le sont pas : elles sont produites et diffusées
par le SCHAPI et les services de l'État via HydroPortail et Hub'Eau, sous leurs
propres conditions. Les citer séparément du logiciel.
