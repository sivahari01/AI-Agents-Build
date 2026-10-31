# Python packages used by this project

## AI and agent frameworks

### langchain
Builds LLM applications using prompts, chains, tools, models, parsers, and retrieval workflows.

### langchain-core
Provides LangChain's core abstractions, including messages, prompts, tools, runnable components, and output parsing.

### langchain-openai
Connects LangChain applications to OpenAI models and OpenAI-compatible API endpoints.

### langchain-anthropic
Connects LangChain applications to Anthropic Claude models.

### langchain-google-genai
Connects LangChain applications to Google Gemini models.

### langgraph
Creates stateful AI agents and workflows with nodes, edges, memory, branching, and loops.

### langgraph-checkpoint
Saves and restores LangGraph workflow or conversation checkpoints.

## Web APIs and servers

### fastapi
Creates REST APIs with automatic validation, documentation, and asynchronous request handling.

### uvicorn
Runs FastAPI and other ASGI Python web applications.

### python-multipart
Processes uploaded files and multipart form data in FastAPI or Starlette applications.

### flask
Creates lightweight Python web applications and REST endpoints.

### flask-cors
Enables browser-based applications to call Flask APIs from different origins.

## HTTP and networking

### requests
Sends synchronous HTTP requests and processes JSON responses. It is used to call the local Ollama API.

### httpx
Sends synchronous or asynchronous HTTP requests; modern frameworks use it internally for API communication.

### aiohttp
Makes asynchronous HTTP requests and can host asynchronous HTTP services.

### anyio
Provides cross-framework asynchronous task, networking, and concurrency support.

### httpcore
Low-level HTTP transport used by HTTP client libraries such as HTTPX.

### h11
HTTP/1 protocol implementation used by HTTP server and client infrastructure.

## Configuration and data validation

### pydantic
Defines structured Python data models and validates API, configuration, and function input data.

### python-dotenv
Loads environment variables, such as tokens and service URLs, from a `.env` file.

### pyyaml
Reads and writes YAML configuration files.

### ijson
Reads large JSON files incrementally instead of loading the entire file into memory.

### typing_extensions
Adds typing features that are supported by specific Python versions or type-checking tools.

## AI retrieval and machine learning

### chromadb
Stores document embeddings and performs similarity searches for retrieval-augmented generation (RAG).

### numpy
Provides fast numeric arrays and vector/matrix calculations used by data and ML libraries.

### scipy
Provides scientific and numerical functions, including statistics, optimization, integration, and linear algebra.

### scikit-learn
Provides machine learning algorithms, preprocessing tools, clustering, classification, and performance evaluation utilities.

## Document and spreadsheet processing

### python-docx
Reads, creates, and edits Microsoft Word `.docx` documents.

### openpyxl
Reads and writes Microsoft Excel `.xlsx` workbooks, worksheets, formulas, and formatted cells.

### python-pptx
Reads, creates, and edits Microsoft PowerPoint `.pptx` presentations.

## Visualization and terminal output

### matplotlib
Creates charts and graphs such as response-time trends, throughput plots, and error-rate dashboards.

### rich
Displays formatted text, tables, progress bars, tracebacks, and colors in the terminal.

## Reliability and infrastructure

### tenacity
Retries failed operations with configurable delays, attempts, and retry conditions.

### redis
Connects Python applications to Redis for caching, queues, sessions, or shared agent state.

### opentelemetry-api
Adds tracing and telemetry APIs for monitoring application performance and agent workflows.

### certifi
Provides a maintained collection of trusted SSL/TLS certificates for secure HTTPS connections.

### idna
Converts and validates internationalized domain names used in network connections.

## Directly useful project packages

For the local performance-test analyzer, learn these first:

1. `requests` — call the Ollama API.
2. `numpy` — calculate numeric metrics.
3. `scikit-learn` — detect patterns and anomalies in test results.
4. `matplotlib` — visualize test metrics.
5. `chromadb` — retrieve relevant reports and documentation.
6. `fastapi` — expose analyzer functions through an API.
7. `pydantic` — validate analysis requests and result structures.
8. `python-dotenv` — manage configuration outside source code.
9. `langgraph` — coordinate multi-step analysis agents.
10. `python-docx`, `openpyxl`, or `python-pptx` — generate reports in those formats.
