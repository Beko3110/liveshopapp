from app import create_app, db
from models import StreamSession, Product, User, ViewHistory, PriceAlert
from sqlalchemy import text

def add_missing_columns():
    app = create_app()
    with app.app_context():
        # Add columns if they don't exist
        with db.engine.connect() as conn:
            # Add language_preference to user table
            conn.execute(text("""
                ALTER TABLE "user"
                ADD COLUMN IF NOT EXISTS language_preference VARCHAR(10) DEFAULT 'en';
            """))
            
            # Add scheduled_for to stream_session table
            conn.execute(text("""
                ALTER TABLE stream_session 
                ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMP,
                ADD COLUMN IF NOT EXISTS recording_url VARCHAR(200);
            """))
            
            # Add view_count and other analytics columns to product table
            conn.execute(text("""
                ALTER TABLE product 
                ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0,
                ADD COLUMN IF NOT EXISTS previous_price FLOAT,
                ADD COLUMN IF NOT EXISTS last_price_change TIMESTAMP;
            """))
            
            # Add votes_count to question table
            conn.execute(text("""
                ALTER TABLE question
                ADD COLUMN IF NOT EXISTS votes_count INTEGER DEFAULT 0;
            """))
            
            # Ensure view_history table exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS view_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES "user"(id),
                    product_id INTEGER REFERENCES product(id),
                    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Ensure price_alert table exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS price_alert (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES "user"(id),
                    product_id INTEGER REFERENCES product(id),
                    target_price FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE
                );
            """))
            
            conn.commit()

if __name__ == "__main__":
    add_missing_columns()
