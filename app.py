from flask import Flask, request, session, g, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import Config
from dotenv import load_dotenv
from models import db
import logging
import requests
import json
from datetime import datetime, timedelta
from jose import jwt, jwk
from models.user import User

load_dotenv()

# Cache JWKS globally
jwks_cache = {
    'keys': None,
    'last_updated': None
}

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

def get_cognito_jwks():
    if (jwks_cache['keys'] is not None and jwks_cache['last_updated'] and
        datetime.now() - jwks_cache['last_updated'] < timedelta(hours=24)):
        return jwks_cache['keys']

    url = Config.COGNITO_JWK_URI
    response = requests.get(url)
    if response.status_code != 200:
        return None

    jwks = response.json()
    jwks_cache['keys'] = jwks
    jwks_cache['last_updated'] = datetime.now()
    return jwks



def verify_jwt_token(token):
    try:
        headers = jwt.get_unverified_header(token)
        kid = headers['kid']
        jwks = get_cognito_jwks()
        if not jwks:
            logging.warning("Cognito JWKS not available")
            return None

        key = next((k for k in jwks['keys'] if k['kid'] == kid), None)
        if not key:
            logging.warning("JWT kid not found in JWKS")
            return None

        public_key = jwk.construct(key)

        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            options={"verify_aud": False},
            issuer=Config.COGNITO_ISSUER_URI
        )

        logging.info("JWT verified successfully")
        return payload

    except jwt.ExpiredSignatureError:
        logging.warning("JWT token has expired")
    except jwt.JWTClaimsError as e:
        logging.warning(f"JWT claims validation failed: {e}")
    except jwt.JWTError as e:
        logging.warning(f"JWT decoding error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during JWT verification: {e}")

    return None


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    CORS(app, 
         resources={r"/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Range", "X-Content-Range"],
             "supports_credentials": False  # Required for sending/receiving cookies
         }})

    @app.before_request
    def load_user():
        auth_header = request.headers.get('Authorization')
        logging.debug("Checking Authorization header")

        user_id = None

        if auth_header and auth_header.startswith('Bearer '):
            logging.debug("JWT token found in Authorization header")

            token = auth_header.split()[1]
            payload = verify_jwt_token(token)
            if payload:
                cognito_sub = payload.get('sub')
                logging.info("Authenticated via JWT. Resolving user from DB.")
                user = User.query.filter_by(cognito_sub=cognito_sub).first()
                if user:
                    user_id = user.id
                    logging.info(f"Authenticated user ID resolved: {user_id}")
                else:
                    logging.warning("User not found in DB for given Cognito sub")
            else:
                logging.warning("JWT verification failed")

        elif 'user_id' in session:
            user_id = session.get('user_id')
            logging.info(f"Authenticated via session. User ID: {user_id}")

        g.user_id = user_id
        logging.debug(f"g.user_id set to: {g.user_id}")

    # Register blueprints
    from routes.company_routes import company_bp
    from routes.portfolio_routes import portfolio_bp
    app.register_blueprint(company_bp)
    app.register_blueprint(portfolio_bp)

    @app.route("/", methods=["GET"])
    def health_check():
        return jsonify({"status": "healthy"}), 200


    return app
