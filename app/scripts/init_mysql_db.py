import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, engine
from app.models.student import Student, StudentScore, StudentRanking, SubjectBlock, CrawlLog

def init_mysql_database():
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ MySQL database initialized successfully!")
        
        # Show created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"📋 Created tables: {tables}")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")

if __name__ == "__main__":
    init_mysql_database()