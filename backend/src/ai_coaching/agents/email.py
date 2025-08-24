"""Email Agent for processing incoming emails and generating AI-powered drafts."""

import asyncio
import time
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Tuple
import json
import hashlib

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ai_coaching.agents.base import BaseAgent, AgentTask
from ai_coaching.models.base import BaseAgentOutput, SystemDependencies
from ai_coaching.services.gmail import EmailProcessingRequest
from ai_coaching.services.airtable import AirtableService
from ai_coaching.agents.knowledge import KnowledgeAgent

logger = structlog.get_logger(__name__)


class EmailContext(BaseModel):
    """Context aggregated from multiple sources for email processing."""
    family_info: Optional[Dict[str, Any]] = Field(None, description="Family information from Airtable")
    schedule_data: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Schedule information")
    payment_status: Optional[Dict[str, Any]] = Field(None, description="Payment status information")
    knowledge_items: List[Dict[str, Any]] = Field(default_factory=list, description="Relevant knowledge base items")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Previous email conversations")
    context_quality_score: float = Field(0.0, description="Quality score of aggregated context (0-1)")


class EmailDraftResponse(BaseModel):
    """Response containing generated email draft and metadata."""
    draft_content: str = Field(..., description="Generated email draft content")
    confidence_score: float = Field(..., description="Confidence in draft quality (0-1)")
    context_used: List[str] = Field(default_factory=list, description="Context sources used")
    tone: str = Field("professional", description="Detected/applied tone")
    suggested_edits: List[str] = Field(default_factory=list, description="Suggested manual edits")
    requires_review: bool = Field(True, description="Whether manual review is recommended")
    processing_time: float = Field(..., description="Time taken to generate draft")


class EmailAgent(BaseAgent):
    """Agent responsible for processing incoming emails and generating AI-powered draft responses.
    
    This agent:
    - Processes incoming emails with sender identification
    - Aggregates context from multiple sources (Airtable, Knowledge base, conversation history)
    - Generates professional draft responses using LLM
    - Scores confidence in generated drafts
    - Maintains consistent communication style
    - Targets <10 second processing time
    """
    
    def __init__(
        self,
        dependencies: SystemDependencies,
        openai_api_key: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Email Agent.
        
        Args:
            dependencies: System dependencies including database and services
            openai_api_key: OpenAI API key for LLM operations
            config: Agent-specific configuration
        """
        super().__init__("EmailAgent", dependencies, config)
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        # Initialize services
        self.airtable_service: Optional[AirtableService] = None
        self.knowledge_agent: Optional[KnowledgeAgent] = None
        
        # Email processing configuration
        self.max_context_length = config.get("max_context_length", 4000) if config else 4000
        self.model_name = config.get("model_name", "gpt-4-turbo-preview") if config else "gpt-4-turbo-preview"
        self.temperature = config.get("temperature", 0.7) if config else 0.7
        self.max_tokens = config.get("max_tokens", 1000) if config else 1000
        
        # Performance tracking
        self.target_processing_time = 10.0  # Target <10 seconds
        
        # Cache for frequently accessed data
        self._family_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    async def _initialize_agent(self) -> None:
        """Initialize agent-specific components."""
        try:
            # Initialize Airtable service if available
            if hasattr(self.dependencies, 'airtable_service'):
                self.airtable_service = self.dependencies.airtable_service
                self.logger.info("Airtable service initialized")
            
            # Initialize Knowledge agent if available
            if hasattr(self.dependencies, 'knowledge_agent'):
                self.knowledge_agent = self.dependencies.knowledge_agent
                self.logger.info("Knowledge agent initialized")
            
            # Verify OpenAI connection
            await self._verify_openai_connection()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize EmailAgent: {str(e)}")
            raise
    
    async def _verify_openai_connection(self) -> None:
        """Verify OpenAI API connection."""
        try:
            # Simple test to verify API key
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            self.logger.info("OpenAI connection verified")
        except Exception as e:
            self.logger.error(f"OpenAI connection failed: {str(e)}")
            raise
    
    async def process_task(self, task: AgentTask) -> BaseAgentOutput:
        """Process an email task.
        
        Args:
            task: Email processing task containing email data
            
        Returns:
            BaseAgentOutput with draft response and metadata
        """
        start_time = time.time()
        
        try:
            # Extract email data from task
            email_data = task.input_data
            if not isinstance(email_data, dict) or 'email_id' not in email_data:
                raise ValueError("Invalid email task data")
            
            # Create EmailProcessingRequest from task data
            # Store sender_name separately as it's not part of EmailProcessingRequest
            sender_name = email_data.get('sender_name', '')
            
            email_request = EmailProcessingRequest(
                email_id=email_data['email_id'],
                sender_email=email_data.get('sender_email', ''),
                subject=email_data.get('subject', ''),
                body_content=email_data.get('body_content', ''),
                received_timestamp=datetime.fromisoformat(email_data.get('received_at', datetime.now(UTC).isoformat())),
                thread_id=email_data.get('thread_id')
            )
            
            # Add sender_name as an attribute for later use
            email_request.sender_name = sender_name
            
            # Process email with multi-source context
            result = await self._process_email_with_context(email_request)
            
            processing_time = time.time() - start_time
            
            # Check if we met performance target
            if processing_time > self.target_processing_time:
                self.logger.warning(
                    f"Processing exceeded target time: {processing_time:.2f}s > {self.target_processing_time}s",
                    email_id=email_request.email_id
                )
            
            return BaseAgentOutput(
                success=True,
                confidence_score=result.confidence_score,
                result_data=result.dict(),
                processing_time=processing_time,
                metadata={
                    "email_id": email_request.email_id,
                    "sender": email_request.sender_email,
                    "subject": email_request.subject,
                    "context_sources": result.context_used
                }
            )
            
        except Exception as e:
            self.logger.error(f"Email processing failed: {str(e)}", task_id=task.task_id)
            processing_time = time.time() - start_time
            
            return BaseAgentOutput(
                success=False,
                confidence_score=0.0,
                result_data={"error": str(e)},
                error_message=str(e),
                processing_time=processing_time
            )
    
    async def _process_email_with_context(self, email_request: EmailProcessingRequest) -> EmailDraftResponse:
        """Process email with multi-source context aggregation.
        
        Args:
            email_request: Email processing request
            
        Returns:
            EmailDraftResponse with generated draft and metadata
        """
        # Aggregate context from multiple sources in parallel
        context = await self._aggregate_context(email_request)
        
        # Generate draft using LLM with context
        draft_content, confidence_score = await self._generate_draft_with_llm(
            email_request, context
        )
        
        # Determine if review is needed based on confidence
        requires_review = confidence_score < 0.8
        
        # Analyze tone and suggest edits
        tone = self._analyze_tone(draft_content)
        suggested_edits = self._suggest_edits(draft_content, confidence_score, context)
        
        return EmailDraftResponse(
            draft_content=draft_content,
            confidence_score=confidence_score,
            context_used=self._get_context_sources(context),
            tone=tone,
            suggested_edits=suggested_edits,
            requires_review=requires_review,
            processing_time=time.time()
        )
    
    async def _aggregate_context(self, email_request: EmailProcessingRequest) -> EmailContext:
        """Aggregate context from multiple sources.
        
        Args:
            email_request: Email processing request
            
        Returns:
            EmailContext with aggregated information
        """
        context = EmailContext()
        
        # Run context aggregation tasks in parallel for performance
        tasks = []
        
        # Airtable context (family info, schedule, payments)
        if self.airtable_service:
            tasks.append(self._get_airtable_context(email_request.sender_email))
        
        # Knowledge base context
        if self.knowledge_agent:
            tasks.append(self._get_knowledge_context(email_request))
        
        # Conversation history from database
        if self.dependencies.db_service:
            tasks.append(self._get_conversation_history(email_request))
        
        # Execute all context gathering tasks in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    self.logger.warning(f"Context aggregation task failed: {str(result)}")
                    continue
                
                if isinstance(result, dict):
                    # Airtable context
                    if 'family_info' in result:
                        context.family_info = result['family_info']
                        context.schedule_data = result.get('schedule_data', [])
                        context.payment_status = result.get('payment_status')
                    # Knowledge context
                    elif 'knowledge_items' in result:
                        context.knowledge_items = result['knowledge_items']
                    # Conversation history
                    elif 'conversation_history' in result:
                        context.conversation_history = result['conversation_history']
        
        # Calculate context quality score
        context.context_quality_score = self._calculate_context_quality(context)
        
        return context
    
    async def _get_airtable_context(self, sender_email: str) -> Dict[str, Any]:
        """Get context from Airtable.
        
        Args:
            sender_email: Sender's email address
            
        Returns:
            Dictionary with Airtable context
        """
        try:
            # Check cache first
            if sender_email in self._family_cache:
                cached_data, cache_time = self._family_cache[sender_email]
                if time.time() - cache_time < self._cache_ttl:
                    return cached_data
            
            # Fetch from Airtable
            family_info = await self.airtable_service.get_family_info(sender_email)
            schedule_data = await self.airtable_service.get_schedule_data(
                family_info.get('Family ID') if family_info else None
            )
            payment_status = await self.airtable_service.get_payment_status(
                family_info.get('Family ID') if family_info else None
            )
            
            result = {
                'family_info': family_info,
                'schedule_data': schedule_data,
                'payment_status': payment_status
            }
            
            # Cache the result
            self._family_cache[sender_email] = (result, time.time())
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get Airtable context: {str(e)}")
            return {}
    
    async def _get_knowledge_context(self, email_request: EmailProcessingRequest) -> Dict[str, Any]:
        """Get relevant knowledge base context.
        
        Args:
            email_request: Email processing request
            
        Returns:
            Dictionary with knowledge items
        """
        try:
            # Create search query from email content
            search_query = f"{email_request.subject} {email_request.body_content[:200]}"
            
            # Search knowledge base
            knowledge_task = AgentTask(
                task_type="search_knowledge",
                input_data={
                    "query": search_query,
                    "limit": 5
                }
            )
            
            result = await self.knowledge_agent.process_task(knowledge_task)
            
            if result.success and result.result_data:
                return {'knowledge_items': result.result_data.get('items', [])}
            
            return {'knowledge_items': []}
            
        except Exception as e:
            self.logger.error(f"Failed to get knowledge context: {str(e)}")
            return {'knowledge_items': []}
    
    async def _get_conversation_history(self, email_request: EmailProcessingRequest) -> Dict[str, Any]:
        """Get conversation history from database.
        
        Args:
            email_request: Email processing request
            
        Returns:
            Dictionary with conversation history
        """
        try:
            if not email_request.thread_id:
                return {'conversation_history': []}
            
            # Query database for thread history
            history = await self.dependencies.db_service.get_email_thread_history(
                email_request.thread_id
            )
            
            return {'conversation_history': history}
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation history: {str(e)}")
            return {'conversation_history': []}
    
    async def _generate_draft_with_llm(
        self, 
        email_request: EmailProcessingRequest,
        context: EmailContext
    ) -> Tuple[str, float]:
        """Generate email draft using LLM with context.
        
        Args:
            email_request: Email processing request
            context: Aggregated context
            
        Returns:
            Tuple of (draft_content, confidence_score)
        """
        try:
            # Build prompt with context
            prompt = self._build_prompt(email_request, context)
            
            # Generate response using OpenAI
            response = await self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            draft_content = response.choices[0].message.content
            
            # Calculate confidence score based on context quality and response
            confidence_score = self._calculate_confidence(context, response)
            
            return draft_content, confidence_score
            
        except Exception as e:
            self.logger.error(f"LLM generation failed: {str(e)}")
            # Return a fallback response
            fallback_draft = self._generate_fallback_draft(email_request)
            return fallback_draft, 0.3
    
    def _build_prompt(self, email_request: EmailProcessingRequest, context: EmailContext) -> str:
        """Build LLM prompt with context.
        
        Args:
            email_request: Email processing request
            context: Aggregated context
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Generate a professional email response for the following incoming email:",
            f"\nFrom: {getattr(email_request, 'sender_name', '')} <{email_request.sender_email}>",
            f"Subject: {email_request.subject}",
            f"Content: {email_request.body_content}\n"
        ]
        
        # Add family context if available
        if context.family_info:
            prompt_parts.append("\n--- Family Information ---")
            prompt_parts.append(f"Family Name: {context.family_info.get('Family Name', 'Unknown')}")
            if context.family_info.get('Children'):
                children = context.family_info['Children']
                prompt_parts.append(f"Children: {', '.join([c.get('name', '') for c in children])}")
        
        # Add schedule context if available
        if context.schedule_data:
            prompt_parts.append("\n--- Upcoming Schedule ---")
            for event in context.schedule_data[:3]:  # Limit to 3 events
                prompt_parts.append(
                    f"- {event.get('Event Name', '')} on {event.get('Date', '')} at {event.get('Time', '')}"
                )
        
        # Add payment status if relevant
        if context.payment_status:
            prompt_parts.append("\n--- Payment Status ---")
            prompt_parts.append(f"Status: {context.payment_status.get('status', 'Unknown')}")
            if context.payment_status.get('balance'):
                prompt_parts.append(f"Balance: ${context.payment_status['balance']}")
        
        # Add relevant knowledge items
        if context.knowledge_items:
            prompt_parts.append("\n--- Relevant Information ---")
            for item in context.knowledge_items[:2]:  # Limit to 2 items
                prompt_parts.append(f"- {item.get('content', '')[:200]}...")
        
        # Add conversation history if available
        if context.conversation_history:
            prompt_parts.append("\n--- Previous Conversation ---")
            for msg in context.conversation_history[-2:]:  # Last 2 messages
                prompt_parts.append(f"- {msg.get('sender', '')}: {msg.get('content', '')[:100]}...")
        
        prompt_parts.append("\n--- Instructions ---")
        prompt_parts.append("Generate a professional, helpful, and personalized response.")
        prompt_parts.append("Include specific details from the context when relevant.")
        prompt_parts.append("Maintain a friendly but professional tone.")
        prompt_parts.append("Keep the response concise and to the point.")
        
        return "\n".join(prompt_parts)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM.
        
        Returns:
            System prompt string
        """
        return """You are an AI assistant helping a Youth Soccer Program Director respond to emails.
        Your responses should be:
        - Professional and friendly
        - Accurate and helpful
        - Personalized using available context
        - Clear and concise
        - Appropriate for communicating with parents and families
        
        Always maintain confidentiality and professionalism.
        Use the provided context to personalize responses.
        If you're unsure about specific details, indicate that you'll follow up with accurate information.
        """
    
    def _calculate_confidence(self, context: EmailContext, response: Any) -> float:
        """Calculate confidence score for generated draft.
        
        Args:
            context: Email context used
            response: OpenAI response object
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on context quality
        confidence += context.context_quality_score * 0.3
        
        # Check if we have family information
        if context.family_info:
            confidence += 0.1
        
        # Check if we have conversation history
        if context.conversation_history:
            confidence += 0.05
        
        # Check if we have relevant knowledge items
        if context.knowledge_items:
            confidence += min(len(context.knowledge_items) * 0.02, 0.1)
        
        # Adjust based on response quality (if available)
        if hasattr(response, 'choices') and response.choices:
            finish_reason = response.choices[0].finish_reason
            if finish_reason == 'stop':
                confidence += 0.05  # Complete response
        
        return min(confidence, 1.0)
    
    def _calculate_context_quality(self, context: EmailContext) -> float:
        """Calculate quality score for aggregated context.
        
        Args:
            context: Aggregated email context
            
        Returns:
            Quality score between 0 and 1
        """
        score = 0.0
        
        # Family info contributes 40%
        if context.family_info:
            score += 0.4
        
        # Schedule data contributes 20%
        if context.schedule_data:
            score += 0.2
        
        # Payment status contributes 10%
        if context.payment_status:
            score += 0.1
        
        # Knowledge items contribute 20%
        if context.knowledge_items:
            score += min(len(context.knowledge_items) * 0.04, 0.2)
        
        # Conversation history contributes 10%
        if context.conversation_history:
            score += 0.1
        
        return score
    
    def _analyze_tone(self, draft_content: str) -> str:
        """Analyze the tone of generated draft.
        
        Args:
            draft_content: Generated email draft
            
        Returns:
            Detected tone descriptor
        """
        # Simple tone analysis based on keywords
        draft_lower = draft_content.lower()
        
        if any(word in draft_lower for word in ['unfortunately', 'apologize', 'sorry', 'regret']):
            return 'apologetic'
        elif any(word in draft_lower for word in ['excited', 'delighted', 'pleased', 'happy']):
            return 'enthusiastic'
        elif any(word in draft_lower for word in ['urgent', 'immediately', 'asap', 'critical']):
            return 'urgent'
        elif any(word in draft_lower for word in ['thank', 'appreciate', 'grateful']):
            return 'appreciative'
        else:
            return 'professional'
    
    def _suggest_edits(
        self, 
        draft_content: str, 
        confidence_score: float,
        context: EmailContext
    ) -> List[str]:
        """Suggest manual edits for the draft.
        
        Args:
            draft_content: Generated draft
            confidence_score: Confidence in draft
            context: Email context used
            
        Returns:
            List of suggested edits
        """
        suggestions = []
        
        # Low confidence suggestions
        if confidence_score < 0.6:
            suggestions.append("Review all details for accuracy")
            suggestions.append("Consider adding more personalization")
        
        # Missing context suggestions
        if not context.family_info:
            suggestions.append("Verify family/sender information if available")
        
        if not context.schedule_data:
            suggestions.append("Check if schedule information needs to be included")
        
        # Content-based suggestions
        if len(draft_content) > 500:
            suggestions.append("Consider shortening for clarity")
        elif len(draft_content) < 100:
            suggestions.append("Consider adding more detail or context")
        
        # Check for placeholder-like content
        if '[' in draft_content or ']' in draft_content:
            suggestions.append("Fill in any placeholder information")
        
        return suggestions
    
    def _get_context_sources(self, context: EmailContext) -> List[str]:
        """Get list of context sources used.
        
        Args:
            context: Email context
            
        Returns:
            List of context source names
        """
        sources = []
        
        if context.family_info:
            sources.append("Airtable Family Data")
        if context.schedule_data:
            sources.append("Schedule Information")
        if context.payment_status:
            sources.append("Payment Records")
        if context.knowledge_items:
            sources.append("Knowledge Base")
        if context.conversation_history:
            sources.append("Conversation History")
        
        return sources
    
    def _generate_fallback_draft(self, email_request: EmailProcessingRequest) -> str:
        """Generate a fallback draft when LLM fails.
        
        Args:
            email_request: Email processing request
            
        Returns:
            Basic fallback draft
        """
        return f"""Dear {getattr(email_request, 'sender_name', None) or 'Parent'},

Thank you for your email regarding "{email_request.subject}".

I have received your message and will review it carefully to provide you with the most accurate and helpful response. I will get back to you as soon as possible with the information you need.

If this is an urgent matter, please don't hesitate to call our office directly.

Best regards,
Youth Soccer Program Director
"""
    
    async def _agent_health_check(self) -> bool:
        """Perform agent-specific health checks.
        
        Returns:
            True if health check passes
        """
        try:
            # Check OpenAI client
            if not self.openai_client:
                return False
            
            # Check services
            if self.airtable_service:
                # Could add specific health check for Airtable
                pass
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
    
    async def _shutdown_agent(self) -> None:
        """Perform agent-specific shutdown tasks."""
        try:
            # Clear caches
            self._family_cache.clear()
            
            # Close OpenAI client if needed
            if hasattr(self.openai_client, 'close'):
                await self.openai_client.close()
            
            self.logger.info("EmailAgent shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Shutdown error: {str(e)}")