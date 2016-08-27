from __future__ import division

from flask import request, render_template, redirect, url_for
from flask_login import login_required, current_user

from bar import db
from bar.pos.models import Participant

from . import auction
from .forms import AuctionForm
from .models import AuctionPurchase

@auction.route('/', methods=['GET', 'POST'])
@login_required
def list_auction():
    form = AuctionForm()
    if form.validate_on_submit():
        participant = Participant.query.filter_by(name=form.participant.data).first()
        purchase = AuctionPurchase(participant_id=participant.id, activity_id=current_user.id, description=form.description.data, price=form.price.data)
        db.session.add(purchase)
        db.session.commit()
        return redirect(url_for('auction.list_auction'))
    purchases = AuctionPurchase.query.filter_by(activity_id=current_user.get_id()).order_by(AuctionPurchase.timestamp.desc()).all()
    return render_template('auction/auction.html', form=form, purchases=purchases)


@auction.route('/purchases/<int:purchase_id>', methods=['GET', 'POST'])
@login_required
def edit_auction_purchase(purchase_id):
    """ Edit a purchase """
    purchase = AuctionPurchase.query.get_or_404(purchase_id)
    if purchase.activity_id != current_user.id:
        return 'Purchase not in current activity', 401
    form = AuctionForm(request.form, purchase)
    if form.validate_on_submit():
        participant = Participant.query.filter_by(name=form.participant.data).first()
        if participant:
            form.participant.data = participant
            form.populate_obj(purchase)
            db.session.commit()
            return redirect(url_for('auction.list_auction'))
        else:
            form.participant.errors.append('Participant not found!')
    else:
        form.participant.data = purchase.participant.name
    return render_template('auction/auction_form.html', form=form, mode='edit', id=purchase.id)


@auction.route('/purchases/<int:purchase_id>/undo', methods=['GET'])
@login_required
def undo_auction_purchase(purchase_id):
    purchase = AuctionPurchase.query.get_or_404(purchase_id)
    if purchase.activity_id != current_user.id:
        return 'Purchase not in current activity', 401    
    purchase.undone = request.args.get('undo') != 'False'
    db.session.commit()
    return redirect(url_for('auction.list_auction'))
