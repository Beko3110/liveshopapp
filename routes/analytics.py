from flask import Blueprint, render_template, jsonify, session, redirect, url_for
from app import db, socketio
from models import StreamSession, Order, Product, User, ViewHistory
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from flask_socketio import join_room, leave_room
import json

analytics_bp = Blueprint('analytics', __name__)

# Store analytics data in memory (could be moved to Redis in production)
stream_analytics = {}

class StreamAnalytics:
    def __init__(self):
        self.viewers = set()
        self.active_viewers = set()
        self.view_durations = {}
        self.peak_viewers = 0
        self.start_time = datetime.utcnow()
        self.engagement_history = []
        self.sales_history = {}
        self.retention_data = {}
        self.device_stats = {'desktop': 0, 'mobile': 0, 'tablet': 0}
        self.location_stats = {}
        self.referral_stats = {}

def get_stream_analytics(stream_id):
    if stream_id not in stream_analytics:
        stream_analytics[stream_id] = StreamAnalytics()
    return stream_analytics[stream_id]

def calculate_stream_metrics(stream_id):
    analytics = get_stream_analytics(stream_id)
    current_time = datetime.utcnow()
    
    # Calculate average watch time
    total_duration = sum(
        (current_time - start_time).total_seconds()
        for start_time in analytics.view_durations.values()
    )
    avg_watch_time = total_duration / len(analytics.viewers) if analytics.viewers else 0
    
    # Calculate engagement rate
    engagement_rate = (len(analytics.active_viewers) / len(analytics.viewers) * 100) if analytics.viewers else 0
    
    # Track retention data
    timestamp = int(current_time.timestamp() * 1000)
    analytics.retention_data[timestamp] = len(analytics.viewers)
    
    # Maintain only last hour of data
    cutoff = timestamp - 3600000  # 1 hour in milliseconds
    analytics.retention_data = {
        ts: count for ts, count in analytics.retention_data.items()
        if ts > cutoff
    }
    
    # Track engagement history
    analytics.engagement_history.append({
        'timestamp': timestamp,
        'rate': engagement_rate
    })
    
    # Keep only last 30 minutes of engagement history
    cutoff_time = timestamp - 1800000  # 30 minutes in milliseconds
    analytics.engagement_history = [
        point for point in analytics.engagement_history
        if point['timestamp'] > cutoff_time
    ]
    
    return {
        'viewers': len(analytics.viewers),
        'active_viewers': len(analytics.active_viewers),
        'engagement_rate': engagement_rate,
        'avg_watch_time': avg_watch_time,
        'retention_data': analytics.retention_data,
        'engagement_history': analytics.engagement_history
    }

@socketio.on('join_room')
def on_join(data):
    room = str(data.get('room'))
    if room and session.get('user_id'):
        join_room(room)
        analytics = get_stream_analytics(room)
        analytics.viewers.add(session['user_id'])
        analytics.active_viewers.add(session['user_id'])
        analytics.view_durations[session['user_id']] = datetime.utcnow()
        
        # Update peak viewers
        analytics.peak_viewers = max(
            analytics.peak_viewers,
            len(analytics.viewers)
        )
        
        # Calculate and emit updated metrics
        metrics = calculate_stream_metrics(room)
        socketio.emit('analytics_update', metrics, room=room)

@socketio.on('disconnect')
def on_disconnect():
    user_id = session.get('user_id')
    if not user_id:
        return
        
    for room, analytics in stream_analytics.items():
        if user_id in analytics.viewers:
            analytics.viewers.remove(user_id)
            if user_id in analytics.active_viewers:
                analytics.active_viewers.remove(user_id)
            
            # Calculate view duration
            if user_id in analytics.view_durations:
                start_time = analytics.view_durations.pop(user_id)
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # Store view duration in database
                stream_id = int(room)
                view_history = ViewHistory(
                    user_id=user_id,
                    stream_id=stream_id,
                    duration=duration
                )
                db.session.add(view_history)
                db.session.commit()
            
            # Emit updated metrics
            metrics = calculate_stream_metrics(room)
            socketio.emit('analytics_update', metrics, room=room)

@socketio.on('viewer_active')
def on_viewer_active(data):
    room = str(data.get('room'))
    if room and session.get('user_id'):
        analytics = get_stream_analytics(room)
        analytics.active_viewers.add(session['user_id'])
        
        metrics = calculate_stream_metrics(room)
        socketio.emit('analytics_update', metrics, room=room)

@socketio.on('viewer_inactive')
def on_viewer_inactive(data):
    room = str(data.get('room'))
    if room and session.get('user_id'):
        analytics = get_stream_analytics(room)
        if session['user_id'] in analytics.active_viewers:
            analytics.active_viewers.remove(session['user_id'])
        
        metrics = calculate_stream_metrics(room)
        socketio.emit('analytics_update', metrics, room=room)

@socketio.on('order_placed')
def on_order_placed(data):
    room = str(data.get('room'))
    if room and session.get('user_id'):
        analytics = get_stream_analytics(room)
        product_id = data.get('product_id')
        
        if product_id not in analytics.sales_history:
            analytics.sales_history[product_id] = []
        
        analytics.sales_history[product_id].append({
            'timestamp': datetime.utcnow(),
            'amount': data.get('amount', 0)
        })
        
        # Calculate and emit updated sales metrics
        metrics = calculate_stream_metrics(room)
        metrics['sales_data'] = get_sales_metrics(room)
        socketio.emit('analytics_update', metrics, room=room)

def get_sales_metrics(room):
    analytics = get_stream_analytics(room)
    stream = StreamSession.query.get(int(room))
    if not stream:
        return {}
    
    sales_data = {}
    for product in stream.products:
        # Calculate sales trend (last 10 minutes in 1-minute intervals)
        now = datetime.utcnow()
        trend = []
        for i in range(10):
            start_time = now - timedelta(minutes=10-i)
            end_time = start_time + timedelta(minutes=1)
            
            period_sales = sum(
                sale['amount']
                for sale in analytics.sales_history.get(product.id, [])
                if start_time <= sale['timestamp'] <= end_time
            )
            trend.append(period_sales)
        
        total_orders = len([
            sale for sale in analytics.sales_history.get(product.id, [])
            if (now - sale['timestamp']).total_seconds() <= 3600  # Last hour
        ])
        
        total_revenue = sum(
            sale['amount']
            for sale in analytics.sales_history.get(product.id, [])
            if (now - sale['timestamp']).total_seconds() <= 3600
        )
        
        conversion_rate = (total_orders / len(analytics.viewers) * 100) if analytics.viewers else 0
        
        sales_data[product.id] = {
            'orders': total_orders,
            'revenue': total_revenue,
            'conversion_rate': conversion_rate,
            'trend': trend
        }
    
    return sales_data

@analytics_bp.route('/analytics/dashboard')
def dashboard():
    if not session.get('is_seller'):
        return redirect(url_for('products.list'))
    
    seller_id = session['user_id']
    
    # Get sales data for last 30 days
    sales_data = db.session.query(
        func.date_trunc('day', Order.created_at).label('date'),
        func.sum(Order.total_amount).label('revenue'),
        func.count(Order.id).label('orders')
    ).join(Product).filter(
        Product.seller_id == seller_id,
        Order.created_at >= datetime.utcnow() - timedelta(days=30)
    ).group_by('date').order_by('date').all()
    
    # Get stream performance data
    stream_data = db.session.query(
        StreamSession.id,
        StreamSession.title,
        StreamSession.created_at,
        StreamSession.status,
        func.count(Order.id).label('orders'),
        func.sum(Order.total_amount).label('revenue')
    ).outerjoin(Order).filter(
        StreamSession.seller_id == seller_id
    ).group_by(
        StreamSession.id
    ).order_by(
        StreamSession.created_at.desc()
    ).all()
    
    return render_template('analytics/dashboard.html',
                         sales_data=sales_data,
                         stream_data=stream_data)

@analytics_bp.route('/analytics/stream/<int:stream_id>')
def stream_analytics_view(stream_id):
    if not session.get('is_seller'):
        return redirect(url_for('products.list'))
    
    stream = StreamSession.query.get_or_404(stream_id)
    if stream.seller_id != session['user_id']:
        return redirect(url_for('products.list'))
    
    analytics = get_stream_analytics(str(stream_id))
    
    return render_template('analytics/stream.html',
                         stream=stream,
                         analytics=analytics)
