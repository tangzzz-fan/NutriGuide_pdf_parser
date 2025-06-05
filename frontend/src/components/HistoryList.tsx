import React, { useState, useEffect } from 'react';
import {
    FileText,
    Eye,
    Clock,
    CheckCircle,
    AlertCircle,
    Loader,
    Star,
    Trash2
} from 'lucide-react';
import { StatusBadge } from './StatusBadge';

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

    const pageSize = 10;

    useEffect(() => {
        fetchHistory(true);
    }, [refreshTrigger]);

    const fetchHistory = async (reset = false) => {
        try {
            if (reset) {
                setLoading(true);
                setCurrentPage(0);
            }

            const page = reset ? 0 : currentPage;
            const response = await fetch(
                `/api/parse/history?limit=${pageSize}&offset=${page * pageSize}`
            );

            if (!response.ok) {
                throw new Error('获取历史记录失败');
            }

            const data = await response.json();

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
            setError(err instanceof Error ? err.message : '未知错误');
        } finally {
            setLoading(false);
        }
    };

    const loadMore = () => {
        if (!loading && hasMore) {
            setCurrentPage(prev => prev + 1);
            fetchHistory(false);
        }
    };

    const deleteItem = async (documentId: string) => {
        if (!confirm('确定要删除这个解析结果吗？')) {
            return;
        }

        try {
            const response = await fetch(`/api/parse/result/${documentId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                setItems(prev => prev.filter(item => item.document_id !== documentId));
                setTotal(prev => prev - 1);
            } else {
                alert('删除失败');
            }
        } catch (err) {
            console.error('删除失败:', err);
            alert('删除失败');
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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
                <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold">解析历史</h2>
                    <span className="text-sm text-gray-500">总计 {total} 个文件</span>
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
                                    >
                                        <Eye className="w-3 h-3" />
                                        查看
                                    </button>
                                )}

                                <button
                                    onClick={() => deleteItem(item.document_id)}
                                    className="flex items-center gap-1 px-3 py-1.5 text-xs bg-red-50 text-red-600 rounded-md hover:bg-red-100"
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