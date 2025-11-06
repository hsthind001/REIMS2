#!/bin/bash
set -e

echo "🚀 REIMS Backend Starting..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
while ! pg_isready -h $POSTGRES_SERVER -p $POSTGRES_PORT -U $POSTGRES_USER; do
  sleep 1
done
echo "✅ PostgreSQL is ready!"

# Check if migrations should run (environment variable control)
RUN_MIGRATIONS=${RUN_MIGRATIONS:-false}

if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "🔄 Checking migration status..."
  cd /app
  
  # Check if database is initialized
  MIGRATION_CHECK=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'alembic_version';" 2>/dev/null || echo "0")
  
  if [ "$MIGRATION_CHECK" -eq "0" ]; then
    echo "🔄 Database not initialized, running migrations..."
    alembic upgrade head
    echo "✅ Migrations complete!"
  else
    # Check if migrations are pending
    CURRENT_REV=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null | xargs || echo "none")
    echo "ℹ️  Current migration: $CURRENT_REV"
    
    # Try to upgrade if behind
    echo "🔄 Checking for pending migrations..."
    alembic upgrade head || echo "⚠️  Migrations already current or failed (non-critical)"
  fi
  
  # Seed database (only if not already seeded)
  SEED_DATABASE=${SEED_DATABASE:-false}
  if [ "$SEED_DATABASE" = "true" ]; then
    echo "🌱 Checking if database needs seeding..."
    SEED_CHECK=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM chart_of_accounts WHERE account_code = '4010-0000';" 2>/dev/null || echo "0")
    
    if [ "$SEED_CHECK" -eq "0" ]; then
      echo "🌱 Seeding database with chart of accounts..."
      PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_balance_sheet_template_accounts.sql
      PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_balance_sheet_template_accounts_part2.sql
      PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_income_statement_template_accounts.sql
      PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_income_statement_template_accounts_part2.sql
      
      echo "🌱 Seeding validation rules..."
      PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_validation_rules.sql
      
      echo "🌱 Seeding extraction templates..."
      PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_extraction_templates.sql
      
      echo "🌱 Seeding lenders..."
      PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -f scripts/seed_lenders.sql
      
      echo "✅ Database seeded successfully!"
    else
      echo "ℹ️  Database already seeded, skipping..."
    fi
  fi
  
  # Reset orphaned extraction tasks
  echo "🧹 Checking for orphaned extraction tasks..."
  python3 /app/scripts/reset_orphaned_tasks.py || echo "⚠️  Orphaned task cleanup failed (non-critical)"
else
  echo "ℹ️  Migrations disabled (RUN_MIGRATIONS=false), skipping..."
fi

# Start the application
echo "🎯 Starting FastAPI application..."
exec "$@"
