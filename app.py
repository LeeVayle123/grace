import os
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from functools import wraps
from supabase import create_client, Client
import traceback
import base64
import re
try:
    from pywebpush import webpush, WebPushException
    PUSH_ENABLED = True
except ImportError:
    PUSH_ENABLED = False

# --- Clés VAPID pour Web Push Notifications ---
VAPID_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg7WAYtbSjbKwrn3/k
gNnHxlLcva2Fv8KZ3aNBiBJjlQehRANCAAT1CZv7NIjooJd4KJJFrDa6GZ8IQbjm
/mboAL00b4RaEaMW0esNYNy0TBq8KsomLWJYDvcG4fsSEayfFvWJElVS
-----END PRIVATE KEY-----"""
VAPID_PUBLIC_KEY = "BPUJm_s0iOigl3gokkWsNroZnwhBuOb-ZugAvTRvhFoRoxbR6w1g3LRMGrwqyiYtYlgO9wbh-xIRrJ8W9YkSVVI="
VAPID_CLAIMS = {"sub": "mailto:admin@lagraceseemin.com"}

# Installation de l'application (Adaptée à la structure Render)
base_dir = os.path.dirname(os.path.abspath(__file__))
# On configure le dossier statique pour pointer vers la racine, ainsi url_for('static') fonctionnera partout
app = Flask(__name__, 
            template_folder='templates', 
            static_folder='static')

# --- Configuration Supabase (Stockage permanent) ---
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://mfdotnwtjbqqnkgcblph.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1mZG90bnd0amJxcW5rZ2NibHBoIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjU0ODE0NCwiZXhwIjoyMDkyMTI0MTQ0fQ.Bb4pW0Lkg7aTEiOAd-BLQFPcBwpVX-JtFhn3Pmez3jw')

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"ERREUR INITIALISATION SUPABASE : {e}")
    supabase = None

# Nom du bucket créé par l'utilisateur
BUCKET_NAME = "boutique"

# Configuration
# Connexion à la base de données.
# Nous priorisons la variable d'environnement, mais le fallback pointe EXCLUSIVEMENT vers Supabase
# pour éviter de perdre les données avec un fichier SQLite local.
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

SUPABASE_DB_URL = "postgresql://postgres.mfdotnwtjbqqnkgcblph:Lee%23%23%23%40hrjkz@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or SUPABASE_DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secretkey_fallback')

# -- Initialisation des extensions --
db = SQLAlchemy(app)  # Pour gerer la base de données
bcrypt = Bcrypt(app)  # Pour chiffrer les mots de passe

# --- Modèles ---
class Categorie(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

class Produit(db.Model):
    __tablename__ = 'produit'
    id = db.Column(db.Integer, primary_key=True) 
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    prix = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)
    id_categorie = db.Column(db.Integer, db.ForeignKey('categories.id'))
    image_filename = db.Column(db.String(255))
    video_filename = db.Column(db.String(255))

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    postnom = db.Column(db.String(150))
    telephone = db.Column(db.String(50))
    adresse = db.Column(db.Text)
    mot_de_passe = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(150))
    photo_filename = db.Column(db.String(255))
    sexe = db.Column(db.String(20))  # M ou F
    est_abonne = db.Column(db.Boolean, default=False)
    date_abonnement = db.Column(db.DateTime)
    
    commandes = db.relationship('Commande', backref='client', lazy=True)
    notifications = db.relationship('Notification', backref='client', lazy=True)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    id_client = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    id_produit = db.Column(db.Integer, db.ForeignKey('produit.id'))
    titre = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text)
    type_notification = db.Column(db.String(50), default='nouveau_produit')  # nouveau_produit, promotion, etc
    est_lue = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    produit = db.relationship('Produit', backref='notifications', lazy=True)

class Commande(db.Model):
    __tablename__ = 'commande'
    id = db.Column(db.Integer, primary_key=True)
    id_client = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date = db.Column(db.DateTime, default=db.func.current_timestamp())
    statut = db.Column(db.String(50), default='en attente')
    rdv_adresse = db.Column(db.Text)
    
    details = db.relationship('DetailsCommande', backref='commande', lazy=True)

class DetailsCommande(db.Model):
    __tablename__ = 'details_commande'
    id = db.Column(db.Integer, primary_key=True)
    id_commande = db.Column(db.Integer, db.ForeignKey('commande.id'), nullable=False)
    id_produit = db.Column(db.Integer, db.ForeignKey('produit.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False)
    prix_unitaire = db.Column(db.Numeric(10, 2), nullable=False)

    produit = db.relationship('Produit', backref='details_commande', lazy=True)

class Paiement(db.Model):
    __tablename__ = 'paiements'
    id = db.Column(db.Integer, primary_key=True)
    id_commande = db.Column(db.Integer, db.ForeignKey('commande.id'), nullable=False)
    mode_paiement = db.Column(db.String(50), nullable=False)
    statut = db.Column(db.String(50), default='en attente')

class Avis(db.Model):
    __tablename__ = 'avis'
    id = db.Column(db.Integer, primary_key=True)
    id_produit = db.Column(db.Integer, nullable=False)  # Sans ForeignKey stricte
    auteur = db.Column(db.String(100), default="Anonyme")
    commentaire = db.Column(db.Text)
    is_liked = db.Column(db.Boolean, default=False)
    date = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relation virtuelle pour l'admin
    produit = db.relationship('Produit', primaryjoin="Avis.id_produit == Produit.id", foreign_keys="Avis.id_produit", backref='avis_list', lazy=True)

class PushSubscription(db.Model):
    """Stocke les abonnements Push des navigateurs des clients"""
    __tablename__ = 'push_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.Text, unique=True, nullable=False)
    p256dh = db.Column(db.Text, nullable=False)
    auth = db.Column(db.Text, nullable=False)
    date_creation = db.Column(db.DateTime, default=db.func.current_timestamp())

# --- Initialisation de la Base de Données ---
with app.app_context():
    try:
        # Création de toutes les tables définies dans les modèles ci-dessus
        db.create_all()
        
        # --- Initialisation des catégories par défaut si elles n'existent pas ---
        noms_categories = ["Informatique", "Électronique", "Beauté", "Maison", "Téléphones", "Homme", "Femme"]
        for nom in noms_categories:
            exist = Categorie.query.filter_by(nom=nom).first()
            if not exist:
                nouvelle_cat = Categorie(nom=nom)
                db.session.add(nouvelle_cat)
        db.session.commit()

        # Migrations manuelles pour ajouter des colonnes si vous mettez à jour votre code plus tard
        with db.engine.connect() as conn:
            # Liste des colonnes à vérifier/ajouter (Table, Nom Colonne, Type)
            migrations = [
                ('produit', 'video_filename', 'VARCHAR(255)'),
                ('commande', 'rdv_adresse', 'TEXT'),
                ('clients', 'postnom', 'VARCHAR(150)'),
                ('clients', 'telephone', 'VARCHAR(50)'),
                ('clients', 'adresse', 'TEXT'),
                ('clients', 'email', 'VARCHAR(150)'),
                ('clients', 'sexe', 'VARCHAR(20)'),
                ('clients', 'photo_filename', 'VARCHAR(255)'),
                ('clients', 'est_abonne', 'BOOLEAN DEFAULT FALSE'),
                ('clients', 'date_abonnement', 'TIMESTAMP')
            ]
            for table, col, col_type in migrations:
                try:
                    conn.execute(db.text(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}'))
                except Exception as e:
                    print(f"Migration ignorée pour {table}.{col} : {e}")
            try:
                conn.commit()
            except Exception:
                pass
    except Exception as e:
        print(f"Erreur d'init DB : {e}")

# --- Décorateurs et Utilitaires ---
from flask import send_from_directory

    # On laisse Flask gérer /static/ via la config ci-dessus

@app.errorhandler(500)
def handle_500_error(e):
    # Ce gestionnaire affichera TOUJOURS l'erreur exacte au lieu de la page générique
    return f"<h3>ERREUR CRITIQUE DÉTECTÉE</h3><p>{e}</p><pre>{traceback.format_exc()}</pre>", 500

@app.route('/debug/test')
def debug_test():
    results = []
    
    # 1. Test Base de données
    try:
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        results.append("✅ BASE DE DONNÉES : Connectée")
    except Exception as e:
        results.append(f"❌ BASE DE DONNÉES : Erreur ({e})")

    # 2. Test Supabase
    if supabase:
        try:
            # Test simple : lister les buckets
            buckets = supabase.storage.list_buckets()
            if any(b.name == BUCKET_NAME for b in buckets):
                results.append(f"✅ SUPABASE : Client OK, Bucket '{BUCKET_NAME}' trouvé")
            else:
                results.append(f"⚠️ SUPABASE : Client OK, mais Bucket '{BUCKET_NAME}' NON TROUVÉ")
        except Exception as e:
            results.append(f"❌ SUPABASE : Erreur lors du test de stockage ({e})")
    else:
        results.append("❌ SUPABASE : Client non initialisé (Vérifiez vos clés)")

    # 3. Test des dossiers locaux
    upload_path = os.path.join(base_dir, 'static', 'uploads')
    if os.path.exists(upload_path):
        results.append(f"✅ DOSSIER UPLOADS : Présent ({upload_path})")
    else:
        results.append(f"⚠️ DOSSIER UPLOADS : Absent (Sera créé au premier upload)")

    # 4. Vérification Versions & Env
    results.append(f"ℹ️ PYTHON_VERSION : {os.environ.get('PYTHON_VERSION', 'Défaut')}")
    
    return "<br>".join(results)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Utilitaire : Enregistrer une image base64 dans uploads ---
def save_base64_image(data_uri, folder='static/uploads'):
    if not data_uri or not data_uri.startswith('data:image/'):
        return None
    try:
        header, encoded = data_uri.split(',', 1)
        match = re.match(r'data:(image/[^;]+);base64', header)
        if not match:
            return None
        image_type = match.group(1).split('/')[-1]
        if image_type == 'jpeg':
            image_type = 'jpg'
        filename = f"abonne_{os.urandom(4).hex()}.{image_type}"
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)
        with open(path, 'wb') as f:
            f.write(base64.b64decode(encoded))
        return filename
    except Exception as e:
        print(f"Erreur de sauvegarde d'image base64 : {e}")
        return None

# --- Utilitaire : Envoyer une notification push à tous les abonnés ---
def envoyer_push_tous(titre, corps, url='/', image=None):
    """Envoie une notification Web Push à tous les navigateurs abonnés"""
    if not PUSH_ENABLED:
        print("pywebpush non disponible, notification ignorée.")
        return
    subscriptions = PushSubscription.query.all()
    payload = json.dumps({"title": titre, "body": corps, "url": url, "image": image})
    erreurs = []
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth}
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as e:
            # Si l'abonnement est expiré (410), on le supprime
            if e.response and e.response.status_code in (404, 410):
                db.session.delete(sub)
                db.session.commit()
            else:
                erreurs.append(str(e))
        except Exception as e:
            erreurs.append(str(e))
    if erreurs:
        print(f"Erreurs push: {erreurs}")

# --- Routes API Web Push ---
@app.route('/api/push/vapid-public-key', methods=['GET'])
def get_vapid_public_key():
    """Retourne la clé publique VAPID pour le frontend"""
    return jsonify({"publicKey": VAPID_PUBLIC_KEY})

@app.route('/api/push/subscribe', methods=['POST'])
def push_subscribe():
    """Sauvegarde un abonnement push navigateur"""
    try:
        data = request.json
        endpoint = data.get('endpoint')
        p256dh = data.get('keys', {}).get('p256dh')
        auth = data.get('keys', {}).get('auth')
        if not endpoint or not p256dh or not auth:
            return jsonify({"error": "Données incomplètes"}), 400
        # Vérifie si déjà enregistré
        existant = PushSubscription.query.filter_by(endpoint=endpoint).first()
        if not existant:
            sub = PushSubscription(endpoint=endpoint, p256dh=p256dh, auth=auth)
            db.session.add(sub)
            db.session.commit()
        return jsonify({"success": True}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/push/unsubscribe', methods=['POST'])
def push_unsubscribe():
    """Supprime un abonnement push"""
    try:
        data = request.json
        endpoint = data.get('endpoint')
        sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
        if sub:
            db.session.delete(sub)
            db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- Routes API pour les Abonnements ---
@app.route('/api/abonne/inscription', methods=['POST'])
def inscription_abonne():
    """Inscrire un nouveau client abonné"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        nom = data.get('nom', 'Anonyme').strip()
        postnom = data.get('postnom', '').strip()
        sexe = data.get('sexe', '').strip()
        telephone = data.get('telephone', '').strip()

        # Validation : email obligatoire
        if not email:
            return jsonify({"error": "L'adresse email est obligatoire."}), 400

        # Vérification stricte : un email = un seul abonnement
        # On normalise l'email en minuscules pour éviter les doublons type "Test@gmail.com" == "test@gmail.com"
        client_existant = Client.query.filter(
            db.func.lower(Client.email) == email
        ).first()

        if client_existant:
            if client_existant.est_abonne:
                return jsonify({"error": "Cette adresse email est déjà inscrite à nos notifications. Vous êtes déjà abonné(e) !"}), 400
            else:
                # Client existant non abonné → on l'abonne
                client_existant.nom = nom
                client_existant.postnom = postnom
                client_existant.sexe = sexe
                client_existant.telephone = telephone
                if data.get('photo_data'):
                    photo_filename = save_base64_image(data.get('photo_data'))
                    if photo_filename:
                        client_existant.photo_filename = photo_filename
                client_existant.est_abonne = True
                client_existant.date_abonnement = db.func.current_timestamp()
                db.session.commit()
                client_id = client_existant.id
        else:
            # Nouveau client → création
            photo_filename = None
            if data.get('photo_data'):
                photo_filename = save_base64_image(data.get('photo_data'))

            nouveau_client = Client(
                nom=nom,
                postnom=postnom,
                sexe=sexe,
                email=email,
                telephone=telephone,
                photo_filename=photo_filename,
                est_abonne=True,
                date_abonnement=db.func.current_timestamp()
            )
            db.session.add(nouveau_client)
            db.session.commit()
            client_id = nouveau_client.id

        return jsonify({
            "success": True,
            "message": "Inscription réussie! Bienvenue parmi nos abonnés.",
            "client_id": client_id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/abonne/<int:client_id>/notifications', methods=['GET'])
def get_notifications(client_id):
    """Récupérer les notifications d'un client"""
    try:
        notifications = Notification.query.filter_by(id_client=client_id).order_by(
            Notification.date_creation.desc()
        ).all()
        
        return jsonify({
            "notifications": [{
                "id": n.id,
                "titre": n.titre,
                "message": n.message,
                "type": n.type_notification,
                "est_lue": n.est_lue,
                "date": n.date_creation.strftime('%d/%m/%Y %H:%M'),
                "id_produit": n.id_produit,
                "produit_nom": n.produit.nom if n.produit else None,
                "produit_image": n.produit.image_filename if n.produit else None
            } for n in notifications]
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/abonne/notification/<int:notification_id>/marquer-lue', methods=['POST'])
def marquer_notification_lue(notification_id):
    """Marquer une notification comme lue"""
    try:
        notification = Notification.query.get(notification_id)
        if not notification:
            return jsonify({"error": "Notification non trouvée"}), 404
        
        notification.est_lue = True
        db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/abonne/<int:client_id>/info', methods=['GET'])
def get_abonne_info(client_id):
    """Récupérer les infos d'un abonné"""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({"error": "Client non trouvé"}), 404
        
        return jsonify({
            "id": client.id,
            "nom": client.nom,
            "postnom": client.postnom,
            "email": client.email,
            "sexe": client.sexe,
            "telephone": client.telephone,
            "adresse": client.adresse,
            "est_abonne": client.est_abonne,
            "date_abonnement": client.date_abonnement.strftime('%d/%m/%Y') if client.date_abonnement else None,
            "nb_non_lues": Notification.query.filter_by(id_client=client_id, est_lue=False).count()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/abonne/<int:client_id>/desabonner', methods=['POST'])
def desabonner_client(client_id):
    """Désabonner un client"""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({"error": "Client non trouvé"}), 404
        
        client.est_abonne = False
        db.session.commit()
        return jsonify({"success": True, "message": "Vous avez été désabonné"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- Routes ---
@app.route('/')
def index():
    # 1. On ne garde que les vrais produits de la base de données
    produits_list = []
    
    # 2. Ajout des vrais produits issus de la base de données
    cats = []
    try:
        cats = Categorie.query.all()
        map_categories = {c.id: c.nom for c in cats}
        produits_db = Produit.query.all()
        
        for p in produits_db:
            try:
                cat_name = map_categories.get(p.id_categorie, "VIP Collection")
                try:
                    prix_final = float(p.prix) if p.prix else 0.0
                except:
                    prix_final = 0.0

                # Détermination de l'URL de l'image (Locale ou Supabase)
                img_path = p.image_filename
                if img_path:
                    if not img_path.startswith('http'):
                        img_path = f'/static/uploads/{img_path}'
                else:
                    img_path = 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600'

                produits_list.append({
                    'id': p.id,
                    'nom': p.nom or "Produit",
                    'categorie': cat_name,
                    'prix': prix_final,
                    'note': 5.0,
                    'avis': 1,
                    'image': img_path,
                    'video': f'/static/uploads/{p.video_filename}' if p.video_filename else None
                })
            except:
                continue

    except Exception as db_err:
        print(f"Erreur DB Index : {db_err}")

    return render_template('accueil.html', 
                         produits_json=json.dumps(produits_list), 
                         all_categories=[c.nom for c in cats] if cats else ["Tout"])
# --- Routes d'Authentification Admin ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Gère la connexion à l'interface d'administration
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # authentification admin 
        if username == 'bunnyjaiteh85' and password == 'lamin1985':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Identifiants incorrects.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Déconnexion de la session admin
    session.pop('admin_logged_in', None)
    return redirect(url_for('login'))

# --- Routes Boutique (Client) ---

@app.route('/')
def home():
    # Page principale de la boutique (Affichage des produits)
    produits = Produit.query.all()
    categories = [c.nom for c in Categorie.query.all()]
    return render_template('accueil.html', produits=produits, categories=categories)

@app.route('/produits', methods=['GET', 'POST'])
@admin_required
def liste_produits():
    if request.method == 'POST':
        try:
            nom = request.form.get('nom')
            description = request.form.get('description', '')
            prix = request.form.get('prix')
            stock = request.form.get('stock')
            id_categorie = request.form.get('id_categorie')
            
            # Conversion sécurisée pour PostgreSQL
            try:
                prix_val = float(prix) if prix else 0.0
                stock_val = int(stock) if stock else 0
                cat_id_val = int(id_categorie) if id_categorie else None
            except ValueError:
                return "Erreur : Le prix et le stock doivent être des nombres.", 400

            image_filename = None
            if 'image' in request.files and supabase:
                file = request.files['image']
                if file and file.filename != '':
                    try:
                        filename = secure_filename(file.filename)
                        unique_filename = f"{os.urandom(4).hex()}_{filename}"
                        
                        file_data = file.read()
                        supabase.storage.from_(BUCKET_NAME).upload(
                            path=unique_filename,
                            file=file_data,
                            file_options={"content-type": file.content_type}
                        )
                        
                        res = supabase.storage.from_(BUCKET_NAME).get_public_url(unique_filename)
                        # Correction : accéder à l'attribut public_url au lieu de l'objet complet
                        image_filename = str(res) if isinstance(res, str) else getattr(res, 'public_url', str(res))
                    except Exception as upload_err:
                        print(f"Erreur Upload Supabase : {upload_err}")
                elif not supabase:
                    print("Supabase n'est pas initialisé, upload impossible.")

            video_filename = None
            if 'video' in request.files:
                vfile = request.files['video']
                if vfile and vfile.filename != '':
                    vfilename = secure_filename(vfile.filename)
                    upload_folder = os.path.join('static', 'uploads')
                    os.makedirs(upload_folder, exist_ok=True)
                    vfile.save(os.path.join(upload_folder, vfilename))
                    video_filename = vfilename

            nouveau_produit = Produit(
                nom=nom, 
                description=description,
                prix=prix_val, 
                stock=stock_val, 
                id_categorie=cat_id_val, 
                image_filename=image_filename, 
                video_filename=video_filename
            )
            db.session.add(nouveau_produit)
            db.session.commit()
            
            # --- Créer les notifications DB pour tous les clients abonnés ---
            clients_abonnes = Client.query.filter_by(est_abonne=True).all()
            for client in clients_abonnes:
                notification = Notification(
                    id_client=client.id,
                    id_produit=nouveau_produit.id,
                    titre=f"Nouveau produit: {nom}",
                    message=f"Un nouveau produit '{nom}' vient d'être ajouté à notre boutique! Découvrez-le maintenant.",
                    type_notification='nouveau_produit'
                )
                db.session.add(notification)
            db.session.commit()

            push_image = None
            if image_filename:
                if image_filename.startswith('http'):
                    push_image = image_filename
                else:
                    push_image = f"/static/uploads/{image_filename}"

            # --- Envoyer les Web Push Notifications (téléphone/navigateur) ---
            try:
                envoyer_push_tous(
                    titre=f"Nouveau produit chez LA GRACE SEEMIN !",
                    corps=f"{nom} vient d'arriver dans notre boutique. Découvrez-le maintenant !",
                    url="/",
                    image=push_image
                )
            except Exception as push_err:
                print(f"Erreur push: {push_err}")
            
            return redirect(url_for('liste_produits'))
        except Exception as e:
            db.session.rollback() # Important : annuler la transaction en cas d'échec
            return f"Erreur lors de l'ajout du produit : {e}<br><pre>{traceback.format_exc()}</pre>", 500
        
    produits = Produit.query.all()
    categories = Categorie.query.all()
    return render_template('produits.html', produits=produits, categories=categories)

@app.route('/produits/<int:id>/edit', methods=['POST'])
def edit_produit(id):
    produit = Produit.query.get_or_404(id)
    
    produit.nom = request.form.get('nom', produit.nom)
    produit.prix = request.form.get('prix', produit.prix)
    produit.stock = request.form.get('stock', produit.stock)
    produit.id_categorie = request.form.get('id_categorie', produit.id_categorie)
    
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '':
            try:
                filename = secure_filename(file.filename)
                unique_filename = f"{os.urandom(4).hex()}_{filename}"
                
                # Upload vers Supabase
                file_data = file.read()
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=unique_filename,
                    file=file_data,
                    file_options={"content-type": file.content_type}
                )
                
                # URL Publique
                res = supabase.storage.from_(BUCKET_NAME).get_public_url(unique_filename)
                produit.image_filename = str(res) if isinstance(res, str) else getattr(res, 'public_url', str(res))
            except Exception as e:
                db.session.rollback()
                print(f"Erreur Edit Supabase : {e}")

    if 'video' in request.files:
        vfile = request.files['video']
        if vfile and vfile.filename != '':
            vfilename = secure_filename(vfile.filename)
            # On conserve le stockage local pour la vidéo pour le moment (plus lourd)
            # ou on pourrait aussi le migrer si besoin.
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            vfile.save(os.path.join(upload_folder, vfilename))
            produit.video_filename = vfilename
            
    db.session.commit()
    return jsonify({"success": True})

@app.route('/produits/<int:id>/delete', methods=['POST'])
def delete_produit(id):
    try:
        produit = Produit.query.get_or_404(id)
        
        # 1. Supprimer les avis associés
        Avis.query.filter_by(id_produit=produit.id).delete()
        
        # 2. Supprimer l'image de Supabase Storage si elle existe
        if produit.image_filename and "supabase.co" in produit.image_filename and supabase:
            try:
                # Extraire le nom du fichier de l'URL
                # Format URL: https://[...]/storage/v1/object/public/[BUCKET]/[FILENAME]
                filename = produit.image_filename.split('/')[-1]
                supabase.storage.from_(BUCKET_NAME).remove([filename])
            except Exception as se:
                print(f"Erreur Supabase Storage Delete : {se}")
        
        # 3. Supprimer le produit de la DB
        db.session.delete(produit)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/clients', methods=['GET'])
@admin_required
def liste_clients():
    return redirect(url_for('admin_abonnes'))

@app.route('/commandes', methods=['GET'])
@admin_required
def liste_commandes():
    commandes = Commande.query.order_by(Commande.id.desc()).all()
    return render_template('commandes.html', commandes=commandes)

@app.route('/admin', methods=['GET'])
@admin_required
def admin_dashboard():
    total_commandes = Commande.query.count()
    en_attente = Commande.query.filter(Commande.statut.ilike('%attente%')).count()
    terminees = Commande.query.filter(Commande.statut.ilike('%termin%')).count()
    total_abonnes = Client.query.filter_by(est_abonne=True).count()
    recent_abonnes = Client.query.filter_by(est_abonne=True).order_by(Client.date_abonnement.desc()).limit(5).all()
    stats = {
        'total_commandes': total_commandes,
        'en_attente': en_attente,
        'terminees': terminees,
        'total_abonnes': total_abonnes
    }
    return render_template('admin.html', stats=stats, recent_abonnes=recent_abonnes)

# --- Liste des abonnés pour l'admin ---
@app.route('/admin/abonnes', methods=['GET'])
@admin_required
def admin_abonnes():
    abonnes = Client.query.filter_by(est_abonne=True).order_by(Client.date_abonnement.desc()).all()
    return render_template('admin_abonnes.html', abonnes=abonnes)

@app.route('/admin/commandes/<int:id>/status', methods=['POST'])
def update_commande_status(id):
    data = request.json
    nouveau_statut = data.get('statut')
    commande = Commande.query.get(id)
    if not commande:
        return jsonify({"error": "Commande introuvable"}), 404
        
    commande.statut = nouveau_statut
    db.session.commit()
    return jsonify({"message": "Statut mis à jour avec succès", "nouveau_statut": commande.statut}), 200

@app.route('/admin/commandes/<int:id>/rdv', methods=['POST'])
def update_commande_rdv(id):
    data = request.json
    nouveaux_rdv = data.get('rdv_adresse')
    commande = Commande.query.get(id)
    if not commande:
        return jsonify({"error": "Commande introuvable"}), 404
        
    commande.rdv_adresse = nouveaux_rdv
    db.session.commit()
    return jsonify({"message": "Rendez-vous mis à jour avec succès"}), 200

@app.route('/admin/commandes/<int:id>/delete', methods=['POST'])
def delete_commande(id):
    commande = Commande.query.get_or_404(id)
    # Supprimer les détails de commande d'abord
    DetailsCommande.query.filter_by(id_commande=id).delete()
    # Supprimer les paiements associés
    Paiement.query.filter_by(id_commande=id).delete()
    db.session.delete(commande)
    db.session.commit()
    return jsonify({"success": True})

@app.route('/paiements', methods=['GET'])
def liste_paiements():
    return "Liste des paiements (à implémenter)"

# --- Accueil et contacts ---
@app.route('/contact', methods=['GET'])
def accueil():
    return redirect(url_for('index'))

# --- Routes d'API pour les Commandes ---
@app.route('/commandes', methods=['POST'])
def create_commande():
    data = request.json
    nouvelle_commande = Commande(id_client=data['id_client'])
    db.session.add(nouvelle_commande)
    db.session.commit()
    return jsonify({"message": "Vous avez créé une commande", "id_commande": nouvelle_commande.id}), 201

@app.route('/commandes/<int:id_commande>/produit', methods=['POST'])
def add_produit_commande(id_commande):
    data = request.json
    produit = Produit.query.get(data['id_produit'])
    
    if not produit:
        return jsonify({"error": "Produit introuvable"}), 404

    detail = DetailsCommande(
        id_commande=id_commande,
        id_produit=data['id_produit'],
        quantite=data['quantite'],
        prix_unitaire=produit.prix
    )
    db.session.add(detail)
    db.session.commit()
    return jsonify({"message": "Produit ajouté à la commande"}), 201

# --- Nouvelle API de Commande Finale ---
@app.route('/api/passer_commande', methods=['POST'])
def passer_commande():
    try:
        data = request.json
        c_info = data.get('client_info', {})
        items = data.get('panier', [])
        
        if not items:
            return jsonify({"error": "Votre panier est vide"}), 400
            
        # Créer le client
        nouveau_client = Client(
            nom=c_info.get('nom', 'Anonyme'),
            postnom=c_info.get('postnom', ''),
            telephone=c_info.get('telephone', ''),
            adresse=c_info.get('adresse', ''),
            mot_de_passe="guest"
        )
        db.session.add(nouveau_client)
        db.session.commit()
        
        # Créer la commande
        nouvelle_commande = Commande(id_client=nouveau_client.id, statut='en attente')
        db.session.add(nouvelle_commande)
        db.session.commit()
        
        # Ajouter les détails
        for item in items:
            p_id = item['id']
            # On vérifie si c'est un produit réel ou exemple
            prix = float(item.get('prix', 0))
            
            # On ne met pas de ForeignKey stricte si c'est un ID d'exemple (>= 1000)
            # Mais DetailsCommande a une FK vers produit.id. 
            # Pour que ça marche avec les produits d'exemple, il faudrait qu'ils soient en DB.
            # On va ignorer la FK stricte pour les tests ou s'assurer que l'item existe.
            # Si le produit n'existe pas en DB, on crée une entrée ou on ignore la FK.
            # Ici on va juste tenter d'ajouter.
            
            detail = DetailsCommande(
                id_commande=nouvelle_commande.id,
                id_produit=p_id if p_id < 1000 else 1, # Fallback vers ID 1 pour les exemples sinon SQLite râle
                quantite=item.get('quantite', 1),
                prix_unitaire=prix
            )
            db.session.add(detail)
            
        db.session.commit()
        return jsonify({"success": True, "id_commande": nouvelle_commande.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- Routes d'API pour les Avis ---
@app.route('/api/avis', methods=['POST'])
def add_avis():
    data = request.json
    
    # Handle removal of a like dynamically
    if data.get('action') == 'unlike':
        avis_like = Avis.query.filter_by(id_produit=data.get('id_produit'), is_liked=True).first()
        if avis_like:
            db.session.delete(avis_like)
            db.session.commit()
        return jsonify({"success": True}), 200

    nouvel_avis = Avis(
        id_produit=data.get('id_produit'),
        auteur=data.get('auteur', 'Anonyme') or 'Anonyme',
        commentaire=data.get('commentaire', ''),
        is_liked=data.get('is_liked', False)
    )
    db.session.add(nouvel_avis)
    db.session.commit()
    return jsonify({"message": "Avis ajouté avec succès", "id": nouvel_avis.id}), 201

@app.route('/api/avis/produit/<int:id_produit>', methods=['GET'])
def get_avis_produit(id_produit):
    avis_list = Avis.query.filter_by(id_produit=id_produit).order_by(Avis.date.desc()).all()
    # Calculer le nombre de likes et avis
    likes = sum(1 for v in avis_list if v.is_liked)
    return jsonify({
        "likes": likes,
        "total_avis": len(avis_list),
        "commentaires": [{
            "auteur": a.auteur,
            "commentaire": a.commentaire,
            "is_liked": a.is_liked,
            "date": a.date.strftime('%d/%m/%Y')
        } for a in avis_list if a.commentaire and len(a.commentaire.strip()) > 0]
    }), 200

@app.route('/admin/avis', methods=['GET'])
@admin_required
def admin_avis():
    # On récupère les avis et on fait un join pour avoir les infos produits (images)
    avis_list = Avis.query.order_by(Avis.date.desc()).all()
    return render_template('admin_avis.html', avis_list=avis_list)

@app.route('/suivi', methods=['GET', 'POST'])
def suivi_commande():
    commande = None
    erreur = None
    if request.method == 'POST':
        query = request.form.get('query')
        if query:
            # Recherche par ID ou par téléphone du client
            if query.isdigit():
                commande = Commande.query.get(int(query))
            
            if not commande:
                # Tentative par téléphone
                client = Client.query.filter_by(telephone=query).first()
                if client:
                    commande = Commande.query.filter_by(id_client=client.id).order_by(Commande.id.desc()).first()
            
            if not commande:
                erreur = "Commande introuvable. Vérifiez le numéro ou le téléphone."
        else:
            erreur = "Veuillez entrer un numéro de commande ou de téléphone."
            
    return render_template('suivi.html', commande=commande, erreur=erreur)

# --- Lancement du serveur ---
@app.route('/api/avis/<int:id>/delete', methods=['POST'])
@admin_required
def delete_avis(id):
    # Suppression d'un avis ou d'un Like spécifique par son ID
    try:
        avis = Avis.query.get(id)
        if avis:
            db.session.delete(avis)
            db.session.commit()
            return jsonify({'success': True}), 200
        return jsonify({'success': False, 'message': 'Avis non trouvé'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    # Point d'entrée de l'application
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

