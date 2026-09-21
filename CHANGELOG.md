# Journal des versions

Format [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versionnage
[sémantique](https://semver.org/lang/fr/). Le troisième chiffre pour une
correction, le deuxième pour un ajout qui ne casse rien, le premier quand le
format des données livrées change.

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
