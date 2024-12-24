# Maison Bourrut - Noirmoutier

Un site web simple pour gérer les réservations de la maison familiale Bourrut à Noirmoutier.

## Fonctionnalités

- Visualisation des réservations existantes
- Création de nouvelles réservations
- Vérification automatique des conflits de dates
- Interface responsive et moderne

## Installation

1. Cloner le repository
2. Créer un environnement virtuel Python :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. Installer les dépendances :
```bash
pip install -r requirements.txt
```

4. Lancer l'application :
```bash
python app.py
```

L'application sera accessible à l'adresse : http://localhost:5000

## Structure du projet

- `app.py` : Application principale Flask
- `templates/` : Templates HTML
  - `index.html` : Page d'accueil
  - `make_reservation.html` : Formulaire de réservation
  - `reservations.html` : Liste des réservations
- `static/` : Fichiers statiques
  - `style.css` : Styles CSS
- `instance/` : Base de données SQLite (créée automatiquement)

## Technologies utilisées

- Flask
- SQLAlchemy
- SQLite
- HTML5
- CSS3
