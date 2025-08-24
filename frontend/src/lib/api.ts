import type { ApiResponse } from '@/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

class ApiClient {
  private baseUrl: string

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}/api/v1${endpoint}`
    
    const defaultHeaders: HeadersInit = {
      'Content-Type': 'application/json',
    }

    const config: RequestInit = {
      headers: { ...defaultHeaders, ...options.headers },
      ...options,
    }

    // Add authentication token if available
    const token = this.getAuthToken()
    if (token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${token}`,
      }
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data as ApiResponse<T>
    } catch (error) {
      console.error('API request failed:', error)
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        message: 'Failed to complete request'
      }
    }
  }

  private getAuthToken(): string | null {
    // In a real app, this would get the token from localStorage, cookies, or a secure store
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth_token')
    }
    return null
  }

  // Health check endpoints
  async healthCheck() {
    return this.request('/health')
  }

  async detailedHealthCheck() {
    return this.request('/health/detailed')
  }

  // Authentication endpoints
  async login(email: string, password: string) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async logout() {
    return this.request('/auth/logout', {
      method: 'POST',
    })
  }

  async getCurrentUser() {
    return this.request('/auth/me')
  }

  // Email endpoints
  async getEmails(params?: {
    limit?: number
    offset?: number
    category?: string
    priority?: string
    isRead?: boolean
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams.append(key, String(value))
        }
      })
    }
    
    const queryString = queryParams.toString()
    const endpoint = `/emails${queryString ? `?${queryString}` : ''}`
    
    return this.request(endpoint)
  }

  async getEmail(emailId: string) {
    return this.request(`/emails/${emailId}`)
  }

  async markEmailRead(emailId: string) {
    return this.request(`/emails/${emailId}/read`, {
      method: 'PATCH',
    })
  }

  async approveEmailDraft(emailId: string) {
    return this.request(`/emails/${emailId}/approve`, {
      method: 'POST',
    })
  }

  async updateEmailDraft(emailId: string, updates: { content: string }) {
    return this.request(`/emails/${emailId}/draft`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    })
  }

  async deferEmail(emailId: string) {
    return this.request(`/emails/${emailId}/defer`, {
      method: 'POST',
    })
  }

  async archiveEmail(emailId: string) {
    return this.request(`/emails/${emailId}/archive`, {
      method: 'POST',
    })
  }

  // Schedule endpoints
  async getSessions(params?: {
    limit?: number
    offset?: number
    startDate?: string
    endDate?: string
    status?: string
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams.append(key, String(value))
        }
      })
    }
    
    const queryString = queryParams.toString()
    const endpoint = `/schedule/sessions${queryString ? `?${queryString}` : ''}`
    
    return this.request(endpoint)
  }

  async getSession(sessionId: string) {
    return this.request(`/schedule/sessions/${sessionId}`)
  }

  async createSession(sessionData: any) {
    return this.request('/schedule/sessions', {
      method: 'POST',
      body: JSON.stringify(sessionData),
    })
  }

  async updateSession(sessionId: string, sessionData: any) {
    return this.request(`/schedule/sessions/${sessionId}`, {
      method: 'PUT',
      body: JSON.stringify(sessionData),
    })
  }

  // Family endpoints
  async getFamilies(params?: {
    limit?: number
    offset?: number
    isActive?: boolean
    paymentStatus?: string
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams.append(key, String(value))
        }
      })
    }
    
    const queryString = queryParams.toString()
    const endpoint = `/families${queryString ? `?${queryString}` : ''}`
    
    return this.request(endpoint)
  }

  async getFamily(familyId: string) {
    return this.request(`/families/${familyId}`)
  }

  async getFamilyByEmail(email: string) {
    return this.request(`/families/by-email/${encodeURIComponent(email)}`)
  }

  async getSessionsByFamily(familyId: string, params?: {
    limit?: number
    includePast?: boolean
  }) {
    const queryParams = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams.append(key, String(value))
        }
      })
    }
    
    const queryString = queryParams.toString()
    const endpoint = `/families/${familyId}/sessions${queryString ? `?${queryString}` : ''}`
    
    return this.request(endpoint)
  }

  // Dashboard endpoints
  async getDashboardStats() {
    return this.request('/dashboard/stats')
  }

  async getActivityLog(limit: number = 10) {
    return this.request(`/dashboard/activity?limit=${limit}`)
  }

  // AI Agent endpoints
  async processEmail(emailId: string) {
    return this.request(`/agents/email/process/${emailId}`, {
      method: 'POST',
    })
  }

  async optimizeSchedule(date: string) {
    return this.request('/agents/schedule/optimize', {
      method: 'POST',
      body: JSON.stringify({ date }),
    })
  }

  async queryKnowledgeBase(query: string) {
    return this.request('/agents/knowledge/query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    })
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL)

// Export the class for testing or custom instances
export { ApiClient }