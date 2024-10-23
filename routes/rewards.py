from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from models import User, Badge, FlashSale, Product, GroupBuying, GroupBuyingParticipant, Wishlist
from datetime import datetime, timedelta

rewards_bp = Blueprint('rewards', __name__)

@rewards_bp.route('/daily-reward', methods=['POST'])
def claim_daily_reward():
    if not session.get('user_id'):
        return jsonify({'error': 'Login required'}), 401
        
    user = User.query.get(session['user_id'])
    points = user.claim_daily_reward()
    
    if points > 0:
        db.session.commit()
        return jsonify({
            'success': True,
            'points': points,
            'total_points': user.loyalty_points,
            'message': f'Claimed {points} points!'
        })
    
    return jsonify({
        'success': False,
        'message': 'Daily reward already claimed'
    })

@rewards_bp.route('/badges')
def view_badges():
    if not session.get('user_id'):
        flash('Please login to view badges')
        return redirect(url_for('auth.login'))
        
    user = User.query.get(session['user_id'])
    return render_template('rewards/badges.html', badges=user.badges)

@rewards_bp.route('/wishlist', methods=['GET', 'POST', 'DELETE'])
def manage_wishlist():
    if not session.get('user_id'):
        flash('Please login to manage wishlist')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        wishlist_item = Wishlist(user_id=session['user_id'], product_id=product_id)
        db.session.add(wishlist_item)
        db.session.commit()
        return jsonify({'success': True})
        
    elif request.method == 'DELETE':
        product_id = request.form.get('product_id')
        Wishlist.query.filter_by(user_id=session['user_id'], product_id=product_id).delete()
        db.session.commit()
        return jsonify({'success': True})
    
    # GET method
    wishlist_items = Wishlist.query.filter_by(user_id=session['user_id']).all()
    return render_template('rewards/wishlist.html', items=wishlist_items)

@rewards_bp.route('/group-buying/<int:product_id>', methods=['POST'])
def create_group_buying(product_id):
    if not session.get('user_id'):
        flash('Please login to create group buying')
        return redirect(url_for('auth.login'))
        
    product = Product.query.get_or_404(product_id)
    target_price = float(request.form.get('target_price'))
    min_buyers = int(request.form.get('min_buyers'))
    expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days expiry
    
    group_buy = GroupBuying(
        product_id=product_id,
        target_price=target_price,
        min_buyers=min_buyers,
        expires_at=expires_at
    )
    
    db.session.add(group_buy)
    db.session.commit()
    
    # Add creator as first participant
    participant = GroupBuyingParticipant(
        group_buying_id=group_buy.id,
        user_id=session['user_id']
    )
    db.session.add(participant)
    db.session.commit()
    
    flash('Group buying created successfully')
    return redirect(url_for('products.list'))

@rewards_bp.route('/group-buying/join/<int:group_id>', methods=['POST'])
def join_group_buying(group_id):
    if not session.get('user_id'):
        flash('Please login to join group buying')
        return redirect(url_for('auth.login'))
        
    group_buy = GroupBuying.query.get_or_404(group_id)
    
    if group_buy.status != 'active':
        flash('This group buying is no longer active')
        return redirect(url_for('products.list'))
        
    if datetime.utcnow() > group_buy.expires_at:
        group_buy.status = 'expired'
        db.session.commit()
        flash('This group buying has expired')
        return redirect(url_for('products.list'))
    
    # Check if user already joined
    existing = GroupBuyingParticipant.query.filter_by(
        group_buying_id=group_id,
        user_id=session['user_id']
    ).first()
    
    if existing:
        flash('You have already joined this group buying')
        return redirect(url_for('products.list'))
    
    participant = GroupBuyingParticipant(
        group_buying_id=group_id,
        user_id=session['user_id']
    )
    db.session.add(participant)
    group_buy.current_buyers += 1
    
    # Check if target reached
    if group_buy.current_buyers >= group_buy.min_buyers:
        group_buy.status = 'completed'
        # Here we would typically trigger the group purchase process
        
    db.session.commit()
    flash('Successfully joined group buying')
    return redirect(url_for('products.list'))

@rewards_bp.route('/flash-sale/create', methods=['POST'])
def create_flash_sale():
    if not session.get('is_seller'):
        return jsonify({'error': 'Seller access required'}), 403
        
    stream_id = request.form.get('stream_id')
    product_id = request.form.get('product_id')
    discount = int(request.form.get('discount'))
    duration = int(request.form.get('duration', 30))  # Default 30 minutes
    
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(minutes=duration)
    
    flash_sale = FlashSale(
        stream_id=stream_id,
        product_id=product_id,
        discount_percentage=discount,
        start_time=start_time,
        end_time=end_time
    )
    
    db.session.add(flash_sale)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'flash_sale_id': flash_sale.id,
        'end_time': end_time.isoformat()
    })
