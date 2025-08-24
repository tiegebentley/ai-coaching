import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, AuthState, LoginResponse, ApiResponse } from '@/types'
import { apiClient } from '@/lib/api'

interface AuthStore extends AuthState {
  login: (email: string, password: string) => Promise<boolean>
  logout: () => Promise<void>
  loadUser: () => Promise<void>
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (email: string, password: string) => {
        set({ isLoading: true })
        
        try {
          const response = await apiClient.login(email, password) as ApiResponse<LoginResponse>
          
          if (response.success && response.data) {
            const { user, token } = response.data
            
            // Store the auth token
            if (typeof window !== 'undefined') {
              localStorage.setItem('auth_token', token)
            }
            
            set({
              user,
              isAuthenticated: true,
              isLoading: false,
            })
            
            return true
          } else {
            set({ isLoading: false })
            return false
          }
        } catch (error) {
          console.error('Login error:', error)
          set({ isLoading: false })
          return false
        }
      },

      logout: async () => {
        set({ isLoading: true })
        
        try {
          await apiClient.logout()
        } catch (error) {
          console.error('Logout error:', error)
        }
        
        // Clear auth token
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token')
        }
        
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        })
      },

      loadUser: async () => {
        const token = typeof window !== 'undefined' 
          ? localStorage.getItem('auth_token') 
          : null
        
        if (!token) {
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          })
          return
        }
        
        set({ isLoading: true })
        
        try {
          const response = await apiClient.getCurrentUser() as ApiResponse<User>
          
          if (response.success && response.data) {
            set({
              user: response.data,
              isAuthenticated: true,
              isLoading: false,
            })
          } else {
            // Token is invalid, clear it
            localStorage.removeItem('auth_token')
            set({
              user: null,
              isAuthenticated: false,
              isLoading: false,
            })
          }
        } catch (error) {
          console.error('Load user error:', error)
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
          })
        }
      },

      setUser: (user) => {
        set({ user, isAuthenticated: !!user })
      },

      setLoading: (loading) => {
        set({ isLoading: loading })
      },
    }),
    {
      name: 'auth-storage',
      // Only persist user and isAuthenticated, not isLoading
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
)