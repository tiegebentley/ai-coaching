"""Airtable integration service for family data and schedule management."""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, UTC
import time

import structlog
from airtable import Airtable
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ai_coaching.config.settings import AirtableConfig

logger = structlog.get_logger(__name__)


class AirtableRateLimiter:
    """Rate limiter for Airtable API requests."""
    
    def __init__(self, requests_per_second: float = 5.0):
        """Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum requests per second
        """
        self._requests_per_second = requests_per_second
        self._min_interval = 1.0 / requests_per_second
        self._last_request = 0.0
    
    async def acquire(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = time.time()
        time_since_last = now - self._last_request
        
        if time_since_last < self._min_interval:
            wait_time = self._min_interval - time_since_last
            logger.debug("Rate limiting Airtable request", wait_time=wait_time)
            await asyncio.sleep(wait_time)
        
        self._last_request = time.time()


class AirtableService:
    """Service for managing Airtable integration."""
    
    def __init__(self, config: AirtableConfig):
        """Initialize Airtable service.
        
        Args:
            config: Airtable configuration
        """
        self.config = config
        self._client: Optional[Airtable] = None
        self._rate_limiter = AirtableRateLimiter(config.rate_limit_rps)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize Airtable client."""
        if self._initialized:
            return
        
        try:
            self._client = Airtable(
                base_id=self.config.base_id,
                api_key=self.config.api_key
            )
            
            # Test the connection by trying to access a table
            await self.health_check()
            
            self._initialized = True
            logger.info("Airtable service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Airtable service", error=str(e))
            raise
    
    @property
    def client(self) -> Airtable:
        """Get Airtable client instance."""
        if not self._client:
            raise RuntimeError("Airtable service not initialized")
        return self._client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_family_info(self, email: str) -> Dict[str, Any]:
        """Retrieve family information by email lookup.
        
        Args:
            email: Email address to search for
            
        Returns:
            Family information dictionary
        """
        try:
            await self._rate_limiter.acquire()
            
            # Search for family by email in the contacts table
            # Note: Adjust table name and field names based on actual Airtable schema
            records = await asyncio.to_thread(
                self.client.get_all,
                'Families',  # Adjust table name
                formula=f"{{{{Email}}}} = '{email}'"
            )
            
            if not records:
                logger.info("No family found for email", email=email)
                return {}
            
            # Get the first matching record
            family_record = records[0]
            
            # Extract and structure family data
            family_data = {
                'family_id': family_record['id'],
                'email': family_record['fields'].get('Email', ''),
                'family_name': family_record['fields'].get('Family Name', ''),
                'primary_contact': family_record['fields'].get('Primary Contact', ''),
                'phone': family_record['fields'].get('Phone', ''),
                'address': family_record['fields'].get('Address', ''),
                'children': [],
                'payment_status': family_record['fields'].get('Payment Status', 'unknown'),
                'notes': family_record['fields'].get('Notes', ''),
                'created_at': family_record.get('createdTime', ''),
                'updated_at': datetime.now(UTC).isoformat()
            }
            
            # Get children information if linked
            children_ids = family_record['fields'].get('Children', [])
            if children_ids:
                family_data['children'] = await self._get_children_info(children_ids)
            
            logger.info(
                "Family info retrieved",
                email=email,
                family_id=family_data['family_id'],
                children_count=len(family_data['children'])
            )
            
            return family_data
            
        except Exception as e:
            logger.error(
                "Failed to get family info",
                error=str(e),
                email=email
            )
            raise
    
    async def _get_children_info(self, children_ids: List[str]) -> List[Dict[str, Any]]:
        """Get information for children records.
        
        Args:
            children_ids: List of Airtable record IDs for children
            
        Returns:
            List of children information
        """
        children = []
        
        for child_id in children_ids:
            try:
                await self._rate_limiter.acquire()
                
                child_record = await asyncio.to_thread(
                    self.client.get,
                    'Children',  # Adjust table name
                    child_id
                )
                
                if child_record:
                    child_data = {
                        'child_id': child_record['id'],
                        'name': child_record['fields'].get('Name', ''),
                        'age': child_record['fields'].get('Age', ''),
                        'team': child_record['fields'].get('Team', ''),
                        'position': child_record['fields'].get('Position', ''),
                        'coach': child_record['fields'].get('Coach', ''),
                        'medical_notes': child_record['fields'].get('Medical Notes', ''),
                        'emergency_contact': child_record['fields'].get('Emergency Contact', '')
                    }
                    children.append(child_data)
                    
            except Exception as e:
                logger.error(
                    "Failed to get child info",
                    error=str(e),
                    child_id=child_id
                )
                # Continue with other children even if one fails
                continue
        
        return children
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_schedule_data(self, family_id: Optional[str] = None) -> Dict[str, Any]:
        """Get schedule information for family or organization.
        
        Args:
            family_id: Optional family ID to filter schedule
            
        Returns:
            Schedule data dictionary
        """
        try:
            await self._rate_limiter.acquire()
            
            # Build formula for filtering if family_id provided
            formula = None
            if family_id:
                formula = f"{{{{Family}}}} = '{family_id}'"
            
            # Get schedule records
            records = await asyncio.to_thread(
                self.client.get_all,
                'Schedule',  # Adjust table name
                formula=formula
            )
            
            schedule_data = {
                'events': [],
                'coaches': set(),
                'venues': set(),
                'teams': set()
            }
            
            for record in records:
                fields = record['fields']
                
                event = {
                    'event_id': record['id'],
                    'title': fields.get('Title', ''),
                    'date': fields.get('Date', ''),
                    'start_time': fields.get('Start Time', ''),
                    'end_time': fields.get('End Time', ''),
                    'venue': fields.get('Venue', ''),
                    'team': fields.get('Team', ''),
                    'coach': fields.get('Coach', ''),
                    'event_type': fields.get('Event Type', ''),  # practice, game, etc.
                    'status': fields.get('Status', 'scheduled'),
                    'notes': fields.get('Notes', '')
                }
                
                schedule_data['events'].append(event)
                
                # Collect unique values for analysis
                if event['coach']:
                    schedule_data['coaches'].add(event['coach'])
                if event['venue']:
                    schedule_data['venues'].add(event['venue'])
                if event['team']:
                    schedule_data['teams'].add(event['team'])
            
            # Convert sets to lists for JSON serialization
            schedule_data['coaches'] = list(schedule_data['coaches'])
            schedule_data['venues'] = list(schedule_data['venues'])
            schedule_data['teams'] = list(schedule_data['teams'])
            
            logger.info(
                "Schedule data retrieved",
                family_id=family_id,
                events_count=len(schedule_data['events']),
                coaches_count=len(schedule_data['coaches']),
                venues_count=len(schedule_data['venues'])
            )
            
            return schedule_data
            
        except Exception as e:
            logger.error(
                "Failed to get schedule data",
                error=str(e),
                family_id=family_id
            )
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def get_payment_status(self, family_id: str) -> Dict[str, Any]:
        """Check payment status and history for a family.
        
        Args:
            family_id: Family record ID
            
        Returns:
            Payment status information
        """
        try:
            await self._rate_limiter.acquire()
            
            # Get payment records for the family
            records = await asyncio.to_thread(
                self.client.get_all,
                'Payments',  # Adjust table name
                formula=f"{{{{Family}}}} = '{family_id}'"
            )
            
            payment_data = {
                'family_id': family_id,
                'current_balance': 0.0,
                'total_paid': 0.0,
                'total_owed': 0.0,
                'last_payment_date': None,
                'payment_history': [],
                'status': 'current'  # current, overdue, paid_ahead
            }
            
            for record in records:
                fields = record['fields']
                
                payment = {
                    'payment_id': record['id'],
                    'amount': fields.get('Amount', 0.0),
                    'date': fields.get('Date', ''),
                    'description': fields.get('Description', ''),
                    'method': fields.get('Payment Method', ''),
                    'status': fields.get('Status', 'pending')
                }
                
                payment_data['payment_history'].append(payment)
                
                # Calculate totals
                if payment['status'] == 'completed':
                    payment_data['total_paid'] += payment['amount']
                    
                    # Track last payment date
                    if payment['date']:
                        if not payment_data['last_payment_date'] or payment['date'] > payment_data['last_payment_date']:
                            payment_data['last_payment_date'] = payment['date']
            
            # Get current balance from family record
            family_record = await asyncio.to_thread(
                self.client.get,
                'Families',
                family_id
            )
            
            if family_record:
                payment_data['current_balance'] = family_record['fields'].get('Balance', 0.0)
                payment_data['total_owed'] = family_record['fields'].get('Total Owed', 0.0)
                
                # Determine payment status
                if payment_data['current_balance'] > 0:
                    payment_data['status'] = 'overdue'
                elif payment_data['current_balance'] < 0:
                    payment_data['status'] = 'paid_ahead'
                else:
                    payment_data['status'] = 'current'
            
            logger.info(
                "Payment status retrieved",
                family_id=family_id,
                balance=payment_data['current_balance'],
                status=payment_data['status']
            )
            
            return payment_data
            
        except Exception as e:
            logger.error(
                "Failed to get payment status",
                error=str(e),
                family_id=family_id
            )
            raise
    
    async def check_venue_availability(self, venue_id: str, time_slot: str) -> bool:
        """Verify venue availability for scheduling.
        
        Args:
            venue_id: Venue identifier
            time_slot: Time slot in ISO format
            
        Returns:
            True if venue is available, False otherwise
        """
        try:
            await self._rate_limiter.acquire()
            
            # Check for conflicting events at the same venue and time
            formula = f"AND({{{{Venue}}}} = '{venue_id}', {{{{Start Time}}}} = '{time_slot}')"
            
            conflicts = await asyncio.to_thread(
                self.client.get_all,
                'Schedule',
                formula=formula
            )
            
            is_available = len(conflicts) == 0
            
            logger.info(
                "Venue availability checked",
                venue_id=venue_id,
                time_slot=time_slot,
                is_available=is_available,
                conflicts=len(conflicts)
            )
            
            return is_available
            
        except Exception as e:
            logger.error(
                "Failed to check venue availability",
                error=str(e),
                venue_id=venue_id,
                time_slot=time_slot
            )
            return False
    
    async def update_communication_log(self, family_id: str, interaction: Dict[str, Any]) -> bool:
        """Log communication interactions.
        
        Args:
            family_id: Family record ID
            interaction: Interaction details
            
        Returns:
            True if logged successfully, False otherwise
        """
        try:
            await self._rate_limiter.acquire()
            
            # Prepare log entry
            log_data = {
                'Family': [family_id],
                'Date': datetime.now(UTC).isoformat(),
                'Type': interaction.get('type', 'email'),
                'Subject': interaction.get('subject', ''),
                'Content': interaction.get('content', ''),
                'AI Generated': interaction.get('ai_generated', False),
                'Confidence Score': interaction.get('confidence_score', 0.0),
                'Status': interaction.get('status', 'sent')
            }
            
            # Create log entry
            result = await asyncio.to_thread(
                self.client.insert,
                'Communication_Log',  # Adjust table name
                log_data
            )
            
            success = bool(result)
            
            logger.info(
                "Communication logged",
                family_id=family_id,
                type=interaction.get('type'),
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to log communication",
                error=str(e),
                family_id=family_id
            )
            return False
    
    async def health_check(self) -> bool:
        """Check Airtable service health.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            await self._rate_limiter.acquire()
            
            # Try to access the Families table
            records = await asyncio.to_thread(
                self.client.get_all,
                'Families',
                max_records=1
            )
            
            is_healthy = isinstance(records, list)
            
            logger.info(
                "Airtable health check completed",
                is_healthy=is_healthy
            )
            
            return is_healthy
            
        except Exception as e:
            logger.error("Airtable health check failed", error=str(e))
            return False