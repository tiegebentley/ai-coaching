import { create } from 'zustand'
import type { DashboardStats, ActivityLog, EmailMessage, ScheduleSession, ApiResponse } from '@/types'
import { apiClient } from '@/lib/api'

interface DashboardStore {
  stats: DashboardStats | null
  activities: ActivityLog[]
  recentEmails: EmailMessage[]
  upcomingSessions: ScheduleSession[]
  isLoading: boolean
  error: string | null

  // Actions
  loadDashboardData: () => Promise<void>
  loadStats: () => Promise<void>
  loadActivities: () => Promise<void>
  loadRecentEmails: () => Promise<void>
  loadUpcomingSessions: () => Promise<void>
  refreshDashboard: () => Promise<void>
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const useDashboardStore = create<DashboardStore>((set, get) => ({
  stats: {
    emailsProcessed: 0,
    upcomingSessions: 0,
    activeFamilies: 0,
    aiInsights: 0,
    pendingTasks: 0,
  },
  activities: [],
  recentEmails: [],
  upcomingSessions: [],
  isLoading: false,
  error: null,

  loadDashboardData: async () => {
    set({ isLoading: true, error: null })
    
    try {
      await Promise.all([
        get().loadStats(),
        get().loadActivities(),
        get().loadRecentEmails(),
        get().loadUpcomingSessions(),
      ])
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
      set({ error: 'Failed to load dashboard data' })
    } finally {
      set({ isLoading: false })
    }
  },

  loadStats: async () => {
    try {
      const response = await apiClient.getDashboardStats() as ApiResponse<DashboardStats>
      if (response.success && response.data) {
        set({ stats: response.data })
      }
    } catch (error) {
      console.error('Failed to load dashboard stats:', error)
      throw error
    }
  },

  loadActivities: async () => {
    try {
      const response = await apiClient.getActivityLog(10) as ApiResponse<ActivityLog[]>
      if (response.success && response.data) {
        set({ activities: response.data })
      }
    } catch (error) {
      console.error('Failed to load activities:', error)
      throw error
    }
  },

  loadRecentEmails: async () => {
    try {
      const response = await apiClient.getEmails({ limit: 5, isRead: false }) as ApiResponse<EmailMessage[]>
      if (response.success && response.data) {
        set({ recentEmails: response.data })
      }
    } catch (error) {
      console.error('Failed to load recent emails:', error)
      throw error
    }
  },

  loadUpcomingSessions: async () => {
    try {
      const today = new Date().toISOString().split('T')[0]
      const nextWeek = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
        .toISOString().split('T')[0]
      
      const response = await apiClient.getSessions({
        limit: 10,
        startDate: today,
        endDate: nextWeek,
        status: 'scheduled'
      }) as ApiResponse<ScheduleSession[]>
      
      if (response.success && response.data) {
        set({ upcomingSessions: response.data })
      }
    } catch (error) {
      console.error('Failed to load upcoming sessions:', error)
      throw error
    }
  },

  refreshDashboard: async () => {
    await get().loadDashboardData()
  },

  setLoading: (loading) => {
    set({ isLoading: loading })
  },

  setError: (error) => {
    set({ error })
  },
}))

// Utility hook for dashboard stats with default values
export const useDashboardStats = () => {
  const stats = useDashboardStore((state) => state.stats)
  
  return {
    emailsProcessed: stats?.emailsProcessed ?? 0,
    upcomingSessions: stats?.upcomingSessions ?? 0,
    activeFamilies: stats?.activeFamilies ?? 0,
    aiInsights: stats?.aiInsights ?? 0,
    pendingTasks: stats?.pendingTasks ?? 0,
  }
}