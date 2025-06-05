import { ApiResponse, BatchResult, ParseResult, PaginatedResponse, Stats, RecentTask } from '../types/index.ts'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:7800'

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Network error' }))
      throw new Error(error.error || error.detail || 'Request failed')
    }

    return response.json()
  }

  // 健康检查
  async healthCheck() {
    return this.request('/health')
  }

  // 同步解析PDF
  async parsePdfSync(file: File, parseType: string = 'auto') {
    const formData = new FormData()
    formData.append('file', file)

    // 构建查询参数
    const params = new URLSearchParams()
    params.append('parsing_type', parseType)

    const response = await fetch(`${API_BASE_URL}/parse/sync?${params}`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Upload failed' }))
      throw new Error(error.error || error.detail || 'Upload failed')
    }

    return response.json()
  }

  // 异步解析PDF
  async parsePdfAsync(file: File, parseType: string = 'auto', callbackUrl?: string) {
    try {
      const formData = new FormData()
      formData.append('file', file)

      // 构建查询参数
      const params = new URLSearchParams()
      params.append('parsing_type', parseType)
      if (callbackUrl) {
        params.append('callback_url', callbackUrl)
      }

      const response = await fetch(`${API_BASE_URL}/parse/async?${params}`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Upload failed' }))

        // 处理特定的错误类型
        if (response.status === 500 && error.error?.includes('authentication')) {
          throw new Error('服务器数据库配置问题，请联系管理员')
        } else if (response.status === 400) {
          throw new Error(error.error || '文件格式不正确，请确保上传PDF文件')
        } else if (response.status === 413) {
          throw new Error('文件太大，请选择小于50MB的文件')
        } else {
          throw new Error(error.error || error.detail || '上传失败，请稍后重试')
        }
      }

      return response.json()
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
      throw new Error('网络连接失败，请检查网络连接')
    }
  }

  // 批量解析PDF
  async parsePdfBatch(files: File[], parseType: string = 'auto') {
    const formData = new FormData()
    files.forEach(file => {
      formData.append('files', file)
    })

    // 构建查询参数
    const params = new URLSearchParams()
    params.append('parsing_type', parseType)

    const response = await fetch(`${API_BASE_URL}/parse/batch?${params}`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Batch upload failed' }))
      throw new Error(error.error || error.detail || 'Batch upload failed')
    }

    return response.json()
  }

  // 获取解析状态
  async getParsingStatus(documentId: string): Promise<ParseResult> {
    return this.request(`/parse/status/${documentId}`)
  }

  // 获取解析历史
  async getParsingHistory(
    page: number = 1,
    limit: number = 10,
    status?: string,
    parseType?: string
  ): Promise<PaginatedResponse<ParseResult>> {
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        offset: ((page - 1) * limit).toString(),
      })

      if (status && status !== 'all') {
        params.append('status', status)
      }
      if (parseType && parseType !== 'all') {
        params.append('parsing_type', parseType)
      }

      return await this.request(`/parse/history?${params}`)
    } catch (error) {
      console.warn('Failed to get parsing history, returning empty result:', error)
      // 返回空结果而不是抛出错误
      return {
        results: [],
        total: 0,
        page: page,
        limit: limit
      }
    }
  }

  // 删除解析结果
  async deleteParsingResult(documentId: string) {
    return this.request(`/parse/${documentId}`, {
      method: 'DELETE',
    })
  }

  // 获取实时统计
  async getRealtimeStats(): Promise<Stats> {
    try {
      return await this.request('/admin/stats/real-time')
    } catch (error) {
      console.warn('Failed to get real-time stats, returning default values:', error)
      // 返回默认统计数据
      return {
        processing: 0,
        queued: 0,
        completed_today: 0,
        success_rate: 0
      }
    }
  }

  // 获取最近任务
  async getRecentTasks(limit: number = 5): Promise<RecentTask[]> {
    try {
      return await this.request(`/admin/stats/recent-tasks?limit=${limit}`)
    } catch (error) {
      console.warn('Failed to get recent tasks, returning empty array:', error)
      // 返回空数组
      return []
    }
  }

  // 获取批次详情
  async getBatchDetail(batchId: string): Promise<BatchResult> {
    return this.request(`/admin/batches/${batchId}`)
  }

  // 删除批次
  async deleteBatch(batchId: string) {
    return this.request(`/admin/batches/${batchId}`, {
      method: 'DELETE',
    })
  }

  // 导出批次数据
  async exportBatch(batchId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/admin/export/batch/${batchId}`)
    if (!response.ok) {
      throw new Error('Export failed')
    }
    return response.blob()
  }

  // 导出所有数据
  async exportAll(): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/admin/export/all`)
    if (!response.ok) {
      throw new Error('Export failed')
    }
    return response.blob()
  }

  // 清理已完成任务
  async clearCompleted() {
    return this.request('/admin/cleanup/completed', {
      method: 'POST',
    })
  }

  // 下载文件结果
  async downloadFileResult(fileId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/admin/download/${fileId}`)
    if (!response.ok) {
      throw new Error('Download failed')
    }
    return response.blob()
  }
}

export const apiService = new ApiService()
export default apiService
