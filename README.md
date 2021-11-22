# Étude de cas Ekimetrics - G17
Étude de Cas Ekimetrics - Groupe 17

## Ressources

Guide notion d'Ekimetrics [ici](https://nettle-search-8c3.notion.site/Guide-tude-de-cas-Ekimetrics-2021-f1bff84a4cbb45319f01a3fd603259ba)

## Gestion de mission

Notion d'équipe [ici](https://www.notion.so/Team-Home-cc51b06a9ffa4bd3aa2c595efe4be9c9)

## Description du repository

- Le dossier `data` contient l'ensemble des fichiers `csv` de l'étude de cas.

- Le notebook `explo_data.ipynb` contient une première exploration des données.

### Diagnotic

Le dossier `diagnostic` contient l'ensemble des analyses de données réalisées durant la première semaine sur l'historique :

- `implantation_entrepot.ipynb` étudie la répartition des entrepôts et leur pression

- `strategie_routage` étudie sommairement la stratégie actuelle d'attribution des routes

- `analyse_commandes.ipynb` analyse la répartition spatiale et temporelle commandes

- `costs_revenues.ipynb` contient une première analyse des coûts

## Script d'optimisation du routage

### Script en mode local avec Docker

D'abord il faut adapter le dockerfile en choisissant le fichier de commandes, le fichier de sortie et le délai de livraison accepté.

`docker build --tag eki-opti .`

`docker run --name eki-contain eki-opti`

On relance le conteneur pour copier le fichier en sortie

`docker run --name eki-contain`

`docker cp eki-contain:new_routes.csv ./new_routes.csv`

### Script en local sans Docker

`pip install -r requirements.txt`

`python ./opti/optimize.py <orders.csv> <delay> <new_routes.csv>`