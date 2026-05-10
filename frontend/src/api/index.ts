import axios from 'axios'
import router from '@/router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_username')
      router.push('/login')
    }
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

// ==================== Feeds ====================
export interface Feed {
  id: number
  name: string
  url: string
  journal_name: string
  paper_count: number
  last_fetched: string | null
  enabled: boolean
  created_at: string
}

export interface FeedCreate {
  name: string
  url: string
  journal_name?: string
}

export interface FeedUpdate {
  name?: string
  url?: string
  journal_name?: string
  enabled?: boolean
}

export const feedApi = {
  list: () => api.get<Feed[]>('/feeds'),
  create: (data: FeedCreate) => api.post<Feed>('/feeds', data),
  update: (id: number, data: FeedUpdate) => api.put<Feed>(`/feeds/${id}`, data),
  delete: (id: number) => api.delete(`/feeds/${id}`),
  fetch: (id: number) => api.post(`/feeds/${id}/fetch`),
  fetchAll: () => api.post('/feeds/fetch-all'),
}

// ==================== Papers ====================
export interface Paper {
  id: number
  title: string
  authors: string | null
  journal_name: string | null
  abstract: string | null
  doi: string | null
  url: string | null
  published_at: string | null
  relevance_score: number | null
  analysis_summary: string | null
  fetched_at: string | null
  feed_id: number | null
  category: string | null
}

export interface PaperListParams {
  page?: number
  page_size?: number
  search?: string
  journal?: string
  keyword?: string
  min_relevance?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export const paperApi = {
  list: (params?: PaperListParams) => api.get<PaginatedResponse<Paper>>('/papers', { params }),
  get: (id: number) => api.get<Paper>(`/papers/${id}`),
  markRead: (id: number) => api.put(`/papers/${id}/read`),
}

// ==================== Keywords ====================
export interface Keyword {
  id: number
  word: string
  category: string
  enabled: boolean
  created_at: string
}

export interface KeywordCreate {
  word: string
  category: string
}

export interface KeywordUpdate {
  word?: string
  category?: string
  enabled?: boolean
}

export const keywordApi = {
  list: () => api.get<Keyword[]>('/keywords'),
  create: (data: KeywordCreate) => api.post<Keyword>('/keywords', data),
  update: (id: number, data: KeywordUpdate) => api.put<Keyword>(`/keywords/${id}`, data),
  delete: (id: number) => api.delete(`/keywords/${id}`),
}

// ==================== Settings ====================
export interface AISettings {
  api_base: string
  api_key: string
  model: string
  enabled: boolean
}

export interface EmailSettings {
  smtp_server: string
  smtp_port: number
  smtp_user: string
  smtp_password: string
  sender_name: string
  recipient: string
  enabled: boolean
}

export interface WebDAVSettings {
  url: string
  username: string
  password: string
  remote_path: string
}

export interface ScheduleSettings {
  cron_hour: number
  cron_minute: number
  relevance_threshold: number
}

export const settingsApi = {
  getAI: () => api.get<AISettings>('/settings/ai'),
  saveAI: (data: AISettings) => api.put('/settings/ai', data),
  testAI: () => api.post('/settings/ai/test'),
  getEmail: () => api.get<EmailSettings>('/settings/email'),
  saveEmail: (data: EmailSettings) => api.put('/settings/email', data),
  testEmail: () => api.post('/settings/email/test'),
  getWebDAV: () => api.get<WebDAVSettings>('/settings/webdav'),
  saveWebDAV: (data: WebDAVSettings) => api.put('/settings/webdav', data),
  testWebDAV: () => api.post('/settings/webdav/test'),
  getSchedule: () => api.get<ScheduleSettings>('/settings/schedule'),
  saveSchedule: (data: ScheduleSettings) => api.put('/settings/schedule', data),
}

// ==================== Analysis ====================
export interface Analysis {
  id: number
  paper_id: number
  paper_title: string
  relevance_score: number
  summary: string
  created_at: string
}

export const analysisApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<PaginatedResponse<Analysis>>('/analysis', { params }),
  run: () => api.post('/analysis/run'),
  fetchAndAnalyze: () => api.post('/analysis/fetch-and-analyze'),
  sendReport: () => api.post('/analysis/send-report'),
}

// ==================== Dashboard ====================
export interface DashboardStats {
  total_feeds: number
  total_papers: number
  today_papers: number
  today_analyses: number
  high_relevance_today: number
}

export interface RecentPaper {
  id: number
  title: string
  journal: string
  relevance_score: number
  published_date: string
}

export const dashboardApi = {
  getStats: () => api.get<DashboardStats>('/dashboard/stats'),
  getRecentHighRelevance: (limit?: number) =>
    api.get<RecentPaper[]>('/dashboard/recent-high-relevance', { params: { limit } }),
}

// ==================== Auth ====================
export interface LoginResponse {
  token: string
  username: string
}

export const authApi = {
  check: () => api.get<{ registered: boolean }>('/auth/check'),
  login: (username: string, password: string) =>
    api.post<LoginResponse>('/auth/login', { username, password }),
  register: (username: string, password: string) =>
    api.post<LoginResponse>('/auth/register', { username, password }),
}

export default api
