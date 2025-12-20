# Alert System Setup Guide

## Overview
This guide covers setting up and configuring the Comprehensive Risk Alerts System in REIMS 2.0.

## Database Setup

### Running Migrations
The alert system requires three database migrations:

1. **Alert Rules Enhancements** - Adds enhanced fields to `alert_rules` table
2. **Alert Enhancements** - Adds priority, correlation, and escalation fields to `committee_alerts` table
3. **Alert History** - Creates `alert_history` table for tracking state changes

**Migrations have been applied manually via SQL.** The migrations are available in:
- `backend/alembic/versions/20251220_0200_add_alert_rules_enhancements.py`
- `backend/alembic/versions/20251220_0201_add_alert_enhancements.py`
- `backend/alembic/versions/20251220_0202_add_alert_history.py`

### Seeding Default Rules
Default alert rules are automatically seeded during database initialization. To manually seed:

```bash
docker exec reims-postgres psql -U reims -d reims -f scripts/seed_default_alert_rules.sql
```

This creates 6 default rules:
- DSCR Threshold Breach (1.25)
- Occupancy Rate Warning (85%)
- LTV Ratio Breach (75%)
- Cash Flow Negative
- Debt Yield Breach (8%)
- Interest Coverage Breach (1.5)

## Email Configuration

### Environment Variables
Configure email settings via environment variables in `.env` or `docker-compose.yml`:

```bash
# SMTP Configuration
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USE_TLS=true
EMAIL_SMTP_USERNAME=your-email@gmail.com
EMAIL_SMTP_PASSWORD=your-app-password
EMAIL_SMTP_FROM_EMAIL=noreply@reims.com
EMAIL_SMTP_FROM_NAME=REIMS 2.0

# Email Features
EMAIL_ENABLED=true
EMAIL_DEBUG=false  # Set to true to log emails instead of sending

# Notification Preferences
EMAIL_SEND_ALERT_EMAILS=true
EMAIL_SEND_DIGEST_EMAILS=true
EMAIL_SEND_ESCALATION_EMAILS=true

# Digest Schedule
EMAIL_DIGEST_SCHEDULE=daily  # daily, weekly, or never
EMAIL_DIGEST_TIME=09:00  # 24-hour format
```

### Development Setup (MailHog)
For local development, use MailHog to capture emails:

```bash
# Add to docker-compose.yml or run separately
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

Then configure:
```bash
EMAIL_SMTP_HOST=localhost
EMAIL_SMTP_PORT=1025
EMAIL_SMTP_USE_TLS=false
EMAIL_DEBUG=false
```

View emails at: http://localhost:8025

### Production Setup
For production, configure with your SMTP provider:

**Gmail Example:**
```bash
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USE_TLS=true
EMAIL_SMTP_USERNAME=your-email@gmail.com
EMAIL_SMTP_PASSWORD=your-app-password  # Use App Password, not regular password
```

**SendGrid Example:**
```bash
EMAIL_SMTP_HOST=smtp.sendgrid.net
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USE_TLS=true
EMAIL_SMTP_USERNAME=apikey
EMAIL_SMTP_PASSWORD=your-sendgrid-api-key
```

## Creating Alert Rules

### Via API
```bash
# Create rule from template
curl -X POST "http://localhost:8000/api/v1/alert-rules/templates/dscr_threshold_breach/create" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create custom rule
curl -X POST "http://localhost:8000/api/v1/alert-rules" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "rule_name": "Custom DSCR Rule",
    "rule_type": "threshold",
    "field_name": "dscr",
    "condition": "less_than",
    "threshold_value": 1.20,
    "severity": "critical",
    "is_active": true
  }'
```

### Via Frontend
1. Navigate to Risk Management page
2. Click "Manage Alert Rules" button
3. Click "Create from Template" or "Create Rule"
4. Fill in rule details
5. Save and activate

## Testing Alert Rules

### Test Rule Evaluation
```bash
curl -X POST "http://localhost:8000/api/v1/alert-rules/{rule_id}/test" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "property_id": 1,
    "period_id": 1
  }'
```

### Trigger Alerts Manually
Alerts are automatically triggered after document processing. To trigger manually:

```bash
# Via Celery task
docker exec reims-celery-worker celery -A app.tasks call app.tasks.alert_monitoring_tasks.evaluate_alerts_for_property \
  --args='[1, 1]'  # property_id, period_id
```

## Monitoring and Maintenance

### Scheduled Tasks
The following Celery tasks run automatically:

1. **Daily Monitoring** - `monitor_all_properties` (runs daily)
2. **Escalation Check** - `escalate_overdue_alerts` (runs hourly)
3. **Priority Update** - `update_alert_priorities` (runs every 6 hours)
4. **Digest Generation** - `generate_alert_digest` (runs daily at configured time)
5. **Cleanup** - `cleanup_resolved_alerts` (runs weekly)

### Viewing Alerts
- **Dashboard**: Navigate to Risk Management → Risk Alerts tab
- **API**: `GET /api/v1/risk-alerts`
- **Analytics**: `GET /api/v1/risk-alerts/analytics`

### Alert Management
- **Acknowledge**: `POST /api/v1/risk-alerts/alerts/{id}/acknowledge`
- **Resolve**: `POST /api/v1/risk-alerts/alerts/{id}/resolve`
- **Dismiss**: `POST /api/v1/risk-alerts/alerts/{id}/dismiss`
- **Escalate**: `POST /api/v1/risk-alerts/{id}/escalate`
- **Bulk Actions**: `POST /api/v1/risk-alerts/bulk-acknowledge`

## Troubleshooting

### Alerts Not Triggering
1. Check rule is active: `GET /api/v1/alert-rules?is_active=true`
2. Verify metrics exist: Check `financial_metrics` table
3. Check cooldown period: Rule may be in cooldown
4. Review logs: `docker logs reims-backend | grep -i alert`

### Email Not Sending
1. Check SMTP configuration: Verify environment variables
2. Test SMTP connection: Check `EMAIL_DEBUG=true` to see logged emails
3. Review logs: `docker logs reims-backend | grep -i email`
4. Verify email enabled: Check `EMAIL_ENABLED=true`

### Migration Issues
If migrations fail:
1. Check current version: `docker exec reims-postgres psql -U reims -d reims -c "SELECT version_num FROM alembic_version;"`
2. Apply manually: Use SQL commands from migration files
3. Verify tables: Check that new columns/tables exist

## Best Practices

1. **Start with Templates**: Use pre-built templates before creating custom rules
2. **Test Rules**: Always test rules before activating
3. **Monitor Performance**: Check rule execution_count to identify slow rules
4. **Review Regularly**: Periodically review and update rule thresholds
5. **Use Cooldowns**: Set appropriate cooldown periods to prevent alert spam
6. **Property-Specific Rules**: Create property-specific rules for unique thresholds
7. **Severity Mapping**: Use severity_mapping for dynamic severity assignment

## API Documentation

Full API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Key endpoints:
- `/api/v1/alert-rules` - Rule management
- `/api/v1/risk-alerts` - Alert management
- `/api/v1/risk-alerts/summary` - Dashboard summary
- `/api/v1/risk-alerts/trends` - Alert trends
- `/api/v1/risk-alerts/analytics` - Analytics data

