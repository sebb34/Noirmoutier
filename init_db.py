from app import app, db, User, Room, Reservation
from datetime import datetime
import bcrypt

with app.app_context():
    # Recréer toutes les tables
    db.drop_all()
    db.create_all()
    
    # Créer un compte administrateur par défaut
    admin = User(
        email='admin@noirmoutier.fr',
        name='Administrateur',
        is_admin=True,
        is_approved=True
    )
    admin.password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    db.session.add(admin)
    db.session.commit()
    
    print("Base de données réinitialisée avec succès!")
    print("Compte administrateur créé:")
    print("Email: admin@noirmoutier.fr")
    print("Mot de passe: admin123")
