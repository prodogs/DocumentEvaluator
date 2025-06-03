#!/bin/bash
# Log Viewer for DocumentEvaluator

echo "======================================"
echo "    DocumentEvaluator Log Viewer"
echo "======================================"
echo ""
echo "Available log files:"
echo "1. Server Log (current session)"
echo "2. Application Log"
echo "3. Queue Processor Activity"
echo "4. Error Log (errors only)"
echo "5. Tail All Logs (live)"
echo ""
echo -n "Select option (1-5): "
read option

case $option in
    1)
        echo "=== Server Log (last 50 lines) ==="
        tail -50 /Users/frankfilippis/AI/Github/DocumentEvaluator/server/server.log
        ;;
    2)
        echo "=== Application Log (last 50 lines) ==="
        tail -50 /Users/frankfilippis/AI/Github/DocumentEvaluator/server/app.log
        ;;
    3)
        echo "=== Queue Processor Activity ==="
        grep -a -i -E "(queue|processing|completed|failed)" /Users/frankfilippis/AI/Github/DocumentEvaluator/server/server.log | tail -50
        ;;
    4)
        echo "=== Errors (last 50) ==="
        grep -a -i -E "(error|exception|failed|traceback)" /Users/frankfilippis/AI/Github/DocumentEvaluator/server/server.log | tail -50
        ;;
    5)
        echo "=== Live Log Tail (Ctrl+C to stop) ==="
        tail -f /Users/frankfilippis/AI/Github/DocumentEvaluator/server/server.log | grep -v "GET /api/dashboard"
        ;;
    *)
        echo "Invalid option"
        ;;
esac