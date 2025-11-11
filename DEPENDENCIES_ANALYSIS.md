# 🔍 REIMS2 Project Dependencies Analysis

**Generated:** November 11, 2025  
**Project Path:** `/home/singh/REIMS2`

---

## 📊 **Overview**

The REIMS2 project is a **full-stack application** with:
- **Frontend:** React + TypeScript + Vite
- **Backend:** Python FastAPI
- **Infrastructure:** Docker Compose with 8 services
- **Total Dependencies:** 100+ packages

---

## 🎨 **Frontend Dependencies (Node.js)**

### **Runtime Dependencies** (3)
| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^19.1.1 | UI framework |
| `react-dom` | ^19.1.1 | React DOM rendering |
| `recharts` | ^3.3.0 | Charts and data visualization |

### **Development Dependencies** (17)
| Package | Version | Purpose |
|---------|---------|---------|
| `typescript` | ~5.9.3 | TypeScript compiler |
| `vite` | ^7.1.7 | Build tool & dev server |
| `@vitejs/plugin-react` | ^5.0.4 | React plugin for Vite |
| `eslint` | ^9.36.0 | Code linting |
| `vitest` | ^4.0.8 | Testing framework |
| `@testing-library/react` | ^16.3.0 | React testing utilities |
| `@testing-library/jest-dom` | ^6.9.1 | Jest DOM matchers |
| `@testing-library/user-event` | ^14.6.1 | User interaction testing |
| `@types/react` | ^19.1.16 | React TypeScript types |
| `@types/react-dom` | ^19.1.9 | React DOM TypeScript types |
| `@types/node` | ^24.6.0 | Node.js TypeScript types |
| `typescript-eslint` | ^8.45.0 | TypeScript ESLint parser |
| `eslint-plugin-react-hooks` | ^5.2.0 | React Hooks linting |
| `eslint-plugin-react-refresh` | ^0.4.22 | React Refresh linting |
| `globals` | ^16.4.0 | Global variables for ESLint |
| `jsdom` | ^27.1.0 | DOM implementation for testing |
| `@eslint/js` | ^9.36.0 | ESLint JavaScript config |

**📦 Installation Command:**
```bash
cd /home/singh/REIMS2
npm install
```

**⚙️ Available Scripts:**
```bash
npm run dev          # Start dev server (port 5173)
npm run build        # Build for production
npm run lint         # Run ESLint
npm run test         # Run tests
npm run test:ui      # Run tests with UI
npm run test:coverage # Run tests with coverage
npm run preview      # Preview production build
```

---

## 🐍 **Backend Dependencies (Python)**

### **Core Framework** (8 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.121.0 | Web framework |
| `uvicorn` | 0.38.0 | ASGI server |
| `pydantic` | 2.12.3 | Data validation |
| `pydantic-settings` | 2.11.0 | Settings management |
| `python-multipart` | 0.0.20 | File upload handling |
| `python-dotenv` | 1.2.1 | Environment variables |
| `starlette` | 0.49.3 | ASGI toolkit |
| `httptools` | 0.7.1 | HTTP parsing |

### **Database** (4 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| `SQLAlchemy` | 2.0.44 | ORM |
| `psycopg2-binary` | 2.9.11 | PostgreSQL driver |
| `alembic` | 1.17.1 | Database migrations |
| `greenlet` | 3.2.4 | Async support |

### **Task Queue** (9 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| `celery` | 5.5.3 | Task queue |
| `redis` | 5.2.1 | Redis client |
| `flower` | 2.0.1 | Celery monitoring |
| `kombu` | 5.5.4 | Messaging library |
| `billiard` | 4.2.2 | Process pooling |
| `vine` | 5.1.0 | Promises/futures |
| `amqp` | 5.3.1 | AMQP protocol |
| `click` | 8.3.0 | CLI framework |
| `prometheus_client` | 0.23.1 | Metrics |

### **Object Storage** (1 package)
| Package | Version | Purpose |
|---------|---------|---------|
| `minio` | 7.2.18 | S3-compatible storage client |

### **PDF Processing** (10 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| `pdfplumber` | 0.11.7 | PDF text extraction |
| `pypdf` | 5.9.0 | PDF manipulation |
| `PyMuPDF` | 1.26.5 | PDF rendering |
| `pdf2image` | 1.17.0 | PDF to image conversion |
| `pdfminer.six` | 20250506 | PDF mining |
| `pypdfium2` | 5.0.0 | PDF rendering |
| `camelot-py` | 1.0.9 | PDF table extraction |
| `pytesseract` | 0.3.13 | OCR |
| `opencv-python-headless` | 4.12.0.88 | Image processing |
| `pillow` | 12.0.0 | Image manipulation |

### **Data Processing** (5 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| `pandas` | 2.3.3 | Data analysis |
| `numpy` | 2.2.6 | Numerical computing |
| `openpyxl` | 3.1.5 | Excel file handling |
| `tabulate` | 0.9.0 | Table formatting |
| `PyYAML` | 6.0.3 | YAML parsing |

### **AI/ML Dependencies** (8 packages) 🤖
| Package | Version | Purpose |
|---------|---------|---------|
| `transformers` | 4.44.2 | Hugging Face transformers |
| `torch` | 2.6.0 | PyTorch deep learning |
| `torchvision` | 0.21.0 | Computer vision |
| `sentencepiece` | 0.2.0 | Text tokenization |
| `accelerate` | 1.2.1 | Training acceleration |
| `easyocr` | 1.7.2 | OCR |
| `pyod` | 1.1.0 | Outlier detection |
| `joblib` | 1.4.2 | Model serialization |

### **Text Processing** (5 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| `fuzzywuzzy` | 0.18.0 | Fuzzy string matching |
| `Levenshtein` | 0.27.3 | String distance |
| `RapidFuzz` | 3.14.3 | Fast fuzzy matching |
| `langdetect` | 1.0.9 | Language detection |
| `chardet` | 5.2.0 | Character encoding detection |

### **Security & Authentication** (5 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| `passlib[bcrypt]` | 1.7.4 | Password hashing |
| `PyJWT` | 2.10.1 | JWT tokens |
| `itsdangerous` | 2.2.0 | Session signing |
| `cryptography` | 46.0.3 | Cryptographic operations |
| `argon2-cffi` | 25.1.0 | Argon2 password hashing |

### **Testing** (2 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | 8.3.4 | Testing framework |
| `httpx` | 0.28.1 | HTTP client for testing |

### **Utilities** (10 packages)
| Package | Version | Purpose |
|---------|---------|---------|
| `python-dateutil` | 2.9.0.post0 | Date utilities |
| `pytz` | 2025.2 | Timezone handling |
| `email-validator` | 2.3.0 | Email validation |
| `humanize` | 4.14.0 | Human-readable formats |
| `slowapi` | 0.1.9 | Rate limiting |
| `dnspython` | 2.8.0 | DNS toolkit |
| `certifi` | 2025.10.5 | SSL certificates |
| `urllib3` | 2.5.0 | HTTP library |
| `requests` | (via certifi) | HTTP requests |
| `packaging` | 25.0 | Version parsing |

**📦 Installation Command:**
```bash
cd /home/singh/REIMS2/backend
pip install -r requirements.txt
```

**Or via Docker:**
```bash
docker build -f backend/Dockerfile.base -t reims-base:latest backend/
```

---

## 🐳 **Docker Infrastructure**

### **Services** (8 containers)
| Service | Image | Purpose | Port(s) |
|---------|-------|---------|---------|
| `postgres` | postgres:17.6 | Database | 5433 |
| `redis` | redis/redis-stack:latest | Cache & Queue | 6379, 8001 |
| `minio` | minio/minio:latest | Object Storage | 9000, 9001 |
| `pgadmin` | dpage/pgadmin4:latest | Database GUI | 5050 |
| `backend` | Custom (Python) | API Server | 8000 |
| `celery-worker` | Custom (Python) | Task Worker | - |
| `flower` | Custom (Python) | Task Monitor | 5555 |
| `frontend` | Custom (Node) | React App | 5173 |

### **Volumes** (5 persistent)
```
postgres-data      # PostgreSQL database files
redis-data         # Redis persistence
minio-data         # Uploaded PDF files
pgadmin-data       # pgAdmin configuration
ai-models-cache    # Cached AI/ML models (Hugging Face)
```

### **Networks**
```
reims-network      # Bridge network for all services
```

**🚀 Management Commands:**
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f celery-worker

# Restart a service
docker compose restart backend

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

---

## 🔧 **System Requirements**

### **Host Machine:**
- **OS:** Ubuntu 24.04 LTS (or compatible Linux)
- **Docker:** 20.10+ 
- **Docker Compose:** 2.0+
- **RAM:** 8GB minimum, 16GB recommended
- **Disk:** 20GB free space (for volumes & images)
- **CPU:** 4+ cores recommended (for AI/ML models)

### **External Dependencies:**
✅ Already containerized (no host installation needed):
- PostgreSQL 17.6
- Redis Stack
- MinIO
- Node.js 20
- Python 3.11+

### **Optional (for development without Docker):**
- Python 3.11+
- Node.js 20+
- npm 10+
- PostgreSQL client tools
- Redis client tools

---

## 📦 **Dependency Installation Matrix**

| Environment | Frontend | Backend | Infrastructure |
|-------------|----------|---------|----------------|
| **Docker (Recommended)** | ✅ Auto | ✅ Auto | ✅ Auto |
| **Local Development** | `npm install` | `pip install -r requirements.txt` | Manual setup |
| **CI/CD** | `npm ci` | `pip install -r requirements.txt` | Docker images |

---

## 🔐 **External Services & API Keys**

The project **may require** these API keys (check `.env` file):

| Service | Environment Variable | Required For |
|---------|---------------------|-------------|
| Anthropic Claude | `ANTHROPIC_API_KEY` | AI document analysis |
| OpenAI | `OPENAI_API_KEY` | AI document analysis |
| Perplexity | `PERPLEXITY_API_KEY` | Research features |
| Google AI | `GOOGLE_API_KEY` | AI features |
| Mistral | `MISTRAL_API_KEY` | AI features |
| Azure OpenAI | `AZURE_OPENAI_API_KEY` | AI features |
| OpenRouter | `OPENROUTER_API_KEY` | AI features |
| Ollama | `OLLAMA_API_KEY` | Local AI models |

**Current Status:** ✅ Anthropic and OpenAI keys configured in `.cursor/mcp.json`

---

## 🎯 **Quick Start Checklist**

### **Verify Docker Setup:**
```bash
cd /home/singh/REIMS2
docker compose ps
```

### **Check Service Health:**
```bash
# Backend API
curl http://localhost:8000/health

# Frontend
curl http://localhost:5173

# PostgreSQL
docker exec reims-postgres pg_isready -U reims

# Redis
docker exec reims-redis redis-cli ping

# MinIO
curl http://localhost:9000/minio/health/live
```

### **Install New Dependencies:**

**Frontend:**
```bash
# Add package
npm install package-name

# Or via Docker
./docker-npm install package-name

# Rebuild container
docker compose restart frontend
```

**Backend:**
```bash
# Add to requirements.txt
echo "package-name==1.0.0" >> backend/requirements.txt

# Or via Docker
./docker-pip install package-name

# Rebuild base image
docker build -f backend/Dockerfile.base -t reims-base:latest backend/

# Restart services
docker compose up -d --build backend celery-worker
```

---

## 📈 **Dependency Size Analysis**

### **Frontend:**
- **node_modules:** ~350 MB
- **Build output:** ~2 MB (gzipped)
- **Docker image:** ~180 MB (node:20-alpine)

### **Backend:**
- **Python packages:** ~2.5 GB
- **AI/ML models:** ~1.5 GB (cached in volume)
- **Docker image:** ~4 GB (base + app)

### **Total Project Size:**
- **Source code:** ~50 MB
- **Dependencies:** ~3 GB
- **Docker volumes:** ~5 GB (with data)
- **Docker images:** ~5 GB
- **Total:** ~13 GB

---

## 🔄 **Dependency Update Strategy**

### **Check for Updates:**
```bash
# Frontend
npm outdated

# Backend
pip list --outdated
```

### **Update Dependencies:**
```bash
# Frontend (minor/patch)
npm update

# Frontend (major - careful!)
npm install react@latest

# Backend (check compatibility first!)
pip install --upgrade package-name
```

### **Security Updates:**
```bash
# Frontend
npm audit fix

# Backend
pip-audit (install separately)
```

---

## 🐛 **Common Dependency Issues**

### **Issue 1: Module Not Found**
```bash
# Frontend
docker compose restart frontend

# Backend
docker compose up -d --build backend celery-worker
```

### **Issue 2: Version Conflicts**
```bash
# Check versions
npm list package-name
pip show package-name

# Clear caches
npm cache clean --force
docker builder prune
```

### **Issue 3: Missing System Dependencies**
```bash
# Backend needs these (already in Dockerfile):
- postgresql-client (for psql)
- redis-tools (for redis-cli)
- build-essential (for compiling Python packages)
```

---

## 📝 **Dependency Files Summary**

| File | Location | Purpose |
|------|----------|---------|
| `package.json` | `/home/singh/REIMS2/` | Frontend deps |
| `package-lock.json` | `/home/singh/REIMS2/` | Locked versions |
| `requirements.txt` | `/home/singh/REIMS2/backend/` | Backend deps |
| `docker-compose.yml` | `/home/singh/REIMS2/` | Infrastructure |
| `Dockerfile` | `/home/singh/REIMS2/backend/` | Backend image |
| `Dockerfile.base` | `/home/singh/REIMS2/backend/` | Base image with all deps |
| `Dockerfile.frontend` | `/home/singh/REIMS2/` | Frontend image |

---

## ✅ **Dependency Health Status**

| Category | Status | Notes |
|----------|--------|-------|
| Frontend Deps | ✅ Healthy | React 19, Vite 7 (latest) |
| Backend Deps | ✅ Healthy | FastAPI, SQLAlchemy (stable) |
| Docker Images | ✅ Healthy | Official images, recent versions |
| AI/ML Models | ✅ Cached | Stored in Docker volume |
| Security | ⚠️ Review | Run `npm audit` periodically |
| Updates | 📅 Regular | Check monthly for updates |

---

**Last Analyzed:** November 11, 2025  
**Next Review:** December 11, 2025  
**Status:** ✅ All dependencies installed and working

