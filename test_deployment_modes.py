#!/usr/bin/env python3
"""
Dual Deployment Mode Test Script

This script demonstrates both SaaS and Self-Hosted deployment modes
by testing the different pricing, features, and behaviors.
"""

import os
import requests
import json
import time
from typing import Dict, Any

def test_deployment_mode(base_url: str, mode_name: str):
    """Test a deployment mode"""
    print(f"\n{'='*60}")
    print(f"Testing {mode_name.upper()} Deployment Mode")
    print(f"URL: {base_url}")
    print(f"{'='*60}")
    
    try:
        # Test root endpoint for deployment info
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint accessible")
            print(f"   Message: {data.get('message', 'N/A')}")
            print(f"   Deployment: {data.get('deployment', 'N/A')}")
            
            deployment_info = data.get('deployment_info', {})
            print(f"   Mode: {deployment_info.get('mode', 'N/A')}")
            print(f"   Is SaaS: {deployment_info.get('is_saas', False)}")
            print(f"   Is Self-Hosted: {deployment_info.get('is_self_hosted', False)}")
            
            # SaaS-specific info
            if deployment_info.get('is_saas'):
                free_tier = data.get('free_tier', {})
                print(f"   Free Tier Enabled: {free_tier.get('enabled', False)}")
                print(f"   Max Free Documents: {free_tier.get('max_documents', 0)}")
            
            # Self-hosted specific info  
            if deployment_info.get('is_self_hosted'):
                instance_info = data.get('instance_info', {})
                print(f"   Instance ID: {instance_info.get('instance_id', 'N/A')}")
                print(f"   Instance Name: {instance_info.get('instance_name', 'N/A')}")
                print(f"   Organization: {instance_info.get('organization', 'N/A')}")
                
                license_server = data.get('license_server', {})
                print(f"   License Server: {license_server.get('url', 'N/A')}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
        
        # Test pricing endpoint
        response = requests.get(f"{base_url}/v1/licenses/pricing")
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Pricing endpoint accessible")
            
            deployment_info = data.get('deployment_info', {})
            print(f"   Deployment Mode: {deployment_info.get('deployment_mode', 'N/A')}")
            
            pricing = data.get('pricing', {})
            print(f"   Premium Plans Available:")
            for duration, price in pricing.get('premium', {}).items():
                print(f"     {duration}: ${price}")
            
            print(f"   Extra Premium Plans Available:")
            for duration, price in pricing.get('extra_premium', {}).items():
                print(f"     {duration}: ${price}")
            
            # Show key features
            features = data.get('features_by_plan', {})
            premium_features = features.get('premium', [])
            if premium_features:
                print(f"   Premium Features: {len(premium_features)} features")
                for feature in premium_features[:3]:  # Show first 3
                    print(f"     • {feature}")
                if len(premium_features) > 3:
                    print(f"     ... and {len(premium_features) - 3} more")
        else:
            print(f"❌ Pricing endpoint failed: {response.status_code}")
        
        # Test deployment info endpoint (if available)
        response = requests.get(f"{base_url}/v1/licenses/deployment-info")
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Deployment info endpoint accessible")
            print(f"   Deployment Mode: {data.get('deployment_mode', 'N/A')}")
            print(f"   Instance ID: {data.get('instance_id', 'N/A')}")
            print(f"   Allows Free Tier: {data.get('allows_free_tier', False)}")
            print(f"   Max Free Documents: {data.get('max_free_documents', 0)}")
        elif response.status_code == 404:
            print(f"ℹ️  Deployment info endpoint not available (expected for some modes)")
        else:
            print(f"⚠️  Deployment info endpoint failed: {response.status_code}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {base_url}")
        return False
    except Exception as e:
        print(f"❌ Error testing {mode_name}: {e}")
        return False

def main():
    """Test both deployment modes"""
    print("🚀 Dual Deployment Mode Testing")
    print("This script tests both SaaS and Self-Hosted deployment configurations")
    
    # Test configurations
    test_configs = [
        {
            "name": "Local SaaS Mode",
            "url": "http://127.0.0.1:8000",
            "description": "Testing local instance configured as SaaS"
        },
        {
            "name": "Local Self-Hosted Mode", 
            "url": "http://127.0.0.1:8001",
            "description": "Testing local instance configured as Self-Hosted"
        }
    ]
    
    results = {}
    
    for config in test_configs:
        print(f"\n🔍 {config['description']}")
        success = test_deployment_mode(config['url'], config['name'])
        results[config['name']] = success
        
        if not success:
            print(f"💡 To test {config['name']}, start the server with appropriate configuration:")
            if "SaaS" in config['name']:
                print(f"   DEPLOYMENT_MODE=saas uvicorn app.main:app --port 8000")
            else:
                print(f"   DEPLOYMENT_MODE=self_hosted uvicorn app.main:app --port 8001")
    
    # Summary
    print(f"\n{'='*60}")
    print("DEPLOYMENT MODE TEST SUMMARY")
    print(f"{'='*60}")
    
    for config_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{config_name:30} {status}")
    
    # Recommendations
    print(f"\n💡 DEPLOYMENT RECOMMENDATIONS:")
    print(f"   • SaaS Mode: Best for B2C, subscription business, managed service")
    print(f"   • Self-Hosted: Best for B2B, enterprise, privacy-sensitive customers")
    print(f"   • Dual deployment maximizes market coverage and revenue potential")
    
    if all(results.values()):
        print(f"\n🎉 All deployment modes tested successfully!")
    else:
        print(f"\n⚠️  Some tests failed. Check server configurations and try again.")

if __name__ == "__main__":
    main()
