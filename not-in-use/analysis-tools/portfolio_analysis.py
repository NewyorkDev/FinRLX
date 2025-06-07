#!/usr/bin/env python3
"""
Analyze portfolio_snapshots table structure and data
"""

import requests
import json

def analyze_portfolio_snapshots():
    supabase_url = "https://ttwbilpwrzoizbthembb.supabase.co"
    service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR0d2JpbHB3cnpvaXpidGhlbWJiIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDIxNjc3NCwiZXhwIjoyMDU5NzkyNzc0fQ.thB5A0wjzIO0GXQ9XXLU9tgQDu0MXk3cI4KoOShYlcs"
    
    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    
    print("=== PORTFOLIO_SNAPSHOTS TABLE ANALYSIS ===\n")
    
    # Get sample data
    response = requests.get(
        f"{supabase_url}/rest/v1/portfolio_snapshots?limit=5&order=created_at.desc",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        
        print("SAMPLE RECORDS:")
        for i, record in enumerate(data, 1):
            print(f"\nRecord {i}:")
            print(json.dumps(record, indent=2, default=str))
        
        # Analyze schema
        if data:
            sample = data[0]
            print(f"\n\nSCHEMA ANALYSIS:")
            print("=" * 30)
            for field, value in sample.items():
                value_type = type(value).__name__
                if value is None:
                    value_type = "null/unknown"
                print(f"{field}: {value_type}")
                if value is not None and len(str(value)) < 100:
                    print(f"  Sample: {value}")
                elif value is not None:
                    print(f"  Sample: {str(value)[:100]}...")
    
    else:
        print(f"Error accessing portfolio_snapshots: {response.status_code}")

if __name__ == "__main__":
    analyze_portfolio_snapshots()