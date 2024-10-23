from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db, socketio
from flask_socketio import join_room
from models import StreamSession, Product, User

stream_bp = Blueprint('stream', __name__)

@stream_bp.route('/stream/create', methods=['GET', 'POST'])
def create():
    if not session.get('is_seller'):
        flash('Only sellers can create streams')
        return redirect(url_for('products.list'))
        
    if request.method == 'POST':
        stream = StreamSession(
            seller_id=session['user_id'],
            title=request.form.get('title')
        )
        
        db.session.add(stream)
        db.session.commit()
        
        return redirect(url_for('stream.room', stream_id=stream.id))
        
    return render_template('stream/create.html')

@stream_bp.route('/stream/<int:stream_id>')
def room(stream_id):
    stream = StreamSession.query.get_or_404(stream_id)
    products = Product.query.filter_by(seller_id=stream.seller_id).all()
    return render_template('stream/room.html', stream=stream, products=products)

@socketio.on('join_room')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('chat_message')
def on_chat_message(data):
    room = data['room']
    user = User.query.get(session['user_id'])
    socketio.emit('chat_message', {
        'username': user.username,
        'message': data['message']
    }, room=room)
