# Ce que le logiciel fait, et pourquoi

Les choix de conception et leurs raisons. Les faits qui les fondent sont dans
[SOURCE.md](SOURCE.md) et ne sont pas recopiés ici : ce fichier y renvoie. Ce
qui n'est pas encore tranché est dans [ROADMAP.md](ROADMAP.md).

Tout ce qui suit est tranché. Ce fichier sera replié dans le `README.md` en
phase 6, quand le code existera : sa matière est celle des sections « Choix
techniques » et « Ce qu'il faut savoir avant d'analyser » des dépôts voisins,
écrite avant le logiciel plutôt qu'après.

## La demande, et le périmètre de la v1

Une équipe travaille sur les cours d'eau à éclusées et a besoin des débits de
68 stations en Rhône-Méditerranée-Corse, sur toute la durée des chroniques, à
une résolution d'une heure ou moins et à pas de temps régulier. La liste des
stations est détenue par l'équipe demandeuse.

**Le périmètre de la v1 est plus étroit que la demande, et c'est délibéré.** La
v1 rapatrie la donnée telle que HydroPortail la diffuse, à son pas natif, pour
la rendre réutilisable dans l'unité. Le rééchantillonnage à pas régulier est
une seconde étape, parce que la question est statistique avant d'être technique.

**On prend tout, et la variabilité n'est pas un défaut.** Que la quantité et la
qualité varient dans le temps et d'une station à l'autre est le principe même
de la donnée hydrométrique, pas une anomalie de cette source ni une limite à
excuser. La résolution n'est pas la même avant 2013 qu'après, le brut n'est pas
aussi profond que le validé, et une station peut être trouée : ce sont des
caractéristiques, elles se documentent.

Le rôle du logiciel s'arrête là. **Il livre toute l'information qui permet de
décider, et ne décide jamais à la place du chercheur** : c'est l'expertise
croisée au besoin qui tranche ce qui est utilisable, et elle ne peut le faire
que si elle voit ce qu'elle manipule. D'où la table de couverture, les quatre
codes de qualité conservés par point, et l'absence de tout filtrage par défaut.

## Deux passes de téléchargement, `raw` et `most_valid`

Elles suffisent à tout prendre, parce que `most_valid` contient
`pre_validated_and_validated` point pour point et qu'un horodatage ne porte
jamais deux niveaux validés concurrents.

La troisième passe n'est donc pas téléchargée, mais **l'inclusion est
contrôlée** sur un échantillon de stations plutôt que tenue pour acquise sur
huit cas : si elle casse un jour, on l'apprend par le contrôle et non au milieu
d'une analyse. Ce contrôle demande d'interroger `pre_validated_and_validated`,
ce qui est la seule raison pour laquelle le code sait encore le faire.

**Ne rien reconstruire est le choix central.** L'arbitrage entre niveaux de
qualité appartient au producteur, qui sait quelle période il a certifiée. Le
refaire ici supposerait d'inventer une règle de découpage en périodes, donc
d'affirmer ce que la source ne dit pas. La passe `most_valid` est donc
téléchargée telle qu'elle est servie, jamais recalculée.

Le corollaire est qu'**une fusion par horodatage ne sera pas produite**. Elle
donnerait à Tarascon en mars 2024 une série de 8 928 points dont 481 corrigés et
8 447 non corrigés, ni brute ni validée, avec des discontinuités là où les deux
alternent. Cet objet là n'a pas de sens.

### Ne pas tout télécharger : `--statuts`

Les deux passes n'ont pas le même coût, dans un rapport de 1 à 17 à Tarascon
sur 2024 : 105 209 points bruts contre 6 077 en plus valides. Une option permet
de ne prendre que ce dont on a besoin :

```
--statuts most_valid     la chronique arbitree par le producteur, seule
--statuts raw            le signal brut seul
--statuts les-deux       defaut, complet sur tout ce qui est publie
```

**Aucune des deux ne se suffit à elle-même, et le choix dépend de la question.**
Pour un usage hydrologique courant, `most_valid` suffit largement et divise le
téléchargement par dix ou plus. Pour le sujet éclusées, il **ne suffit pas** sur
les stations où la courbe validée a été élaguée au delà de l'heure. Et pour les
périodes anciennes, `raw` ne rend **rien du tout** sur presque toutes les
stations, puisque le brut ne remonte qu'à 2013 ou 2014.

C'est la table de couverture qui permet de choisir avant de lancer, et c'est une
des raisons pour lesquelles elle est le premier livrable.

## Ce que la v1 livre

```
donnees_hydroportail/
├── stations.csv       csv       une ligne par code demande, identite et bornes
├── couverture.csv     csv       station x annee x statut, de quoi decider
├── ref_codes.csv      csv       vocabulaire de s, q, m, c, engendre depuis Sandre
├── mesures/           parquet   la table de faits, un fichier par station
├── datapackage.json   json      schema, provenance, empreintes sha256
└── .sources/          json.gz   cache des reponses recues, ignore par git
```

**Une seule table de faits**, et trois tables de référence qui disent comment la
lire. Tout le reste s'en déduit.

## La table de faits

**Une ligne par point publié.** Rien d'autre.

```
code_station  date_obs              debit_m3s  statut  qualification  methode  continuite  most_valid
V720001002    2024-03-01T04:35:00Z   2140.000       4             16        8           0  false
V720001002    2024-03-01T04:35:00Z   2150.000      16             20       10           0  true
V720001002    2024-03-01T04:40:00Z   2160.000       4             16        8           0  false
V720001002    2026-09-15T10:00:00Z   1050.000       4             16        8           0  true
```

Les deux premières lignes sont le même instant en deux versions, la brute et la
validée. La dernière est le cas qui se lit mal sans l'avoir vu une fois : en
2026 rien de mieux que le brut n'existe, donc `statut = 4` et `most_valid` vrai
sur la même ligne.

| colonne | type | d'où elle vient |
|---|---|---|
| `code_station` | texte | la demande |
| `date_obs` | horodatage ms UTC | `t` |
| `debit_m3s` | flottant | `v`, divisé par 1000 |
| `statut` | entier 8 bits | `s`, nomenclature Sandre 510 |
| `qualification` | entier 8 bits | `q`, nomenclature Sandre 515 |
| `methode` | entier 8 bits | `m`, nomenclature Sandre 512 |
| `continuite` | entier 8 bits | `c`, nomenclature Sandre 923 |
| `most_valid` | booléen | la passe qui a rendu le point |

Le champ `md` de la source n'est pas repris : il est toujours nul pour le Q
instantané. Il faudra le traiter le jour où une grandeur journalière sera
ajoutée.

### Pourquoi le format long

Une variante plus compacte avait été envisagée, une ligne par horodatage avec
une colonne compagnon `debit_brut_m3s` à côté de la valeur retenue. **La mesure
l'a écartée** : `s` prend au moins quatre valeurs dans la nature (4, 8, 12, 16),
pas deux, et les quatre codes ne se déduisent pas l'un de l'autre. Une colonne
compagnon par niveau ne généralise donc pas.

Le format long est le seul qui absorbe ces cas sans être réécrit, et qui
absorbera un cinquième code si Sandre en ajoute un. Une ligne veut toujours dire
la même chose : une valeur publiée par HydroPortail, avec ses quatre codes.
Aucune colonne dont le vide signifierait deux choses, aucune colonne dont
l'existence dépendrait du nombre de niveaux.

Le coût est la redondance des horodatages publiés à plusieurs niveaux. Sur
parquet, où ces colonnes sont très répétitives, l'occupation croît beaucoup
moins que le nombre de lignes : mesuré à 8,2 octets par ligne en zstd.

### La clé de dédoublonnage

Les deux passes se recouvrent partiellement, puisque `most_valid` rend les mêmes
points bruts que `raw` sur les périodes récentes. L'union est donc dédoublonnée,
et `most_valid` vaut vrai dès que l'une des passes l'a rendu.

**Dédoublonner sur la ligne entière plutôt que sur `(code_station, date_obs,
statut)`.** Les deux donnent le même résultat sur les cas mesurés, mais la
seconde suppose que deux niveaux portent toujours deux statuts différents, ce
qui est vrai pour `s` et pas pour `q` : une même série brute mêle `q=16` et
`q=12`. La clé complète ne coûte rien et ne suppose rien.

### Un fichier parquet par station

```
mesures/
├── V720001002.parquet
├── W011001001.parquet
└── ...
```

`code_station` reste une vraie colonne à l'intérieur, donc un fichier isolé se
lit seul et se transmet seul, pendant que le dossier entier s'ouvre d'un coup
comme un jeu unique avec `pyarrow` comme avec `arrow` en R. La colonne étant
constante dans un fichier, le parquet la réduit à presque rien.

Le découpage par station est aussi celui des empreintes sha256, donc une par
station, ce qui rendra directement mesurable au passage suivant quelles stations
ont bougé. Le découpage par fenêtre de téléchargement ne remonte pas jusqu'au
disque : il vit dans `.sources/`.

## Une seule table, pas deux

Le plan initial prévoyait un second dossier `chronique/`, la passe `most_valid`
seule, une ligne par horodatage, pour le confort de relecture. **Il est
abandonné.**

Par construction `chronique/` vaut exactement `mesures[most_valid]` : c'est une
vue, pas une table. La stocker doublerait le disque et créerait une surface
d'incohérence pour une information déjà présente. L'analogie avec
`onde_full.parquet` du dépôt voisin ne tenait pas : celui-ci est une
**jointure** de quatre tables et épargne un vrai travail, alors qu'ici il se
serait agi d'un **filtre** sur une colonne d'une seule table.

**La contrepartie est à la charge du README**, et elle n'est pas négociable : si
la chronique propre n'est plus un fichier, il faut qu'elle soit évidente à
obtenir. Le README doit donner, dès sa section de relecture et avant toute
considération savante, les deux lignes qui la produisent :

```python
import pandas as pd
mesures = pd.read_parquet("donnees_hydroportail/mesures/")
chronique = mesures[mesures.most_valid]
```

```r
library(arrow)
mesures <- read_parquet("donnees_hydroportail/mesures/")
chronique <- mesures[mesures$most_valid, ]
```

et dire en une phrase ce que cette chronique est : la donnée arbitrée par le
producteur, homogène par blocs, qui convient à la plupart des usages
hydrologiques. Le reste de `mesures/` sert à ceux qui ont besoin de descendre
au brut, et le README doit dire comment savoir si on en a besoin, en renvoyant
à la table de couverture.

## Le référentiel

### `stations.csv`

Une ligne par code demandé, y compris ceux qui ne portent aucun débit :

- l'identité venue de Hub'Eau : libellé, cours d'eau, coordonnées, altitude,
  dates d'ouverture et de fermeture, opérateur, influence ;
- la résolution site/station : code du site, stations soeurs, laquelle porte le
  débit ;
- les bornes réelles de l'instantané et le taux de couverture, obtenus par la
  carte `QIXnJ` sans rien télécharger de lourd.

### `couverture.csv`

Le plan initial mettait un `intervalle_median_min` unique par station dans
`stations.csv`. La mesure montre que la résolution varie d'un facteur 20 au
cours de la vie d'une station, et pas monotonement : un chiffre unique dit donc
le contraire de la vérité sur les deux bouts de la chronique.

C'est donc une table à part, **une ligne par station, année et statut**, et
elle se remplit en deux temps.

| colonne | ce qu'elle dit | remplie |
|---|---|---|
| `code_station` | | inventaire |
| `annee` | | inventaire |
| `statut` | le code `s`, parce que brut et validé n'ont pas la même densité | inventaire |
| `jours_avec_donnees` | les trous, qu'un pas médian ne montre jamais | inventaire |
| `nb_points` | le volume réel | après téléchargement |
| `intervalle_median_min` | la résolution courante | après téléchargement |
| `intervalle_p90_min` | la résolution dans le pire décile, donc l'irrégularité | après téléchargement |

Sept colonnes, et chacune répond à une question qu'un analyste se pose avant de
lancer un calcul. Elle reste petite : environ 7 000 lignes pour 68 stations sur
toute leur vie.

**Les quatre premières colonnes s'obtiennent sans rien télécharger de lourd**,
par la carte `QIXnJ` décrite dans [SOURCE.md](SOURCE.md), à raison d'une requête
de deux secondes par station. Les trois dernières demandent la donnée elle-même
et restent vides tant qu'elle n'a pas été téléchargée.

**Un seul fichier, rempli progressivement**, plutôt que deux fichiers qui se
ressembleraient. Une colonne vide veut dire une seule chose, « pas encore
mesuré », et jamais « mesuré à zéro » : `jours_avec_donnees` à 0 signifie qu'il
n'y a rien cette année là, alors qu'un `nb_points` vide signifie qu'on n'a pas
regardé. Un run partiel donne donc un fichier partiellement complété, ce qui est
exactement l'information vraie.

C'est ce qui permet de rendre un tableau de ce qui existe sur une liste de
stations **avant** d'engager le téléchargement, pour que le demandeur dise ce
qu'il veut vraiment plutôt que de recevoir un gigaoctet à trier.

**Pourquoi ces trois indicateurs et pas un seul.** Sur l'Isère à Moûtiers, la
médiane seule raconte une histoire fausse à deux endroits : en 2015 elle
remonte à 72 minutes alors que les années encadrantes sont à 15 et 12, et une
médiane de 5 minutes sur une année à 200 jours de données ne dit pas que le
tiers de l'année manque. Le couple médiane et p90 sépare une série régulière
d'une série qui alterne rafales et silences, et `jours_avec_donnees` sépare une
chronique dense d'une chronique trouée.

C'est cette table qui répond à la seule question qui compte pour le sujet
éclusées : **cette station, cette année là, décrit-elle une éclusée ?** Elle ne
répond pas à sa place : elle lui donne de quoi trancher.

### `--inventaire`, avant de télécharger

Comme chez les voisins, `--inventaire` interroge la carte de couverture et
s'arrête, sans toucher aux chroniques. Il affiche un résumé et **écrit
`stations.csv` et les colonnes d'inventaire de `couverture.csv`**, de sorte que
son résultat se transmette et se discute au lieu de défiler à l'écran.

C'est ce qui permet de voir ce qu'une liste de codes contient réellement avant
d'engager une campagne : combien ne portent aucun débit instantané, lesquels
sont des codes de site, quelle profondeur et quels trous chacun offre.

### `ref_codes.csv`

**Pourquoi il existe.** Chaque point arrive avec quatre nombres collés dessus,
`s`, `q`, `m` et `c`. Sans nomenclature ce sont quatre entiers opaques ; avec
elle, ce sont quatre informations de qualité fournies par le producteur.

Le cas qui montre l'enjeu est `q = 12`, qui veut dire **« douteuse »** : le
producteur signale lui-même ce point comme suspect. Sur septembre 2026 à
Tarascon, 2 018 des 5 754 points bruts le sont, soit 35 %. Une analyse qui
calcule des gradients d'éclusée sur la série brute les avalerait tous sans le
savoir, parce que dans le fichier ce n'est qu'un `12` dans une colonne.
`ref_codes.csv` est ce qui rend cette information lisible ; sans lui, autant ne
pas livrer les colonnes.

**Sa forme.** Une ligne par valeur : `type` (`s`, `q`, `m`, `c`), `code`,
`libelle`, `definition`, `nomenclature_sandre`, `source`. Les quatre
nomenclatures sont 510, 515, 512 et 923, et le piège des nomenclatures
homonymes est documenté dans [SOURCE.md](SOURCE.md) : l'appariement se fait sur
les valeurs de code, jamais sur le titre.

**La table est figée dans `schema.py`**, pas rapatriée à chaque exécution.
Vingt lignes qui bougent tous les dix ans ne justifient pas de dépendre d'un
troisième service à chaque lancement, ni qu'une panne du Sandre casse un
téléchargement HydroPortail. C'est aussi ce que fait le dépôt voisin ONDE avec
son vocabulaire d'écoulement.

La contrepartie est que **le contrôle final signale tout code absent de la
table**. C'est le seul moment où l'on a besoin d'apprendre qu'une nomenclature a
bougé, et cela arrive alors comme un avertissement explicite plutôt que comme un
libellé vide.

## Le cache des réponses, `.sources/`

Les réponses JSON gzippées telles que reçues, une par requête, donc une par
station, passe et fenêtre :

```
.sources/V720001002/2024_raw.json.gz
.sources/V720001002/2024_most_valid.json.gz
```

L'année sert d'unité de compte mais **n'est pas imposée par l'API**, et le nom
des fichiers suivra la fenêtre réellement retenue.

Même rôle que `donnees_vigieau/.sources/` chez le voisin : reconstruire les
tables sans retélécharger, ce qui compte double ici puisque chaque passage coûte
de la bande passante à HydroPortail. Il porte aussi la trace de ce qui a été
servi à une date donnée, seul moyen de constater plus tard qu'une révision de
courbe de tarage a réécrit le passé. Ignoré par git, effaçable.

## Le fenêtrage des requêtes

La règle vient de la falaise HTTP 500, pas du quota annoncé.

1. **Viser environ 100 000 points par réponse**, ce qui vaut une station-année
   de brut à 5 minutes, environ 5 secondes et 570 Ko sur le fil. C'est
   confortablement sous la falaise, mesurée entre 420 000 et 630 000 points.
2. **Garder `step` petit.** Un grand pas abaisse le compteur de quota sans
   alléger la réponse, donc il fait accepter des requêtes que le serveur ne sait
   pas produire. Il ne sert à rien d'autre qu'au quota, puisqu'il ne
   sous-échantillonne pas.
3. **Sur un 500, couper la fenêtre en deux et réessayer**, jamais reculer
   exponentiellement : un 500 dit « trop gros », pas « en panne ». Un recul
   exponentiel à cinq tentatives ferait replanter le service cinq fois.
4. **Sur 429 et 503, reculer exponentiellement**, et s'arrêter franchement après
   quelques échecs consécutifs.

## Politesse envers HydroPortail

Aucune règle publiée n'encadre l'accès automatisé, donc les règles sont fixées
ici, et elles sont mesurées.

1. **gzip systématique.** Facteur 55 sur la bande passante. Non négociable.
2. **Une requête à la fois**, aucun parallélisme, jamais. C'est la règle qui
   protège réellement le service.
3. **Temporisation adaptative**, au moins aussi longue que la requête
   précédente a mis à répondre. Une réponse lourde ou un serveur qui peine nous
   ralentissent alors automatiquement, ce qu'un délai fixe ne sait pas faire.
   Le plancher n'est pas choisi au jugé mais **calibré par la mesure**, voir
   ci-dessous.
4. **Un peu d'aléatoire**, de l'ordre de 20 %, pour lisser la charge. La raison
   est le lissage, pas le camouflage : chercher à passer pour un humain serait
   de l'évasion, et c'est précisément ce qui ferait ressembler un usage légitime
   à un usage qui se cache. On fait l'inverse, on se rend identifiable.
5. **Le fenêtrage ci-dessus**, qui est autant de la politesse que de la
   robustesse : ne jamais être celui qui fait tomber le service.
6. **Reprise sur disque**, pour qu'une interruption ne fasse jamais
   retélécharger ce qui est déjà là.
7. **Campagnes longues hors heures ouvrées.**

### Calibrer le rythme plutôt que le deviner

Un plancher de deux secondes serait un chiffre arbitraire, ni prudent ni
efficace, juste inventé. Le rythme de croisière est donc **mesuré en phase 2**,
par une expérience courte et bornée dont le résultat part dans
[SOURCE.md](SOURCE.md) comme n'importe quelle autre mesure.

**Le principe : on cherche le point de fonctionnement sûr, pas le point de
rupture.** Il n'est pas nécessaire de faire plier un service pour savoir à
quelle allure il est à l'aise. Le protocole mesure le temps de réponse d'une
requête identique à cadence décroissante, et **s'arrête au premier signe de
fatigue** plutôt que de continuer jusqu'à l'échec :

```
requete temoin identique, repetee, en faisant varier le delai entre requetes
  delai genereux        -> temps de reponse de reference
  on resserre par paliers
  des que le temps de reponse s'ecarte de la reference     -> on s'arrete
  rythme retenu = dernier palier sain, avec une marge confortable
```

La falaise HTTP 500 a déjà été rencontrée une fois, involontairement, et elle a
suffi à nous apprendre ce qu'il fallait savoir. **On n'en cherche pas une
seconde.**

Cette calibration est aussi ce qui permet d'annoncer honnêtement la durée d'une
campagne complète, de l'ordre de quelques heures pour 68 stations, plutôt que de
la subir.

### Ce que le README doit dire à l'utilisateur

La politesse ne peut pas être entièrement dans le code, puisque c'est
l'utilisateur qui choisit quand et combien il lance. Le README doit donc porter,
comme des recommandations et non comme des contraintes techniques :

- **lancer les campagnes longues la nuit ou le week-end**, hors heures ouvrées ;
- **ne jamais lancer plusieurs exécutions en parallèle** pour aller plus vite,
  ce qui annulerait d'un coup toutes les précautions du code ;
- **commencer par `--inventaire`**, puis ne télécharger que ce dont on a besoin
  avec `--statuts`, plutôt que de tout prendre par défaut et de trier après ;
- **garder le cache `.sources/`**, qui évite de redemander au service ce qu'il a
  déjà donné ;
- et dire en une phrase que cette source est **un service public gratuit sans
  contrepartie**, dont la capacité est finie et partagée avec tous les autres
  usagers.

### Comment s'identifier sans exposer qui que ce soit

Le `User-Agent` doit dire **quel logiciel appelle et où le trouver**, pas qui est
derrière le clavier :

```
get-data-hydroportail/1.0 (+https://github.com/lou-heraut/get-data-hydroportail-debit-instantane)
```

L'URL du dépôt porte déjà le moyen de joindre quelqu'un, sans diffuser une
adresse à chaque requête. Un courriel dans un en-tête est une donnée personnelle
envoyée à un tiers et journalisée chez lui, ce qui n'a pas à être le défaut. Et
la valeur ne change pas d'un utilisateur à l'autre, donc ce qui est déclaré
reste vrai quel que soit celui qui lance le script.

**Rien n'est collecté automatiquement** : ni l'adresse du dépôt git local, ni
l'utilisateur du système, ni le courriel de la configuration git. Le déduire
reviendrait à publier l'identité de quelqu'un sans son accord.

Pour qui veut se signaler nommément, une variable d'environnement facultative
ajoute un contact, et elle seule :

```bash
export HYDROPORTAIL_CONTACT="prenom.nom@inrae.fr"
```

### Est-ce que c'est une faille

Non, et c'est tranché par écrit plutôt que laissé en malaise diffus.

Une faille, ce serait contourner une authentification, atteindre une donnée qui
n'est pas destinée au public, ou détourner un paramètre pour sortir du périmètre
prévu. Rien de tout cela ici : la route sert exactement ce que la page affiche à
n'importe quel visiteur anonyme, avec les mêmes paramètres que le formulaire à
l'écran, et les quatre statuts sont les quatre boutons de ce formulaire. Quand
l'instruction a rencontré la voie réservée, `direct-export`, celle-ci a renvoyé
la page de connexion et on s'est arrêté là : le contrôle d'accès a fonctionné et
il a été respecté.

**L'absence de `robots.txt` ne veut rien dire.** Ce fichier encadre l'indexation
par les moteurs de recherche, pas l'accès aux données. Un 404 signifie qu'aucune
directive n'existe, ce qui n'est ni une autorisation ni une interdiction.

**En revanche le service est bel et bien fragilisable**, et la falaise à 500 le
démontre : une requête un peu trop large suffit à le faire échouer. Ce n'est pas
un défaut de sécurité, c'est une caractéristique de capacité. La conclusion
n'est pas de s'interdire l'usage, c'est de dimensionner les fenêtres pour ne
jamais s'en approcher.

**Le compte HydroPortail est écarté.** Il aurait ouvert `direct-export` et son
CSV, mais le gain est illusoire une fois gzip actif : on est déjà à 5,5 octets
par point sur le fil. Le seul gain réel serait pour le serveur, qui fabriquerait
moins de texte avant de le compresser. C'est mince au regard du coût, un dépôt
inutilisable sans identifiants.

**Un courriel au SCHAPI n'est pas nécessaire à ce stade.** Le `User-Agent`
nominatif est la forme proportionnée de la déclaration. La question se reposera
avant la campagne complète sur les 68 stations, où un message devient une
assurance bon marché.

## Ce que le README devra dire, plutôt que ce que le script déciderait

**Aucun filtrage de qualité n'est appliqué par défaut, et il n'y en aura pas.**
Le produit complet sort avec ses horodatages répétés et ses quatre codes, et le
README porte les avertissements :

- mélanger les statuts **par période** a un sens, c'est ce que fait le
  producteur ; les mélanger **par horodatage** n'en a pas ;
- la série validée est une **courbe à points de rupture**, pas un
  échantillonnage : la lire sans interpoler sous-échantillonne sans le dire ;
- la série brute est un échantillonnage régulier mais **non corrigé**, et son
  pas a varié au cours du temps ;
- **`qualification = 12` veut dire « douteuse »**, et cela concerne une part
  importante du brut récent ;
- descendre d'un cran de statut sur une période donnée est légitime et attendu,
  c'est même l'usage principal de la table de faits ;
- la résolution utile se décide **station par station et année par année**,
  d'où la table de couverture.

### À qui sert quoi

```
besoin                                        ou regarder
savoir si une station convient                stations.csv puis couverture.csv
chronique propre directement exploitable      mesures[most_valid]
selection personnalisee sur les codes         mesures, avec les 4 codes
signal infra-horaire des eclusees             mesures, filtrer statut = 4
```

## Conventions d'écriture

Séparateur décimal point, dates ISO-8601 en UTC, UTF-8 sans BOM, comme dans les
dépôts voisins. Débits en **m3/s**, convertis depuis les litres par seconde de
la source, la conversion étant signalée dans le datapackage.

**Nommage des colonnes : ne jamais traduire la source.** La règle de la famille
est la traçabilité jusqu'à la documentation d'origine, pas une préférence de
langue. Ici elle se coupe en deux, et les deux moitiés cohabitent :

```
venant de Hub'Eau       code_station, libelle_station, code_site_hydro
venant du Sandre        statut, qualification, methode, continuite
venant d'HydroPortail   raw, most_valid, validated
```

Les deux premières sont en français parce que leurs sources le sont, reprises
telles quelles, sans accent comme Hub'Eau les écrit. La troisième reste en
anglais pour exactement la même raison : `most_valid` et `raw` sont les noms des
boutons du formulaire d'HydroPortail et de son paramètre `statusData`. Un nom de
produit ou de paramètre se recopie, il ne se traduit pas, sous peine de rompre
le lien avec la documentation d'origine.

**Cette règle vaut aussi pour les options de la ligne de commande.** Le plan
initial proposait `--statuts brut | most_valid | les-deux`, ce qui traduisait
`raw` et pas `most_valid` sur la même ligne. C'est `--statuts raw` qui est
retenu, par simple application de la règle ci-dessus.

## La mise à jour incrémentale, écartée en v1

Pas seulement pour aller vite. Un débit n'est pas une observation figée : il est
calculé depuis une hauteur par une courbe de tarage, et **une révision de cette
courbe réécrit le passé**. Une reprise fondée sur les dates manquerait ces
corrections en silence. La mesure le confirme par un autre chemin : la
validation modifie déjà 196 valeurs sur 481 sur un seul mois.

Ce que la v1 fait : tout télécharger. Ce qu'elle prépare : une **empreinte
sha256 par station**, écrite dans le datapackage, qui rendra mesurable au
passage suivant ce qui a bougé dans le passé. Une v2 se décidera sur ces faits.

À instruire pour cette v2 : le JSON porte un champ `correctionCurves`, vide sur
tous les essais. S'il expose un jour les courbes de tarage et leurs dates, il
donne le signal de révision qui manque.

## Organisation du code

Conforme aux dépôts voisins :

```
download_hydroportail.py    interface en ligne de commande
hydroportail/api.py         couche HTTP, politesse, quota, fenetrage, reprise
hydroportail/schema.py      colonnes, types, vocabulaire, datapackage
hydroportail/download.py    orchestration, ecriture, relecture
```
