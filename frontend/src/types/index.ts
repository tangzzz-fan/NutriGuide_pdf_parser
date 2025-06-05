export interface UploadFile {
  id: string
  file: File
  name: string
  size: number
  status: 'pending' | 'uploading' | 'uploaded' | 'error'
  progress: number
  error?: string
}

export interface ParseResult {
  document_id: string
  task_id?: string
  file_id: string
  filename: string
  parsing_type: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  created_at: string
  updated_at?: string
  result?: any
  error_message?: string
}

export interface BatchResult {
  batch_id: string
  task_id?: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  total_files: number
  completed_files: number
  processing_files: number
  failed_files: number
  parsing_type: string
  description?: string
  created_at: string
  updated_at?: string
  files?: ParseResult[]
}

export interface Stats {
  processing: number
  queued: number
  completed_today: number
  success_rate: number
}

export interface RecentTask {
  filename: string
  status: string
  updated_at: string
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  results: T[]
  total: number
  page: number
  limit: number
}

export interface UploadProgress {
  loaded: number
  total: number
  percentage: number
}
