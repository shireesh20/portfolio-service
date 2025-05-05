from flask import Blueprint, jsonify, request, g
from models.company import Company
import yfinance as yf
import logging

company_bp = Blueprint('company_routes', __name__)
logger = logging.getLogger(__name__)

@company_bp.route('/companies', methods=['GET'])
def get_companies():
    if not g.user_id:
        logger.warning("Unauthorized access to /companies")
        return jsonify({"error": "Authentication required. Please log in."}), 401

    logger.info(f"Fetching company list for user_id={g.user_id}")
    companies = Company.query.all()
    result = [
        {
            "company_name": c.company_name,
            "ticker_symbol": c.ticker_symbol,
            "company_description": c.company_description
        }
        for c in companies
    ]
    logger.info(f"Returned {len(result)} companies")
    return jsonify(result), 200

def format_market_cap(value):
    if value is None:
        return "N/A"
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    elif value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return str(value)

@company_bp.route('/market-overview', methods=['GET'])
def get_market_overview():
    if not g.user_id:
        logger.warning("Unauthorized access to /market-overview")
        return jsonify({"error": "Authentication required. Please log in."}), 401

    ticker_symbol = request.args.get('ticker', '').upper()
    if not ticker_symbol:
        logger.warning("Missing ticker in /market-overview request")
        return jsonify({"error": "Ticker parameter is required"}), 400

    logger.info(f"Fetching market overview for ticker: {ticker_symbol}")

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        response = {
            "ticker": ticker_symbol,
            "marketCap": format_market_cap(info.get("marketCap")),
            "volume": info.get("volume"),
            "52wHigh": info.get("fiftyTwoWeekHigh"),
            "52wLow": info.get("fiftyTwoWeekLow"),
            "peRatio": info.get("trailingPE"),
            "dividendYield": info.get("dividendYield"),
            "avgVolume": info.get("averageVolume"),
            "beta": info.get("beta")
        }

        logger.info(f"Market data returned for {ticker_symbol}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error fetching market overview for {ticker_symbol}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@company_bp.route('/current-price', methods=['GET'])
def get_current_price():
    if not g.user_id:
        logger.warning("Unauthorized access to /current-price")
        return jsonify({"error": "Authentication required. Please log in."}), 401

    ticker_symbol = request.args.get('ticker', '').upper()
    if not ticker_symbol:
        logger.warning("Missing ticker in /current-price request")
        return jsonify({"error": "Ticker parameter is required"}), 400

    logger.info(f"Fetching current price for ticker: {ticker_symbol}")

    try:
        ticker = yf.Ticker(ticker_symbol)
        current_price = ticker.fast_info.get("lastPrice")

        if current_price is None:
            logger.warning(f"Price unavailable for {ticker_symbol}")
            return jsonify({"error": "Price data unavailable"}), 404

        logger.info(f"Returned current price for {ticker_symbol}")
        return jsonify({
            "ticker": ticker_symbol,
            "currentPrice": round(current_price, 2)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching current price for {ticker_symbol}: {str(e)}")
        return jsonify({"error": str(e)}), 500
