import { useEffect } from 'react'
import { useAuthStore } from '@/stores/auth'

export const useAuth = () => {
  const {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    loadUser,
  } = useAuthStore()

  // Load user on mount if we have a token
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('auth_token')
      if (token && !user && !isLoading) {
        loadUser()
      }
    }
  }, [user, isLoading, loadUser])

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    loadUser,
  }
}

// Hook to check if user has specific role
export const usePermissions = () => {
  const { user } = useAuth()

  const hasRole = (role: string) => {
    return user?.role === role
  }

  const isAdmin = () => hasRole('admin')
  const isCoach = () => hasRole('coach') || isAdmin()
  const isAssistant = () => hasRole('assistant') || isCoach()

  return {
    hasRole,
    isAdmin,
    isCoach,
    isAssistant,
  }
}