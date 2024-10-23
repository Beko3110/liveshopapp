from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app import db
from models import User, ActivityFeed, StreamSession, Product

social_bp = Blueprint('social', __name__)

@social_bp.route('/follow/<int:user_id>', methods=['POST'])
def follow(user_id):
    if not session.get('user_id'):
        flash('Please login to follow sellers')
        return redirect(url_for('auth.login'))
    
    user_to_follow = User.query.get_or_404(user_id)
    if not user_to_follow.is_seller:
        flash('You can only follow sellers')
        return redirect(url_for('products.list'))
    
    current_user = User.query.get(session['user_id'])
    current_user.follow(user_to_follow)
    
    # Record in activity feed
    activity = ActivityFeed(
        user_id=session['user_id'],
        activity_type='follow',
        target_id=user_id
    )
    db.session.add(activity)
    db.session.commit()
    
    flash(f'You are now following {user_to_follow.username}')
    return redirect(url_for('social.seller_profile', user_id=user_id))

@social_bp.route('/unfollow/<int:user_id>', methods=['POST'])
def unfollow(user_id):
    if not session.get('user_id'):
        flash('Please login to unfollow sellers')
        return redirect(url_for('auth.login'))
    
    user_to_unfollow = User.query.get_or_404(user_id)
    current_user = User.query.get(session['user_id'])
    current_user.unfollow(user_to_unfollow)
    db.session.commit()
    
    flash(f'You have unfollowed {user_to_unfollow.username}')
    return redirect(url_for('social.seller_profile', user_id=user_id))

@social_bp.route('/seller/<int:user_id>')
def seller_profile(user_id):
    seller = User.query.get_or_404(user_id)
    if not seller.is_seller:
        flash('Invalid seller profile')
        return redirect(url_for('products.list'))
    
    products = Product.query.filter_by(seller_id=user_id).all()
    active_streams = StreamSession.query.filter_by(seller_id=user_id, status='active').all()
    
    is_following = False
    if session.get('user_id'):
        current_user = User.query.get(session['user_id'])
        is_following = current_user.is_following(seller)
    
    return render_template('social/seller_profile.html',
                         seller=seller,
                         products=products,
                         active_streams=active_streams,
                         is_following=is_following)

@social_bp.route('/feed')
def activity_feed():
    if not session.get('user_id'):
        flash('Please login to view your feed')
        return redirect(url_for('auth.login'))
    
    current_user = User.query.get(session['user_id'])
    followed_sellers = current_user.followed.all()
    seller_ids = [seller.id for seller in followed_sellers]
    
    # Get activities from followed sellers
    activities = ActivityFeed.query\
        .filter(ActivityFeed.user_id.in_(seller_ids))\
        .order_by(ActivityFeed.created_at.desc())\
        .limit(50)\
        .all()
    
    # Get active streams from followed sellers
    active_streams = StreamSession.query\
        .filter(StreamSession.seller_id.in_(seller_ids))\
        .filter_by(status='active')\
        .order_by(StreamSession.created_at.desc())\
        .all()
    
    # Get latest products from followed sellers
    latest_products = Product.query\
        .filter(Product.seller_id.in_(seller_ids))\
        .order_by(Product.created_at.desc())\
        .limit(12)\
        .all()
    
    return render_template('social/feed.html',
                         activities=activities,
                         active_streams=active_streams,
                         latest_products=latest_products)
