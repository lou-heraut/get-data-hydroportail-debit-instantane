# Chantier

Ce que ce dépôt doit faire, ce qui a été mesuré avant d'écrire une ligne de
code, et dans quel ordre le construire. Les faits durables passeront dans
CLAUDE.md et le README quand ils existeront.

Ouvert le 21 septembre 2026. Aucun code à cette date.

## La demande

Une équipe travaille sur les cours d'eau à éclusées et a besoin des débits de
68 stations en Rhône-Méditerranée-Corse, sur toute la durée des chroniques, à
une résolution d'une heure ou moins et à pas de temps régulier. La liste des
stations est détenue par l'équipe demandeuse, elle n'est pas encore ici.

**Le périmètre de la v1 est plus étroit que la demande, et c'est délibéré.**
La v1 rapatrie proprement la donnée telle que HydroPortail la diffuse, à son
pas de temps natif, pour la rendre réutilisable dans l'unité. Le rééchantillonnage
à pas régulier est une seconde étape, traitée plus bas, parce que la question
est statistique avant d'être technique.

## Le point dur : Hub'Eau ne sait pas répondre

L'API Hub'Eau hydrométrie ne donne accès à aucune chronique instantanée
historique.

| Endpoint | Pas de temps | Profondeur |
|---|---|---|
| `observations_tr` | instantané, 5 min | **un mois glissant** |
| `obs_elab` | journalier et mensuel | depuis 1900 |

Soit instantané sans passé, soit complet mais journalier. La chronique
instantanée complète n'existe que sur **HydroPortail**.

## La source

La page station de HydroPortail sert ses séries par une route publique, sans
authentification, qui est le canal du formulaire affiché à l'écran :

```
GET https://hydro.eaufrance.fr/stationhydro/ajax/{code}/series
GET https://hydro.eaufrance.fr/sitehydro/ajax/{code}/series

hydro_series[variableType]                           simple_and_interpolated_and_hourly_variable
hydro_series[simpleAndInterpolatedAndHourlyVariable] Q | Qln | QmnH | H | Hln | V
hydro_series[statusData]                             raw | pre_validated_and_validated | validated | most_valid
hydro_series[step]                                   entier, minutes
hydro_series[startAt] / [endAt]                      jj/mm/aaaa
```

Réponse JSON, `series.data` = liste de `{t, v, s, q, m, c}`, `t` en UTC,
`v` **en litres par seconde**.

L'autre voie, `/export/series-hydro/direct-export/...`, rend du CSV et porte
ses paramètres dans l'URL, mais renvoie la page de connexion : elle demande un
compte HydroPortail, gratuit et en libre création.

## Ce que Hub'Eau et HydroPortail diffusent, et leur accord

Les mentions légales de HydroPortail disent que l'accès aux données
hydrométriques publiques est libre, et qu'un compte, facultatif, ouvre les
menus complets d'export. Sans compte, on exporte ce qui est affiché. Les quatre
statuts ci-dessous sont donc **tous publics** : ce sont les boutons du
formulaire, rien n'est dérobé à une zone réservée.

| Bouton du site | Valeur | Définition donnée par l'aide |
|---|---|---|
| Brutes | `raw` | données non traitées |
| Pré-validées et validées | `pre_validated_and_validated` | données contrôlées |
| Validées | `validated` | contrôlées et qualifiées par le producteur |
| Les plus valides | `most_valid` | meilleure qualité disponible, sélection automatique |

**Hub'Eau et HydroPortail sont bien la même donnée.** Vérifié sur
V720001002 du 22 août au 21 septembre 2026 : 8 594 horodatages communs,
**8 594 valeurs identiques au litre près**, écart maximal 0,000 m3/s.
HydroPortail en rend 8 827, sa fenêtre commençant plus tôt que le mois glissant
de Hub'Eau. Le recoupement est donc exact, ce n'est pas une source parallèle.

## Ce qui a été mesuré, pas déduit

Mesures du 21 septembre 2026, essentiellement sur V720001002, le Rhône à
Tarascon.

### Les statuts ne s'emboîtent pas

C'est le fait qui commande la conception. Sur une même semaine, les quatre
statuts rendent des volumes sans relation d'inclusion :

```
Durance a Embrun, X031001001, 1er au 7 mars 2024
  raw                          672 points, pas median 15 min
  pre_validated_and_validated   56
  validated                      0
  most_valid                    56
```

`most_valid`, pourtant le défaut du site, perd ici 92 % des points et fait
passer le pas de 15 minutes à 3 heures. Inversement l'Arc à Aiguebelle a du
validé en mars 2012 (432 points) là où le brut est absent.

Sur l'année entière à Tarascon, l'écart est massif : `raw` rend 105 209 points
en 2024, `validated` 6 077. Et la densité du validé varie énormément d'une
année à l'autre, de 3 622 points en 2022 à 37 952 en 2017, soit un pas médian
implicite de 145 minutes à 14 minutes, alors que le brut reste à 5 minutes.

**Conséquence : deux passes, `raw` et `most_valid`**, et elles suffisent à tout
prendre. Démonstration, en cherchant précisément le cas qui les mettrait en
défaut, celui d'un horodatage existant à deux niveaux validés différents :

```
station      periode           validated  preval+val  most_valid   statuts dans preval+val
V720001002   03/2024                 481         481         481   {16: 481}
V720001002   01/2026-06/2026           6        2849        2849   {16: 6, 12: 2843}
X031001001   03/2024                   0         293         293   {12: 293}
W011001001   03/2024                5055        5055        5055   {16: 5055}
V271201001   03/2024                 849         849         849   {16: 849}
Y532501001   03/2024                 135         135         135   {16: 135}
W107403001   03/2012                2314        2314        2314   {16: 2314}
V720001002   2015                  28278       28278       28278   {16: 28278}
```

La deuxième ligne est celle qui tranche : au premier semestre 2026 les deux
niveaux **coexistent bien** dans la même période, 6 points validés et 2 843
pré-validés, et `most_valid` rend les 2 849. Donc **un horodatage ne porte
jamais deux niveaux validés concurrents** : il n'existe pas de version
pré-validée d'un point par ailleurs validé. Il porte bien, lui, jusqu'à deux
versions, la brute et une validée, et c'est le maximum possible. `most_valid`
ramasse donc tout ce qui existe de validé avant d'y ajouter le brut là où rien
de mieux n'est disponible :

```
most_valid  =  pre_validated_and_validated  u  (brut la ou rien de mieux n'existe)
```

C'est un sur-ensemble, et la passe `pre_validated_and_validated` rend donc zéro
ligne supplémentaire sur les huit cas testés.

Huit cas ne sont pas une garantie. Un garde-fou plutôt qu'un pari : un
**contrôle automatique** vérifie sur un échantillon de stations que
`most_valid` contient bien `pre_validated_and_validated`. Si l'inclusion casse
un jour, on l'apprend par le contrôle et non au milieu d'une analyse.

### La validation corrige les valeurs, elle ne fait pas que trier

Mars 2024 à Tarascon :

```
brut      8 928 points, pas median  5 min, codes s=4  q=16 m=8  c=0
valide      481 points, pas median 70 min, codes s=16 q=20 m=10 c=0
```

Les 481 horodatages validés sont tous présents dans le brut, mais **196 portent
une valeur différente**, écart relatif médian 0,444 % et maximal 2,871 %. Garder
les deux niveaux n'est donc pas de la redondance.

### Les codes de qualité

`s` = statut, `q` = qualification, `m` = méthode, `c` = continuité. Établi par
la mesure : **`s=4` est brute et `s=16` est validée**. Mais `s` prend aussi la
valeur **12**, et les quatre codes ne se déduisent pas l'un de l'autre : le
dépouillement complet est dans la section sur le format de sortie, c'est lui qui
a commandé le choix du format long.

Sur `m`, une précision établie depuis : **dans une grille interpolée, `m=10`
marque les vrais points et `m=8` l'interpolation**, vérifié au litre près. Mais
`m` ne se lit pas seul pour autant, puisque la série brute est entièrement
`m=8` alors qu'il s'agit d'acquisitions bien réelles : un débit brut est
lui-même dérivé de la hauteur par la courbe de tarage. `m` se lit donc avec
`s`, et sa nomenclature reste à confirmer.

### Ce que `most_valid` fait vraiment : un mélange par période, pas par point

Point capital pour la forme du produit livré. `most_valid` **ne fusionne pas
horodatage par horodatage**, il retient le meilleur niveau disponible sur
chaque période. Dépouillement des statuts mois par mois :

```
V720001002 Rhone a Tarascon, janvier 2025 a septembre 2026, 34 425 points
  2025-01  {16: 1212}        valide
  2025-07  {16: 1994}        valide
  2026-01  {16: 6, 12: 436}  frontiere, mois melange
  2026-04  {12: 810}         pre-valide
  2026-07  {12: 252, 4: 1363} frontiere, mois melange
  mois melangeant plusieurs statuts : 2 sur 21
```

Sur la Durance à Embrun, 1 mois sur 33. La chronique est donc **homogène par
blocs** : le passé consolidé est validé, la période intermédiaire pré-validée,
le récent brut, et la frontière avance avec le temps. C'est un objet cohérent.

A contrario, une fusion **par horodatage**, qui prendrait le meilleur statut de
chaque point, produirait à Tarascon en mars 2024 une série de 8 928 points dont
481 corrigés et 8 447 non corrigés. Ni brute, ni validée, avec des
discontinuités là où les deux alternent. **Cet objet là n'a pas de sens, et il
ne sera pas produit.**

### La série validée est une courbe à points de rupture, pas un échantillonnage

L'autre moitié de l'explication. La série validée n'est pas « la série brute
dont on aurait gardé les bons points » : c'est la courbe que l'hydromètre
certifie, stockée par ses points de rupture. Démonstration sur mars 2024 à
Tarascon :

```
Q validated              481 points
Qln validated, 5 min   8 928 points   dont m=10 : 481   m=8 : 8 447
  la grille repasse exactement par les 481 points validés, ecart 0,0 l/s
  elle ne reprend pas la serie brute : 40 % de valeurs communes seulement
```

`m=10` marque donc les vrais points validés et `m=8` l'interpolation entre eux.
Vérifié aussi que `step` ne sous-échantillonne pas la série validée : `step` 1,
5, 20 et 60 rendent les mêmes 481 horodatages. Ces 481 points sont bien tout ce
que la série validée contient.

**Brut et validé ne diffèrent donc pas seulement en qualité, ils diffèrent en
nature** : l'un est un échantillonnage régulier à 5 minutes, l'autre une courbe
définie par des points de rupture qu'il faut interpoler pour lire. Les mettre
dans une même colonne sans le dire mélangerait deux objets différents.

Conséquence directe pour le sujet éclusées, et c'est la limite scientifique à
retenir : **l'hydromètre a élagué selon ce qui l'intéressait, qui n'est pas la
variation infra-horaire**. À Tarascon la courbe validée a un pas médian de
70 minutes, ce qui ne décrit pas une éclusée. À Moûtiers elle en a 5 055 points
pour 8 906 bruts, donc elle la décrit. **Cela se décide station par station**,
et c'est la raison d'être de la table de couverture.

### Le quota, et ce sur quoi il porte

Une demande trop large est refusée par un message qui annonce le compte :
« Vous avez demandé trop de données (527039 / 500000) ». Or 527 039 = 366 x
1440 : le compte est **la durée en minutes divisée par le pas**, pas le nombre
réel de points. La fenêtre maximale vaut donc `500000 x pas` minutes.

Et **`step` ne sous-échantillonne pas la série brute** : sur janvier 2024,
`step=1` et `step=20` rendent les 191 mêmes points aux mêmes horodatages. Pour
le brut, le paramètre ne sert qu'au quota. C'est ce qui permet de demander de
larges fenêtres, à condition de rester raisonnable sur la taille des réponses.

### Le coût réseau, et le rôle de gzip

Une station-année de brut à Tarascon, soit 105 209 points :

```
sans compression    31 552 303 octets sur le fil
avec gzip              567 840 octets sur le fil     facteur 56
```

**La compression est donc obligatoire, pas optionnelle.** Elle ne coûte rien au
serveur en calcul de la réponse, mais divise sa bande passante par 56. Budget
qui en découle, environ 0,57 Mo par station-année : 170 Mo pour dix stations sur
trente ans, 1,2 Go pour les 68. C'est tenable.

### Site et station

Question tranchée, avec une nuance qui mérite d'être retenue.

**Les chroniques vivent bien sur les stations.** Mais une station peut ne porter
qu'une partie des grandeurs, et le site est un regroupement, pas une série
fusionnée.

Le cas de l'Arc à Aiguebelle, site W1074030 :

```
W107403001  L'Arc a Aiguebelle                      H : 2016 points   Q : aucun
W107403003  L'Arc a Aiguebelle - Debit              Q : 2016 points
site W1074030                                       Q : 2016 points
```

La station au nom le plus évident **ne porte aucun débit**, seulement de la
hauteur. Le débit est sur une station voisine du même site, et le site le rend
aussi. Une liste de « 68 stations » peut donc parfaitement contenir des codes
sans débit.

Le cas du Rhône à Tarascon, site V7200010, montre le revers : le site groupe
trois stations, et interroger le site **empile des séries incompatibles**.

```
QmnJ au niveau site, 1er janvier 2024
  station=None        1 744,3 m3/s     la serie de reference du site
  V720001001  CNR     1 854,1 m3/s     autre operateur, autre courbe de tarage
  V720001002  DREAL   1 744,3 m3/s     identique a la serie du site
```

Deux opérateurs sur la même section donnent des débits journaliers écartés de
6 %. Un groupement naïf sur le site en ferait une moyenne dénuée de sens.

Autre piège du même endpoint : `observations_tr` interrogé avec un code de site
**renvoie chaque observation deux fois**, une fois attribuée à la station et une
fois au site avec `code_station` nul. Vérifié, 8 594 horodatages, 8 594
doublons, aucun écart de valeur. Un comptage naïf double tout.

**Règle retenue : interroger les stations, jamais les sites.** Mais résoudre
chaque code demandé vers son site, lister les stations soeurs, et dire laquelle
porte le débit. Une liste fournie par un tiers ne peut pas être prise au mot.

### La profondeur de l'instantané

L'instantané ne remonte pas aussi loin que le journalier. À Tarascon, station
ouverte en décembre 1994 d'après le référentiel, les requêtes sur 1970, 1980 et
1990 rendent zéro point, la série commence en 1995. « Toute la durée des
chroniques » ne veut donc pas dire la même chose selon le pas de temps, et la
couverture réelle doit être annoncée station par station.

## Le jeu de test

Dix stations, choisies pour couvrir les cas plutôt que pour représenter le
réseau. Densités mesurées sur la première semaine de mars, en points par
semaine.

```
code          cours d'eau et lieu                  2012 brut/val   2024 brut/val
W011001001    Isere a Moutiers          infl 3        0 /  217      2016 / 1293
W283201001    Drac au Pont-de-Claix     infl 3        0 /    0      2016 /  407
V271201001    Ain a Pont-d'Ain          infl 3        0 /  147      2016 /  265
V720001002    Rhone a Tarascon DREAL    infl 2     2016 /  123      2016 /   88
X031001001    Durance a Embrun          infl 1        0 /    0       672 /    0
Y532501001    Reyran a Frejus           fermee       0 /   21       672 /   51
W107403003    Arc a Aiguebelle - Debit  infl 3                      2016 / a voir
W107403001    Arc a Aiguebelle          infl 3        0 /  432         0 /    0   hauteur seule
W103000301    Arc a St-Michel Saussaz   infl 0        0 /    0         0 /    0   aucun debit
V031661301    Dranse a Chatel           2022                          0 /    0   aucun debit
```

Les sept premières portent du débit et donnent des profils variés : éclusée
alpine et de plaine, grand fleuve régulé, chronique faiblement influencée,
station fermée, site à trois stations. Les trois dernières sont des cas limites
délibérés : hauteur sans débit, et station en service au référentiel mais muette.

Le RRSE aurait été un choix naturel pour la partie faiblement influencée, mais
son code réseau n'a pas été identifié dans `code_sandre_reseau_station`, dont
les valeurs sont opaques (POH900, BSH060, RIC300). À reprendre si le besoin
s'en fait sentir ; la Durance à Embrun joue ce rôle en attendant.

## Ce que la v1 livre

```
donnees_hydroportail/
├── stations.csv       csv       une ligne par code demandé, couverture mesurée
├── ref_codes.csv      csv       vocabulaire de s, q, m, c
├── mesures/           parquet   la table de faits, tout ce qui est publié
├── chronique/         parquet   la passe most_valid telle que servie
├── datapackage.json   json      schéma, provenance, empreintes sha256
└── .sources/          json.gz   cache des réponses reçues, ignoré par git
```

Deux produits, comme chez les voisins : une table de faits fidèle à la source,
et un produit dérivé pour le confort, entièrement reconstructible depuis elle.

### La table de faits, `mesures/`

**Une ligne par point publié.** Rien d'autre.

```
code_station  date_obs              debit_m3s  statut  qualification  methode  continuite  most_valid
V720001002    2024-03-01T04:35:00Z   2140.000       4             16        8           0  false
V720001002    2024-03-01T04:35:00Z   2150.000      16             20       10           0  true
V720001002    2024-03-01T04:40:00Z   2160.000       4             16        8           0  false
V720001002    2026-09-15T10:00:00Z   1050.000       4             16        8           0  true
```

Les deux premières lignes sont le même instant en deux versions, la brute et la
validée. La dernière est le cas qui se lit mal si on ne l'a pas vu une fois :
en 2026 rien de mieux que le brut n'existe, donc `statut = 4` et `most_valid`
vrai sur la même ligne.

Une ligne veut toujours dire la même chose : une valeur publiée par
HydroPortail, avec ses quatre codes. Aucune colonne dont le vide signifierait
deux choses différentes, aucune colonne dont l'existence dépendrait du nombre de
niveaux de statut. Un horodatage publié à deux niveaux donne deux lignes, ce qui
est la stricte vérité de ce que la source diffuse.

Cette forme a été choisie **contre** une variante plus compacte, une ligne par
horodatage avec une colonne `debit_brut_m3s` à côté de la valeur retenue. La
mesure l'a écartée : `s` prend au moins trois valeurs dans la nature.

```
s statut        : 4 (32 711)    12 (293)      16 (8 834)
q qualification : 12 (934)      16 (31 892)   20 (9 012)
m methode       : 8 (33 139)    10 (8 699)
c continuite    : 0 (41 834)     4 (4)
```

La Durance à Embrun ne rend jamais `s=16` mais `s=12`, et sa série brute mêle
`q=16` sur 2 260 points et `q=12` sur 714. Une colonne compagnon par niveau ne
généralise donc pas, et les quatre codes ne sont pas déductibles l'un de
l'autre : le Reyran à Fréjus porte du validé en `m=8` là où les autres stations
le portent en `m=10`. Le format long est le seul qui absorbe ces cas sans être
réécrit, et qui absorbera un cinquième code si Sandre en ajoute un.

Le coût est la redondance des horodatages publiés à plusieurs niveaux, mesurée
sur mars : nulle sur l'Arc à Aiguebelle, 4,5 % sur le Reyran, 5 % sur l'Ain,
5,4 % à Tarascon, 9,8 % sur la Durance, et **57 % sur l'Isère à Moûtiers**, qui
valide 5 055 de ses 8 906 points bruts. Sur parquet, où ces colonnes sont très
répétitives, l'occupation réelle croît beaucoup moins que le nombre de lignes.

**Disposition sur le disque.** Un fichier parquet par station, rien de plus :

```
mesures/
├── V720001002.parquet
├── W011001001.parquet
└── ...
```

`code_station` reste une vraie colonne à l'intérieur du fichier, donc un fichier
isolé se lit seul et se transmet seul, pendant que le dossier entier s'ouvre
d'un coup comme un jeu unique avec `pyarrow` comme avec `arrow` en R. La colonne
étant constante dans un fichier, le parquet la réduit à presque rien.

Le découpage par station est aussi celui des **empreintes sha256**, une par
fichier donc une par station, ce qui rendra directement mesurable au passage
suivant quelles stations ont bougé. Le découpage par année, lui, est celui des
téléchargements et ne remonte pas jusqu'au disque : il vit dans `.sources/`.

| colonne | type | exemple | d'où elle vient |
|---|---|---|---|
| `code_station` | texte | `V720001002` | la demande |
| `date_obs` | horodatage ms UTC | `2024-03-01T04:35:00Z` | `t` |
| `debit_m3s` | flottant | `2140.000` | `v`, divisé par 1000 |
| `statut` | entier 8 bits | `4` | `s` |
| `qualification` | entier 8 bits | `16` | `q` |
| `methode` | entier 8 bits | `8` | `m` |
| `continuite` | entier 8 bits | `0` | `c` |
| `most_valid` | booléen | `false` | la passe qui a rendu le point |

La colonne `most_valid` ne se déduit pas de `statut`. Sur les périodes récentes
où aucun niveau validé n'existe, la passe `most_valid` rend le point brut
lui-même : la ligne porte alors `statut = 4` **et** `most_valid` vrai. C'est précisément ce qui
fait de `chronique/` un objet homogène par blocs plutôt qu'une série tronquée.

**Poids.** Mesuré : une station-année brute à Tarascon vaut 105 209 points, soit
567 840 octets de JSON gzippé sur le fil. Le parquet devrait tomber dans le même
ordre de grandeur, les quatre colonnes de codes étant quasi constantes et les
horodatages réguliers, ce qui donnerait environ 1,2 Go pour les 68 stations sur
trente ans. **À mesurer en phase 4** : c'est une attente, pas une mesure.

### La chronique propre, `chronique/`

**Elle n'est pas reconstruite, elle est téléchargée.** C'est la passe
`most_valid` telle que HydroPortail la sert, une ligne par horodatage :

```
code_station  date_obs              debit_m3s  statut  qualification  methode  continuite
V720001002    2024-03-01T04:35:00Z   2150.000      16             20       10           0
V720001002    2024-03-01T05:45:00Z   2160.000      16             20       10           0
```

Ne rien reconstruire est le choix central. L'arbitrage entre niveaux de qualité
appartient au producteur, qui sait quelle période il a certifiée ; le refaire
ici supposerait d'inventer une règle de découpage en périodes, donc d'affirmer
quelque chose que la source ne dit pas.

La table de faits porte une colonne booléenne `most_valid`, vraie pour les
points venus de cette passe, de sorte que `chronique/` soit exactement
`mesures[most_valid]` et qu'aucune information ne vive à un seul endroit.

Les deux passes se recouvrent partiellement : sur les périodes récentes,
`most_valid` rend les mêmes points bruts que la passe `raw`. La table de faits
est donc dédoublonnée sur la clé `(code_station, date_obs, statut)`, ce qui
suffit puisque deux niveaux différents portent par construction deux statuts
différents.

Même schéma et même partitionnement que `mesures/`, moins la colonne
`most_valid`, vraie partout par construction. Son poids va de 5 % de `mesures/`
sur une année entièrement validée comme 2024 à Tarascon, à 100 % sur une année
récente où `most_valid` ne rend que du brut faute de mieux.

### Le référentiel, `stations.csv` et `ref_codes.csv`

`stations.csv`, une ligne par code demandé, y compris ceux qui ne portent aucun
débit : l'identité Hub'Eau (libellé, cours d'eau, coordonnées, altitude, dates
d'ouverture et de fermeture, opérateur, influence), la résolution site/station
(code du site, stations soeurs, laquelle porte le débit), et surtout la
**couverture réellement mesurée**, début et fin de l'instantané, puis par passe
le nombre de points et l'`intervalle_median_min`, médiane des écarts entre deux
points consécutifs. Ce n'est **pas** un pas de temps : l'instantané n'a aucune
régularité garantie, et c'est bien pourquoi il faut le mesurer plutôt que le
supposer. Le brut approche 5 minutes parce que le capteur enregistre à cette
cadence, mais rien ne l'impose, et la courbe validée n'a aucune raison d'être
régulière, les 70 minutes de médiane à Tarascon recouvrant des écarts très
inégaux. C'est ce dernier bloc qui dit, station par
station, si `chronique/` suffit ou s'il faut descendre au brut, et c'est le
premier livrable, avant même de décider quoi télécharger en grand.

`ref_codes.csv`, une ligne par valeur rencontrée : `type` (`s`, `q`, `m`, `c`),
`code`, `libelle`, `definition`, `source`. C'est là que les nomenclatures Sandre
seront résolues, pas ailleurs.

### Le cache des réponses, `.sources/`

Les réponses JSON gzippées telles que reçues, **une par requête**, donc une par
station, passe et fenêtre de temps :

```
.sources/V720001002/2024_raw.json.gz
.sources/V720001002/2024_most_valid.json.gz
```

L'année sert d'unité de compte dans tout ce plan, mais **elle n'est pas imposée
par l'API** et le nom des fichiers suivra la fenêtre réellement retenue. La
seule contrainte mesurée est le quota, durée en minutes divisée par le pas,
plafonné à 500 000 : 347 jours si l'on demande au pas de 1 minute, dix-neuf ans
au pas de 20, et le pas ne sous-échantillonne pas le brut. Ce qui tranchera est
donc la taille des réponses, 31,5 Mo non compressés par station-année, pas le
quota. **Le fenêtrage est le travail de la phase 2**, il n'est pas arrêté ici.

Même rôle que `donnees_vigieau/.sources/` chez le voisin, reconstruire les
tables sans retélécharger, ce qui compte double ici puisque chaque passage coûte
de la bande passante à HydroPortail. Il porte aussi les empreintes sha256 du
datapackage, donc la trace de ce qui a été servi à une date donnée : c'est le
seul moyen de constater plus tard qu'une révision de courbe de tarage a réécrit
le passé. Ignoré par git, effaçable, d'un poids voisin de celui de `mesures/`.

### Ce que le README doit dire, plutôt que ce que le script déciderait

Le filtrage sur les statuts **n'est pas fait à la place de l'utilisateur**. Le
produit complet sort avec ses horodatages répétés et ses quatre codes, et le
README porte les avertissements qui disent ce qu'on peut en faire :

- mélanger les statuts **par période** a un sens, c'est ce que fait le
  producteur dans `chronique/` ; les mélanger **par horodatage** n'en a pas ;
- la série validée est une **courbe à points de rupture**, pas un
  échantillonnage : la lire sans interpoler entre ses points sous-échantillonne
  sans le dire ;
- la série brute est un vrai échantillonnage à 5 minutes, mais **non corrigée** ;
- descendre d'un cran sur une période donnée est légitime et attendu, c'est
  même l'usage principal de `mesures/` ;
- aucun seuil de qualité n'est appliqué par défaut, et il n'y en aura pas.

### À qui sert quoi

```
besoin                                        table          
chronique propre, directement exploitable     chronique/     une ligne par horodatage
selection personnalisee sur les codes         mesures/       tout, avec les 4 codes
signal infra-horaire des eclusees             mesures/       filtrer statut = 4
savoir laquelle des deux convient             stations.csv   couverture par statut
```

### Ne pas tout télécharger : `--statuts`

Les deux passes n'ont pas le même coût, dans un rapport de 1 à 17 à Tarascon
(105 209 points bruts contre 6 077 en plus valides sur 2024). Le paramètre
`--statuts` permet de ne prendre que ce dont on a besoin :

```
--statuts most_valid     la chronique propre seule, legere, suffit a beaucoup d'usages
--statuts brut           le signal a 5 minutes seul
--statuts les-deux       defaut, complet sur tout ce qui a ete mesure
```

Pour le sujet éclusées, `most_valid` **ne suffit pas** sur les stations où la
courbe validée a été élaguée au delà de l'heure. Pour un usage hydrologique
courant, il suffit très largement et divise le téléchargement par dix ou plus.

### Conventions d'écriture

Séparateur décimal **point**, dates ISO-8601 en UTC, UTF-8 sans BOM, comme dans
les dépôts voisins. Le parquet stocke de toute façon des flottants binaires,
sans séparateur. Débits en **m3/s**, convertis depuis les litres par seconde de
la source, la conversion étant signalée dans le datapackage.

**Nommage des colonnes : ne jamais traduire la source.** La règle de la famille
est la traçabilité jusqu'à la documentation d'origine, pas une préférence de
langue. Ici elle se coupe en deux, et les deux moitiés cohabitent sans conflit :

```
venant de Hub'Eau       code_station, libelle_station, code_site_hydro
venant du Sandre        statut, qualification, methode, continuite
venant d'HydroPortail   raw, most_valid, validated
```

Les deux premières sont en français parce que leurs sources le sont, reprises
telles quelles, sans accent comme Hub'Eau les écrit, jamais reformulées. La
troisième reste en anglais pour exactement la même raison : `most_valid` est le
nom d'un produit d'HydroPortail, celui du bouton de leur formulaire et de leur
paramètre `statusData`. Un nom de produit ou de paramètre se recopie, il ne se
traduit pas, sous peine de rompre le lien avec la documentation d'origine.

## La question ouverte du pas de temps régulier

**Point de chantier à part entière, à instruire en phase 2, pas à trancher
maintenant.** La demande veut un pas régulier de 20 minutes ou d'une heure. Ce
n'est pas un problème de format, c'est un problème statistique, et les mesures
ci-dessus montrent pourquoi.

Ce qui est acquis :

- HydroPortail sait interpoler côté serveur (`Qln` avec `step=20`), et rend une
  grille complète à 100 % sur une année testée. Rien ne dit ce qu'il fait d'un
  trou de trois mois, et la complétude parfaite suggère qu'il comble tout.
- Le pas natif varie d'un facteur 30 selon la station, le statut et l'année : de
  5 minutes à plus de 3 heures. **Une grille à 20 minutes bâtie sur une série à
  pas médian de 145 minutes serait très majoritairement de l'invention.**
- `QmnH`, le débit moyen horaire, est à écarter pour ce sujet : une moyenne
  lisse précisément les montées et descentes qui font l'éclusée.

Ce qu'il faut instruire, et qui demande un arbitrage scientifique :

1. **La loi d'interpolation.** Linéaire par défaut, mais l'hydrogramme d'éclusée
   a des fronts raides ; une interpolation linéaire sur un pas de 2 heures
   arrondit les angles et biaise toute métrique de gradient.
2. **Le seuil au delà duquel on renonce**, et sa justification. Une valeur de
   l'ordre de quelques heures se défend, mais il faut la confronter à la
   distribution réelle des écarts entre points sur les stations retenues.
3. **Les modalités d'application du seuil** : coupe franche laissant la grille
   vide, ou marquage conservant la valeur avec un indicateur de confiance.
4. **Ce qu'on publie à côté de la valeur.** L'idiome des dépôts voisins veut
   qu'une colonne dérivée s'accompagne d'une colonne qui dit jusqu'où la croire,
   comme `distance_site_hydro_m` ou `ecart_date_campagne_j`. Ici ce serait
   l'écart en minutes à la mesure réelle la plus proche.
5. **Faut-il seulement livrer une grille**, ou livrer la série native plus un
   outil de rééchantillonnage que l'analyste paramètre lui-même ? La seconde
   voie évite de figer un choix scientifique dans un fichier.

Rien de tout cela ne bloque la v1, et c'est la raison de l'ordre retenu : la
série native est le socle dont toute grille se déduit, et la déduction ne peut
pas se décider sans avoir vu la distribution réelle des pas.

## La mise à jour incrémentale

Écartée en v1, et pas seulement pour aller vite.

Un débit n'est pas une observation figée : il est calculé à partir d'une hauteur
par une courbe de tarage, et **une révision de cette courbe réécrit le passé**.
Une reprise fondée sur les dates manquerait ces corrections en silence. La
mesure le confirme d'ailleurs par un autre chemin : la validation modifie déjà
196 valeurs sur 481 sur un seul mois.

Ce que v1 fait : tout télécharger. Ce que v1 prépare : une **empreinte sha256
par station et par tranche**, écrite dans le datapackage, qui rendra mesurable
au passage suivant ce qui a bougé dans le passé. Une v2 se décidera sur ces
faits.

À instruire pour cette v2 : le JSON porte un champ `correctionCurves`, vide sur
les essais faits. S'il expose les courbes de tarage et leurs dates, il donne le
signal de révision qui manque.

## Est-ce que c'est une faille, et faut-il prévenir ?

Question posée, et elle mérite d'être tranchée par écrit plutôt que laissée en
malaise diffus.

**Ce n'est pas une faille.** Une faille, ce serait contourner une
authentification, atteindre une donnée qui n'est pas destinée au public, ou
détourner un paramètre pour sortir du périmètre prévu. Rien de tout cela ici :
la route sert exactement ce que la page affiche à n'importe quel visiteur
anonyme, avec les mêmes paramètres que le formulaire à l'écran. Et quand
l'instruction a rencontré la voie réservée, `direct-export`, celle-ci a renvoyé
la page de connexion et on s'est arrêté là. Le contrôle d'accès a fonctionné et
il a été respecté. Ce qu'on fait est l'automatisation d'une lecture publique
d'une donnée publique, dont les mentions légales disent elles-mêmes que l'accès
est libre.

**L'absence de `robots.txt` ne veut rien dire.** Ce fichier encadre l'indexation
par les moteurs de recherche, pas l'accès aux données. Une réponse 404 signifie
qu'aucune directive n'existe, ce qui n'est ni une autorisation ni une
interdiction. Beaucoup de sites de service public n'en ont pas. Ce n'est pas un
signal.

**En revanche le service est bel et bien fragilisable**, et le constat est
juste : une requête peut demander 500 000 points, et sa génération coûte cher au
serveur, 31,5 Mo de JSON pour une seule station-année. Quelques dizaines de
requêtes lancées en parallèle feraient mal. Ce n'est pas un défaut de sécurité,
c'est une caractéristique de capacité que partage n'importe quelle fonction de
recherche ou d'export. La conclusion n'est pas de s'interdire l'usage, c'est de
ne jamais être celui qui fait ça.

**Le mail n'est pas nécessaire pour l'instant.** Le `User-Agent` nominatif, qui
porte le projet, l'unité et une adresse de contact, est la forme proportionnée
de la déclaration : si quelqu'un regarde les journaux, il voit un usage de
recherche identifié et un moyen de joindre son auteur, pas un aspirateur
anonyme. C'est plus utile qu'un courriel qui se perd. La question se reposera
au moment de lancer la campagne complète sur les 68 stations avec tout
l'historique, où un message devient une assurance bon marché. Pas avant.

## Politesse envers HydroPortail

Aucune règle publiée n'encadre l'accès automatisé, donc les règles sont fixées
ici, et elles sont mesurées.

1. **gzip systématique.** Facteur 56 sur la bande passante, 31,5 Mo contre
   568 Ko pour une station-année. Non négociable.
2. **Une requête à la fois**, aucun parallélisme, jamais. C'est la règle qui
   protège réellement le service.
3. **Temporisation adaptative, indexée sur le coût de la réponse précédente.**
   Plutôt qu'un délai fixe, attendre au moins aussi longtemps que la requête
   précédente a mis à répondre, avec un plancher de 2 secondes. Une réponse
   lourde ou un serveur qui peine nous ralentissent alors automatiquement, ce
   qu'un délai fixe ne sait pas faire.
4. **Un peu d'aléatoire sur ce délai**, de l'ordre de 20 %, pour ne pas taper à
   intervalle parfaitement régulier. La raison est le lissage de charge, pas le
   camouflage : chercher à passer pour un humain serait de l'évasion, et c'est
   précisément ce qui ferait ressembler un usage légitime à un usage qui se
   cache. On fait l'inverse, on se rend identifiable.
5. **Recul exponentiel** sur 429, 500 et 503, et arrêt franc après quelques
   échecs consécutifs plutôt qu'un acharnement.
6. **Fenêtres larges plutôt que nombreuses**, en visant moins de 100 000 points
   par réponse : le serveur paie la génération, une requête de cinq ans coûte
   moins que soixante requêtes mensuelles.
7. **`User-Agent` explicite**, sans donnée personnelle, voir ci-dessous. Aucune
   imitation de navigateur.
8. **Reprise sur disque**, pour qu'une interruption ne fasse jamais
   retélécharger ce qui est déjà là. C'est de la politesse autant que du confort.
9. **Campagnes longues hors heures ouvrées.**

### Comment s'identifier sans exposer qui que ce soit

Le `User-Agent` doit dire **quel logiciel appelle et où le trouver**, pas qui
est derrière le clavier. C'est la convention des robots bien élevés, qui portent
une URL et non une adresse de courriel :

```
get-data-hydroportail/1.0 (+https://github.com/lou-heraut/get-data-hydroportail-debit-instantane)
```

Trois raisons de s'en tenir là. L'URL du dépôt porte déjà le moyen de joindre
quelqu'un, sans diffuser une adresse à chaque requête. Un courriel dans un
en-tête est une donnée personnelle envoyée à un tiers et journalisée chez lui,
ce qui n'a pas à être le défaut. Et la valeur ne change pas d'un utilisateur à
l'autre, donc ce qui est déclaré reste vrai quel que soit celui qui lance le
script.

**Rien n'est collecté automatiquement.** Ni l'adresse du dépôt git local, ni
l'utilisateur du système, ni le courriel de la configuration git : le déduire
reviendrait à publier l'identité de quelqu'un sans son accord.

Pour qui veut se signaler nommément, par exemple avant une campagne longue, une
variable d'environnement facultative ajoute un contact, et elle seule :

```bash
export HYDROPORTAIL_CONTACT="louis.heraut@inrae.fr"
```

L'adresse IP, elle, est vue de toute façon et ne se contrôle pas. Elle
identifie une machine, pas une intention : c'est le `User-Agent` qui dit
pourquoi on appelle, et c'est lui qui distingue un usage de recherche déclaré
d'un aspirateur anonyme.

**Le compte HydroPortail est écarté.** Il aurait ouvert `direct-export` et son
CSV, mais le gain de poids est illusoire une fois gzip actif : on est déjà à
5,4 octets par point sur le fil, et un CSV compressé ne ferait pas beaucoup
mieux. Le seul gain réel serait pour le serveur, qui fabriquerait moins de
texte avant de le compresser. C'est mince au regard du coût, à savoir un dépôt
inutilisable sans identifiants. Les neuf règles ci-dessus pèsent infiniment
plus lourd que le format de la réponse.

**Risque assumé** : cette route n'est pas une API contractuelle, c'est le canal
interne d'une page web. Elle peut changer sans préavis. Elle est isolée dans
`api.py` pour qu'une rupture reste la correction d'un seul fichier, et
`direct-export` reste documenté comme repli si le besoin d'un compte devient
inévitable.

## Le plan

```
phase 1   squelette du depot                  pyproject, LICENSE, SPDX, venv
phase 2   couche API isolee                   politesse, quota, fenetrage, reprise
phase 3   referentiel et couverture reelle    stations.csv, resolution site/station
phase 4   telechargement, 2 passes            mesures/ et chronique/
phase 5   datapackage et empreintes           datapackage.json
phase 6   README, relecture Python et R       la partie qui repond au mail
phase 7   controles                           croise Hub'Eau, inclusion des statuts
---- livraison v1 ----
phase 8   instruction du pas regulier          la question ouverte ci-dessus
```

Disposition, conforme aux dépôts voisins :

```
download_hydroportail.py    interface en ligne de commande
hydroportail/api.py         couche HTTP, politesse, quota, fenetrage
hydroportail/schema.py      colonnes, types, vocabulaire, datapackage
hydroportail/download.py    orchestration, ecriture, relecture
```

## Questions ouvertes

1. **La liste des 68 stations.** En attente de l'équipe demandeuse. Le jeu de test de dix
   stations permet de tout construire sans elle.
2. **Nomenclatures Sandre** de `s`, `q`, `m` et `c`. À résoudre en écrivant
   `ref_codes.csv`, pas avant. Valeurs rencontrées : `s` 4, 12, 16 ; `q` 12, 16,
   20 ; `m` 8, 10 ; `c` 0, 4. Seul `s=4` brute et `s=16` validée sont établis
   par la mesure ; `s=12` est vraisemblablement pré-validée, à confirmer. Le
   format long ne dépend pas de cette réponse, c'est ce qui permet de la
   remettre à plus tard.

Deux questions sont tranchées et n'en sont plus. **Pas de compte HydroPortail**,
le gain de poids est illusoire sous gzip. **Pas de hauteur d'eau**, seulement le
débit : les stations à hauteur seule, comme l'Arc à Aiguebelle, sont signalées
dans `stations.csv` comme sans débit, et c'est tout.

## Journal

**21 septembre 2026.** Instruction complète de la source. Établi que Hub'Eau ne
sert pas l'instantané historique ; trouvé et testé la route AJAX de
HydroPortail ; recoupé Hub'Eau et HydroPortail sur un mois, 8 594 valeurs
identiques au litre près ; mesuré le quota, le comportement de `step`, le gain
de gzip, la non-inclusion des statuts, la correction des valeurs par la
validation, la relation site/station sur deux contre-exemples, et la densité de
dix stations de test. Dossier créé, dépôt git initialisé, plan écrit. Aucun code.

Arbitrages du même jour : périmètre v1 réduit à la donnée native, le pas
régulier devenant un point de chantier à part ; table de faits en chronique
unique avec statut par point plutôt qu'en doublons par statut ; compte
HydroPortail écarté ; hauteur d'eau écartée ; pas de courriel au SCHAPI à ce
stade, le `User-Agent` tenant lieu de déclaration.

Revirement en fin de journée sur le format de sortie. La proposition d'une
ligne par horodatage avec colonne compagnon `debit_brut_m3s` a été **abandonnée**
après mesure des codes : `s` prend trois valeurs et non deux, et les quatre
codes ne se déduisent pas l'un de l'autre. Format long retenu pour la table de
faits, plus un produit dérivé à une ligne par horodatage pour le confort de
relecture. Le `User-Agent` passe d'une identification nominative à une
identification du logiciel par URL, sans donnée personnelle.

Second revirement, sur le produit dérivé. Mesuré que `most_valid` mélange les
statuts **par période et non par horodatage**, 2 mois sur 21 à Tarascon, et que
la série validée est une courbe à points de rupture et non un échantillonnage.
La fusion par horodatage que j'avais proposée aurait produit un objet sans
signification. La chronique propre est donc **téléchargée** telle que le
producteur l'arbitre, plus jamais reconstruite. Passes ramenées à `raw` et
`most_valid`, `pre_validated_and_validated` étant inutile puisque `most_valid`
la contient point pour point, vérifié sur six cas. Ajout du paramètre
`--statuts`.

Relecture à deux de la forme du produit livré, après une coupure qui avait
laissé cette partie dans la conversation et non dans ce fichier. Trois
corrections. La colonne booléenne porte le nom d'HydroPortail, **`most_valid`**,
et la règle de nommage, ne jamais traduire un nom de produit ou de paramètre de
la source, est écrite dans les conventions.
Le partitionnement Hive par station et par année est abandonné au profit d'**un
fichier parquet par station**, le découpage par année n'ayant d'existence que
dans `.sources/` et dans les empreintes. Les colonnes, les dossiers, le poids
attendu et un exemple de lignes réelles sont maintenant dans le plan, ce qui
était le manque à l'origine de cette relecture.

Discussion de fin de journée sur le risque de décider à la place de
l'utilisateur. Le retrait de la passe intermédiaire est confirmé par la mesure,
un horodatage ne portant jamais deux niveaux validés concurrents, mais il est
assorti d'un contrôle automatique d'inclusion plutôt que laissé en pari sur huit
cas. Principe posé : le script n'applique **aucun**
filtrage de qualité par défaut, il livre tout, et le README dit ce qu'on peut
en faire.
