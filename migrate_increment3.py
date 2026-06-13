"""Run once to add Badge and MissionTarget tables to existing database."""
from app import app, db
import sqlalchemy as sa
with app.app_context():
    db.create_all()   # creates new tables, safe to re-run
    print("Migration complete — Badge and MissionTarget tables created")
