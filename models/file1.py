from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ----- User Table -----
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)  # could be email
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'admin' or 'user'
    full_name = db.Column(db.String(120), nullable=False)
    reservations = db.relationship('Reservation', back_populates='user')

    def __repr__(self):
        return f"<User {self.username}>"

# ----- ParkingLot Table -----
class ParkingLot(db.Model):
    __tablename__ = 'parking_lots'
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    maximum_number_of_spots = db.Column(db.Integer, nullable=False)
    spots = db.relationship('ParkingSpot', back_populates='lot', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ParkingLot {self.prime_location_name}>"

# ----- ParkingSpot Table -----
class ParkingSpot(db.Model):
    __tablename__ = 'parking_spots'
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
    status = db.Column(db.String(1), default='A')  # 'A' = Available, 'O' = Occupied
    lot = db.relationship('ParkingLot', back_populates='spots')
    reservations = db.relationship('Reservation', back_populates='spot')

    def __repr__(self):
        return f"<ParkingSpot {self.id} (Lot {self.lot_id}) {self.status}>"

# ----- Reservation Table -----
class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spots.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parking_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    parking_cost = db.Column(db.Float, nullable=True)
    vehicle_number = db.Column(db.String(32), nullable=True)

    

    user = db.relationship('User', back_populates='reservations')
    spot = db.relationship('ParkingSpot', back_populates='reservations')

    def __repr__(self):
        return f"<Reservation {self.id} (User {self.user_id} - Spot {self.spot_id})>"
