from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from models import Order, Product

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/orders')
def list():
    if not session.get('user_id'):
        flash('Please login to view orders')
        return redirect(url_for('auth.login'))
        
    orders = Order.query.filter_by(user_id=session['user_id']).all()
    return render_template('orders/list.html', orders=orders)

@orders_bp.route('/orders/create/<int:product_id>', methods=['POST'])
def create(product_id):
    if not session.get('user_id'):
        flash('Please login to place an order')
        return redirect(url_for('auth.login'))
        
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    
    if quantity > product.stock:
        flash('Not enough stock available')
        return redirect(url_for('products.list'))
        
    order = Order(
        user_id=session['user_id'],
        product_id=product_id,
        quantity=quantity,
        total_amount=product.price * quantity
    )
    
    product.stock -= quantity
    
    db.session.add(order)
    db.session.commit()
    
    flash('Order placed successfully')
    return redirect(url_for('orders.list'))
