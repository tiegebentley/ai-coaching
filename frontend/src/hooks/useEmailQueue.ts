import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import { apiClient } from '@/lib/api'
import type { EmailMessage, ApiResponse } from '@/types'

interface QueueFilters {
  priority: string
  category: string  
  status: string
}

interface UseEmailQueueReturn {
  emails: EmailMessage[]
  loading: boolean
  error: string | null
  approveEmail: (emailId: string) => Promise<void>
  editDraft: (emailId: string, content: string) => Promise<void>
  deferEmail: (emailId: string) => Promise<void>
  archiveEmail: (emailId: string) => Promise<void>
  refetch: () => Promise<void>
}

export const useEmailQueue = (filters: QueueFilters): UseEmailQueueReturn => {
  const [emails, setEmails] = useState<EmailMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchEmails = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      // Build query parameters from filters
      const queryParams: any = {
        limit: 50,
        isRead: false, // Only unprocessed emails
      }

      if (filters.priority !== 'all') {
        queryParams.priority = filters.priority
      }
      
      if (filters.category !== 'all') {
        queryParams.category = filters.category
      }

      const response = await apiClient.getEmails(queryParams) as ApiResponse<EmailMessage[]>
      
      if (response.success && response.data) {
        setEmails(response.data)
      } else {
        throw new Error(response.error || 'Failed to fetch emails')
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
      setError(errorMessage)
      console.error('Error fetching email queue:', err)
    } finally {
      setLoading(false)
    }
  }, [filters])

  // Real-time subscription for email updates
  useEffect(() => {
    const channel = supabase
      .channel('email_queue_updates')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'emails',
          filter: 'isRead=eq.false'
        },
        (payload) => {
          console.log('Email queue update:', payload)
          // Refetch emails when changes occur
          fetchEmails()
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [fetchEmails])

  // Initial fetch and refetch when filters change
  useEffect(() => {
    fetchEmails()
  }, [fetchEmails])

  const approveEmail = async (emailId: string) => {
    try {
      const response = await apiClient.approveEmailDraft(emailId) as ApiResponse<any>
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to approve email')
      }
      
      // Optimistically update local state
      setEmails(prev => prev.filter(email => email.id !== emailId))
    } catch (error) {
      console.error('Error approving email:', error)
      throw error
    }
  }

  const editDraft = async (emailId: string, content: string) => {
    try {
      const response = await apiClient.updateEmailDraft(emailId, { content }) as ApiResponse<EmailMessage>
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to edit draft')
      }
      
      // Update local state
      if (response.data) {
        setEmails(prev => 
          prev.map(email => 
            email.id === emailId ? response.data! : email
          )
        )
      }
    } catch (error) {
      console.error('Error editing draft:', error)
      throw error
    }
  }

  const deferEmail = async (emailId: string) => {
    try {
      const response = await apiClient.deferEmail(emailId) as ApiResponse<any>
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to defer email')
      }
      
      // Remove from current queue
      setEmails(prev => prev.filter(email => email.id !== emailId))
    } catch (error) {
      console.error('Error deferring email:', error)
      throw error
    }
  }

  const archiveEmail = async (emailId: string) => {
    try {
      const response = await apiClient.archiveEmail(emailId) as ApiResponse<any>
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to archive email')
      }
      
      // Remove from current queue
      setEmails(prev => prev.filter(email => email.id !== emailId))
    } catch (error) {
      console.error('Error archiving email:', error)
      throw error
    }
  }

  return {
    emails,
    loading,
    error,
    approveEmail,
    editDraft,
    deferEmail,
    archiveEmail,
    refetch: fetchEmails,
  }
}