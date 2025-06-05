import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function formatDateTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function formatTimeAgo(dateString: string): string {
  const now = new Date()
  const date = new Date(dateString)
  const diff = now.getTime() - date.getTime()

  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  return `${days}天前`
}

export function calculateDuration(startTime: string, endTime?: string): string {
  if (!endTime) return '-'

  const start = new Date(startTime)
  const end = new Date(endTime)
  const diff = end.getTime() - start.getTime()

  const minutes = Math.floor(diff / 60000)
  const seconds = Math.floor((diff % 60000) / 1000)

  if (minutes > 0) {
    return `${minutes}分${seconds}秒`
  }
  return `${seconds}秒`
}

export const parseTypeLabels = {
  auto: '自动识别',
  nutrition_label: '营养标签',
  recipe: '食谱',
  diet_guide: '膳食指南'
} as const

export const statusLabels = {
  completed: '已完成',
  processing: '处理中',
  failed: '失败',
  queued: '队列中',
  pending: '等待中'
} as const

export const statusColors = {
  completed: 'green',
  processing: 'yellow',
  failed: 'red',
  queued: 'gray',
  pending: 'gray'
} as const

export type ParseType = keyof typeof parseTypeLabels
export type Status = keyof typeof statusLabels
export type StatusColor = typeof statusColors[Status]
