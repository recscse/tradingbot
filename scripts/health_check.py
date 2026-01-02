import sys
import requests
import time
import os

def check_health(url, retries=5, delay=10):
    print(f"🏥 Checking health for {url}...")
    
    for i in range(retries):
        try:
            response = requests.get(f"{url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed! Status: {data.get('status')}")
                print(f"   Architecture: {data.get('architecture')}")
                return True
            else:
                print(f"⚠️ Attempt {i+1}/{retries}: Health check failed with status {response.status_code}")
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
