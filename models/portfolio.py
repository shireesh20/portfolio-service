from models import db

class Portfolio(db.Model):
    __tablename__ = 'portfolio'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    company_id = db.Column(db.BigInteger, db.ForeignKey('companies.id'), primary_key=True)
    current_holding_qty = db.Column(db.Integer, default=0)
    amount_invested = db.Column(db.Numeric(15, 2), default=0.00)
