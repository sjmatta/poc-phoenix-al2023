#!/usr/bin/env python3
"""
Interactive API Test Script
Test the LLM microservices and view results in Phoenix
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any

API_BASE = "http://localhost:8080/api/v1"

async def test_health_checks():
    """Test health endpoints of all services"""
    print("🏥 Testing Health Endpoints")
    print("=" * 40)
    
    endpoints = {
        "Phoenix": "http://localhost:6006/",
        "API Gateway": "http://localhost:8080/health",
        "LLM Service": "http://localhost:8000/health",
        "Vector Store": "http://localhost:8001/health"
    }
    
    async with httpx.AsyncClient() as client:
        for service, url in endpoints.items():
            try:
                response = await client.get(url, timeout=10.0)
                status = "✅ Healthy" if response.status_code == 200 else f"❌ Status {response.status_code}"
                print(f"{service:15}: {status}")
                
                if response.status_code == 200 and service == "API Gateway":
                    health_data = response.json()
                    downstream = health_data.get("downstream_services", {})
                    for ds_service, ds_health in downstream.items():
                        ds_status = ds_health.get("status", "unknown")
                        print(f"  └─ {ds_service}: {ds_status}")
                        
            except Exception as e:
                print(f"{service:15}: ❌ Error - {str(e)}")
    
    print()

async def test_question_answering():
    """Test the Q&A functionality"""
    print("❓ Testing Question Answering")
    print("=" * 40)
    
    questions = [
        {
            "question": "What is artificial intelligence?",
            "context_limit": 5,
            "temperature": 0.7
        },
        {
            "question": "How does machine learning work?",
            "context_limit": 3,
            "temperature": 0.5
        },
        {
            "question": "Explain Docker containers",
            "context_limit": 4,
            "temperature": 0.8
        }
    ]
    
    async with httpx.AsyncClient() as client:
        for i, question_data in enumerate(questions, 1):
            print(f"\n📝 Question {i}: {question_data['question']}")
            
            try:
                start_time = time.time()
                response = await client.post(
                    f"{API_BASE}/ask",
                    json=question_data,
                    headers={"Authorization": "Bearer demo-token"},
                    timeout=30.0
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ Success (took {response_time:.2f}s)")
                    print(f"   Answer: {result['answer'][:100]}...")
                    print(f"   Confidence: {result['confidence']:.2f}")
                    print(f"   Sources: {len(result['sources'])} documents")
                    print(f"   Processing: {result['processing_time_ms']}ms")
                    
                    if 'gateway_info' in result:
                        gateway_info = result['gateway_info']
                        print(f"   User: {gateway_info.get('user_id', 'unknown')}")
                else:
                    print(f"❌ Error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"❌ Exception: {str(e)}")
            
            # Small delay between requests
            await asyncio.sleep(1)

async def test_vector_search():
    """Test vector search directly"""
    print("\n🔍 Testing Vector Search")
    print("=" * 40)
    
    search_queries = [
        {"query": "machine learning algorithms", "limit": 3},
        {"query": "Python programming", "limit": 2},
        {"query": "container technology", "limit": 4}
    ]
    
    async with httpx.AsyncClient() as client:
        for query_data in search_queries:
            print(f"\n🔎 Searching: {query_data['query']}")
            
            try:
                response = await client.post(
                    "http://localhost:8001/search",
                    json=query_data,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    results = response.json()
                    print(f"✅ Found {len(results)} results")
                    
                    for i, result in enumerate(results, 1):
                        score = result['score']
                        content = result['content'][:80]
                        source = result['metadata']['source']
                        print(f"   {i}. {content}... (score: {score:.3f}, source: {source})")
                else:
                    print(f"❌ Error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"❌ Exception: {str(e)}")

async def test_authentication():
    """Test different authentication scenarios"""
    print("\n🔐 Testing Authentication")
    print("=" * 40)
    
    auth_tests = [
        {"name": "No Auth", "headers": {}},
        {"name": "Demo Token", "headers": {"Authorization": "Bearer demo-token"}},
        {"name": "User Token", "headers": {"Authorization": "Bearer user-alice"}},
        {"name": "Invalid Token", "headers": {"Authorization": "Bearer invalid-token"}}
    ]
    
    test_question = {
        "question": "What is authentication?",
        "context_limit": 3
    }
    
    async with httpx.AsyncClient() as client:
        for auth_test in auth_tests:
            print(f"\n🔑 Testing: {auth_test['name']}")
            
            try:
                response = await client.post(
                    f"{API_BASE}/ask",
                    json=test_question,
                    headers=auth_test["headers"],
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    user_id = result.get('gateway_info', {}).get('user_id', 'unknown')
                    print(f"✅ Success - User: {user_id}")
                elif response.status_code == 401:
                    print("❌ Unauthorized (expected for invalid token)")
                else:
                    print(f"❌ Status: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Exception: {str(e)}")

async def test_rate_limiting():
    """Test rate limiting"""
    print("\n⏱️  Testing Rate Limiting")
    print("=" * 40)
    
    async with httpx.AsyncClient() as client:
        print("Sending multiple rapid requests...")
        
        for i in range(10):
            try:
                response = await client.post(
                    f"{API_BASE}/ask",
                    json={"question": f"Rate limit test {i}"},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    print(f"Request {i+1}: ✅ Success")
                elif response.status_code == 429:
                    print(f"Request {i+1}: ⏱️  Rate limited (expected)")
                    break
                else:
                    print(f"Request {i+1}: ❌ Status {response.status_code}")
                    
            except Exception as e:
                print(f"Request {i+1}: ❌ Exception: {str(e)}")
            
            await asyncio.sleep(0.1)  # Rapid requests

async def get_system_stats():
    """Get system statistics"""
    print("\n📊 System Statistics")
    print("=" * 40)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE}/stats",
                headers={"Authorization": "Bearer demo-token"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                stats = response.json()
                
                print("Gateway Stats:")
                gateway_stats = stats.get('gateway', {})
                for key, value in gateway_stats.items():
                    print(f"  {key}: {value}")
                
                print("\nService Stats:")
                service_stats = stats.get('services', {})
                for service, service_data in service_stats.items():
                    print(f"  {service}:")
                    if isinstance(service_data, dict):
                        for key, value in service_data.items():
                            print(f"    {key}: {value}")
                    else:
                        print(f"    {service_data}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")

def print_phoenix_info():
    """Print Phoenix access information"""
    print("\n🔍 Phoenix Observability")
    print("=" * 40)
    print("Phoenix UI: http://localhost:6006")
    print("- View all traces and spans")
    print("- Monitor service performance")
    print("- Analyze LLM token usage")
    print("- Debug errors and bottlenecks")
    print()
    print("Service Endpoints:")
    print("- API Gateway: http://localhost:8080/health")
    print("- LLM Service: http://localhost:8000/health")
    print("- Vector Store: http://localhost:8001/health")

async def main():
    """Run all tests"""
    print("🚀 Phoenix LLM Service Integration Test")
    print("=" * 50)
    
    # Wait for services
    print("⏳ Waiting for services to start...")
    await asyncio.sleep(5)
    
    # Run tests
    await test_health_checks()
    await test_question_answering()
    await test_vector_search()
    await test_authentication()
    await test_rate_limiting()
    await get_system_stats()
    
    print_phoenix_info()
    
    print("\n✨ All tests completed!")
    print("Check Phoenix UI for detailed traces: http://localhost:6006")

if __name__ == "__main__":
    asyncio.run(main())