from flask import Flask, render_template
from flask_login import LoginManager, login_required, current_user
from models.file1 import db, User
from controllers.auth import auth_bp
from werkzeug.security import generate_password_hash
from controllers.admin import admin_bp
from controllers.user import user_bp
from flask_migrate import Migrate




app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


migrate = Migrate(app, db)
# Flask-Login setup
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def seed_admin():
    if not User.query.filter_by(role='admin').first():
        admin = User(username='admin', full_name='Super User', password=generate_password_hash('Admin'),
                     role='admin')
        db.session.add(admin)
        db.session.commit()
with app.app_context():
    db.create_all()
    seed_admin()

# Register the authentication blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)

# Dashboards
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return "Not authorized", 403
    return render_template('admin_dashboard.html', user=current_user)

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'user':
        return "Not authorized", 403
    return render_template('user_dashboard.html', user=current_user)

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
