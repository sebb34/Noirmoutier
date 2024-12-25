from app import app, db, Room, User

def update_database():
    with app.app_context():
        try:
            # Drop all tables
            db.drop_all()
            print("Dropped all existing tables")
            
            # Create all tables with the new schema
            db.create_all()
            print("Created all tables with new schema")
            
            # Create admin user
            admin = User(
                email='bourrut@gmail.com',
                name='Admin',
                is_admin=True,
                is_approved=True
            )
            admin.set_password('admin123')  # Set a secure password in production
            db.session.add(admin)
            print("Added admin user")
            
            # Add default rooms
            default_rooms = [
                Room(
                    name='Chambre sur la rue',
                    capacity=2,
                    description='Chambre double avec vue sur la rue, lit double 140cm',
                    image='images/rooms/rue.jpg'
                ),
                Room(
                    name='Chambre côté jardin',
                    capacity=3,
                    description='Chambre triple avec vue sur le jardin, un lit double 140cm et un lit simple 90cm',
                    image='images/rooms/jardin.jpg'
                ),
                Room(
                    name='Chambre des parents',
                    capacity=2,
                    description='Chambre principale avec salle de bain privée, lit double 160cm',
                    image='images/rooms/parents.jpg'
                )
            ]
            
            # Add rooms to database
            for room in default_rooms:
                db.session.add(room)
            
            db.session.commit()
            print("Added default rooms")
            
            print("Database update completed successfully")
            
        except Exception as e:
            print(f"Error updating database: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    update_database()
