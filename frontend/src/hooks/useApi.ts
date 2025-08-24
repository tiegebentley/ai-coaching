import { useState, useEffect, useCallback } from 'react'
import type { ApiResponse } from '@/types'

interface UseApiOptions<T> {
  immediate?: boolean
  onSuccess?: (data: T) => void
  onError?: (error: string) => void
}

interface UseApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export function useApi<T = any>(
  apiFunction: () => Promise<ApiResponse<T>>,
  options: UseApiOptions<T> = {}
) {
  const { immediate = true, onSuccess, onError } = options

  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  })

  const execute = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }))

    try {
      const response = await apiFunction()

      if (response.success && response.data) {
        setState({
          data: response.data,
          loading: false,
          error: null,
        })
        onSuccess?.(response.data)
      } else {
        const errorMessage = response.error || 'Unknown error occurred'
        setState({
          data: null,
          loading: false,
          error: errorMessage,
        })
        onError?.(errorMessage)
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Network error'
      setState({
        data: null,
        loading: false,
        error: errorMessage,
      })
      onError?.(errorMessage)
    }
  }, [apiFunction, onSuccess, onError])

  useEffect(() => {
    if (immediate) {
      execute()
    }
  }, [immediate, execute])

  return {
    ...state,
    execute,
    refetch: execute,
  }
}

// Hook for handling API mutations (POST, PUT, DELETE)
export function useApiMutation<TParams = any, TResult = any>(
  apiFunction: (params: TParams) => Promise<ApiResponse<TResult>>,
  options: UseApiOptions<TResult> = {}
) {
  const { onSuccess, onError } = options

  const [state, setState] = useState<UseApiState<TResult>>({
    data: null,
    loading: false,
    error: null,
  })

  const mutate = useCallback(async (params: TParams) => {
    setState(prev => ({ ...prev, loading: true, error: null }))

    try {
      const response = await apiFunction(params)

      if (response.success) {
        setState({
          data: response.data || null,
          loading: false,
          error: null,
        })
        onSuccess?.(response.data as TResult)
        return { success: true, data: response.data }
      } else {
        const errorMessage = response.error || 'Unknown error occurred'
        setState({
          data: null,
          loading: false,
          error: errorMessage,
        })
        onError?.(errorMessage)
        return { success: false, error: errorMessage }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Network error'
      setState({
        data: null,
        loading: false,
        error: errorMessage,
      })
      onError?.(errorMessage)
      return { success: false, error: errorMessage }
    }
  }, [apiFunction, onSuccess, onError])

  return {
    ...state,
    mutate,
  }
}

// Hook for paginated API requests
export function usePaginatedApi<T = any>(
  apiFunction: (params: { limit: number; offset: number }) => Promise<ApiResponse<T>>,
  initialLimit: number = 20
) {
  const [page, setPage] = useState(0)
  const [limit] = useState(initialLimit)

  const { data, loading, error, execute } = useApi(
    () => apiFunction({ limit, offset: page * limit }),
    { immediate: true }
  )

  const nextPage = useCallback(() => {
    setPage(prev => prev + 1)
  }, [])

  const prevPage = useCallback(() => {
    setPage(prev => Math.max(0, prev - 1))
  }, [])

  const goToPage = useCallback((newPage: number) => {
    setPage(Math.max(0, newPage))
  }, [])

  useEffect(() => {
    execute()
  }, [page, execute])

  return {
    data,
    loading,
    error,
    page,
    limit,
    nextPage,
    prevPage,
    goToPage,
    refetch: execute,
  }
}