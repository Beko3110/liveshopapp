from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db, socketio
from flask_socketio import join_room, emit
from models import StreamSession, Product, User, Question, Poll, ActivityFeed
from datetime import datetime
from sqlalchemy import desc

stream_bp = Blueprint('stream', __name__)

@stream_bp.route('/stream/create', methods=['GET', 'POST'])
def create():
    if not session.get('is_seller'):
        flash('Only sellers can create streams')
        return redirect(url_for('products.list'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        scheduled_for = request.form.get('scheduled_for')
        notify_followers = request.form.get('notify_followers') == 'on'
        
        scheduled_datetime = datetime.strptime(scheduled_for, '%Y-%m-%dT%H:%M') if scheduled_for else None
        
        # Validate scheduled time is in the future
        if scheduled_datetime and scheduled_datetime <= datetime.utcnow():
            flash('Stream schedule time must be in the future')
            return redirect(url_for('stream.create'))
        
        stream = StreamSession(
            seller_id=session['user_id'],
            title=title,
            scheduled_for=scheduled_datetime
        )
        
        db.session.add(stream)
        
        # Create activity feed entry for new stream
        activity = ActivityFeed(
            user_id=session['user_id'],
            activity_type='stream_scheduled' if scheduled_datetime else 'stream_start',
            target_id=stream.id
        )
        db.session.add(activity)
        
        # If notify followers is enabled and stream is scheduled
        if notify_followers and scheduled_datetime:
            seller = User.query.get(session['user_id'])
            for follower in seller.followers:
                # Here we would typically create notifications for followers
                # This would be implemented in a notification system
                pass
                
        db.session.commit()
        
        if scheduled_datetime:
            flash(f'Stream scheduled for {scheduled_for}')
            return redirect(url_for('products.list'))
        else:
            return redirect(url_for('stream.room', stream_id=stream.id))
        
    return render_template('stream/create.html')

@stream_bp.route('/stream/<int:stream_id>')
def room(stream_id):
    stream = StreamSession.query.get_or_404(stream_id)
    products = Product.query.filter_by(seller_id=stream.seller_id).all()
    
    # Check if stream is scheduled for future
    if stream.scheduled_for and stream.scheduled_for > datetime.utcnow():
        flash('This stream has not started yet')
        return redirect(url_for('products.list'))
    
    # Get questions sorted by votes_count and timestamp
    questions = Question.query.filter_by(stream_id=stream_id)\
        .order_by(desc(Question.votes_count), desc(Question.created_at))\
        .all()
    
    # Get active polls
    polls = Poll.query.filter_by(stream_id=stream_id, status='active').all()
    
    return render_template('stream/room.html', 
                         stream=stream, 
                         products=products, 
                         questions=questions,
                         polls=polls)

@socketio.on('join_room')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('chat_message')
def on_chat_message(data):
    if not session.get('user_id'):
        return
        
    user = User.query.get(session['user_id'])
    if user:
        emit('chat_message', {
            'username': user.username,
            'message': data['message']
        }, room=data['room'])

@socketio.on('submit_question')
def on_submit_question(data):
    if not session.get('user_id'):
        return
    
    user = User.query.get(session['user_id'])
    if user:
        question = Question(
            stream_id=int(data['room']),
            user_id=user.id,
            question=data['question']
        )
        
        db.session.add(question)
        db.session.commit()
        
        stream = StreamSession.query.get(question.stream_id)
        emit('new_question', {
            'id': question.id,
            'username': user.username,
            'question': question.question,
            'time': question.created_at.strftime('%H:%M'),
            'is_seller': session.get('user_id') == stream.seller_id
        }, room=data['room'])

@socketio.on('submit_answer')
def on_submit_answer(data):
    if not session.get('user_id'):
        return
        
    question = Question.query.get(int(data['question_id']))
    if question:
        stream = StreamSession.query.get(question.stream_id)
        if session.get('user_id') == stream.seller_id:
            question.answer = data['answer']
            question.status = 'answered'
            db.session.commit()
            
            emit('question_answered', {
                'question_id': question.id,
                'answer': question.answer
            }, room=data['room'])

@socketio.on('vote_question')
def on_vote_question(data):
    if not session.get('user_id'):
        return
        
    question = Question.query.get(int(data['question_id']))
    if question:
        question.votes_count += 1
        db.session.commit()
        
        emit('question_voted', {
            'question_id': question.id,
            'votes': question.votes_count
        }, room=data['room'])

@socketio.on('create_poll')
def on_create_poll(data):
    if not session.get('user_id') or not session.get('is_seller'):
        return
        
    poll = Poll(
        stream_id=int(data['room']),
        question=data['question'],
        options=data['options']
    )
    
    db.session.add(poll)
    db.session.commit()
    
    emit('new_poll', {
        'id': poll.id,
        'question': poll.question,
        'options': poll.options,
        'is_seller': True
    }, room=data['room'])

@socketio.on('vote_poll')
def on_vote_poll(data):
    if not session.get('user_id'):
        return
        
    poll = Poll.query.get(int(data['poll_id']))
    if poll and poll.status == 'active':
        option = data['option']
        if option in poll.options:
            if not poll.votes:
                poll.votes = {}
            poll.votes[option] = poll.votes.get(option, 0) + 1
            db.session.commit()
            
            total_votes = sum(poll.votes.values())
            emit('poll_updated', {
                'poll_id': poll.id,
                'votes': poll.votes,
                'total_votes': total_votes
            }, room=data['room'])

@socketio.on('close_poll')
def on_close_poll(data):
    if not session.get('user_id') or not session.get('is_seller'):
        return
        
    poll = Poll.query.get(int(data['poll_id']))
    if poll:
        poll.status = 'closed'
        db.session.commit()
        
        emit('poll_closed', {
            'poll_id': poll.id
        }, room=data['room'])
