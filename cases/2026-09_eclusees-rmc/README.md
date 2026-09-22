# Éclusées en Rhône-Méditerranée-Corse

Demande ouverte en septembre 2026. Une équipe étudie les cours d'eau à éclusées
et a besoin des chroniques de débit d'une cinquantaine de stations du bassin
Rhône-Méditerranée-Corse, sur toute la durée disponible, à pas de temps
régulier : quinze minutes de préférence, une heure au plus, et le même pas d'un
bout à l'autre.

| fichier | ce qu'il est |
|---|---|
| `received-list.xlsx` | la liste transmise, telle qu'elle a été reçue, jamais retouchée |
| `resolved-stations.csv` | ce que `prepare_list.py` en tire : codes normalisés, traduits en codes de station, confrontés au service |
| `arbitrations.csv` | les choix que le script ne peut pas faire seul, avec leur motif |

Les codes de la liste sont pour l'essentiel des codes de site, parce que c'est
ce que les pages d'HydroPortail affichent en titre. Or les chroniques vivent sur
les stations, et un code de site interrogé tel quel rend la série de sa station
de référence sans dire laquelle. La traduction n'est donc pas une formalité :
douze des quarante-cinq codes de site ne désignent pas la station numéro 01.

Pour régénérer la table depuis la liste :

```bash
python prepare_list.py --case 2026-09_eclusees-rmc
```

Ce que la traduction a donné est mesuré dans [SOURCE.md](../../SOURCE.md),
section « Ce qu'une liste réelle a donné ». Ce qui reste à faire est dans
[ROADMAP.md](../../ROADMAP.md).
