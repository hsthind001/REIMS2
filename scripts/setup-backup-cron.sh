#!/bin/bash
# REIMS2 Backup Cron Setup Script
# Sets up automated daily backups via cron

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== REIMS2 Backup Cron Setup ===${NC}"
echo ""

SCRIPT_PATH="/home/singh/REIMS2/scripts/backup-volumes.sh"
LOG_PATH="/home/singh/REIMS2/backups/backup.log"

# Verify backup script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo -e "${RED}Error: Backup script not found at $SCRIPT_PATH${NC}"
    exit 1
fi

# Make sure log directory exists
mkdir -p "$(dirname "$LOG_PATH")"

echo "This script will set up automated daily backups."
echo ""
echo "Available schedules:"
echo "1) Daily at 2:00 AM (recommended)"
echo "2) Daily at 12:00 AM (midnight)"
echo "3) Daily at 6:00 AM"
echo "4) Every 12 hours (2:00 AM and 2:00 PM)"
echo "5) Custom schedule"
echo "6) Cancel"
echo ""
read -p "Select schedule (1-6): " schedule

case $schedule in
    1)
        CRON_SCHEDULE="0 2 * * *"
        DESCRIPTION="Daily at 2:00 AM"
        ;;
    2)
        CRON_SCHEDULE="0 0 * * *"
        DESCRIPTION="Daily at midnight"
        ;;
    3)
        CRON_SCHEDULE="0 6 * * *"
        DESCRIPTION="Daily at 6:00 AM"
        ;;
    4)
        CRON_SCHEDULE="0 2,14 * * *"
        DESCRIPTION="Every 12 hours (2:00 AM and 2:00 PM)"
        ;;
    5)
        echo ""
        echo "Enter custom cron schedule (e.g., '0 3 * * *' for 3:00 AM daily):"
        read -p "Schedule: " CRON_SCHEDULE
        DESCRIPTION="Custom: $CRON_SCHEDULE"
        ;;
    6)
        echo "Setup cancelled"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${YELLOW}Setting up backup schedule: $DESCRIPTION${NC}"

# Create cron job entry
CRON_JOB="$CRON_SCHEDULE $SCRIPT_PATH >> $LOG_PATH 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo -e "${YELLOW}Existing backup cron job found. Replacing...${NC}"
    # Remove old entry and add new one
    (crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH"; echo "$CRON_JOB") | crontab -
else
    # Add new entry
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
fi

echo -e "${GREEN}✓ Backup cron job installed successfully${NC}"
echo ""
echo "Configuration:"
echo "  Schedule: $DESCRIPTION ($CRON_SCHEDULE)"
echo "  Script: $SCRIPT_PATH"
echo "  Log: $LOG_PATH"
echo ""
echo "Current crontab:"
crontab -l | grep "$SCRIPT_PATH"
echo ""

# Test the backup script
echo -e "${YELLOW}Testing backup script...${NC}"
read -p "Run a test backup now? (yes/no): " test

if [ "$test" = "yes" ]; then
    echo ""
    bash "$SCRIPT_PATH"
    echo ""
    echo -e "${GREEN}✓ Test backup completed${NC}"
fi

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Useful commands:"
echo "  View cron jobs:     crontab -l"
echo "  Edit cron jobs:     crontab -e"
echo "  Remove cron job:    crontab -l | grep -v 'backup-volumes.sh' | crontab -"
echo "  View backup log:    tail -f $LOG_PATH"
echo "  Run backup manually: bash $SCRIPT_PATH"
echo ""

