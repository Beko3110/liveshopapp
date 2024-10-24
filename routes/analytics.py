from flask import Blueprint, render_template, jsonify, session, redirect, url_for, request
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
                'retention_segments': {'0-5m': 0, '5-15m': 0, '15-30m': 0, '30m+': 0},
                'revenue_data': {'hourly': [], 'total': 0},
                'conversion_rate': 0,
                'avg_session_duration': 0
            }
        return self.streams[stream_id]

    def update_viewer_metrics(self, stream_id, user_id, action_type, timestamp=None):
        analytics = self.get_stream_analytics(stream_id)
        timestamp = timestamp or datetime.utcnow()

        if action_type == 'join':
            analytics['viewers'].add(user_id)
            analytics['active_viewers'].add(user_id)
            analytics['view_durations'][user_id] = timestamp
            analytics['peak_viewers'] = max(analytics['peak_viewers'], len(analytics['viewers']))
        elif action_type == 'leave':
            if user_id in analytics['viewers']:
                analytics['viewers'].remove(user_id)
                analytics['active_viewers'].discard(user_id)
                if user_id in analytics['view_durations']:
                    duration = (timestamp - analytics['view_durations'].pop(user_id)).total_seconds()
                    self.update_retention_data(stream_id, duration)

        # Update engagement data
        analytics['engagement_data'].append({
            'timestamp': timestamp,
            'viewers': len(analytics['viewers']),
            'active_viewers': len(analytics['active_viewers'])
        })

        # Keep only last hour of engagement data
        cutoff = timestamp - timedelta(hours=1)
        analytics['engagement_data'] = [
            data for data in analytics['engagement_data']
            if data['timestamp'] > cutoff
        ]

        return self.calculate_metrics(stream_id)

    def update_retention_data(self, stream_id, duration):
        analytics = self.get_stream_analytics(stream_id)
        if duration <= 300:  # 5 minutes
            analytics['retention_segments']['0-5m'] += 1
        elif duration <= 900:  # 15 minutes
            analytics['retention_segments']['5-15m'] += 1
        elif duration <= 1800:  # 30 minutes
            analytics['retention_segments']['15-30m'] += 1
        else:
            analytics['retention_segments']['30m+'] += 1

    def update_sales_data(self, stream_id, order):
        analytics = self.get_stream_analytics(stream_id)
        timestamp = datetime.utcnow()
        
        # Update hourly revenue data
        hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
        hour_data = next((x for x in analytics['revenue_data']['hourly'] if x['hour'] == hour_key), None)
        
        if hour_data:
            hour_data['revenue'] += order.total_amount
            hour_data['orders'] += 1
        else:
            analytics['revenue_data']['hourly'].append({
                'hour': hour_key,
                'revenue': order.total_amount,
                'orders': 1
            })
        
        analytics['revenue_data']['total'] += order.total_amount
        
        # Update conversion rate
        total_viewers = len(analytics['viewers'])
        if total_viewers > 0:
            analytics['conversion_rate'] = (
                len(Order.query.filter_by(stream_id=stream_id).all()) / total_viewers * 100
            )

    def calculate_metrics(self, stream_id):
        analytics = self.get_stream_analytics(stream_id)
        total_viewers = len(analytics['viewers'])
        active_viewers = len(analytics['active_viewers'])
        
        # Calculate engagement rate
        engagement_rate = (active_viewers / total_viewers * 100) if total_viewers > 0 else 0
        
        # Calculate average session duration
        current_time = datetime.utcnow()
        durations = [
            (current_time - start_time).total_seconds()
            for start_time in analytics['view_durations'].values()
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0
        analytics['avg_session_duration'] = avg_duration
        
        # Calculate retention rate for each segment
        total_sessions = sum(analytics['retention_segments'].values())
        retention_rates = {
            segment: (count / total_sessions * 100) if total_sessions > 0 else 0
            for segment, count in analytics['retention_segments'].items()
        }
        
        return {
            'viewers': total_viewers,
            'active_viewers': active_viewers,
            'engagement_rate': engagement_rate,
            'avg_session_duration': avg_duration,
            'peak_viewers': analytics['peak_viewers'],
            'retention_rates': retention_rates,
            'device_stats': analytics['device_stats'],
            'revenue_data': analytics['revenue_data'],
            'conversion_rate': analytics['conversion_rate']
        }

analytics_manager = AnalyticsManager()

@socketio.on('join_stream')
def on_join_stream(data):
    room = str(data.get('room'))
    if room and session.get('user_id'):
        join_room(room)
        
        # Update analytics
        metrics = analytics_manager.update_viewer_metrics(
            room, session['user_id'], 'join'
        )
        
        # Track device type
        user_agent = request.headers.get('User-Agent', '').lower()
        analytics = analytics_manager.get_stream_analytics(room)
        if 'mobile' in user_agent:
            analytics['device_stats']['mobile'] += 1
        elif 'tablet' in user_agent:
            analytics['device_stats']['tablet'] += 1
        else:
            analytics['device_stats']['desktop'] += 1
        
        socketio.emit('analytics_update', metrics, to=room)

@socketio.on('leave_stream')
def on_leave_stream(data):
    room = str(data.get('room'))
    if room and session.get('user_id'):
        metrics = analytics_manager.update_viewer_metrics(
            room, session['user_id'], 'leave'
        )
        socketio.emit('analytics_update', metrics, to=room)
        leave_room(room)

@socketio.on('viewer_activity')
def on_viewer_activity(data):
    room = str(data.get('room'))
    if room and session.get('user_id'):
        analytics = analytics_manager.get_stream_analytics(room)
        user_id = session['user_id']
        
        if data.get('active'):
            analytics['active_viewers'].add(user_id)
        else:
            analytics['active_viewers'].discard(user_id)
        
        metrics = analytics_manager.calculate_metrics(room)
        socketio.emit('analytics_update', metrics, to=room)

@analytics_bp.route('/analytics/dashboard/<int:stream_id>')
def stream_dashboard(stream_id):
    if not session.get('is_seller'):
        return redirect(url_for('stream.list'))
    
    stream = StreamSession.query.get_or_404(stream_id)
    if stream.seller_id != session['user_id']:
        return redirect(url_for('stream.list'))
    
    analytics = analytics_manager.get_stream_analytics(str(stream_id))
    metrics = analytics_manager.calculate_metrics(str(stream_id))
    
    # Get historical data
    historical_data = db.session.query(
        func.date_trunc('hour', Order.created_at).label('hour'),
        func.sum(Order.total_amount).label('revenue'),
        func.count(Order.id).label('orders')
    ).filter(
        Order.stream_id == stream_id
    ).group_by('hour').order_by('hour').all()
    
    return render_template('analytics/dashboard.html',
                         stream=stream,
                         metrics=metrics,
                         historical_data=historical_data)

@analytics_bp.route('/api/analytics/heatmap/<int:stream_id>')
def get_heatmap_data(stream_id):
    if not session.get('is_seller'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    stream = StreamSession.query.get_or_404(stream_id)
    if stream.seller_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    analytics = analytics_manager.get_stream_analytics(str(stream_id))
    return jsonify(analytics['heatmap_data'])

@analytics_bp.route('/api/analytics/retention/<int:stream_id>')
def get_retention_data(stream_id):
    if not session.get('is_seller'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    stream = StreamSession.query.get_or_404(stream_id)
    if stream.seller_id != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    analytics = analytics_manager.get_stream_analytics(str(stream_id))
    return jsonify(analytics['retention_segments'])
