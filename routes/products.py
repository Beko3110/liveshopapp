from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from models import Product, User, StreamSession

products_bp = Blueprint('products', __name__)

@products_bp.route('/')
@products_bp.route('/products')
def list():
    products = Product.query.all()
    active_streams = StreamSession.query.filter_by(status='active').all()
    return render_template('products/list.html', products=products, active_streams=active_streams)

# ... rest of the file remains unchanged ...
