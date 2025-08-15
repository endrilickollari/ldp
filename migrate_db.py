"""
Database migration script to add user_type and company support
Run this script to migrate existing database to support solo/enterprise users
"""

from app.database import engine, Base
from app.models.user import User, Company, UserType
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

def migrate_database():
    """Migrate database to add new user type and company features"""
    print("Starting database migration...")
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Create new tables (companies table)
        print("Creating new tables...")
        Base.metadata.create_all(bind=engine)
        print("New tables created successfully!")
        
        # Check if user_type column exists
        result = db.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'user_type' not in columns:
            print("Adding user_type column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN user_type VARCHAR DEFAULT 'solo'"))
            db.commit()
            print("user_type column added successfully!")
        
        if 'company_id' not in columns:
            print("Adding company_id column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN company_id INTEGER"))
            db.commit()
            print("company_id column added successfully!")
        
        # Update existing users to have solo user type
        print("Updating existing users to solo type...")
        db.execute(text("UPDATE users SET user_type = 'solo' WHERE user_type IS NULL"))
        db.commit()
        print("Existing users updated successfully!")
        
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_database()
