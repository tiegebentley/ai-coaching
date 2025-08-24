import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api'
import type { Family, ScheduleSession, ApiResponse } from '@/types'

interface UseFamilyContextReturn {
  family: Family | null
  sessions: ScheduleSession[]
  loading: boolean
  error: string | null
}

export const useFamilyContext = (emailId: string): UseFamilyContextReturn => {
  const [family, setFamily] = useState<Family | null>(null)
  const [sessions, setSessions] = useState<ScheduleSession[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchFamilyContext = async () => {
      try {
        setLoading(true)
        setError(null)

        // Get the email details first to extract sender information
        const emailResponse = await apiClient.getEmail(emailId) as ApiResponse<any>
        
        if (!emailResponse.success || !emailResponse.data) {
          throw new Error('Failed to fetch email details')
        }

        const email = emailResponse.data
        const senderEmail = email.senderEmail

        // Find family by primary or secondary contact email
        const familyResponse = await apiClient.getFamilyByEmail(senderEmail) as ApiResponse<Family>
        
        if (familyResponse.success && familyResponse.data) {
          const familyData = familyResponse.data
          setFamily(familyData)

          // Fetch recent and upcoming sessions for this family
          const sessionsResponse = await apiClient.getSessionsByFamily(familyData.id, {
            limit: 10,
            includePast: true
          }) as ApiResponse<ScheduleSession[]>

          if (sessionsResponse.success && sessionsResponse.data) {
            setSessions(sessionsResponse.data)
          }
        } else {
          // No family found - this might be a new inquiry
          setFamily(null)
          setSessions([])
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred'
        setError(errorMessage)
        console.error('Error fetching family context:', err)
      } finally {
        setLoading(false)
      }
    }

    if (emailId) {
      fetchFamilyContext()
    }
  }, [emailId])

  return {
    family,
    sessions,
    loading,
    error,
  }
}