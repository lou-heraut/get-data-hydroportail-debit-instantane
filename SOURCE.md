# La source

Ce que les services interrogés font réellement, établi par la mesure et non par
la lecture de leur documentation. Ce fichier ne contient que des faits et la
façon de les revérifier. Ce qu'on en déduit pour le produit est dans
[DESIGN.md](DESIGN.md), ce qui reste à faire dans [ROADMAP.md](ROADMAP.md).

Chaque affirmation chiffrée ci-dessous a été obtenue sur le service réel. Les
dates entre parenthèses disent quand, parce qu'un service change.

## Pourquoi pas Hub'Eau

L'API Hub'Eau hydrométrie ne donne accès à aucune chronique instantanée
historique.

| Endpoint | Pas de temps | Profondeur |
|---|---|---|
| `observations_tr` | instantané, 5 min | un mois glissant |
| `obs_elab` | journalier (`QmnJ`) et mensuel (`QmM`) | depuis 1900 |

Soit l'instantané sans le passé, soit le passé sans l'instantané. La chronique
instantanée complète n'existe que sur HydroPortail.

Hub'Eau garde deux rôles, tous deux secondaires : son référentiel des stations
porte l'identité, la position, les dates d'ouverture et le rattachement au
site ; et `observations_tr` porte les **libellés** des codes de qualité que
HydroPortail ne rend qu'en chiffres, ce qui a servi à les résoudre.

**Hub'Eau et HydroPortail diffusent bien la même donnée.** Vérifié sur
V720001002 du 22 août au 21 septembre 2026 : 8 594 horodatages communs, 8 594
valeurs identiques au litre près, écart maximal 0,000 m3/s. HydroPortail en
rend 8 827, sa fenêtre commençant plus tôt que le mois glissant de Hub'Eau.

## La route HydroPortail

La page station sert ses séries par une route publique, sans authentification,
qui est le canal du formulaire affiché à l'écran :

```
GET https://hydro.eaufrance.fr/stationhydro/ajax/{code}/series
GET https://hydro.eaufrance.fr/sitehydro/ajax/{code}/series
```

L'autre voie, `/export/series-hydro/direct-export/...`, rend du CSV mais
renvoie la page de connexion : elle demande un compte HydroPortail.

### Les paramètres, relevés dans le formulaire de la page

**Il y a trois familles de grandeurs, pas une.** Le champ `variableType` choisit
la famille, et chaque famille a son propre champ de sélection. C'est le point
que les premières sondes avaient manqué, et il porte tout le reste.

| `hydro_series[variableType]` | champ de sélection associé | grandeurs |
|---|---|---|
| `simple_and_interpolated_and_hourly_variable` | `simpleAndInterpolatedAndHourlyVariable` | `H`, `Hln`, `Q`, `Qln`, `QmnH`, `V` |
| `daily_variable` | `dailyVariable` | `HINnJ`, `HIXnJ`, `QmnJ`, `QINnJ`, `QIXnJ` |
| `monthly_variable` | `monthlyVariable` | `HINM`, `HIXM`, `QmM`, `QINM`, `QIXM` |

Les autres paramètres :

```
hydro_series[statusData]    raw | pre_validated_and_validated | validated | most_valid
hydro_series[step]          entier, minutes
hydro_series[startAt]       jj/mm/aaaa
hydro_series[endAt]         jj/mm/aaaa
hydro_series[rolling]       case a cocher, moyennes glissantes
```

Les quatre statuts sont les quatre boutons du formulaire public :

| Bouton du site | Valeur |
|---|---|
| Les plus valides | `most_valid` |
| Validées | `validated` |
| Pré-validées et validées | `pre_validated_and_validated` |
| Brutes | `raw` |

### La forme de la réponse

JSON. `series.data` est la liste des points, et le reste décrit le contexte :

```
range             les bornes demandees, renvoyees telles quelles
timezone          UTC
unitH unitQ unitRR    m, m3, mm : unites d'AFFICHAGE, pas celles des donnees
series.unit       l : l'unite reelle des valeurs, litres par seconde pour Q
series.code       le code de l'entite qui a repondu
series.timeStep   le pas demande
series.statuses   le statut demande
series.title      libelle complet, entite, periode
statistics        q25, median, q75, minimum, maximum, mean, en unite de series.unit
events tonnages correctionCurves thresholds    vides sur tous les essais
```

**Attention à l'unité.** `unitQ` vaut `m3` mais les valeurs sont en litres par
seconde, ce que dit `series.unit` valant `l`. Lire `unitQ` conduirait à un
facteur 1 000 d'erreur. C'est `series.unit` qui fait foi.

**Un point porte sept clés, pas six** :

```json
{"v": 2230000, "t": "2024-03-01T00:00:00Z", "md": null, "s": 4, "q": 16, "m": 8, "c": 0}
```

`md` est le **moment de la donnée** : pour une grandeur d'extrême journalier, il
porte l'instant où l'extrême s'est produit, tandis que `t` porte le jour. Pour
le Q instantané il est toujours nul, vérifié sur 634 998 points en cache
(21 septembre 2026). Il n'est donc pas repris dans le produit, mais il existe et
toute reprise ajoutant une grandeur journalière devra le traiter.

## Les codes de qualité

Les quatre codes `s`, `q`, `m`, `c` sont des nomenclatures Sandre, servies en
entier dans un seul JSON : `https://api.sandre.eaufrance.fr/referentiels/v1/nsa.json`,
874 nomenclatures avec tous leurs éléments.

| champ | nomenclature Sandre | valeurs observées |
|---|---|---|
| `s` statut | **510** Statut de l'observation | 4, 8, 12, 16 |
| `q` qualification | **515** Qualification de l'observation | 12, 16, 20 |
| `m` méthode | **512** Méthode d'obtention du résultat | 8, 10 |
| `c` continuité | **923** Continuité de la donnée de l'observation hydrométrique | 0, 4, 8 |

```
s  510    0 Sans validation   4 Brute   8 Corrige   12 Pre-valide   16 Valide
q  515    0 Neutre   4 Faible   8 Forte   12 Douteuse   16 Non qualifiee
          20 Bonne   30 Valeur estimee
m  512    0 MES   4 REC   8 CAL   10 EXP   12 Interpolation   14 EST   16 Forcage
c  923    0 Continue   1 Discontinue   2 et 4 Discontinue faible
          6 Discontinue neutre   8 Discontinue forte
```

**Le piège : les nomenclatures au titre le plus évident sont les mauvaises.** La
507 s'appelle « Méthode d'obtention du résultat de l'observation hydro » mais ne
contient ni le code 8 ni le code 10. La 72 « Code de continuité du point » ne
contient que 1 et 2. La 508 « Qualification de la donnée de l'observation » ne
contient pas « Douteuse ». Choisir sur le titre donne une table fausse et
plausible, ce qui est pire qu'une table absente. **Apparier sur les valeurs de
code, puis vérifier contre les libellés que Hub'Eau sert dans
`observations_tr`**, où ils concordent exactement (`4` Brute, `12` Pré-validée,
`12` Douteuse, `16` Non qualifiée, `8` Calculée, `0` Continue, `4` Discontinue
faible, `8` Discontinue forte).

Deux lectures que cela corrige, et qui comptent pour l'analyse :

- **`m = 10` veut dire « expertisée » (EXP), pas « vrai point de mesure ».** Que
  les points expertisés coïncident avec les points de rupture d'une série
  validée est vrai localement, ce n'est pas la définition du code.
- **`q = 12` veut dire « douteuse ».** C'est le seul drapeau de qualité porté par
  chaque point, et il n'est pas rare : sur septembre 2026 à Tarascon, 2 018 des
  5 754 points bruts sont marqués douteux, soit 35 %.

## Ce que font les quatre statuts

### Ils ne s'emboîtent pas

Sur une même semaine, les quatre statuts rendent des volumes sans relation
d'inclusion. La Durance à Embrun, X031001001, du 1er au 7 mars 2024 :

```
raw                          672 points, pas median 15 min
pre_validated_and_validated   56
validated                      0
most_valid                    56
```

`most_valid`, pourtant le défaut du site, perd ici 92 % des points et fait
passer le pas de 15 minutes à 3 heures.

### `most_valid` est un sur-ensemble de `pre_validated_and_validated`

Vérifié sur le cas qui pourrait le mettre en défaut, celui d'une période où
deux niveaux validés coexistent. Tarascon, premier semestre 2026 :

```
validated                        6 points   s={16: 6}
pre_validated_and_validated   2 849 points   s={16: 6, 12: 2843}
most_valid                    2 849 points   s={16: 6, 12: 2843}
raw                          51 551 points   s={4: 51551}
```

Les deux niveaux coexistent bien dans la même période, et `most_valid` les rend
tous les deux. Aucun horodatage ne porte deux niveaux validés concurrents :
zéro doublon d'horodatage dans `pre_validated_and_validated`. Donc

```
most_valid  =  pre_validated_and_validated  u  (brut la ou rien de mieux n'existe)
```

et la passe `pre_validated_and_validated` n'apporte rien. Vérifié sur huit cas
au total.

### Quand rien de mieux n'existe, `most_valid` rend exactement le brut

Tarascon, du 1er au 20 septembre 2026 : les deux passes rendent les mêmes 5 754
points, tous `s = 4`, avec **zéro écart de valeur**. C'est ce qui garantit
qu'une union des deux passes ne peut pas faire apparaître deux valeurs
différentes sous le même statut au même instant.

### `most_valid` mélange par période, jamais par horodatage

Point capital pour la forme du produit. Dépouillement des statuts mois par mois
à Tarascon, janvier 2025 à septembre 2026, 34 425 points :

```
2025-01  {16: 1212}           valide
2025-07  {16: 1994}           valide
2026-01  {16: 6, 12: 436}     frontiere, mois melange
2026-04  {12: 810}            pre-valide
2026-07  {12: 252, 4: 1363}   frontiere, mois melange
mois melangeant plusieurs statuts : 2 sur 21
```

Sur la Durance à Embrun, 1 mois sur 33. La chronique est **homogène par blocs** :
passé consolidé validé, période intermédiaire pré-validée, récent brut, et la
frontière avance avec le temps.

### La validation corrige les valeurs, elle ne fait pas que trier

Mars 2024 à Tarascon :

```
brut      8 928 points, pas median  5 min, codes s=4  q=16 m=8  c=0
valide      481 points, pas median 70 min, codes s=16 q=20 m=10 c=0
```

Les 481 horodatages validés sont tous présents dans le brut, mais **196 portent
une valeur différente**, écart relatif médian 0,444 % et maximal 2,871 %.

### La série validée est une courbe à points de rupture

Ce n'est pas « la série brute dont on aurait gardé les bons points », c'est la
courbe que l'hydromètre certifie, stockée par ses points de rupture. Vérifié
que `step` ne la sous-échantillonne pas : `step` 1, 5, 20 et 60 rendent les
mêmes 481 horodatages en mars 2024 à Tarascon.

**Brut et validé diffèrent donc en nature, pas seulement en qualité** : l'un est
un échantillonnage régulier, l'autre une courbe définie par des points de
rupture qu'il faut interpoler pour lire.

### La grille interpolée `Qln` perd les points de rupture

Conséquence directe, et elle disqualifie l'interpolation côté serveur. Mars 2024
à Tarascon, série validée :

```
Q   validated              481 points, les points de rupture reels
Qln validated, step=20   2 232 points, grille complete a 100 %
                           dont m=10 (EXP) : 105     m=8 (CAL) : 2 127
Qln validated, step=60     744 points   dont m=10 :  35
```

La grille ne retient que les points de rupture qui tombent sur ses bornes :
**105 sur 481 à 20 minutes, soit 78 % de perdus**, remplacés par de
l'interpolation. Demander la grille au serveur dégrade donc la donnée validée
au lieu de la servir.

## Les limites du service

### Le quota annoncé

Une demande trop large est refusée par un HTTP 400 portant un JSON :

```
{"hydro_series[endAt]":["Vous avez demande trop de donnees (527039 / 500000),
 merci de reduire la plage de temps ou de choisir une grandeur produisant
 moins de donnees."]}
```

527 039 = 366 x 1440 : le compte est **la durée en minutes divisée par le pas**,
pas le nombre réel de points. La fenêtre maximale annoncée vaut donc
`500 000 x pas` minutes.

### `step` ne veut pas dire la même chose selon la famille

**C'est le piège le plus dangereux rencontré sur cette source**, parce qu'il ne
casse rien : il rend simplement moins de données, sans le dire.

Dans la famille **instantanée**, `step` ne sous-échantillonne rien. Sur janvier
2024 à Tarascon, `step=1` et `step=20` rendent les mêmes 191 points aux mêmes
horodatages, et sur la série validée de mars 2024 les pas 1, 5, 20 et 60 rendent
les mêmes 481 horodatages. Le paramètre ne sert qu'au quota.

Dans la famille **journalière**, `step` est le **`n` du nom de la grandeur**.
`QIXnJ` se lit « débit instantané maximal **n** journalier », et le titre servi
par la réponse le dit : « (n=1, non glissant) ». Demander `QIXnJ` avec `step=20`
rend donc les maxima sur vingt jours, soit un vingtième des lignes.

```
QIXnJ most_valid, W011001001, toute la vie de la station
  step = 1     16 684 jours      la carte de couverture
  step = 20       728 jours      des maxima sur vingt jours
```

Rien dans la réponse ne signale la différence : mêmes colonnes, même forme,
juste moins de lignes. L'écart n'a été vu que parce qu'une valeur de référence
existait. **Pour toute grandeur journalière ou mensuelle, `step` doit rester à
1.**

Le quota, lui, ne s'applique pas de la même façon : une requête `QIXnJ` sur 126
ans avec `step=1` est servie sans protester, alors que la même largeur en
instantané serait refusée.

### `step` est borné à 30

« Le pas de temps doit être compris entre 1 et 30 », répond le formulaire en
HTTP 400. Comme c'est le pas qui achète du quota en famille instantanée, cette
borne plafonne la largeur d'une fenêtre à `30 x 500 000` minutes, soit **10 416
jours, environ 28 ans et demi**, quelle que soit la densité de la série.

### Les autres codes d'erreur

Un **HTTP 504** a été observé sur une fenêtre large d'une station sans données.
Contrairement au 500, il n'est pas systématiquement reproductible : il est
traité comme transitoire, avec un recul exponentiel, puis comme une fenêtre trop
large s'il persiste.

### La falaise HTTP 500

**Le quota n'est pas la vraie limite.** Mesuré à Tarascon en `raw`, `step=20` :

| fenêtre | quota consommé | points rendus | résultat |
|---|---|---|---|
| 1 an, 2024 | 26 352 | 105 209 | 200, 4,7 s |
| 2 ans, 2023-2024 | 52 632 | 210 108 | 200, 8,4 s |
| 4 ans, 2021-2024 | 105 192 | 419 461 | 200, 18,8 s |
| 6 ans, 2019-2024 | 157 788 | environ 630 000 | **500**, 25,7 s |
| 8 ans, 2017-2024 | 210 384 | environ 840 000 | **500**, 6,2 s |
| 19 ans, step=20 | 499 608 | | **500** |

Déterministe : le cas à 8 ans a été rejoué et a échoué deux fois de suite. La
falaise est entre 420 000 et 630 000 points rendus, alors que le quota
n'était consommé qu'au cinquième.

**Le mécanisme est pervers.** Puisque `step` ne sous-échantillonne pas le brut,
un grand pas fait *baisser le compteur de quota sans alléger la réponse* : il
trompe le garde-fou et fait accepter une requête que le serveur ne sait pas
produire. Un `step` élevé est donc dangereux, exactement à l'inverse de ce que
l'intuition suggère.

Conséquence pour le code : **un 500 veut dire « ma fenêtre est trop large », pas
« le serveur est en panne »**. Y répondre par un recul exponentiel et cinq
tentatives ferait replanter le service cinq fois.

### Le rythme soutenable, et pourquoi on ne l'a pas trouvé

Calibration du 21 septembre 2026. Requête témoin d'un mois de brut à Tarascon,
environ 8 900 points et 50 Ko gzippés, avec une fenêtre différente à chaque
appel pour ne pas mesurer un cache. Le délai entre requêtes vaut `k` fois le
temps de réponse précédent, et `k` décroît par paliers de cinq répétitions.

```
    k   median    min    max  req/min  verdict
  4.0    1.08s  0.98s  1.49s     11.1  sain
  3.0    1.01s  0.83s  1.57s     14.8  sain
  2.0    0.99s  0.89s  1.06s     20.2  sain
  1.5    0.95s  0.89s  1.69s     25.3  sain
  1.0    1.00s  0.90s  1.45s     30.0  sain
  0.5    1.03s  0.90s  1.56s     38.9  sain

reference initiale 1,21 s -> finale 0,98 s, soit -19 %
```

**Le temps de réponse reste plat de 11 à 39 requêtes par minute.** Le contrôle
de dérive va dans le même sens : la référence refaite en fin d'expérience est
plus rapide que celle du début, les 1,21 s initiales étant gonflées par
l'établissement de la connexion. Le palier réel est à une seconde.

**On n'a donc pas trouvé la limite polie, et cela ne prouve pas qu'elle
n'existe pas.** Ce qui a été mesuré est un client seul, sur des requêtes
moyennes, pendant quatre minutes. Rien n'est établi sur une charge soutenue
pendant des heures, sur les requêtes sept fois plus lourdes d'une campagne
réelle, ni sur ce que les autres usagers subissent pendant ce temps.

La conclusion utile est ailleurs : **le facteur limitant n'est pas le débit de
requêtes mais la taille des réponses**, dont la falaise est mesurée plus haut.
C'est ce qui justifie une règle indexée sur le service plutôt qu'un chiffre de
prudence, voir [DESIGN.md](DESIGN.md).

### gzip

Une station-mois de brut à Tarascon, mars 2024, 8 928 points :

```
Accept-Encoding: identity    2 679 271 octets
Accept-Encoding: gzip           48 911 octets      facteur 55
```

Soit 5,5 octets par point sur le fil. La compression est obligatoire, pas
optionnelle. Le JSON servi est mis en forme avec indentation, ce qui explique
à la fois les 300 octets par point non compressés et le facteur.

## Ce que contiennent réellement les chroniques

Mesures du 21 septembre 2026 sur le jeu de test. Elles corrigent plusieurs
généralisations tirées du seul cas de Tarascon.

### La carte de couverture, ou comment savoir avant de télécharger

**Le problème.** Pour savoir si une station porte des données utilisables, sur
quelle période et à quelle finesse, il faudrait les avoir téléchargées. Mais une
station représente jusqu'à plusieurs millions de points et une heure de
requêtes. On ne peut donc pas choisir quoi télécharger sans avoir déjà tout
téléchargé, ce qui est absurde et coûteux pour un service public gratuit.

**L'idée.** HydroPortail publie, à côté de la chronique instantanée, des
**résumés journaliers calculés à partir d'elle**. L'un d'eux, `QIXnJ`, est le
débit instantané maximal de chaque journée : une valeur par jour au lieu de 288.

Comme cette valeur est *dérivée* de la chronique instantanée, elle n'existe
**que les jours où celle-ci existe**. La demander revient donc à lire la table
des matières de la donnée au lieu de lire la donnée : on apprend le premier
jour, le dernier, quels jours manquent, et dans quel état de validation chacun
se trouve, sans jamais toucher aux points eux-mêmes.

**Le gain.** Toute la vie d'une station tient dans une requête de moins de deux
secondes et quelques milliers de points, là où la chronique correspondante en
compte des millions. À Tarascon, 11 217 points au lieu de plus de 3 millions.

**En pratique**, c'est la famille `daily_variable`, la grandeur `QIXnJ`, le
statut `most_valid` et une fenêtre couvrant toute la vie de la station. Le champ
`md` donne en prime l'instant où le maximum s'est produit.

Vérifié que sa présence implique bien celle de la chronique sous-jacente, y
compris aux dates les plus anciennes : W011001001 en janvier 1981 rend 299
points de Q, Y532501001 en décembre 1970 en rend 81. La table des matières ne
ment pas sur le contenu.

Une réserve à connaître : **la carte dit quels jours existent, pas à quelle
finesse**. Un jour présent peut porter 288 points ou 8. La densité réelle ne se
mesure qu'après téléchargement, et c'est pourquoi `couverture.csv` se remplit en
deux temps.

```
code           jours      debut        fin   couv   statuts (jours)
W011001001     16684 1981-01-01 2026-09-20  99.9%  {16:16422, 12:222, 8:38, 4:2}
W283201001      2510 2019-11-01 2026-09-20  99.8%  {4:1159, 16:732, 12:600, 8:19}
V271201001     16699 1981-01-01 2026-09-20 100.0%  {16:16437, 12:257, 8:5}
V720001002     11217 1994-12-01 2026-09-20  96.6%  {16:10954, 12:207, 4:56}
X031001001      5691 2010-04-03 2026-09-20  94.6%  {12:5672, 8:19}
Y532501001     19460 1970-12-24 2026-04-12  96.3%  {16:17896, 12:1552, 4:12}
W107403003      1886 2021-07-16 2026-09-20  99.6%  {4:1518, 8:368}
W107403001      3264 2011-06-02 2026-09-14  58.5%  {16:3232, 12:23, 8:8, 4:1}
W103000301         0          -          -         aucun debit instantane
V031661301         0          -          -         aucun debit instantane
```

Noter que le statut `raw` appliqué à `QIXnJ` ne rend que deux mois : pour les
grandeurs journalières, le brut n'est conservé que brièvement. C'est
`most_valid` qu'il faut demander pour la carte.

### Une sonde ponctuelle ne peut pas établir une absence

W107403001, l'Arc à Aiguebelle, rend zéro point de Q sur la semaine du 1er mars
2024, et son voisin W107403003 en rend 2 016. On en avait conclu qu'elle ne
portait que de la hauteur. La carte de couverture dit qu'elle porte **3 264
jours de débit instantané**, de 2011 à 2026, avec une couverture de 58,5 % : la
sonde était tombée dans un trou.

À l'inverse W103000301 et V031661301 n'ont réellement aucun instantané, et la
carte le **prouve** là où la sonde ne faisait que le suggérer.

### La profondeur de l'instantané

Bien plus grande que ce que Tarascon laissait croire : **1970** au Reyran à
Fréjus, **1981** à l'Isère à Moûtiers et à l'Ain à Pont-d'Ain, contre 1994 à
Tarascon.

### Mais le brut ne remonte qu'à 2013 ou 2014

Points bruts sur la première semaine de mars :

```
code           2000   2005   2010   2012   2014   2016   2018   2020
V720001002      760   1144   2015   2016    675    672   2015   2016
W011001001        0      0      0      0    168    336   1680   1680
V271201001        0      0      0      0    168    168   1679   1673
X031001001        0      0      0      0    672    349    672    669
Y532501001        0      0      0      0    672    672    672    672
W283201001        0      0      0      0      0      0      0   1680
```

Avant cela il n'existe que du validé, sauf à Tarascon qui a du brut depuis au
moins 2000. **Un téléchargement en `raw` seul rend donc zéro ligne sur toute la
période ancienne**, sur presque toutes les stations.

### La résolution varie d'un facteur 20, et pas monotonement

Pas médian sur le mois de mars à l'Isère à Moûtiers :

```
annee  brut pts   pas    most_valid pts   pas
 1981         0     -               314   101
 1990         0     -               533    36
 1995         0     -               767    29
 2000         0     -               656    45
 2005         0     -               453    45
 2010         0     -               788    15
 2015      1488    30               239    72
 2020      7439     6              1525    12
 2024      8906     5              5055     5
```

Le creux de 2015 n'est pas du bruit : le brut de Tarascon en fait un aussi,
5 min jusqu'en 2012, 15 min en 2014 et 2016, 5 min à nouveau ensuite. **Un pas
médian unique par station est donc une moyenne qui dit le contraire de la vérité
sur les deux bouts de la chronique.**

C'est la limite scientifique principale pour le sujet éclusées : la résolution
demandée, une heure ou moins, n'est pas tenue avant 2013 environ sur la plupart
des stations, et la courbe validée a été élaguée selon ce qui intéressait
l'hydromètre, qui n'est pas la variation infra-horaire. À Tarascon elle a un pas
médian de 70 minutes et ne décrit pas une éclusée ; à Moûtiers elle en a 5 055
points pour 8 906 bruts en mars 2024, donc elle la décrit. **Cela se décide
station par station et année par année.**

### Le poids sur disque, et le coût d'une campagne

Mesuré sur le jeu de test complet, les deux passes, écrit en parquet zstd
(21 septembre 2026) :

```
station       lignes     Mo   o/ligne   periode
V271201001  1 134 502   6,29     5,5    1981-01-01 a 2026-09-20
V720001002  2 825 465  14,73     5,2    1994-12-01 a 2026-09-20
W011001001  1 551 646   8,09     5,2    1981-01-01 a 2026-09-20
W107403001    506 331   2,99     5,9    2011-06-02 a 2026-09-14
W107403003    649 172   3,97     6,1    2021-07-16 a 2026-09-20
W283201001    781 976   5,35     6,8    2019-11-01 a 2026-09-20
X031001001    471 465   2,70     5,7    2010-04-03 a 2026-09-20
Y532501001    527 259   2,88     5,5    1970-12-26 a 2026-04-12
TOTAL       8 447 816  47,00
```

**Environ 5,5 octets par ligne**, les quatre colonnes de codes étant presque
constantes et les horodatages réguliers. Le cache des réponses pèse 38 Mo pour
le même jeu, soit moins que le produit.

Par extrapolation, **de l'ordre de 400 Mo pour 68 stations**, et non le
gigaoctet supposé. Le jeu de test penche vers les longues chroniques, donc
l'estimation est plutôt haute.

Coût de la campagne, mesuré sur ces huit stations :

```
duree            24 min 51 s          soit environ 3 min par station
CPU              8 %                  on attend le serveur, c'est voulu
memoire au pic   1,58 Go              une station a la fois, ne croit pas avec leur nombre
```

Soit **environ trois heures et demie pour 68 stations**, ce qui confirme l'ordre
de grandeur annoncé. La mémoire est le seul point de vigilance : elle est
dominée par la plus grosse station, Tarascon et ses 2,8 millions de lignes, et
une station beaucoup plus dense demanderait de traiter les fenêtres au fil de
l'eau plutôt que de les accumuler.

## Site et station

**Les chroniques vivent sur les stations.** Une station peut ne porter qu'une
partie des grandeurs, et le site est un regroupement.

L'Arc à Aiguebelle, site W1074030, porte trois stations dont le
`type_station` ne prédit rien d'utile :

```
W107403001  L'Arc a Aiguebelle                       type STD
W107403002  L'Arc a Aiguebelle - Barrage Aquabella   type DEB
W107403003  L'Arc a Aiguebelle - Debit               type DEB
```

`STD` ne veut pas dire « sans débit » : V720001002, qui porte le débit du Rhône
à Tarascon, est `STD`. Seule la mesure tranche.

Le Rhône à Tarascon, site V7200010, montre le revers : trois stations, deux
opérateurs, et des débits journaliers écartés de 6 % sur la même section.

```
QmnJ au niveau site, 1er janvier 2024
  station=None        1 744,3 m3/s     la serie de reference du site
  V720001001  CNR     1 854,1 m3/s     autre operateur, autre courbe de tarage
  V720001002  DREAL   1 744,3 m3/s     identique a la serie du site
```

**Sur HydroPortail, interroger le site ne duplique pas et ne fusionne pas** :
vérifié sur V7200010 en `most_valid`, 88 points, aucun horodatage en double, et
valeurs identiques à celles de V720001002. Le site rend simplement la série de
sa station de référence, **sans dire laquelle**. C'est cette opacité qui justifie
la règle, pas un risque de doublon.

**Règle retenue : interroger les stations, jamais les sites.** Mais résoudre
chaque code demandé vers son site, lister les stations soeurs, et dire laquelle
porte le débit. Une liste fournie par un tiers ne peut pas être prise au mot.

Le doublement, lui, existe bien mais **chez Hub'Eau** : `observations_tr`
interrogé avec un code de site renvoie chaque observation deux fois, une fois
attribuée à la station et une fois au site avec `code_station` nul. Vérifié,
8 594 horodatages, 8 594 doublons, aucun écart de valeur.

## Le jeu de test

Dix stations, choisies pour couvrir les cas plutôt que pour représenter le
réseau, et corrigées par la carte de couverture ci-dessus.

| code | cours d'eau et lieu | influence | ce qu'elle illustre |
|---|---|---|---|
| `W011001001` | Isère à Moûtiers | 3 | éclusée alpine, validé dense, brut depuis 2015 |
| `W283201001` | Drac au Pont-de-Claix | 3 | station récente, statuts très mélangés |
| `V271201001` | Ain à Pont-d'Ain | 3 | éclusée de plaine, couverture 100 % depuis 1981 |
| `V720001002` | Rhône à Tarascon, DREAL | 2 | grand fleuve régulé, seule à avoir du brut ancien |
| `X031001001` | Durance à Embrun | 1 | jamais de `s=16`, tout en pré-validé |
| `Y532501001` | Reyran à Fréjus | fermée | la plus longue, 1970, et fermée en 2026 |
| `W107403003` | Arc à Aiguebelle, Débit | 3 | site à trois stations, beaucoup de `s=8` corrigé |
| `W107403001` | Arc à Aiguebelle | 3 | **couverture trouée, 58,5 %** : le piège de la sonde |
| `W103000301` | Arc à Saint-Michel, Saussaz | 0 | aucun débit instantané, établi |
| `V031661301` | Dranse à Châtel | | aucun débit instantané, établi |

Le RRSE aurait été un choix naturel pour la partie faiblement influencée, mais
son code réseau n'a pas été identifié dans `code_sandre_reseau_station`, dont
les valeurs sont opaques (`POH900`, `BSH060`, `RIC300`). La Durance à Embrun
joue ce rôle en attendant.

## Refaire ces mesures

Aucune de ces valeurs ne doit être reprise sur parole si le service a changé.
La façon de les revérifier, avec le client d'exploration minimal :

```python
params = {
    "hydro_series[variableType]": "daily_variable",     # ou simple_and_...
    "hydro_series[dailyVariable]": "QIXnJ",             # ou Q en famille simple
    "hydro_series[statusData]": "most_valid",
    "hydro_series[step]": 1,
    "hydro_series[startAt]": "01/01/1900",
    "hydro_series[endAt]": "20/09/2026",
}
requests.get(f"https://hydro.eaufrance.fr/stationhydro/ajax/{code}/series",
             params=params, headers={"Accept-Encoding": "gzip"})
```

Les nomenclatures Sandre se relisent d'un coup :

```python
j = requests.get("https://api.sandre.eaufrance.fr/referentiels/v1/nsa.json").json()
{r["CdReferentiel"]: r for r in j["REFERENTIELS"]["Referentiel"]}["510"]["Element"]
```

**Risque assumé** : cette route n'est pas une API contractuelle, c'est le canal
interne d'une page web. Elle peut changer sans préavis. Elle sera isolée dans
`hydroportail/api.py` pour qu'une rupture reste la correction d'un seul fichier,
et `direct-export` reste documenté comme repli si le besoin d'un compte devient
inévitable.
