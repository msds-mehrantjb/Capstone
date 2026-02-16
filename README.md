# Capstone
Agent-Based Risk Analysis and Assessment on Windows-Based Machines Using the ISO 27001 Standard <br/>

This project implements a fully local, agent-based AI system that performs automated risk analysis and assessment on Windows-based machines using Generative AI, structured tools, and Retrieval-Augmented Generation (RAG). The system provides a web-based GUI, local LLM inference, and persistent audit-ready results without relying on external cloud services.

---

## Key Features

- Fully local LLM inference (no external APIs required)
- Agent-based workflow using structured tools and stateful orchestration
- Automated collection and analysis of system security information
- ISO 27001–aligned risk assessment and compliance mapping
- Retrieval-Augmented Generation (RAG) using local vector database
- Web-based GUI with real-time agent execution timeline
- Persistent storage of reports, artifacts, and audit logs
- Modular architecture for extensibility and integration

---

## Architecture Overview
React Web GUI
│
▼
FastAPI Backend (API + Event Streaming)
│
▼
Agent Runtime (LangGraph)
├── Tool Execution Layer
├── RAG (Chroma Vector Database)
├── Local LLM Inference (Ollama / llama.cpp)
└── Report Generation
│
▼
Local Storage (Artifacts, Logs, Reports)

---

## Technology Stack

- Frontend: React + Vite
- Backend: FastAPI (Python)
- Agent Orchestration: LangGraph
- Local LLM Runtime: Ollama or llama.cpp
- Vector Database: Chroma
- Data Validation: Pydantic
- Streaming: Server-Sent Events (SSE)

---

## Project Structure
app/
├── ui/ # React web interface
├── api/ # FastAPI backend
├── agent/ # Agent workflows, tools, schemas
├── data/ # Vector database and artifacts
└── storage/ # Reports, logs, and run metadata
