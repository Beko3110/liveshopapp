from flask import Blueprint, render_template, jsonify, session, redirect, url_for
from app import db, socketio
from models import StreamSession, Order, Product, User, ViewHistory
from sqlalchemy import func, desc, text
from datetime import datetime, timedelta
from flask_socketio import join_room, leave_room
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import json

analytics_bp = Blueprint('analytics', __name__)

class AnalyticsManager:
    def __init__(self):
        self.streams = {}
    
    def get_stream_analytics(self, stream_id):
        if stream_id not in self.streams:
            self.streams[stream_id] = {
                'viewers': set(),
                'active_viewers': set(),
                'view_durations': {},
                'peak_viewers': 0,
                'engagement_data': [],
                'sales_history': [],
                'viewer_actions': [],
                'heatmap_data': {},
                'device_stats': {'desktop': 0, 'mobile': 0, 'tablet': 0},
                'retention_segments': {'0-5m': 0, '5-15m': 0, '15-30m': 0, '30m+': 0}
            }
        return self.streams[stream_id]

    def track_viewer_action(self, stream_id, user_id, action_type, timestamp=None):
        analytics = self.get_stream_analytics(stream_id)
        timestamp = timestamp or datetime.utcnow()
        analytics['viewer_actions'].append({
            'user_id': user_id,
            'action': action_type,
            'timestamp': timestamp
        })
        
        # Update heatmap data
        minute_key = timestamp.strftime('%H:%M')
        if minute_key not in analytics['heatmap_data']:
            analytics['heatmap_data'][minute_key] = {'actions': 0, 'viewers': set()}
        analytics['heatmap_data'][minute_key]['actions'] += 1
        analytics['heatmap_data'][minute_key]['viewers'].add(user_id)

    def calculate_engagement_metrics(self, stream_id):
        analytics = self.get_stream_analytics(stream_id)
        total_viewers = len(analytics['viewers'])
        if total_viewers == 0:
            return {
                'engagement_rate': 0,
                'avg_watch_time': 0,
                'retention_rate': 0
            }

        active_viewers = len(analytics['active_viewers'])
        current_time = datetime.utcnow()
        
        # Calculate average watch time
        watch_times = [(current_time - start).total_seconds()
                      for start in analytics['view_durations'].values()]
        avg_watch_time = sum(watch_times) / len(watch_times) if watch_times else 0
        
        # Calculate retention rate (viewers who stayed more than 5 minutes)
        retained_viewers = sum(1 for t in watch_times if t >= 300)
        retention_rate = (retained_viewers / total_viewers) * 100
        
        # Update retention segments
        for duration in watch_times:
            if duration <= 300:  # 5 minutes
                analytics['retention_segments']['0-5m'] += 1
            elif duration <= 900:  # 15 minutes
                analytics['retention_segments']['5-15m'] += 1
            elif duration <= 1800:  # 30 minutes
                analytics['retention_segments']['15-30m'] += 1
            else:
                analytics['retention_segments']['30m+'] += 1
        
        return {
            'engagement_rate': (active_viewers / total_viewers) * 100,
            'avg_watch_time': avg_watch_time,
            'retention_rate': retention_rate,
            'retention_segments': analytics['retention_segments']
        }

    def predict_best_streaming_times(self, seller_id):
        # Get historical stream data
        streams = StreamSession.query.filter_by(seller_id=seller_id).all()
        if not streams:
            return []
        
        stream_data = []
        for stream in streams:
            viewer_count = ViewHistory.query.filter_by(stream_id=stream.id).count()
            hour = stream.created_at.hour
            day = stream.created_at.weekday()
            stream_data.append([hour, day, viewer_count])
        
        if not stream_data:
            return []
            
        df = pd.DataFrame(stream_data, columns=['hour', 'day', 'viewers'])
        
        # Simple linear regression for prediction
        X = df[['hour', 'day']]
        y = df['viewers']
        model = LinearRegression()
        model.fit(X, y)
        
        # Predict viewers for all hour/day combinations
        predictions = []
        for day in range(7):
            for hour in range(24):
                viewers = model.predict([[hour, day]])[0]
                predictions.append({
                    'day': day,
                    'hour': hour,
                    'predicted_viewers': int(viewers)
                })
        
        # Sort by predicted viewers
        predictions.sort(key=lambda x: x['predicted_viewers'], reverse=True)
        return predictions[:5]  # Return top 5 times

analytics_manager = AnalyticsManager()

@socketio.on('join_room')
def on_join(data):
    room = str(data.get('room'))
    if room and session.get('user_id'):
        join_room(room)
        analytics = analytics_manager.get_stream_analytics(room)
        user_id = session['user_id']
        
        analytics['viewers'].add(user_id)
        analytics['active_viewers'].add(user_id)
        analytics['view_durations'][user_id] = datetime.utcnow()
        
        # Track viewer device type (from user agent)
        user_agent = request.headers.get('User-Agent', '').lower()
        if 'mobile' in user_agent:
            analytics['device_stats']['mobile'] += 1
        elif 'tablet' in user_agent:
            analytics['device_stats']['tablet'] += 1
        else:
            analytics['device_stats']['desktop'] += 1
        
        # Track action
        analytics_manager.track_viewer_action(room, user_id, 'join')
        
        # Calculate and emit metrics
        metrics = analytics_manager.calculate_engagement_metrics(room)
        socketio.emit('analytics_update', metrics, room=room)

@socketio.on('viewer_action')
def on_viewer_action(data):
    room = str(data.get('room'))
    action_type = data.get('action_type')
    if room and session.get('user_id') and action_type:
        analytics_manager.track_viewer_action(
            room, session['user_id'], action_type)
        metrics = analytics_manager.calculate_engagement_metrics(room)
        socketio.emit('analytics_update', metrics, room=room)

@analytics_bp.route('/analytics/dashboard')
def dashboard():
    if not session.get('is_seller'):
        return redirect(url_for('products.list'))
    
    seller_id = session['user_id']
    
    # Get sales performance data
    sales_data = db.session.query(
        func.date_trunc('hour', Order.created_at).label('hour'),
        func.sum(Order.total_amount).label('revenue'),
        func.count(Order.id).label('orders')
    ).join(Product).filter(
        Product.seller_id == seller_id,
        Order.created_at >= datetime.utcnow() - timedelta(days=7)
    ).group_by('hour').order_by('hour').all()
    
    # Get best streaming times prediction
    best_times = analytics_manager.predict_best_streaming_times(seller_id)
    
    # Get stream performance metrics
    stream_metrics = db.session.query(
        StreamSession.id,
        StreamSession.title,
        StreamSession.created_at,
        func.count(ViewHistory.id).label('total_viewers'),
        func.avg(ViewHistory.duration).label('avg_watch_time'),
        func.count(Order.id).label('orders'),
        func.sum(Order.total_amount).label('revenue')
    ).outerjoin(ViewHistory).outerjoin(Order).filter(
        StreamSession.seller_id == seller_id
    ).group_by(StreamSession.id).order_by(
        StreamSession.created_at.desc()
    ).all()
    
    return render_template('analytics/dashboard.html',
                         sales_data=sales_data,
                         stream_metrics=stream_metrics,
                         best_times=best_times)

@analytics_bp.route('/analytics/stream/<int:stream_id>')
def stream_analytics(stream_id):
    if not session.get('is_seller'):
        return redirect(url_for('products.list'))
    
    stream = StreamSession.query.get_or_404(stream_id)
    if stream.seller_id != session['user_id']:
        return redirect(url_for('products.list'))
    
    analytics = analytics_manager.get_stream_analytics(str(stream_id))
    metrics = analytics_manager.calculate_engagement_metrics(str(stream_id))
    
    # Get real-time sales data
    sales_data = db.session.query(
        Product.name,
        func.count(Order.id).label('orders'),
        func.sum(Order.total_amount).label('revenue')
    ).join(Order).filter(
        Order.created_at >= stream.created_at
    ).group_by(Product.id).all()
    
    return render_template('analytics/stream.html',
                         stream=stream,
                         analytics=analytics,
                         metrics=metrics,
                         sales_data=sales_data)

@analytics_bp.route('/analytics/heatmap/<int:stream_id>')
def get_engagement_heatmap(stream_id):
    if not session.get('is_seller'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    stream = StreamSession.query.get_or_404(stream_id)
    if stream.seller_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    analytics = analytics_manager.get_stream_analytics(str(stream_id))
    return jsonify(analytics['heatmap_data'])
