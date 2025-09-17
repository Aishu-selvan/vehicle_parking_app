from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models.file1 import db, ParkingLot, ParkingSpot, Reservation
from datetime import datetime
from math import ceil

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/dashboard')
@login_required
def dashboard():
    lots = ParkingLot.query.all()
    active_res = Reservation.query.filter_by(user_id=current_user.id, leaving_timestamp=None).first()
    return render_template('user_dashboard.html', lots=lots, active_res=active_res)

@user_bp.route('/history')
@login_required
def history():
    reservations = (Reservation.query
                    .filter_by(user_id=current_user.id)
                    .order_by(Reservation.parking_timestamp.desc())
                    .all())

    def calc_duration_and_cost(res):
        if res.leaving_timestamp and res.parking_timestamp:
            delta = res.leaving_timestamp - res.parking_timestamp
            mins = int(delta.total_seconds() // 60)
            hrs = int(mins // 60)
            mins_display = mins % 60
            duration = f"{hrs}h {mins_display}m" if hrs else f"{mins_display}m"
            lot = res.spot.lot if res.spot else None
            cost = 0
            if lot:
                total_hours = delta.total_seconds() / 3600
                hours_rounded = max(1, int(ceil(total_hours)))
                cost = hours_rounded * lot.price
            return duration, f"₹{cost:.2f}"
        else:
            return "-", "-"
    return render_template(
        'user_history.html', reservations=reservations, calc_duration_and_cost=calc_duration_and_cost
    )


@user_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    search_term = ""
    if request.method == 'POST':
        search_term = request.form.get('location', '').strip()
        if search_term:
            lots = ParkingLot.query.filter(
                (ParkingLot.address.ilike(f"%{search_term}%")) |
                (ParkingLot.prime_location_name.ilike(f"%{search_term}%"))
            ).all()
        else:
            lots = ParkingLot.query.all()
    else:
        lots = ParkingLot.query.all()   # On initial page load, show all lots

    return render_template('user_search.html', lots=lots, search_term=search_term)




@user_bp.route('/release', methods=['GET', 'POST'])
@login_required
def release_page():
    res = Reservation.query.filter_by(user_id=current_user.id, leaving_timestamp=None).first()
    if not res:
        flash("No active reservation to release.")
        return redirect(url_for('user.dashboard'))

    # Calculate total cost (same logic as before)
    total_cost = None
    if res.parking_timestamp:
        now = datetime.utcnow()
        delta = now - res.parking_timestamp
        hours = delta.total_seconds() / 3600
        hours_rounded = max(1, int(ceil(hours)))
        total_cost = hours_rounded * res.spot.lot.price if res.spot and res.spot.lot else 0

    if request.method == 'POST':
        res.leaving_timestamp = db.func.now()
        spot = ParkingSpot.query.get(res.spot_id)
        spot.status = 'A'
        res.parking_cost = total_cost
        db.session.commit()
        flash("Spot released. Have a great day!")
        return redirect(url_for('user.dashboard'))

    return render_template('release_confirm.html', reservation=res, total_cost=total_cost)




@user_bp.route('/release/<int:res_id>', methods=['POST'])
@login_required
def release_spot(res_id):
    res = Reservation.query.get_or_404(res_id)
    if res.user_id != current_user.id or res.leaving_timestamp is not None:
        flash('Invalid operation.')
        return redirect(url_for('user.dashboard'))
    res.leaving_timestamp = db.func.now()
    spot = ParkingSpot.query.get(res.spot_id)
    spot.status = 'A'
    db.session.commit()
    flash('Spot released. Thank you!')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/lot/<int:lot_id>')
@login_required
def lot_detail(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
    return render_template('user_lot_detail.html', lot=lot, spots=spots)




@user_bp.route('/reserve/<int:lot_id>', methods=['POST'])
@login_required
def reserve_spot(lot_id):

    
    # Don't allow multiple active reservations
    active_res = Reservation.query.filter_by(user_id=current_user.id, leaving_timestamp=None).first()
    if active_res:
        flash('You already have an active reservation.')
        return redirect(url_for('user.dashboard'))

    # Find the first available spot in this lot
    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if not spot:
        flash('No available spots in this lot.')
        return redirect(url_for('user.dashboard'))

    # Get vehicle number from submitted form
    vehicle_number = request.form.get('vehicle_number', '').strip()
    if not vehicle_number or len(vehicle_number) < 6:
        flash('Vehicle number is required and must be at least 6 characters.')
        return redirect(url_for('user.dashboard'))

    # Create reservation with vehicle number
    spot.status = 'O'
    reservation = Reservation(
        spot_id=spot.id,
        user_id=current_user.id,
        vehicle_number=vehicle_number
    )
    db.session.add(reservation)
    db.session.commit()
    flash(f'Reservation successful! Spot #{spot.id} in Lot "{spot.lot.prime_location_name}".')
    return redirect(url_for('user.dashboard'))




@user_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # You can add actual profile editing logic here if needed
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        if full_name:
            current_user.full_name = full_name
        if email:
            current_user.username = email
        db.session.commit()
        flash("Profile updated successfully.")
        return redirect(url_for('user.edit_profile'))
    return render_template('edit_profile.html', user=current_user)






@user_bp.route('/summary')
@login_required
def summary():
    # get all user's reservations
    reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    # summary: count per lot name
    from collections import Counter
    lot_names = [res.spot.lot.prime_location_name for res in reservations if res.spot and res.spot.lot]
    count_per_lot = Counter(lot_names)
    bar_labels = list(count_per_lot.keys())
    bar_values = list(count_per_lot.values())
    return render_template('user_summary.html', bar_labels=bar_labels, bar_values=bar_values)

