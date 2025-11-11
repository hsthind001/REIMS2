#!/bin/bash

##############################################################################
# MinIO Persistence Test Script
# Tests that MinIO buckets and files persist across container restarts
##############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "MinIO Persistence Test"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test file content
TEST_CONTENT="This is a test file created at $(date '+%Y-%m-%d %H:%M:%S')"
TEST_FILENAME="persistence-test-$(date +%s).txt"

echo -e "${BLUE}Step 1: Check if MinIO is running${NC}"
if ! docker ps | grep -q reims-minio; then
    echo -e "${RED}❌ MinIO container is not running${NC}"
    echo "Please start the stack first: docker compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ MinIO is running${NC}"
echo ""

echo -e "${BLUE}Step 2: Check if bucket exists${NC}"
docker run --rm --network reims_reims-network \
    minio/mc alias set myminio http://minio:9000 minioadmin minioadmin > /dev/null 2>&1

if ! docker run --rm --network reims_reims-network \
    minio/mc ls myminio/reims > /dev/null 2>&1; then
    echo -e "${RED}❌ Bucket 'reims' does not exist${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Bucket 'reims' exists${NC}"
echo ""

echo -e "${BLUE}Step 3: Upload test file${NC}"
echo "$TEST_CONTENT" | docker run --rm -i --network reims_reims-network \
    minio/mc pipe myminio/reims/test/$TEST_FILENAME
echo -e "${GREEN}✅ Uploaded: test/$TEST_FILENAME${NC}"
echo ""

echo -e "${BLUE}Step 4: Verify file exists${NC}"
docker run --rm --network reims_reims-network \
    minio/mc ls myminio/reims/test/
echo -e "${GREEN}✅ File listed successfully${NC}"
echo ""

echo -e "${BLUE}Step 5: Download and verify content${NC}"
DOWNLOADED_CONTENT=$(docker run --rm --network reims_reims-network \
    minio/mc cat myminio/reims/test/$TEST_FILENAME)
if [ "$DOWNLOADED_CONTENT" = "$TEST_CONTENT" ]; then
    echo -e "${GREEN}✅ Content matches!${NC}"
    echo "   Original: $TEST_CONTENT"
    echo "   Downloaded: $DOWNLOADED_CONTENT"
else
    echo -e "${RED}❌ Content mismatch!${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 6: Restart MinIO container${NC}"
echo "Stopping MinIO..."
docker compose stop minio
sleep 2
echo "Starting MinIO..."
docker compose up -d minio
echo "Waiting for MinIO to be healthy..."
sleep 5
echo -e "${GREEN}✅ MinIO restarted${NC}"
echo ""

echo -e "${BLUE}Step 7: Verify file still exists after restart${NC}"
MAX_RETRIES=10
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if docker run --rm --network reims_reims-network \
        minio/mc ls myminio/reims/test/$TEST_FILENAME > /dev/null 2>&1; then
        echo -e "${GREEN}✅ File still exists after restart!${NC}"
        break
    fi
    RETRY=$((RETRY + 1))
    echo "Waiting for MinIO... ($RETRY/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Failed to verify file after restart${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 8: Verify content still matches${NC}"
DOWNLOADED_CONTENT_AFTER=$(docker run --rm --network reims_reims-network \
    minio/mc cat myminio/reims/test/$TEST_FILENAME)
if [ "$DOWNLOADED_CONTENT_AFTER" = "$TEST_CONTENT" ]; then
    echo -e "${GREEN}✅ Content still matches after restart!${NC}"
    echo "   Content: $DOWNLOADED_CONTENT_AFTER"
else
    echo -e "${RED}❌ Content changed after restart!${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 9: Test bucket recreation${NC}"
echo "Removing and recreating containers (keeps volumes)..."
docker compose down
sleep 2
docker compose up -d minio minio-init
echo "Waiting for MinIO initialization..."
sleep 8
echo -e "${GREEN}✅ Containers recreated${NC}"
echo ""

echo -e "${BLUE}Step 10: Verify file still exists after down/up${NC}"
MAX_RETRIES=10
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if docker run --rm --network reims_reims-network \
        minio/mc ls myminio/reims/test/$TEST_FILENAME > /dev/null 2>&1; then
        echo -e "${GREEN}✅ File persists after docker compose down/up!${NC}"
        break
    fi
    RETRY=$((RETRY + 1))
    echo "Waiting for MinIO... ($RETRY/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ Failed to verify file after down/up${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 11: Final content verification${NC}"
FINAL_CONTENT=$(docker run --rm --network reims_reims-network \
    minio/mc cat myminio/reims/test/$TEST_FILENAME)
if [ "$FINAL_CONTENT" = "$TEST_CONTENT" ]; then
    echo -e "${GREEN}✅ Content remains intact!${NC}"
    echo "   Content: $FINAL_CONTENT"
else
    echo -e "${RED}❌ Content was corrupted!${NC}"
    exit 1
fi
echo ""

echo -e "${BLUE}Step 12: List all test files${NC}"
echo "All files in test directory:"
docker run --rm --network reims_reims-network \
    minio/mc ls myminio/reims/test/ || echo "No files in test/"
echo ""

echo -e "${BLUE}Step 13: Cleanup (optional)${NC}"
read -p "Do you want to delete the test file? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker run --rm --network reims_reims-network \
        minio/mc rm myminio/reims/test/$TEST_FILENAME
    echo -e "${GREEN}✅ Test file deleted${NC}"
else
    echo -e "${YELLOW}ℹ️  Test file kept: test/$TEST_FILENAME${NC}"
fi
echo ""

echo "=========================================="
echo -e "${GREEN}✅ ALL PERSISTENCE TESTS PASSED!${NC}"
echo "=========================================="
echo ""
echo "Summary:"
echo "  • Bucket 'reims' exists and is persistent"
echo "  • Files persist across container restarts"
echo "  • Files persist across docker compose down/up"
echo "  • Data is stored in volume: reims_minio-data"
echo ""
echo "View all stored data:"
echo "  docker run --rm --network reims_reims-network minio/mc ls myminio/reims --recursive"
echo ""
echo "Access MinIO Console:"
echo "  http://localhost:9001"
echo "  Username: minioadmin"
echo "  Password: minioadmin"
echo ""
echo "For more information, see: MINIO_PERSISTENCE.md"

