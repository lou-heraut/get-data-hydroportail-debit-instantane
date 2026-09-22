# Ce qui reste à faire

État au 21 septembre 2026 : **v1.0.0 livrée**. Ce que cette version contient est
dans [CHANGELOG.md](CHANGELOG.md), pourquoi elle est faite ainsi dans
[DESIGN.md](DESIGN.md), et ce que la source fait réellement dans
[SOURCE.md](SOURCE.md).

Ce fichier ne garde que l'avenir. Il rétrécit à chaque version, voir la section
« Cycle de vie des fichiers » de [CLAUDE.md](CLAUDE.md).

## L'outil de rééchantillonnage

**C'est ce que la demande d'origine réclamait vraiment.** La v1 livre la donnée
native, qui est le socle dont toute grille se déduit, mais elle ne répond pas
encore à la question posée : une chronique à pas régulier, utilisable pour
étudier les éclusées.

Le point de départ a changé en cours de route. On comptait sur l'interpolation
côté serveur, `Qln` avec un pas choisi ; la mesure montre qu'elle perd 78 % des
points de rupture de la série validée, donc qu'elle dégrade la donnée au lieu de
la servir. Cette voie est fermée.

### Ce que la demande a précisé le 22 septembre

Le pas visé est de quinze minutes ; une heure au plus si ce n'est pas possible ;
et surtout le même pas d'un bout à l'autre. Trois choses en sortent :

- **Une cible, 15 minutes, et un plafond, une heure.** La fourchette d'avant,
  « une heure ou moins », devient un ordre de préférence.
- **La régularité prime sur la finesse.** Une grille dont le pas suivrait la
  densité réellement disponible aurait été la réponse la plus fidèle à la
  donnée ; la demande l'écarte.
- **Une ambiguïté à lever avant d'écrire quoi que ce soit.** « Toujours le même
  pour chaque station » se lit de deux façons : un seul pas pour les 51
  stations, ou un pas propre à chaque station mais constant sur toute sa
  chronique. Les deux donnent un outil différent, et la première est la plus
  contraignante, puisque la station la moins bien servie fixerait le pas de
  toutes les autres.

### Ce que les mesures disent de cette cible

Le comptage est dans [SOURCE.md](SOURCE.md), section « Ce qu'une grille
régulière trouverait sous elle ». Il tranche un point : **le pas natif ne
soutient une grille de 15 minutes que sur le brut, et le brut ne commence qu'en
2013** sur sept des huit stations du jeu de test. Avant 2013 il ne reste que la
courbe validée, dont la moitié des jours ont un pas médian supérieur à une heure
et dont le p90 dépasse l'heure dans 97 % des cas.

Une grille unique à 15 minutes sur toute la chronique reste réalisable, mais
elle serait portée par la mesure après 2013 et par l'interpolation avant. C'est
l'arbitrage central, et il appartient à l'analyste et non au logiciel.

### Les arbitrages qui restent

**Ce sera un outil paramétrable et non une grille figée**, ce qui évite
d'enfermer un choix scientifique dans un fichier et laisse l'analyste assumer le
sien. Cinq points demandent un arbitrage qui n'est pas technique :

1. **La loi d'interpolation, qui ne pose pas la même question selon le statut.**
   Sur le brut, qui est un échantillonnage régulier, interpoler linéairement un
   front d'éclusée arrondit les angles et biaise toute métrique de gradient. Sur
   le validé, qui est une courbe à points de rupture, l'interpolation linéaire
   est la lecture que le producteur définit, et non une approximation ajoutée.
   La même option n'a donc pas le même sens des deux côtés.
2. **Le statut qui sert de source à la grille.** Le brut est dense mais récent ;
   le validé est profond mais élagué selon ce qui intéressait l'hydromètre, qui
   n'est pas la variation infra-horaire. Prendre le meilleur des deux à chaque
   instant produit une chronique dont la nature change en cours de route, ce que
   la v1 a refusé de faire point par point ; n'en garder qu'un seul ampute soit
   le passé, soit la finesse.
3. **Le seuil au delà duquel on renonce à interpoler.** Il décide concrètement
   si les années d'avant 2013 sortent vides ou remplies. `couverture.csv` donne
   la distribution réelle des écarts station par station et année par année,
   c'est à elle qu'il faut le confronter.
4. **Les modalités d'application du seuil** : coupe franche laissant la grille
   vide, ou marquage conservant la valeur avec un indicateur de confiance. La
   coupe franche est celle qui respecte la contrainte de constance, puisqu'elle
   laisse la grille intacte et se contente de ne pas la remplir.
5. **Ce qu'on publie à côté de la valeur.** L'idiome des dépôts voisins veut
   qu'une colonne dérivée s'accompagne d'une colonne qui dit jusqu'où la croire.
   Ici ce serait l'écart en minutes à la mesure réelle la plus proche, qui rend
   vérifiable ligne par ligne ce que le seuil a laissé passer.

`QmnH`, le débit moyen horaire, reste à écarter pour ce sujet : une moyenne
lisse précisément les montées et descentes qui font l'éclusée.

### Les deux questions à poser à l'équipe demandeuse

Elles conditionnent l'outil et ne se tranchent pas ici :

1. Un seul pas pour les 51 stations, ou un pas par station constant dans le
   temps ?
2. Faut-il remonter avant 2013, sachant que la grille y serait portée par la
   courbe validée et non par la mesure brute, ou l'étude se limite-t-elle à la
   période où le pas natif soutient la cible ?

Les trois autres arbitrages peuvent lui être soumis sous forme de proposition
argumentée plutôt que de question ouverte.

## Les questions ouvertes

### La liste des stations, reçue le 22 septembre 2026

Tout tient dans `ressources/2026-09_eclusees-rmc/`, dont le `README.md` dit le
besoin : la liste telle qu'elle a été reçue, et ce que `preparer_liste.py` en
tire, 51 codes normalisés, traduits en codes de station et confrontés au
service, avec pour chacun comment il a été résolu et ce qui reste douteux. Ce
que la traduction a donné est mesuré dans [SOURCE.md](SOURCE.md), section « Ce
qu'une liste réelle a donné ».

Les choix que le script ne peut pas faire seul vivent dans l'`arbitrages.csv`
du dossier, avec leur motif et leur type, plutôt que dans le CSV produit, qui se
réécrit à chaque passage. Trois ont été tranchés, et la règle
qui s'en dégage vaut pour la suite : **c'est la donnée qui prime sur
l'exploitant demandé.** Quand la station nommée ne publie pas d'instantané et
qu'une autre du même point en publie, on prend celle qui en publie et on le
signale. C'est ce qui a été fait pour la Bourne, où la station EDF demandée ne
porte que 64 jours contre 3 241 à celle de la DREAL, et c'est déjà ce que le
script faisait pour les trois stations CNR du Rhône qui ne publient rien.

Ce qui reste à faire :

1. **Poser les quatre codes sans station à l'équipe demandeuse.** Deux sont des
   absences établies, l'Arc à Saint-Michel et l'Eau d'Olle à Allemond, qui ne
   portent aucun débit instantané. Les deux autres, la Romanche à Livet-et-Gavet
   et le Rhône à Ruffieux, ne sont pas conclus : le service refuse de servir une
   de leurs stations, et une station non sondée ne prouve rien.
2. **Inventorier** les stations retenues, une requête de deux secondes chacune,
   sans télécharger de chronique.
3. **Rendre `couverture.csv` à l'équipe demandeuse** pour qu'elle choisisse ses
   stations et sa période avant qu'on engage les heures de téléchargement.

Les dix-neuf lignes encore signalées le sont pour information et non pour
décision : un site porte plusieurs stations dont une seule s'appelle comme lui,
ou le service a refusé une soeur qui ne changeait rien. Elles se relisent au
moment de rendre la liste.

L'écart entre 51 et les 68 stations annoncées n'est toujours pas expliqué, et
vaut d'être posé avec le reste.

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
place naturelle est le résumé de `--inventaire` et le rapport de
`preparer_liste.py`, pas les CSV, qui restent des données.

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

## Ce qui est tranché, et qu'on ne rouvre pas

Le raisonnement de chacun est dans [DESIGN.md](DESIGN.md). Cette liste n'est là
que pour éviter de les rediscuter par oubli.

- **Une seule table de faits**, pas de chronique séparée : ce serait une vue, et
  le README porte la ligne qui la produit.
- **Une table de couverture station x année x statut**, parce qu'un pas médian
  unique par station dit le contraire de la vérité aux deux bouts.
- **On prend tout.** La variabilité de quantité et de qualité est le principe de
  la donnée hydrométrique, pas un défaut à corriger ni une limite à excuser.
- **`--statuts raw`**, pas `brut` : un nom de paramètre de la source se recopie.
- **Pas de compte HydroPortail**, le gain est illusoire sous gzip.
- **Pas de hauteur d'eau**, seulement le débit.
- **Pas de fusion par horodatage** entre niveaux de statut.
- **Pas de filtrage de qualité par défaut**, jamais.
- **Pas d'incrémental** tant qu'aucun signal de révision n'est exposé.
