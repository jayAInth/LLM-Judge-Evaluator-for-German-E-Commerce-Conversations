# LLM-as-Judge Evaluation Framework

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)
![React](https://img.shields.io/badge/React-18-61DAFB.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**Automated evaluation of German e-commerce customer support chatbots using LLMs as judges**

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [API Documentation](#api-documentation) • [Deployment](#deployment)

</div>

---

## Overview

This framework provides automated, scalable evaluation of customer support chatbot conversations using Large Language Models as judges. Designed specifically for German e-commerce contexts, it combines rigorous prompt engineering with customizable rubrics to deliver reliable, GDPR-compliant quality assessments.

### Key Benefits

| Stakeholder | Benefit |
|-------------|---------|
| **QA Teams** | Reduce manual review time by 85% while maintaining evaluation consistency |
| **Product Managers** | Real-time dashboards with actionable insights on chatbot performance |
| **Compliance Officers** | Full audit trails, GDPR-compliant logging, on-premise deployment |
| **ML Engineers** | Meta-evaluation metrics to validate judge reliability (target: 0.87 human correlation) |

---

## Features

### 🎯 Multi-Dimensional Evaluation
Evaluate conversations across 6 customizable dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| **Accuracy** | 25% | Factual correctness of product/policy information |
| **Tone** | 20% | Professional, helpful, empathetic communication |
| **Compliance** | 20% | Adherence to legal requirements (Widerrufsrecht, DSGVO) |
| **Completeness** | 15% | Full resolution of customer inquiry |
| **Language Quality** | 10% | German grammar, spelling, natural phrasing |
| **Efficiency** | 10% | Concise responses without unnecessary verbosity |

### 🔄 Batch Processing
- Async job queue with Celery + Redis
- Configurable batch sizes (up to 1000 conversations)
- Real-time progress tracking
- Resumable jobs with failure handling

### 📊 Analytics Dashboard
- Interactive React dashboard with Plotly visualizations
- Time-series analysis of evaluation metrics
- Category-wise performance breakdown
- Critical error and compliance issue tracking

### 🔒 GDPR Compliance
- Right to erasure (Article 17) endpoints
- Full audit logging with timestamps
- PII redaction capabilities
- On-premise deployment support

### 🧪 Meta-Evaluation
- Human annotation interface
- Inter-annotator agreement metrics
- Judge-human correlation analysis
- Calibration recommendations

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for local backend development)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/llm-judge-framework.git
cd llm-judge-framework
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# IMPORTANT: Set POSTGRES_PASSWORD to a secure value
# IMPORTANT: Add your HF_TOKEN if using vLLM with gated models
```

### 3. Start Services

```bash
# Start all services (without GPU)
docker-compose up -d

# OR with GPU support for vLLM (72B model)
docker-compose --profile gpu up -d
```

### 4. Access the Application

| Service | URL |
|---------|-----|
| **Frontend Dashboard** | http://localhost:3000 |
| **API Documentation** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/api/v1/health |
| **Celery Flower** | http://localhost:5555 (monitoring profile) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LLM-as-Judge Framework                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │   Frontend   │    │   Backend    │    │   Workers    │                  │
│  │  (React +    │◄──►│  (FastAPI)   │◄──►│  (Celery)    │                  │
│  │   Plotly)    │    │              │    │              │                  │
│  └──────────────┘    └──────┬───────┘    └──────┬───────┘                  │
│                             │                    │                          │
│                             ▼                    ▼                          │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │                    Data Layer                             │              │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │              │
│  │  │ PostgreSQL │  │   Redis    │  │   Object Storage   │  │              │
│  │  │ (Results)  │  │  (Queue)   │  │  (Conversations)   │  │              │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │              │
│  └──────────────────────────────────────────────────────────┘              │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────┐              │
│  │                    Judge Engine                           │              │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │              │
│  │  │  LLM Judge │  │  Rubric    │  │  LanguageTool      │  │              │
│  │  │  (Qwen/    │  │  Engine    │  │  (German Checks)   │  │              │
│  │  │   Ollama)  │  │            │  │                    │  │              │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │              │
│  └──────────────────────────────────────────────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
llm-judge-framework/
├── README.md                     # This file
├── docker-compose.yml            # Docker orchestration
├── .env.example                  # Environment template
│
├── backend/                      # FastAPI Backend
│   ├── app/
│   │   ├── main.py              # Application entry point
│   │   ├── api/routes.py        # REST API endpoints
│   │   ├── core/config.py       # Configuration management
│   │   ├── models/database.py   # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Business logic
│   │   └── workers/             # Celery tasks
│   ├── tests/                   # pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                     # React Dashboard
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   ├── pages/               # Dashboard pages
│   │   ├── hooks/               # Custom React hooks
│   │   └── lib/                 # Utilities
│   ├── package.json
│   └── vite.config.ts
│
├── judge/                        # LLM Judge Engine
│   ├── engine.py                # Core evaluation logic
│   ├── models.py                # Judge data models
│   ├── languagetool.py          # German grammar integration
│   └── rubrics/                 # Evaluation rubrics
│
├── evaluation/                   # Meta-Evaluation Tools
│   ├── datasets/                # Sample conversations
│   └── meta/                    # Correlation analysis
│
└── kubernetes/                   # K8s Deployment
    ├── namespace.yaml
    ├── deployments/
    ├── services/
    └── config/
```

---

## API Documentation

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | System health check |
| `POST` | `/api/v1/conversations` | Create conversation |
| `POST` | `/api/v1/conversations/batch` | Bulk upload conversations |
| `POST` | `/api/v1/evaluations/single` | Evaluate single conversation |
| `POST` | `/api/v1/evaluations/inline` | Evaluate without storing |
| `POST` | `/api/v1/jobs` | Create batch evaluation job |
| `GET` | `/api/v1/jobs/{id}/progress` | Real-time job progress |
| `GET` | `/api/v1/stats/overview` | Evaluation statistics |
| `GET` | `/api/v1/meta-evaluation` | Judge-human correlation |

### Example: Evaluate a Conversation

```bash
curl -X POST http://localhost:8000/api/v1/evaluations/inline \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": {
      "category": "retoure",
      "messages": [
        {"role": "customer", "content": "Ich möchte meine Bestellung zurückgeben."},
        {"role": "chatbot", "content": "Gerne helfe ich Ihnen bei der Retoure..."}
      ],
      "conversation_timestamp": "2026-01-14T12:00:00Z"
    }
  }'
```

Full API documentation available at `/docs` when running the backend.

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | **Required** |
| `HF_TOKEN` | HuggingFace token (for vLLM) | Optional |
| `JUDGE_MODEL_PROVIDER` | LLM provider | `openai_compatible` |
| `JUDGE_MODEL_NAME` | Model name | `gpt-oss-120b` |
| `JUDGE_API_URL` | LLM API endpoint | `http://host.docker.internal:11434/v1` |
| `DEBUG` | Enable debug mode | `true` |

### LLM Provider Options

1. **Ollama (Default)** - Local, no GPU required
   ```env
   JUDGE_MODEL_PROVIDER=openai_compatible
   JUDGE_MODEL_NAME=gpt-oss-120b
   JUDGE_API_URL=http://host.docker.internal:11434/v1
   ```

2. **vLLM (GPU Required)** - High-performance 72B model
   ```env
   JUDGE_MODEL_PROVIDER=openai_compatible
   JUDGE_MODEL_NAME=Qwen/Qwen2.5-72B-Instruct-GPTQ-Int4
   JUDGE_API_URL=http://vllm:8000/v1
   ```

---

## Deployment

### Docker Compose (Development)

```bash
docker-compose up -d
```

### Kubernetes (Production)

```bash
# Apply namespace and configs
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/config/

# Deploy services
kubectl apply -f kubernetes/deployments/
kubectl apply -f kubernetes/services/
```

---

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python -m backend.app.main
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Pydantic, SQLAlchemy, Celery |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Plotly.js |
| **Database** | PostgreSQL 15 |
| **Cache/Queue** | Redis 7 |
| **LLM** | Qwen2.5-72B / Ollama (configurable) |
| **German NLP** | LanguageTool |
| **Deployment** | Docker, Kubernetes |

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Judge-Human Correlation | ≥ 0.87 (Pearson's r) |
| Throughput | 1000 conversations/hour |
| Single Evaluation Latency | < 3s (P95) |
| Availability | 99.9% |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [LanguageTool](https://languagetool.org/) - Open-source grammar checker
- [Qwen](https://github.com/QwenLM/Qwen) - Open-source LLM with strong multilingual support
