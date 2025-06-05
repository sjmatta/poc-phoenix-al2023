"""
Mock Vector Store Service
Simulates a vector database with realistic behavior and tracing
"""

import os
import time
import asyncio
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# Configure OpenTelemetry
resource = Resource.create({
    "service.name": "vector-store-service",
    "service.version": "1.0.0",
    "service.instance.id": "vector-store-1"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()

otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("PHOENIX_ENDPOINT", "http://phoenix:6006/v1/traces")
)

span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

tracer = trace.get_tracer(__name__)

app = FastAPI(title="Vector Store Service", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)

# Mock document database
MOCK_DOCUMENTS = [
    {
        "id": "doc_1",
        "content": "Artificial Intelligence (AI) is a branch of computer science that aims to create intelligent machines. It includes machine learning, deep learning, and neural networks.",
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],  # Mock embedding
        "metadata": {"source": "ai_handbook.pdf", "page": 1, "category": "technology"}
    },
    {
        "id": "doc_2", 
        "content": "Machine learning is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed. It uses algorithms to find patterns in data.",
        "embedding": [0.2, 0.3, 0.4, 0.5, 0.6],
        "metadata": {"source": "ml_guide.pdf", "page": 5, "category": "technology"}
    },
    {
        "id": "doc_3",
        "content": "Python is a high-level programming language known for its simplicity and readability. It's widely used in data science, web development, and automation.",
        "embedding": [0.3, 0.4, 0.5, 0.6, 0.7],
        "metadata": {"source": "python_tutorial.pdf", "page": 2, "category": "programming"}
    },
    {
        "id": "doc_4",
        "content": "Docker is a containerization platform that allows developers to package applications and their dependencies into lightweight, portable containers.",
        "embedding": [0.4, 0.5, 0.6, 0.7, 0.8],
        "metadata": {"source": "docker_docs.pdf", "page": 1, "category": "devops"}
    },
    {
        "id": "doc_5",
        "content": "Kubernetes is an open-source container orchestration platform for automating deployment, scaling, and management of containerized applications.",
        "embedding": [0.5, 0.6, 0.7, 0.8, 0.9],
        "metadata": {"source": "k8s_manual.pdf", "page": 3, "category": "devops"}
    }
]

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    threshold: float = 0.5

class Document(BaseModel):
    content: str
    score: float
    metadata: Dict[str, Any]

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

def mock_embed_text(text: str) -> List[float]:
    """Generate a mock embedding for text based on content"""
    # Simple hash-based mock embedding
    import hashlib
    hash_obj = hashlib.md5(text.lower().encode())
    hash_bytes = hash_obj.digest()[:5]  # Take first 5 bytes
    return [b / 255.0 for b in hash_bytes]  # Normalize to 0-1

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "vector-store"}

@app.post("/search", response_model=List[Document])
async def search_similar(request: SearchRequest):
    """Search for similar documents"""
    with tracer.start_as_current_span("vector_search") as span:
        span.set_attribute("search.query", request.query)
        span.set_attribute("search.limit", request.limit)
        span.set_attribute("search.threshold", request.threshold)
        
        try:
            # Step 1: Generate embedding for query
            with tracer.start_as_current_span("embed_query") as embed_span:
                start_time = time.time()
                query_embedding = mock_embed_text(request.query)
                embed_time = time.time() - start_time
                
                embed_span.set_attribute("embedding.dimensions", len(query_embedding))
                embed_span.set_attribute("embedding.time_ms", embed_time * 1000)
            
            # Step 2: Search through documents
            with tracer.start_as_current_span("similarity_search") as search_span:
                start_time = time.time()
                
                results = []
                for doc in MOCK_DOCUMENTS:
                    # Calculate similarity
                    score = cosine_similarity(query_embedding, doc["embedding"])
                    
                    # Simple text matching boost for more realistic results
                    query_words = set(request.query.lower().split())
                    doc_words = set(doc["content"].lower().split())
                    text_overlap = len(query_words.intersection(doc_words)) / len(query_words) if query_words else 0
                    
                    # Combine embedding similarity with text overlap
                    final_score = (score * 0.7) + (text_overlap * 0.3)
                    
                    if final_score >= request.threshold:
                        results.append({
                            "content": doc["content"],
                            "score": final_score,
                            "metadata": doc["metadata"]
                        })
                
                # Sort by score and limit results
                results.sort(key=lambda x: x["score"], reverse=True)
                results = results[:request.limit]
                
                search_time = time.time() - start_time
                search_span.set_attribute("search.candidates_count", len(MOCK_DOCUMENTS))
                search_span.set_attribute("search.results_count", len(results))
                search_span.set_attribute("search.time_ms", search_time * 1000)
                search_span.set_attribute("search.top_score", results[0]["score"] if results else 0)
            
            # Simulate realistic processing time
            await asyncio.sleep(0.05 + len(request.query) * 0.001)
            
            span.set_attribute("response.results_count", len(results))
            span.set_attribute("response.total_time_ms", (embed_time + search_time) * 1000)
            
            return [Document(**result) for result in results]
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/embed")
async def embed_text(text: str):
    """Generate embedding for text"""
    with tracer.start_as_current_span("embed_text") as span:
        span.set_attribute("embedding.input_length", len(text))
        
        try:
            # Simulate embedding generation time
            await asyncio.sleep(0.02 + len(text) * 0.0001)
            
            embedding = mock_embed_text(text)
            
            span.set_attribute("embedding.dimensions", len(embedding))
            span.set_attribute("embedding.model", "mock-embeddings-v1")
            
            return {
                "embedding": embedding,
                "model": "mock-embeddings-v1",
                "dimensions": len(embedding)
            }
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get vector store statistics"""
    with tracer.start_as_current_span("get_stats"):
        return {
            "total_documents": len(MOCK_DOCUMENTS),
            "index_size_mb": 2.5,
            "last_updated": "2025-06-05T00:00:00Z",
            "search_requests_today": 156
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)