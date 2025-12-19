#!/bin/bash
# Configure CPU governor to performance mode
# Run with: sudo bash setup-cpu-governor.sh

set -e

echo "⚡ Configuring CPU governor to performance mode..."

# Install cpufrequtils if not already installed
if ! command -v cpufreq-set &> /dev/null; then
    apt-get update
    apt-get install -y cpufrequtils
fi

# Set governor immediately for all CPUs
cpufreq-set -r -g performance

# Create configuration file
cat > /etc/default/cpufrequtils << 'EOF'
# CPU Frequency Scaling Configuration
# Set to 'performance' for maximum CPU speed
GOVERNOR=performance
EOF

# Create systemd service to persist governor setting
cat > /etc/systemd/system/cpu-governor.service << 'EOF'
[Unit]
Description=Set CPU governor to performance
After=sysinit.target

[Service]
Type=oneshot
ExecStart=/usr/bin/cpufreq-set -r -g performance
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl daemon-reload
systemctl enable cpu-governor.service
systemctl start cpu-governor.service

echo "✅ CPU governor configured to performance mode!"
echo "Current governor status:"
cpufreq-info -o | grep -E "(analyzing|governor)" | head -3

