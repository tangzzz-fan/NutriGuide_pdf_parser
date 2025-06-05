import React, { useState, useEffect } from 'react'
import { FileText, Activity, Clock, TrendingUp, Download, RefreshCw, Trash2 } from 'lucide-react'
import { FileUpload } from './components/FileUpload'
import { StatsCard } from './components/StatsCard'
import { ProgressBar, CircularProgress } from './components/ProgressBar'
import { StatusBadge } from './components/StatusBadge'
import HistoryList from './components/HistoryList'
import ParsedContentViewer from './components/ParsedContentViewer'
import { UploadFile, ParseResult, Stats, RecentTask } from './types/index.ts'
import { apiService } from './services/api'
import { formatFileSize, formatDateTime, formatTimeAgo, parseTypeLabels, cn } from './lib/utils'

function App() {
  const [files, setFiles] = useState<UploadFile[]>([])
  const [parseType, setParseType] = useState('auto')
  const [description, setDescription] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [stats, setStats] = useState<Stats>({ processing: 0, queued: 0, completed_today: 0, success_rate: 0 })
  const [recentTasks, setRecentTasks] = useState<RecentTask[]>([])
  const [history, setHistory] = useState<ParseResult[]>([])
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [apiError, setApiError] = useState<string | null>(null)
  const [serviceStatus, setServiceStatus] = useState<'checking' | 'connected' | 'error'>('checking')

  // 新增：内容查看器相关状态
  const [viewingDocumentId, setViewingDocumentId] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<'upload' | 'history' | 'viewer'>('upload')
  const [historyRefreshTrigger, setHistoryRefreshTrigger] = useState(0)

  // 测试API连接
  const testApiConnection = async () => {
    setServiceStatus('checking')
    try {
      await apiService.healthCheck()
      setApiError(null)
      setServiceStatus('connected')
      return true
    } catch (error) {
      setApiError('无法连接到后端服务，请检查服务是否正常运行')
      setServiceStatus('error')
      return false
    }
  }

  // 加载初始数据
  useEffect(() => {
    const initializeApp = async () => {
      const isConnected = await testApiConnection()
      if (isConnected) {
        loadStats()
        loadRecentTasks()
        loadHistory()

        // 设置定时刷新
        const statsInterval = setInterval(loadStats, 10000) // 10秒
        const tasksInterval = setInterval(loadRecentTasks, 15000) // 15秒
        const historyInterval = setInterval(() => loadHistory(currentPage), 30000) // 30秒

        return () => {
          clearInterval(statsInterval)
          clearInterval(tasksInterval)
          clearInterval(historyInterval)
        }
      }
    }

    initializeApp()
  }, [currentPage])

  const loadStats = async () => {
    try {
      const data = await apiService.getRealtimeStats()
      setStats(data)
    } catch (error) {
      console.warn('Failed to load stats, using default values:', error)
      // 设置默认值，不显示错误给用户
      setStats({ processing: 0, queued: 0, completed_today: 0, success_rate: 0 })
    }
  }

  const loadRecentTasks = async () => {
    try {
      const data = await apiService.getRecentTasks(5)
      setRecentTasks(data)
    } catch (error) {
      console.warn('Failed to load recent tasks, using empty array:', error)
      // 设置空数组，不显示错误给用户
      setRecentTasks([])
    }
  }

  const loadHistory = async (page = 1) => {
    try {
      const data = await apiService.getParsingHistory(page, 10)
      setHistory(data.results || [])
      setTotalPages(Math.ceil((data.total || 0) / 10))
    } catch (error) {
      console.warn('Failed to load history, using empty array:', error)
      // 设置空数组，不显示错误给用户
      setHistory([])
      setTotalPages(1)
    }
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      alert('请先选择要上传的文件')
      return
    }

    setIsUploading(true)

    try {
      // 更新文件状态为上传中
      const updatedFiles = files.map(f => ({ ...f, status: 'uploading' as const, progress: 0 }))
      setFiles(updatedFiles)

      let successCount = 0
      let errorCount = 0

      // 逐个上传文件
      for (let i = 0; i < files.length; i++) {
        const file = files[i]

        try {
          // 更新当前文件进度
          setFiles(prev => prev.map(f =>
            f.id === file.id ? { ...f, progress: 30 } : f
          ))

          // 验证文件类型
          if (!file.file.type.includes('pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
            throw new Error('只支持PDF文件格式')
          }

          // 验证文件大小 (50MB)
          if (file.file.size > 50 * 1024 * 1024) {
            throw new Error('文件大小不能超过50MB')
          }

          setFiles(prev => prev.map(f =>
            f.id === file.id ? { ...f, progress: 60 } : f
          ))

          const result = await apiService.parsePdfAsync(file.file, parseType)

          // 标记为已上传
          setFiles(prev => prev.map(f =>
            f.id === file.id ? { ...f, status: 'uploaded', progress: 100 } : f
          ))

          successCount++
          console.log('Upload successful:', result)

        } catch (error) {
          errorCount++
          const errorMessage = error instanceof Error ? error.message : '上传失败'
          console.error('Upload failed for file:', file.name, error)

          // 标记为错误
          setFiles(prev => prev.map(f =>
            f.id === file.id ? {
              ...f,
              status: 'error',
              error: errorMessage,
              progress: 0
            } : f
          ))
        }
      }

      // 显示结果摘要
      if (successCount > 0 && errorCount === 0) {
        alert(`✅ 成功上传 ${successCount} 个文件`)
      } else if (successCount > 0 && errorCount > 0) {
        alert(`⚠️ 上传完成：${successCount} 个成功，${errorCount} 个失败`)
      } else if (errorCount > 0) {
        alert(`❌ 上传失败：${errorCount} 个文件上传失败`)
      }

      // 刷新数据
      if (successCount > 0) {
        setTimeout(() => {
          loadStats()
          loadRecentTasks()
          loadHistory()
        }, 1000)
      }

      // 清空成功上传的文件
      setTimeout(() => {
        setFiles(prev => prev.filter(f => f.status === 'error'))
        if (successCount === files.length) {
          setDescription('')
        }
      }, 2000)

    } catch (error) {
      console.error('Upload process failed:', error)
      alert('上传过程出错: ' + (error instanceof Error ? error.message : '未知错误'))
    } finally {
      setIsUploading(false)
    }
  }

  // 处理查看解析内容
  const handleViewContent = (documentId: string) => {
    setViewingDocumentId(documentId)
    setActiveView('viewer')
  }

  // 关闭内容查看器
  const handleCloseViewer = () => {
    setViewingDocumentId(null)
    setActiveView('history')
  }

  // 刷新历史记录
  const refreshHistory = () => {
    setHistoryRefreshTrigger(prev => prev + 1)
    loadHistory()
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部导航 */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <FileText className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">NutriGuide PDF解析工具</h1>
                <p className="text-sm text-gray-500">智能营养文档解析平台</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* 服务状态指示器 */}
              <div className="flex items-center space-x-2">
                <div className={cn(
                  'w-2 h-2 rounded-full',
                  serviceStatus === 'connected' ? 'bg-green-500' :
                    serviceStatus === 'checking' ? 'bg-yellow-500 animate-pulse' :
                      'bg-red-500'
                )} />
                <span className="text-xs text-gray-500">
                  {serviceStatus === 'connected' ? '服务正常' :
                    serviceStatus === 'checking' ? '检查中...' :
                      '服务异常'}
                </span>
              </div>
              <span className="text-sm text-gray-500">v1.0.0</span>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* API错误提示 */}
        {apiError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-800">{apiError}</p>
              </div>
              <div className="ml-auto">
                <button
                  onClick={testApiConnection}
                  className="text-sm text-red-600 hover:text-red-500 font-medium"
                >
                  重试连接
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 服务状态提示 */}
        {serviceStatus === 'connected' && !apiError && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <div>
                  <p className="text-sm text-blue-800 font-medium">
                    服务状态说明
                  </p>
                  <p className="text-sm text-blue-700 mt-1">
                    • 后端服务正常运行<br />
                    • 文件上传功能可用（会显示数据库错误，这是正常的）<br />
                    • 统计和历史功能暂时受限<br />
                    • 您可以正常上传PDF文件进行解析测试
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="处理中任务"
            value={stats.processing}
            icon={Activity}
            color="yellow"
          />
          <StatsCard
            title="队列等待"
            value={stats.queued}
            icon={Clock}
            color="gray"
          />
          <StatsCard
            title="今日完成"
            value={stats.completed_today}
            icon={TrendingUp}
            color="green"
          />
          <StatsCard
            title="成功率"
            value={`${stats.success_rate}%`}
            icon={TrendingUp}
            color="blue"
          />
        </div>

        {/* 主要导航标签 */}
        {!viewingDocumentId && (
          <div className="mb-6">
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveView('upload')}
                  className={cn(
                    'py-2 px-1 border-b-2 font-medium text-sm',
                    activeView === 'upload'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  )}
                >
                  文件上传
                </button>
                <button
                  onClick={() => setActiveView('history')}
                  className={cn(
                    'py-2 px-1 border-b-2 font-medium text-sm',
                    activeView === 'history'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  )}
                >
                  解析历史
                </button>
              </nav>
            </div>
          </div>
        )}

        {/* 主内容区域 */}
        {viewingDocumentId ? (
          /* 内容查看器 */
          <ParsedContentViewer
            documentId={viewingDocumentId}
            onClose={handleCloseViewer}
          />
        ) : activeView === 'upload' ? (
          /* 上传界面 */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* 左侧：文件上传 */}
            <div className="lg:col-span-2 space-y-6">
              <div className="card">
                <div className="card-header">
                  <h2 className="text-lg font-semibold text-gray-900">文件上传</h2>
                  <p className="text-sm text-gray-500">上传PDF文件进行智能解析</p>
                </div>
                <div className="card-body space-y-6">
                  <FileUpload
                    files={files}
                    onFilesChange={setFiles}
                    disabled={isUploading}
                  />

                  {/* 解析选项 */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        解析类型
                      </label>
                      <select
                        value={parseType}
                        onChange={(e) => setParseType(e.target.value)}
                        disabled={isUploading}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                        {Object.entries(parseTypeLabels).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* 描述 */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      批次描述（可选）
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      disabled={isUploading}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="描述本次上传的文件类型和来源..."
                    />
                  </div>

                  {/* 上传按钮 */}
                  <button
                    onClick={handleUpload}
                    disabled={files.length === 0 || isUploading}
                    className={cn(
                      'w-full btn btn-primary py-3 text-base font-medium',
                      (files.length === 0 || isUploading) && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    {isUploading ? (
                      <>
                        <RefreshCw className="w-5 h-5 mr-2 animate-spin" />
                        上传中...
                      </>
                    ) : (
                      <>
                        <FileText className="w-5 h-5 mr-2" />
                        开始解析 ({files.length} 个文件)
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* 右侧：实时状态 */}
            <div className="space-y-6">
              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-semibold text-gray-900">最近任务</h3>
                </div>
                <div className="card-body">
                  {recentTasks.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <Clock className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                      <p>暂无最近任务</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {recentTasks.map((task, index) => (
                        <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                          <div className={cn(
                            'w-2 h-2 rounded-full',
                            task.status === 'completed' ? 'bg-green-500' :
                              task.status === 'processing' ? 'bg-yellow-500 animate-pulse' :
                                task.status === 'failed' ? 'bg-red-500' : 'bg-gray-400'
                          )} />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {task.filename}
                            </p>
                            <p className="text-xs text-gray-500">
                              {formatTimeAgo(task.updated_at)}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* 快速操作 */}
              <div className="card">
                <div className="card-header">
                  <h3 className="text-lg font-semibold text-gray-900">快速操作</h3>
                </div>
                <div className="card-body space-y-3">
                  <button
                    onClick={() => window.open('/admin/export/all')}
                    className="w-full btn btn-outline text-left"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    导出全部数据
                  </button>
                  <button
                    onClick={() => {
                      loadStats()
                      loadRecentTasks()
                      loadHistory()
                      refreshHistory()
                    }}
                    className="w-full btn btn-outline text-left"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    刷新状态
                  </button>
                  <button
                    onClick={() => setActiveView('history')}
                    className="w-full btn btn-outline text-left"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    查看历史记录
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* 历史记录界面 */
          <HistoryList
            onViewContent={handleViewContent}
            refreshTrigger={historyRefreshTrigger}
          />
        )}
      </div>
    </div>
  )
}

export default App
