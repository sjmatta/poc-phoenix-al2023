"""
Load Test Script
Generates realistic traffic to demonstrate Phoenix observability
"""

import asyncio
import httpx
import random
import time
from typing import List

# Sample questions for realistic testing
SAMPLE_QUESTIONS = [
    "What is artificial intelligence and how does it work?",
    "Explain machine learning algorithms",
    "How do I get started with Python programming?",
    "What are the benefits of using Docker containers?",
    "How does Kubernetes help with container orchestration?",
    "What is the difference between supervised and unsupervised learning?",
    "How do neural networks process information?",
    "What are the best practices for API design?",
    "How do I implement authentication in web applications?",
    "What is the role of databases in modern applications?",
    "How do microservices communicate with each other?",
    "What are the advantages of using cloud computing?",
    "How do I optimize application performance?",
    "What is DevOps and why is it important?",
    "How do I secure my web application?"
]

# Different user scenarios
USER_SCENARIOS = [
    {"auth": None, "questions_per_session": 3, "delay_range": (1, 3)},
    {"auth": "Bearer demo-token", "questions_per_session": 5, "delay_range": (0.5, 2)},
    {"auth": "Bearer user-alice", "questions_per_session": 2, "delay_range": (2, 5)},
    {"auth": "Bearer user-bob", "questions_per_session": 4, "delay_range": (1, 4)},
]

async def simulate_user_session(client: httpx.AsyncClient, scenario: dict, session_id: int):
    """Simulate a user session with multiple questions"""
    print(f"[Session {session_id}] Starting user session...")
    
    headers = {}
    if scenario["auth"]:
        headers["Authorization"] = scenario["auth"]
    
    questions_asked = 0
    successful_requests = 0
    
    for i in range(scenario["questions_per_session"]):
        try:
            # Select a random question
            question = random.choice(SAMPLE_QUESTIONS)
            
            # Add some variation to request parameters
            request_data = {
                "question": question,
                "context_limit": random.randint(3, 7),
                "temperature": round(random.uniform(0.3, 0.9), 1)
            }
            
            print(f"[Session {session_id}] Asking: {question[:50]}...")
            
            # Make the request
            start_time = time.time()
            response = await client.post(
                "http://api-gateway:8080/api/v1/ask",
                json=request_data,
                headers=headers,
                timeout=30.0
            )
            response_time = time.time() - start_time
            
            questions_asked += 1
            
            if response.status_code == 200:
                successful_requests += 1
                result = response.json()
                confidence = result.get("confidence", 0)
                processing_time = result.get("processing_time_ms", 0)
                
                print(f"[Session {session_id}] ✅ Response received (confidence: {confidence:.2f}, "
                      f"processing: {processing_time}ms, total: {response_time*1000:.0f}ms)")
            else:
                print(f"[Session {session_id}] ❌ Error: {response.status_code} - {response.text}")
            
            # Wait before next question
            if i < scenario["questions_per_session"] - 1:
                delay = random.uniform(*scenario["delay_range"])
                await asyncio.sleep(delay)
                
        except Exception as e:
            print(f"[Session {session_id}] ❌ Exception: {str(e)}")
    
    print(f"[Session {session_id}] Session complete: {successful_requests}/{questions_asked} successful")
    return {"session_id": session_id, "successful": successful_requests, "total": questions_asked}

async def generate_error_scenarios(client: httpx.AsyncClient):
    """Generate some error scenarios for testing"""
    print("\n🔥 Generating error scenarios...")
    
    # Rate limiting test
    print("Testing rate limiting...")
    for i in range(5):
        try:
            response = await client.post(
                "http://api-gateway:8080/api/v1/ask",
                json={"question": f"Rate limit test {i}"},
                timeout=5.0
            )
            if response.status_code == 429:
                print("✅ Rate limiting triggered")
                break
        except Exception:
            pass
        await asyncio.sleep(0.1)
    
    # Invalid request test
    print("Testing invalid requests...")
    try:
        response = await client.post(
            "http://api-gateway:8080/api/v1/ask",
            json={"invalid": "request"},
            timeout=5.0
        )
        print(f"Invalid request response: {response.status_code}")
    except Exception as e:
        print(f"Invalid request error: {e}")

async def check_services_health(client: httpx.AsyncClient):
    """Check health of all services"""
    services = {
        "Phoenix": "http://phoenix:6006/",
        "API Gateway": "http://api-gateway:8080/health",
        "LLM Service": "http://llm-service:8000/health", 
        "Vector Store": "http://vector-store:8001/health"
    }
    
    print("🏥 Checking service health...")
    for service_name, url in services.items():
        try:
            response = await client.get(url, timeout=10.0)
            status = "✅ Healthy" if response.status_code == 200 else f"❌ Status {response.status_code}"
            print(f"  {service_name}: {status}")
        except Exception as e:
            print(f"  {service_name}: ❌ Error - {str(e)}")

async def get_statistics(client: httpx.AsyncClient):
    """Get system statistics"""
    print("\n📊 Getting system statistics...")
    try:
        response = await client.get("http://api-gateway:8080/api/v1/stats", timeout=10.0)
        if response.status_code == 200:
            stats = response.json()
            print(f"Gateway stats: {stats.get('gateway', {})}")
            print(f"Service stats available: {list(stats.get('services', {}).keys())}")
        else:
            print(f"Failed to get stats: {response.status_code}")
    except Exception as e:
        print(f"Error getting stats: {e}")

async def main():
    """Main load testing function"""
    print("🚀 Starting Phoenix LLM Service Load Test")
    print("=" * 50)
    
    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    await asyncio.sleep(10)
    
    async with httpx.AsyncClient() as client:
        # Check service health
        await check_services_health(client)
        await asyncio.sleep(2)
        
        # Generate normal user traffic
        print(f"\n👥 Simulating {len(USER_SCENARIOS)} concurrent user sessions...")
        
        # Create concurrent user sessions
        tasks = []
        for i, scenario in enumerate(USER_SCENARIOS):
            task = simulate_user_session(client, scenario, i + 1)
            tasks.append(task)
        
        # Run sessions concurrently
        session_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Print session summary
        print("\n📈 Session Summary:")
        total_successful = 0
        total_requests = 0
        
        for result in session_results:
            if isinstance(result, dict):
                total_successful += result["successful"]
                total_requests += result["total"]
                print(f"  Session {result['session_id']}: {result['successful']}/{result['total']}")
        
        success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        print(f"\n✨ Overall Success Rate: {success_rate:.1f}% ({total_successful}/{total_requests})")
        
        # Generate some error scenarios
        await asyncio.sleep(2)
        await generate_error_scenarios(client)
        
        # Get final statistics
        await asyncio.sleep(2)
        await get_statistics(client)
        
        print("\n🎉 Load test complete!")
        print("🔍 View traces and metrics in Phoenix: http://localhost:6006")
        print("📊 API Gateway health: http://localhost:8080/health")

if __name__ == "__main__":
    asyncio.run(main())