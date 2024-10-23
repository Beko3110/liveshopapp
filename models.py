from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

# Followers association table
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_seller = db.Column(db.Boolean, default=False)
    products = db.relationship('Product', backref='seller', lazy=True)
    streams = db.relationship('StreamSession', backref='seller', lazy=True)
    language_preference = db.Column(db.String(10), default='en')
    loyalty_points = db.Column(db.Integer, default=0)
    last_daily_reward = db.Column(db.DateTime)
    
    # Followers relationship
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'),
        lazy='dynamic'
    )
    
    def __init__(self, username, email, is_seller=False):
        self.username = username
        self.email = email
        self.is_seller = is_seller
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)
    
    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)
    
    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def add_loyalty_points(self, points):
        self.loyalty_points += points
        # Check for new badge achievements
        earned_badges = []
        if self.loyalty_points >= 1000 and not self.has_badge("Gold Member"):
            badge = Badge(user_id=self.id, name="Gold Member", 
                        description="Earned 1000 loyalty points")
            db.session.add(badge)
            earned_badges.append(badge)
        elif self.loyalty_points >= 500 and not self.has_badge("Silver Member"):
            badge = Badge(user_id=self.id, name="Silver Member", 
                        description="Earned 500 loyalty points")
            db.session.add(badge)
            earned_badges.append(badge)
        elif self.loyalty_points >= 100 and not self.has_badge("Bronze Member"):
            badge = Badge(user_id=self.id, name="Bronze Member", 
                        description="Earned 100 loyalty points")
            db.session.add(badge)
            earned_badges.append(badge)
        return earned_badges

    def has_badge(self, badge_name):
        return Badge.query.filter_by(user_id=self.id, name=badge_name).first() is not None

    def claim_daily_reward(self):
        now = datetime.utcnow()
        if not self.last_daily_reward or (now - self.last_daily_reward).days >= 1:
            self.last_daily_reward = now
            points = 50  # Base daily reward
            # Bonus for consecutive days (implement later)
            self.add_loyalty_points(points)
            return points
        return 0

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='badges')

class FlashSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stream_id = db.Column(db.Integer, db.ForeignKey('stream_session.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    discount_percentage = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    stream = db.relationship('StreamSession', backref='flash_sales')
    product = db.relationship('Product', backref='flash_sales')

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200))
    stock = db.Column(db.Integer, default=0)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviews = db.relationship('Review', backref='product', lazy=True)
    comments = db.relationship('Comment', backref='product', lazy=True)
    view_count = db.Column(db.Integer, default=0)
    previous_price = db.Column(db.Float)
    last_price_change = db.Column(db.DateTime)
    category = db.Column(db.String(50))
    ar_model_url = db.Column(db.String(200))

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='wishlist_items')
    product = db.relationship('Product', backref='wishlist_entries')

class GroupBuying(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    min_buyers = db.Column(db.Integer, nullable=False)
    current_buyers = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')  # active, completed, expired
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product', backref='group_buys')

class GroupBuyingParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_buying_id = db.Column(db.Integer, db.ForeignKey('group_buying.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    group_buying = db.relationship('GroupBuying', backref='participants')
    user = db.relationship('User', backref='group_buying_participations')

# Import other required models
from models_other import Order, StreamSession, ActivityFeed, Review, Question, Poll, Message, Comment, PriceAlert, ViewHistory
