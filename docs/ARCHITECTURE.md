# System Architecture

## Delivera — Smart Delivery. Smarter Logistics.

**Version:** 1.0
**Status:** Active
**Stack:** Python · Django · DRF · PostgreSQL · Django Templates · HTML/CSS/JS · AI/LLM

---

## 1. Architecture Overview

Delivera is a **monolithic Django application** organized into **domain-driven apps** under `apps/`, with a **layered internal architecture** (Presentation → Permission → Service → Model). It exposes both **server-rendered pages** (Django Templates) and **REST APIs** (Django REST Framework), and integrates an **AI Logistics Assistant** that executes controlled tools through the same service and permission layers used by regular requests.

**Core principles:**

- Clear separation of concerns via layers and apps.
- Role-based access enforced at the permission and service layers.
- The AI Agent **never** touches the database directly.
- Every critical action — including AI-initiated ones — is auditable.

---

## 2. High-Level Architecture

```
Browser
  ↓
Django Templates + HTML / CSS / JavaScript
  ↓
Django
├── Views
├── REST APIs
├── Services
├── Authentication / Authorization
└── AI Agent
  ↓
PostgreSQL
```

---

## 3. Backend Architecture

- **Framework:** Django (MVT) + Django REST Framework for APIs.
- **Apps:** Domain-scoped apps under `apps/`, each owning its models, views, serializers, services, URLs, and migrations.
- **Service layer:** Encapsulates business logic and is the **only** entry point to models for mutations.
- **Database:** PostgreSQL accessed exclusively through the Django ORM.
- **AI Agent:** A dedicated `ai_agent` app that maps user intent to registered tools and routes them through the service layer.

---

## 4. Django Application Architecture

```
apps/
├── accounts/
├── shipments/
├── drivers/
├── warehouses/
├── payments/
├── complaints/
├── notifications/
├── analytics/
└── ai_agent/
```

> **Note:** There is **no `common` app.** Each domain is self-contained.

### App Responsibilities

| App | Responsibility |
|-----|----------------|
| `accounts` | Users, roles, profiles, authentication |
| `shipments` | Shipments, assignments, status history |
| `drivers` | Driver profiles, vehicles, locations |
| `warehouses` | Warehouse data and management |
| `payments` | Payment records and statuses |
| `complaints` | Customer complaints and resolution |
| `notifications` | User notifications |
| `analytics` | Dashboard metrics, audit logs |
| `ai_agent` | AI tool registry, execution, AIAction log |

---

## 5. Layered Architecture

```
Presentation Layer
  ↓
Views / API Views
  ↓
Permission Layer
  ↓
Service Layer
  ↓
Models / Database
```

### Layer Responsibilities

| Layer | Responsibility |
|-------|----------------|
| **Presentation** | Templates, static assets, client-side JS |
| **Views / API Views** | Request handling, input parsing, response shaping |
| **Permission** | Role checks, ownership checks, tool permissions |
| **Service** | Business rules, validation, orchestration, transactions |
| **Models / Database** | ORM entities, constraints, persistence |

**Rule:** Views and AI tools **must not** mutate models directly. All mutations flow through the **Service Layer**.

---

## 6. Frontend Architecture

```
templates/
├── base.html
├── components/
├── landingpage/
├── auth/
├── customer/
├── driver/
└── manager/
```

### Shared Components

- `navbar`
- `footer`
- `chatbot`
- `alerts`
- `pagination`
- `sidebar`

### Structure

- `base.html` provides the common layout, includes shared components, and loads global CSS/JS.
- Role-specific folders (`customer/`, `driver/`, `manager/`) contain role-tailored pages.
- `auth/` contains login and account pages.
- `landingpage/` contains public marketing pages.

---

## 7. Static Files Architecture

```
static/
├── css/
├── imgs/
└── js/
```

### CSS Files

- `main.css`
- `components.css`
- `dashboard.css`
- `auth.css`
- `landingpage.css`

### JavaScript Files

- `main.js`
- `sidebar.js`
- `dashboard.js`
- `auth.js`
- `chatbot.js`
- `ai_assistant.js`
- `shipments.js`
- `tracking.js`
- `notifications.js`
- `analytics.js`
- `landingpage.js`

**Notes:**

- `main.js` provides shared behavior; feature scripts are loaded per page.
- `chatbot.js` + `ai_assistant.js` implement the AI Assistant UI.

---

## 8. API Architecture

The API is exposed via Django REST Framework and organized by domain:

```
/api/accounts/
/api/shipments/
/api/drivers/
/api/warehouses/
/api/payments/
/api/complaints/
/api/notifications/
/api/analytics/
/api/ai-agent/
```

**Conventions:**

- All endpoints enforce authentication and role-based authorization.
- Serializers handle input validation and output shaping.
- Write operations delegate to the **service layer**.

---

## 9. Authentication and Authorization

- **Authentication:** Django's authentication system (session-based for pages, token/session for API).
- **Authorization:** Role-based at the **permission layer** and re-checked at the **service layer**.
- **Roles:** `CUSTOMER`, `DRIVER`, `MANAGER`.
- **No Admin role:** The Manager holds all management and system permissions.
- **Ownership checks:** Enforced for customer-owned and driver-assigned resources.

---

## 10. AI Agent Architecture

The AI Agent is available to **all roles** but can only perform actions allowed by the caller's permissions.

**Hard rules:**

- The AI Agent **must never** access PostgreSQL directly.
- The AI Agent **must never** execute arbitrary SQL.
- Every AI tool call passes through Authentication → Authorization → Business Validation → Service Layer.

### Components

- **Tool Registry:** Defines available tools and their schemas.
- **Tool Executor:** Runs a selected tool with validated inputs.
- **Permission Gate:** Verifies the calling user's role and ownership.
- **Service Bridge:** Calls the appropriate service function.
- **AIAction Logger:** Records every execution in `AIAction`.

---

## 11. AI Tool Execution Flow

```
User
  ↓
AI Assistant
  ↓
AI Agent
  ↓
Tool Selection
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
AI Action / Audit Log
```

### Tools

```
get_delivery_status()
get_delayed_deliveries()
get_available_drivers()
get_driver_details()
assign_driver()
reassign_driver()
update_shipment_status()
get_customer_shipments()
```

---

## 12. Role-Based Access Architecture

### Customer
- Own shipments
- Own payments
- Own complaints
- Own notifications
- AI Assistant (permission-scoped)
- Profile

### Driver
- Assigned deliveries
- Delivery history
- Availability
- Location
- Notifications
- AI Assistant (permission-scoped)
- Profile

### Manager
- Users
- Customers
- Drivers
- Warehouses
- Shipments
- Assignments
- Payments
- Complaints
- Delayed deliveries
- Analytics
- Notifications
- AI Assistant
- AI Actions
- Audit Logs
- Settings

> There is **no separate Admin role.**

**Enforcement model:**

- Permission layer rejects unauthorized routes/actions.
- Service layer re-verifies ownership and role before mutations.
- AI tools use the same permission gate as regular requests.

---

## 13. Database Architecture

- **Engine:** PostgreSQL
- **Access:** Django ORM only
- **Transactions:** Used for multi-step writes (e.g., assignment, reassignment, status change).
- **Key rules:**
  - `Shipment` has no direct driver field.
  - Driver assignment is via `DeliveryAssignment` (supports reassignment and history).
  - Only one active `DeliveryAssignment` per shipment.

---

## 14. Security Architecture

| Concern | Approach |
|---------|----------|
| Authentication | Django auth system |
| Authorization | Role + ownership checks |
| Role-based permissions | Permission layer + service layer |
| Input validation | Serializers + service validation |
| Business validation | Service layer |
| CSRF protection | Django CSRF middleware |
| Secure passwords | Django password hashing |
| Environment variables | `.env` (DB credentials, secrets) |
| AI tool permissions | Same permission gate as regular requests |
| Audit logging | `AuditLog` + `AIAction` |
| Database access | Restricted — no direct AI access, no raw SQL from AI |

---

## 15. Design Principles

1. **Separation of concerns** — each app owns its domain.
2. **Single source of truth** — business logic lives in the service layer.
3. **Defense in depth** — permissions enforced at multiple layers.
4. **Auditability by design** — every critical action is logged.
5. **Explicit over implicit** — no hidden DB access, no magic.
6. **Modularity** — apps are independent and testable.
7. **Least privilege** — users and AI tools only see what they need.

---

## 16. Scalability / Future Improvements

> The following are **Planned / Not yet implemented**:

- Horizontal scaling with a load balancer and stateless app servers.
- Background workers (Celery/RQ) for notifications and heavy jobs.
- Caching layer (Redis) for dashboards and hot reads.
- Real-time updates via WebSockets for tracking and notifications.
- Advanced AI capabilities (predictive ETA, route optimization).
- Multi-tenant / multi-organization support.
- Public API for external partners.
- Native mobile applications (iOS / Android).

---

## Appendix: End-to-End Request Flow

```
Browser
  ↓
Django URL Router
  ↓
View / API View
  ↓
Permission Layer (role + ownership)
  ↓
Service Layer (business validation)
  ↓
Django ORM
  ↓
PostgreSQL
  ↓
Response (Template or JSON)
```

## Appendix: AI End-to-End Flow

```
User → AI Assistant → AI Agent → Tool → Auth → Authz
     → Business Validation → Service → Transaction
     → PostgreSQL → AI Action / Audit Log
```
