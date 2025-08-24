"""Gmail service for OAuth authentication and email processing."""

import base64
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import structlog
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ai_coaching.config.settings import GmailConfig
from ai_coaching.models.base import BaseTask

logger = structlog.get_logger(__name__)


class EmailProcessingRequest:
    """Email processing request data structure."""
    
    def __init__(
        self,
        email_id: str,
        sender_email: str,
        subject: str,
        body_content: str,
        received_timestamp: datetime,
        thread_id: Optional[str] = None
    ):
        self.email_id = email_id
        self.sender_email = sender_email
        self.subject = subject
        self.body_content = body_content
        self.received_timestamp = received_timestamp
        self.thread_id = thread_id


class GmailService:
    """Service for Gmail API operations."""
    
    def __init__(self, config: GmailConfig):
        """Initialize Gmail service.
        
        Args:
            config: Gmail configuration
        """
        self.config = config
        self._service = None
        self._credentials = None
        self._initialized = False
    
    async def initialize(self, credentials: Optional[Credentials] = None) -> None:
        """Initialize Gmail service with credentials.
        
        Args:
            credentials: Optional OAuth credentials
        """
        if self._initialized:
            return
        
        try:
            if credentials:
                self._credentials = credentials
                self._service = build('gmail', 'v1', credentials=credentials)
                
                # Test the connection
                await self.health_check()
                
                self._initialized = True
                logger.info("Gmail service initialized successfully")
            else:
                logger.warning("Gmail service initialized without credentials")
                
        except Exception as e:
            logger.error("Failed to initialize Gmail service", error=str(e))
            raise
    
    def create_oauth_flow(self, state: Optional[str] = None) -> Flow:
        """Create OAuth flow for authentication.
        
        Args:
            state: Optional state parameter for OAuth flow
            
        Returns:
            OAuth flow instance
        """
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.config.redirect_uri]
                }
            },
            scopes=self.config.scopes
        )
        
        flow.redirect_uri = self.config.redirect_uri
        
        if state:
            flow.state = state
        
        return flow
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get OAuth authorization URL.
        
        Args:
            state: Optional state parameter
            
        Returns:
            Authorization URL
        """
        flow = self.create_oauth_flow(state)
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        logger.info("Generated OAuth authorization URL")
        return auth_url
    
    async def handle_oauth_callback(self, authorization_code: str, state: Optional[str] = None) -> Credentials:
        """Handle OAuth callback and exchange code for credentials.
        
        Args:
            authorization_code: Authorization code from OAuth callback
            state: Optional state parameter
            
        Returns:
            OAuth credentials
        """
        try:
            flow = self.create_oauth_flow(state)
            flow.fetch_token(code=authorization_code)
            
            credentials = flow.credentials
            
            # Initialize the service with new credentials
            await self.initialize(credentials)
            
            logger.info("OAuth callback handled successfully")
            return credentials
            
        except Exception as e:
            logger.error("Failed to handle OAuth callback", error=str(e))
            raise
    
    async def refresh_credentials(self, credentials: Credentials) -> Credentials:
        """Refresh OAuth credentials.
        
        Args:
            credentials: Existing credentials
            
        Returns:
            Refreshed credentials
        """
        try:
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                
                # Update service with refreshed credentials
                self._credentials = credentials
                self._service = build('gmail', 'v1', credentials=credentials)
                
                logger.info("Credentials refreshed successfully")
            
            return credentials
            
        except Exception as e:
            logger.error("Failed to refresh credentials", error=str(e))
            raise
    
    async def setup_webhook_subscription(self, topic_name: str) -> Dict[str, str]:
        """Configure Gmail push notifications.
        
        Args:
            topic_name: Cloud Pub/Sub topic name
            
        Returns:
            Subscription details
        """
        if not self._service:
            raise RuntimeError("Gmail service not initialized")
        
        try:
            request = {
                'labelIds': ['INBOX'],
                'topicName': topic_name
            }
            
            result = self._service.users().watch(userId='me', body=request).execute()
            
            logger.info(
                "Gmail webhook subscription configured",
                history_id=result.get('historyId'),
                expiration=result.get('expiration')
            )
            
            return result
            
        except HttpError as e:
            logger.error("Failed to setup Gmail webhook", error=str(e))
            raise
    
    async def process_incoming_email(self, message_id: str) -> EmailProcessingRequest:
        """Parse and structure incoming email data.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Structured email processing request
        """
        if not self._service:
            raise RuntimeError("Gmail service not initialized")
        
        try:
            # Get message details
            message = self._service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message['payload'].get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}
            
            # Extract email details
            sender = header_dict.get('From', '')
            subject = header_dict.get('Subject', '')
            date_str = header_dict.get('Date', '')
            thread_id = message.get('threadId')
            
            # Parse date
            received_timestamp = datetime.utcnow()
            if date_str:
                try:
                    # Parse email date format
                    import email.utils
                    date_tuple = email.utils.parsedate_tz(date_str)
                    if date_tuple:
                        received_timestamp = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                except Exception:
                    logger.warning("Failed to parse email date", date_str=date_str)
            
            # Extract body content
            body_content = self._extract_message_body(message['payload'])
            
            # Extract sender email from "Name <email>" format
            sender_email = sender
            if '<' in sender and '>' in sender:
                sender_email = sender.split('<')[1].split('>')[0]
            
            email_request = EmailProcessingRequest(
                email_id=message_id,
                sender_email=sender_email.strip(),
                subject=subject,
                body_content=body_content,
                received_timestamp=received_timestamp,
                thread_id=thread_id
            )
            
            logger.info(
                "Email processed",
                message_id=message_id,
                sender=sender_email,
                subject=subject[:50] + '...' if len(subject) > 50 else subject
            )
            
            return email_request
            
        except HttpError as e:
            logger.error("Failed to process incoming email", error=str(e), message_id=message_id)
            raise
    
    def _extract_message_body(self, payload: Dict[str, Any]) -> str:
        """Extract text body from email payload.
        
        Args:
            payload: Email payload from Gmail API
            
        Returns:
            Extracted text content
        """
        body = ""
        
        if 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body_data = part['body']['data']
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
                elif part['mimeType'] == 'multipart/alternative':
                    # Nested multipart
                    body = self._extract_message_body(part)
                    if body:
                        break
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
                body_data = payload['body']['data']
                body = base64.urlsafe_b64decode(body_data).decode('utf-8')
        
        return body.strip()
    
    async def send_email_response(
        self,
        draft_content: str,
        thread_id: str,
        to_email: str,
        subject: str
    ) -> bool:
        """Send approved email response.
        
        Args:
            draft_content: Email content to send
            thread_id: Gmail thread ID for reply
            to_email: Recipient email address
            subject: Email subject
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self._service:
            raise RuntimeError("Gmail service not initialized")
        
        try:
            # Create message
            message = MIMEText(draft_content)
            message['to'] = to_email
            message['subject'] = subject
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            send_message = {
                'raw': raw_message,
                'threadId': thread_id
            }
            
            result = self._service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            message_id = result['id']
            
            logger.info(
                "Email sent successfully",
                message_id=message_id,
                thread_id=thread_id,
                to_email=to_email
            )
            
            return True
            
        except HttpError as e:
            logger.error(
                "Failed to send email",
                error=str(e),
                thread_id=thread_id,
                to_email=to_email
            )
            return False
    
    async def get_thread_history(self, thread_id: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a thread.
        
        Args:
            thread_id: Gmail thread ID
            max_messages: Maximum number of messages to retrieve
            
        Returns:
            List of message data
        """
        if not self._service:
            raise RuntimeError("Gmail service not initialized")
        
        try:
            thread = self._service.users().threads().get(
                userId='me',
                id=thread_id,
                format='metadata'
            ).execute()
            
            messages = thread.get('messages', [])[:max_messages]
            
            conversation_history = []
            
            for message in messages:
                headers = message['payload'].get('headers', [])
                header_dict = {h['name']: h['value'] for h in headers}
                
                conversation_history.append({
                    'message_id': message['id'],
                    'sender': header_dict.get('From', ''),
                    'subject': header_dict.get('Subject', ''),
                    'date': header_dict.get('Date', ''),
                    'snippet': message.get('snippet', '')
                })
            
            logger.info(
                "Thread history retrieved",
                thread_id=thread_id,
                message_count=len(conversation_history)
            )
            
            return conversation_history
            
        except HttpError as e:
            logger.error("Failed to get thread history", error=str(e), thread_id=thread_id)
            return []
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark email as read.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self._service:
            raise RuntimeError("Gmail service not initialized")
        
        try:
            self._service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            logger.info("Email marked as read", message_id=message_id)
            return True
            
        except HttpError as e:
            logger.error("Failed to mark email as read", error=str(e), message_id=message_id)
            return False
    
    async def health_check(self) -> bool:
        """Check Gmail service health.
        
        Returns:
            True if service is healthy, False otherwise
        """
        if not self._service:
            return False
        
        try:
            # Try to get user profile
            profile = self._service.users().getProfile(userId='me').execute()
            
            is_healthy = 'emailAddress' in profile
            
            logger.info(
                "Gmail health check completed",
                is_healthy=is_healthy,
                email=profile.get('emailAddress', 'unknown') if is_healthy else None
            )
            
            return is_healthy
            
        except Exception as e:
            logger.error("Gmail health check failed", error=str(e))
            return False