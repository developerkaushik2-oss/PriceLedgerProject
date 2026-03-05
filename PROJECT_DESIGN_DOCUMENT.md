# Price Ledger Project - Design Document

**Project Name:** Price Ledger  
**Version:** 1.0.0  
**Date:** March 2026  
**Status:** Production Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Context Diagram](#context-diagram)
3. [Solution Architecture](#solution-architecture)
4. [Design Decisions](#design-decisions)
5. [Non-Functional Requirements](#non-functional-requirements)
6. [Assumptions](#assumptions)
7. [Implementation Sources](#implementation-sources)

---

## Executive Summary

**Price Ledger** is an enterprise-grade pricing management platform designed for retail chains with 3000+ store locations globally. The system enables centralized collection, validation, storage, and analysis of pricing data across distributed store networks.

### Key Capabilities

- **Bulk CSV Upload** with async processing for large files (up to 50MB)
- **Advanced Search & Filtering** with pagination and real-time results
- **Data Validation** with duplicate detection and conflict resolution
- **Multi-Region Support** with currency and locale awareness
- **Horizontal Scalability** with containerized architecture

### Technology Stack

| Layer             | Technology     | Version | Purpose                                 |
| ----------------- | -------------- | ------- | --------------------------------------- |
| **Presentation**  | Angular        | 17.x    | Single Page Application (SPA)           |
| **API**           | Python Flask   | 2.3.3   | RESTful API with Flask-RESTX            |
| **Database**      | PostgreSQL     | 15      | Primary data store with ACID guarantees |
| **Cache/Queue**   | Redis          | 7       | Message broker, cache, session store    |
| **Task Queue**    | Celery         | 5.3+    | Async task processing                   |
| **Container**     | Docker         | Latest  | Infrastructure as Code                  |
| **Orchestration** | Docker Compose | v3+     | Multi-container environment             |

---

## Context Diagram

### System Boundaries & External Interactions

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SYSTEMS                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐     ┌──────────────────┐    ┌──────────────┐ │
│  │  Store Systems   │     │  Regional Hubs   │    │ Admin Portal │ │
│  │  (POS, Inventory)│     │  (Email, SMS)    │    │  (Reports)   │ │
│  └────────┬─────────┘     └────────┬─────────┘    └──────┬───────┘ │
│           │                        │                     │          │
│           ↓ CSV Files              ↓ Notifications       ↓ Browser  │
│  ┌────────────────────────────────────────────────────────────────┐│
│  │                    PRICE LEDGER SYSTEM                         ││
│  │                                                                ││
│  │  ┌──────────────┐         ┌──────────────┐   ┌────────────┐  ││
│  │  │  Web UI      │◄────────│  REST API    │───│ Validation │  ││
│  │  │  (Angular)   │         │  (Flask)     │   │  Engine    │  ││
│  │  └──────────────┘         └──────┬───────┘   └────────────┘  ││
│  │         ▲                        │                            ││
│  │         │                        ↓                            ││
│  │         │                  ┌──────────────┐                  ││
│  │         │                  │ Task Queue   │                  ││
│  │         │                  │  (Celery)    │                  ││
│  │         │                  └──────┬───────┘                  ││
│  │         │                        │                            ││
│  │         │                        ↓                            ││
│  │         │              ┌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐                      ││
│  │         │              ║ PostgreSQL  ║                      ││
│  │         └──────────────║   Database  ║                      ││
│  │                        ║ (Primary)   ║                      ││
│  │          ┌─────────────╌╌╌╌╌╌╌╌╌╌╌╌╌╌┐                      ││
│  │          │             └──────┬───────┘                      ││
│  │          ↓                     │                             ││
│  │    ┌──────────────┐            ↓                             ││
│  │    │ Redis Cache  │      ┌──────────────┐                   ││
│  │    │  (Session,   ├──────│ File Storage │                   ││
│  │    │  Message Q)  │      │  (Uploads)   │                   ││
│  │    └──────────────┘      └──────────────┘                   ││
│  │                                                                ││
│  └────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │          EXTERNAL INTEGRATIONS (Future)                      │  │
│  │  • Email Service (SendGrid/AWS SES)                          │  │
│  │  • Analytics Platform (Mixpanel/Amplitude)                  │  │
│  │  • Data Warehouse (Snowflake/BigQuery)                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow - CSV Upload Process

```
User Interface                API Layer              Processing           Database
─────────────────            ──────────              ──────────           ────────

[Browser]
    │
    │ 1. Click Upload CSV
    │
    ├────────► [Upload Component]
    │              │
    │              │ 2. File Selected
    │              │
    │              ├────────► [Flask API]
    │              │              │
    │              │              │ 3. Validate File
    │              │              │    - Check format
    │              │              │    - Check size
    │              │              │
    │              │              ├────────► [Celery Task]
    │              │              │              │
    │              │              │ 4. Queue Job │ 5. Parse CSV
    │              │              │    + Task ID │    Validate Data
    │              │              │              │    Check Duplicates
    │              │              │
    │◄─────────────┤◄─────────────┤              │
    │ Response:                                   │
    │ 202 Accepted                               │
    │ + task_id                                  │
    │              ┌──────────────────────────────┤
    │              │                              │
    │              │ 6. Poll Status               │
    │              │    /upload_status/{task_id}  ├──────────► [PostgreSQL]
    │              │                              │    INSERT Records
    │◄─────────────┤◄─────────────────────────────┤
    │ Status: Processing                         │
    │              │                              │
    │ (Repeat polling every 1 sec)                │
    │              │                              │
    │              │ 7. Final Status              │
    │              │    Success + Count           │
    │◄─────────────┤◄─────────────────────────────┤
    │ Alert: "1,234 records imported"            │
    │                                             │
```

---

## Solution Architecture

### 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Angular 17 SPA                                          │  │
│  │  ├─ Upload Component      (File ingestion UI)           │  │
│  │  ├─ Search Component      (Filtering & Discovery)       │  │
│  │  ├─ Dashboard Component   (Analytics & KPIs)            │  │
│  │  ├─ Shared Services       (HTTP, State Mgmt)            │  │
│  │  └─ Interceptors          (Auth, Error Handling)        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              ↕         (REST/JSON)              │
├─────────────────────────────────────────────────────────────────┤
│                      API LAYER (Flask)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Flask Application                                       │  │
│  │  ├─ pricing_api.py     (CSV Upload, Search, CRUD)      │  │
│  │  ├─ stats_api.py       (Analytics endpoints)            │  │
│  │  ├─ Middleware:        (CORS, Auth, Logging)            │  │
│  │  └─ Error Handlers     (Global exception mgmt)          │  │
│  │                                                          │  │
│  │  Service Layer                                           │  │
│  │  ├─ PricingService    (Search, Update, Delete logic)   │  │
│  │  ├─ ImportService     (CSV parsing, validation)         │  │
│  │  └─ StatsService      (Analytics, reporting)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ↕         (SQL)                         │
├─────────────────────────────────────────────────────────────────┤
│                  DATA ACCESS & PERSISTENCE                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  SQLAlchemy ORM                                          │  │
│  │  ├─ Store Model        (Retail locations)               │  │
│  │  ├─ Product Model      (SKUs/Articles)                  │  │
│  │  └─ PricingRecord Model (Price history)                 │  │
│  │                                                          │  │
│  │  Database Layer                                          │  │
│  │  ├─ PostgreSQL 15     (Primary OLTP store)              │  │
│  │  ├─ Redis             (Session, Cache, Message Queue)   │  │
│  │  └─ File System       (CSV uploads staging)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         ↕                                       │
├─────────────────────────────────────────────────────────────────┤
│             ASYNCHRONOUS PROCESSING LAYER                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Celery Task Queue                                       │  │
│  │  ├─ process_csv_upload()  (Main import job)             │  │
│  │  │  ├─ Parse CSV                                        │  │
│  │  │  ├─ Validate Data                                    │  │
│  │  │  ├─ Check Duplicates                                 │  │
│  │  │  └─ Import Records                                   │  │
│  │  │                                                       │  │
│  │  ├─ Celery Beat       (Scheduled jobs)                  │  │
│  │  │  ├─ Cleanup old files (daily)                        │  │
│  │  │  ├─ Generate reports (weekly)                        │  │
│  │  │  └─ Sync analytics (hourly)                          │  │
│  │  │                                                       │  │
│  │  └─ Result Backend    (Redis for status tracking)       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│              INFRASTRUCTURE & DEPLOYMENT                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Docker & Docker Compose                                │  │
│  │  ├─ Container Images      (REG, Alpine base images)     │  │
│  │  ├─ Volumes              (Persistent storage)           │  │
│  │  ├─ Networks             (Internal communication)       │  │
│  │  ├─ Health Checks        (Service monitoring)           │  │
│  │  └─ Environment Config   (12-factor app principles)     │  │
│  │                                                          │  │
│  │  Logs & Monitoring                                       │  │
│  │  ├─ Application Logs    (Flask, Celery)                │  │
│  │  ├─ Database Logs       (PostgreSQL)                    │  │
│  │  └─ Container Logs      (Docker logs)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Database Schema

```
┌─────────────────────────────────────────────────────────────┐
│              DATABASE: priceledger (PostgreSQL 15)          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │  stores          │        │   products       │          │
│  ├──────────────────┤        ├──────────────────┤          │
│  │ id (PK)          │        │ id (PK)          │          │
│  │ store_id (UNIQUE)│        │ sku (UNIQUE)     │          │
│  │ store_name       │        │ product_name     │          │
│  │ country          │        │ category         │          │
│  │ region           │        │ is_active        │          │
│  │ city             │        │ created_at       │          │
│  │ is_active        │        │ updated_at       │          │
│  │ created_at       │        └──────────────────┘          │
│  │ updated_at       │               ▲                      │
│  └────────┬─────────┘               │ (FK)                 │
│           │ (FK)                    │                      │
│           │                         │                      │
│           └──────────┬──────────────┘                      │
│                      │                                    │
│                      ↓                                    │
│         ┌─────────────────────────┐                       │
│         │  pricing_records        │                       │
│         ├─────────────────────────┤                       │
│         │ id (PK)                 │                       │
│         │ store_id (FK) ◆ Index   │                       │
│         │ product_id (FK) ◆ Index │                       │
│         │ price                   │                       │
│         │ currency                │                       │
│         │ price_date ◆ Index      │                       │
│         │ source_file             │                       │
│         │ updated_by              │                       │
│         │ created_at ◆ Index      │                       │
│         │ updated_at              │                       │
│         │                         │                       │
│         │ CONSTRAINTS:            │                       │
│         │ • UNIQUE(store_id,      │                       │
│         │    product_id,price_date)│                      │
│         │ • Index on (price_date  │                       │
│         │    DESC, store_id,      │                       │
│         │    product_id)          │                       │
│         └─────────────────────────┘                       │
│                                                              │
│  Key Indexes:                                               │
│  • idx_store_id, idx_country, idx_is_active (stores)      │
│  • idx_sku, idx_product_is_active (products)              │
│  • idx_pricing_store_id, idx_pricing_product_id           │
│  • idx_pricing_date, idx_store_product_date (composite)   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCKER COMPOSE STACK                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Network: priceledger-network (Internal)                    │
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │  priceledger-db  │  │  priceledger-    │  │  price     │ │
│  │  (PostgreSQL 15) │  │  redis           │  │  ledger-   │ │
│  │                  │  │  (Redis 7)       │  │  backend   │ │
│  │  Port: 5432      │  │                  │  │  (Flask)   │ │
│  │  User: price...  │  │  Port: 6379      │  │            │ │
│  │                  │  │  Protocol: TCP   │  │  Port:5000 │ │
│  │  Volume:         │  │                  │  │            │ │
│  │  postgres_data   │  │  Volume:         │  │ Depends on:│ │
│  │                  │  │  redis_data      │  │ • db       │ │
│  │  Healthcheck:    │  │                  │  │ • redis    │ │
│  │  pg_isready      │  │  Healthcheck:    │  │            │ │
│  │                  │  │  redis-cli ping  │  │ Volume:    │ │
│  └──────────────────┘  └──────────────────┘  │ ./backend  │ │
│         ▲                      ▲              │ ./uploads  │ │
│         │                      │              └────────────┘ │
│         └──────────────────────┴────────────────────┘         │
│                                                               │
│  ┌────────────────────┐  ┌────────────────────┐             │
│  │  priceledger-      │  │  priceledger-      │             │
│  │  celery-worker     │  │  celery-beat       │             │
│  │  (Celery)          │  │  (Celery Beat)     │             │
│  │                    │  │                    │             │
│  │  Command:          │  │  Command:          │             │
│  │  celery -A app.cel │  │  celery -A app.cel │             │
│  │  worker --loglevel │  │  beat --loglevel   │             │
│  │                    │  │                    │             │
│  │  Depends on:       │  │  Depends on:       │             │
│  │  • db              │  │  • db              │             │
│  │  • redis           │  │  • redis           │             │
│  └────────────────────┘  └────────────────────┘             │
│         ▲                         ▲                          │
│         └─────────────────────────┘                          │
│                 (Connected via Redis)                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Legend:
→ Synchronous Communication (HTTP/REST)
◆ Asynchronous Communication (Message Queue)
```

### 4. Request/Response Flow

```
CLIENT REQUEST → BACKEND PROCESSING → DATABASE → RESPONSE

1. CSV UPLOAD FLOW:
   POST /api/pricing/upload_csv
   ├─ Receive FormData with file
   ├─ Validate file (format, size)
   ├─ Save file to disk
   ├─ Queue Celery task: process_csv_upload()
   └─ Return 202 ACCEPTED + task_id
      └─ Response: { "task_id": "abc-123", "status": "queued" }

   CLIENT POLLS STATUS:
   GET /api/pricing/upload_status/{task_id}
   ├─ Check Celery task status
   └─ Return Status (pending → processing → success/failure)
      └─ Response: {
           "status": "processing",
           "percent": 45,
           "current": 450,
           "total": 1000,
           "message": "Importing records..."
        }

2. SEARCH FLOW:
   GET /api/pricing/search?store_id=S001&sku=SKU-123
   ├─ Parse filters from query params
   ├─ Build SQLAlchemy query
   ├─ Execute with eager loading + indexing
   ├─ Format response
   └─ Return 200 OK + results
      └─ Response: {
           "items": [...],
           "total": 1234,
           "pages": 25,
           "current_page": 1
        }

3. EDIT PRICING FLOW:
   PUT /api/pricing/records/{id}
   ├─ Retrieve record from DB
   ├─ Apply changes
   ├─ Validate constraints
   ├─ Persist to DB
   └─ Return 200 OK + updated record
```

---

## Design Decisions

### 1. **Asynchronous CSV Processing (Celery + Redis)**

**Decision:** Use Celery with Redis as message broker for CSV uploads

**Rationale:**

- **Scale**: Files up to 50MB, processing can take 5-30 minutes
- **UX**: Return response immediately (202 Accepted) instead of blocking
- **Reliability**: Task retries, dead-letter queues, error handling
- **Monitoring**: Track progress in real-time via polling

**Trade-offs:**
| Pros | Cons |
|------|------|
| Non-blocking uploads | Added complexity (message broker, workers) |
| Real-time progress tracking | Operational overhead (uptime, monitoring) |
| Error recovery & retries | Harder to debug distributed issues |
| Horizontal scaling (multiple workers) | Eventual consistency |

**Alternative Considered:**

- Synchronous upload: Simpler but poor UX for large files, timeout risks

---

### 2. **PostgreSQL with Composite Indexes**

**Decision:** PostgreSQL 15 Alpine with strategic indexing

**Rationale:**

- **ACID Guarantees**: Data integrity critical for financial pricing
- **Scalability**: Handles millions of records efficiently
- **Query Performance**: Composite indexes on (store_id, product_id, price_date)
- **Unique Constraints**: Prevents duplicate entries at DB level

**Indexes Created:**

```sql
-- Prevents duplicate pricing records
UNIQUE (store_id, product_id, price_date)

-- Speed up common search patterns
INDEX ON (price_date DESC, store_id, product_id)
INDEX ON (store_id)
INDEX ON (product_id)
```

**Trade-offs:**

- Slower writes (index maintenance) → acceptable for read-heavy workload (80/20)
- Storage overhead → acceptable for historical pricing data

---

### 3. **Duplicate Detection Before Import**

**Decision:** Two-pass validation (check then import)

**Rationale:**

- **Data Integrity**: Prevent partial imports with corrupt data
- **Clear Feedback**: Line numbers pinpoint exact duplicates
- **Atomic Operations**: All-or-nothing ensures consistency

**Implementation:**

```
Pass 1: Validate
  └─ Check for duplicates within file
  └─ Check for existing records in database
  └─ If any found → Return error with details (Line X, Y, Z)

Pass 2: Import (only if Pass 1 succeeds)
  └─ Insert all records
  └─ Commit transaction
```

**Trade-off:**

- Extra validation overhead → worth it for data quality

---

### 4. **REST API with Flask-RESTX**

**Decision:** Flask + Flask-RESTX (Swagger/OpenAPI)

**Rationale:**

- **Documentation**: Auto-generated Swagger UI at `/api/docs`
- **Validation**: Decorator-based request/response validation
- **Lightweight**: Perfect for microservices, quick iteration
- **Extensible**: Namespaces for organized endpoints

**API Design:**

```
GET    /api/pricing/search              → Search records
POST   /api/pricing/upload_csv          → Upload file
GET    /api/pricing/upload_status/{id}  → Check status
PUT    /api/pricing/records/{id}        → Update price
DELETE /api/pricing/records/{id}        → Delete record
GET    /api/stats/summary               → Dashboard stats
```

**Alternative Considered:** Django REST Framework (heavier, overkill for this use case)

---

### 5. **Angular SPA with RxJS**

**Decision:** Angular 17 with Reactive Programming patterns

**Rationale:**

- **Reactive Forms**: Strong typing (FormGroup, FormControl)
- **RxJS Subjects**: Manage component lifecycle properly
- **Type Safety**: Full TypeScript support
- **Component Architecture**: Modular, testable, reusable

**Component Structure:**

```
├─ UploadComponent
│  ├─ File selection (hidden input)
│  ├─ Real-time progress polling
│  └─ Alert notifications
│
├─ SearchComponent
│  ├─ FormGroup with filters
│  ├─ Pagination handling
│  └─ Results display
│
└─ PricingService
   ├─ HTTP calls (uploadCSV, search)
   └─ State management
```

---

### 6. **Docker Compose for Local Development**

**Decision:** Single `docker-compose.yml` with all services

**Rationale:**

- **Reproducibility**: "Works on my laptop" → works everywhere
- **Consistency**: Dev = Staging = Prod (with env vars)
- **Simplicity**: Single command: `docker-compose up -d`
- **Dependency Management**: Service ordering, health checks

**Services:**

1. PostgreSQL (database)
2. Redis (cache + message broker)
3. Flask Backend (REST API)
4. Celery Worker (async processing)
5. Celery Beat (scheduled tasks)

---

### 7. **Stateless Backend Design**

**Decision:** Backend services have no local state (scalability)

**Rationale:**

- **Horizontal Scaling**: Each backend instance identical
- **Load Balancing**: Route requests anywhere without affinity
- **Container Orchestration**: Easy to scale up/down

**Implementation:**

- Session store: Redis (not Flask session)
- File uploads: Persistent volume shared across instances
- Task queue: Redis (not in-memory)

**Example:** Running 3 replicas with load balancer

```
Request 1 → Backend-1 → Redis
Request 2 → Backend-2 → Redis  (same session/queue)
Request 3 → Backend-3 → Redis
```

---

## Non-Functional Requirements

### 1. **Performance**

#### Requirement: Response time ≤ 200ms for 95th percentile

| Operation             | Target                  | Implementation                           |
| --------------------- | ----------------------- | ---------------------------------------- |
| Search (100K records) | ≤ 100ms                 | Composite indexes, pagination (limit 50) |
| CSV upload (1MB)      | 202 response in ≤ 500ms | Queue immediately, process async         |
| Status check          | ≤ 50ms                  | Redis lookup, no DB query                |

**How Design Addresses:**

- **Eager Loading**: `selectinload()` in SQLAlchemy prevents N+1 queries
- **Pagination**: Always limit 50 records per query
- **Caching**: Redis for session, task status
- **Async Processing**: Heavy lifting off request thread

---

### 2. **Scalability**

#### Requirement: Support 3000+ stores, 100K+ pricing records

**Vertical Scaling (Single Instance):**

- PostgreSQL: 100K records manageable in RAM
- Flask: WSGI server handles ~500 req/sec
- Celery: 1 worker ~100 files/hour

**Horizontal Scaling (Multiple Instances):**

```yaml
# docker-compose override for scaling
services:
  backend:
    deploy:
      replicas: 3 # 3 API instances
  celery_worker:
    deploy:
      replicas: 5 # 5 processing workers
```

**Load Balancing Pattern:**

```
Nginx/HAProxy
    ├─ Backend-1
    ├─ Backend-2
    └─ Backend-3

All share same:
    ├─ PostgreSQL (read replicas optional)
    ├─ Redis (cluster mode for HA)
    └─ File storage (shared volume or S3)
```

---

### 3. **Reliability & Fault Tolerance**

#### Requirement: 99.5% uptime SLA

**Health Checks:**

```yaml
db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U user -d db"]
    interval: 10s
    retries: 5

redis:
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    retries: 5

backend:
  depends_on:
    db:
      condition: service_healthy
    redis:
      condition: service_healthy
```

**Resilience Patterns:**

- **Retry Logic**: Celery tasks retry up to 3x on transient failures
- **Circuit Breaker**: Fail fast if database connection fails
- **Graceful Degradation**: Search returns partial results if cache misses
- **Dead Letter Queue**: Failed tasks stored for investigation

---

### 4. **Security**

#### Requirement: Protect sensitive pricing data

**Implementation:**

| Security Aspect     | Mechanism                                 |
| ------------------- | ----------------------------------------- |
| **Data in Transit** | POSTGRES_PASSWORD env var, not in code    |
| **File Uploads**    | Validate format (CSV only), max size 50MB |
| **SQL Injection**   | SQLAlchemy ORM parameterized queries      |
| **XSS Protection**  | Angular template escaping                 |
| **CORS**            | Flask-CORS headers configured             |
| **Logging**         | Exclude sensitive data from logs          |

**Future Enhancements:**

- JWT authentication for API
- API rate limiting (Flask-Limiter)
- Encryption at rest (pgcrypto for PG)
- TLS/SSL certificates (production)
- Role-based access control (RBAC)

---

### 5. **Maintainability**

#### Requirement: Easy to understand, modify, extend

**Code Organization:**

```
backend/
├─ app/
│  ├─ models/       (SQLAlchemy models - single source of truth)
│  ├─ routes/       (API endpoints - thin controllers)
│  ├─ services/     (Business logic - testable)
│  ├─ utils/        (Helpers - CSV parsing, validation)
│  └─ celery_tasks/ (Async jobs)
├─ tests/           (Unit & integration tests)
└─ config.py        (Centralized configuration)
```

**Logging:**

```python
logger.info(f"Processing file: {filename}")
logger.error(f"Duplicate found at line {line_no}", extra={'context': data})
```

**Error Handling:**

```python
try:
    # operation
except ValidationError as e:
    return {"error": str(e)}, 400
except DatabaseError as e:
    logger.error(f"DB Error: {e}")
    return {"error": "Database error"}, 500
```

---

### 6. **Data Consistency**

#### Requirement: No lost or corrupted pricing data

**ACID Compliance:**

- **Atomicity**: Entire CSV import commits or rolls back (no partial imports)
- **Consistency**: Foreign key constraints, unique violations caught
- **Isolation**: Concurrent uploads don't interfere (transaction isolation level)
- **Durability**: PostgreSQL fsync ensures data on disk

**Implementation:**

```python
# Atomic import
try:
    db.session.add_all(records)
    db.session.commit()  # All or nothing
except IntegrityError:
    db.session.rollback()  # Revert all changes
    return {"error": "Duplicate record"}, 409
```

---

## Assumptions

### 1. **Operational Assumptions**

| Assumption                       | Justification                          |
| -------------------------------- | -------------------------------------- |
| **Docker installed locally**     | Required for development environment   |
| **Network connectivity**         | API calls between frontend & backend   |
| **Persistent storage available** | Docker volumes for PostgreSQL, uploads |
| **200MB free disk space**        | Database + sample data + logs          |

### 2. **Data Assumptions**

| Assumption                                    | Justification                                      |
| --------------------------------------------- | -------------------------------------------------- |
| **CSV always has headers**                    | Line 1: Store ID, SKU, Product Name, Price, Date   |
| **Prices in valid format**                    | Numeric, 2 decimal places (e.g., 19.99)            |
| **Dates in YYYY-MM-DD**                       | ISO 8601 format, no time component                 |
| **Store IDs unique**                          | Each store has exactly one ID (S0001, S0002, etc.) |
| **Duplicate detection by (Store, SKU, Date)** | Natural key for pricing                            |

### 3. **Technical Assumptions**

| Assumption              | Justification                             |
| ----------------------- | ----------------------------------------- |
| **Python 3.9+**         | Type hints, walrus operator               |
| **Node.js 18+**         | ES2020 features, npm packages             |
| **PostgreSQL 12+**      | JSON support, generated columns           |
| **Modern browser**      | ES2020, Fetch API, LocalStorage           |
| **Kubernetes optional** | Works with Docker Compose for single-node |

### 4. **Business Assumptions**

| Assumption                      | Justification                             |
| ------------------------------- | ----------------------------------------- |
| **3000-10000 stores**           | Pricing coordination at scale             |
| **Daily/weekly uploads**        | Batch processing, not real-time streaming |
| **Multi-region support**        | Currency (USD, EUR, GBP), locale aware    |
| **Pricing data is proprietary** | Implement access control (future)         |
| **Historical tracking needed**  | Keep all records, no data deletion policy |

---

## Implementation Sources

### 1. **Framework & Library Decisions**

#### Frontend Stack

```
Angular 17
├─ Source: https://angular.io
├─ Why: Type-safe SPA, RxJS reactive patterns
├─ Modules Used:
│  ├─ ReactiveFormsModule (FormGroup)
│  ├─ RouterModule (Navigation)
│  ├─ CommonModule (ngIf, ngFor, etc)
│  └─ HttpClientModule (REST calls)
│
Services
├─ PricingService: Encapsulate API calls
├─ StatsService: Dashboard data
└─ AppState: Shared state management

Components
├─ UploadComponent: CSV ingestion
├─ SearchComponent: Advanced filtering
├─ DashboardComponent: Analytics
└─ Shared: Reusable UI components
```

#### Backend Stack

```
Flask 2.3.3
├─ Source: https://flask.palletsprojects.com
├─ Why: Lightweight, perfect for REST APIs
├─ Extensions:
│  ├─ Flask-SQLAlchemy (ORM)
│  ├─ Flask-RESTX (Swagger docs)
│  ├─ Flask-CORS (Cross-origin)
│  └─ Flask-Migrate (Database migrations)
│
SQLAlchemy 2.0
├─ Source: https://www.sqlalchemy.org
├─ Features: Parameterized queries (SQL injection protection)
├─ ORM: Model-based database queries
└─ Performance: Eager loading, query optimization

Celery 5.3
├─ Source: https://docs.celeryproject.io
├─ Why: Distributed task queue
├─ Features:
│  ├─ Task retries and error handling
│  ├─ Scheduled tasks (Celery Beat)
│  └─ Progress tracking
│
├─ Redis Backend: In-memory result store
└─ Message Broker: Task distribution
```

#### Database

```
PostgreSQL 15 Alpine
├─ Source: https://www.postgresql.org
├─ Why: ACID guarantees, JSON support, scalability
├─ Features Used:
│  ├─ Foreign keys (referential integrity)
│  ├─ Unique constraints
│  ├─ Composite indexes
│  └─ Transaction isolation levels
│
Indexing Strategy
├─ B-tree indexes (default, for range queries)
├─ Partial indexes (on is_active=TRUE)
└─ Composite index (store_id, product_id, price_date)
```

### 2. **Design Patterns Used**

| Pattern                  | Location             | Purpose                             |
| ------------------------ | -------------------- | ----------------------------------- |
| **Service Layer**        | `services/*.py`      | Separate business logic from routes |
| **Repository Pattern**   | SQLAlchemy models    | Abstract data access                |
| **Dependency Injection** | Constructor params   | Loose coupling                      |
| **Factory Pattern**      | `create_app()`       | Flask app initialization            |
| **Singleton**            | Database, Redis conn | Shared resources                    |
| **Observer**             | RxJS Subjects        | Reactive updates                    |
| **Strategy**             | Multiple validators  | Pluggable validation rules          |

### 3. **Deployment & Infrastructure Sources**

#### Docker

```
Dockerfile (Multi-stage build)
├─ Base image: python:3.11-alpine
├─ Why: Small (50MB vs 500MB), secure
├─ Build stages:
│  ├─ Layer 1: Install dependencies
│  ├─ Layer 2: Copy app code
│  └─ Layer 3: Configure health checks
│
Benefits:
├─ Reproducible builds
├─ Smaller image size (alpine)
└─ Easy distribution via registry

docker-compose.yml
├─ Service orchestration
├─ Environment configuration
├─ Volume management
└─ Network setup
```

**Sources:**

- Docker documentation: https://docs.docker.com
- Best practices: https://docs.docker.com/develop/dev-best-practices/

#### Environment Configuration

```
12-Factor App Principles
├─ I. Codebase: Single git repo
├─ III. Config: Via environment variables
├─ IV. Backing services: Treat as attached resources
├─ XI. Logs: Write to stdout (Docker collects)
└─ XII. Admin tasks: Manage via scripts

Example:
DATABASE_URL=postgresql://user:pass@host:5432/db
CELERY_BROKER_URL=redis://host:6379/0
FLASK_ENV=production
```

---

### 4. **Code Quality & Testing**

#### Testing Strategy

```
Unit Tests
├─ Services: Isolated business logic tests
├─ Models: ORM behavior verification
└─ Utils: CSV parsing, validation

Integration Tests
├─ API endpoints: Full request/response cycle
├─ Database: With real PostgreSQL
└─ Celery: Task execution and state

Example:
def test_import_detects_duplicates():
    df = pd.DataFrame([
        {'store id': 'S1', 'sku': 'SKU1', ...},
        {'store id': 'S1', 'sku': 'SKU1', ...},  # Duplicate
    ])
    count, errors = ImportService.import_pricing_records(df, 'test.csv')
    assert count == 0
    assert len(errors) > 0
```

#### Code Organization Lessons

```
Problem: Monolithic structure → Hard to test
Solution: Service layer + dependency injection

Before:
app.py (500 lines)
├─ Routes
├─ DB queries
├─ Business logic
└─ Error handling (all mixed)

After:
routes/pricing_api.py (100 lines, thin)
├─ Endpoint definitions
└─ Call services

services/pricing_service.py (300 lines, focused)
├─ Search logic
├─ Import logic
└─ Update logic

models/__init__.py (150 lines)
├─ SQLAlchemy models
└─ Database schema
```

---

### 5. **References & Further Reading**

#### Architecture & Design

- **Microservices**: https://martinfowler.com/articles/microservices.html
- **REST API Design**: https://restfulapi.net
- **Database Indexing**: https://use-the-index-luke.com
- **Async Patterns**: https://www.rabbitmq.com/getstarted.html

#### Technology Docs

- Flask: https://flask.palletsprojects.com/
- Angular: https://angular.io/docs
- PostgreSQL: https://www.postgresql.org/docs/
- Celery: https://docs.celeryproject.io/
- Redis: https://redis.io/documentation
- Docker: https://docs.docker.com

#### Security Best Practices

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **SQL Injection Prevention**: Use ORMs (SQLAlchemy)
- **XSS Prevention**: Template sanitization (Angular)
- **CORS**: https://enable-cors.org/

#### Performance Optimization

- **Query Optimization**: https://use-the-index-luke.com
- **Caching**: Redis https://redis.io
- **Async**: Celery documentation
- **DB Indexing**: PostgreSQL EXPLAIN ANALYZE

---

## Conclusion

The Price Ledger system demonstrates **scalable**, **maintainable**, and **reliable** architecture suitable for enterprise retail environments. Key highlights:

✅ **Asynchronous Processing**: Handle 50MB files without blocking  
✅ **Data Integrity**: ACID compliance, duplicate detection  
✅ **Scalability**: Horizontal scaling with stateless design  
✅ **Developer Experience**: Clean separation of concerns, tests  
✅ **Operational Excellence**: Docker, health checks, monitoring

### Next Steps (Future Enhancements)

1. **Authentication**: JWT token-based API security
2. **Kubernetes**: Move from Docker Compose to EKS/AKS
3. **Analytics**: Real-time dashboard with Grafana
4. **Data Warehouse**: Sync with Snowflake/BigQuery
5. **Mobile App**: React Native iOS/Android client
6. **Notifications**: Email alerts for import failures

---

**Document Version:** 1.0  
**Last Updated:** March 2026  
**Author:** Price Ledger Team
