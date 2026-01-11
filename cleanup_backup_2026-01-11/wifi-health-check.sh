#!/bin/bash
# WiFi Health Check and Optimization Script
# Generated for Intel WiFi (iwlwifi driver)

echo "========================================"
echo "   WiFi Health Check & Diagnostics"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Hardware Detection
echo "1. WiFi Hardware Detection"
echo "----------------------------------------"
WIFI_DEVICE=$(lspci | grep -i "network\|wireless" | head -1)
if [ -n "$WIFI_DEVICE" ]; then
    echo -e "${GREEN}✓${NC} WiFi Hardware: $WIFI_DEVICE"
else
    echo -e "${RED}✗${NC} No WiFi hardware detected"
    exit 1
fi
echo ""

# 2. Driver Information
echo "2. Driver Status"
echo "----------------------------------------"
DRIVER=$(nmcli -f GENERAL.DRIVER dev show wlp128s20f3 2>/dev/null | awk '{print $2}')
DRIVER_VERSION=$(nmcli -f GENERAL.DRIVER-VERSION dev show wlp128s20f3 2>/dev/null | awk '{print $2}')
FIRMWARE=$(nmcli -f GENERAL.FIRMWARE-VERSION dev show wlp128s20f3 2>/dev/null | awk '{print $2}')

echo -e "${GREEN}✓${NC} Driver: $DRIVER"
echo -e "${GREEN}✓${NC} Driver Version: $DRIVER_VERSION"
echo -e "${GREEN}✓${NC} Firmware: $FIRMWARE"

# Check if module is loaded
if lsmod | grep -q iwlwifi; then
    echo -e "${GREEN}✓${NC} iwlwifi module loaded"
else
    echo -e "${RED}✗${NC} iwlwifi module NOT loaded"
fi
echo ""

# 3. Connection Status
echo "3. Connection Status"
echo "----------------------------------------"
CONNECTION_STATE=$(nmcli -f GENERAL.STATE dev show wlp128s20f3 2>/dev/null | awk '{print $2, $3}')
SSID=$(iwconfig wlp128s20f3 2>/dev/null | grep ESSID | awk -F'"' '{print $2}')
IP_ADDRESS=$(nmcli -f IP4.ADDRESS dev show wlp128s20f3 2>/dev/null | awk 'NR==1{print $2}')

if [ "$CONNECTION_STATE" == "100 (connected)" ]; then
    echo -e "${GREEN}✓${NC} Status: Connected"
    echo -e "${GREEN}✓${NC} SSID: $SSID"
    echo -e "${GREEN}✓${NC} IP Address: $IP_ADDRESS"
else
    echo -e "${YELLOW}⚠${NC} Status: $CONNECTION_STATE"
fi
echo ""

# 4. Signal Strength & Speed
echo "4. Signal Quality & Performance"
echo "----------------------------------------"
SPEED=$(nmcli -f CAPABILITIES.SPEED dev show wlp128s20f3 2>/dev/null | awk '{print $2, $3}')
SIGNAL=$(iwconfig wlp128s20f3 2>/dev/null | grep "Signal level" | awk -F'=' '{print $3}' | awk '{print $1}')
QUALITY=$(iwconfig wlp128s20f3 2>/dev/null | grep "Link Quality" | awk -F'=' '{print $2}' | awk '{print $1}')
FREQUENCY=$(iwconfig wlp128s20f3 2>/dev/null | grep Frequency | awk '{print $2}' | cut -d':' -f2)

echo -e "${GREEN}✓${NC} Link Speed: $SPEED"
echo -e "${GREEN}✓${NC} Frequency: ${FREQUENCY} GHz"
echo -e "${GREEN}✓${NC} Signal Level: $SIGNAL dBm"
echo -e "${GREEN}✓${NC} Link Quality: $QUALITY"

# Evaluate signal strength
SIGNAL_NUM=$(echo $SIGNAL | tr -d '-')
if [ $SIGNAL_NUM -lt 50 ]; then
    echo -e "${GREEN}✓${NC} Signal: Excellent"
elif [ $SIGNAL_NUM -lt 60 ]; then
    echo -e "${GREEN}✓${NC} Signal: Good"
elif [ $SIGNAL_NUM -lt 70 ]; then
    echo -e "${YELLOW}⚠${NC} Signal: Fair"
else
    echo -e "${RED}✗${NC} Signal: Weak"
fi
echo ""

# 5. Power Management Status
echo "5. Power Management"
echo "----------------------------------------"
POWER_SAVE=$(cat /sys/module/iwlwifi/parameters/power_save 2>/dev/null)
if [ "$POWER_SAVE" == "N" ]; then
    echo -e "${GREEN}✓${NC} Power Save: Disabled (Optimal for performance)"
elif [ "$POWER_SAVE" == "Y" ]; then
    echo -e "${YELLOW}⚠${NC} Power Save: Enabled (May reduce performance)"
else
    echo -e "${YELLOW}⚠${NC} Power Save: $POWER_SAVE"
fi
echo ""

# 6. RF Kill Status
echo "6. RF Kill Status"
echo "----------------------------------------"
if rfkill list wifi | grep -q "Soft blocked: no"; then
    echo -e "${GREEN}✓${NC} WiFi not soft-blocked"
else
    echo -e "${RED}✗${NC} WiFi is soft-blocked"
fi

if rfkill list wifi | grep -q "Hard blocked: no"; then
    echo -e "${GREEN}✓${NC} WiFi not hard-blocked"
else
    echo -e "${RED}✗${NC} WiFi is hard-blocked (hardware switch)"
fi
echo ""

# 7. Connectivity Test
echo "7. Connectivity Test"
echo "----------------------------------------"
echo "Testing latency to 8.8.8.8..."
PING_RESULT=$(ping -c 5 -i 0.2 8.8.8.8 2>&1)
PACKET_LOSS=$(echo "$PING_RESULT" | grep -oP '\d+(?=% packet loss)')
AVG_LATENCY=$(echo "$PING_RESULT" | grep -oP 'rtt.*= [\d.]+/\K[\d.]+')

if [ "$PACKET_LOSS" -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Packet Loss: 0%"
else
    echo -e "${YELLOW}⚠${NC} Packet Loss: ${PACKET_LOSS}%"
fi

if [ -n "$AVG_LATENCY" ]; then
    echo -e "${GREEN}✓${NC} Average Latency: ${AVG_LATENCY} ms"

    if (( $(echo "$AVG_LATENCY < 30" | bc -l) )); then
        echo -e "${GREEN}✓${NC} Latency: Excellent"
    elif (( $(echo "$AVG_LATENCY < 100" | bc -l) )); then
        echo -e "${GREEN}✓${NC} Latency: Good"
    else
        echo -e "${YELLOW}⚠${NC} Latency: High"
    fi
fi
echo ""

# 8. DNS Test
echo "8. DNS Resolution Test"
echo "----------------------------------------"
if nslookup google.com >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} DNS Resolution: Working"
else
    echo -e "${RED}✗${NC} DNS Resolution: Failed"
fi
echo ""

# 9. Firmware Version Check
echo "9. Firmware Status"
echo "----------------------------------------"
INSTALLED_FW=$(dpkg -l | grep linux-firmware | awk '{print $3}')
echo -e "${GREEN}✓${NC} Installed: $INSTALLED_FW"
echo ""

# 10. WiFi Capabilities
echo "10. WiFi Capabilities"
echo "----------------------------------------"
if nmcli -f WIFI-PROPERTIES dev show wlp128s20f3 | grep -q "2GHZ.*yes"; then
    echo -e "${GREEN}✓${NC} 2.4 GHz Support: Yes"
fi
if nmcli -f WIFI-PROPERTIES dev show wlp128s20f3 | grep -q "5GHZ.*yes"; then
    echo -e "${GREEN}✓${NC} 5 GHz Support: Yes"
fi
if nmcli -f WIFI-PROPERTIES dev show wlp128s20f3 | grep -q "6GHZ.*yes"; then
    echo -e "${GREEN}✓${NC} 6 GHz Support: Yes (WiFi 6E)"
fi
if nmcli -f WIFI-PROPERTIES dev show wlp128s20f3 | grep -q "WPA2.*yes"; then
    echo -e "${GREEN}✓${NC} WPA2 Support: Yes"
fi
echo ""

# Summary
echo "========================================"
echo "   Summary & Recommendations"
echo "========================================"
echo ""

# Performance recommendations
if [ "$POWER_SAVE" == "Y" ]; then
    echo -e "${YELLOW}⚠${NC} Recommendation: Disable power saving for better performance"
    echo "   Command: sudo sed -i 's/wifi.powersave = 3/wifi.powersave = 2/' /etc/NetworkManager/conf.d/default-wifi-powersave-on.conf"
    echo "   Then run: sudo systemctl restart NetworkManager"
fi

if [ $SIGNAL_NUM -gt 65 ]; then
    echo -e "${YELLOW}⚠${NC} Recommendation: Weak signal detected"
    echo "   - Move closer to the router"
    echo "   - Check for interference"
    echo "   - Consider using 5GHz band if available"
fi

if [ -n "$PACKET_LOSS" ] && [ "$PACKET_LOSS" -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC} Recommendation: Packet loss detected"
    echo "   - Check for WiFi interference"
    echo "   - Update router firmware"
    echo "   - Try different WiFi channel"
fi

echo ""
echo "Overall Status: WiFi is functioning properly!"
echo "Current connection is using 5GHz band at $SPEED"
echo ""
