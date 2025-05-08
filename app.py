from flask import Flask, request, redirect, url_for, render_template, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
db = SQLAlchemy(app)

# MODELLI DATABASE
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Paziente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cognome = db.Column(db.String(120), nullable=False)

class Intervento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descrizione = db.Column(db.String(255), nullable=False)

class Foto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    paziente_id = db.Column(db.Integer, db.ForeignKey('paziente.id'))
    intervento_id = db.Column(db.Integer, db.ForeignKey('intervento.id'))
    caricata_da = db.Column(db.String(80), nullable=False)
    data_ora = db.Column(db.String(50), nullable=False)
    salvata_su_gestionale = db.Column(db.Boolean, default=False)
    flag_modificato_da = db.Column(db.String(80))
    flag_modificato_data = db.Column(db.String(50))

# ROUTE AUTENTICAZIONE
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user'] = username
            return redirect(url_for('index'))
        else:
            flash("Utente o password errati")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# ROUTE PRINCIPALE
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    utenti = User.query.all()
    pazienti = Paziente.query.all()
    interventi = Intervento.query.all()
    foto = Foto.query.all()
    return render_template('index.html', utenti=utenti, pazienti=pazienti, interventi=interventi, foto=foto)

# GESTIONE UTENTI
@app.route('/user/add', methods=['POST'])
def add_user():
    password = request.form.get('password', 'defaultpass')
    user = User(
        username=request.form['username'],
        password_hash=generate_password_hash(password, method='pbkdf2:sha256')
    )
    db.session.add(user)
    db.session.commit()
    return redirect(url_for('utenti'))

@app.route('/user/delete/<int:uid>')
def delete_user(uid):
    user = User.query.get(uid)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('utenti'))

@app.route('/utenti')
def utenti():
    if 'user' not in session:
        return redirect(url_for('login'))
    utenti = User.query.all()
    return render_template('utenti.html', utenti=utenti)

# GESTIONE PAZIENTI
@app.route('/paziente/add', methods=['POST'])
def add_paziente():
    paziente = Paziente(nome=request.form['nome'], cognome=request.form['cognome'])
    db.session.add(paziente)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/paziente/delete/<int:pid>')
def delete_paziente(pid):
    paziente = Paziente.query.get(pid)
    if paziente:
        db.session.delete(paziente)
        db.session.commit()
    return redirect(url_for('index'))

# GESTIONE INTERVENTI
@app.route('/intervento/add', methods=['POST'])
def add_intervento():
    intervento = Intervento(descrizione=request.form['descrizione'])
    db.session.add(intervento)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/intervento/delete/<int:iid>')
def delete_intervento(iid):
    intervento = Intervento.query.get(iid)
    if intervento:
        db.session.delete(intervento)
        db.session.commit()
    return redirect(url_for('index'))

# UPLOAD FOTO
@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        return redirect(url_for('login'))

    file = request.files['foto']
    tipo = request.form['tipo']
    paziente_id = request.form['paziente']
    intervento_id = request.form['intervento']

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    foto = Foto(
        filename=filename,
        tipo=tipo,
        paziente_id=paziente_id,
        intervento_id=intervento_id,
        caricata_da=session['user'],
        data_ora=datetime.now().isoformat()
    )
    db.session.add(foto)
    db.session.commit()
    return redirect(url_for('index'))

# CHECKBOX LOGGING
@app.route('/foto/flag/<int:fid>', methods=['POST'])
def flag_foto(fid):
    foto = Foto.query.get(fid)
    if foto:
        foto.salvata_su_gestionale = 'salvata' in request.form
        foto.flag_modificato_da = session['user']
        foto.flag_modificato_data = datetime.now().isoformat()
        db.session.commit()
    return redirect(url_for('index'))

# DOWNLOAD FOTO
@app.route('/foto/download/<filename>')
def download_foto(filename):
    if 'user' not in session:
        return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# ELIMINA FOTO
@app.route('/foto/delete/<int:fid>', methods=['POST'])
def delete_foto(fid):
    foto = Foto.query.get(fid)
    if foto:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], foto.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        db.session.delete(foto)
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Creazione primo utente amministratore se non esiste
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password_hash=generate_password_hash('pippo123!', method='pbkdf2:sha256'))
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
