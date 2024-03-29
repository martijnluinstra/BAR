import json
from datetime import datetime
from functools import wraps

from flask import abort, request, render_template, redirect, url_for, current_app, has_request_context, jsonify
from flask_login import login_user
from flask_coverapi import current_user, login_url
from sqlalchemy.exc import IntegrityError

from bar import db
from bar.pos.models import Activity, Product, Participant, Purchase
from bar.auction.models import AuctionPurchase

from . import bp
from .forms import ActivityForm, ActivityConfirmForm, ImportForm


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_app.config.get('STAND_ALONE', False):
            return func(*args, **kwargs)
        elif not current_user.is_authenticated:
            print(current_user, flush=True)
            return redirect(login_url())
        elif not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)
    return decorated_view


@bp.route('/', methods=['GET'])
@bp.route('/activities', methods=['GET'])
@admin_required
def list_activities():
    activities = Activity.query.all()
    return render_template('admin/activity_list.html', activities=activities)


@bp.route('/activities/add', methods=['GET', 'POST'])
@admin_required
def add_activity():
    """ Try to create a new activity. """
    form = ActivityForm()
    if form.validate_on_submit():
        activity = Activity(
            name=form.name.data, 
            passcode=form.passcode.data, 
            active=form.active.data
        )
        db.session.add(activity)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.passcode.errors.append('Please provide a unique passcode!')
            return render_template('admin/activity_form.html', form=form, mode='add')
        else:
            return redirect(url_for('admin.list_activities'))
    return render_template('admin/activity_form.html', form=form, mode='add')


@bp.route('/activities/import', methods=['GET', 'POST'])
@admin_required
def import_activity():
    form = ImportForm()
    if form.validate_on_submit():
        try: 
            data = json.load(form.import_file.data)
            if not form.name.data:
                form.name.data = data['name']
            if not form.passcode.data:
                form.passcode.data = data['passcode']
            _load_activity(data, form.name.data, form.passcode.data)
        except IntegrityError:
            db.session.rollback()
            form.passcode.errors.append('Please provide a unique passcode!')
        except Exception as e:
            db.session.rollback()
            form.import_file.errors.append(str(e))
        else:
            return redirect(url_for('admin.list_activities'))
    return render_template('admin/activity_import_form.html', form=form)


def _load_activity(data, name=None, passcode=None):
    if not name:
        name = data['name']
    if not passcode:
        passcode = data['passcode']

    activity = Activity(
            name=name,
            passcode=passcode,
            **data['settings']
        )
    
    db.session.add(activity)
    db.session.flush()

    products = {}
    participants = {}

    for product in data['products']:
        p_id = str(product['id'])
        del product['id']
        product['activity_id'] = activity.id
        products[p_id] = Product(**product)
        db.session.add(products[p_id])

    for participant in data['participants']:
        p_id = str(participant['id'])
        del participant['id']
        if participant['birthday']:
            birthday = datetime.strptime(participant['birthday'], "%Y-%m-%dT%H:%M:%S"),
        else:
            birthday = None
        del participant['birthday']
        participant['activity_id'] = activity.id
        participants[p_id] = Participant(birthday=birthday, **participant)
        db.session.add(participants[p_id])

    db.session.flush()

    for purchase in data['pos_purchases']:
        p = Purchase(
            participant_id=participants[str(purchase['participant_id'])].id,
            activity_id=activity.id,
            product_id=products[str(purchase['product_id'])].id,
            timestamp=datetime.strptime(purchase['timestamp'], "%Y-%m-%dT%H:%M:%S"),
            undone=purchase['undone']
        )
        db.session.add(p)

    for purchase in data['auction_purchases']:
        p = AuctionPurchase(
            participant_id=participants[str(purchase['participant_id'])].id,
            activity_id=activity.id,
            description=purchase['description'],
            price=purchase['price'],
            timestamp=datetime.strptime(purchase['timestamp'], "%Y-%m-%dT%H:%M:%S"),
            undone=purchase['undone']
        )
        db.session.add(p)

    db.session.commit()


@bp.route('/activities/<int:activity_id>', methods=['GET'])
@admin_required
def view_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if activity.is_archived:
        stats = json.loads(activity.archived_stats)
    else:
        pos_purchases_query = db.session.query(
                db.func.sum(Product.price).label('amount'), 
                db.func.count(Product.price).label('units')
            )\
            .join(Purchase, Purchase.product_id == Product.id)\
            .filter(Purchase.activity_id == activity.id)\
            .filter(Purchase.undone == False)
        auction_purchases_query = db.session.query(
                db.func.sum(AuctionPurchase.price).label('amount'), 
                db.func.count(AuctionPurchase.price).label('units')
            )\
            .filter(AuctionPurchase.activity_id == activity.id)\
            .filter(AuctionPurchase.undone == False)
        participants_with_purchase = db.session.query(
            db.func.count(db.distinct(Purchase.participant_id))
        ).filter_by(activity_id=activity.id).scalar()
        stats = {
            'participants': {
                'total': Participant.query.filter_by(activity_id=activity.id).count(),
                'with_purchase': participants_with_purchase,
            },
            'pos_purchases_total': pos_purchases_query.first(),
            'pos_purchases_products': pos_purchases_query.add_column(Product.name)\
                .group_by(Product.name).order_by(db.desc('amount')).all(),
            'pos_purchases_participants': pos_purchases_query.add_column(Participant.name)\
                .join(Participant, Purchase.participant_id == Participant.id)\
                .group_by(Participant.name).order_by(db.desc('amount')).limit(10),
            'auction_purchases_total': auction_purchases_query.first(),
            'auction_purchases_participants': auction_purchases_query.add_column(Participant.name)\
                .join(Participant, AuctionPurchase.participant_id == Participant.id)\
                .group_by(Participant.name).order_by(db.desc('amount')).limit(10)
        }
    return render_template('admin/activity_details.html', activity=activity, stats=stats)


@bp.route('/activities/<int:activity_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if activity.is_archived:
        abort(403)
    form = ActivityForm(obj=activity)
    if form.validate_on_submit():
        form.populate_obj(activity)
        try:
            db.session.commit()
        except IntegrityError:
            form.name.errors.append('Please provide a unique name!')
            return render_template('admin/activity_form.html', form=form, mode='edit', id=activity.id)
        else:
            return redirect(url_for('admin.list_activities'))
    return render_template('admin/activity_form.html', form=form, mode='edit', id=activity.id)


@bp.route('/activities/<int:activity_id>/impersonate', methods=['GET', 'POST'])
@admin_required
def impersonate_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if activity.is_archived:
        abort(403)
    login_user(activity, force=True)
    return redirect(url_for('pos.view_home'))


@bp.route('/activities/<int:activity_id>/activate', methods=['GET', 'POST'])
@admin_required
def activate_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if activity.is_archived:
        abort(403)
    activity.active = request.args.get('activate') != 'False'
    db.session.commit()
    return redirect(url_for('admin.list_activities'))


@bp.route('/activities/<int:activity_id>/export.json', methods=['GET'])
@admin_required
def export_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    if activity.is_archived:
        abort(403)
    return jsonify(activity.to_dict())


@bp.route('/activities/<int:activity_id>/archive', methods=['GET', 'POST'])
@admin_required
def archive_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    form = ActivityConfirmForm()

    is_valid = form.validate_on_submit()
    if form.is_submitted() and form.name.data != activity.name:
        is_valid = False
        form.name.errors.append('Incorrect activity name entered. Please double check.')

    if not is_valid:
        return render_template('admin/activity_archive_confirm.html', form=form, activity=activity)

    if not activity.is_archived:
        pos_purchases_query = db.session.query(
                db.func.sum(Product.price).label('amount'), 
                db.func.count(Product.price).label('units')
            )\
            .join(Purchase, Purchase.product_id == Product.id)\
            .filter(Purchase.activity_id == activity.id)\
            .filter(Purchase.undone == False)
        auction_total = db.session.query(
                db.func.sum(AuctionPurchase.price).label('amount'), 
                db.func.count(AuctionPurchase.price).label('units')
            )\
            .filter(AuctionPurchase.activity_id == activity.id)\
            .filter(AuctionPurchase.undone == False)\
            .first()

        pos_total = pos_purchases_query.first()
        pos_products = pos_purchases_query.add_column(Product.name)\
            .group_by(Product.name).order_by(db.desc('amount')).all()

        participants_with_purchase = db.session.query(
            db.func.count(db.distinct(Purchase.participant_id))
        ).filter_by(activity_id=activity.id).scalar()

        stats = {
            'participants': {
                'total': Participant.query.filter_by(activity_id=activity.id).count(),
                'with_purchase': participants_with_purchase,
            },
            'auction_purchases_total': {
                'amount': float(auction_total.amount) if auction_total.amount else 0,
                'units': auction_total.units,
            },
            'pos_purchases_total': {
                'amount': float(pos_total.amount) if pos_total.amount else 0,
                'units': pos_total.units,
            },
            'pos_purchases_products': [ {
                'name': product.name,
                'amount': float(product.amount) if product.amount else 0,
                'units': product.units,
            } for product in pos_products],
        }

        activity.archived_stats = json.dumps(stats)

    activity.active = False
    activity.is_archived = True

    # Commit for good measure
    db.session.commit()

    # Delete purchases
    AuctionPurchase.query.filter_by(activity_id=activity.id).delete()
    Purchase.query.filter_by(activity_id=activity.id).delete()

    # Commit so we can delete participants
    db.session.commit()

    # Delete participants
    Participant.query.filter_by(activity_id=activity.id).delete()

    db.session.commit()
    return redirect(url_for('admin.list_activities'))


@bp.route('/activities/<int:activity_id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_activity(activity_id):
    activity = Activity.query.get_or_404(activity_id)
    form = ActivityConfirmForm()

    is_valid = form.validate_on_submit()
    if form.is_submitted() and form.name.data != activity.name:
        is_valid = False
        form.name.errors.append('Incorrect activity name entered. Please double check.')

    if not is_valid:
        return render_template('admin/activity_delete_confirm.html', form=form, activity=activity)

    # Delete purchases
    AuctionPurchase.query.filter_by(activity_id=activity.id).delete()
    Purchase.query.filter_by(activity_id=activity.id).delete()

    # Commit so we can delete participants and products
    db.session.commit()

    # Delete participants
    Participant.query.filter_by(activity_id=activity.id).delete()

    # Product
    Product.query.filter_by(activity_id=activity.id).delete()

    # Commit so we can delete the activity
    db.session.commit()

    db.session.delete(activity)
    db.session.commit()
    return redirect(url_for('admin.list_activities'))
