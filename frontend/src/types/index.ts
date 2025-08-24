// Core API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

// User and Authentication Types
export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  createdAt: string
  updatedAt: string
}

export type UserRole = 'admin' | 'coach' | 'assistant'

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}

export interface LoginResponse {
  user: User
  token: string
}

// Email Processing Types
export interface EmailMessage {
  id: string
  threadId: string
  subject: string
  sender: string
  senderEmail: string
  body: string
  htmlBody?: string
  receivedAt: string
  isRead: boolean
  category: EmailCategory
  priority: EmailPriority
  aiSummary?: string
  extractedInfo?: ExtractedEmailInfo
}

export type EmailCategory = 
  | 'schedule_request'
  | 'payment_inquiry'
  | 'absence_notice'
  | 'general_question'
  | 'complaint'
  | 'feedback'
  | 'emergency'
  | 'other'

export type EmailPriority = 'low' | 'medium' | 'high' | 'urgent'

export interface ExtractedEmailInfo {
  childName?: string
  sessionDate?: string
  requestType?: string
  paymentAmount?: number
  urgencyLevel?: string
  actionRequired?: string[]
}

// Schedule Management Types
export interface ScheduleSession {
  id: string
  title: string
  description?: string
  startTime: string
  endTime: string
  venue: Venue
  coach: Coach
  participants: Participant[]
  status: SessionStatus
  maxParticipants: number
  createdAt: string
  updatedAt: string
}

export type SessionStatus = 
  | 'scheduled'
  | 'confirmed'
  | 'cancelled'
  | 'completed'
  | 'in_progress'

export interface Venue {
  id: string
  name: string
  address: string
  capacity: number
  amenities: string[]
  isAvailable: boolean
}

export interface Coach {
  id: string
  name: string
  email: string
  specialties: string[]
  availability: AvailabilitySlot[]
  isActive: boolean
}

export interface AvailabilitySlot {
  dayOfWeek: number // 0-6 (Sunday to Saturday)
  startTime: string // HH:mm format
  endTime: string // HH:mm format
}

// Family and Participant Types
export interface Family {
  id: string
  familyName: string
  primaryContact: Contact
  secondaryContact?: Contact
  children: Child[]
  paymentStatus: PaymentStatus
  joinDate: string
  isActive: boolean
  specialNotes?: string
}

export interface Contact {
  name: string
  email: string
  phone: string
  relationship: string
}

export interface Child {
  id: string
  name: string
  dateOfBirth: string
  grade?: string
  skillLevel: SkillLevel
  medicalNotes?: string
  preferences?: string[]
}

export type SkillLevel = 'beginner' | 'intermediate' | 'advanced'

export interface Participant {
  childId: string
  childName: string
  familyId: string
  attendanceStatus: AttendanceStatus
}

export type AttendanceStatus = 'confirmed' | 'pending' | 'absent' | 'cancelled'

export type PaymentStatus = 'current' | 'overdue' | 'pending' | 'cancelled'

// AI Agent Types
export interface AgentResponse {
  agentType: AgentType
  response: string
  confidence: number
  suggestedActions?: string[]
  extractedData?: Record<string, any>
  timestamp: string
}

export type AgentType = 
  | 'email_processing'
  | 'schedule_optimization'
  | 'knowledge_base'
  | 'orchestrator'

// Dashboard and Analytics Types
export interface DashboardStats {
  emailsProcessed: number
  upcomingSessions: number
  activeFamilies: number
  aiInsights: number
  pendingTasks: number
}

export interface ActivityLog {
  id: string
  type: ActivityType
  description: string
  agentType?: AgentType
  timestamp: string
  priority: 'low' | 'medium' | 'high'
}

export type ActivityType = 
  | 'email_processed'
  | 'session_scheduled'
  | 'payment_received'
  | 'conflict_detected'
  | 'insight_generated'
  | 'task_completed'

// Form and UI Types
export interface FormField {
  id: string
  label: string
  type: 'text' | 'email' | 'textarea' | 'select' | 'date' | 'time'
  required: boolean
  options?: { value: string; label: string }[]
  validation?: ValidationRule[]
}

export interface ValidationRule {
  type: 'required' | 'email' | 'minLength' | 'maxLength' | 'pattern'
  value?: string | number
  message: string
}

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}