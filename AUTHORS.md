# Auteurs

- **Louis Héraut** <louis.heraut@inrae.fr>, INRAE : conception et maintenance.

Code écrit avec l'assistance de Claude (Anthropic).

## Origine des données

Les débits ne sont pas produits par ce dépôt. Ils sont mesurés et calculés par
les services hydrométriques de l'État, principalement les DREAL et leurs unités
d'hydrométrie, puis rassemblés dans la **banque Hydro** et diffusés par le
**SCHAPI** via HydroPortail et l'API Hub'Eau.

Un débit n'est jamais une mesure directe : c'est une hauteur d'eau mesurée sur
le terrain, convertie par une courbe de tarage que l'hydromètre établit et
révise. Les codes de qualité qui accompagnent chaque point disent où en est
cette expertise, et leur vocabulaire est administré par le **Sandre**.

Ce dépôt ne contient que le code de téléchargement et de mise en forme. La
licence GPL-3.0-or-later porte sur ce code, pas sur les données, qui restent
diffusées sous leurs propres conditions.

Pour citer les données elles-mêmes :

> SCHAPI, Banque Hydro, diffusée par HydroPortail,
> <https://hydro.eaufrance.fr/>
