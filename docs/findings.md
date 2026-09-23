# Ce que nous avons constaté

Ce que les services interrogés font réellement, et ce que leur donnée contient,
établi par la mesure et non par la lecture de leur documentation. Ce fichier ne
contient que des faits et la façon de les revérifier. Ce qu'on a lu ailleurs est
dans [references.md](references.md), ce qu'on en déduit pour le produit dans
[design.md](design.md), ce qui reste à faire dans [ROADMAP.md](../ROADMAP.md).

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

### La validation retire les artefacts que le brut garde

W283201001, 27 novembre 2024 : un point brut isolé à 298 m³/s à 10:15, entre
deux valeurs à 16,3 m³/s cinq minutes avant et après. Le producteur l'a marqué
`q = 12`, douteux, quand ses voisins sont à `q = 16`. La série validée ne le
porte pas : son point de 10:40 vaut 16,3 m³/s, comme tout ce qui l'entoure.
Agrégé tel quel, ce point fait une moyenne de 63 m³/s sur son pas de quinze
minutes, soit une éclusée qui n'a pas eu lieu. Un cas, relevé en traçant des
journées d'exemple ; la fréquence de ces artefacts reste à mesurer.

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

### `QmnH` est l'intégrale de la courbe, sur l'heure qui suit l'horodatage

Mesuré le 23 septembre 2026, du 1er au 7 mars 2024, en comparant le `QmnH`
servi à des moyennes que nous calculons nous-mêmes sur la série `most_valid`
déjà téléchargée. La documentation du service dit seulement « moyenne des
débits instantanés », voir [references.md](references.md).

Écart relatif au `QmnH` servi, pour quatre manières de faire une moyenne
horaire, n = 1 :

```
                                    Tarascon V720001002      Embrun X031001001
                                    median   p95    max      median   p95    max
trapezes sur [t, t+1h]               0,12   0,31   0,42      0,06   0,21   0,64
trapezes sur [t-1h, t]               0,97   4,75   6,88      0,69   7,46  17,18
moyenne arithmetique des points      0,43   1,02   3,86      0,43   3,58   6,09
valeur interpolee a l'instant t      0,51   2,59   4,67      0,27   4,07   8,81
```

- **`QmnH` est une moyenne pondérée par le temps, calculée par la méthode des
  trapèzes**, c'est-à-dire la définition de l'OMM. Ni la moyenne arithmétique
  des points ni la lecture à l'instant ne la reproduisent.
- **L'horodatage est le début de l'intervalle** : la valeur de 00:00 est la
  moyenne de 00:00 à 01:00. La lecture inverse, que la documentation laisse
  ouverte, s'écarte jusqu'à 17 %.
- **Les valeurs servies sont arrondies à trois chiffres significatifs.** Les
  168 valeurs de Tarascon, de 1 980 000 à 3 330 000 l/s, sont toutes des
  multiples de 10 000 ; celles d'Embrun, de 46 500 à 66 700, des multiples de
  100. C'est un arrondi de 0,5 % au pire. L'écart restant avec notre calcul
  tient dans 0,9 unité de ce dernier chiffre, ce que l'arrondi explique à
  l'essentiel.
- **Le producteur intègre lui-même la courbe élaguée.** À Embrun, `most_valid`
  n'a sur cette semaine que 56 points pré-validés, un toutes les trois heures,
  et `QmnH` en donne 168 moyennes horaires qui concordent à 0,06 % en médiane
  avec leur intégrale. Il fait donc exactement ce que la lecture de la série
  validée comme courbe certifiée autorise.
- **`step` est le « n » du nom**, comme pour `QIXnJ` : `step=3` rend 56
  moyennes sur trois heures au lieu de 168, et le titre le dit, « n=3, non
  glissant ». Ce n'est pas un bouton de quota pour cette grandeur, alors
  qu'elle appartient à la famille instantanée.
- **`QmnH` n'existe pas en brut.** Le statut `raw` rend zéro point à Embrun sur
  une semaine où le brut compte 672 points. Il ne descend pas non plus sous
  l'heure. Il ne peut donc pas être un produit pour les éclusées, seulement la
  référence qui valide notre calcul.

Une première indication sur la tolérance de l'élagage, en attendant la mesure
complète : la moyenne horaire calculée sur le **brut** s'écarte du `QmnH` de
0,34 % en médiane et de 4,2 % au plus à Embrun, de 0,20 % et 0,84 % à Tarascon.
Cela reste sous les 5 % de la Banque Hydro, mais sur une semaine et deux
stations seulement.

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

### Le 500 qui ne parle pas de la fenêtre

Mesuré le 22 septembre 2026 sur `V126002001`, le Rhône à Ruffieux, rencontré en
préparant la liste demandée. Le service répond 500 quoi qu'on lui demande :

```
QIXnJ most_valid, annee 2020        500
QIXnJ most_valid, janvier 2024      500
Q     most_valid, deux jours        500
fiche d'identite de la station      200
V126002002, code inexistant         404
```

Le corps est la page d'erreur générique du site, « Une erreur est survenue,
l'application a rencontré une erreur », et non un message sur la fenêtre. Trois
choses en découlent :

- **Un 500 ne dit pas toujours « fenêtre trop large ».** La falaise mesurée plus
  haut reste vraie, elle n'est simplement pas la seule cause possible.
- **Un code inexistant répond 404**, donc un 500 ne dit pas non plus « cette
  station n'existe pas ». La fiche d'identité de celle-ci répond d'ailleurs 200.
- **Découper la fenêtre ne mène nulle part.** La descente de 46 286 jours à un
  seul a coûté quinze requêtes avant d'abandonner. En famille journalière, où
  toute la vie d'une station tient en 46 000 points, deux ordres de grandeur
  sous la falaise, la largeur ne peut pas être en cause : le code n'y découpe
  donc plus et rend l'erreur telle quelle.

Une station dans ce cas est hors de portée de l'outil tant que le service ne la
sert pas. C'est aussi pourquoi une campagne ne peut pas s'arrêter à la première
rencontrée : l'échec se note station par station, et la liste continue.

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
prudence, voir [design.md](design.md).

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
mesure qu'après téléchargement, et c'est pourquoi `coverage.csv` se remplit en
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

La liste demandée va plus loin encore, **1901** sur trois stations de l'Ardèche
et 1912 sur le Chassezac. Mais la nature de la donnée change avec l'âge, et il
faut le savoir avant de promettre quoi que ce soit sur cette période :

```
V501403001, Q most_valid
  mars 1901      1 point par jour, a 07:00              s=12 q=12 m=10
  janvier 1912   1 point par jour, a 07:00              s=12 q=12 m=10
  janvier 1960   jusqu'a 3 par jour, 07:00 12:00 17:00  s=12 q=12 m=10
  mars 2024      88 points en 3 jours, infra-horaire    s=16 q=20 m=10
```

Ce sont des relevés d'échelle saisis à la main, pré-validés et qualifiés
douteux, et non la chronique d'une sonde. La carte de couverture ne ment pas
pour autant, `QIXnJ` existe bien là où `Q` existe ; simplement un jour couvert
en 1901 porte une lecture de sept heures du matin, et le `md` de ces points,
l'instant du maximum, ne vaut que `00:00:00`, `07:00:00` ou `23:59:59`, ce qui
est la marque d'un remplissage.

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

### Ce qu'une grille régulière trouverait sous elle

Comptage du 22 septembre 2026 sur le `coverage.csv` du jeu de test, 341
couples station x année x statut, huit stations, 1970 à 2026. Les parts sont
pondérées par les jours de données, pour qu'une année de trois jours ne pèse pas
autant qu'une année pleine.

Part des jours dont le **pas médian** tient dans une grille donnée :

| statut | période | <= 15 min | 16 à 60 min | > 60 min | jours |
|---|---|---|---|---|---|
| brut | avant 2013 | 100 % | 0 % | 0 % | 6 275 |
| brut | 2013 et après | 88,8 % | 11,1 % | 0,1 % | 30 263 |
| validé | avant 2013 | 3,7 % | 44,8 % | 51,6 % | 35 699 |
| validé | 2013 et après | 37,9 % | 56,8 % | 5,3 % | 20 457 |

Le brut d'avant 2013 ne contredit pas la profondeur mesurée plus haut : il
n'existe qu'au Rhône à Tarascon, où il est à 5 minutes depuis 1994. Sur les sept
autres stations, la première année de brut est 2013, 2019 ou 2021.

Le **p90**, qui porte sur le pire décile, dit la même chose en plus sévère :

| statut | période | <= 15 min | 16 à 60 min | > 60 min |
|---|---|---|---|---|
| brut | avant 2013 | 45,9 % | 54,1 % | 0 % |
| brut | 2013 et après | 83,7 % | 16,0 % | 0,3 % |
| validé | avant 2013 | 0 % | 3,0 % | 97,0 % |
| validé | 2013 et après | 4,0 % | 28,3 % | 67,7 % |

Le pré-validé, présent sur sept des huit stations, est le plus grossier des
quatre statuts : 5 694 de ses 8 432 jours ont un pas médian supérieur à une
heure. Le corrigé est trop rare pour compter, 461 jours en tout.

Le pas médian de la série validée, par décennie et en station-années :

```
decennie  station-annees  pas median  dont <= 15 min
    1970              10     309 min               0
    1980              28     100 min               0
    1990              35      54 min               0
    2000              40      56 min               0
    2010              45      27 min              14
    2020              32      20 min              14
```

Ces chiffres ne disent pas qu'une grille de 15 minutes serait impossible avant
2013. La série validée est une courbe à points de rupture, qui se lit en
interpolant, et un pas médian de 100 minutes peut décrire fidèlement un débit
qui ne bouge pas. Ils disent qu'avant 2013 une telle grille serait remplie par
l'interpolation plutôt que par la mesure, et que le choix de l'accepter ou non
est une décision d'analyse et non un réglage. Voir [ROADMAP.md](../ROADMAP.md).

### Le pas du brut change au cours de la vie d'une station

« Le brut est à cinq minutes » n'est vrai que des années récentes. Pas médian
entre deux points bruts consécutifs, en minutes, lu dans le `coverage.csv` du
jeu de test le 23 septembre 2026 :

```
annees      V271201001  V720001002  W011001001  W107403001  X031001001  Y532501001
1994-2004            .           6           .           .           .           .
2005-2012            .           5           .           .           .           .
2013                60           5          60           3          15          15
2014                60          15          60          60          15          15
2015-2016           60     15 puis 5        30          30          15          15
2017-2021            6           5    6 puis 5      3 a 6           15          15
2022-2026            5           5           5           5          15          15
```

W283201001 et W107403003, dont le brut commence en 2019 et 2021, passent de 6 à
5 minutes. Trois lectures :

- **le pas se resserre par paliers**, de 60 à 30 puis 6 et 5 minutes sur l'Ain
  et l'Isère, et n'atteint cinq minutes qu'en 2021 ou 2022 ;
- **certaines stations ne descendent jamais sous quinze minutes**, Embrun et
  Fréjus depuis le début de leur brut ;
- **la médiane annuelle cache ce qui se passe dans l'année.** À Tarascon de
  1994 à 2004, la médiane est de 6 minutes mais le p90 de 30 : un écart sur dix
  dure une demi-heure ou plus.

C'est le pas **stocké** qu'on lit ici. L'instrument peut mesurer plus souvent
et ne stocker qu'une valeur sur plusieurs, la donnée ne permet pas de le savoir.

### Ce que chaque pas de sortie garde du brut

Le critère qui répond à la règle « ne jamais agréger plus fin que la mesure »
se juge **pas par pas, et non par année** : un pas de sortie de durée D est
porté par le brut quand aucun écart entre deux points bruts consécutifs qui le
chevauche ne dépasse D. Il n'y a alors aucune rupture de régime à détecter, les
changements en cours d'année sont pris en compte d'eux-mêmes, et une valeur
agrégée ne repose jamais sur un intervalle que le capteur a sauté.

Part des pas de chaque année civile ainsi portés, mesurée le 23 septembre 2026
sur le jeu de test, en % :

```
                    sortie a 15 min          sortie a 30 min          sortie a 60 min
                  2013 2015 2017 2019 2024  2013 2015 2017 2019 2024  2013 2015 2017 2019 2024
V271201001 Ain       0    0   48   99  100     0    0   48   99  100    10  100   99   99  100
V720001002 Rhone   100  100  100   99  100   100  100  100  100  100   100  100  100  100  100
W011001001 Isere     0    0   16   98  100     0   98   95   98  100    11  100   95   99  100
W107403001           1    0   16   87    6     1   98  100   87    6    12  100  100   87    7
X031001001 Durance  12   53   92   98   69    12   53   92   99   59    12   50   91   98   99
Y532501001 Frejus   11  100   98   99  100    11  100   98   99  100    11   99   98   99  100
```

Tarascon est porté à 74 % ou plus dès 2005 à quinze minutes, à 88 % ou plus à
trente. Une année partielle, 2013 pour la plupart, et 2026 qui plafonne à
72 %, ne dit rien du pas. Ce que le tableau montre :

- **le pas de sortie décide de la part de chronique qu'on garde sans rien
  inventer.** L'Ain n'est porté à trente minutes qu'à partir de 2018, mais à
  une heure dès 2014 ; l'Isère gagne trois ans en passant de quinze à trente
  minutes ;
- **un trou se voit aussi bien qu'un pas grossier.** W107403001, dont le brut
  est à cinq minutes, tombe à 0 % de 2020 à 2023 parce que sa couverture est
  trouée ; Embrun perd un tiers de ses pas de quinze minutes en 2024 et 2025 par
  des écarts de trente à quarante-cinq minutes, qu'une heure absorbe.

Ce critère ne vaut que pour le brut. La série validée est une courbe certifiée
à une tolérance près et ne se juge pas sur l'écart entre ses points, voir
« La série validée est une courbe à points de rupture » plus haut et
[references.md](references.md).

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

Par extrapolation, **de l'ordre de 6 Mo par station**, soit environ 300 Mo pour
une cinquantaine, et non le gigaoctet supposé. Le jeu de test penche vers les
longues chroniques, donc l'estimation est plutôt haute.

Coût de la campagne, mesuré sur ces huit stations :

```
duree            24 min 51 s          soit environ 3 min par station
CPU              8 %                  on attend le serveur, c'est voulu
memoire au pic   1,58 Go              une station a la fois, ne croit pas avec leur nombre
```

Soit **environ deux heures et demie pour une cinquantaine de stations**, ce qui
confirme l'ordre de grandeur annoncé.

La mémoire n'est pas une contrainte. Le pic vient de la plus grosse station et
non de leur nombre, puisqu'elles sont traitées une par une, et vaut environ 560
octets par ligne pendant la fusion. Saturer une machine de 16 Go demanderait
donc **une seule station d'environ 28 millions de points**, soit 350
station-années au pas de 5 minutes qui est la norme. Le cas n'existe pas en
pratique. Si un jour il se présentait, le remède connu est d'écrire les fenêtres
au fil de l'eau au lieu de les accumuler.

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

### Ce qu'une liste réelle a donné

Mesuré le 22 septembre 2026 sur les 51 codes de la demande, dont 45 codes de
site, résolus par Hub'Eau puis sondés un par un avec la carte de couverture.

```
51 codes demandes           45 de site, 6 de station
84 stations candidates      1,6 par code demande
 6 refusees par le service  4 en 500, 2 en 404
47 stations retenues
 4 codes sans station       2 absences etablies, 2 non etablies faute de sondage
```

**Douze des 45 codes de site ne désignent pas la station `<site>01`.** Huit
portent leur débit sur une autre station du site, quatre n'en ont aucune qui en
porte. Ajouter « 01 » à un code de site, qui est le réflexe naturel, se serait
donc trompé une fois sur quatre.

Quatorze sites ont plusieurs stations portant du débit, et leurs libellés disent
pourquoi : le site nu d'un côté, de l'autre des variantes suffixées par
l'exploitant (`- EDF`, `- DREAL`, `- DIREN`), par l'instrument (`- Limnimètre`,
`- Débitmètre`) ou par l'usage (`- Échelle Annonce de Crues`). Le suffixe ne dit
pas laquelle est la bonne, et l'écart de contenu va jusqu'au facteur cent : à
Pégomas, une station porte 19 932 jours et sa voisine 224.

**Ce que les 47 stations retenues contiennent**, inventorié le 22 septembre 2026
sans télécharger une seule chronique :

```
47 stations, toutes portent du debit instantane
416 542 jours, 1 374 station-annees, 1 449 lignes de couverture
profondeur mediane  5 979 jours, soit seize ans
la plus profonde    24 736 jours, l'Ain a Chazey-sur-Ain depuis 1959
4 stations sous 1 000 jours, 8 sous 60 % de couverture
statuts (lignes)    {4: 97, 8: 21, 12: 252, 16: 1079}
```

Par extrapolation du coût mesuré plus bas, la campagne complète pèse de l'ordre
de **280 Mo et deux heures et demie**. La moitié basse de la liste n'existe que
depuis 2013 ou après, ce qui recoupe la date d'apparition du brut.

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
