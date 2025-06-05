import React, { useState, useEffect } from 'react';
import {
    FileText,
    Eye,
    Clock,
    AlertCircle,
    Loader,
    Star,
    Trash2,
    Download,
    RefreshCw,
    Filter
} from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { apiService } from '../services/api';

interface HistoryItem {
    document_id: string;
    filename: string;
    parsing_type: string;
    status: string;
    created_at: string;
    quality_score?: number;
    processing_time?: number;
}

interface HistoryListProps {
    onViewContent?: (documentId: string) => void;
    refreshTrigger?: number;
}

const HistoryList: React.FC<HistoryListProps> = ({
    onViewContent,
    refreshTrigger = 0
}) => {
    const [items, setItems] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [currentPage, setCurrentPage] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [total, setTotal] = useState(0);
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [typeFilter, setTypeFilter] = useState<string>('all');
    const [refreshing, setRefreshing] = useState(false);

    const pageSize = 10;

    useEffect(() => {
        fetchHistory(true);
    }, [refreshTrigger, statusFilter, typeFilter]);

    const fetchHistory = async (reset = false) => {
        try {
            if (reset) {
                setLoading(true);
                setCurrentPage(0);
                setError(null);
            }

            const page = reset ? 1 : currentPage + 1;
            const data = await apiService.getParsingHistory(
                page,
                pageSize,
                statusFilter === 'all' ? undefined : statusFilter,
                typeFilter === 'all' ? undefined : typeFilter
            );

            if (reset) {
                setItems(data.results || []);
            } else {
                setItems(prev => [...prev, ...(data.results || [])]);
            }

            setTotal(data.total || 0);
            setHasMore((data.results || []).length === pageSize);

            if (!reset) {
                setCurrentPage(prev => prev + 1);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : '获取历史记录失败');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const loadMore = () => {
        if (!loading && hasMore) {
            fetchHistory(false);
        }
    };

    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchHistory(true);
    };

    const deleteItem = async (documentId: string) => {
        if (!confirm('确定要删除这个解析结果吗？')) {
            return;
        }

        try {
            await apiService.deleteParsingResult(documentId);
            setItems(prev => prev.filter(item => item.document_id !== documentId));
            setTotal(prev => prev - 1);
        } catch (err) {
            console.error('删除失败:', err);
            alert('删除失败');
        }
    };

    const downloadResult = async (documentId: string, filename: string) => {
        try {
            const response = await fetch(`/api/parse/result/${documentId}/download`);
            if (!response.ok) {
                throw new Error('下载失败');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `${filename.replace('.pdf', '')}_解析结果.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            console.error('下载失败:', err);
            alert('下载失败');
        }
    };

    const formatDuration = (seconds: number) => {
        if (seconds < 60) return `${seconds.toFixed(1)}秒`;
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}分${remainingSeconds}秒`;
    };

    if (loading && items.length === 0) {
        return (
            <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-center py-8">
                    <Loader className="w-6 h-6 animate-spin mr-3" />
                    <span>加载历史记录中...</span>
                </div>
            </div>
        );
    }

    if (error && items.length === 0) {
        return (
            <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-center py-8 text-red-600">
                    <AlertCircle className="w-6 h-6 mr-3" />
                    <span>{error}</span>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b border-gray-200">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">解析历史</h2>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={handleRefresh}
                            disabled={refreshing}
                            className="flex items-center gap-1 px-3 py-1.5 text-xs bg-gray-50 text-gray-600 rounded-md hover:bg-gray-100 disabled:opacity-50"
                        >
                            <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
                            刷新
                        </button>
                        <span className="text-sm text-gray-500">总计 {total} 个文件</span>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <Filter className="w-4 h-4 text-gray-400" />
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="all">所有状态</option>
                            <option value="completed">已完成</option>
                            <option value="processing">处理中</option>
                            <option value="failed">失败</option>
                            <option value="pending">等待中</option>
                        </select>
                    </div>

                    <div className="flex items-center gap-2">
                        <select
                            value={typeFilter}
                            onChange={(e) => setTypeFilter(e.target.value)}
                            className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="all">所有类型</option>
                            <option value="auto">自动解析</option>
                            <option value="text">文本提取</option>
                            <option value="table">表格提取</option>
                            <option value="image">图像提取</option>
                        </select>
                    </div>
                </div>
            </div>

            <div className="divide-y divide-gray-200">
                {items.map((item) => (
                    <div key={item.document_id} className="p-6 hover:bg-gray-50">
                        <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-3 mb-2">
                                    <FileText className="w-5 h-5 text-gray-400 flex-shrink-0" />
                                    <h3 className="text-sm font-medium truncate">
                                        {item.filename}
                                    </h3>
                                    <StatusBadge status={item.status as any} />
                                </div>

                                <div className="flex items-center gap-4 text-xs text-gray-500">
                                    <span>类型: {item.parsing_type}</span>
                                    <span className="flex items-center gap-1">
                                        <Clock className="w-3 h-3" />
                                        {new Date(item.created_at).toLocaleString()}
                                    </span>
                                    {item.processing_time && (
                                        <span>
                                            耗时: {formatDuration(item.processing_time)}
                                        </span>
                                    )}
                                    {item.quality_score && (
                                        <span className="flex items-center gap-1">
                                            <Star className="w-3 h-3 text-yellow-500" />
                                            质量: {(item.quality_score * 100).toFixed(0)}%
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div className="flex items-center gap-2 ml-4">
                                {item.status === 'completed' && onViewContent && (
                                    <button
                                        onClick={() => onViewContent(item.document_id)}
                                        className="flex items-center gap-1 px-3 py-1.5 text-xs bg-blue-50 text-blue-600 rounded-md hover:bg-blue-100"
                                        title="查看解析结果"
                                    >
                                        <Eye className="w-3 h-3" />
                                        查看
                                    </button>
                                )}

                                {item.status === 'completed' && (
                                    <button
                                        onClick={() => downloadResult(item.document_id, item.filename)}
                                        className="flex items-center gap-1 px-3 py-1.5 text-xs bg-green-50 text-green-600 rounded-md hover:bg-green-100"
                                        title="下载解析结果"
                                    >
                                        <Download className="w-3 h-3" />
                                        下载
                                    </button>
                                )}

                                <button
                                    onClick={() => deleteItem(item.document_id)}
                                    className="flex items-center gap-1 px-3 py-1.5 text-xs bg-red-50 text-red-600 rounded-md hover:bg-red-100"
                                    title="删除解析结果"
                                >
                                    <Trash2 className="w-3 h-3" />
                                    删除
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {items.length === 0 && !loading && (
                <div className="p-12 text-center text-gray-500">
                    <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>暂无解析记录</p>
                    <p className="text-sm mt-1">上传PDF文件开始解析</p>
                </div>
            )}

            {hasMore && items.length > 0 && (
                <div className="p-4 border-t border-gray-200">
                    <button
                        onClick={loadMore}
                        disabled={loading}
                        className="w-full py-2 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50"
                    >
                        {loading ? (
                            <span className="flex items-center justify-center gap-2">
                                <Loader className="w-4 h-4 animate-spin" />
                                加载中...
                            </span>
                        ) : (
                            '加载更多'
                        )}
                    </button>
                </div>
            )}
        </div>
    );
};

export default HistoryList; 