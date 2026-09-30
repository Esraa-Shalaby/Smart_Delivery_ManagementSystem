
# 🚚 Delivera

### Smart Delivery. Smarter Logistics.

Delivera is a smart delivery and logistics management platform built with Django and PostgreSQL. It manages shipments, customers, drivers, warehouses, payments, complaints, notifications, analytics, and provides an AI-powered logistics assistant.

## ✨ Features
- 👤 Customer, Driver, and Manager roles
- 📦 Shipment management and tracking
- 🚗 Driver and delivery management
- 🏢 Warehouse management
- 💳 Payment tracking
- 📢 Complaints and notifications
- 📊 Analytics dashboard
- 🤖 AI Logistics Assistant
- 🔐 Role-based permissions

## 🛠️ Tech Stack
Python · Django · Django REST Framework · PostgreSQL · HTML · CSS · JavaScript · AI/LLM

## 🚀 Installation

git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Delivera
python -m venv .venv

### Windows
.venv\Scripts\activate

### Git Bash
source .venv/Scripts/activate

### Install Dependencies
pip install -r requirements.txt

### Configure Environment Variables

Create a .env file in the project root:

DB_NAME=smart_delivery_db
DB_USER=postgres
DB_PASSWORD=YOUR_POSTGRES_PASSWORD
DB_HOST=localhost
DB_PORT=5432

### Run Migrations
python manage.py migrate

### Run the Server
python manage.py runserver

Open: http://127.0.0.1:8000/

## 📁 Project Structure

Delivera/
├── apps/
├── config/
├── templates/
├── static/
├── manage.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md

## 👩‍💻 Project

Delivera — Smart Delivery & Logistics

Smart Delivery. Smarter Logistics.
