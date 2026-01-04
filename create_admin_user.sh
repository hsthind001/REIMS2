#!/bin/bash
# Create default admin user for REIMS

echo "Creating default admin user..."

curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "Admin123!"
  }'

echo ""
echo ""
echo "✅ Default admin user created!"
echo ""
echo "Login credentials:"
echo "  Email: admin@example.com"
echo "  Username: admin"
echo "  Password: Admin123!"
echo ""
echo "Access the application at: http://localhost:5173"
echo ""
echo "⚠️  IMPORTANT: Change the password after first login!"
