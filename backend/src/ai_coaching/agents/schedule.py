"""Schedule Agent for conflict detection and schedule optimization."""

import asyncio
import time
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
import math

import structlog
from pydantic import BaseModel, Field, validator

from ai_coaching.agents.base import BaseAgent, AgentTask
from ai_coaching.models.base import BaseAgentOutput, SystemDependencies
from ai_coaching.services.airtable import AirtableService

logger = structlog.get_logger(__name__)


class ConflictType(Enum):
    """Types of schedule conflicts."""
    COACH_DOUBLE_BOOKING = "coach_double_booking"
    VENUE_OVERLAP = "venue_overlap" 
    TRAVEL_IMPOSSIBLE = "travel_impossible"
    COACH_OVERLOAD = "coach_overload"
    VENUE_UNAVAILABLE = "venue_unavailable"
    TIME_CONSTRAINT = "time_constraint"


class ConflictSeverity(Enum):
    """Severity levels for conflicts."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScheduleEvent(BaseModel):
    """Schedule event model."""
    event_id: str = Field(..., description="Unique event identifier")
    event_name: str = Field(..., description="Event name")
    event_type: str = Field(..., description="Type of event (practice, game, training)")
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    venue_id: str = Field(..., description="Venue identifier")
    venue_name: str = Field(..., description="Venue name")
    venue_location: str = Field(..., description="Venue address/location")
    assigned_coaches: List[str] = Field(default_factory=list, description="List of assigned coach IDs")
    required_coaches: int = Field(1, description="Number of coaches required")
    team_id: Optional[str] = Field(None, description="Team identifier if applicable")
    age_group: str = Field(..., description="Age group (U8, U10, etc.)")
    priority: int = Field(5, ge=1, le=10, description="Event priority (1=lowest, 10=highest)")
    is_flexible: bool = Field(True, description="Whether event time can be adjusted")
    travel_time_required: int = Field(15, description="Travel time to venue in minutes")
    
    @validator('end_time')
    def end_after_start(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class Coach(BaseModel):
    """Coach model with availability and expertise."""
    coach_id: str = Field(..., description="Unique coach identifier")
    name: str = Field(..., description="Coach name")
    email: str = Field(..., description="Coach email")
    expertise_levels: List[str] = Field(default_factory=list, description="Age groups coach can handle")
    max_events_per_day: int = Field(4, description="Maximum events coach can handle per day")
    availability_windows: List[Dict[str, Any]] = Field(default_factory=list, description="Available time windows")
    travel_speed_mph: int = Field(30, description="Average travel speed for distance calculations")
    current_workload: int = Field(0, description="Current number of assigned events")
    

class Venue(BaseModel):
    """Venue model with capacity and availability."""
    venue_id: str = Field(..., description="Unique venue identifier") 
    name: str = Field(..., description="Venue name")
    location: str = Field(..., description="Venue address")
    capacity: int = Field(..., description="Maximum capacity")
    field_count: int = Field(1, description="Number of fields/courts available")
    available_hours: Dict[str, List[str]] = Field(default_factory=dict, description="Available hours by day")
    latitude: Optional[float] = Field(None, description="Venue latitude for distance calculations")
    longitude: Optional[float] = Field(None, description="Venue longitude for distance calculations")


class ScheduleConflict(BaseModel):
    """Detected schedule conflict."""
    conflict_id: str = Field(..., description="Unique conflict identifier")
    conflict_type: ConflictType = Field(..., description="Type of conflict")
    severity: ConflictSeverity = Field(..., description="Conflict severity")
    affected_events: List[str] = Field(..., description="List of affected event IDs")
    affected_resources: List[str] = Field(..., description="Affected coaches/venues")
    description: str = Field(..., description="Human-readable conflict description")
    suggested_resolutions: List[Dict[str, Any]] = Field(default_factory=list, description="Suggested fixes")
    auto_resolvable: bool = Field(False, description="Whether conflict can be auto-resolved")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="When conflict was detected")


class ScheduleOptimization(BaseModel):
    """Schedule optimization result."""
    original_conflicts: int = Field(..., description="Number of conflicts before optimization")
    resolved_conflicts: int = Field(..., description="Number of conflicts resolved")
    remaining_conflicts: List[ScheduleConflict] = Field(default_factory=list, description="Unresolved conflicts")
    optimizations_applied: List[str] = Field(default_factory=list, description="List of optimizations applied")
    coach_workload_balance: float = Field(..., description="Coach workload balance score (0-1)")
    venue_utilization: float = Field(..., description="Venue utilization efficiency (0-1)")
    travel_efficiency: float = Field(..., description="Travel efficiency score (0-1)")
    overall_score: float = Field(..., description="Overall optimization score (0-1)")


class ScheduleAgent(BaseAgent):
    """Agent responsible for schedule conflict detection and optimization.
    
    This agent:
    - Analyzes events and detects scheduling conflicts
    - Identifies coach double-booking and venue overlaps
    - Detects travel impossibilities between venues
    - Optimizes coach assignments based on expertise and workload
    - Suggests conflict resolutions with priority ranking
    - Validates schedule feasibility
    - Provides real-time notifications for conflicts
    - Targets <5 second performance for conflict detection
    """
    
    def __init__(
        self,
        dependencies: SystemDependencies,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Schedule Agent.
        
        Args:
            dependencies: System dependencies including database and services
            config: Agent-specific configuration
        """
        super().__init__("ScheduleAgent", dependencies, config)
        
        # Initialize services
        self.airtable_service: Optional[AirtableService] = None
        
        # Performance configuration
        self.target_processing_time = 5.0  # Target <5 seconds
        self.max_travel_distance_miles = config.get("max_travel_distance", 50) if config else 50
        self.min_travel_time_minutes = config.get("min_travel_time", 10) if config else 10
        
        # Optimization weights
        self.conflict_weights = {
            ConflictType.COACH_DOUBLE_BOOKING: 1.0,
            ConflictType.VENUE_OVERLAP: 0.9,
            ConflictType.TRAVEL_IMPOSSIBLE: 0.8,
            ConflictType.COACH_OVERLOAD: 0.6,
            ConflictType.VENUE_UNAVAILABLE: 0.7,
            ConflictType.TIME_CONSTRAINT: 0.5
        }
        
        # Caching for performance
        self._venue_cache: Dict[str, Venue] = {}
        self._coach_cache: Dict[str, Coach] = {}
        self._distance_cache: Dict[Tuple[str, str], float] = {}
        self._cache_ttl = 300  # 5 minutes
        
    async def _initialize_agent(self) -> None:
        """Initialize agent-specific components."""
        try:
            # Initialize Airtable service if available
            if hasattr(self.dependencies, 'airtable_service'):
                self.airtable_service = self.dependencies.airtable_service
                self.logger.info("Airtable service initialized")
            
            # Load initial cache data
            await self._load_cache_data()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ScheduleAgent: {str(e)}")
            raise
    
    async def _load_cache_data(self) -> None:
        """Load frequently used data into cache."""
        try:
            # Load venues and coaches from Airtable if available
            if self.airtable_service:
                # This would be implemented based on actual Airtable schema
                # For now, we'll use mock data in tests
                pass
            
        except Exception as e:
            self.logger.warning(f"Failed to load cache data: {str(e)}")
    
    async def process_task(self, task: AgentTask) -> BaseAgentOutput:
        """Process a schedule analysis task.
        
        Args:
            task: Schedule task (conflict_detection, optimization, validation)
            
        Returns:
            BaseAgentOutput with conflict analysis and suggestions
        """
        start_time = time.time()
        
        try:
            task_type = task.task_type
            task_data = task.input_data
            
            if task_type == "detect_conflicts":
                result = await self._detect_conflicts(task_data)
            elif task_type == "optimize_schedule":
                result = await self._optimize_schedule(task_data)
            elif task_type == "validate_schedule":
                result = await self._validate_schedule(task_data)
            elif task_type == "suggest_resolutions":
                result = await self._suggest_resolutions(task_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            processing_time = time.time() - start_time
            
            # Check performance target
            if processing_time > self.target_processing_time:
                self.logger.warning(
                    f"Processing exceeded target time: {processing_time:.2f}s > {self.target_processing_time}s",
                    task_type=task_type
                )
            
            return BaseAgentOutput(
                success=True,
                confidence_score=result.get('confidence_score', 0.9),
                result_data=result,
                processing_time=processing_time,
                metadata={
                    "task_type": task_type,
                    "events_processed": len(task_data.get('events', [])),
                    "conflicts_found": len(result.get('conflicts', []))
                }
            )
            
        except Exception as e:
            self.logger.error(f"Schedule processing failed: {str(e)}", task_id=task.task_id)
            processing_time = time.time() - start_time
            
            return BaseAgentOutput(
                success=False,
                confidence_score=0.0,
                result_data={"error": str(e)},
                error_message=str(e),
                processing_time=processing_time
            )
    
    async def _detect_conflicts(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect conflicts in the provided schedule.
        
        Args:
            task_data: Dictionary containing 'events', 'coaches', 'venues'
            
        Returns:
            Dictionary with detected conflicts and analysis
        """
        events = [ScheduleEvent(**event) for event in task_data.get('events', [])]
        coaches = {c['coach_id']: Coach(**c) for c in task_data.get('coaches', [])}
        venues = {v['venue_id']: Venue(**v) for v in task_data.get('venues', [])}
        
        conflicts = []
        
        # Run conflict detection algorithms in parallel
        conflict_tasks = [
            self._detect_coach_conflicts(events, coaches),
            self._detect_venue_conflicts(events, venues),
            self._detect_travel_conflicts(events, venues),
            self._detect_workload_conflicts(events, coaches)
        ]
        
        conflict_results = await asyncio.gather(*conflict_tasks, return_exceptions=True)
        
        # Combine all detected conflicts
        for result in conflict_results:
            if isinstance(result, list):
                conflicts.extend(result)
            elif isinstance(result, Exception):
                self.logger.warning(f"Conflict detection failed: {str(result)}")
        
        # Sort conflicts by severity and priority
        conflicts.sort(key=lambda c: (
            self._get_severity_weight(c.severity),
            max([e.priority for e in events if e.event_id in c.affected_events], default=0)
        ), reverse=True)
        
        return {
            'conflicts': [c.dict() for c in conflicts],
            'total_conflicts': len(conflicts),
            'conflict_summary': self._generate_conflict_summary(conflicts),
            'confidence_score': 0.95 if conflicts else 1.0,
            'recommendations': self._generate_recommendations(conflicts)
        }
    
    async def _detect_coach_conflicts(self, events: List[ScheduleEvent], coaches: Dict[str, Coach]) -> List[ScheduleConflict]:
        """Detect coach-related conflicts."""
        conflicts = []
        
        # Group events by coach
        coach_events = {}
        for event in events:
            for coach_id in event.assigned_coaches:
                if coach_id not in coach_events:
                    coach_events[coach_id] = []
                coach_events[coach_id].append(event)
        
        # Check for double-booking
        for coach_id, coach_event_list in coach_events.items():
            # Sort events by start time
            sorted_events = sorted(coach_event_list, key=lambda e: e.start_time)
            
            for i in range(len(sorted_events) - 1):
                current_event = sorted_events[i]
                next_event = sorted_events[i + 1]
                
                # Check for time overlap
                if current_event.end_time > next_event.start_time:
                    coach = coaches.get(coach_id)
                    coach_name = coach.name if coach else 'Unknown'
                    
                    conflicts.append(ScheduleConflict(
                        conflict_id=f"coach_double_{coach_id}_{current_event.event_id}_{next_event.event_id}",
                        conflict_type=ConflictType.COACH_DOUBLE_BOOKING,
                        severity=ConflictSeverity.HIGH,
                        affected_events=[current_event.event_id, next_event.event_id],
                        affected_resources=[coach_id],
                        description=f"Coach {coach_name} is double-booked between {current_event.event_name} and {next_event.event_name}",
                        auto_resolvable=True
                    ))
        
        return conflicts
    
    async def _detect_venue_conflicts(self, events: List[ScheduleEvent], venues: Dict[str, Venue]) -> List[ScheduleConflict]:
        """Detect venue-related conflicts."""
        conflicts = []
        
        # Group events by venue and check for overlaps
        venue_events = {}
        for event in events:
            if event.venue_id not in venue_events:
                venue_events[event.venue_id] = []
            venue_events[event.venue_id].append(event)
        
        for venue_id, venue_event_list in venue_events.items():
            venue = venues.get(venue_id)
            if not venue:
                continue
            
            # Sort by start time
            sorted_events = sorted(venue_event_list, key=lambda e: e.start_time)
            
            # Check capacity and field availability
            for i in range(len(sorted_events)):
                for j in range(i + 1, len(sorted_events)):
                    event1 = sorted_events[i]
                    event2 = sorted_events[j]
                    
                    # Check for time overlap
                    if event1.end_time > event2.start_time and event1.start_time < event2.end_time:
                        # If venue has multiple fields, check if conflict is real
                        if venue.field_count <= 1:
                            conflicts.append(ScheduleConflict(
                                conflict_id=f"venue_overlap_{venue_id}_{event1.event_id}_{event2.event_id}",
                                conflict_type=ConflictType.VENUE_OVERLAP,
                                severity=ConflictSeverity.HIGH,
                                affected_events=[event1.event_id, event2.event_id],
                                affected_resources=[venue_id],
                                description=f"Venue {venue.name} has overlapping events: {event1.event_name} and {event2.event_name}",
                                auto_resolvable=event1.is_flexible or event2.is_flexible
                            ))
        
        return conflicts
    
    async def _detect_travel_conflicts(self, events: List[ScheduleEvent], venues: Dict[str, Venue]) -> List[ScheduleConflict]:
        """Detect impossible travel scenarios between venues."""
        conflicts = []
        
        # Group events by coach and check travel feasibility
        coach_events = {}
        for event in events:
            for coach_id in event.assigned_coaches:
                if coach_id not in coach_events:
                    coach_events[coach_id] = []
                coach_events[coach_id].append(event)
        
        for coach_id, coach_event_list in coach_events.items():
            sorted_events = sorted(coach_event_list, key=lambda e: e.start_time)
            
            for i in range(len(sorted_events) - 1):
                current_event = sorted_events[i]
                next_event = sorted_events[i + 1]
                
                # Calculate required travel time
                travel_time_needed = await self._calculate_travel_time(
                    current_event.venue_id,
                    next_event.venue_id,
                    venues
                )
                
                # Available time between events
                available_time = (next_event.start_time - current_event.end_time).total_seconds() / 60
                
                if travel_time_needed > available_time:
                    conflicts.append(ScheduleConflict(
                        conflict_id=f"travel_impossible_{coach_id}_{current_event.event_id}_{next_event.event_id}",
                        conflict_type=ConflictType.TRAVEL_IMPOSSIBLE,
                        severity=ConflictSeverity.CRITICAL,
                        affected_events=[current_event.event_id, next_event.event_id],
                        affected_resources=[coach_id],
                        description=f"Insufficient travel time for coach between {current_event.venue_name} and {next_event.venue_name} ({travel_time_needed:.0f} min needed, {available_time:.0f} min available)",
                        auto_resolvable=current_event.is_flexible or next_event.is_flexible
                    ))
        
        return conflicts
    
    async def _detect_workload_conflicts(self, events: List[ScheduleEvent], coaches: Dict[str, Coach]) -> List[ScheduleConflict]:
        """Detect coach workload conflicts."""
        conflicts = []
        
        # Check daily workload for each coach
        coach_daily_events = {}
        
        for event in events:
            event_date = event.start_time.date()
            
            for coach_id in event.assigned_coaches:
                if coach_id not in coach_daily_events:
                    coach_daily_events[coach_id] = {}
                if event_date not in coach_daily_events[coach_id]:
                    coach_daily_events[coach_id][event_date] = []
                
                coach_daily_events[coach_id][event_date].append(event)
        
        for coach_id, daily_events in coach_daily_events.items():
            coach = coaches.get(coach_id)
            if not coach:
                continue
            
            for date, date_events in daily_events.items():
                if len(date_events) > coach.max_events_per_day:
                    conflicts.append(ScheduleConflict(
                        conflict_id=f"workload_overload_{coach_id}_{date}",
                        conflict_type=ConflictType.COACH_OVERLOAD,
                        severity=ConflictSeverity.MEDIUM,
                        affected_events=[e.event_id for e in date_events],
                        affected_resources=[coach_id],
                        description=f"Coach {coach.name} assigned to {len(date_events)} events on {date} (max: {coach.max_events_per_day})",
                        auto_resolvable=any(e.is_flexible for e in date_events)
                    ))
        
        return conflicts
    
    async def _calculate_travel_time(self, venue1_id: str, venue2_id: str, venues: Dict[str, Venue]) -> float:
        """Calculate travel time between venues in minutes."""
        if venue1_id == venue2_id:
            return 0.0
        
        # Check cache first
        cache_key = (venue1_id, venue2_id)
        if cache_key in self._distance_cache:
            distance = self._distance_cache[cache_key]
        else:
            venue1 = venues.get(venue1_id)
            venue2 = venues.get(venue2_id)
            
            if not venue1 or not venue2:
                return self.min_travel_time_minutes
            
            # Calculate distance if coordinates available
            if (venue1.latitude and venue1.longitude and 
                venue2.latitude and venue2.longitude):
                distance = self._calculate_distance(
                    venue1.latitude, venue1.longitude,
                    venue2.latitude, venue2.longitude
                )
            else:
                # Use default distance based on location strings
                distance = 10.0  # Default 10 miles
            
            # Cache the result
            self._distance_cache[cache_key] = distance
        
        # Convert distance to travel time (assuming 30 mph average)
        travel_time = (distance / 30.0) * 60  # minutes
        return max(travel_time, self.min_travel_time_minutes)
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in miles using Haversine formula."""
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in miles
        earth_radius = 3959
        
        return earth_radius * c
    
    async def _optimize_schedule(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize the schedule to resolve conflicts and improve efficiency."""
        # This would implement optimization algorithms
        # For now, return a placeholder result
        return {
            'optimization_applied': True,
            'conflicts_resolved': 0,
            'optimization_score': 0.8,
            'message': 'Schedule optimization not yet implemented'
        }
    
    async def _validate_schedule(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate schedule feasibility."""
        conflicts = await self._detect_conflicts(task_data)
        
        return {
            'is_valid': len(conflicts['conflicts']) == 0,
            'validation_score': 1.0 - (len(conflicts['conflicts']) * 0.1),
            'issues_found': conflicts['conflicts'],
            'recommendations': conflicts['recommendations']
        }
    
    async def _suggest_resolutions(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest resolutions for detected conflicts."""
        conflicts = await self._detect_conflicts(task_data)
        
        resolutions = []
        for conflict_data in conflicts['conflicts']:
            conflict = ScheduleConflict(**conflict_data)
            
            if conflict.conflict_type == ConflictType.COACH_DOUBLE_BOOKING:
                resolutions.append({
                    'conflict_id': conflict.conflict_id,
                    'resolution_type': 'reassign_coach',
                    'description': 'Assign a different coach to one of the conflicting events',
                    'priority': 'high',
                    'estimated_effort': 'low'
                })
            elif conflict.conflict_type == ConflictType.VENUE_OVERLAP:
                resolutions.append({
                    'conflict_id': conflict.conflict_id,
                    'resolution_type': 'reschedule_event',
                    'description': 'Move one event to a different time or venue',
                    'priority': 'high',
                    'estimated_effort': 'medium'
                })
            # Add more resolution types as needed
        
        return {
            'suggested_resolutions': resolutions,
            'auto_resolvable_count': sum(1 for c in conflicts['conflicts'] if c.get('auto_resolvable', False)),
            'manual_review_required': len(resolutions) - sum(1 for r in resolutions if r.get('priority') == 'low')
        }
    
    def _generate_conflict_summary(self, conflicts: List[ScheduleConflict]) -> Dict[str, int]:
        """Generate summary of conflicts by type and severity."""
        summary = {
            'by_type': {},
            'by_severity': {},
            'total': len(conflicts)
        }
        
        for conflict in conflicts:
            # Count by type
            type_name = conflict.conflict_type.value
            summary['by_type'][type_name] = summary['by_type'].get(type_name, 0) + 1
            
            # Count by severity
            severity_name = conflict.severity.value
            summary['by_severity'][severity_name] = summary['by_severity'].get(severity_name, 0) + 1
        
        return summary
    
    def _generate_recommendations(self, conflicts: List[ScheduleConflict]) -> List[str]:
        """Generate high-level recommendations based on conflicts."""
        recommendations = []
        
        if any(c.conflict_type == ConflictType.COACH_DOUBLE_BOOKING for c in conflicts):
            recommendations.append("Review coach assignments and consider hiring additional coaches")
        
        if any(c.conflict_type == ConflictType.VENUE_OVERLAP for c in conflicts):
            recommendations.append("Negotiate additional venue time slots or find alternative locations")
        
        if any(c.conflict_type == ConflictType.TRAVEL_IMPOSSIBLE for c in conflicts):
            recommendations.append("Adjust event timing to allow adequate travel time between venues")
        
        if any(c.severity == ConflictSeverity.CRITICAL for c in conflicts):
            recommendations.append("Address critical conflicts immediately to avoid disruption")
        
        return recommendations
    
    def _get_severity_weight(self, severity: ConflictSeverity) -> float:
        """Get numeric weight for conflict severity."""
        weights = {
            ConflictSeverity.LOW: 1.0,
            ConflictSeverity.MEDIUM: 2.0,
            ConflictSeverity.HIGH: 3.0,
            ConflictSeverity.CRITICAL: 4.0
        }
        return weights.get(severity, 1.0)
    
    async def _agent_health_check(self) -> bool:
        """Perform agent-specific health checks."""
        try:
            # Check if we can access Airtable service
            if self.airtable_service:
                # Could add specific health check
                pass
            
            # Check cache sizes (prevent memory leaks)
            if len(self._distance_cache) > 10000:
                # Clear old cache entries
                self._distance_cache.clear()
                self.logger.info("Cleared distance cache due to size limit")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False
    
    async def _shutdown_agent(self) -> None:
        """Perform agent-specific shutdown tasks."""
        try:
            # Clear all caches
            self._venue_cache.clear()
            self._coach_cache.clear()
            self._distance_cache.clear()
            
            self.logger.info("ScheduleAgent shutdown completed")
            
        except Exception as e:
            self.logger.error(f"Shutdown error: {str(e)}")