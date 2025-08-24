"""Authentication routes."""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional
import structlog
from datetime import datetime

from ai_coaching.services.gmail import GmailService
from ai_coaching.config.settings import get_config
from google.oauth2.credentials import Credentials

logger = structlog.get_logger(__name__)

router = APIRouter()


class OAuthUrlResponse(BaseModel):
    """OAuth authorization URL response."""
    auth_url: str
    state: Optional[str] = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""
    code: str
    state: Optional[str] = None


class OAuthTokenResponse(BaseModel):
    """OAuth token response."""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    user_email: Optional[str] = None


def get_gmail_service() -> GmailService:
    """Get Gmail service dependency."""
    config = get_config()
    return GmailService(config.gmail)


@router.get("/google/authorize", response_model=OAuthUrlResponse)
async def get_google_auth_url(
    state: Optional[str] = None,
    gmail_service: GmailService = Depends(get_gmail_service)
) -> OAuthUrlResponse:
    """Get Google OAuth authorization URL.
    
    Args:
        state: Optional state parameter for CSRF protection
        
    Returns:
        Authorization URL for Google OAuth flow
    """
    try:
        auth_url = gmail_service.get_authorization_url(state=state)
        
        logger.info("Generated Google OAuth URL", state=state)
        
        return OAuthUrlResponse(
            auth_url=auth_url,
            state=state
        )
        
    except Exception as e:
        logger.error("Failed to generate OAuth URL", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@router.post("/google/callback", response_model=OAuthTokenResponse)
async def handle_google_callback(
    request: OAuthCallbackRequest,
    gmail_service: GmailService = Depends(get_gmail_service)
) -> OAuthTokenResponse:
    """Handle Google OAuth callback.
    
    Args:
        request: OAuth callback data
        
    Returns:
        OAuth token information
    """
    try:
        credentials = await gmail_service.handle_oauth_callback(
            authorization_code=request.code,
            state=request.state
        )
        
        # Get user profile to retrieve email
        user_email = None
        if await gmail_service.health_check():
            try:
                # Access the service directly to get profile
                service = gmail_service._service
                profile = service.users().getProfile(userId='me').execute()
                user_email = profile.get('emailAddress')
            except Exception as e:
                logger.warning("Could not retrieve user email", error=str(e))
        
        logger.info(
            "OAuth callback handled successfully",
            user_email=user_email,
            has_refresh_token=bool(credentials.refresh_token)
        )
        
        return OAuthTokenResponse(
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expiry,
            user_email=user_email
        )
        
    except Exception as e:
        logger.error("OAuth callback failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.post("/google/refresh", response_model=OAuthTokenResponse)
async def refresh_google_token(
    refresh_token: str,
    gmail_service: GmailService = Depends(get_gmail_service)
) -> OAuthTokenResponse:
    """Refresh Google OAuth token.
    
    Args:
        refresh_token: Refresh token
        
    Returns:
        New OAuth token information
    """
    try:
        # Create credentials from refresh token
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=gmail_service.config.client_id,
            client_secret=gmail_service.config.client_secret
        )
        
        # Refresh credentials
        refreshed_credentials = await gmail_service.refresh_credentials(credentials)
        
        logger.info("Token refreshed successfully")
        
        return OAuthTokenResponse(
            access_token=refreshed_credentials.token,
            refresh_token=refreshed_credentials.refresh_token,
            expires_at=refreshed_credentials.expiry
        )
        
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {str(e)}"
        )