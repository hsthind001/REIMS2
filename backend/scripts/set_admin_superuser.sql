-- Set admin user as superuser so /api/v1/admin/users and /api/v1/admin/audit-log work (Administration page).
-- Run once: PGPASSWORD=reims psql -h localhost -p 5433 -U reims -d reims -f scripts/set_admin_superuser.sql
UPDATE users SET is_superuser = true WHERE username = 'admin';
