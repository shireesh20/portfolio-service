from models import db

class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.BigInteger, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    ticker_symbol = db.Column(db.String(10), unique=True, nullable=False)
    company_description = db.Column(db.Text)
