# Ce qui reste à faire

État au 21 septembre 2026 : **les phases 1 à 3 sont faites**, chacune vérifiée
contre les mesures de [SOURCE.md](SOURCE.md). L'inventaire tourne et rend la
table de couverture des dix stations de test à l'identique.

Les faits sont dans [SOURCE.md](SOURCE.md), les choix dans
[DESIGN.md](DESIGN.md). Ce fichier ne garde que l'avenir : ce qui est fait en
sort, voir la section « Cycle de vie des fichiers » de [CLAUDE.md](CLAUDE.md).

## Les phases

Cette liste est le plan de la v1. Elle graduera d'un bloc vers le
`CHANGELOG.md` au moment de la livraison ; d'ici là les phases faites restent
visibles pour que l'avancement se lise d'un coup d'oeil.

```
phase 1   squelette du depot           FAIT   pyproject, LICENSE, CITATION, venv, ref_codes
phase 2   couche API isolee            FAIT   politesse, fenetrage, falaise 500, cache
phase 3   referentiel et couverture    FAIT   stations.csv, couverture.csv, ref_codes.csv
phase 4   telechargement, 2 passes            la table de faits
phase 5   datapackage et empreintes           datapackage.json
phase 6   README, relecture Python et R       DESIGN.md y est replie
phase 7   controles                           croise Hub'Eau, inclusion des statuts
---- livraison v1 ----
phase 8   outil de reechantillonnage          voir ci-dessous
```

Chaque phase se termine sur une **preuve chiffrée**, prise dans les mesures de
[SOURCE.md](SOURCE.md) :

| # | preuve |
|---|---|
| 1 | `pip install -e .` passe, la table des codes rend ses 25 lignes |
| 2 | Tarascon 2024 en `raw` rend **105 209 points**, et une fenêtre de 8 ans est coupée au lieu de planter |
| 3 | les 10 stations de test rendent **la table de couverture de `SOURCE.md` à l'identique** |
| 4 | Tarascon 2024 rend **111 286 lignes** et **0,92 Mo en zstd** |
| 5 | `frictionless` valide le datapackage |
| 6 | les exemples de relecture Python et R tournent vraiment |
| 7 | recoupement Hub'Eau au litre près, inclusion des statuts vérifiée |

La phase 3 est le premier livrable utile, et elle est possible **avant** tout
téléchargement lourd grâce à la carte `QIXnJ` : une requête par station donne
les bornes, la couverture et le mélange de statuts. C'est ce qui permet de
décider quoi télécharger plutôt que de le découvrir après coup.

Le plan initial demandait à la phase 3 le nombre de points et le pas médian par
passe, qui ne s'obtiennent qu'après téléchargement : la contradiction est levée
en distinguant ce que la carte donne d'avance (bornes, jours, statuts) de ce qui
se calcule après coup sur la table de faits (pas médian et p90 réels).

## Les questions ouvertes

### La liste des 68 stations

En attente de l'équipe demandeuse. Le jeu de test de dix stations, décrit dans
[SOURCE.md](SOURCE.md), permet de tout construire sans elle.

Quand elle arrivera, la première chose à faire est de passer `--inventaire` sur
les 68 codes : c'est immédiat, et cela dira combien d'entre eux ne portent aucun
débit instantané, combien sont des codes de site, et quelle profondeur réelle
chacun offre. Une liste fournie par un tiers ne peut pas être prise au mot.

### L'outil de rééchantillonnage, phase 8

**Après la v1, pas pendant.** On se concentre d'abord sur la donnée native, qui
est le socle dont toute grille se déduit.

Le point de départ a changé depuis le plan initial. Celui-ci comptait sur
l'interpolation côté serveur, `Qln` avec un `step` choisi ; la mesure montre
qu'elle perd 78 % des points de rupture de la série validée, donc qu'elle
dégrade la donnée au lieu de la servir. Cette voie est fermée.

**Ce sera donc un outil de rééchantillonnage paramétrable, pas une grille
figée**, ce qui évite de figer un choix scientifique dans un fichier et laisse
l'analyste assumer le sien.

Ce qu'il reste à instruire, et qui demande un arbitrage scientifique :

1. **La loi d'interpolation.** Linéaire par défaut, mais l'hydrogramme d'éclusée
   a des fronts raides ; une interpolation linéaire sur un pas de deux heures
   arrondit les angles et biaise toute métrique de gradient.
2. **Le seuil au delà duquel on renonce à interpoler**, à confronter à la
   distribution réelle des écarts entre points sur les stations retenues, que
   `couverture.csv` donnera.
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

### Le signal de révision des courbes de tarage

Pour une éventuelle v2 incrémentale : le JSON porte un champ `correctionCurves`,
vide sur tous les essais. S'il expose un jour les courbes et leurs dates, il
donne le signal qui manque.

## Ce qui est tranché, et qu'on ne rouvre pas

Le raisonnement de chacun est dans [DESIGN.md](DESIGN.md). Cette liste n'est là
que pour éviter de les rediscuter par oubli.

- **Une seule table de faits**, pas de `chronique/` : c'est une vue, et le
  README porte les deux lignes qui la produisent.
- **Une table de couverture station x année x statut**, parce qu'un pas médian
  unique par station dit le contraire de la vérité aux deux bouts.
- **On prend tout.** La variabilité de quantité et de qualité est le principe de
  la donnée hydrométrique, pas un défaut à corriger ni une limite à excuser.
- **`--statuts raw`**, pas `brut` : un nom de paramètre de la source se recopie.
- **Pas de compte HydroPortail**, le gain est illusoire sous gzip.
- **Pas de hauteur d'eau**, seulement le débit.
- **Pas de fusion par horodatage** entre niveaux de statut.
- **Pas de filtrage de qualité par défaut**, jamais.
- **Pas d'incrémental en v1**, parce qu'une révision de courbe de tarage réécrit
  le passé.

## Journal

Le journal explique les revirements tant qu'ils sont frais. Une fois qu'une
décision est stable, son raisonnement vit dans [DESIGN.md](DESIGN.md) et
l'entrée correspondante peut disparaître d'ici.

### 21 septembre 2026, instruction de la source

Établi que Hub'Eau ne sert pas l'instantané historique. Trouvé et testé la route
AJAX de HydroPortail. Recoupé les deux services sur un mois, 8 594 valeurs
identiques au litre près. Mesuré le quota, le comportement de `step`, le gain de
gzip, la non-inclusion des statuts, la correction des valeurs par la validation,
la relation site/station sur deux contre-exemples, et la densité de dix stations
de test. Dépôt créé, plan écrit, aucun code.

Deux revirements le même jour. Le format compact à colonne compagnon
`debit_brut_m3s` est abandonné après mesure des codes, au profit du format long.
Puis la chronique propre, qu'on envisageait de reconstruire par fusion des
statuts horodatage par horodatage, se révèle devoir être téléchargée telle que
le producteur l'arbitre : `most_valid` mélange par période et non par point, et
la fusion envisagée aurait produit un objet sans signification.

### 21 septembre 2026, seconde instruction après reprise de contexte

Environ 130 requêtes sur HydroPortail, Hub'Eau et Sandre, portant cette fois sur
l'ensemble du jeu de test et non sur le seul Rhône à Tarascon, ce qui corrige
plusieurs généralisations. Le détail est dans [SOURCE.md](SOURCE.md) ; les
découvertes qui ont changé la conception sont la falaise HTTP 500, la carte de
couverture `QIXnJ`, la résolution des quatre nomenclatures Sandre, la profondeur
réelle des chroniques et la variation de leur résolution d'un facteur 20.

Correction d'une erreur du jeu de test : W107403001, l'Arc à Aiguebelle, était
classée « hauteur seule, aucun débit » sur la foi d'une sonde d'une semaine. Elle
porte 3 264 jours de débit instantané. Leçon retenue et inscrite dans
[CLAUDE.md](CLAUDE.md) : **une sonde ponctuelle ne peut pas établir une
absence.**

Le fichier `chantier.md` est éclaté par objectif, et ce qui n'était pas tranché
devient une liste explicite d'arbitrages plutôt qu'une ambiguïté noyée dans la
prose.

### 21 septembre 2026, phases 1 à 3

Le squelette, la couche API et l'inventaire. Trois découvertes faites en
écrivant le code plutôt qu'en le planifiant.

**Les fenêtres doivent grandir autant que rétrécir.** Le plan ne prévoyait que
la coupe en deux sur un 500. En chiffrant les requêtes, le validé épars aurait
coûté trente-deux requêtes par station contre trois, soit plus cher que le brut
dense, ce qui est absurde. La largeur suit maintenant la densité observée dans
les deux sens.

**`step` est un bouton de quota, pas un garde-fou.** À `step=1` une fenêtre est
plafonnée à 347 jours, ce qui rendait impossible la fenêtre de seize ans dont le
validé a besoin. L'ordre est donc d'estimer les points, d'en déduire la fenêtre,
puis de mettre `step` au minimum qui la fasse accepter.

**`step` ne veut pas dire la même chose selon la famille**, et c'est le piège le
plus dangereux rencontré : en journalier, c'est le « n » de `QIXnJ`. L'inventaire
rendait 728 jours au lieu de 16 684 sans lever la moindre erreur, et seule la
valeur de référence l'a montré. C'est la justification par l'exemple des preuves
chiffrées attachées à chaque phase.

S'y ajoutent deux contraintes que la source impose et que les mesures de la
veille n'avaient pas rencontrées : `step` est borné à 1..30, ce qui plafonne une
fenêtre à 10 416 jours, et un HTTP 504 peut survenir sur une fenêtre large, qui
est traité comme transitoire puis comme une fenêtre trop large.

### 21 septembre 2026, rythme et nomenclature

Le plancher de temporisation de deux secondes est retiré : c'était un chiffre
inventé. La calibration qui devait le remplacer a été faite dans la foulée, en
cherchant le point de fonctionnement sûr et non le point de rupture, et **le
service n'a pas bronché** de 11 à 39 requêtes par minute. N'ayant pas de seuil
mesuré à respecter, la règle retenue s'indexe sur le service lui-même : attendre
aussi longtemps que la requête précédente a mis à répondre, ce qui maintient
notre rapport cyclique à 50 % quelles que soient la taille des requêtes et la
charge du serveur, et supprime le dernier nombre arbitraire du code. La campagne
complète est chiffrée à environ 2 h 40.

`ref_codes.csv` est figé dans le code plutôt que rapatrié du Sandre à chaque
exécution, avec un contrôle qui signale tout code inconnu. Vingt lignes
décennales ne valent pas une dépendance réseau supplémentaire. L'occasion a
montré que le plan disait ce qu'était cette table sans jamais dire à quoi elle
sert ; c'est corrigé dans [DESIGN.md](DESIGN.md), avec le cas de `q = 12`
« douteuse » qui touche 35 % du brut récent à Tarascon.

### 21 septembre 2026, arbitrages rendus

`chronique/` supprimée au profit d'une vue documentée dans le README.
`couverture.csv` retenue en station x année x statut, avec médiane, p90 et jours
de données. Le périmètre « on prend tout » est confirmé, avec le recadrage que
la variabilité n'est pas une limite à excuser mais la nature de la donnée.
L'outil de rééchantillonnage est retenu contre la grille figée, mais renvoyé
après la v1.
