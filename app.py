from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import calendar as cal
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from functools import wraps
import secrets
from flask_mail import Mail, Message
import logging
import locale
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Configuration par défaut
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Essayer de charger la configuration depuis config.py
try:
    app.config.from_object('config')
    logger.info("Configuration chargée depuis config.py")
except Exception as e:
    logger.warning(f"Impossible de charger config.py, utilisation de la configuration par défaut: {str(e)}")

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
mail = Mail(app)

# Room colors mapping - using pastel colors
ROOM_COLORS = {
    'Chambre sur la rue': '#FFB5B5',       # Pastel Red
    'Chambre du garage': '#B5D8FF',        # Pastel Blue
    'Petit salon': '#E2B5FF',              # Pastel Purple
    'Chambre des parents': '#B5E2B5',      # Pastel Green
    'Dortoir des enfants': '#FFE2B5',      # Pastel Orange
}

def get_room_color(room_name):
    """Get color for a room, with fallback to default color"""
    return ROOM_COLORS.get(room_name, '#CCCCCC')

def handle_room_image(image_file, room_name, old_image=None):
    """Handle room image upload"""
    if image_file:
        # Create a secure filename
        filename = secure_filename(image_file.filename)
        # Add room name prefix to avoid conflicts
        filename = f"room_{room_name.lower().replace(' ', '_')}.jpg"
        
        # Save the file
        image_path = os.path.join(app.root_path, 'static/images/rooms', filename)
        image_file.save(image_path)
        
        # Delete old image if it exists and is different
        if old_image and old_image != filename:
            try:
                old_image_path = os.path.join(app.root_path, 'static/images/rooms', old_image)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            except Exception as e:
                logger.error(f"Error deleting old image: {str(e)}")
        
        return filename
    return old_image

def allowed_file(filename):
    """Check if the file extension is allowed."""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def parent_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_parent:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def send_email_to_admins(subject, body):
    """
    Envoie un email à tous les administrateurs
    """
    admins = User.query.filter_by(is_admin=True).all()
    for admin in admins:
        msg = Message(
            subject,
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[admin.email]
        )
        msg.body = body
        mail.send(msg)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expiry = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer)
    description = db.Column(db.Text)
    image = db.Column(db.String(200))

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    number_of_guests = db.Column(db.Integer, nullable=False)
    room = db.relationship('Room', backref=db.backref('reservations', lazy=True))
    user = db.relationship('User', backref=db.backref('reservations', lazy=True))

@app.template_filter('current_year')
def current_year_filter(text):
    return datetime.now().year

@app.context_processor
def utility_processor():
    """Make utility functions available to all templates"""
    return {
        'current_year': datetime.now().year,
        'get_room_color': get_room_color
    }

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_approved:
                flash('Votre compte n\'a pas encore été approuvé.', 'error')
                return redirect(url_for('login'))
            
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('home'))
        else:
            flash('Email ou mot de passe incorrect.', 'error')
    
    current_year = datetime.now().year
    return render_template('login.html', current_year=current_year)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('home'))

@app.route('/')
def home():
    rooms = Room.query.all()
    next_reservations = []
    
    if current_user.is_authenticated:
        # Get next 3 reservations across all rooms
        next_reservations = Reservation.query.filter(
            Reservation.end_date >= datetime.now()
        ).order_by(Reservation.start_date).limit(3).all()

    return render_template('home.html', 
                         rooms=rooms,
                         next_reservations=next_reservations,
                         now=datetime.now())

@app.route('/reservations', methods=['GET'])
@login_required
def view_reservations():
    return redirect(url_for('calendar'))

@app.route('/make-reservation', methods=['GET', 'POST'])
@login_required
def make_reservation():
    if request.method == 'GET':
        rooms = Room.query.all()
        return render_template('make_reservation.html', rooms=rooms)
        
    # Handle POST request
    if request.is_json:
        data = request.get_json()
    else:
        data = {
            'room_id': request.form.get('room_id'),
            'start_date': request.form.get('start_date'),
            'end_date': request.form.get('end_date'),
            'number_of_guests': request.form.get('number_of_guests')
        }
    
    if not data:
        flash('Données de réservation manquantes.', 'error')
        return redirect(url_for('make_reservation'))

    try:
        # Convert string inputs to appropriate types
        room_id = int(data['room_id'])
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        number_of_guests = int(data['number_of_guests'])
        current_date = datetime.now().date()

        # Validate dates
        if start_date < current_date:
            if request.is_json:
                return jsonify({'error': 'La date de début doit être dans le futur'}), 400
            flash('La date de début doit être dans le futur.', 'error')
            return redirect(url_for('make_reservation'))
            
        if end_date <= start_date:
            if request.is_json:
                return jsonify({'error': 'La date de fin doit être après la date de début'}), 400
            flash('La date de fin doit être après la date de début.', 'error')
            return redirect(url_for('make_reservation'))

        # Validate the room exists
        room = Room.query.get(room_id)
        if not room:
            if request.is_json:
                return jsonify({'error': 'Chambre non trouvée'}), 404
            flash('Chambre non trouvée.', 'error')
            return redirect(url_for('make_reservation'))

        # Validate guest count
        if number_of_guests > room.capacity:
            if request.is_json:
                return jsonify({'error': f'Cette chambre ne peut accueillir que {room.capacity} personnes'}), 400
            flash(f'Cette chambre ne peut accueillir que {room.capacity} personnes.', 'error')
            return redirect(url_for('make_reservation'))
        
        if number_of_guests < 1:
            if request.is_json:
                return jsonify({'error': 'Le nombre de personnes doit être supérieur à 0'}), 400
            flash('Le nombre de personnes doit être supérieur à 0.', 'error')
            return redirect(url_for('make_reservation'))

        # Check if room is available for these dates
        overlapping = Reservation.query.filter(
            Reservation.room_id == room_id,
            Reservation.end_date > start_date,
            Reservation.start_date < end_date
        ).first()

        if overlapping:
            if request.is_json:
                return jsonify({'error': 'La chambre n\'est pas disponible pour ces dates'}), 400
            flash('La chambre n\'est pas disponible pour ces dates.', 'error')
            return redirect(url_for('make_reservation'))

        # Create the reservation
        reservation = Reservation(
            user_id=current_user.id,
            room_id=room_id,
            start_date=start_date,
            end_date=end_date,
            number_of_guests=number_of_guests
        )

        db.session.add(reservation)
        db.session.commit()

        # Send email to admin
        try:
            subject = 'Nouvelle réservation'
            body = f"""Nouvelle réservation de {current_user.name} ({current_user.email})

Chambre: {room.name}
Du: {start_date}
Au: {end_date}
Nombre de personnes: {number_of_guests}"""
            send_email_to_admins(subject, body)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email aux administrateurs : {str(e)}")

        if request.is_json:
            return jsonify({'message': 'Réservation créée avec succès'}), 201
        flash('Réservation créée avec succès!', 'success')
        return redirect(url_for('my_reservations'))

    except (ValueError, KeyError) as e:
        logger.error(f"Error in make_reservation: {str(e)}")
        if request.is_json:
            return jsonify({'error': 'Données de réservation invalides'}), 400
        flash('Données de réservation invalides.', 'error')
        return redirect(url_for('make_reservation'))

    except Exception as e:
        logger.error(f"Unexpected error in make_reservation: {str(e)}")
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': 'Erreur lors de la création de la réservation'}), 500
        flash('Erreur lors de la création de la réservation.', 'error')
        return redirect(url_for('make_reservation'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            name = request.form.get('name')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            logger.debug(f"Tentative d'inscription avec email: {email}, name: {name}")
            
            # Vérification des champs requis
            if not email or not name or not password or not confirm_password:
                logger.warning("Champs manquants dans le formulaire d'inscription")
                flash('Tous les champs sont obligatoires.', 'error')
                return redirect(url_for('register'))
            
            # Vérification de la correspondance des mots de passe
            if password != confirm_password:
                logger.warning("Les mots de passe ne correspondent pas")
                flash('Les mots de passe ne correspondent pas.', 'error')
                return redirect(url_for('register'))
            
            # Vérification de la longueur minimale du mot de passe
            if len(password) < 6:
                logger.warning("Mot de passe trop court")
                flash('Le mot de passe doit contenir au moins 6 caractères.', 'error')
                return redirect(url_for('register'))
            
            # Vérification de l'email existant
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                logger.warning(f"Tentative d'inscription avec un email existant: {email}")
                flash('Un compte existe déjà avec cet email.', 'error')
                return redirect(url_for('register'))
            
            # Création de l'utilisateur
            new_user = User(
                email=email,
                name=name,
                is_admin=False,
                is_approved=False,
            )
            new_user.set_password(password)
            
            try:
                # Sauvegarde dans la base de données
                db.session.add(new_user)
                db.session.commit()
                
                # Envoi d'email aux administrateurs
                try:
                    subject = "Nouvelle inscription sur Maison Bourrut"
                    body = f"""Un nouvel utilisateur s'est inscrit sur le site :
                    
Nom : {name}
Email : {email}

Vous pouvez approuver ou rejeter cette inscription depuis la page de gestion des utilisateurs :
{url_for('manage_users', _external=True)}
"""
                    send_email_to_admins(subject, body)
                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi de l'email aux administrateurs : {str(e)}")
                
                logger.info(f"Nouvel utilisateur créé avec succès: {email}")
                flash('Votre compte a été créé avec succès. Un administrateur doit maintenant l\'approuver.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Erreur lors de la sauvegarde de l'utilisateur: {str(e)}")
                flash('Une erreur est survenue lors de la création du compte. Veuillez réessayer.', 'error')
                return redirect(url_for('register'))
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'inscription: {str(e)}")
            flash('Une erreur inattendue est survenue. Veuillez réessayer.', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        if current_password and new_password:
            if current_user.check_password(current_password):
                current_user.set_password(new_password)
                flash('Mot de passe mis à jour avec succès!', 'success')
            else:
                flash('Mot de passe actuel incorrect.', 'error')
                return redirect(url_for('profile'))
        
        current_user.name = name
        db.session.commit()
        flash('Profil mis à jour avec succès!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

@app.route('/manage_users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/toggle_admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    if current_user.id == user_id:
        flash('Vous ne pouvez pas modifier vos propres droits d\'administrateur.', 'error')
        return redirect(url_for('manage_users'))
    
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    
    flash(f'Les droits d\'administrateur de {user.name} ont été {"retirés" if not user.is_admin else "accordés"}.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/toggle_parent/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_parent(user_id):
    user = User.query.get_or_404(user_id)
    user.is_parent = not user.is_parent
    db.session.commit()
    
    flash(f'Les droits de parent de {user.name} ont été {"retirés" if not user.is_parent else "accordés"}.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Impossible de supprimer un administrateur.', 'error')
        return redirect(url_for('manage_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash('Utilisateur supprimé avec succès.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Impossible de modifier le statut d\'un administrateur.', 'error')
        return redirect(url_for('manage_users'))
    
    user.is_approved = True
    db.session.commit()
    flash(f'L\'utilisateur {user.name} a été approuvé.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/reject_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Impossible de rejeter un administrateur.', 'error')
        return redirect(url_for('manage_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f'L\'utilisateur {user.name} a été rejeté et supprimé.', 'success')
    return redirect(url_for('manage_users'))

@app.route('/manage_rooms')
@login_required
@admin_required
def manage_rooms():
    rooms = Room.query.all()
    return render_template('manage_rooms.html', rooms=rooms)

@app.route('/add_room', methods=['POST'])
@login_required
@admin_required
def add_room():
    name = request.form.get('name')
    capacity = request.form.get('capacity')
    description = request.form.get('description')
    image_file = request.files.get('image')
    
    if not name or not capacity:
        flash('Le nom et la capacité sont requis.', 'error')
        return redirect(url_for('manage_rooms'))
    
    try:
        # Handle image upload first
        image_path = handle_room_image(image_file, name) if image_file else None
        
        # Create new room
        room = Room(name=name, capacity=int(capacity), description=description, image=image_path)
        db.session.add(room)
        db.session.commit()
        
        flash('Chambre ajoutée avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Une erreur est survenue lors de l\'ajout de la chambre.', 'error')
        app.logger.error(f'Error adding room: {str(e)}')
    
    return redirect(url_for('manage_rooms'))

@app.route('/get_room/<int:room_id>')
@login_required
def get_room(room_id):
    room = Room.query.get_or_404(room_id)
    return jsonify({
        'id': room.id,
        'name': room.name,
        'capacity': room.capacity,
        'description': room.description,
        'image': room.image
    })

@app.route('/edit_room/<int:room_id>', methods=['POST'])
@login_required
@admin_required
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    
    name = request.form.get('name')
    capacity = request.form.get('capacity')
    description = request.form.get('description')
    image_file = request.files.get('image')
    
    if not name or not capacity:
        flash('Le nom et la capacité sont requis.', 'error')
        return redirect(url_for('manage_rooms'))
    
    try:
        room.name = name
        room.capacity = int(capacity)
        room.description = description
        
        # Handle image upload if new image is provided
        if image_file:
            if allowed_file(image_file.filename):
                # Delete old image if it exists
                if room.image:
                    old_image_path = os.path.join(app.root_path, 'static', 'images', 'rooms', room.image)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # Save new image using room name
                image_path = handle_room_image(image_file, name, room.image)
                room.image = image_path
            else:
                flash('Format de fichier non autorisé. Utilisez JPG, JPEG, PNG ou GIF.', 'error')
                return redirect(url_for('manage_rooms'))
        
        db.session.commit()
        flash('Chambre modifiée avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Une erreur est survenue lors de la modification de la chambre.', 'error')
        app.logger.error(f'Error editing room: {str(e)}')
    
    return redirect(url_for('manage_rooms'))

@app.route('/delete_room/<int:room_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    
    # Check for existing reservations
    if room.reservations:
        flash('Impossible de supprimer cette chambre car elle a des réservations existantes.', 'error')
        return redirect(url_for('manage_rooms'))

    try:
        # Delete room image if it exists
        if room.image:
            image_path = os.path.join(app.root_path, 'static', 'images', 'rooms', room.image)
            if os.path.exists(image_path):
                os.remove(image_path)

        db.session.delete(room)
        db.session.commit()
        
        flash('Chambre supprimée avec succès!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Une erreur est survenue lors de la suppression de la chambre.', 'error')
        app.logger.error(f'Error deleting room: {str(e)}')
    
    return redirect(url_for('manage_rooms'))

@app.route('/delete_selected_reservations', methods=['POST'])
@login_required
@admin_required
def delete_selected_reservations():
    try:
        selected_ids = request.form.getlist('selected_reservations')
        if not selected_ids:
            flash('Aucune réservation sélectionnée.', 'error')
            return redirect(url_for('my_reservations'))
        
        # Convert string IDs to integers
        selected_ids = [int(id) for id in selected_ids]
            
        # Only delete reservations that don't belong to the current user
        reservations_to_delete = Reservation.query.filter(
            Reservation.id.in_(selected_ids),
            Reservation.user_id != current_user.id
        ).all()
        
        for reservation in reservations_to_delete:
            db.session.delete(reservation)
        
        db.session.commit()
        flash('Les réservations sélectionnées ont été supprimées avec succès.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Une erreur est survenue lors de la suppression des réservations.', 'error')
    return redirect(url_for('my_reservations'))

@app.route('/list_rooms')
@login_required
@admin_required
def list_rooms():
    """List all rooms in the database"""
    rooms = Room.query.all()
    return jsonify([{'id': room.id, 'name': room.name, 'capacity': room.capacity} for room in rooms])

def generate_calendar_html(year, month, reservations):
    # Get first day of the month and number of days
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    num_days = last_day.day

    # Get the weekday of the first day (0 = Monday, 6 = Sunday)
    first_weekday = first_day.weekday()
    
    # Start building the HTML
    html = ['<table class="calendar">']
    html.append('<tr><th>Lun</th><th>Mar</th><th>Mer</th><th>Jeu</th><th>Ven</th><th>Sam</th><th>Dim</th></tr>')
    
    # Current date for highlighting today
    today = datetime.now().date()
    
    # Add empty cells for days before the first day of the month
    html.append('<tr>')
    for i in range(first_weekday):
        html.append('<td class="empty"></td>')
    
    # Add cells for each day of the month
    current_weekday = first_weekday
    for day in range(1, num_days + 1):
        if current_weekday == 0 and day != 1:
            html.append('</tr><tr>')
        
        date = datetime(year, month, day).date()
        classes = ['calendar-day']
        
        if date == today:
            classes.append('today')
        
        # Find reservations for this day
        day_reservations = []
        for reservation in reservations:
            start_date = reservation.start_date if isinstance(reservation.start_date, datetime) else datetime.combine(reservation.start_date, datetime.min.time())
            end_date = reservation.end_date if isinstance(reservation.end_date, datetime) else datetime.combine(reservation.end_date, datetime.min.time())
            if start_date.date() <= date <= end_date.date():
                day_reservations.append(reservation)
        
        html.append(f'<td class="{" ".join(classes)}">')
        html.append(f'<div class="date-number">{day}</div>')
        
        # Add reservations with room-specific colors
        if day_reservations:
            html.append('<div class="reservations">')
            for reservation in day_reservations:
                room_name = reservation.room.name
                room_color = get_room_color(room_name)
                
                # Create tooltip content
                tooltip = f"{reservation.user.name}<br>"
                tooltip += f"Du {reservation.start_date.strftime('%d/%m/%Y')}<br>"
                tooltip += f"Au {reservation.end_date.strftime('%d/%m/%Y')}"
                
                html.append(f'<div class="reservation-marker" style="background-color: {room_color};" '
                          f'data-tooltip="{tooltip}">'
                          f'<span class="user-name">{reservation.user.name}</span></div>')
            html.append('</div>')
        
        html.append('</td>')
        current_weekday = (current_weekday + 1) % 7
    
    # Add empty cells for days after the last day of the month
    while current_weekday != 0:
        html.append('<td class="empty"></td>')
        current_weekday = (current_weekday + 1) % 7
    
    html.append('</tr>')
    html.append('</table>')

    # Add room color legend
    html.append('<div class="room-legend">')
    html.append('<h4>Légende des chambres</h4>')
    html.append('<div class="legend-items">')
    for room in Room.query.all():
        room_color = get_room_color(room.name)
        html.append(f'<div class="legend-item">'
                   f'<div class="legend-color" style="background-color: {room_color};"></div>'
                   f'<span>{room.name}</span>'
                   f'</div>')
    html.append('</div>')
    html.append('</div>')

    return '\n'.join(html)

@app.route('/calendar', methods=['GET'])
@app.route('/calendar/<int:year>/<int:month>', methods=['GET'])
@login_required
def calendar(year=None, month=None):
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month

    current_date = datetime.now().date()

    # Get all future reservations for list view
    list_reservations = Reservation.query.filter(
        Reservation.end_date >= current_date
    ).order_by(Reservation.start_date).all()

    # Get reservations for the calendar view (keep this filtered by month)
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date()
    else:
        end_date = datetime(year, month + 1, 1).date()

    calendar_reservations = Reservation.query.filter(
        Reservation.start_date < end_date,
        Reservation.end_date >= start_date
    ).all()

    calendar_html = generate_calendar_html(year, month, calendar_reservations)
    
    return render_template('calendar.html',
                         calendar_html=calendar_html,
                         reservations=list_reservations,
                         current_year=year,
                         current_month=month,
                         now=datetime.now())

@app.route('/my_reservations')
@login_required
def my_reservations():
    room_id = request.args.get('room_id', type=int)
    query = Reservation.query

    if current_user.is_admin:
        if room_id:
            query = query.filter_by(room_id=room_id)
    else:
        query = query.filter_by(user_id=current_user.id)
        if room_id:
            query = query.filter_by(room_id=room_id)

    reservations = query.order_by(Reservation.start_date).all()
    rooms = Room.query.all()  # Get all rooms for the filter dropdown
    
    return render_template('my_reservations.html', 
                         reservations=reservations, 
                         rooms=rooms, 
                         selected_room_id=room_id)

@app.route('/edit_reservation/<int:reservation_id>', methods=['GET', 'POST'])
@login_required
def edit_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # Check if user has permission to edit this reservation
    if not current_user.is_admin and reservation.user_id != current_user.id:
        flash('Vous n\'avez pas la permission de modifier cette réservation.', 'error')
        return redirect(url_for('my_reservations'))
    
    if request.method == 'POST':
        try:
            # Get and validate form data
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            number_of_guests = int(request.form.get('number_of_guests'))
            current_date = datetime.now().date()
            
            # Validate dates
            if start_date < current_date:
                flash('La date de début doit être dans le futur.', 'error')
                return redirect(url_for('edit_reservation', reservation_id=reservation_id))
                
            if end_date <= start_date:
                flash('La date de fin doit être après la date de début.', 'error')
                return redirect(url_for('edit_reservation', reservation_id=reservation_id))
            
            # Validate guest count
            if number_of_guests > reservation.room.capacity:
                flash(f'Cette chambre ne peut accueillir que {reservation.room.capacity} personnes.', 'error')
                return redirect(url_for('edit_reservation', reservation_id=reservation_id))
            
            if number_of_guests < 1:
                flash('Le nombre de personnes doit être supérieur à 0.', 'error')
                return redirect(url_for('edit_reservation', reservation_id=reservation_id))
            
            # Check if room is available for these dates (excluding current reservation)
            overlapping = Reservation.query.filter(
                Reservation.room_id == reservation.room_id,
                Reservation.id != reservation_id,
                Reservation.end_date > start_date,
                Reservation.start_date < end_date
            ).first()
            
            if overlapping:
                flash('La chambre n\'est pas disponible pour ces dates.', 'error')
                return redirect(url_for('edit_reservation', reservation_id=reservation_id))
            
            # Update reservation
            reservation.start_date = start_date
            reservation.end_date = end_date
            reservation.number_of_guests = number_of_guests
            
            db.session.commit()
            
            # Notify admins of the change
            try:
                subject = 'Modification de réservation'
                body = f"""La réservation de {reservation.user.name} ({reservation.user.email}) a été modifiée.

Chambre: {reservation.room.name}
Nouvelles dates: du {start_date} au {end_date}
Nombre de personnes: {number_of_guests}

Modifié par: {current_user.name} ({current_user.email})"""
                send_email_to_admins(subject, body)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'email aux administrateurs : {str(e)}")
            
            flash('Réservation mise à jour avec succès!', 'success')
            return redirect(url_for('my_reservations'))
            
        except ValueError as e:
            logger.error(f"Error in edit_reservation: {str(e)}")
            flash('Données de réservation invalides.', 'error')
            return redirect(url_for('edit_reservation', reservation_id=reservation_id))
        except Exception as e:
            logger.error(f"Unexpected error in edit_reservation: {str(e)}")
            db.session.rollback()
            flash('Une erreur est survenue lors de la mise à jour de la réservation.', 'error')
            return redirect(url_for('edit_reservation', reservation_id=reservation_id))
    
    # GET request - show edit form
    rooms = Room.query.all()
    return render_template('edit_reservation.html', 
                         reservation=reservation,
                         rooms=rooms)

@app.route('/delete_reservation/<int:reservation_id>', methods=['GET', 'POST'])
@login_required
def delete_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # Check if user is authorized to delete this reservation
    if reservation.user_id != current_user.id and not current_user.is_admin:
        flash('Vous n\'êtes pas autorisé à supprimer cette réservation.', 'error')
        return redirect(url_for('my_reservations'))
    
    try:
        # Send email to admins
        subject = "Annulation de réservation"
        body = f"""Une réservation a été annulée:
        
Chambre: {reservation.room.name}
Dates: du {reservation.start_date.strftime('%d/%m/%Y')} au {reservation.end_date.strftime('%d/%m/%Y')}
Annulée par: {current_user.name} ({current_user.email})"""
        send_email_to_admins(subject, body)
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email aux administrateurs : {str(e)}")
    
    # Delete the reservation
    db.session.delete(reservation)
    db.session.commit()
    
    flash('Réservation annulée avec succès.', 'success')
    return redirect(url_for('my_reservations'))

@app.route('/debug_rooms')
def debug_rooms():
    rooms = Room.query.all()
    room_data = []
    for room in rooms:
        room_data.append({
            'id': room.id,
            'name': room.name,
            'image': room.image,
            'image_exists': os.path.exists(os.path.join(app.root_path, 'static', 'images', 'rooms', room.image)) if room.image else False
        })
    return jsonify(room_data)

@app.route('/test-email')
def test_email():
    try:
        msg = Message('Test Email - Maison Bourrut',
                    recipients=['bourrut@gmail.com'])
        msg.body = '''Ceci est un email de test pour vérifier la configuration du système de réinitialisation de mot de passe.

Si vous recevez cet email, la configuration est correcte!'''
        mail.send(msg)
        return 'Email envoyé avec succès! Vérifiez votre boîte de réception.'
    except Exception as e:
        return f'Erreur lors de l\'envoi de l\'email: {str(e)}'

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.get_reset_token()
            reset_url = url_for('reset_password', token=token, _external=True)
            
            msg = Message('Réinitialisation de mot de passe - Maison Bourrut',
                        recipients=[user.email])
            msg.body = f'''Pour réinitialiser votre mot de passe, visitez le lien suivant:
{reset_url}

Si vous n'avez pas demandé de réinitialisation de mot de passe, ignorez cet email.

Ce lien expirera dans 1 heure.
'''
            try:
                mail.send(msg)
                flash('Un email avec les instructions de réinitialisation a été envoyé.', 'success')
            except Exception as e:
                flash('Erreur lors de l\'envoi de l\'email. Veuillez réessayer plus tard.', 'error')
                print(f"Email error: {str(e)}")
        else:
            # Pour des raisons de sécurité, nous affichons le même message même si l'email n'existe pas
            flash('Un email avec les instructions de réinitialisation a été envoyé.', 'success')
        
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    user = User.verify_reset_token(token)
    if user is None:
        flash('Le lien de réinitialisation est invalide ou a expiré.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash('Votre mot de passe a été mis à jour.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
