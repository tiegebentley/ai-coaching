import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// Create a dummy client for build time when env vars are not available
const createSupabaseClient = () => {
  if (!supabaseUrl || !supabaseAnonKey) {
    // Return a dummy client for build time
    if (typeof window === 'undefined') {
      // Server-side/build time - return a mock client
      return {
        from: () => ({
          select: () => Promise.resolve({ data: [], error: null }),
          insert: () => Promise.resolve({ data: null, error: null }),
          update: () => Promise.resolve({ data: null, error: null }),
          delete: () => Promise.resolve({ data: null, error: null }),
        }),
        auth: {
          getSession: () => Promise.resolve({ data: null, error: null }),
          signIn: () => Promise.resolve({ data: null, error: null }),
          signOut: () => Promise.resolve({ error: null }),
        },
      } as any
    }
    // Client-side - throw error
    throw new Error('Missing Supabase environment variables')
  }
  
  return createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      autoRefreshToken: true,
      persistSession: true,
      detectSessionInUrl: false
    },
    realtime: {
      params: {
        eventsPerSecond: 10,
      },
    },
  })
}

export const supabase = createSupabaseClient()

export type Database = {
  public: {
    Tables: {
      emails: {
        Row: {
          id: string
          created_at: string
          updated_at: string
          sender_email: string
          sender_name: string | null
          subject: string
          content: string
          ai_response: string | null
          confidence_score: number | null
          priority: 'low' | 'medium' | 'high' | 'urgent'
          category: 'general' | 'schedule' | 'payment' | 'emergency'
          is_processed: boolean
          is_approved: boolean
          is_sent: boolean
          gmail_message_id: string | null
          gmail_thread_id: string | null
          family_id: string | null
        }
        Insert: {
          id?: string
          created_at?: string
          updated_at?: string
          sender_email: string
          sender_name?: string | null
          subject: string
          content: string
          ai_response?: string | null
          confidence_score?: number | null
          priority?: 'low' | 'medium' | 'high' | 'urgent'
          category?: 'general' | 'schedule' | 'payment' | 'emergency'
          is_processed?: boolean
          is_approved?: boolean
          is_sent?: boolean
          gmail_message_id?: string | null
          gmail_thread_id?: string | null
          family_id?: string | null
        }
        Update: {
          id?: string
          created_at?: string
          updated_at?: string
          sender_email?: string
          sender_name?: string | null
          subject?: string
          content?: string
          ai_response?: string | null
          confidence_score?: number | null
          priority?: 'low' | 'medium' | 'high' | 'urgent'
          category?: 'general' | 'schedule' | 'payment' | 'emergency'
          is_processed?: boolean
          is_approved?: boolean
          is_sent?: boolean
          gmail_message_id?: string | null
          gmail_thread_id?: string | null
          family_id?: string | null
        }
      }
      sessions: {
        Row: {
          id: string
          created_at: string
          updated_at: string
          title: string
          description: string | null
          start_time: string
          end_time: string
          venue: string
          coach_id: string | null
          max_participants: number | null
          current_participants: number
          status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled'
          session_type: 'practice' | 'match' | 'training'
          notes: string | null
        }
        Insert: {
          id?: string
          created_at?: string
          updated_at?: string
          title: string
          description?: string | null
          start_time: string
          end_time: string
          venue: string
          coach_id?: string | null
          max_participants?: number | null
          current_participants?: number
          status?: 'scheduled' | 'in_progress' | 'completed' | 'cancelled'
          session_type?: 'practice' | 'match' | 'training'
          notes?: string | null
        }
        Update: {
          id?: string
          created_at?: string
          updated_at?: string
          title?: string
          description?: string | null
          start_time?: string
          end_time?: string
          venue?: string
          coach_id?: string | null
          max_participants?: number | null
          current_participants?: number
          status?: 'scheduled' | 'in_progress' | 'completed' | 'cancelled'
          session_type?: 'practice' | 'match' | 'training'
          notes?: string | null
        }
      }
      families: {
        Row: {
          id: string
          created_at: string
          updated_at: string
          family_name: string
          parent_name: string
          parent_email: string
          phone_number: string | null
          child_name: string
          child_age: number | null
          emergency_contact: string | null
          payment_status: 'pending' | 'paid' | 'overdue'
          is_active: boolean
          notes: string | null
          airtable_id: string | null
        }
        Insert: {
          id?: string
          created_at?: string
          updated_at?: string
          family_name: string
          parent_name: string
          parent_email: string
          phone_number?: string | null
          child_name: string
          child_age?: number | null
          emergency_contact?: string | null
          payment_status?: 'pending' | 'paid' | 'overdue'
          is_active?: boolean
          notes?: string | null
          airtable_id?: string | null
        }
        Update: {
          id?: string
          created_at?: string
          updated_at?: string
          family_name?: string
          parent_name?: string
          parent_email?: string
          phone_number?: string | null
          child_name?: string
          child_age?: number | null
          emergency_contact?: string | null
          payment_status?: 'pending' | 'paid' | 'overdue'
          is_active?: boolean
          notes?: string | null
          airtable_id?: string | null
        }
      }
      knowledge_base: {
        Row: {
          id: string
          created_at: string
          updated_at: string
          title: string
          content: string
          source_url: string | null
          category: 'general' | 'coaching' | 'admin' | 'safety' | 'rules'
          tags: string[] | null
          relevance_score: number | null
          embedding_vector: number[] | null
        }
        Insert: {
          id?: string
          created_at?: string
          updated_at?: string
          title: string
          content: string
          source_url?: string | null
          category?: 'general' | 'coaching' | 'admin' | 'safety' | 'rules'
          tags?: string[] | null
          relevance_score?: number | null
          embedding_vector?: number[] | null
        }
        Update: {
          id?: string
          created_at?: string
          updated_at?: string
          title?: string
          content?: string
          source_url?: string | null
          category?: 'general' | 'coaching' | 'admin' | 'safety' | 'rules'
          tags?: string[] | null
          relevance_score?: number | null
          embedding_vector?: number[] | null
        }
      }
      system_config: {
        Row: {
          id: string
          created_at: string
          updated_at: string
          key: string
          value: string
          description: string | null
          is_sensitive: boolean
        }
        Insert: {
          id?: string
          created_at?: string
          updated_at?: string
          key: string
          value: string
          description?: string | null
          is_sensitive?: boolean
        }
        Update: {
          id?: string
          created_at?: string
          updated_at?: string
          key?: string
          value?: string
          description?: string | null
          is_sensitive?: boolean
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      similarity_search: {
        Args: {
          query_embedding: number[]
          match_threshold: number
          match_count: number
        }
        Returns: {
          id: string
          title: string
          content: string
          category: string
          similarity: number
        }[]
      }
    }
    Enums: {
      [_ in never]: never
    }
  }
}