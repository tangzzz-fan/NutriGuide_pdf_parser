import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X, FileText, AlertCircle } from 'lucide-react'
import { UploadFile } from '../types/index.ts'
import { formatFileSize, cn } from '../lib/utils'

interface FileUploadProps {
  files: UploadFile[]
  onFilesChange: (files: UploadFile[]) => void
  maxFiles?: number
  maxSize?: number
  disabled?: boolean
}

export function FileUpload({
  files,
  onFilesChange,
  maxFiles = 10,
  maxSize = 50 * 1024 * 1024, // 50MB
  disabled = false
}: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false)

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // 处理被拒绝的文件
    rejectedFiles.forEach(({ file, errors }) => {
      console.warn(`File ${file.name} rejected:`, errors)
    })

    // 处理接受的文件
    const newFiles: UploadFile[] = acceptedFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      name: file.name,
      size: file.size,
      status: 'pending',
      progress: 0
    }))

    // 检查文件数量限制
    const totalFiles = files.length + newFiles.length
    if (totalFiles > maxFiles) {
      alert(`最多只能上传 ${maxFiles} 个文件`)
      return
    }

    // 检查重复文件
    const existingNames = files.map(f => f.name)
    const uniqueFiles = newFiles.filter(file => !existingNames.includes(file.name))

    if (uniqueFiles.length !== newFiles.length) {
      alert('部分文件已存在，已自动过滤')
    }

    onFilesChange([...files, ...uniqueFiles])
  }, [files, onFilesChange, maxFiles])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxSize,
    maxFiles,
    disabled,
    onDragEnter: () => setDragActive(true),
    onDragLeave: () => setDragActive(false),
    onDropAccepted: () => setDragActive(false),
    onDropRejected: () => setDragActive(false)
  })

  const removeFile = (fileId: string) => {
    onFilesChange(files.filter(f => f.id !== fileId))
  }

  const getStatusColor = (status: UploadFile['status']) => {
    switch (status) {
      case 'uploaded': return 'text-green-600'
      case 'uploading': return 'text-yellow-600'
      case 'error': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getStatusIcon = (status: UploadFile['status']) => {
    switch (status) {
      case 'error': return <AlertCircle className="w-4 h-4" />
      default: return <FileText className="w-4 h-4" />
    }
  }

  return (
    <div className="space-y-4">
      {/* 拖拽上传区域 */}
      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200",
          isDragActive || dragActive
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 hover:border-blue-400 hover:bg-gray-50",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <div className="space-y-2">
          <p className="text-lg font-medium text-gray-900">
            {isDragActive ? '释放文件到此处' : '拖拽PDF文件到此处'}
          </p>
          <p className="text-sm text-gray-500">
            或者 <span className="text-blue-600 font-medium">点击选择文件</span>
          </p>
          <p className="text-xs text-gray-400">
            支持PDF格式，单个文件最大{formatFileSize(maxSize)}，最多{maxFiles}个文件
          </p>
        </div>
      </div>

      {/* 文件列表 */}
      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-900">
            已选择文件 ({files.length})
          </h4>
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className={getStatusColor(file.status)}>
                    {getStatusIcon(file.status)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <div className="flex items-center space-x-2 text-xs text-gray-500">
                      <span>{formatFileSize(file.size)}</span>
                      {file.status === 'uploading' && (
                        <span>• {file.progress}%</span>
                      )}
                      {file.error && (
                        <span className="text-red-600">• {file.error}</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* 进度条 */}
                {file.status === 'uploading' && (
                  <div className="w-20 mx-3">
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* 删除按钮 */}
                <button
                  onClick={() => removeFile(file.id)}
                  disabled={file.status === 'uploading'}
                  className="p-1 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="移除文件"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
