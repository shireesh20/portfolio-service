from flask import Blueprint, request, jsonify, g
from models import db
from models.company import Company
from models.portfolio import Portfolio
from models.transaction import Transaction
from models.user import User
from datetime import datetime
from decimal import Decimal
import yfinance as yf
import logging

portfolio_bp = Blueprint('portfolio_routes', __name__)
logger = logging.getLogger(__name__)

@portfolio_bp.route('/portfolio', methods=['GET'])
def get_user_portfolio():
    logger.info("Accessing /portfolio")

    if not g.user_id:
        logger.warning("Unauthorized portfolio access attempt")
        return jsonify({"error": "Authentication required. Please log in."}), 401

    try:
        results = db.session.query(
            Portfolio.company_id,
            Portfolio.current_holding_qty,
            Portfolio.amount_invested,
            Company.company_name,
            Company.ticker_symbol
        ).join(Company, Portfolio.company_id == Company.id
        ).filter(Portfolio.user_id == g.user_id).all()

        portfolio_list = []
        total_invested = 0.0
        total_current_value = 0.0

        for row in results:
            ticker = row.ticker_symbol
            current_price = None
            try:
                current_price = yf.Ticker(ticker).fast_info.get("lastPrice")
                logger.debug(f"Fetched price for {ticker}: {current_price}")
            except Exception as e:
                logger.warning(f"Failed to fetch price for {ticker}: {e}")
                current_price = None

            invested = float(row.amount_invested)
            qty = row.current_holding_qty

            if current_price is not None:
                current_value = current_price * qty
                profit_or_loss_amount = round(current_value - invested, 2)
                profit_or_loss_percent = (
                    round((profit_or_loss_amount / invested) * 100, 2)
                    if invested != 0 else None
                )
                status = (
                    "Profit" if profit_or_loss_amount > 0 else
                    "Loss" if profit_or_loss_amount < 0 else
                    "Break-even"
                )

                # Aggregate totals
                total_invested += invested
                total_current_value += current_value
            else:
                current_value = None
                profit_or_loss_amount = None
                profit_or_loss_percent = None
                status = "Price unavailable"

            portfolio_list.append({
                "company_id": row.company_id,
                "company_name": row.company_name,
                "ticker_symbol": row.ticker_symbol,
                "current_holding_qty": qty,
                "amount_invested": invested,
                "current_price": round(current_price, 2) if current_price else None,
                "profit_or_loss_amount": profit_or_loss_amount,
                "profit_or_loss_percent": profit_or_loss_percent,
                "status": status
            })

        # Summary totals
        total_profit_or_loss_amount = round(total_current_value - total_invested, 2)
        total_profit_or_loss_percent = (
            round((total_profit_or_loss_amount / total_invested) * 100, 2)
            if total_invested > 0 else None
        )
        # Determine overall status
        if total_profit_or_loss_amount > 0:
            overall_status = "Profit"
        elif total_profit_or_loss_amount < 0:
            overall_status = "Loss"
        else:
            overall_status = "Break-even"

        response = {
            "portfolio": portfolio_list,
            "summary": {
                "total_amount_invested": round(total_invested, 2),
                "total_profit_or_loss_amount": total_profit_or_loss_amount,
                "total_profit_or_loss_percent": total_profit_or_loss_percent,
                "status": overall_status
            }
        }

        logger.info(f"Returned portfolio for user_id={g.user_id} with {len(portfolio_list)} entries")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error in /portfolio for user_id={g.user_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500



@portfolio_bp.route('/transaction', methods=['POST'])
def post_transaction():
    logger.info("POST /transaction request received")

    if not g.user_id:
        logger.warning("Unauthorized transaction attempt")
        return jsonify({"error": "Authentication required"}), 401

    data = request.get_json()
    required_fields = ['ticker', 'trade_qty', 'action', 'action_price', 'timestamp']
    if not all(field in data for field in required_fields):
        logger.warning("Transaction missing required fields")
        return jsonify({"error": "Missing required fields"}), 400

    ticker = data['ticker'].upper()
    trade_qty = int(data['trade_qty'])
    action = data['action'].upper()
    action_price = Decimal(str(data['action_price']))

    try:
        timestamp = datetime.fromisoformat(data['timestamp'])
    except ValueError:
        logger.warning("Invalid timestamp format")
        return jsonify({"error": "Invalid timestamp format. Use ISO 8601."}), 400

    company = Company.query.filter_by(ticker_symbol=ticker).first()
    if not company:
        logger.warning(f"Invalid ticker submitted: {ticker}")
        return jsonify({"error": "Invalid ticker"}), 404

    if action not in ['BUY', 'SELL']:
        logger.warning(f"Invalid action submitted: {action}")
        return jsonify({"error": "Action must be 'BUY' or 'SELL'"}), 400

    if action == 'BUY' and not (1 <= trade_qty <= 100):
        logger.warning(f"Invalid BUY quantity: {trade_qty}")
        return jsonify({"error": "Buy quantity must be between 1 and 100"}), 400

    if action == 'SELL':
        portfolio = Portfolio.query.filter_by(user_id=g.user_id, company_id=company.id).first()
        if not portfolio or portfolio.current_holding_qty < trade_qty:
            logger.warning(f"Attempted to sell more shares than owned for {ticker}")
            return jsonify({"error": "Not enough shares to sell"}), 400

    try:
        # Insert transaction
        new_txn = Transaction(
            user_id=g.user_id,
            company_id=company.id,
            quantity=trade_qty,
            action=action,
            action_price=action_price,
            timestamp=timestamp
        )
        db.session.add(new_txn)
        logger.info(f"Recorded {action} transaction for user_id={g.user_id}, ticker={ticker}, qty={trade_qty}")

        # Update portfolio
        portfolio = Portfolio.query.filter_by(user_id=g.user_id, company_id=company.id).first()

        if action == 'BUY':
            if not portfolio:
                portfolio = Portfolio(
                    user_id=g.user_id,
                    company_id=company.id,
                    current_holding_qty=trade_qty,
                    amount_invested=trade_qty * action_price
                )
                db.session.add(portfolio)
                logger.info(f"Created new portfolio entry for {ticker}")
            else:
                portfolio.current_holding_qty += trade_qty
                portfolio.amount_invested += trade_qty * action_price
                logger.info(f"Updated portfolio (BUY) for {ticker}")

        elif action == 'SELL':
            portfolio.current_holding_qty -= trade_qty
            portfolio.amount_invested -= trade_qty * action_price
            logger.info(f"Updated portfolio (SELL) for {ticker}")
            if portfolio.current_holding_qty == 0:
                db.session.delete(portfolio)
                logger.info(f"Removed portfolio entry for {ticker} (holding reduced to 0)")

        db.session.commit()
        logger.info("Transaction committed successfully")
        return jsonify({"message": "Transaction recorded successfully"}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing transaction: {str(e)}")
        return jsonify({"error": str(e)}), 500
