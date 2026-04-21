
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import sys

# Ensure UTF-8 output if possible, but let's just avoid emojis
app = Flask(__name__)
SUPABASE_DB_URL = "postgresql://postgres.mfdotnwtjbqqnkgcblph:Lee%23%23%23%40hrjkz@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or SUPABASE_DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def fix_schema():
    with app.app_context():
        migrations = [
            ('produit', 'video_filename', 'VARCHAR(255)'),
            ('commande', 'rdv_adresse', 'TEXT'),
            ('clients', 'postnom', 'VARCHAR(150)'),
            ('clients', 'telephone', 'VARCHAR(50)'),
            ('clients', 'adresse', 'TEXT'),
            ('clients', 'email', 'VARCHAR(150)'),
            ('clients', 'sexe', 'VARCHAR(20)'),
            ('clients', 'est_abonne', 'BOOLEAN DEFAULT FALSE'),
            ('clients', 'date_abonnement', 'TIMESTAMP')
        ]
        
        for table, col, col_type in migrations:
            print(f"Checking {table}.{col}...")
            try:
                # Check if column exists
                query = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='{col}'")
                result = db.session.execute(query).fetchone()
                
                if not result:
                    print(f"Adding column {col} to {table}...")
                    db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                    db.session.commit()
                    print(f"DONE: Added {col}")
                else:
                    print(f"INFO: {col} already exists")
            except Exception as e:
                print(f"ERROR with {table}.{col}: {e}")
                db.session.rollback()

if __name__ == "__main__":
    fix_schema()
