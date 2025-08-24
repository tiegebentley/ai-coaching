import { useEffect, useState, useCallback } from 'react'
import { supabase, type Database } from '@/lib/supabase'
import { PostgrestError, RealtimeChannel } from '@supabase/supabase-js'

type Tables = Database['public']['Tables']
type EmailRow = Tables['emails']['Row']
type SessionRow = Tables['sessions']['Row']
type FamilyRow = Tables['families']['Row']

export const useEmails = (filters?: {
  category?: string
  priority?: string
  is_processed?: boolean
}) => {
  const [emails, setEmails] = useState<EmailRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchEmails = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      let query = supabase
        .from('emails')
        .select('*')
        .order('created_at', { ascending: false })

      if (filters?.category) {
        query = query.eq('category', filters.category)
      }
      if (filters?.priority) {
        query = query.eq('priority', filters.priority)
      }
      if (filters?.is_processed !== undefined) {
        query = query.eq('is_processed', filters.is_processed)
      }

      const { data, error: fetchError } = await query

      if (fetchError) throw fetchError

      setEmails(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch emails')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetchEmails()
  }, [fetchEmails])

  // Real-time subscription
  useEffect(() => {
    const channel = supabase
      .channel('emails-changes')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'emails'
        },
        (payload: any) => {
          if (payload.eventType === 'INSERT') {
            setEmails(prev => [payload.new as EmailRow, ...prev])
          } else if (payload.eventType === 'UPDATE') {
            setEmails(prev => 
              prev.map(email => 
                email.id === payload.new.id 
                  ? payload.new as EmailRow 
                  : email
              )
            )
          } else if (payload.eventType === 'DELETE') {
            setEmails(prev => 
              prev.filter(email => email.id !== payload.old.id)
            )
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  return { emails, loading, error, refetch: fetchEmails }
}

export const useSessions = (filters?: {
  status?: string
  startDate?: string
  endDate?: string
}) => {
  const [sessions, setSessions] = useState<SessionRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      let query = supabase
        .from('sessions')
        .select('*')
        .order('start_time', { ascending: true })

      if (filters?.status) {
        query = query.eq('status', filters.status)
      }
      if (filters?.startDate) {
        query = query.gte('start_time', filters.startDate)
      }
      if (filters?.endDate) {
        query = query.lte('end_time', filters.endDate)
      }

      const { data, error: fetchError } = await query

      if (fetchError) throw fetchError

      setSessions(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch sessions')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  // Real-time subscription
  useEffect(() => {
    const channel = supabase
      .channel('sessions-changes')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'sessions'
        },
        (payload: any) => {
          if (payload.eventType === 'INSERT') {
            setSessions(prev => [...prev, payload.new as SessionRow].sort(
              (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
            ))
          } else if (payload.eventType === 'UPDATE') {
            setSessions(prev => 
              prev.map(session => 
                session.id === payload.new.id 
                  ? payload.new as SessionRow 
                  : session
              )
            )
          } else if (payload.eventType === 'DELETE') {
            setSessions(prev => 
              prev.filter(session => session.id !== payload.old.id)
            )
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  return { sessions, loading, error, refetch: fetchSessions }
}

export const useFamilies = (filters?: {
  is_active?: boolean
  payment_status?: string
}) => {
  const [families, setFamilies] = useState<FamilyRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchFamilies = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      let query = supabase
        .from('families')
        .select('*')
        .order('family_name', { ascending: true })

      if (filters?.is_active !== undefined) {
        query = query.eq('is_active', filters.is_active)
      }
      if (filters?.payment_status) {
        query = query.eq('payment_status', filters.payment_status)
      }

      const { data, error: fetchError } = await query

      if (fetchError) throw fetchError

      setFamilies(data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch families')
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetchFamilies()
  }, [fetchFamilies])

  // Real-time subscription
  useEffect(() => {
    const channel = supabase
      .channel('families-changes')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'families'
        },
        (payload: any) => {
          if (payload.eventType === 'INSERT') {
            setFamilies(prev => [...prev, payload.new as FamilyRow].sort(
              (a, b) => a.family_name.localeCompare(b.family_name)
            ))
          } else if (payload.eventType === 'UPDATE') {
            setFamilies(prev => 
              prev.map(family => 
                family.id === payload.new.id 
                  ? payload.new as FamilyRow 
                  : family
              )
            )
          } else if (payload.eventType === 'DELETE') {
            setFamilies(prev => 
              prev.filter(family => family.id !== payload.old.id)
            )
          }
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  return { families, loading, error, refetch: fetchFamilies }
}

// Generic hook for dashboard stats with real-time updates
export const useDashboardStats = () => {
  const [stats, setStats] = useState({
    totalEmails: 0,
    pendingEmails: 0,
    upcomingSessions: 0,
    activeFamilies: 0,
    processingRate: 0
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      // Parallel queries for dashboard stats
      const [
        { count: totalEmails },
        { count: pendingEmails },
        { count: upcomingSessions },
        { count: activeFamilies }
      ] = await Promise.all([
        supabase.from('emails').select('id', { count: 'exact', head: true }),
        supabase.from('emails').select('id', { count: 'exact', head: true }).eq('is_processed', false),
        supabase.from('sessions').select('id', { count: 'exact', head: true })
          .eq('status', 'scheduled')
          .gte('start_time', new Date().toISOString()),
        supabase.from('families').select('id', { count: 'exact', head: true }).eq('is_active', true)
      ])

      // Calculate processing rate
      const { data: recentEmails } = await supabase
        .from('emails')
        .select('is_processed, created_at')
        .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString())

      const processed = recentEmails?.filter((e: any) => e.is_processed).length || 0
      const total = recentEmails?.length || 0
      const processingRate = total > 0 ? Math.round((processed / total) * 100) : 100

      setStats({
        totalEmails: totalEmails || 0,
        pendingEmails: pendingEmails || 0,
        upcomingSessions: upcomingSessions || 0,
        activeFamilies: activeFamilies || 0,
        processingRate
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard stats')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  // Real-time subscription for stats updates
  useEffect(() => {
    const channels: RealtimeChannel[] = []

    // Listen to email changes
    const emailChannel = supabase
      .channel('stats-emails')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'emails' }, fetchStats)
      .subscribe()
    channels.push(emailChannel)

    // Listen to session changes
    const sessionChannel = supabase
      .channel('stats-sessions')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'sessions' }, fetchStats)
      .subscribe()
    channels.push(sessionChannel)

    // Listen to family changes
    const familyChannel = supabase
      .channel('stats-families')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'families' }, fetchStats)
      .subscribe()
    channels.push(familyChannel)

    return () => {
      channels.forEach(channel => supabase.removeChannel(channel))
    }
  }, [fetchStats])

  return { stats, loading, error, refetch: fetchStats }
}