from models import db

class Transaction(db.Model):
    __tablename__ = 'transactions'

    transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_id = db.Column(db.BigInteger, db.ForeignKey('companies.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    action = db.Column(db.Enum('BUY', 'SELL'), nullable=False)
    action_price = db.Column(db.Numeric(10, 2), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
