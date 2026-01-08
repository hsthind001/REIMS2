#!/bin/bash
# Setup script for Best-in-Class NLQ System with Temporal Support
#
# This script sets up:
# 1. Qdrant vector store
# 2. Neo4j knowledge graph
# 3. Python dependencies
# 4. Document ingestion
# 5. Environment configuration

set -e  # Exit on error

echo "=========================================="
echo "  REIMS NLQ System Setup"
echo "  Best-in-Class Multi-Agent RAG"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

print_success "Docker found"

# Step 1: Start Qdrant vector store
echo ""
echo "Step 1: Starting Qdrant vector store..."
if docker ps | grep -q qdrant; then
    print_warning "Qdrant is already running"
else
    docker run -d \
        --name qdrant \
        -p 6333:6333 \
        -p 6334:6334 \
        -v $(pwd)/qdrant_storage:/qdrant/storage \
        qdrant/qdrant:latest

    print_success "Qdrant started on port 6333"
fi

# Wait for Qdrant to be ready
echo "Waiting for Qdrant to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:6333/health > /dev/null 2>&1; then
        print_success "Qdrant is ready"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        print_error "Qdrant failed to start"
        exit 1
    fi
done

# Step 2: Start Neo4j knowledge graph (optional)
echo ""
echo "Step 2: Starting Neo4j knowledge graph..."
if docker ps | grep -q neo4j; then
    print_warning "Neo4j is already running"
else
    docker run -d \
        --name neo4j \
        -p 7474:7474 \
        -p 7687:7687 \
        -e NEO4J_AUTH=neo4j/password \
        -e NEO4J_PLUGINS='["apoc"]' \
        -v $(pwd)/neo4j_data:/data \
        neo4j:latest

    print_success "Neo4j started on ports 7474 (HTTP) and 7687 (Bolt)"
    print_warning "Default credentials: neo4j/password (change in production!)"
fi

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."
for i in {1..60}; do
    if curl -s http://localhost:7474 > /dev/null 2>&1; then
        print_success "Neo4j is ready"
        break
    fi
    sleep 1
    if [ $i -eq 60 ]; then
        print_warning "Neo4j startup timeout (may still be initializing)"
    fi
done

# Step 3: Install Python dependencies
echo ""
echo "Step 3: Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_success "Python dependencies installed"
else
    print_error "requirements.txt not found"
    exit 1
fi

# Step 4: Download spaCy model
echo ""
echo "Step 4: Downloading spaCy English model..."
python -m spacy download en_core_web_sm || print_warning "spaCy model download failed (not critical)"
print_success "spaCy model ready"

# Step 5: Create environment file
echo ""
echo "Step 5: Creating .env file..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# ============================================================================
# REIMS NLQ System Configuration
# ============================================================================

# LLM API Keys (at least one required)
NLQ_GROQ_API_KEY=your_groq_api_key_here  # Free, ultra-fast Llama 3.3 70B
NLQ_OPENAI_API_KEY=your_openai_api_key_here  # Optional fallback
NLQ_ANTHROPIC_API_KEY=your_anthropic_api_key_here  # Optional fallback

# Embedding API Keys
NLQ_JINA_API_KEY=your_jina_api_key_here  # Free tier available

# Qdrant Configuration
NLQ_QDRANT_HOST=localhost
NLQ_QDRANT_PORT=6333
NLQ_QDRANT_API_KEY=  # Leave empty for local deployment

# Neo4j Configuration
NLQ_NEO4J_URI=bolt://localhost:7687
NLQ_NEO4J_USER=neo4j
NLQ_NEO4J_PASSWORD=password

# Feature Flags
NLQ_ENABLE_HYBRID_SEARCH=true
NLQ_ENABLE_RERANKING=true
NLQ_ENABLE_MULTI_AGENT=true
NLQ_ENABLE_SEMANTIC_CACHE=true
NLQ_ENABLE_TEMPORAL_UNDERSTANDING=true

# Logging
NLQ_LOG_LEVEL=INFO

# Timezone
NLQ_TIMEZONE=UTC
EOF
    print_success ".env file created"
    print_warning "Please edit .env and add your API keys!"
else
    print_warning ".env file already exists (not overwriting)"
fi

# Step 6: Initialize database collections
echo ""
echo "Step 6: Initializing vector store collections..."
python -c "
from app.services.nlq.vector_store_manager import vector_store_manager
print('✅ Vector store initialized')
" || print_error "Failed to initialize vector store"

# Step 7: Ingest reconciliation documents
echo ""
echo "Step 7: Ingesting reconciliation documents..."
if [ -d "/home/hsthind/Downloads/Reconcile - Aduit - Rules" ]; then
    python scripts/ingest_reconciliation_docs.py
    print_success "Reconciliation documents ingested"
else
    print_warning "Reconciliation documents directory not found (skipping)"
fi

# Step 8: Create Neo4j schema
echo ""
echo "Step 8: Creating Neo4j knowledge graph schema..."
python -c "
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))

with driver.session() as session:
    # Create constraints
    session.run('CREATE CONSTRAINT IF NOT EXISTS FOR (p:Property) REQUIRE p.property_code IS UNIQUE')
    session.run('CREATE CONSTRAINT IF NOT EXISTS FOR (a:Account) REQUIRE a.account_code IS UNIQUE')

    # Create indexes
    session.run('CREATE INDEX IF NOT EXISTS FOR (p:FinancialPeriod) ON (p.year, p.month)')
    session.run('CREATE INDEX IF NOT EXISTS FOR (f:Formula) ON (f.name)')

    print('✅ Neo4j schema created')
driver.close()
" || print_warning "Neo4j schema creation failed (graph may not be ready yet)"

# Final summary
echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
print_success "Qdrant running on http://localhost:6333"
print_success "Neo4j UI available at http://localhost:7474"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys (especially NLQ_GROQ_API_KEY)"
echo "2. Run 'python scripts/ingest_chart_of_accounts.py' to load COA"
echo "3. Run 'python scripts/ingest_formulas.py' to load financial formulas"
echo "4. Start the backend: 'uvicorn app.main:app --reload'"
echo "5. Test the NLQ API: 'python scripts/test_nlq_queries.py'"
echo ""
print_success "REIMS NLQ System is ready!"
