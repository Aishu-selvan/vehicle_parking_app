from flask import Blueprint, render_template, request, redirect, url_for, flash  
from flask import jsonify
from flask_login import login_required, current_user
from models.file1 import db, User, ParkingLot, ParkingSpot, Reservation
from math import ceil
from sqlalchemy import or_

admin_bp = Blueprint('admin', __name__)

# --- ADMIN DASHBOARD ---
@admin_bp.route('/admin')
@login_required
def dashboard():
    if current_user.role != 'admin':
        return "Not Authorized", 403
    lots = ParkingLot.query.all()
    users = User.query.filter(User.role != 'admin').all()
    total_lots = len(lots)
    total_users = len(users)        # <-- FIXED HERE
    total_spots = ParkingSpot.query.count()
    total_reservations = Reservation.query.count()
    total_revenue = db.session.query(db.func.sum(Reservation.parking_cost)).scalar() or 0
    total_revenue = f"₹{total_revenue:.2f}"
    return render_template(
        'admin_dashboard.html',
        lots=lots, users=users,
        total_lots=total_lots,
        total_users=total_users,
        total_spots=total_spots,
        total_reservations=total_reservations,
        total_revenue=total_revenue
    )



# --- CREATE LOT ---
@admin_bp.route('/admin/lots/add', methods=['GET', 'POST'])
@login_required
def lot_add():
    if current_user.role != 'admin':
        return "Not Authorized", 403
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pincode = request.form['pincode']
        price = float(request.form['price'])
        max_spots = int(request.form['max_spots'])
        new_lot = ParkingLot(
            prime_location_name=name,
            address=address,
            pin_code=pincode,
            price=price,
            maximum_number_of_spots=max_spots
        )
        db.session.add(new_lot)
        db.session.commit()
        # Auto-create spots
        for _ in range(max_spots):
            db.session.add(ParkingSpot(lot_id=new_lot.id, status='A'))
        db.session.commit()
        flash('Parking lot created (and spots auto-generated).')
        return redirect(url_for('admin.dashboard'))
    return render_template('lot_form.html', action='add')

# --- EDIT LOT ---
@admin_bp.route('/admin/lots/<int:lot_id>/edit', methods=['GET', 'POST'])
@login_required
def lot_edit(lot_id):
    if current_user.role != 'admin':
        return "Not Authorized", 403
    lot = ParkingLot.query.get_or_404(lot_id)
    if request.method == 'POST':
        lot.prime_location_name = request.form['name']
        lot.address = request.form['address']
        lot.pin_code = request.form['pincode']
        lot.price = float(request.form['price'])
        new_max = int(request.form['max_spots'])
        delta = new_max - lot.maximum_number_of_spots
        lot.maximum_number_of_spots = new_max
        db.session.commit()
        # If admin increases max_spots, create new spots; if lowers and there are free spots, you may delete them (optional enhancement)
        if delta > 0:
            for _ in range(delta):
                db.session.add(ParkingSpot(lot_id=lot.id, status='A'))
            db.session.commit()
        flash('Parking lot updated.')
        return redirect(url_for('admin.dashboard'))
    return render_template('lot_form.html', action='edit', lot=lot)

# --- DELETE LOT (only if all spots free) ---
@admin_bp.route('/admin/lots/<int:lot_id>/delete', methods=['POST'])
@login_required
def lot_delete(lot_id):
    if current_user.role != 'admin':
        return "Not Authorized", 403
    lot = ParkingLot.query.get_or_404(lot_id)
    if any(spot.status == 'O' for spot in lot.spots):
        flash("Cannot delete: some spots are occupied.")
        return redirect(url_for('admin.dashboard'))
    db.session.delete(lot)
    db.session.commit()
    flash('Parking lot deleted.')
    return redirect(url_for('admin.dashboard'))

# --- VIEW LOT DETAIL (all spots in lot) ---
@admin_bp.route('/admin/lots/<int:lot_id>/detail')
@login_required
def lot_detail(lot_id):
    if current_user.role != 'admin':
        return "Not Authorized", 403
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
    return render_template('lot_detail.html', lot=lot, spots=spots)

# --- USERS AND THEIR SPOTS ---
@admin_bp.route('/admin/users')
@login_required
def users_list():
    if current_user.role != 'admin':
        return "Not Authorized", 403
    users = User.query.filter(User.role != 'admin').all()
    user_spots = []
    for u in users:
        active_res = Reservation.query.filter_by(user_id=u.id, leaving_timestamp=None).order_by(Reservation.id.desc()).first()
        spot = ParkingSpot.query.get(active_res.spot_id) if active_res else None
        user_spots.append((u, spot))
    return render_template('admin_users.html', user_spots=user_spots)

#admin/lots_panel'_____


@admin_bp.route('/admin/lots_panel', methods=['GET', 'POST'])
@login_required
def lots_panel():
    if current_user.role != 'admin':
        return "Not Authorized", 403
    lots = ParkingLot.query.all()
    user_search = ""
    addr_search = ""
    filtered_lots = lots

    if request.method == 'POST':
        user_search = request.form.get('user_id', '').strip()
        addr_search = request.form.get('address', '').strip()
        query = ParkingLot.query

        if user_search:
            # Show lots where this user currently has any (even past) reservation
            user = User.query.filter((User.username == user_search) | (str(User.id) == user_search)).first()
            if user:
                lot_ids = db.session.query(ParkingLot.id).join(ParkingSpot).join(Reservation).filter(Reservation.user_id==user.id).distinct()
                query = query.filter(ParkingLot.id.in_(lot_ids))
            else:
                query = query.filter(False)  # No results if user not found

        if addr_search:
            query = query.filter(
                or_(
                    ParkingLot.address.ilike(f"%{addr_search}%"),
                    ParkingLot.prime_location_name.ilike(f"%{addr_search}%"),
                    ParkingLot.pin_code.ilike(f"%{addr_search}%")
                )
            )
        filtered_lots = query.all()

    return render_template('admin_lots_panel.html',
                           lots=filtered_lots,
                           user_search=user_search,
                           addr_search=addr_search)
   
#------Admin Spot Detail Route------
from flask import request

@admin_bp.route('/admin/spot/<int:spot_id>', methods=['GET', 'POST'])
@login_required
def spot_detail(spot_id):
    if current_user.role != 'admin':
        return "Not Authorized", 403

    spot = ParkingSpot.query.get_or_404(spot_id)
    lot = ParkingLot.query.get(spot.lot_id)

    reservation = None
    user = None
    # If occupied, get the current active reservation and linked user
    if spot.status == 'O':
        reservation = Reservation.query.filter_by(spot_id=spot.id, leaving_timestamp=None).first()
        if reservation:
            user = User.query.get(reservation.user_id)

    # Handle spot deletion if POST and spot is available
    if request.method == 'POST':
        if spot.status == 'A':
            db.session.delete(spot)
            db.session.commit()
            flash('Spot deleted successfully.')
            return redirect(url_for('admin.lots_panel'))
        else:
            flash('Occupied spot cannot be deleted.')
            return redirect(url_for('admin.spot_detail', spot_id=spot.id))

    return render_template('admin_spot_detail.html',
                           spot=spot,
                           lot=lot,
                           user=user,
                           reservation=reservation)





#-----adminsummary------



@admin_bp.route('/admin/summary')
@login_required
def summary():
    if current_user.role != 'admin':
        return "Not Authorized", 403
    lots = ParkingLot.query.all()
    total_lots = len(lots)
    total_revenue = db.session.query(db.func.sum(Reservation.parking_cost)).scalar() or 0
    lot_data = [
        {
            'name': lot.prime_location_name,
            'available': sum(1 for s in lot.spots if s.status == 'A'),
            'occupied': sum(1 for s in lot.spots if s.status == 'O')
        }
        for lot in lots
    ]
    return render_template(
        'admin_summary.html',
        total_lots=total_lots,
        total_revenue=total_revenue,
        lot_data=lot_data
    )




# --- ADMIN PARKING HISTORY: All Records, Duration, Cost ---
@admin_bp.route('/admin/parking_records')
@login_required
def parking_records():
    if current_user.role != 'admin':
        return "Not authorized", 403
    reservations = (Reservation.query.order_by(Reservation.parking_timestamp.desc()).all())
    def calc_duration_and_cost(res):
        if res.leaving_timestamp and res.parking_timestamp and res.spot and res.spot.lot:
            delta = res.leaving_timestamp - res.parking_timestamp
            mins = int(delta.total_seconds() // 60)
            hrs = int(mins // 60)
            mins_display = mins % 60
            duration = f"{hrs}h {mins_display}m" if hrs else f"{mins_display}m"
            lot = res.spot.lot
            total_hours = delta.total_seconds() / 3600
            hours_rounded = max(1, int(ceil(total_hours)))
            cost = hours_rounded * lot.price
            return duration, f"₹{cost:.2f}"
        else:
            return "-", "-"
    return render_template(
        'admin_parking_records.html',
        reservations=reservations,
        calc_duration_and_cost=calc_duration_and_cost
    )
