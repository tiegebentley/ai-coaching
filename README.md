# AI Coaching System

An intelligent coaching management system that streamlines email processing, task management, and workflow automation for coaching organizations.

## Project Structure

```
ai-coaching/
├── frontend/          # Next.js frontend application
├── backend/           # Python FastAPI backend with AI agents
├── BMAD/             # Business Model and Architecture Documentation
├── PRPs/             # Product Requirement Prompts
└── use-cases-pydantic-ai/  # Pydantic AI use cases and examples
```

## Features

- **Email Processing**: Automated Gmail integration for handling coaching communications
- **Knowledge Management**: Vector-powered AI infrastructure for intelligent information retrieval
- **Task Automation**: N8N workflow integration with Airtable for task tracking
- **Multi-Agent Architecture**: Specialized AI agents for different coaching tasks
- **Real-time Dashboard**: Interactive frontend for monitoring and managing coaching activities

## Tech Stack

### Frontend
- Next.js 14
- TypeScript
- Tailwind CSS
- Supabase Client

### Backend
- Python FastAPI
- Pydantic AI
- Supabase (PostgreSQL with pgvector)
- OpenAI Embeddings
- Gmail API

### Integrations
- Airtable for data management
- N8N for workflow automation
- Archon MCP for task orchestration

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- Supabase account
- Gmail API credentials
- OpenAI API key

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python -m ai_coaching.main
```

### Environment Variables

Create `.env` files in both `frontend/` and `backend/` directories based on the `.env.example` files provided.

## Development Status

### Phase 1: Foundation Infrastructure ✅
- Monorepo project structure
- Supabase database with pgvector
- Vector embedding service
- Knowledge base data models
- Knowledge Agent core

### Phase 2: Email Processing (In Progress)
- Gmail API integration
- Email classification and routing
- Automated response generation

## Deployment

The project is configured for deployment on Vercel (frontend) and can be deployed to any Python-supporting platform for the backend.

## Contributing

This project uses Archon MCP for task management. All development should follow the task-driven workflow defined in `CLAUDE.md`.

## License

Private project - All rights reserved