#!/bin/bash
set -e

echo "🚀 REIMS Backend Starting..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
while ! pg_isready -h $POSTGRES_SERVER -p $POSTGRES_PORT -U $POSTGRES_USER; do
  sleep 1
done
echo "✅ PostgreSQL is ready!"

# Run Alembic migrations
echo "🔄 Running database migrations..."
cd /app
alembic upgrade heads
echo "✅ Migrations complete!"

# Seed database (only if not already seeded)
echo "🌱 Checking if database needs seeding..."
SEED_CHECK=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM chart_of_accounts WHERE account_code = '4010-0000';" 2>/dev/null || echo "0")

if [ "$SEED_CHECK" -eq "0" ]; then
  echo "🌱 Seeding database with accounts and lenders..."
  
  PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_balance_sheet_template_accounts.sql
  PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_balance_sheet_template_accounts_part2.sql
  PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_income_statement_template_accounts.sql
  PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_income_statement_template_accounts_part2.sql
  PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_lenders.sql
  
  echo "✅ Database seeded successfully!"
else
  echo "ℹ️  Database already seeded, skipping..."
fi

# Start the application
echo "🎯 Starting FastAPI application..."
exec "$@"

