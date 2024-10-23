from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_seller = request.form.get('is_seller') == 'on'
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('auth.register'))
            
        user = User(username=username, email=email, is_seller=is_seller)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['is_seller'] = user.is_seller
            return redirect(url_for('products.list'))
            
        flash('Invalid username or password')
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
