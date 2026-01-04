#!/bin/bash
# Switch BELL565 to 5 GHz Band for Better Performance
# This fixes low signal issues caused by 2.4 GHz congestion

echo "================================================"
echo "   BELL565 - Switch to 5 GHz Band"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Show current status
echo "Step 1: Current Connection Status"
echo "----------------------------------------"
CURRENT_FREQ=$(iwconfig wlp128s20f3 2>/dev/null | grep Frequency | awk '{print $2}' | cut -d':' -f2)
CURRENT_SIGNAL=$(iwconfig wlp128s20f3 2>/dev/null | grep "Signal level" | awk -F'=' '{print $3}' | awk '{print $1}')
CURRENT_BSSID=$(iwconfig wlp128s20f3 2>/dev/null | grep "Access Point" | awk '{print $6}')

echo "Current Frequency: ${YELLOW}${CURRENT_FREQ}${NC} GHz"
echo "Current Signal: ${YELLOW}${CURRENT_SIGNAL}${NC} dBm"
echo "Current BSSID: ${YELLOW}${CURRENT_BSSID}${NC}"

if [[ "$CURRENT_FREQ" == "2.412" ]] || [[ "$CURRENT_FREQ" =~ ^2\. ]]; then
    echo -e "${RED}✗${NC} You are on 2.4 GHz (congested band)"
    NEEDS_SWITCH=true
elif [[ "$CURRENT_FREQ" =~ ^5\. ]]; then
    echo -e "${GREEN}✓${NC} You are already on 5 GHz (optimal)"
    NEEDS_SWITCH=false
else
    echo -e "${YELLOW}⚠${NC} Cannot determine frequency"
    NEEDS_SWITCH=true
fi

echo ""

if [ "$NEEDS_SWITCH" = false ]; then
    echo "================================================"
    echo "   Already Optimized!"
    echo "================================================"
    echo ""
    echo "You're already connected to 5 GHz band."
    echo "No changes needed."
    echo ""
    exit 0
fi

# Step 2: Show available bands
echo "Step 2: Available BELL565 Networks"
echo "----------------------------------------"
echo "Scanning for BELL565 access points..."
nmcli dev wifi rescan >/dev/null 2>&1
sleep 2

echo ""
nmcli dev wifi list | grep -E "SSID|BELL565" | head -10
echo ""

# Step 3: Configure for 5 GHz
echo "Step 3: Configuring for 5 GHz Band"
echo "----------------------------------------"
echo "Setting 802-11-wireless.band to 'a' (5 GHz)..."

nmcli connection modify BELL565 802-11-wireless.band a

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Configuration updated successfully"
else
    echo -e "${RED}✗${NC} Failed to update configuration"
    exit 1
fi

echo ""

# Step 4: Reconnect
echo "Step 4: Reconnecting to Network"
echo "----------------------------------------"
echo "Disconnecting from BELL565..."
nmcli connection down BELL565 >/dev/null 2>&1

echo "Waiting 2 seconds..."
sleep 2

echo "Connecting to BELL565 (5 GHz)..."
nmcli connection up BELL565

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Reconnected successfully"
else
    echo -e "${RED}✗${NC} Failed to reconnect"
    echo ""
    echo "Reverting to automatic band selection..."
    nmcli connection modify BELL565 802-11-wireless.band ""
    nmcli connection up BELL565
    exit 1
fi

echo ""
echo "Waiting 3 seconds for connection to stabilize..."
sleep 3
echo ""

# Step 5: Verify new connection
echo "Step 5: Verifying New Connection"
echo "----------------------------------------"
NEW_FREQ=$(iwconfig wlp128s20f3 2>/dev/null | grep Frequency | awk '{print $2}' | cut -d':' -f2)
NEW_SIGNAL=$(iwconfig wlp128s20f3 2>/dev/null | grep "Signal level" | awk -F'=' '{print $3}' | awk '{print $1}')
NEW_QUALITY=$(iwconfig wlp128s20f3 2>/dev/null | grep "Link Quality" | awk -F'=' '{print $2}' | awk '{print $1}')
NEW_BSSID=$(iwconfig wlp128s20f3 2>/dev/null | grep "Access Point" | awk '{print $6}')
NEW_SPEED=$(nmcli -f CAPABILITIES.SPEED dev show wlp128s20f3 2>/dev/null | awk '{print $2, $3}')

echo "New Frequency: ${GREEN}${NEW_FREQ}${NC} GHz"
echo "New Signal: ${GREEN}${NEW_SIGNAL}${NC} dBm"
echo "Link Quality: ${GREEN}${NEW_QUALITY}${NC}"
echo "Link Speed: ${GREEN}${NEW_SPEED}${NC}"
echo "New BSSID: ${GREEN}${NEW_BSSID}${NC}"

echo ""

if [[ "$NEW_FREQ" =~ ^5\. ]]; then
    echo -e "${GREEN}✓✓✓ SUCCESS! ✓✓✓${NC}"
    echo ""
    echo "You are now connected to 5 GHz band!"
    echo ""
elif [[ "$NEW_FREQ" =~ ^2\. ]]; then
    echo -e "${YELLOW}⚠ PARTIAL SUCCESS${NC}"
    echo ""
    echo "Still on 2.4 GHz. Possible reasons:"
    echo "  - 5 GHz signal too weak at your location"
    echo "  - Router 5 GHz band disabled"
    echo "  - Interference on 5 GHz band"
    echo ""
    echo "Recommendation: Try moving closer to router"
else
    echo -e "${YELLOW}⚠ UNKNOWN STATUS${NC}"
fi

# Step 6: Performance test
echo "Step 6: Quick Performance Test"
echo "----------------------------------------"
echo "Testing connectivity and latency..."
echo ""

PING_RESULT=$(ping -c 5 -i 0.2 8.8.8.8 2>&1)
PACKET_LOSS=$(echo "$PING_RESULT" | grep -oP '\d+(?=% packet loss)')
AVG_LATENCY=$(echo "$PING_RESULT" | grep -oP 'rtt.*= [\d.]+/\K[\d.]+')

if [ -n "$AVG_LATENCY" ]; then
    echo -e "Average Latency: ${GREEN}${AVG_LATENCY} ms${NC}"
else
    echo -e "Latency: ${YELLOW}Unable to measure${NC}"
fi

if [ "$PACKET_LOSS" -eq 0 ]; then
    echo -e "Packet Loss: ${GREEN}0%${NC}"
else
    echo -e "Packet Loss: ${YELLOW}${PACKET_LOSS}%${NC}"
fi

echo ""

# Summary
echo "================================================"
echo "   Summary"
echo "================================================"
echo ""
echo "Before:"
echo "  Frequency: ${YELLOW}${CURRENT_FREQ}${NC} GHz (2.4 GHz - congested)"
echo "  Signal: ${YELLOW}${CURRENT_SIGNAL}${NC} dBm"
echo ""
echo "After:"
echo "  Frequency: ${GREEN}${NEW_FREQ}${NC} GHz (5 GHz - optimal)"
echo "  Signal: ${GREEN}${NEW_SIGNAL}${NC} dBm"
echo "  Quality: ${GREEN}${NEW_QUALITY}${NC}"
echo "  Speed: ${GREEN}${NEW_SPEED}${NC}"
echo ""

if [[ "$NEW_FREQ" =~ ^5\. ]]; then
    echo "Expected improvements:"
    echo "  ✓ Less interference"
    echo "  ✓ Better real-world speeds (300-500 Mbps)"
    echo "  ✓ Lower latency for gaming/video calls"
    echo "  ✓ More stable connection"
    echo ""
    echo "Your connection is now optimized!"
else
    echo "To revert to automatic band selection:"
    echo "  nmcli connection modify BELL565 802-11-wireless.band \"\""
    echo "  nmcli connection down BELL565 && nmcli connection up BELL565"
fi

echo ""
echo "================================================"
echo "Done!"
echo "================================================"
