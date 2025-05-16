# portfolio-service

This service is a backend module for managing user investment portfolios in the Stock Market Predictive Analysis system. It enables users to log buy/sell transactions, view current holdings, and fetch company or stock price data using real-time sources like Yahoo Finance.

---

## Features

- User-specific portfolio tracking
- Buy/sell stock transaction support
- Real-time stock price retrieval via yFinance
- Secure endpoints requiring user authentication context (`g.user_id`)

---

## Tech Stack

- **Python 3**
- **Flask**
- **SQLAlchemy**
- **yFinance**
- **Docker** (for containerization)
- **Gunicorn** (for WSGI deployment)

---

# Getting Started

## 1. Clone & Install Dependencies
commands:
  - git clone https://github.com/shireesh20/portfolio-service
  - cd portfolio-service
  - pip install -r requirements.txt

## 2. Set Environment Variables
.env:
  DB_USER
  DB_PASSWORD
  DB_HOST
  DB_PORT
  DB_NAME
  AWS_REGION
  COGNITO_USER_POOL_ID
  COGNITO_APP_CLIENT_ID
  COGNITO_APP_CLIENT_SECRET

Set all these values in Github Secrets if you are running this on cloud

## 3. Run the App (Development)
run:
  - python app.py

## 4. Run with WSGI (Production)
gunicorn:
  - gunicorn wsgi:app

## 5. Run with Docker
docker:
  - docker-compose up --build
## 6. Run in Cloud
  - Set Github secrets(mentioned in .env and additionally AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, PUBLIC_SUBNET_1, PUBLIC_SUBNET_2, VPC_ID)
  - Create the roles required in IAM
  - Create a cloudwatch log group
  - Create a ECR repo
  - Run the pipeline deploy.sh
