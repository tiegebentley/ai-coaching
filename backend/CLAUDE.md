# Project Context

## Current Focus
**AI Coaching Management System - Phase 2 Implementation**
- Building email automation and agent architecture
- Completed Gmail API and Airtable integrations
- Next: Email Agent with AI draft generation

## Project Status
- **Project**: AI Coaching Management System
- **Current Phase**: Phase 2 - Email Automation & Dashboard
- **Archon Project ID**: efd4711e-ed34-4809-8480-7d35f4870a3d

## Recently Completed (2025-08-24)

### ✅ Gmail API Integration (Story 2.1)
- **Status**: COMPLETE - In Review
- **Task ID**: 3695415a-feda-4fe2-8c8a-421f15ed68ed
- **Implemented**:
  - OAuth 2.0 flow with proper scopes (gmail.readonly, gmail.send, gmail.modify)
  - Gmail service with webhook support
  - Rate limiting middleware (path-specific limits)
  - API routes for OAuth and webhook endpoints
  - Comprehensive integration tests
- **Key Files**:
  - `/src/ai_coaching/services/gmail.py` - Gmail service implementation
  - `/src/ai_coaching/api/routes/gmail.py` - API endpoints
  - `/src/ai_coaching/api/middleware/rate_limit.py` - Rate limiting
  - `/test_gmail_integration.py` - Full test suite

### ✅ Airtable Integration Service (Story 2.2)
- **Status**: COMPLETE - In Review
- **Task ID**: 8f3a705f-3c25-4af8-865a-e304d5a9e27b
- **Implemented**:
  - Async methods: `get_family_info()`, `get_schedule_data()`, `get_payment_status()`
  - Rate limiting (5 RPS) with exponential backoff
  - Data mapping for secondBrainExec base (appsdldIgkZ1fDzX2)
  - Family lookup by email with children relationships
  - Payment status calculations
  - Venue availability checking
- **Key Files**:
  - `/src/ai_coaching/services/airtable.py` - Airtable service (updated)
  - `/test_airtable_integration.py` - Full test suite
- **Fixes Applied**:
  - Fixed Airtable formula f-string escaping
  - Updated deprecated datetime.utcnow() to datetime.now(UTC)

## Priority Tasks for Next Session

### HIGH Priority (Continue Phase 2)
1. **Email Agent with AI Draft Generation** (Story 2.4)
   - Task ID: be59ddb4-c4c8-4cf2-a614-480cd8657c07
   - Process incoming emails with sender identification
   - Multi-source context aggregation (Airtable + Knowledge base)
   - LLM prompt engineering for professional drafts
   - Confidence scoring
   - <10 second processing target

2. **BaseAgent Architecture** (Story 3.1)
   - Task ID: 50fc132c-2840-4ebc-b15a-aae7d4f72361
   - Standardized BaseAgent abstract class
   - Task management functionality
   - Structured logging with correlation IDs
   - Agent registry system

3. **Next.js Dashboard Foundation** (Story 2.5)
   - Task ID: f8c7e1d8-7da9-43fe-a661-0a5717a67c43
   - Setup Next.js 14 with App Router
   - Dashboard layout with navigation
   - Supabase client integration

## Technical Notes

### Environment Setup
- Virtual environment active at `/root/AI_Coaching/backend/venv`
- All dependencies installed from `requirements.txt`
- Test environment variables configured in test files

### API Structure
- FastAPI app with modular route structure
- Rate limiting middleware implemented
- CORS configured for frontend integration
- Health check endpoints available

### Testing
- Run tests with: `source venv/bin/activate && python test_[service]_integration.py`
- All tests passing for Gmail and Airtable services
- Mock-based testing for external API dependencies

## Important Instructions
- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary
- ALWAYS prefer editing existing files
- NEVER proactively create documentation files unless explicitly requested