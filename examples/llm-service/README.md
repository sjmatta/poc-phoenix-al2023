# Real-World LLM Microservices with Phoenix Observability

A complete example demonstrating Phoenix observability with a realistic LLM-powered Q&A system.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │────│   LLM Service    │────│  Vector Store   │
│  (Port 8080)    │    │  (Port 8000)     │    │  (Port 8001)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  │
                          ┌───────────────┐
                          │    Phoenix    │
                          │ (Port 6006)   │
                          │ Observability │
                          └───────────────┘
```

## Features

### 🔍 **Complete Observability**
- **Automatic tracing** for all HTTP requests, LLM calls, and database operations
- **Custom spans** for business logic (Q&A processing, vector search, confidence calculation)
- **Error tracking** with stack traces and context
- **Performance metrics** including token usage and response times

### 🤖 **Realistic LLM Integration**
- **Q&A Service** with context retrieval and answer generation
- **Vector Search** for finding relevant documents
- **LLM Token Tracking** (prompt tokens, completion tokens, total tokens)
- **Confidence Scoring** based on context quality

### 🛡️ **Production Features**
- **API Gateway** with authentication and rate limiting
- **Health Checks** for all services
- **Error Handling** with proper HTTP status codes
- **CORS Support** for web applications

### 📊 **Phoenix Integration**
- **Service Map** showing request flow between microservices
- **Trace Timeline** with detailed span information
- **LLM Metrics** including model usage and token consumption
- **Error Analysis** for debugging failures

## Quick Start

### 1. Start All Services
```bash
cd examples/llm-service
docker-compose up -d
```

### 2. Wait for Services to Start
```bash
# Check health status
curl http://localhost:8080/health
```

### 3. Test the API
```bash
# Run interactive tests
python test_api.py

# Or test manually
curl -X POST http://localhost:8080/api/v1/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-token" \
  -d '{
    "question": "What is artificial intelligence?",
    "context_limit": 5,
    "temperature": 0.7
  }'
```

### 4. View Traces in Phoenix
Open http://localhost:6006 to see:
- Service dependency graph
- Request traces with timing
- LLM call details and token usage
- Error rates and performance metrics

### 5. Generate Load for Demo
```bash
# Run load test to generate realistic traffic
docker-compose --profile load-test up load-generator
```

## API Endpoints

### API Gateway (Port 8080)
- `GET /health` - Health check with downstream service status
- `POST /api/v1/ask` - Ask a question (main endpoint)
- `GET /api/v1/stats` - Get system statistics
- `GET /api/v1/trace/{trace_id}` - Get trace information

### LLM Service (Port 8000)
- `GET /health` - Health check
- `POST /ask` - Direct Q&A endpoint
- `POST /chat` - OpenAI-compatible chat completion
- `GET /metrics` - Service metrics

### Vector Store (Port 8001)
- `GET /health` - Health check
- `POST /search` - Search similar documents
- `POST /embed` - Generate text embeddings
- `GET /stats` - Vector store statistics

## Example Request Flow

1. **Client** sends question to API Gateway
2. **API Gateway** authenticates request and checks rate limits
3. **LLM Service** receives question and searches for context
4. **Vector Store** performs similarity search and returns relevant documents
5. **LLM Service** generates answer using retrieved context
6. **Response** flows back through gateway with trace information

Each step is automatically traced with Phoenix, showing:
- Request/response timing
- Service dependencies
- LLM token usage
- Vector search metrics
- Error details if any failures occur

## Authentication

The example supports multiple authentication modes:

```bash
# No authentication (allowed)
curl -X POST http://localhost:8080/api/v1/ask -d '{"question": "test"}'

# Demo admin token
curl -H "Authorization: Bearer demo-token" ...

# User tokens
curl -H "Authorization: Bearer user-alice" ...

# Invalid token (401 error)
curl -H "Authorization: Bearer invalid" ...
```

## Observability Features

### 🔍 **Request Tracing**
- Complete request flow from gateway to services
- HTTP method, URL, status codes, response times
- User authentication and client IP tracking

### 🤖 **LLM Observability**
- Model name and parameters (temperature, max_tokens)
- Prompt and completion token counts
- Request/response content and timing
- Error tracking for failed LLM calls

### 📊 **Vector Search Metrics**
- Query text and search parameters
- Number of results and similarity scores
- Embedding generation time
- Search performance metrics

### ⚡ **Performance Monitoring**
- Service response times
- Database query performance
- Memory and CPU usage patterns
- Bottleneck identification

## Phoenix UI Navigation

1. **Service Map**: Visual representation of service dependencies
2. **Traces**: Detailed timeline view of individual requests
3. **Projects**: Filter traces by service or environment
4. **Evaluations**: Analyze LLM response quality (with custom evals)

## Development

### Adding New Services
1. Create service with OpenTelemetry instrumentation
2. Add to `docker-compose.yml`
3. Configure `PHOENIX_ENDPOINT` environment variable
4. Update API Gateway routing if needed

### Custom Spans
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("custom.parameter", value)
    # Your code here
    span.set_attribute("custom.result", result)
```

### Adding Metrics
```python
span.set_attribute("llm.model", "gpt-4")
span.set_attribute("llm.prompt_tokens", 150)
span.set_attribute("llm.completion_tokens", 50)
span.set_attribute("vector.similarity_score", 0.95)
```

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (data will be lost)
docker-compose down -v
```

## Production Considerations

- Replace mock LLM calls with real OpenAI/Azure OpenAI API
- Use production vector database (Pinecone, Weaviate, etc.)
- Implement proper authentication (JWT, OAuth2)
- Add persistent storage for Phoenix data
- Configure alerts and monitoring
- Use secrets management for API keys
- Add horizontal scaling with load balancers