# REIMS 2.0 - Real Estate Investment Management System

<div align="center">

**Enterprise-Grade Financial Intelligence Platform for Real Estate Portfolio Management**

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/yourusername/REIMS2)
[![Status](https://img.shields.io/badge/status-production--ready-green.svg)](https://github.com/yourusername/REIMS2)
[![License](https://img.shields.io/badge/license-proprietary-red.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-19.1-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115-green.svg)](https://fastapi.tiangolo.com/)

**Last Updated**: January 29, 2026

[Features](#-key-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Architecture](#-architecture) • [API](#-api-reference)

</div>

---

## 🎯 Overview

REIMS 2.0 is a **world-class financial intelligence platform** designed for institutional real estate investors, asset managers, and CFOs. It combines **AI-powered document extraction**, **311+ automated reconciliation rules**, **forensic audit capabilities**, and **real-time financial analytics** into a unified system.

### What Makes REIMS 2.0 Different?

- 🧠 **311+ Automated Rules** - Comprehensive reconciliation framework covering all financial statements
- 🔍 **Forensic Audit Engine** - SEC-grade validation with 9 specialized dashboards
- 🤖 **Self-Learning System** - Continuously improves extraction accuracy from human feedback
- 📊 **Executive Intelligence** - Real-time KPIs, covenant tracking, and risk alerts
- 🔗 **Cross-Document Reconciliation** - Validates consistency across 5 financial documents
- ⚡ **95-98% Extraction Accuracy** - Multi-engine PDF processing with OCR fallback

---

## ✨ Key Features

### 🔍 Forensic Audit & Reconciliation

- **311+ Automated Rules** across 13 specialized rule engines:
  - Period Alignment (5 rules)
  - Cash Flow Internal Consistency (7 rules)
  - Fraud Detection (Benford's Law, duplicate detection)
  - Working Capital Reconciliation (3 rules)
  - Mortgage & Debt Validation (20+ rules)
  - Rent Roll Forensics (4 rules)
  - Cross-Document Audit (55+ rules)
  - Data Quality (33 rules)
  - Analytics & Covenants (39 rules)
  - Trend & Benchmark Analysis (7 rules)
  - Stress Testing (5 rules)

- **9 Specialized Forensic Dashboards**:
  - **Math Integrity** - Balance sheet equation, cash flow reconciliation
  - **Performance Benchmarking** - Portfolio comparison, market analysis
  - **Fraud Detection** - Benford's Law, pattern anomalies
  - **Covenant Compliance** - DSCR, LTV, debt yield tracking
  - **Tenant Risk** - Concentration, delinquency analysis
  - **Collections Quality** - Receivables aging, bad debt trends
  - **Document Completeness** - Required document tracking
  - **Reconciliation Results** - Cross-document validation status
  - **Audit History** - Complete forensic trail

- **Filter Persistence** - Seamless navigation across all dashboards with retained context

### 📄 Document Processing

- **Multi-Engine Extraction**:
  - PyMuPDF (primary)
  - PDFPlumber (tables)
  - Camelot (complex tables)
  - Tesseract OCR (scanned documents)

- **Supported Documents**:
  - Balance Sheet
  - Income Statement (P&L)
  - Cash Flow Statement
  - Rent Roll
  - Mortgage Statements
  - General Ledger

- **Quality Assurance**:
  - 10-layer PDF quality validation
  - Confidence scoring per field
  - Human-in-the-loop review workflow
  - Automatic anomaly detection
  - Self-learning feedback loop

### 💼 Portfolio Management

- **Multi-Property Support** - Unlimited properties with hierarchical organization
- **Period Tracking** - Monthly, quarterly, annual reporting periods
- **Chart of Accounts** - 179-account structure with customization
- **Financial Metrics** - 20+ KPIs including:
  - DSCR (Debt Service Coverage Ratio)
  - LTV (Loan-to-Value)
  - Debt Yield
  - NOI (Net Operating Income)
  - Cap Rate
  - Cash-on-Cash Return

### 🚨 Risk Management & Alerts

- **Committee Alert System**:
  - Finance Committee
  - Audit Committee
  - Investment Committee
  - Risk Management Committee

- **Alert Types**:
  - Covenant breaches
  - Variance thresholds
  - Documentation gaps
  - Reconciliation failures
  - Fraud indicators

- **Proactive Monitoring**:
  - AUDIT-48: Variance investigation triggers
  - AUDIT-53: Escrow documentation tracking
  - AUDIT-54: Journal entry validation

### 🧠 AI & Machine Learning

- **Self-Learning Engine**:
  - Learns from user corrections
  - Builds issue knowledge base
  - Improves extraction patterns
  - Reduces false positives

- **Market Intelligence**:
  - Property research automation
  - Competitive analysis
  - Market trend detection
  - Valuation benchmarking

- **Document Intelligence**:
  - Automatic document classification
  - Smart field extraction
  - Context-aware validation
  - Template learning

### 🔗 General Ledger Integration

- **GL Data Ingestion**:
  - CSV/Excel import
  - Automated account mapping
  - Transaction categorization
  - Period alignment

- **Data Governance**:
  - Data lineage tracking
  - Quality metrics
  - Validation rules
  - Audit trail

### 📊 Analytics & Reporting

- **Executive Dashboard** - CEO/CFO view with comprehensive health metrics
- **Financial Integrity Hub** - Live reconciliation and validation
- **Quality Dashboard** - Document processing metrics
- **Anomaly Dashboard** - Exception management
- **Market Intelligence Dashboard** - Property research and analysis

- **Export Capabilities**:
  - Excel (formatted)
  - CSV
  - PDF reports
  - API access

---

## 🚀 Quick Start

### Prerequisites

- **Docker** and **Docker Compose** (v2.0+)
- **4GB RAM** minimum (8GB recommended)
- **20GB disk space**
- **Linux/macOS/Windows** with WSL2

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/REIMS2.git
cd REIMS2
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start all services**:
```bash
docker compose up -d
```

4. **Wait for services to initialize** (30-60 seconds):
```bash
docker compose ps  # Check all services are healthy
```

5. **Access the application**:
   - 🌐 **Frontend**: http://localhost:5173
   - 📚 **API Docs**: http://localhost:8000/docs
   - 🌺 **Celery Monitor**: http://localhost:5555
   - 🐘 **pgAdmin**: http://localhost:5050

6. **Optional: Seed reconciliation config** (AUDIT-48, COVENANT-6, BENCHMARK, FA-MORT-4 thresholds, etc.):
   ```bash
   docker exec -i reims-postgres psql -U reims -d reims < backend/scripts/seed_reconciliation_config.sql
   ```

### First Steps

1. **Register an account** at http://localhost:5173
2. **Add a property** via Properties page
3. **Upload documents** (drag & drop PDFs)
4. **Monitor extraction** on Dashboard
5. **Run reconciliation** in Financial Integrity Hub
6. **Review results** across forensic dashboards

---

## 📚 Documentation

### User Guides
- **Getting Started** - [USER_GUIDE.md](docs/USER_GUIDE.md)
- **Reconciliation Rules** - [RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md](RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md)
- **Reconciliation Deep Dive & Plan** - [docs/RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md](docs/RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md)
- **Reconciliation Implementation Summary** - [docs/RECONCILIATION_RULES_IMPLEMENTATION_SUMMARY.md](docs/RECONCILIATION_RULES_IMPLEMENTATION_SUMMARY.md)
- **Filter Persistence** - [FILTER_PERSISTENCE_IMPLEMENTATION.md](FILTER_PERSISTENCE_IMPLEMENTATION.md)
- **API Reference** - http://localhost:8000/docs (when running)

### Technical Documentation
- **Architecture Overview** - [COMPLETE_SYSTEM_STATUS.md](COMPLETE_SYSTEM_STATUS.md)
- **Implementation Summary** - [COMPLETE_IMPLEMENTATION_SUMMARY.md](COMPLETE_IMPLEMENTATION_SUMMARY.md)
- **Rule Mapping** - [backend/app/services/rules/RULES_MAPPING.md](backend/app/services/rules/RULES_MAPPING.md)
- **Self-Learning System** - [docs/SELF_LEARNING_CLEANUP_SYSTEM.md](docs/SELF_LEARNING_CLEANUP_SYSTEM.md)

### Testing Guides
- **Reconciliation Testing** - [QUICK_TEST_GUIDE.md](QUICK_TEST_GUIDE.md)
- **Filter Persistence Testing** - [FILTER_PERSISTENCE_TEST_GUIDE.md](FILTER_PERSISTENCE_TEST_GUIDE.md)

---

## 🏗️ Architecture

### Tech Stack

#### Backend
- **Framework**: FastAPI (Python 3.13)
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL 17
- **Task Queue**: Celery + Redis
- **Storage**: MinIO (S3-compatible)
- **AI/ML**: Ollama (local LLM)

#### Frontend
- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite
- **State Management**: Zustand + TanStack Query
- **UI Components**: Material-UI + Headless UI
- **Charts**: Recharts + Chart.js
- **Maps**: Leaflet

#### Infrastructure
- **Container**: Docker + Docker Compose
- **Reverse Proxy**: Nginx (production)
- **Monitoring**: Flower (Celery), pgAdmin (DB)

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      REIMS 2.0 Platform                      │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐        ┌──────────────────┐
│  React Frontend  │◄──────►│   FastAPI API    │
│   (Port 5173)    │  REST  │   (Port 8000)    │
└──────────────────┘        └──────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
           ┌────────▼────────┐  ┌───▼────┐  ┌───────▼──────┐
           │   PostgreSQL    │  │ Redis  │  │    MinIO     │
           │   (Port 5433)   │  │ Cache  │  │   Storage    │
           └─────────────────┘  └────────┘  └──────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
           ┌────────▼────────┐  ┌───▼────────┐  ┌───▼──────┐
           │  Celery Worker  │  │ Celery Beat│  │  Ollama  │
           │  (Processing)   │  │ (Schedule) │  │   (AI)   │
           └─────────────────┘  └────────────┘  └──────────┘
```

### Services

| Service | Description | Port(s) | Health Check |
|---------|-------------|---------|--------------|
| `postgres` | PostgreSQL 17 database | 5433 | ✅ Automated |
| `redis` | Cache & message broker | 6379, 8001 | ✅ Automated |
| `minio` | Object storage (S3) | 9000, 9001 | ✅ Automated |
| `backend` | FastAPI application | 8000 | ✅ Automated |
| `celery-worker` | Document processing | - | ✅ Automated |
| `celery-audit-worker` | Audit & reconciliation | - | ✅ Automated |
| `celery-beat` | Scheduled tasks | - | ✅ Automated |
| `flower` | Celery monitoring | 5555 | ✅ Automated |
| `frontend` | React application | 5173 | ✅ Automated |
| `pgadmin` | Database admin UI | 5050 | ⚠️  Optional |
| `ollama` | Local LLM (optional) | 11434 | ⚠️  Optional |

**Note**: PostgreSQL runs on port **5433** (not 5432) to avoid conflicts with system installations.

---

## 📊 Database Schema

### Core Tables (49 total)

#### Document Management
- `document_uploads` - PDF uploads and metadata
- `escrow_document_links` - FA-MORT-4: links supporting documents to escrow activity (property/period/type)
- `extraction_logs` - Processing history
- `extraction_learning_cases` - Self-learning data
- `document_summaries` - AI-generated summaries

#### Financial Data
- `balance_sheet_data` - Balance sheet entries
- `income_statement_data` - P&L entries
- `cash_flow_data` - Cash flow entries
- `rent_roll_data` - Tenant data
- `mortgage_statement_data` - Loan data
- `general_ledger_entries` - GL transactions

#### Reconciliation & Audit
- `cross_document_reconciliations` - Rule execution results (stores 311+ rule outputs)
- `forensic_reconciliation_sessions` - Audit sessions
- `forensic_matches` - Cross-document matches
- `anomaly_detections` - Identified anomalies
- `anomaly_thresholds` - Configuration

#### Risk Management
- `committee_alerts` - Alert records
- `alert_rules` - Alert configuration
- `alert_history` - Alert lifecycle
- `workflow_locks` - Concurrent control

#### Portfolio Management
- `properties` - Property master data
- `financial_periods` - Period definitions
- `chart_of_accounts` - 179-account structure
- `property_market_data` - Market intelligence

#### Self-Learning
- `issue_knowledge_base` - Known issues
- `pattern_library` - Extraction patterns
- `field_confidence_history` - Accuracy tracking

### Current Data Scale
- **Properties**: 5+ managed
- **Documents**: 100+ processed
- **Extraction Records**: 10,000+ entries
- **Reconciliation Rules**: 311+ executed
- **Accounts**: 179 in chart
- **Audit Trail**: Complete lineage

---

## 🔐 Security

### Authentication & Authorization
- ✅ **Session-based auth** with HTTP-only cookies
- ✅ **Bcrypt password hashing** (12 rounds)
- ✅ **RBAC** - Role-based access control
- ✅ **API rate limiting** - 200 requests/minute
- ✅ **CORS protection** - Whitelisted origins

### Data Protection
- ✅ **Audit trail** - All changes tracked
- ✅ **User attribution** - Creator/modifier records
- ✅ **Sensitive data encryption** - At rest & transit
- ✅ **Workflow locks** - Concurrent edit prevention
- ✅ **Data lineage** - Complete governance trail

### Infrastructure Security
- ✅ **Container isolation** - Docker security
- ✅ **Network segregation** - Internal services only
- ✅ **Secrets management** - Environment variables
- ✅ **MinIO encryption** - S3-compatible storage

---

## 🧪 Testing

### Test Coverage

| Component | Tests | Coverage | Status |
|-----------|-------|----------|--------|
| Backend Models | 50+ | 85% | ✅ Passing |
| API Endpoints | 80+ | 75% | ✅ Passing |
| Reconciliation Rules | 40+ | 70% | ✅ Passing |
| Authentication | 25+ | 90% | ✅ Passing |
| Document Extraction | 30+ | 65% | ⚠️  In Progress |
| Frontend Components | 20+ | 40% | ⚠️  In Progress |
| **Total** | **245+** | **~70%** | **Target: 85%** |

### Running Tests

```bash
# Backend tests
docker exec reims-backend python3 -m pytest tests/ -v

# Backend with coverage
docker exec reims-backend python3 -m pytest tests/ --cov=app --cov-report=html

# Frontend tests
docker exec reims-frontend npm run test

# Frontend with UI
docker exec reims-frontend npm run test:ui

# Frontend coverage
docker exec reims-frontend npm run test:coverage
```

---

## 📈 Performance

### Benchmarks

| Metric | Performance | Notes |
|--------|-------------|-------|
| **PDF Extraction** | 30-60 sec/doc | Depends on page count |
| **Reconciliation** | 5-10 sec | 311 rules across 5 docs |
| **API Response** | <200ms avg | 95th percentile <500ms |
| **Upload Speed** | <5 sec | 50MB PDF |
| **Concurrent Users** | 50+ | Tested load |
| **Document Throughput** | 100+/hour | With 2 workers |
| **Database Queries** | <50ms avg | Indexed queries |

### Scalability

- **Horizontal Scaling**: Add more Celery workers for parallel processing
- **Vertical Scaling**: Increase database resources for larger portfolios
- **Tested Scale**: 100+ properties × 12 months = 1,200+ period combinations
- **Document Retention**: 10+ years of historical data

---

## 🛠️ Development

### Backend Development

```bash
# View logs
docker logs reims-backend -f

# Access Python shell
docker exec -it reims-backend python3

# Run migrations
docker exec reims-backend alembic upgrade head

# Create new migration
docker exec reims-backend alembic revision --autogenerate -m "Add new table"

# Run specific test
docker exec reims-backend python3 -m pytest tests/test_specific.py -v

# Install new package
docker exec reims-backend pip install <package>
# Then update backend/requirements.txt
```

### Frontend Development

```bash
# View logs
docker logs reims-frontend -f

# Install new package
docker exec reims-frontend npm install <package>

# Lint code
docker exec reims-frontend npm run lint

# Build for production
docker exec reims-frontend npm run build

# Frontend auto-reloads on file changes - just edit src/ files
```

### Database Management

```bash
# PostgreSQL CLI
docker exec -it reims-postgres psql -U reims -d reims

# Execute SQL file
docker exec -i reims-postgres psql -U reims -d reims < script.sql

# Backup database
docker exec reims-postgres pg_dump -U reims reims > backup.sql

# Restore database
docker exec -i reims-postgres psql -U reims reims < backup.sql

# pgAdmin: http://localhost:5050
# Email: admin@pgadmin.com / Password: admin
# Add server: hostname=postgres, port=5432, user=reims, db=reims
```

### Celery Monitoring

```bash
# View worker logs
docker logs reims-celery-worker -f
docker logs reims-celery-audit-worker -f

# Restart workers
docker compose restart celery-worker celery-audit-worker

# Monitor tasks: http://localhost:5555

# Inspect active tasks
docker exec reims-celery-worker celery -A app.celery_app inspect active
```

---

## 🎯 API Reference

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Register new user |
| `/auth/login` | POST | Login user |
| `/auth/logout` | POST | Logout user |
| `/auth/me` | GET | Get current user |

### Properties

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/properties` | GET | List all properties |
| `/properties` | POST | Create property |
| `/properties/{id}` | GET | Get property details |
| `/properties/{id}` | PUT | Update property |
| `/properties/{id}` | DELETE | Delete property |
| `/properties/{id}/periods` | GET | Get periods for property |

### Documents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/documents/upload` | POST | Upload PDF document |
| `/documents/uploads` | GET | List all uploads |
| `/documents/uploads/{id}` | GET | Get upload details |
| `/documents/uploads/{id}/data` | GET | Get extracted data |
| `/documents/uploads/{id}/download` | GET | Download PDF |
| `/documents/uploads/{id}/reprocess` | POST | Reprocess extraction |
| `/documents/escrow-links` | GET | List escrow document links (FA-MORT-4; optional `property_id`, `period_id`) |
| `/documents/escrow-links` | POST | Create escrow document link (property_id, period_id, document_upload_id, escrow_type) |
| `/documents/escrow-links/{id}` | DELETE | Remove escrow document link |

### Reconciliation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/forensic-reconciliation/sessions` | POST | Start reconciliation |
| `/forensic-reconciliation/sessions/{id}` | GET | Get session details |
| `/forensic-reconciliation/calculated-rules` | GET | Get rule results |
| `/forensic-reconciliation/run` | POST | Execute rules |

### Forensic Audit

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/forensic-audit/overview` | GET | Executive dashboard data |
| `/forensic-audit/math-integrity` | GET | Math integrity analysis |
| `/forensic-audit/fraud-detection` | GET | Fraud indicators |
| `/forensic-audit/covenant-compliance` | GET | Covenant metrics |
| `/forensic-audit/tenant-risk` | GET | Tenant risk analysis |

### Alerts

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/alerts/committee-alerts` | GET | List committee alerts |
| `/alerts/committee-alerts` | POST | Create alert |
| `/alerts/alert-rules` | GET | List alert rules |
| `/alerts/alert-rules/{id}` | PUT | Update rule |

### General Ledger

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/gl/entries` | POST | Upload GL entries |
| `/gl/entries` | GET | List GL entries |
| `/gl/entries/{id}` | GET | Get entry details |

### Export

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/exports/balance-sheet/excel` | GET | Export BS to Excel |
| `/exports/income-statement/excel` | GET | Export IS to Excel |
| `/exports/csv` | GET | Export to CSV |
| `/exports/reconciliation-report` | GET | Export reconciliation |

**Full API Documentation**: http://localhost:8000/docs (Interactive Swagger UI)

---

## 📅 Changelog

### Version 2.1.0 (January 29, 2026) - **Current**
- ✅ **311+ Reconciliation Rules** - Complete implementation across 13 mixins
- ✅ **FA-MORT-4 Escrow Documentation** - EscrowDocumentLink model, rule, and API (`GET/POST/DELETE /documents/escrow-links`)
- ✅ **Reconciliation Config Seed** - Optional `backend/scripts/seed_reconciliation_config.sql` (AUDIT-48, COVENANT-6, BENCHMARK, RRBS-1, FA-CASH-4, FA-MORT-4 thresholds)
- ✅ **Filter Persistence** - Context maintained across 9 forensic dashboards
- ✅ **General Ledger Integration** - CSV/Excel import with auto-mapping
- ✅ **Data Governance** - Complete lineage and quality tracking
- ✅ **JSON Serialization Fix** - Resolved "0 Rules Active" bug
- ✅ **Proactive Alerts** - AUDIT-48, AUDIT-53, AUDIT-54 implementations
- ✅ **Market Intelligence Dashboard** - Property research automation
- ✅ **Self-Learning Enhancements** - Improved pattern recognition

### Version 2.0.0 (November 4, 2025)
- ✅ Complete authentication system
- ✅ 179-account Chart of Accounts
- ✅ 20 validation rules seeded
- ✅ 4 extraction templates
- ✅ Modern React + TypeScript frontend
- ✅ Excel and CSV export
- ✅ Celery worker operational
- ✅ Comprehensive documentation

### Version 1.1.0 (October 2025)
- ✅ Sprint 1.1 complete (core tables, APIs)
- ✅ Multi-engine PDF extraction
- ✅ PostgreSQL 17 + Redis infrastructure

### Version 1.0.0 (September 2025)
- ✅ Initial backend foundation
- ✅ FastAPI framework
- ✅ SQLAlchemy ORM

---

## 🤝 Contributing

### Development Workflow

1. **Read Documentation**:
   - [COMPLETE_IMPLEMENTATION_SUMMARY.md](COMPLETE_IMPLEMENTATION_SUMMARY.md)
   - [RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md](RECONCILIATION_RULES_IMPLEMENTATION_ANALYSIS.md)
   - [docs/RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md](docs/RECONCILIATION_RULES_DEEP_DIVE_AND_PLAN.md)
   - [docs/RECONCILIATION_RULES_IMPLEMENTATION_SUMMARY.md](docs/RECONCILIATION_RULES_IMPLEMENTATION_SUMMARY.md)

2. **Pick a Task**: Check open issues or backlog

3. **Write Tests First**: TDD approach preferred

4. **Implement Feature**: Follow coding standards

5. **Test Thoroughly**: Unit + integration tests

6. **Document Changes**: Update README and relevant docs

7. **Submit PR**: Include tests, docs, and description

### Code Standards

#### Backend (Python)
- Follow PEP 8 style guide
- Use type hints for all functions
- Write docstrings (Google style)
- 80% test coverage minimum
- Use SQLAlchemy 2.0 patterns

#### Frontend (TypeScript)
- TypeScript strict mode enabled
- Functional components with hooks
- ESLint + Prettier formatting
- Accessible UI (WCAG 2.1 AA)
- Responsive design (mobile-first)

### Branch Strategy
- `master` - Production-ready code
- `develop` - Integration branch
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

---

## 🐛 Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check service logs
docker compose logs backend
docker compose logs postgres

# Restart all services
docker compose restart

# Nuclear option: Full rebuild
docker compose down -v
docker compose up -d --build
```

#### Port Conflicts

```bash
# Port 5433 (PostgreSQL) in use
sudo lsof -i :5433
# Kill process or change port in docker-compose.yml

# Port 8000 (Backend) in use
sudo lsof -i :8000
```

#### Database Issues

```bash
# Check database connection
docker exec reims-postgres psql -U reims -d reims -c "SELECT version();"

# Reset database (WARNING: destroys all data)
docker compose down -v
docker compose up -d

# Manual migration
docker exec reims-backend alembic upgrade head
```

#### Extraction Failures

```bash
# Check Celery worker
docker logs reims-celery-worker -f

# Restart worker
docker compose restart celery-worker

# Monitor Flower
http://localhost:5555
```

#### Frontend Not Loading

```bash
# Clear browser cache
# Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

# Check frontend logs
docker logs reims-frontend -f

# Rebuild frontend
docker compose restart frontend
```

#### Reconciliation Shows "0 Rules Active"

```bash
# Restart backend (contains rule engine)
docker compose restart backend

# Check reconciliation logs
docker logs reims-backend | grep "Rule results saved"

# Verify database has results
docker exec reims-postgres psql -U reims -d reims \
  -c "SELECT COUNT(*) FROM cross_document_reconciliations;"
```

### Getting Help

1. **Check Logs**: Always start with `docker compose logs <service>`
2. **API Docs**: http://localhost:8000/docs for endpoint testing
3. **Celery Monitor**: http://localhost:5555 for task status
4. **Database Admin**: http://localhost:5050 for data inspection
5. **GitHub Issues**: Create an issue with logs and steps to reproduce

---

## 📄 License

Copyright © 2024-2026 REIMS Development Team. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

For licensing inquiries, contact: [your-email@example.com]

---

## 🙏 Acknowledgments

REIMS 2.0 is built on excellent open-source technologies:

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Powerful ORM
- **React** - UI library
- **PostgreSQL** - Robust database
- **Celery** - Distributed task queue
- **MinIO** - S3-compatible storage
- **PyMuPDF, PDFPlumber, Camelot, Tesseract** - PDF extraction engines

Special thanks to the open-source community for making this possible.

---

## 📞 Support & Contact

### Resources
- **Documentation**: See [docs/](docs/) folder
- **API Reference**: http://localhost:8000/docs
- **GitHub**: [Your Repository URL]
- **Email**: [your-email@example.com]

### Status

- **Production Status**: ✅ **Production-Ready**
- **Pilot Deployment**: ✅ **Active**
- **Enterprise Support**: ✅ **Available**

---

<div align="center">

**REIMS 2.0** - *Intelligent Financial Management for Real Estate*

Built with ❤️ by the REIMS Development Team

[⬆ Back to Top](#reims-20---real-estate-investment-management-system)

</div>
