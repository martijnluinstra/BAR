import csv
import io
import json
import re
from datetime import datetime

from flask import request, render_template, redirect, url_for, abort, make_response, flash, Response, get_flashed_messages, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from email_validator import validate_email, EmailNotValidError

from bar import db, login_manager
from bar.utils import is_safe_url, get_secretary_api, validate_bic, validate_iban
from bar.auction.models import AuctionPurchase

from . import bp
from .models import Activity, Participant, Purchase, Product
from .forms import ParticipantForm, ProductForm, RegistrationForm, SettingsForm, ImportForm, ExportForm


class CSVRowError(Exception):
    pass


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == 'POST':
        activity = Activity.query.filter_by(passcode = request.form['passcode']).first()
        if not activity or not activity.is_active():
            error = 'Invalid code!'
        else:
            login_user(activity)

            next = request.args.get('next')
            if not is_safe_url(next):
                return abort(400)
            return redirect(next or url_for('pos.view_home'))
    flashes = get_flashed_messages()
    return render_template('login.html', error=error)


@bp.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('pos.login'))


@bp.route('/', methods=['GET'])
@login_required
def view_home():
    """ View all participants attending the activity, ordered by name """
    spend_subq = db.session.query(Purchase.participant_id.label("participant_id"), db.func.sum(Product.price).label("spend"))\
                           .join(Product, Purchase.product_id == Product.id)\
                           .filter(Purchase.undone == False)\
                           .filter(Purchase.activity_id == current_user.id)\
                           .group_by(Purchase.participant_id)\
                           .subquery()
    parti_subq = current_user.participants.subquery()
    participants = db.session.query(parti_subq, spend_subq.c.spend)\
                           .outerjoin(spend_subq, spend_subq.c.participant_id==parti_subq.c.id)\
                           .order_by(parti_subq.c.name)\
                           .all()
    products = Product.query.filter_by(activity_id=current_user.id).order_by(Product.priority.desc()).all()
    return render_template('pos/main.html', participants=participants, products=products)

 
@bp.route('/faq', methods=['GET'])
def faq():
    return render_template('faq.html')


@bp.route('/participants', methods=['GET'])
@login_required
def list_participants():
    """ List all participants in the system by name """
    participants = current_user.participants.order_by(Participant.name).all()
    return render_template('pos/participant_list.html', participants=participants)


@bp.route('/participants/import', methods=['GET', 'POST'])
@login_required
def import_participants():
    form = ImportForm()
    if form.validate_on_submit():
        try:
            return import_process_csv(form)
        except (CSVRowError, csv.Error) as e:
            form.import_file.errors.append(str(e))
    elif request.method == 'POST':
        return import_process_data(request.get_json())
    return render_template('pos/import_upload_form.html', form=form)


def import_process_csv(form):
    data = []
    line_length = 0
    # csv.reader needs text file, not binary
    participant_data = csv.reader(io.TextIOWrapper(form.import_file.data), delimiter=form.delimiter.data)
    for line, row in enumerate(participant_data):
        if line==0:
            line_length = len(row)
            for column, value in enumerate(row):
                data.append({
                    'header': value if form.header.data else ('Column_%d' % (column+1)),
                    'rows': []
                    })
            if form.header.data:
                continue
        if line_length != len(row):
            raise CSVRowError('Not all rows have equal length')
        for column, value in enumerate(row):
            data[column]["rows"].append(value)
    return render_template('pos/import_select_form.html', json_data=data)


def import_report_error(errors, key, err):
    if key in errors:
        errors[key].update(err)
    else:
        errors[key] = err


def import_validate_row(key, row, errors):
    # Fix birthday
    birthday = None
    if row['birthday']:
        try:
            birthday = datetime.strptime(row['birthday'], '%Y-%m-%d')
        except ValueError:
            import_report_error(errors,key,{'birthday': ['type']})
    row['birthday'] = birthday
    # Clean iban and bic
    row['iban'] = row['iban'].upper().replace(" ", "").encode('ascii', 'ignore').decode()
    row['bic'] = row['bic'].upper().replace(" ", "")

    try:
        validate_email(
            row['email'],
            check_deliverability=False
        )
    except EmailNotValidError as e:
        import_report_error(errors,key,{'email': ['type', str(e)]})

    try:
        iban = validate_iban(row['iban'])
    except Exception as e:
        iban = None
        import_report_error(errors, key, {'iban': ['type', str(e)]})

    try:
        if row['bic']:
            validate_bic(row['bic'])
        elif iban:
            row['bic'] = iban.bic
    except Exception as e:
        import_report_error(errors, key, {'bic': ['type', str(e)]})

    for prop in ['name', 'address', 'city', 'email', 'iban']:
        if not row[prop].strip():
            import_report_error(errors,key,{prop: ['nonblank']})
    return (row, errors)


def import_process_data(data):
    errors = {}
    for key, row in data.items():
        row, errors = import_validate_row(key, row, errors)
        participant = Participant(
            name=row['name'],
            uuid=row['uuid'],
            address=row['address'],
            city=row['city'],
            email=row['email'],
            iban=row['iban'],
            bic=row['bic'],
            birthday=row['birthday'],
            activity=current_user
        )
        db.session.add(participant)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            import_report_error(errors,key,{'name': ['nonunique']})
    if not errors:
        db.session.commit()
        return "", 200
    else:
        db.session.rollback()
        return jsonify(errors)


@bp.route('/participants/add', methods=['GET', 'POST'])
@login_required
def add_participant():
    """ Try to create a new participant. """
    form = ParticipantForm()
    if form.validate_on_submit():
        participant = Participant(
            name=form.name.data, 
            address=form.address.data,
            city=form.city.data,
            email=form.email.data,
            iban=form.iban.data,
            bic=form.bic.data,
            birthday=form.birthday.data,
            activity=current_user
        )
        db.session.add(participant)
        try:
            db.session.commit()
        except IntegrityError:
            form.name.errors.append('Please provide a unique name!')
            return render_template('pos/participant_form.html', form=form, mode='add')
        else:
            return redirect(url_for('pos.view_home'))
    return render_template('pos/participant_form.html', form=form, mode='add')


@bp.route('/participants/<int:participant_id>', methods=['GET', 'POST'])
@login_required
def edit_participant(participant_id):
    participant = Participant.query.get_or_404(participant_id)
    form = ParticipantForm(obj=participant)
    if form.validate_on_submit():
        form.populate_obj(participant)
        try:
            db.session.commit()
        except IntegrityError:
            form.name.errors.append('Please provide a unique name!')
            return render_template('pos/participant_form.html', form=form, mode='edit', id=participant.id)
        else:
            return redirect(url_for('pos.list_participants'))
    return render_template('pos/participant_form.html', form=form, mode='edit', id=participant.id)


@bp.route('/participants/<int:participant_id>/terms', methods=['GET', 'POST'])
@login_required
def accept_terms_participant(participant_id):
    """ Let a participant accept terms """
    next_url = request.args.get('next')
    if not is_safe_url(next_url):
        return abort(400)

    participant = Participant.query.get_or_404(participant_id)
    products = Product.query.filter_by(activity_id=current_user.id).all()

    if request.method == 'POST':
        participant.has_agreed_to_terms = True
        db.session.commit()
        return redirect(next_url or url_for('pos.view_home'))
    
    return render_template(
        'pos/terms.html',
        terms=current_user.terms,
        participant=participant,
        products=products,
        next_url=next_url or url_for('pos.view_home')
    )


@bp.route('/participants/<int:participant_id>/history', methods=['GET'])
@login_required
def participant_history(participant_id):
    view = request.args.get('view', 'pos')
    
    if view == 'auction':
        purchase_query = AuctionPurchase.query.filter_by(participant_id=participant_id)\
                .filter_by(activity_id=current_user.id)\
                .order_by(AuctionPurchase.timestamp.desc())
    elif view == 'pos':
        purchase_query = db.session.query(Purchase, Product.name, Product.price)\
                .join(Product, Purchase.product_id == Product.id)\
                .filter(Purchase.participant_id == participant_id)\
                .filter(Purchase.activity_id == current_user.id)\
                .order_by(Purchase.timestamp.desc())
    else:
        return 'Invalid view', 400

    try:
        limit = request.args.get('limit', type=int)
    except KeyError:
        purchases = purchase_query.all();
    else:
        purchases = purchase_query.limit(limit).all();

    participant = Participant.query.get_or_404(participant_id)
    return render_template('pos/participant_history.html', purchases=purchases, participant=participant, view=view)


@bp.route('/participants/registration', methods=['GET', 'POST'])
@login_required
def participant_registration():
    """ Register a participant """
    form = RegistrationForm()
    if form.validate_on_submit():
        participant = Participant.query.filter_by(name=form.name.data, activity=current_user).first()
        if participant:
            participant.birthday = form.birthday.data
            participant.barcode = form.barcode.data
            db.session.commit()

            next_url = url_for('pos.participant_registration')
            if current_user.require_terms and not participant.has_agreed_to_terms:
                return redirect(url_for(
                    'pos.accept_terms_participant', 
                    participant_id=participant.id,
                    next=next_url
                ))
            return redirect(next_url)
        else:
            form.name.errors.append('Participant\'s name can not be found')
    return render_template('pos/participant_registration.html', form=form)


@bp.route('/participants/names.json', methods=['GET'])
@login_required
def list_participant_names():
    """ List all participants """
    participants = current_user.participants
    def generate(data):
        for participant in data:
            yield {
                'id': participant.id,
                'uuid': participant.uuid,
                'name': participant.name,
                'birthday': '' if not participant.birthday else participant.birthday.strftime('%d-%m-%Y'),
                'barcode': '' if not participant.barcode else participant.barcode,
                'is_legal_age': participant.age >= current_user.age_limit if participant.age else None
            }
    return jsonify(list(generate(participants)))


@bp.route('/purchases', methods=['POST'])
@login_required
def batch_consume():
    data = request.get_json()
    for row in data:
        purchase = Purchase(participant_id=row['participant_id'], activity_id=current_user.id, product_id=row['product_id'])
        db.session.add(purchase)
    db.session.commit()
    return 'Purchases created', 201


@bp.route('/purchases/undo', methods=['POST'])
@login_required
def batch_undo():
    data = request.get_json()
    for row in data:
        purchase = Purchase.query.get_or_404(row['purchase_id'])
        if purchase.activity_id != current_user.id:
            return 'Purchase not in current activity', 401
        purchase.undone = True
    db.session.commit()
    return 'Purchases undone', 201


@bp.route('/purchases/<int:purchase_id>/undo', methods=['GET'])
@login_required
def undo(purchase_id):
    next_url = request.args.get('next')
    if not is_safe_url(next_url):
        return abort(400)

    purchase = Purchase.query.get_or_404(purchase_id)
    if purchase.activity_id != current_user.id:
        return 'Purchase not in current activity', 401    
    purchase.undone = request.args.get('undo') != 'False'
    db.session.commit()
    return redirect(next_url or url_for('pos.participant_history', participant_id = purchase.participant_id))


@bp.route('/products', methods=['GET', 'POST'])
@login_required
def list_products():
    """ 
    View all products.
    """
    products = Product.query.order_by(Product.priority.desc()).filter_by(activity_id=current_user.id).all()
    return render_template('pos/product_list.html', products=products)


@bp.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    """ 
    Create a new product.
    """
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data, 
            activity_id=current_user.id,
            price=form.price.data, 
            priority=form.priority.data, 
            age_limit=form.age_limit.data
        )
        db.session.add(product)
        db.session.commit()
        return redirect(url_for('pos.list_products'))
    return render_template('pos/product_form.html', form=form, mode='add')


@bp.route('/products/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """ Edit a product """
    product = Product.query.get_or_404(product_id)
    if product.activity_id != current_user.id:
        return 'Product not in current activity', 401 
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        db.session.commit()
        return redirect(url_for('pos.list_products'))
    return render_template('pos/product_form.html', form=form, mode='edit', id=product.id)


@bp.route('/products/<int:product_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_product(product_id):
    """ Edit a product """
    product = Product.query.get_or_404(product_id)
    if product.activity_id != current_user.id:
        return 'Product not in current activity', 401 
    purchase = Purchase.query.filter_by(product_id=product.id).first()
    if purchase:
        flash('Cannot delete product, as it has been purchased already. Carry on or contact the AC/DCee!')
    else:
        db.session.delete(product)
        db.session.commit()
    return redirect(url_for('pos.list_products'))


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def activity_settings():
    """ Edit settings """
    form = SettingsForm(obj=current_user)
    if form.validate_on_submit():
        form.populate_obj(current_user)
        db.session.commit()
        flash('Changes are saved!')
    return render_template('pos/activity_settings.html', form=form)


@bp.route('/settings/export', methods=['GET'])
@login_required
def activity_export_form():
    """ Edit settings """
    form = ExportForm(meta={'csrf': False})
    return render_template('pos/export_form.html', form=form)


@bp.route('/activity/export.csv', methods=['GET'])
@login_required
def activity_export():
    """ Export all purchases of an activity """
    form = ExportForm(formdata=request.args, meta={'csrf': False})
    if not form.validate():
        return 'Unexpected error in form', 400

    if not (form.pos.data or form.auction.data):
        return '', 200

    pos_subq = db.session.query(Purchase.participant_id.label('participant_id'), db.func.sum(Product.price).label('spend'))\
                         .join(Product, Purchase.product_id==Product.id)\
                         .filter(Purchase.undone == False)\
                         .filter(Purchase.activity_id==current_user.id)\
                         .group_by(Purchase.participant_id)\
                         .subquery()

    auction_subq = db.session.query(AuctionPurchase.participant_id.label('participant_id'), db.func.sum(AuctionPurchase.price).label('spend'))\
                             .filter(AuctionPurchase.undone == False)\
                             .filter(AuctionPurchase.activity_id==current_user.get_id())\
                             .group_by(AuctionPurchase.participant_id)\
                             .subquery()

    participants = current_user.participants\
                             .add_columns(pos_subq.c.spend.label('spend_pos'), auction_subq.c.spend.label('spend_auction'))\
                             .outerjoin(pos_subq, pos_subq.c.participant_id == Participant.id)\
                             .outerjoin(auction_subq, auction_subq.c.participant_id == Participant.id)\
                             .order_by(Participant.name)\
                             .all()

    spend_data = []

    settings={
        'pos': form.pos.data,
        'auction': form.auction.data,
        'description_pos_prefix': form.description_pos_prefix.data,
        'description_auction_prefix': form.description_auction_prefix.data,
        'description': form.description.data
    }

    def generate(data, settings):
        for participant, spend_pos, spend_auction in data:        
            spend_pos = 0 if spend_pos is None else spend_pos
            spend_auction = 0 if spend_auction is None else spend_auction
            
            if settings['pos'] and settings['auction']:
                amount = spend_auction + spend_pos
            elif settings['pos']:
                amount = spend_pos
            else:
                amount = spend_auction

            if amount == 0:
                continue

            if amount > 0 and settings['description_pos_prefix'] and settings['description_auction_prefix']:
                if spend_pos > 0 and spend_auction > 0:
                    description = settings['description_pos_prefix'] + ' + ' + settings['description_auction_prefix'] + (' ' + settings['description'] if settings['description'] else '')
                elif spend_pos > 0:
                    description = settings['description_pos_prefix'] +  (' ' + settings['description'] if settings['description'] else '')
                else: 
                    description = settings['description_auction_prefix'] +  (' ' + settings['description'] if settings['description'] else '')
            else:
                description = settings['description']

            iban = re.sub(r'\s+', '', participant.iban)
            bic = re.sub(r'\s+', '', participant.bic) if participant.bic else ''

            p_data = [participant.name, participant.address, participant.city, participant.email, iban, bic, float(amount)/100, description]
            yield ','.join(['"' + str(field) + '"' for field in p_data]) + '\n'

    return Response(''.join(generate(participants, settings)), mimetype='text/csv')


@bp.route('/auto_complete/members', methods=['GET'])
@login_required
def auto_complete_members():
    if current_app.config.get('STAND_ALONE', False) or not current_user.has_secretary_access:
        return jsonify([])
    name = request.args.get('name')
    if not name:
        return jsonify([])
    members = get_secretary_api().find_members_by_name(name)
    return jsonify([m.to_dict() for m in members.values()])


@bp.route('/stats', methods=['GET'])
@login_required
def activity_stats():
    pos_purchases_query = db.session.query(
            db.func.sum(Product.price).label('amount'), 
            db.func.count(Product.price).label('units')
        )\
        .join(Purchase, Purchase.product_id == Product.id)\
        .filter(Purchase.activity_id == current_user.get_id())\
        .filter(Purchase.undone == False)
    auction_purchases_query = db.session.query(
            db.func.sum(AuctionPurchase.price).label('amount'), 
            db.func.count(AuctionPurchase.price).label('units')
        )\
        .filter(AuctionPurchase.activity_id == current_user.get_id())\
        .filter(AuctionPurchase.undone == False)

    stats = {
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
    return render_template('pos/activity_stats.html', **stats)
