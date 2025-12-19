#!/bin/bash
# Real-time Upload Pipeline Monitor
# Monitors: Frontend → Backend → MinIO → Extraction → Database

echo "🚀 Upload Pipeline Monitor Started"
echo "=================================="
echo "Monitoring: Frontend → Backend → MinIO → Extraction → Database"
echo ""

# Function to check upload status
check_status() {
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') - Status Check ==="
    
    # Get recent uploads
    docker compose exec -T postgres psql -U reims -d reims -c "
        SELECT 
            id,
            document_type,
            extraction_status,
            LEFT(file_name, 30) as file_name
        FROM document_uploads 
        ORDER BY id DESC 
        LIMIT 5;
    " 2>&1 | grep -v "rows)" | grep -v "^$" | tail -6
    
    echo ""
}

# Function to check for issues
check_issues() {
    # Check for stuck processing
    stuck=$(docker compose exec -T postgres psql -U reims -d reims -t -c "
        SELECT COUNT(*) 
        FROM document_uploads 
        WHERE extraction_status = 'processing' 
        AND extraction_started_at < NOW() - INTERVAL '10 minutes';
    " 2>&1 | tr -d ' ')
    
    if [ "$stuck" != "0" ] && [ "$stuck" != "" ]; then
        echo "⚠️  WARNING: $stuck upload(s) stuck in processing for >10 minutes"
    fi
    
    # Check for failed extractions
    failed=$(docker compose exec -T postgres psql -U reims -d reims -t -c "
        SELECT COUNT(*) 
        FROM document_uploads 
        WHERE extraction_status = 'failed';
    " 2>&1 | tr -d ' ')
    
    if [ "$failed" != "0" ] && [ "$failed" != "" ]; then
        echo "❌ WARNING: $failed failed extraction(s) found"
    fi
    
    # Check for pending extractions
    pending=$(docker compose exec -T postgres psql -U reims -d reims -t -c "
        SELECT COUNT(*) 
        FROM document_uploads 
        WHERE extraction_status = 'pending';
    " 2>&1 | tr -d ' ')
    
    if [ "$pending" != "0" ] && [ "$pending" != "" ]; then
        echo "⏸️  WARNING: $pending upload(s) pending extraction for >30 seconds"
    fi
}

# Initial status
check_status
check_issues

# Monitor logs in real-time
echo "📊 Monitoring logs (Ctrl+C to stop)..."
echo ""

docker compose logs -f --tail=0 backend celery-worker 2>&1 | while IFS= read -r line; do
    # Check for upload events
    if echo "$line" | grep -qE "(POST /api/v1/documents/upload|📤 Uploading to MinIO|✅ File uploaded to MinIO)"; then
        echo "[$(date '+%H:%M:%S')] 📤 $line"
        sleep 2
        check_status
        check_issues
    fi
    
    # Check for extraction events
    if echo "$line" | grep -qE "(Starting extraction for upload_id|Extraction completed successfully|Extraction failed for upload_id)"; then
        echo "[$(date '+%H:%M:%S')] 🔄 $line"
        sleep 2
        check_status
    fi
    
    # Check for errors
    if echo "$line" | grep -qE "(ERROR|❌|error:|Exception|Traceback)"; then
        echo "[$(date '+%H:%M:%S')] ❌ $line"
    fi
done

