"""Gmail API routes and webhook handlers."""

import base64
import json
import hmac
import hashlib
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import structlog
from datetime import datetime

from ai_coaching.services.gmail import GmailService, EmailProcessingRequest
from ai_coaching.services.database import DatabaseService
from ai_coaching.config.settings import get_config
from google.oauth2.credentials import Credentials

logger = structlog.get_logger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)


class WebhookPayload(BaseModel):
    """Gmail webhook payload model."""
    message: Dict[str, Any]
    subscription: str


class WebhookSetupRequest(BaseModel):
    """Request to setup Gmail webhook subscription."""
    topic_name: str = Field(description="Cloud Pub/Sub topic name")
    access_token: str = Field(description="OAuth access token")
    refresh_token: Optional[str] = Field(default=None, description="OAuth refresh token")


class WebhookSetupResponse(BaseModel):
    """Response from webhook setup."""
    subscription_id: str
    history_id: str
    expiration: Optional[str] = None


class EmailProcessResponse(BaseModel):
    """Email processing response."""
    message_id: str
    status: str
    processing_time: float
    draft_generated: bool = False
    confidence_score: Optional[float] = None


def get_gmail_service() -> GmailService:
    """Get Gmail service dependency."""
    config = get_config()
    return GmailService(config.gmail)


def get_database_service() -> DatabaseService:
    """Get database service dependency."""
    config = get_config()
    return DatabaseService(config.database)


async def verify_webhook_signature(request: Request, raw_body: bytes) -> bool:
    """Verify webhook signature for security.
    
    Args:
        request: FastAPI request object
        raw_body: Raw request body bytes
        
    Returns:
        True if signature is valid
    """
    # In production, you would verify the Pub/Sub signature
    # For now, we'll implement basic token verification
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header")
        return False
    
    # Extract and verify token (simplified for development)
    token = auth_header.split(" ")[1]
    # In production, verify this token against your webhook secret
    
    return True


@router.post("/webhook", response_model=Dict[str, str])
async def handle_gmail_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    gmail_service: GmailService = Depends(get_gmail_service),
    db_service: DatabaseService = Depends(get_database_service)
) -> Dict[str, str]:
    """Handle Gmail webhook notifications.
    
    This endpoint receives push notifications from Gmail when new emails arrive.
    It processes the notification and triggers email processing in the background.
    
    Args:
        request: FastAPI request object
        background_tasks: Background task manager
        
    Returns:
        Acknowledgment response
    """
    try:
        # Get raw body for signature verification
        raw_body = await request.body()
        
        # Verify webhook signature
        if not await verify_webhook_signature(request, raw_body):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse JSON payload
        try:
            payload_data = json.loads(raw_body)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON payload", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Extract Pub/Sub message
        if "message" not in payload_data:
            logger.error("Missing 'message' field in payload")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'message' field"
            )
        
        message = payload_data["message"]
        
        # Decode the message data
        if "data" in message:
            try:
                # Decode base64 data
                decoded_data = base64.b64decode(message["data"]).decode('utf-8')
                webhook_data = json.loads(decoded_data)
            except Exception as e:
                logger.error("Failed to decode webhook data", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to decode webhook data"
                )
        else:
            webhook_data = {}
        
        # Extract relevant information
        email_address = webhook_data.get("emailAddress")
        history_id = webhook_data.get("historyId")
        
        logger.info(
            "Gmail webhook received",
            email_address=email_address,
            history_id=history_id,
            message_id=message.get("messageId")
        )
        
        # Add background task to process the webhook
        background_tasks.add_task(
            process_gmail_notification,
            email_address,
            history_id,
            webhook_data
        )
        
        return {"status": "accepted", "message_id": message.get("messageId", "unknown")}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


async def process_gmail_notification(
    email_address: Optional[str],
    history_id: Optional[str],
    webhook_data: Dict[str, Any]
) -> None:
    """Background task to process Gmail notification.
    
    Args:
        email_address: User's email address
        history_id: Gmail history ID
        webhook_data: Full webhook payload data
    """
    try:
        config = get_config()
        gmail_service = GmailService(config.gmail)
        
        # TODO: Retrieve user's OAuth credentials from database
        # For now, this would need to be implemented with proper credential storage
        
        logger.info(
            "Processing Gmail notification",
            email_address=email_address,
            history_id=history_id
        )
        
        # Process new emails (this would get implemented with email history API)
        # For now, log the notification
        logger.info("Gmail notification processed successfully")
        
    except Exception as e:
        logger.error("Background Gmail processing failed", error=str(e))


@router.post("/setup-webhook", response_model=WebhookSetupResponse)
async def setup_gmail_webhook(
    request: WebhookSetupRequest,
    gmail_service: GmailService = Depends(get_gmail_service)
) -> WebhookSetupResponse:
    """Setup Gmail webhook subscription.
    
    Args:
        request: Webhook setup parameters
        
    Returns:
        Subscription details
    """
    try:
        # Create credentials from tokens
        credentials = Credentials(
            token=request.access_token,
            refresh_token=request.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=gmail_service.config.client_id,
            client_secret=gmail_service.config.client_secret
        )
        
        # Initialize Gmail service with credentials
        await gmail_service.initialize(credentials)
        
        # Setup webhook subscription
        result = await gmail_service.setup_webhook_subscription(request.topic_name)
        
        logger.info(
            "Gmail webhook subscription created",
            topic_name=request.topic_name,
            subscription_id=result.get("historyId"),
            expiration=result.get("expiration")
        )
        
        return WebhookSetupResponse(
            subscription_id=result.get("historyId", "unknown"),
            history_id=result.get("historyId", "unknown"),
            expiration=result.get("expiration")
        )
        
    except Exception as e:
        logger.error("Webhook setup failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook setup failed: {str(e)}"
        )


@router.post("/process-email/{message_id}", response_model=EmailProcessResponse)
async def process_email_manually(
    message_id: str,
    access_token: str,
    background_tasks: BackgroundTasks,
    refresh_token: Optional[str] = None,
    gmail_service: GmailService = Depends(get_gmail_service)
) -> EmailProcessResponse:
    """Manually process a specific email.
    
    This endpoint allows manual processing of emails for testing or recovery.
    
    Args:
        message_id: Gmail message ID to process
        access_token: OAuth access token
        refresh_token: Optional refresh token
        background_tasks: Background task manager
        
    Returns:
        Processing status and results
    """
    processing_start = datetime.utcnow()
    
    try:
        # Create credentials
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=gmail_service.config.client_id,
            client_secret=gmail_service.config.client_secret
        )
        
        # Initialize Gmail service
        await gmail_service.initialize(credentials)
        
        # Process the email
        email_request = await gmail_service.process_incoming_email(message_id)
        
        # Calculate processing time
        processing_time = (datetime.utcnow() - processing_start).total_seconds()
        
        # TODO: Add background task to generate AI response
        # background_tasks.add_task(generate_ai_email_response, email_request)
        
        logger.info(
            "Email processed manually",
            message_id=message_id,
            sender=email_request.sender_email,
            processing_time=processing_time
        )
        
        return EmailProcessResponse(
            message_id=message_id,
            status="processed",
            processing_time=processing_time,
            draft_generated=False  # Will be True when AI response generation is implemented
        )
        
    except Exception as e:
        processing_time = (datetime.utcnow() - processing_start).total_seconds()
        logger.error("Manual email processing failed", error=str(e), message_id=message_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email processing failed: {str(e)}"
        )


@router.get("/health")
async def gmail_health_check(
    gmail_service: GmailService = Depends(get_gmail_service)
) -> Dict[str, Any]:
    """Check Gmail service health.
    
    Returns:
        Health status information
    """
    try:
        # Basic service instantiation check
        config = get_config()
        has_config = bool(
            config.gmail.client_id and
            config.gmail.client_secret and
            config.gmail.redirect_uri
        )
        
        return {
            "status": "healthy" if has_config else "configuration_missing",
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": {
                "client_id_configured": bool(config.gmail.client_id),
                "client_secret_configured": bool(config.gmail.client_secret),
                "redirect_uri": config.gmail.redirect_uri,
                "scopes": config.gmail.scopes
            },
            "webhook_endpoint": config.gmail.webhook_endpoint
        }
        
    except Exception as e:
        logger.error("Gmail health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }