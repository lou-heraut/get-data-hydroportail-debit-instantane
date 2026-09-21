# Ce qui reste à faire

État au 21 septembre 2026 : **aucun code écrit**. La source est instruite, les
choix de conception sont posés, quatre arbitrages attendent une décision.

Les faits sont dans [SOURCE.md](SOURCE.md), les choix déjà tranchés dans
[DESIGN.md](DESIGN.md).

## Les arbitrages en attente

Quatre points où le plan initial est contredit par la mesure, et où la décision
appartient au responsable du projet. Tant qu'ils ne sont pas tranchés, le code
ne doit pas être écrit : chacun change la forme du produit livré.

### A. Garder la chronique propre comme table stockée ?

Le plan initial livre deux dossiers, `mesures/` et `chronique/`. Or
`chronique/` vaut par construction `mesures[most_valid]` : c'est une vue, pas
une table.

**Recommandation : la supprimer**, ne livrer qu'une table de faits, et
documenter le filtre dans le README en Python et en R. Un seul objet, moitié
moins de disque, et plus aucun risque que les deux divergent.

Contre : le confort du non-programmeur. Mais `mesures[mesures.most_valid]` tient
en une ligne dans les deux langages.

### B. Quelle granularité pour la couverture ?

Le plan initial met un `intervalle_median_min` unique par station dans
`stations.csv`. La résolution varie d'un facteur 20 au cours de la vie d'une
station, et pas monotonement.

**Recommandation : une table `couverture.csv` séparée, station x année**, avec
les jours présents, le pas médian et le mélange de statuts. `stations.csv` garde
l'identité et les bornes. C'est la seule forme qui réponde à « cette station,
cette année là, décrit-elle une éclusée ».

### C. Que veut dire « toute la durée des chroniques » ?

La demande supposait une chronique homogène. Il n'y en a pas : du validé épars
depuis 1970, du brut dense depuis 2013.

**Recommandation : tout prendre**, et ne rien trancher dans le script.
`most_valid` est peu coûteux sur les périodes anciennes et le brut est court de
toute façon. Mais il faut dire à la demandeuse que la résolution demandée n'est
pas tenue avant 2013 environ sur la plupart des stations.

### D. Comment nommer les valeurs de `--statuts` ?

Le plan initial propose `--statuts brut | most_valid | les-deux`, ce qui traduit
`raw` mais pas `most_valid`, alors que les deux sont au même titre des noms de
boutons du formulaire d'HydroPortail.

**Recommandation : `--statuts raw | most_valid | les-deux`**, par application de
la règle de nommage que le projet s'est lui-même donnée.

## Les phases

```
phase 1   squelette du depot                  pyproject, LICENSE, CITATION, SPDX, venv
phase 2   couche API isolee                   politesse, fenetrage, falaise 500, reprise
phase 3   referentiel et couverture           stations.csv, couverture.csv, ref_codes.csv
phase 4   telechargement, 2 passes            la table de faits
phase 5   datapackage et empreintes           datapackage.json
phase 6   README, relecture Python et R       la partie qui repond au mail
phase 7   controles                           croise Hub'Eau, inclusion des statuts
---- livraison v1 ----
phase 8   instruction du pas regulier         voir ci-dessous
```

La phase 3 est le premier livrable utile, et elle est possible **avant** tout
téléchargement lourd grâce à la carte `QIXnJ` : une requête par station donne
les bornes, la couverture et le mélange de statuts. C'est ce qui permet de
décider quoi télécharger plutôt que de le découvrir après coup.

Le plan initial demandait à la phase 3 le nombre de points et le pas médian par
passe, qui ne s'obtiennent qu'après téléchargement : cette contradiction est
levée en distinguant ce que la carte donne d'avance (bornes, jours, statuts) de
ce qui se calcule après coup sur la table de faits (pas médian réel).

## Les questions ouvertes

### La liste des 68 stations

En attente de l'équipe demandeuse. Le jeu de test de dix stations, décrit dans
[SOURCE.md](SOURCE.md), permet de tout construire sans elle.

Quand elle arrivera, la première chose à faire est de passer la carte `QIXnJ`
sur les 68 codes : c'est immédiat, et cela dira combien d'entre eux ne portent
aucun débit instantané, combien sont des codes de site, et quelle profondeur
réelle chacun offre. Une liste fournie par un tiers ne peut pas être prise au
mot.

### Le pas de temps régulier, phase 8

**Le point de départ a changé.** Le plan initial comptait sur l'interpolation
côté serveur, `Qln` avec un `step` choisi. La mesure montre qu'elle perd 78 %
des points de rupture de la série validée : elle dégrade la donnée au lieu de la
servir. Cette voie est donc fermée.

**Recommandation : livrer un outil de rééchantillonnage paramétrable plutôt
qu'une grille figée.** C'était déjà une des pistes du plan initial, elle devient
la seule défendable : elle évite de figer un choix scientifique dans un fichier,
et laisse l'analyste assumer le sien.

Ce qu'il reste à instruire, et qui demande un arbitrage scientifique :

1. **La loi d'interpolation.** Linéaire par défaut, mais l'hydrogramme d'éclusée
   a des fronts raides ; une interpolation linéaire sur un pas de deux heures
   arrondit les angles et biaise toute métrique de gradient.
2. **Le seuil au delà duquel on renonce à interpoler**, à confronter à la
   distribution réelle des écarts entre points sur les stations retenues.
3. **Les modalités d'application du seuil** : coupe franche laissant la grille
   vide, ou marquage conservant la valeur avec un indicateur de confiance.
4. **Ce qu'on publie à côté de la valeur.** L'idiome des dépôts voisins veut
   qu'une colonne dérivée s'accompagne d'une colonne qui dit jusqu'où la croire,
   comme `distance_site_hydro_m` chez ONDE. Ici ce serait l'écart en minutes à
   la mesure réelle la plus proche.

`QmnH`, le débit moyen horaire, reste à écarter pour ce sujet : une moyenne
lisse précisément les montées et descentes qui font l'éclusée.

### Le réseau RRSE

Son code n'a pas été identifié dans `code_sandre_reseau_station`, dont les
valeurs sont opaques. À reprendre si le besoin s'en fait sentir.

## Ce qui est tranché et n'est plus une question

- **Pas de compte HydroPortail.** Le gain de poids est illusoire sous gzip.
- **Pas de hauteur d'eau**, seulement le débit. Les stations à hauteur seule
  sont signalées dans `stations.csv` comme sans débit, et c'est tout.
- **Pas de fusion par horodatage** entre niveaux de statut.
- **Pas de filtrage de qualité par défaut**, jamais.
- **Pas d'incrémental en v1**, parce qu'une révision de courbe de tarage réécrit
  le passé.

## Journal

### 21 septembre 2026, instruction de la source

Établi que Hub'Eau ne sert pas l'instantané historique. Trouvé et testé la route
AJAX de HydroPortail. Recoupé les deux services sur un mois, 8 594 valeurs
identiques au litre près. Mesuré le quota, le comportement de `step`, le gain de
gzip, la non-inclusion des statuts, la correction des valeurs par la validation,
la relation site/station sur deux contre-exemples, et la densité de dix stations
de test. Dépôt créé, plan écrit, aucun code.

Arbitrages du même jour : périmètre v1 réduit à la donnée native, le pas
régulier devenant un point de chantier à part ; compte HydroPortail écarté ;
hauteur d'eau écartée.

Revirement sur le format de sortie : la proposition d'une ligne par horodatage
avec colonne compagnon `debit_brut_m3s` est abandonnée après mesure des codes.
Format long retenu.

Second revirement, sur le produit dérivé : mesuré que `most_valid` mélange les
statuts par période et non par horodatage, et que la série validée est une
courbe à points de rupture. La fusion par horodatage envisagée aurait produit un
objet sans signification. La chronique propre est donc téléchargée telle que le
producteur l'arbitre, plus jamais reconstruite. Passes ramenées à `raw` et
`most_valid`.

Le `User-Agent` passe d'une identification nominative à une identification du
logiciel par URL, sans donnée personnelle.

### 21 septembre 2026, seconde instruction après reprise de contexte

Environ 130 requêtes sur HydroPortail, Hub'Eau et Sandre, une à la fois,
gzippées, avec temporisation adaptative. Les mesures portent cette fois sur
l'ensemble du jeu de test et non sur le seul Rhône à Tarascon, ce qui corrige
plusieurs généralisations.

Découvertes qui changent la conception, toutes détaillées dans
[SOURCE.md](SOURCE.md) :

- **la falaise HTTP 500**, qui rend fausse la règle de recul exponentiel et
  impose de couper la fenêtre ;
- **la carte de couverture `QIXnJ`**, qui rend la phase 3 possible avant tout
  téléchargement lourd et lève la contradiction de l'ordre des phases ;
- **les quatre nomenclatures Sandre** 510, 515, 512 et 923, qui ferment la
  question ouverte des codes, avec le piège des nomenclatures homonymes ;
- **`m = 10` veut dire « expertisée »** et non « vrai point », et **`q = 12`
  veut dire « douteuse »**, ce qui en fait le seul drapeau qualité par point ;
- **`s = 8` « Corrigé » existe**, ce qui renforce le choix du format long ;
- **le point porte sept clés**, `md` ayant été manqué ;
- **la profondeur réelle** de l'instantané, 1970 à Fréjus et 1981 à Moûtiers,
  alors que **le brut ne remonte qu'à 2013 ou 2014** ;
- **la résolution varie d'un facteur 20** sur une vie de station et pas
  monotonement, ce qui invalide un pas médian unique par station ;
- **la grille `Qln` perd 78 % des points de rupture**, ce qui ferme la voie de
  l'interpolation côté serveur ;
- **le poids réel sur disque**, 0,92 Mo par station-année en zstd.

Correction d'une erreur du jeu de test : W107403001, l'Arc à Aiguebelle, était
classée « hauteur seule, aucun débit » sur la foi d'une sonde d'une semaine. Elle
porte 3 264 jours de débit instantané, avec une couverture de 58,5 %. Leçon de
méthode retenue : **une sonde ponctuelle ne peut pas établir une absence.**

Le fichier `chantier.md` est éclaté en trois, chacun avec un objectif distinct,
et ce qui n'était pas tranché devient une liste explicite d'arbitrages plutôt
qu'une ambiguïté noyée dans la prose.
