# Software Requirements Specification (SRS)

## Delivera — Smart Delivery. Smarter Logistics.

**Version:** 1.0
**Status:** Active
**Project Type:** Smart Delivery & Logistics Management Platform

---

## 1. Project Overview

Delivera is a smart delivery and logistics management platform built with Python, Django, Django REST Framework, PostgreSQL, Django Templates, HTML, CSS, Vanilla JavaScript, and AI/LLM integration.

The system manages the complete delivery lifecycle — from shipment creation by customers, through driver assignment and warehouse handling, to final delivery, payment tracking, complaint resolution, and analytics — with an integrated AI Logistics Assistant available to all roles under strict permission control.

---

## 2. Problem Statement

Traditional delivery and logistics operations suffer from:

- Fragmented communication between customers, drivers, and managers.
- Manual and error-prone driver assignment.
- Lack of real-time shipment visibility.
- Poor handling of delayed or failed deliveries.
- Weak audit trails for critical operations.
- No intelligent assistance for decision-making.

Delivera addresses these problems through a centralized, role-based, auditable platform with an AI assistant that performs controlled actions through a secure service layer.

---

## 3. Project Objectives

- Provide a unified platform for shipment, driver, warehouse, payment, and complaint management.
- Enable real-time shipment tracking across all roles.
- Automate and simplify driver assignment and reassignment.
- Enforce strict role-based permissions.
- Integrate an AI Logistics Assistant with controlled, auditable tool execution.
- Deliver actionable analytics for managers.
- Maintain a complete audit trail for every critical action, including AI-initiated actions.

---

## 4. Project Scope

### In Scope

- Role-based access for **Customer**, **Driver**, and **Manager**.
- Shipment lifecycle management and tracking.
- Driver management and delivery assignment/reassignment.
- Warehouse management.
- Payment tracking.
- Complaint management.
- Notification system.
- Analytics dashboard.
- AI Logistics Assistant with tool-based execution.
- Audit and AI action logging.

### Out of Scope

- Native mobile applications.
- Third-party courier integrations.
- Real-time GPS hardware integration.
- Multi-tenant or multi-organization support.
- Separate Admin role (all management permissions belong to **Manager**).

---

## 5. User Roles

There are exactly **three** roles. There is **no separate Admin role**. The **Manager** holds full management and system permissions.

### 5.1 Customer

- Create shipments.
- View own shipments.
- Track shipments.
- View own payments.
- Create complaints.
- View notifications.
- Use AI Assistant according to permissions.
- Manage own profile.

### 5.2 Driver

- View assigned deliveries.
- View delivery details.
- Update permitted shipment statuses.
- Manage availability.
- Share location.
- View delivery history.
- View notifications.
- Use AI Assistant according to permissions.
- Manage own profile.

### 5.3 Manager

- Manage users.
- Manage customers.
- Manage drivers.
- Manage warehouses.
- Manage shipments.
- Assign and reassign drivers.
- Manage payments.
- Manage complaints.
- Monitor delayed deliveries.
- View analytics.
- Manage notifications.
- Review AI actions.
- Review audit logs.
- Manage system settings.
- Use AI Assistant.

---

## 6. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | The system shall support three roles: Customer, Driver, Manager. |
| FR-02 | The system shall enforce role-based permissions on every action. |
| FR-03 | The system shall allow customers to create and track shipments. |
| FR-04 | The system shall allow drivers to view and update assigned deliveries. |
| FR-05 | The system shall allow managers to manage all core entities. |
| FR-06 | The system shall assign and reassign drivers to shipments. |
| FR-07 | The system shall track payments and their statuses. |
| FR-08 | The system shall allow customers to create complaints. |
| FR-09 | The system shall send notifications based on events. |
| FR-10 | The system shall provide an analytics dashboard for managers. |
| FR-11 | The system shall provide an AI Logistics Assistant to all roles. |
| FR-12 | The system shall log AI actions and audit events. |
| FR-13 | The system shall expose a REST API via Django REST Framework. |

---

## 7. Authentication and Account Management

- The system shall use Django's authentication system.
- Users shall log in and log out securely.
- Each user shall be assigned exactly one role: Customer, Driver, or Manager.
- Customers and Drivers shall manage their own profiles.
- Managers shall manage all user accounts.
- Passwords shall be stored using Django's secure password hashing.
- Unauthorized access shall be denied by default.

---

## 8. Shipment Management

### Shipment Statuses

- `PENDING`
- `ASSIGNED`
- `PICKED_UP`
- `IN_TRANSIT`
- `OUT_FOR_DELIVERY`
- `DELIVERED`
- `CANCELLED`
- `FAILED`

### Requirements

- Customers shall create shipments.
- Customers shall view and track their own shipments.
- Drivers shall update only permitted shipment statuses.
- Managers shall manage all shipments, including status overrides.
- Managers shall monitor delayed deliveries.
- Every shipment status change shall be validated by the service layer.

---

## 9. Driver Management

- Managers shall create, update, and manage driver profiles.
- Managers shall assign and reassign drivers to shipments.
- Drivers shall manage their availability.
- Drivers shall share their location.
- Drivers shall view their delivery history.
- Assignment and reassignment operations shall be logged.

---

## 10. Warehouse Management

- Managers shall create, update, and manage warehouses.
- Warehouses shall be associated with shipments where applicable.
- Warehouse data shall be used in shipment routing and analytics.

---

## 11. Payment Management

### Payment Methods

- `CASH`
- `CARD`
- `ONLINE`

### Payment Statuses

- `PENDING`
- `PAID`
- `FAILED`
- `REFUNDED`
- `CANCELLED`

### Requirements

- Customers shall view their own payments.
- Managers shall manage all payments.
- Payment status transitions shall be validated.

---

## 12. Complaint Management

### Complaint Statuses

- `OPEN`
- `IN_PROGRESS`
- `RESOLVED`
- `CLOSED`

### Complaint Priorities

- `LOW`
- `MEDIUM`
- `HIGH`
- `URGENT`

### Requirements

- Customers shall create complaints.
- Managers shall review, update, and resolve complaints.
- Complaints shall support priority and status tracking.

---

## 13. Notification System

- The system shall generate notifications based on key events (shipment status changes, assignments, payments, complaints).
- All roles shall view their relevant notifications.
- Managers shall manage and broadcast notifications where required.

---

## 14. Analytics

- Managers shall access an analytics dashboard.
- Analytics shall include shipment, driver, warehouse, payment, and complaint metrics.
- Analytics shall highlight delayed deliveries and operational trends.

---

## 15. AI Logistics Assistant

The AI Assistant is available to **all roles**, but each role can only perform actions allowed by its permissions. The AI Agent **must never access the database directly** and must not execute arbitrary SQL.

### Controlled Tools

- `get_delivery_status()`
- `get_delayed_deliveries()`
- `get_available_drivers()`
- `get_driver_details()`
- `assign_driver()`
- `reassign_driver()`
- `update_shipment_status()`
- `get_customer_shipments()`

### AI Architecture

```
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
Database Transaction
  ↓
PostgreSQL
  ↓
Audit / AI Action Log
```

### Requirements

- Every AI action shall pass through authentication, authorization, and business validation.
- The AI Agent shall interact only through the service layer.
- Every AI action shall be recorded in the AI Action Log.

---

## 16. Security Requirements

- All requests shall be authenticated and authorized.
- Role-based permissions shall be enforced at the service layer.
- The AI Agent shall never bypass the service layer.
- All critical and AI-initiated actions shall be audited.
- Sensitive data shall be protected using Django's built-in security features.
- The system shall prevent unauthorized data access between roles.

---

## 17. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | The system shall be modular and maintainable. |
| NFR-02 | The system shall follow Django best practices. |
| NFR-03 | The system shall provide clear separation of concerns (views, services, models). |
| NFR-04 | The system shall support role-based scalability. |
| NFR-05 | The system shall log all critical operations. |
| NFR-06 | The system shall be deployable on standard Python/Django hosting. |

---

## 18. Technology Requirements

- Python
- Django
- Django REST Framework
- PostgreSQL
- Django Templates
- HTML
- CSS
- Vanilla JavaScript
- AI / LLM Integration

---

## 19. API Overview

- The system shall expose RESTful endpoints via Django REST Framework.
- Endpoints shall be grouped by domain: accounts, shipments, drivers, warehouses, payments, complaints, notifications, analytics, ai_agent.
- Every endpoint shall enforce authentication and role-based authorization.

---

## 20. Frontend Overview

- The frontend shall use Django Templates with HTML, CSS, and Vanilla JavaScript.
- The UI shall adapt to the current user's role.
- The AI Assistant shall be accessible from the UI for all roles.
- The UI shall display notifications, shipment tracking, and dashboards.

---

## 21. Expected Outcome

A secure, modular, and auditable delivery and logistics platform that:

- Centralizes shipment, driver, warehouse, payment, and complaint management.
- Enforces strict role-based permissions.
- Provides an AI Logistics Assistant with controlled, auditable tool execution.
- Delivers actionable analytics for managers.
- Maintains a full audit trail of actions, including AI-initiated ones.

---

## 22. Future Improvements

The following are **planned / not yet implemented**:

- Native mobile applications (iOS / Android).
- Real-time GPS tracking.
- Third-party courier and payment gateway integrations.
- Advanced AI capabilities (predictive ETA, route optimization).
- Multi-tenant and multi-organization support.
- Public API for external partners.
- Enhanced reporting and export options.

---

## Appendix: Main Django Apps

- `accounts`
- `shipments`
- `drivers`
- `warehouses`
- `payments`
- `complaints`
- `notifications`
- `analytics`
- `ai_agent`

> **Note:** There is no `common` app.
