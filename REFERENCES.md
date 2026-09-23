# Ce que d'autres ont établi

Ce fichier rassemble ce que la littérature et les documentations disent des
questions que ce dépôt se pose, avec la référence et, quand c'est possible, le
passage exact. Il a été ouvert le 23 septembre 2026 pour préparer l'outil de
rééchantillonnage, décrit dans [ROADMAP.md](ROADMAP.md).

**Rien ici n'est une mesure.** C'est ce qui le sépare de [SOURCE.md](SOURCE.md) :
une affirmation lue ici est une hypothèse de travail sur notre source, pas un
fait établi sur elle. Quand on la vérifie sur le service, le résultat va dans
`SOURCE.md` et cite la référence ; quand une décision s'appuie dessus, elle vit
dans [DESIGN.md](DESIGN.md) et renvoie ici.

## Agréger une série instantanée : l'intégrale, par la méthode des trapèzes

**OMM, *Manual on Stream Gauging*, vol. II, *Computation of discharge*,
WMO-No. 1044, 2010**, § 6.12.
[library.wmo.int](https://library.wmo.int/records/item/35841-manual-on-stream-gauging-vol-ii-computation-of-discharge)

C'est la référence normative, et elle définit l'agrégation que nos collègues
hydrologues réclament :

> The time-weighted arithmetic method of computing daily mean values is referred
> to as the trapezoidal method. The trapezoidal method is a mathematical
> integration of the unit value hydrograph [...]. The time interval between unit
> values may be constant or variable.

Et pour les bornes de l'intervalle :

> If actual values are not recorded for the midnight time, a unit value should
> be interpolated based on the recorded unit values on either side of the
> midnight time. These interpolated midnight values should be flagged as
> interpolated.

Ce qu'on en tire :

- **agréger n'est pas le contraire d'interpoler.** La méthode des trapèzes est
  exactement l'intégrale de l'interpolation linéaire entre les points ; toute
  moyenne sur un pas d'une série irrégulière la suppose. Ce qui est à écarter,
  c'est l'**échantillonnage** : lire la courbe interpolée à des instants fixes,
  ce qui prétend à une information que la mesure n'a pas ;
- **la borne interpolée se marque.** L'idiome des dépôts voisins, une colonne
  qui dit jusqu'où croire la valeur, est donc aussi celui de la norme ;
- le manuel range sous le nom de valeurs journalières la **moyenne**, le
  **maximum instantané** et le **minimum instantané** (introduction, § 1.3). Le
  même trio vaut à n'importe quel pas.

Le manuel demande aussi que tous les horodatages soient convertis en UTC
(§ 6.4), ce que fait HydroPortail.

## Ce que veut dire un point de la série validée

**Courret D., Baran P., Larinier M. (2021).** An indicator to characterize
hydrological alteration due to hydropeaking. *Journal of Ecohydraulics* 6(2),
139-156. [doi:10.1080/24705357.2020.1871307](https://doi.org/10.1080/24705357.2020.1871307),
texte intégral sur [HAL](https://hal.science/hal-03382554).

En note de la section des données, la définition de ce que la Banque Hydro
servait comme débits à pas variable :

> QTVAR 5%: data with variable time steps, composed of flow-date couples set up
> to maintain a maximum deviation of 5% of flow with respect to all registered
> flow-date couples. Consequently, the time step can vary between 1 minute and
> several hours.

C'est l'information qui manquait pour lire la série validée, décrite dans
[SOURCE.md](SOURCE.md) comme « une courbe à points de rupture ». **Un écart de
trois heures entre deux points ne dit pas que l'instrument mesurait toutes les
trois heures, il dit que la courbe ne s'écarte pas de plus de 5 % d'un segment
entre les deux.** Intégrer cette courbe sur quinze minutes ne crée donc pas
d'information, on lit ce que le producteur certifie. Pour le validé, le critère
pertinent n'est pas le pas de l'instrument mais la tolérance.

Deux limites, qui font de ce chiffre une hypothèse et non un acquis :

- il date d'un jeu constitué en 2009 sur la Banque Hydro. Rien ne dit
  qu'HYDRO3 et HydroPortail élaguent aujourd'hui avec la même tolérance, ni même
  qu'ils élaguent de la même manière ;
- il ne vaut pas pour les relevés d'échelle anciens, une lecture par jour à sept
  heures, qui ne sont pas une courbe élaguée mais une observation isolée.

## Les éclusées et la résolution temporelle

**Courret et al. (2021)**, ci-dessus. C'est l'indicateur français de référence :
cinq classes de perturbation par année et par saison, à partir du nombre
d'éclusées, du premier décile des débits de base et du dernier décile des
amplitudes et des gradients. Deux points comptent ici :

- **la méthode s'applique directement à un pas variable.** Elle détecte des
  franchissements de seuils de débit, sans grille régulière, et a été construite
  sur QTVAR 5 % et sur des débits horaires d'EDF. Pour cet usage, la donnée
  native est la meilleure entrée ;
- elle signale que les débits moyens journaliers sous-estiment les vitesses de
  variation, et ne les a utilisés que faute d'autre chose.

Le calcul est automatisé dans une macro Excel fournie en matériel
supplémentaire. La thèse qui la précède : Courret D. (2014), *Problématique des
impacts de la gestion par éclusées [...]*, INP Toulouse,
[theses.fr/2014INPT0127](http://www.theses.fr/2014INPT0127).

**Greimel F. et al. (2016).** A method to detect and characterize sub-daily
flow fluctuations. *Hydrological Processes* 30(13), 2063-2078.
[doi:10.1002/hyp.10773](https://doi.org/10.1002/hyp.10773)

Méthode par événements, montées et descentes, chacun décrit par son amplitude,
son gradient, sa durée. Elle demande un pas horaire ou plus fin. Elle est
implémentée dans le paquet R
[`hydropeak`](https://cran.r-project.org/web/packages/hydropeak/index.html)
(Haider, Grün, Altmann, Greimel), dont le manuel précise l'entrée attendue :

> steplength: Numeric value which specifies the distance between (equispaced)
> time steps in minutes. (default: 15 [...]). Non-equispaced time steps are not
> supported and missing time steps are imputed [...], Q values are assumed to
> be NA.

**C'est très probablement l'origine de la demande reçue** : un pas régulier de
quinze minutes, les trous en `NA`. Une grille à 15 minutes est donc l'entrée
directe de l'outil le plus répandu dans le domaine.

**Bevelhimer M.S., McManamay R.A., O'Connor B. (2015).** Characterizing
sub-daily flow regimes: implications of hydrologic resolution on ecohydrology
studies. *River Research and Applications* 31(7), 867-879.
[OSTI](https://www.osti.gov/servlets/purl/1263830)

Treize indicateurs infra-journaliers et leur comparaison aux indicateurs
journaliers sur trente stations américaines. À citer surtout comme contre-exemple
de méthode : pour ramener leurs données à l'heure, les auteurs ont gardé « one
flow value per hour, usually the top-of-the-hour », c'est-à-dire un
échantillonnage et non une agrégation.

**Ashraf F.B. et al. (2022).** A method for assessment of sub-daily flow
alterations using wavelet analysis for regulated rivers. *Water Resources
Research* 58(1). [doi:10.1029/2021WR030421](https://doi.org/10.1029/2021WR030421)

Analyse en ondelettes sur des débits horaires, qui fait ressortir les cycles de
douze heures et d'un jour. Utile si l'on veut une lecture spectrale plutôt que
par événements, et elle suppose elle aussi un pas régulier.

## Ce qu'une moyenne fait aux extrêmes

Une moyenne sur un pas fixe est un filtre passe-bas : elle conserve le volume
et aplatit ce qui est plus court que le pas. Pour les éclusées, cela porte
directement sur le gradient, qui est une des variables de l'indicateur.

L'analogue le mieux étudié est la pluie. *Precipitation extremes derived from
temporally aggregated time series and the efficiency of their correction*,
*Hydrological Sciences Journal*, 2021,
[doi:10.1080/02626667.2021.1988087](https://doi.org/10.1080/02626667.2021.1988087),
montre que les extrêmes calculés sur des pas fixes sont sous-estimés parce que
le début d'un épisode tombe rarement sur une borne, et qu'il se retrouve coupé
en deux pas. Le même mécanisme vaut pour un front d'éclusée coupé par une borne
de quinze minutes. Nous ne l'avons lu que par son résumé.

C'est ce qui justifie de publier le minimum et le maximum instantanés de chaque
pas à côté de la moyenne : ils gardent l'amplitude que la moyenne aplatit.

## L'incertitude des débits

Aucune publication de Benjamin Renard (INRAE RiverLy) ne traite du
rééchantillonnage ou de l'agrégation en tant que tels, du moins aucune que la
recherche du 23 septembre 2026 ait trouvée. Ses travaux portent sur
l'incertitude des courbes de tarage et des chroniques qui en sortent, et deux
éclairent notre question.

**Horner I., Renard B., Le Coz J., Branger F., McMillan H.K., Pierrefeu G.
(2018).** Impact of stage measurement errors on streamflow uncertainty. *Water
Resources Research* 54(3), 1952-1976.
[doi:10.1002/2017WR022039](https://doi.org/10.1002/2017WR022039)

L'erreur sur la hauteur se sépare en une part **aléatoire**, vagues et bruit de
l'instrument, et une part **systématique**, biais et dérive du calage. Moyenner
réduit la première et laisse la seconde intacte. Sur des débits moyens
mensuels, l'erreur de hauteur pèse entre 8 et 20 % de l'incertitude totale
selon la sensibilité du contrôle hydraulique. Pour nous : une moyenne à quinze
minutes nettoie le bruit du brut, mais ni sa dérive ni l'erreur de courbe de
tarage.

**Kiang J.E. et al. (2018).** A comparison of methods for streamflow
uncertainty estimation. *Water Resources Research* 54.
[doi:10.1029/2018WR022708](https://doi.org/10.1029/2018WR022708)

Comparaison de plusieurs méthodes, dont BaRatin, sur les mêmes stations. Les écarts
entre méthodes sont larges, ce qui rappelle qu'aucune colonne de confiance ne
peut prétendre à une incertitude chiffrée sans un travail de cet ordre.

Autres travaux du même groupe, pour mémoire : Le Coz et al. (2014, *Journal of
Hydrology* 509, BaRatin) ; Mansanarez et al. (2019, *WRR*, ruptures de courbe à
dates connues) ; Darienzo et al. (2021, *WRR*, détection de ruptures par
jaugeages) ; Perret et al. (2021, *WRR*, courbes cycliques dues à la
végétation) ; Horner et al. (2022, *Hydrological Processes*,
[doi:10.1002/hyp.14497](https://doi.org/10.1002/hyp.14497), sensibilité des
contrôles).

**Une question à lui poser directement** : que devient l'incertitude quand on
intègre sur un pas une courbe élaguée à une tolérance donnée, et cette
tolérance doit-elle entrer dans l'incertitude publiée ?

## La documentation d'HydroPortail

**Aide d'HydroPortail, « Données et noms des variables »**,
[hydro.eaufrance.fr/aide/donnees-et-noms-des-variables](https://hydro.eaufrance.fr/aide/donnees-et-noms-des-variables).

> À ce jour, le débit n-horaire moyen (QmnH) est calculé comme la moyenne des
> débits instantanés sur la période couvrant les n-1 heures précédentes et
> l'heure en cours.

La phrase ne dit pas si la moyenne est pondérée par le temps. Sur une courbe à
points de rupture, une moyenne arithmétique des points serait fausse, puisque
les points se resserrent là où le débit bouge. Elle ne dit pas non plus de quel
statut `QmnH` est calculé, ni ce que vaut `step` pour cette grandeur. Tout cela
a été mesuré le 23 septembre 2026 : c'est une intégrale par la méthode des
trapèzes, horodatée au début de l'heure, arrondie à trois chiffres
significatifs, et absente en brut. Voir [SOURCE.md](SOURCE.md).
