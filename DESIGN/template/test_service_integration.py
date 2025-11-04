import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from terminate_service_manager import start_terminate_service, get_terminate_service

print("="*60)
print("Test Terminate Service Integration")
print("="*60)

print("\n[Test 1] Import terminate service manager...")
try:
    from terminate_service_manager import start_terminate_service, get_terminate_service
    print("[Success] Terminate service manager imported")
except ImportError as e:
    print(f"[Failed] Import failed: {e}")
    sys.exit(1)

print("\n[Test 2] Start terminate service...")
if start_terminate_service(port=8081):
    print("[Success] Terminate service started on port 8081")
    print(f"[Current PID] {os.getpid()}")
else:
    print("[Failed] Failed to start terminate service")
    sys.exit(1)

print("\n[Test 3] Get service instance...")
service = get_terminate_service()
if service:
    print(f"[Success] Service instance obtained, port: {service.port}")
else:
    print("[Failed] Cannot get service instance")

print("\n[Test 4] Simulate algorithm running...")
print("Algorithm running...")
import time
for i in range(5):
    print(f"Iteration {i+1}/5")
    time.sleep(1)

print("\n[Test 5] Show request logs...")
service.print_logs()

print("\n[Complete] Test successful!")
print("="*60)

