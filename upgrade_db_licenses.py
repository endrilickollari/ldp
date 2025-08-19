"""Add license management tables

This migration adds the license table to support license-based access control.
"""

import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models.user import Base

def upgrade_database():
    """Run the database upgrade to add license table"""
    engine = create_engine(
        settings.DATABASE_URL, 
        connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
    )
    
    # Create all tables (this will create new ones, existing ones are ignored)
    Base.metadata.create_all(bind=engine)
    
    print("✓ License tables created successfully")
    
    # Add some sample license pricing data
    with engine.connect() as connection:
        # Check if plan_limits table has data
        result = connection.execute(text("SELECT COUNT(*) FROM plan_limits"))
        count = result.scalar()
        
        if count == 0:
            # Insert default plan limits if they don't exist
            connection.execute(text("""
                INSERT INTO plan_limits (plan_type, monthly_documents, max_file_size_mb, priority_processing, support_level, price_usd)
                VALUES 
                ('free', 10, 5.0, false, 'Community', 0.0),
                ('premium', 500, 100.0, true, 'Email support', 29.99),
                ('extra_premium', 2000, 500.0, true, '24/7 Priority support', 59.99)
                ON CONFLICT (plan_type) DO NOTHING
            """))
            connection.commit()
            print("✓ Default plan limits added")

if __name__ == "__main__":
    upgrade_database()
