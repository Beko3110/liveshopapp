from flask import Blueprint, render_template, jsonify, session
from app import db, socketio
from models import StreamSession, Order, Product, User
from sqlalchemy import func
from datetime import datetime, timedelta
from flask_socketio import join_room, leave_room

analytics_bp = Blueprint('analytics', __name__)

# Store viewer data in memory (could be moved to Redis in production)
stream_analytics = {}

def init_stream_analytics(stream_id):
    if stream_id not in stream_analytics:
        stream_analytics[stream_id] = {
            'viewers': set(),
            'active_viewers': set(),
            'view_durations': {},
            'peak_viewers': 0,
            'start_time': datetime.utcnow(),
        }

@socketio.on('join_room')
def on_join(data):
    room = data.get('room')
    if room and session.get('user_id'):
        join_room(room)
        init_stream_analytics(room)
        stream_analytics[room]['viewers'].add(session['user_id'])
        stream_analytics[room]['active_viewers'].add(session['user_id'])
        stream_analytics[room]['view_durations'][session['user_id']] = datetime.utcnow()
        
        viewer_count = len(stream_analytics[room]['viewers'])
        stream_analytics[room]['peak_viewers'] = max(
            stream_analytics[room]['peak_viewers'], 
            viewer_count
        )
        
        socketio.emit('viewer_count_update', {
            'count': viewer_count
        }, room=room)

@socketio.on('disconnect')
def on_disconnect():
    for room in stream_analytics:
        if session.get('user_id') in stream_analytics[room]['viewers']:
            stream_analytics[room]['viewers'].remove(session['user_id'])
            if session['user_id'] in stream_analytics[room]['active_viewers']:
                stream_analytics[room]['active_viewers'].remove(session['user_id'])
            
            # Calculate view duration
            start_time = stream_analytics[room]['view_durations'].get(session['user_id'])
            if start_time:
                duration = (datetime.utcnow() - start_time).total_seconds()
                # Store duration in database or analytics system
            
            socketio.emit('viewer_count_update', {
                'count': len(stream_analytics[room]['viewers'])
            }, room=room)

@socketio.on('viewer_active')
def on_viewer_active(data):
    room = data.get('room')
    if room and session.get('user_id'):
        stream_analytics[room]['active_viewers'].add(session['user_id'])
        emit_engagement_metrics(room)

@socketio.on('viewer_inactive')
def on_viewer_inactive(data):
    room = data.get('room')
    if room and session.get('user_id'):
        if session['user_id'] in stream_analytics[room]['active_viewers']:
            stream_analytics[room]['active_viewers'].remove(session['user_id'])
        emit_engagement_metrics(room)

def emit_engagement_metrics(room):
    if room in stream_analytics:
        total_viewers = len(stream_analytics[room]['viewers'])
        active_viewers = len(stream_analytics[room]['active_viewers'])
        engagement_rate = (active_viewers / total_viewers * 100) if total_viewers > 0 else 0
        
        # Calculate average watch time
        current_time = datetime.utcnow()
        total_duration = sum(
            (current_time - start_time).total_seconds()
            for start_time in stream_analytics[room]['view_durations'].values()
        )
        avg_watch_time = total_duration / total_viewers if total_viewers > 0 else 0
        
        socketio.emit('engagement_update', {
            'activeViewers': active_viewers,
            'engagementRate': round(engagement_rate, 2),
            'avgWatchTime': round(avg_watch_time)
        }, room=room)

@analytics_bp.route('/analytics/dashboard')
def dashboard():
    if not session.get('is_seller'):
        return redirect(url_for('products.list'))
    
    seller_id = session['user_id']
    
    # Get sales data
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
        func.count(Order.id).label('orders'),
        func.sum(Order.total_amount).label('revenue')
    ).outerjoin(Order).filter(
        StreamSession.seller_id == seller_id
    ).group_by(StreamSession.id).order_by(StreamSession.created_at.desc()).all()
    
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
    
    analytics = stream_analytics.get(str(stream_id), {})
    
    return render_template('analytics/stream.html',
                         stream=stream,
                         analytics=analytics)
