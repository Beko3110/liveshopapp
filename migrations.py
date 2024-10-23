from app import create_app, db
from models import StreamSession, Product, User, ViewHistory, PriceAlert
from sqlalchemy import text

def add_missing_columns():
    app = create_app()
    with app.app_context():
        # Add columns if they don't exist
        with db.engine.connect() as conn:
            # Add loyalty points and last daily reward to user table
            conn.execute(text("""
                ALTER TABLE "user"
                ADD COLUMN IF NOT EXISTS loyalty_points INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS last_daily_reward TIMESTAMP;
            """))
            
            # Add AR model URL and category to product table
            conn.execute(text("""
                ALTER TABLE product 
                ADD COLUMN IF NOT EXISTS ar_model_url VARCHAR(200),
                ADD COLUMN IF NOT EXISTS category VARCHAR(50);
            """))
            
            # Create badge table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS badge (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES "user"(id),
                    name VARCHAR(50) NOT NULL,
                    description VARCHAR(200),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create flash sale table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS flash_sale (
                    id SERIAL PRIMARY KEY,
                    stream_id INTEGER REFERENCES stream_session(id),
                    product_id INTEGER REFERENCES product(id),
                    discount_percentage INTEGER NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create wishlist table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS wishlist (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES "user"(id),
                    product_id INTEGER REFERENCES product(id),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Create group buying tables
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS group_buying (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES product(id),
                    target_price FLOAT NOT NULL,
                    min_buyers INTEGER NOT NULL,
                    current_buyers INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'active',
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS group_buying_participant (
                    id SERIAL PRIMARY KEY,
                    group_buying_id INTEGER REFERENCES group_buying(id),
                    user_id INTEGER REFERENCES "user"(id),
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            conn.commit()

if __name__ == "__main__":
    add_missing_columns()
