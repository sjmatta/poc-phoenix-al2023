import time
import random
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode

# Configure the tracer provider
resource = Resource.create({
    "service.name": "test-llm-application",
    "service.version": "1.0.0"
})

# Set up the tracer provider
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()

# Configure OTLP exporter to send to Phoenix
otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:6006/v1/traces",
    headers={}
)

# Add the exporter to the tracer provider
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

# Get a tracer
tracer = trace.get_tracer("test-tracer")

def simulate_llm_calls():
    """Simulate LLM application traces"""
    
    # Simulate a chat completion
    with tracer.start_as_current_span("chat.completion") as span:
        span.set_attribute("llm.vendor", "openai")
        span.set_attribute("llm.request.model", "gpt-3.5-turbo")
        span.set_attribute("llm.request.messages", str([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ]))
        
        # Simulate processing time
        time.sleep(random.uniform(0.5, 2.0))
        
        # Set response attributes
        span.set_attribute("llm.response.model", "gpt-3.5-turbo-0613")
        span.set_attribute("llm.usage.total_tokens", 150)
        span.set_attribute("llm.usage.prompt_tokens", 50)
        span.set_attribute("llm.usage.completion_tokens", 100)
        span.set_attribute("llm.response.choices", str([
            {"message": {"role": "assistant", "content": "The capital of France is Paris."}}
        ]))
        
    # Simulate a retrieval operation
    with tracer.start_as_current_span("retrieval.query") as span:
        span.set_attribute("retrieval.query", "capital of France")
        span.set_attribute("retrieval.k", 5)
        
        # Simulate vector search
        with tracer.start_as_current_span("vector.search") as search_span:
            search_span.set_attribute("vector.database", "pinecone")
            search_span.set_attribute("vector.index", "knowledge-base")
            time.sleep(random.uniform(0.1, 0.5))
            search_span.set_attribute("vector.results.count", 5)
        
        span.set_attribute("retrieval.documents", str([
            {"content": "Paris is the capital of France", "score": 0.95},
            {"content": "France is a country in Europe", "score": 0.75}
        ]))
    
    # Simulate an embedding operation
    with tracer.start_as_current_span("embedding.create") as span:
        span.set_attribute("embedding.model", "text-embedding-ada-002")
        span.set_attribute("embedding.input", "What is the capital of France?")
        time.sleep(random.uniform(0.1, 0.3))
        span.set_attribute("embedding.dimension", 1536)
        span.set_attribute("embedding.tokens", 8)

def simulate_error_trace():
    """Simulate an error trace"""
    with tracer.start_as_current_span("chat.completion.error") as span:
        span.set_attribute("llm.vendor", "openai")
        span.set_attribute("llm.request.model", "gpt-4")
        span.set_attribute("error", True)
        span.set_status(Status(StatusCode.ERROR, "Rate limit exceeded"))
        span.record_exception(Exception("Rate limit exceeded"))

if __name__ == "__main__":
    print("Sending telemetry data to Phoenix...")
    
    # Send multiple traces
    for i in range(5):
        print(f"Sending trace batch {i+1}/5")
        simulate_llm_calls()
        
        # Occasionally simulate an error
        if i == 2:
            simulate_error_trace()
        
        time.sleep(1)
    
    # Force flush to ensure all spans are sent
    tracer_provider.force_flush()
    
    print("Telemetry data sent successfully!")
    print("Check Phoenix UI at http://localhost:6006")