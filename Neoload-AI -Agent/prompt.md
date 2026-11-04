# Project: PerfAI – AI-Powered Performance Testing Analysis Agent

## 1. Role

Act as a Senior Python Developer, AI Engineer, Performance Testing Engineer and UI/UX Designer.

Help me build a local AI-powered Performance Testing Analysis Agent called **PerfAI**. I am a beginner in AI development, but I have experience in performance testing. Explain the implementation clearly and use simple, maintainable code. Do not overcomplicate the architecture.

## 2. Project Objective

Build a local AI agent that automatically analyzes performance testing reports, test results, server logs, CPU and memory metrics, and monitoring screenshots.

When I upload a report or ask a question about uploaded data, the application should:
1. Identify the input file type.
2. Extract relevant performance data.
3. Analyze performance metrics.
4. Identify potential bottlenecks.
5. Investigate possible root causes.
6. Recommend corrective actions.
7. Answer questions using the uploaded data.

The application should behave like an experienced Senior Performance Test Engineer.

## 3. Technology Stack

- Programming: Python
- Frontend: Streamlit
- AI runtime: Ollama
- AI model: Qwen (choose a lightweight model suitable for 16 GB RAM and CPU-only execution)
- Data processing: Pandas
- HTML parsing: BeautifulSoup
- Charts: Plotly
- Storage: Local JSON files
- File processing: Python standard libraries and suitable parsing libraries

All AI processing should run locally through Ollama. Do not require OpenAI API keys or paid cloud AI services.

## 4. Input File Support

### Performance testing reports
- NeoLoad HTML reports
- NeoLoad ZIP report packages
- JMeter CSV reports
- Excel files
- JSON reports

### Server logs
- Application logs
- NGINX logs
- Apache logs
- Tomcat logs
- Java exception logs
- Error and warning logs

### Infrastructure metrics
- CPU utilization
- Memory utilization
- Disk utilization
- Network utilization
- Database metrics
- Prometheus metric exports

### Images
- Grafana dashboards
- CPU and memory monitoring screenshots
- Performance testing graphs

For images, use a compatible local vision model through Ollama when supported. Do not assume a text-only model can interpret images.

## 5. NeoLoad Report Analysis – Primary Feature

This is the first and most important feature. My NeoLoad HTML reports follow a consistent structure.

When I upload a NeoLoad HTML report or ZIP package, automatically extract and analyze:

### Test execution information
- Scenario name
- Test start time and end time
- Test duration
- Total, average and maximum virtual users
- Total, completed and failed iterations

### Transaction analysis
- Transaction names
- Total transaction executions
- Average, minimum and maximum response time
- P90, P95 and P99
- Transaction success and failure counts
- Transaction error percentage

### TPS and throughput analysis
- Overall TPS
- Transaction-wise TPS
- Requests per second
- Throughput over time
- Peak and average TPS
- TPS trends during ramp-up and ramp-down

### Error analysis
- Total errors and error percentage
- HTTP 4xx and 5xx errors
- Assertion failures
- Timeout errors
- Connection errors
- Error distribution by transaction
- Error trends over time

### Performance observations
- Slowest transactions
- Transactions breaching SLA
- Response time degradation
- TPS degradation
- Error spikes
- User load versus response time
- Potential saturation points

Important: The report may contain HTML, JavaScript, JSON, CSV and supporting assets. Inspect the complete ZIP structure and extract underlying data instead of relying only on visible HTML content. Create a reusable parser because future NeoLoad reports will follow the same format. Do not hardcode values from sample reports.

## 6. Bottleneck Identification

Identify potential performance bottlenecks involving:
- Application server CPU
- Application server memory
- Garbage collection
- Database performance
- Slow SQL queries
- Connection pools
- Thread pools
- Network latency
- External API dependencies
- Load generator saturation
- High response times
- High error rates

Correlate metrics across the same time window whenever timestamps are available. Do not conclude that a component is the root cause based on a single metric.

Clearly distinguish:
- Confirmed observations
- Potential bottlenecks
- Hypotheses
- Additional evidence required

## 7. AI Analysis Engine

Use Ollama with Qwen. Build a Python module that connects to the local Ollama service.

Processing flow:
1. Python extracts the original report data.
2. Python calculates numerical metrics.
3. Python creates structured JSON.
4. Structured results are sent to Qwen.
5. Qwen interprets the results.
6. Qwen generates performance observations and recommendations.
7. Streamlit displays the results.

The AI must not invent performance metrics. If a metric is absent, explicitly state that it is unavailable. Use uploaded data as the source of truth.

## 8. AI Assistant – Chat Functionality

Provide a chat interface where I can ask questions about the uploaded report.

Example questions:
- Which transaction has the highest response time?
- What is the average TPS?
- Why did the error rate increase?
- Which transaction is causing the most failures?
- What happened when users increased from 100 to 500?
- Is CPU utilization a bottleneck?
- Is the application server overloaded?
- Which transactions breached the SLA?
- Compare average response time with P95.
- What should I investigate first?
- Provide a detailed RCA.
- Give recommendations to improve performance.

The AI should answer based on the currently uploaded report. Avoid generic answers when report-specific evidence is available.

## 9. Application UI Design

Build a modern, professional, enterprise-style dashboard.

Application name: **PerfAI**

Design preferences:
- Modern dark theme
- Professional color palette
- Clean dashboard layout
- Good typography
- Clear visual hierarchy
- Responsive interface
- Minimal unnecessary decorations
- Professional charts and tables

### Main navigation
1. Dashboard
2. Report Analyzer
3. Transaction Analysis
4. Performance Metrics
5. Bottleneck Analysis
6. AI Assistant
7. Analysis History

### Dashboard KPI cards
- Virtual users
- Average TPS
- Peak TPS
- Average response time
- P95 response time
- Error percentage
- Total transactions
- Failed transactions

### Transaction Analysis table
- Transaction name
- Execution count
- Average response time
- P95
- P99
- TPS
- Error count
- Error percentage
- SLA status

### Performance charts
- TPS over time
- Response time over time
- Virtual users over time
- Error rate over time
- CPU utilization over time
- Memory utilization over time

### Bottleneck Analysis
Display:
- Identified issue
- Severity
- Supporting metrics
- Time window
- Possible root cause
- Recommended investigation
- Corrective action

### AI Assistant
Provide a conversational chat interface for questions about the uploaded report.

## 10. Project Architecture

Use a simple modular Python architecture.

```text
performance-ai-agent/
│
├── app.py
│
├── analyzer/
│   ├── neoload_parser.py
│   ├── metrics_analyzer.py
│   ├── log_analyzer.py
│   ├── resource_analyzer.py
│   └── image_analyzer.py
│
├── ai/
│   ├── ollama_client.py
│   ├── prompts.py
│   └── agent.py
│
├── utils/
│   ├── file_handler.py
│   └── report_generator.py
│
├── uploads/
├── reports/
│
├── requirements.txt
├── config.py
└── README.md
```

You may adjust the architecture if necessary, but keep it simple.

## 11. Development Requirements

1. I am a beginner in AI development.
2. Build a working application, not just a prototype UI.
3. Use simple Python code.
4. Avoid unnecessary abstractions.
5. Do not introduce LangChain, vector databases, Kubernetes, microservices or complex agent frameworks in version 1.
6. Use Ollama directly through its Python interface or local API.
7. Provide complete updated files whenever modifying existing files.
8. Include comments explaining important code sections.
9. Provide exact Ubuntu terminal commands.
10. Explain how to run and test the application.
11. Handle missing files, invalid formats and parsing errors gracefully.
12. Never fabricate analysis results.

## 12. Performance Analysis Quality

The application must calculate metrics accurately.

For example:

**Error Rate** = (Failed Requests / Total Requests) × 100

**TPS** = Successful Transactions / Measurement Duration

Use the appropriate denominator for each metric and clearly identify whether TPS means transactions per second or requests per second.

Calculate percentiles from raw observations when available. Do not calculate P95 by averaging transaction averages.

For aggregated reports, explain when exact percentile calculations are unavailable.

Correlate performance metrics with infrastructure data before making bottleneck conclusions.

## 13. Future Enhancements

Keep the architecture ready for:
- JMeter integration
- NeoLoad report comparisons
- Historical performance analysis
- Baseline versus current test comparison
- Automatic RCA generation
- Prometheus integration
- Grafana integration
- Downloadable PDF analysis reports
- Multiple report uploads
- Performance regression detection

Do not implement all these advanced features initially.

## 14. Final Expected Outcome

Build a functional local AI Performance Testing Agent that can:
1. Accept performance testing reports.
2. Automatically extract test metrics.
3. Analyze transactions and errors.
4. Identify potential bottlenecks.
5. Explain possible root causes.
6. Recommend corrective actions.
7. Answer questions through an AI chat interface.
8. Generate a professional performance analysis report.

The application should be useful for a real Performance Test Engineer, not just a generic chatbot.

## 15. How to Start

Before writing code:
1. Review the entire project requirement.
2. Propose the final architecture.
3. Design the dashboard UI.
4. Identify the required Python dependencies.
5. Plan the implementation in small milestones.

Then start implementing the first working milestone: NeoLoad HTML/ZIP report parsing and performance metric extraction.

**Important: Build incrementally. Validate extracted metrics against the actual NeoLoad report before proceeding to AI integration. Do not generate the entire project in one unverified code dump.**


sample Neoload test report is in Summary.zip
