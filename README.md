# Delivera

**Smart Delivery. Smarter Logistics.**

Delivera is a smart delivery and logistics management platform built with Python, Django, Django REST Framework, PostgreSQL, Django Templates, HTML, CSS, Vanilla JavaScript, and AI/LLM integration.

---

## 📋 Description

Delivera is a comprehensive logistics management system that streamlines shipment handling, driver coordination, warehouse operations, and delivery tracking. It features an AI-powered logistics assistant that helps users perform actions based on their role permissions.

---

## ✨ Main Features

- Customer, Driver, and Manager roles
- Shipment management
- Shipment tracking
- Driver management
- Delivery assignment and reassignment
- Warehouse management
- Payment tracking
- Complaints
- Notifications
- Analytics dashboard
- AI Logistics Assistant
- Role-based permissions
- AI action and audit logging

---

## 👥 User Roles

| Role | Description |
|------|-------------|
| **Customer** | Create and track shipments, make payments, submit complaints |
| **Driver** | Manage assigned deliveries, update shipment status |
| **Manager** | Full management and system permissions, oversee all operations |

> **Note:** There is no separate Admin role. The Manager role has full management/system permissions.

---

## 🛠️ Technology Stack

- **Backend:** Python, Django, Django REST Framework
- **Database:** PostgreSQL
- **Frontend:** Django Templates, HTML5, CSS3, Vanilla JavaScript
- **AI:** AI / LLM Integration

---

## 🚀 Installation & Setup

### 1. Clone the repository

 
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Delivera
2. Create and activate a virtual environment
bash
python -m venv .venv
Windows:

 
.venv\Scripts\activate
Git Bash:

 
source .venv/Scripts/activate
3. Install dependencies
 
pip install -r requirements.txt
4. Create a .env file
env
DB_NAME=smart_delivery_db
DB_USER=postgres
DB_PASSWORD=YOUR_POSTGRES_PASSWORD
DB_HOST=localhost
DB_PORT=5432
5. Run migrations
bash
python manage.py migrate
6. Run the development server
bash
python manage.py runserver
7. Access the project
text
http://127.0.0.1:8000/
📁 Project Structure
text
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
🤖 AI Assistant Overview
The AI Assistant is available to all roles, but each role can only perform actions allowed by its permissions. The AI Agent never accesses the database directly.

AI Flow
text
User
  ↓
AI Agent
  ↓
Tool
  ↓
Authentication
  ↓
Authorization
  ↓
Business Validation
  ↓
Service Layer
  ↓
Database
  ↓
Audit / AI Action Log
📌 Tagline
Delivera — Smart Delivery. Smarter Logistics.
