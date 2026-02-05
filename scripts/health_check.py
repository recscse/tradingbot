import sys
import requests
import time
import os

def check_health(url, retries=5, delay=5):
    print(f"≡ƒÅÑ Checking comprehensive system health for {url}...")
    
    for i in range(retries):
        try:
            # 1. Base Health Check
            response = requests.get(f"{url}/api/v1/system/status", timeout=10) # Using your existing system health router
            if response.status_code == 200:
                data = response.json()
                
                print("\nΓ£à SYSTEM STATUS:")
                print(f"   ΓùÅ Overall:    {data.get('status', 'Unknown')}")
                
                # 2. Database & Redis
                db = data.get('database', {})
                redis = data.get('redis', {})
                print(f"   ΓùÅ Database:   {'Γ£à Connected' if db.get('status') == 'connected' else 'Γ¥î Disconnected'}")
                print(f"   ΓùÅ Redis:      {'Γ£à Connected' if redis.get('status') == 'connected' else 'Γ¥î Disconnected'}")
                
                # 3. Services
                services = data.get('services', {})
                print("\n≡ƒôª ACTIVE SERVICES:")
                for s_name, s_data in services.items():
                    status_icon = "Γ£à" if s_data.get('is_running') else "ΓÅ║"
                    print(f"   {status_icon} {s_name:<20} [Mode: {s_data.get('trading_mode', 'N/A')}]")
                
                # 4. System Metrics
                system = data.get('system', {})
                print("\n≡ƒôê SYSTEM METRICS:")
                print(f"   ΓùÅ CPU Usage:  {system.get('cpu_percent')}%")
                print(f"   ΓùÅ Memory:     {system.get('memory_percent')}%")
                
                return True
            else:
                # Fallback to base /health if system router not fully up
                base_resp = requests.get(f"{url}/health", timeout=5)
                if base_resp.status_code == 200:
                    print("Γ£à Basic server is UP (System Status API still warming up)")
                    return True
                print(f"ΓÜá∩╕Å Attempt {i+1}/{retries}: Status {response.status_code}")

        except Exception as e:
            print(f"⚠️ Attempt {i+1}/{retries}: Connection failed - {str(e)}")
        
        if i < retries - 1:
            print(f"⏳ Waiting {delay}s before retry...")
            time.sleep(delay)
            
    print("❌ All health check attempts failed")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python health_check.py <base_url>")
        sys.exit(1)
        
    url = sys.argv[1].rstrip('/')
    if check_health(url):
        sys.exit(0)
    else:
        sys.exit(1)
