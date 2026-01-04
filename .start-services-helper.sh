#!/bin/bash
# Helper script to start REIMS2 services
# This script will be run to start all Docker services

cd /home/hsthind/Documents/GitHub/REIMS2

echo "Starting REIMS2 services..."
docker compose up -d

echo "Waiting for services to initialize (60 seconds)..."
sleep 60

echo "Checking service status..."
docker compose ps

echo "Services started! Check http://localhost:5173"
