"""
LLM-powered Q&A Service with Phoenix Observability
A real-world example demonstrating automatic tracing of:
- FastAPI endpoints
- LLM calls (OpenAI/mock)
- Vector database operations
- External API calls
"""

import os
import time
import httpx
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
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
    "service.name": "llm-qa-service",
    "service.version": "1.0.0",
    "service.instance.id": "qa-service-1"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()

# Configure OTLP exporter to send to Phoenix
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("PHOENIX_ENDPOINT", "http://phoenix:6006/v1/traces")
)

span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

# Get tracer
tracer = trace.get_tracer(__name__)

# Initialize FastAPI app
app = FastAPI(title="LLM Q&A Service", version="1.0.0")

# Auto-instrument FastAPI and HTTP clients
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()

# Pydantic models
class QuestionRequest(BaseModel):
    question: str
    context_limit: int = 5
    temperature: float = 0.7

class Answer(BaseModel):
    answer: str
    confidence: float
    sources: List[str]
    processing_time_ms: int

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7

# Vector store client
class VectorStoreClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents in vector store"""
        with tracer.start_as_current_span("vector_store.search") as span:
            span.set_attribute("vector_store.query", query)
            span.set_attribute("vector_store.limit", limit)
            span.set_attribute("vector_store.index", "knowledge_base")
            
            try:
                # Simulate vector search with some processing time
                await asyncio.sleep(0.1 + (len(query) * 0.01))  # Realistic latency
                
                # Mock similar documents (in real app, this would hit a vector DB)
                mock_results = [
                    {
                        "content": f"Document about {query[:20]}... with relevant information",
                        "score": 0.95 - (i * 0.1),
                        "metadata": {"source": f"doc_{i+1}.pdf", "page": i+1}
                    }
                    for i in range(min(limit, 3))
                ]
                
                span.set_attribute("vector_store.results_count", len(mock_results))
                span.set_attribute("vector_store.top_score", mock_results[0]["score"] if mock_results else 0)
                
                return mock_results
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

# LLM client with tracing
class LLMClient:
    def __init__(self):
        self.client = httpx.AsyncClient()
        self.model = "gpt-3.5-turbo"
    
    async def generate_answer(self, question: str, context: List[str], temperature: float = 0.7) -> str:
        """Generate answer using LLM with context"""
        with tracer.start_as_current_span("llm.completion") as span:
            # Set LLM-specific attributes
            span.set_attribute("llm.vendor", "openai")
            span.set_attribute("llm.request.model", self.model)
            span.set_attribute("llm.request.temperature", temperature)
            span.set_attribute("llm.request.max_tokens", 500)
            
            # Build prompt
            context_text = "\n".join(context)
            prompt = f"""Context:\n{context_text}\n\nQuestion: {question}\n\nAnswer:"""
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context."},
                {"role": "user", "content": prompt}
            ]
            
            span.set_attribute("llm.request.messages", str(messages))
            
            try:
                # Simulate LLM API call with realistic timing
                start_time = time.time()
                await asyncio.sleep(0.5 + (len(prompt) * 0.001))  # Realistic latency
                
                # Mock LLM response (in real app, this would call OpenAI API)
                answer = f"Based on the provided context, {question.lower().replace('?', '')} can be explained as follows: This is a comprehensive answer that draws from the relevant documents and provides accurate information."
                
                # Set response attributes
                processing_time = time.time() - start_time
                prompt_tokens = len(prompt.split())
                completion_tokens = len(answer.split())
                total_tokens = prompt_tokens + completion_tokens
                
                span.set_attribute("llm.response.model", self.model)
                span.set_attribute("llm.usage.prompt_tokens", prompt_tokens)
                span.set_attribute("llm.usage.completion_tokens", completion_tokens)
                span.set_attribute("llm.usage.total_tokens", total_tokens)
                span.set_attribute("llm.response.finish_reason", "stop")
                span.set_attribute("llm.processing_time_ms", processing_time * 1000)
                
                return answer
                
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise

# Initialize clients
vector_store = VectorStoreClient(os.getenv("VECTOR_STORE_URL", "http://vector-store:8001"))
llm_client = LLMClient()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "llm-qa-service"}

@app.post("/ask", response_model=Answer)
async def ask_question(request: QuestionRequest):
    """Ask a question and get an AI-powered answer with context"""
    with tracer.start_as_current_span("ask_question") as span:
        start_time = time.time()
        
        # Set request attributes
        span.set_attribute("question.text", request.question)
        span.set_attribute("question.context_limit", request.context_limit)
        span.set_attribute("question.temperature", request.temperature)
        
        try:
            # Step 1: Search for relevant context
            with tracer.start_as_current_span("retrieve_context"):
                similar_docs = await vector_store.search_similar(
                    request.question, 
                    limit=request.context_limit
                )
                context = [doc["content"] for doc in similar_docs]
                sources = [doc["metadata"]["source"] for doc in similar_docs]
            
            # Step 2: Generate answer using LLM
            answer_text = await llm_client.generate_answer(
                request.question, 
                context, 
                request.temperature
            )
            
            # Step 3: Calculate confidence based on context quality
            with tracer.start_as_current_span("calculate_confidence"):
                avg_score = sum(doc["score"] for doc in similar_docs) / len(similar_docs) if similar_docs else 0
                confidence = min(avg_score * 1.2, 1.0)  # Boost confidence slightly
                span.set_attribute("confidence.average_score", avg_score)
                span.set_attribute("confidence.final", confidence)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Set response attributes
            span.set_attribute("response.processing_time_ms", processing_time)
            span.set_attribute("response.confidence", confidence)
            span.set_attribute("response.sources_count", len(sources))
            
            return Answer(
                answer=answer_text,
                confidence=confidence,
                sources=sources,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.post("/chat")
async def chat_completion(request: ChatRequest):
    """Chat completion endpoint (simulates OpenAI-compatible API)"""
    with tracer.start_as_current_span("chat_completion") as span:
        span.set_attribute("llm.vendor", "openai")
        span.set_attribute("llm.request.model", request.model)
        span.set_attribute("llm.request.temperature", request.temperature)
        span.set_attribute("llm.request.messages_count", len(request.messages))
        
        try:
            # Simulate processing time
            await asyncio.sleep(0.3)
            
            # Extract last user message
            last_message = request.messages[-1].content if request.messages else ""
            
            # Mock response
            response_content = f"I understand your message: '{last_message[:50]}...' Here's my response based on that."
            
            # Set usage metrics
            prompt_tokens = sum(len(msg.content.split()) for msg in request.messages)
            completion_tokens = len(response_content.split())
            
            span.set_attribute("llm.usage.prompt_tokens", prompt_tokens)
            span.set_attribute("llm.usage.completion_tokens", completion_tokens)
            span.set_attribute("llm.usage.total_tokens", prompt_tokens + completion_tokens)
            
            return {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    """Endpoint to get service metrics"""
    with tracer.start_as_current_span("get_metrics"):
        # In a real app, this would return actual metrics
        return {
            "requests_total": 42,
            "avg_response_time_ms": 750,
            "vector_search_calls": 38,
            "llm_calls": 35,
            "error_rate": 0.02
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)