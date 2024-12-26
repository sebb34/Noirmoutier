from app import app, db, User
from werkzeug.security import generate_password_hash

def reset_admin():
    with app.app_context():
        # Create default admin user
        admin = User(
            email='admin@noirmoutier.fr',
            name='Administrateur',
            is_admin=True,
            is_approved=True
        )
        admin.set_password('admin123')  # Set a default password

        try:
            # Drop existing tables
            db.drop_all()
            print("Existing database tables dropped.")

            # Create new tables
            db.create_all()
            print("New database tables created.")

            # Add admin user
            db.session.add(admin)
            db.session.commit()
            print("\nAdmin account created successfully!")
            print("Email: admin@noirmoutier.fr")
            print("Password: admin123")
            print("\nIMPORTANT: Please change the admin password after first login!")

        except Exception as e:
            print(f"Error: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    reset_admin()
