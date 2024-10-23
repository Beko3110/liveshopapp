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

@products_bp.route('/products/populate-sample')
def populate_sample():
    # Create a sample seller if none exists
    seller = User.query.filter_by(username='sample_seller').first()
    if not seller:
        seller = User(
            username='sample_seller',
            email='seller@example.com',
            is_seller=True
        )
        seller.set_password('password123')
        db.session.add(seller)
        db.session.commit()

    # Sample products data
    sample_products = [
        {
            'name': 'Smart Watch',
            'description': 'Latest generation smartwatch with fitness tracking and notifications',
            'price': 199.99,
            'stock': 50,
            'image_url': 'https://placehold.co/600x400?text=Smart+Watch'
        },
        {
            'name': 'Wireless Earbuds',
            'description': 'Premium wireless earbuds with noise cancellation',
            'price': 149.99,
            'stock': 100,
            'image_url': 'https://placehold.co/600x400?text=Wireless+Earbuds'
        },
        {
            'name': 'Gaming Laptop',
            'description': 'High-performance gaming laptop with RTX graphics',
            'price': 1299.99,
            'stock': 25,
            'image_url': 'https://placehold.co/600x400?text=Gaming+Laptop'
        }
    ]

    # Add products to database
    for product_data in sample_products:
        product = Product.query.filter_by(name=product_data['name']).first()
        if not product:
            product = Product(**product_data, seller_id=seller.id)
            db.session.add(product)

    db.session.commit()
    flash('Sample products have been added to the database')
    return redirect(url_for('products.list'))
