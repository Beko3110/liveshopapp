from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from models import Product, User

products_bp = Blueprint('products', __name__)

@products_bp.route('/')
@products_bp.route('/products')
def list():
    products = Product.query.all()
    return render_template('products/list.html', products=products)

@products_bp.route('/products/manage')
def manage():
    if not session.get('is_seller'):
        flash('Only sellers can manage products')
        return redirect(url_for('products.list'))
        
    seller_id = session.get('user_id')
    products = Product.query.filter_by(seller_id=seller_id).all()
    return render_template('products/manage.html', products=products)

@products_bp.route('/products/create', methods=['GET', 'POST'])
def create():
    if not session.get('is_seller'):
        flash('Only sellers can create products')
        return redirect(url_for('products.list'))
        
    if request.method == 'POST':
        product = Product(
            name=request.form.get('name'),
            description=request.form.get('description'),
            price=float(request.form.get('price')),
            stock=int(request.form.get('stock')),
            image_url=request.form.get('image_url'),
            seller_id=session['user_id']
        )
        
        db.session.add(product)
        db.session.commit()
        
        flash('Product created successfully')
        return redirect(url_for('products.manage'))
        
    return render_template('products/form.html')
