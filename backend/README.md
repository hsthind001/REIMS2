# REIMS Backend API

FastAPI backend with PostgreSQL and Redis integration.

## Features

- ✅ FastAPI framework
- ✅ PostgreSQL database with SQLAlchemy ORM
- ✅ Redis caching
- ✅ Pydantic data validation
- ✅ CORS middleware
- ✅ Modular architecture (routers, models, schemas)
- ✅ Health check endpoint
- ✅ Auto-generated API documentation

## Prerequisites

- Python 3.13+
- PostgreSQL 17
- Redis 7+

## Installation

1. Create virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (see `.env` file)

## Running the Application

### Development Mode

```bash
# From the backend directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── health.py      # Health check endpoint
│   │       └── users.py       # User CRUD operations
│   ├── core/
│   │   └── config.py          # Configuration settings
│   ├── db/
│   │   ├── database.py        # PostgreSQL connection
│   │   └── redis_client.py    # Redis connection
│   ├── models/
│   │   └── user.py            # SQLAlchemy models
│   ├── schemas/
│   │   └── user.py            # Pydantic schemas
│   └── main.py                # FastAPI application
├── tests/                     # Test files
├── venv/                      # Virtual environment
├── .env                       # Environment variables
├── .gitignore
├── requirements.txt
└── README.md
```

## Available Endpoints

### Health Check
- **GET** `/api/v1/health` - Check API, Database, and Redis status

### Users
- **GET** `/api/v1/users` - Get all users
- **GET** `/api/v1/users/{user_id}` - Get user by ID
- **POST** `/api/v1/users` - Create new user
- **PUT** `/api/v1/users/{user_id}` - Update user
- **DELETE** `/api/v1/users/{user_id}` - Delete user

## Database Connection

The application connects to PostgreSQL using:
- **Host**: localhost
- **Port**: 5432
- **Database**: reims
- **User**: reims
- **Password**: reims

## Redis Connection

The application connects to Redis using:
- **Host**: localhost
- **Port**: 6379
- **DB**: 0

## Environment Variables

See `.env` file for all available configuration options.

## Development

### Add New Endpoint

1. Create router in `app/api/v1/`
2. Create model in `app/models/`
3. Create schema in `app/schemas/`
4. Include router in `app/main.py`

### Database Migrations (with Alembic)

```bash
# Initialize Alembic (if not done)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Testing

```bash
pytest tests/
```

## Notes

- Password hashing is not implemented in the example user endpoints (marked with TODO)
- Add authentication/authorization as needed for production
- Update SECRET_KEY in production
- Configure proper CORS origins for production

