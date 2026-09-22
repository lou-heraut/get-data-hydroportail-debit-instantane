# Jeu de test

Dix stations choisies en septembre 2026 pour couvrir les cas limites plutôt que
pour représenter le réseau. Ce n'est pas une demande extérieure : c'est le jeu
sur lequel le code a été mis au point, sur lequel tournent les exemples du
README et la procédure de vérification de [CLAUDE.md](../../CLAUDE.md).

Ce que chacune illustre est dans [SOURCE.md](../../SOURCE.md), section « Le jeu
de test », et n'est pas recopié ici. En deux mots : une éclusée alpine, une
éclusée de plaine, un grand fleuve régulé, une station sans `s=16`, la plus
longue chronique connue, un site à trois stations, une couverture trouée à
58 %, et deux stations qui ne portent aucun débit instantané.

Le fichier `stations.txt` est le contrat commun à tous les cas : un code par
ligne, et rien d'autre.

```bash
python download_hydroportail.py --case 2026-09_test-set --inventory
python download_hydroportail.py --case 2026-09_test-set
python check_hydroportail.py --case 2026-09_test-set
```
