"""
Database initialization script
Run this to create all tables and seed initial data
"""

from app.database import engine, Base
from app.models.user import User, APIKey, PlanLimits, UsageLog, Company
from sqlalchemy.orm import sessionmaker
from app.models.user import PlanType

def init_database():
    """Create all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
    
    # Seed plan limits data
    print("Seeding plan limits data...")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Check if plan limits already exist
    existing_plans = db.query(PlanLimits).count()
    if existing_plans == 0:
        plan_configs = [
            PlanLimits(
                plan_type=PlanType.FREE,
                monthly_documents=10,
                max_file_size_mb=5.0,
                priority_processing=False,
                support_level="Community",
                price_usd=0.0
            ),
            PlanLimits(
                plan_type=PlanType.PREMIUM,
                monthly_documents=100,
                max_file_size_mb=25.0,
                priority_processing=True,
                support_level="Email Support",
                price_usd=29.99
            ),
            PlanLimits(
                plan_type=PlanType.EXTRA_PREMIUM,
                monthly_documents=500,
                max_file_size_mb=100.0,
                priority_processing=True,
                support_level="Priority Support + Phone",
                price_usd=99.99
            )
        ]
        
        for plan in plan_configs:
            db.add(plan)
        
        db.commit()
        print("Plan limits seeded successfully!")
    else:
        print("Plan limits already exist, skipping seed.")
    
    db.close()
    print("Database initialization completed!")

if __name__ == "__main__":
    init_database()
