from app import db
from flask_login import UserMixin
from sqlalchemy.sql import func

class Entry(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	file = db.Column(db.String(150))
	result = db.Column(db.String(150))
	upvotes = db.Column(db.Integer)
	in_review = db.Column(db.Boolean, default=True, nullable=False)
