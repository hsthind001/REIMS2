#!/bin/bash
# PostgreSQL Restore Script

set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore_postgres.sh <backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE=$1

echo "WARNING: This will restore the database to backup: $BACKUP_FILE"
echo "All current data will be lost. Continue? (yes/no)"
read CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Stop services
echo "Stopping services..."
docker-compose down

# Drop and recreate database
echo "Recreating database..."
docker-compose up -d db
sleep 5

# Restore from backup
echo "Restoring from backup..."
gunzip < $BACKUP_FILE | docker exec -i reims2_db psql -U postgres -d reims2_db

# Restart services
echo "Restarting services..."
docker-compose up -d

echo "Restore completed successfully!"

