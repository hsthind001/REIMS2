from app.db.database import engine
from sqlalchemy import text

def drop_tables():
    with engine.connect() as conn:
        print("Dropping organization_members...")
        conn.execute(text("DROP TABLE IF EXISTS organization_members CASCADE"))
        print("Dropping organizations...")
        conn.execute(text("DROP TABLE IF EXISTS organizations CASCADE"))
        conn.commit()
        print("Dropped SaaS tables successfully.")

if __name__ == "__main__":
    drop_tables()
