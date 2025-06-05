"""
API Gateway Service
Routes requests and adds authentication, rate limiting, and observability
"""

import os
import time
import httpx
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": "api-gateway",
    "service.version": "1.0.0",
    "service.instance.id": "gateway-1"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()

otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("PHOENIX_ENDPOINT", "http://phoenix:6006/v1/traces")
)

span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

tracer = trace.get_tracer(__name__)

app = FastAPI(title="API Gateway", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-instrument
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()

# Services configuration
SERVICES = {
    "llm-service": os.getenv("LLM_SERVICE_URL", "http://llm-service:8000"),
    "vector-store": os.getenv("VECTOR_STORE_URL", "http://vector-store:8001")
}

# HTTP client for service communication
http_client = httpx.AsyncClient(timeout=30.0)

# Simple auth
security = HTTPBearer(auto_error=False)

# Rate limiting storage (in-memory for demo)
request_counts: Dict[str, Dict[str, int]] = {}

class QuestionRequest(BaseModel):
    question: str
    context_limit: int = 5
    temperature: float = 0.7

async def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def check_rate_limit(client_ip: str, limit: int = 100) -> bool:
    """Simple rate limiting check"""
    current_time = int(time.time() / 60)  # Per minute
    
    if client_ip not in request_counts:
        request_counts[client_ip] = {}
    
    if current_time not in request_counts[client_ip]:
        request_counts[client_ip][current_time] = 0
    
    request_counts[client_ip][current_time] += 1
    
    # Clean old entries
    cutoff = current_time - 5  # Keep last 5 minutes
    for ip in request_counts:
        for timestamp in list(request_counts[ip].keys()):
            if timestamp < cutoff:
                del request_counts[ip][timestamp]
    
    return request_counts[client_ip][current_time] <= limit

async def authenticate(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Simple authentication check"""
    if not credentials:
        # For demo, allow unauthenticated requests
        return {"user_id": "anonymous", "role": "user"}
    
    # In real implementation, validate JWT token
    token = credentials.credentials
    if token == "demo-token":
        return {"user_id": "demo-user", "role": "admin"}
    elif token.startswith("user-"):
        return {"user_id": token, "role": "user"}
    else:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

@app.middleware("http")
async def add_trace_headers(request: Request, call_next):
    """Add tracing context to all requests"""
    start_time = time.time()
    
    # Get current span and add request info
    current_span = trace.get_current_span()
    if current_span:
        current_span.set_attribute("http.method", request.method)
        current_span.set_attribute("http.url", str(request.url))
        current_span.set_attribute("http.user_agent", request.headers.get("user-agent", ""))
        current_span.set_attribute("client.ip", await get_client_ip(request))
    
    response = await call_next(request)
    
    # Add response info
    processing_time = time.time() - start_time
    if current_span:
        current_span.set_attribute("http.status_code", response.status_code)
        current_span.set_attribute("http.response_time_ms", processing_time * 1000)
    
    response.headers["X-Response-Time"] = str(processing_time)
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    with tracer.start_as_current_span("health_check"):
        # Check downstream services
        service_health = {}
        
        for service_name, service_url in SERVICES.items():
            try:
                response = await http_client.get(f"{service_url}/health", timeout=5.0)
                service_health[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            except Exception as e:
                service_health[service_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        overall_status = "healthy" if all(
            service["status"] == "healthy" for service in service_health.values()
        ) else "degraded"
        
        return {
            "status": overall_status,
            "service": "api-gateway",
            "downstream_services": service_health
        }

@app.post("/api/v1/ask")
async def ask_question(
    request: QuestionRequest,
    req: Request,
    user: Dict[str, Any] = Depends(authenticate)
):
    """Ask a question via the LLM service"""
    with tracer.start_as_current_span("gateway.ask_question") as span:
        # Set user context
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("user.role", user["role"])
        span.set_attribute("question.text", request.question)
        
        # Rate limiting
        client_ip = await get_client_ip(req)
        if not await check_rate_limit(client_ip):
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Rate limit exceeded"))
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        try:
            # Forward request to LLM service
            with tracer.start_as_current_span("forward_to_llm_service") as forward_span:
                response = await http_client.post(
                    f"{SERVICES['llm-service']}/ask",
                    json=request.dict(),
                    headers={"X-User-ID": user["user_id"]}
                )
                
                forward_span.set_attribute("downstream.service", "llm-service")
                forward_span.set_attribute("downstream.status_code", response.status_code)
                forward_span.set_attribute("downstream.response_time_ms", 
                                         response.elapsed.total_seconds() * 1000)
                
                if response.status_code != 200:
                    forward_span.set_status(trace.Status(trace.StatusCode.ERROR, 
                                                       f"HTTP {response.status_code}"))
                    raise HTTPException(status_code=response.status_code, 
                                      detail=response.text)
                
                result = response.json()
                
                # Add gateway metadata
                result["gateway_info"] = {
                    "user_id": user["user_id"],
                    "client_ip": client_ip,
                    "request_timestamp": time.time()
                }
                
                span.set_attribute("response.confidence", result.get("confidence", 0))
                span.set_attribute("response.processing_time_ms", 
                                 result.get("processing_time_ms", 0))
                
                return result
                
        except httpx.RequestError as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(status_code=503, detail="LLM service unavailable")
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/stats")
async def get_gateway_stats(user: Dict[str, Any] = Depends(authenticate)):
    """Get API gateway statistics"""
    with tracer.start_as_current_span("gateway.get_stats") as span:
        span.set_attribute("user.id", user["user_id"])
        
        # Calculate basic stats
        total_requests = sum(
            sum(counts.values()) for counts in request_counts.values()
        )
        
        active_clients = len(request_counts)
        
        # Get downstream service stats
        service_stats = {}
        for service_name, service_url in SERVICES.items():
            try:
                if service_name == "llm-service":
                    response = await http_client.get(f"{service_url}/metrics")
                    if response.status_code == 200:
                        service_stats[service_name] = response.json()
                elif service_name == "vector-store":
                    response = await http_client.get(f"{service_url}/stats")
                    if response.status_code == 200:
                        service_stats[service_name] = response.json()
            except Exception:
                service_stats[service_name] = {"status": "unavailable"}
        
        return {
            "gateway": {
                "total_requests": total_requests,
                "active_clients": active_clients,
                "rate_limits_active": bool(request_counts)
            },
            "services": service_stats
        }

@app.get("/api/v1/trace/{trace_id}")
async def get_trace(trace_id: str, user: Dict[str, Any] = Depends(authenticate)):
    """Get trace information (would typically query Phoenix)"""
    with tracer.start_as_current_span("gateway.get_trace") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("trace.id", trace_id)
        
        # In a real implementation, this would query Phoenix API
        return {
            "trace_id": trace_id,
            "status": "completed",
            "duration_ms": 1250,
            "spans": 8,
            "services": ["api-gateway", "llm-service", "vector-store"],
            "phoenix_url": f"http://localhost:6006/traces/{trace_id}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)