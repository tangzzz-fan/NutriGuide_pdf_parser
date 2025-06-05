import React, { useState, useEffect } from 'react';
import {
    FileText,
    Download,
    Eye,
    Clock,
    CheckCircle,
    AlertCircle,
    Star,
    Users,
    Timer,
    X
} from 'lucide-react';

interface ParsedContent {
    document_id: string;
    filename: string;
    parsing_type: string;
    status: string;
    created_at: string;
    result?: {
        content?: string;
        nutrition_info?: {
            calories?: number;
            protein?: number;
            carbs?: number;
            fat?: number;
            fiber?: number;
            sugar?: number;
            sodium?: number;
            [key: string]: any;
        };
        recipe_info?: {
            title?: string;
            ingredients?: string[];
            instructions?: string[];
            prep_time?: string;
            cook_time?: string;
            servings?: number;
            difficulty?: string;
            [key: string]: any;
        };
        text_content?: string;
        quality_score?: number;
        [key: string]: any;
    };
}

interface ParsedContentViewerProps {
    documentId: string;
    onClose?: () => void;
}

const ParsedContentViewer: React.FC<ParsedContentViewerProps> = ({
    documentId,
    onClose
}) => {
    const [content, setContent] = useState<ParsedContent | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState('overview');

    useEffect(() => {
        fetchParsedContent();
    }, [documentId]);

    const fetchParsedContent = async () => {
        try {
            setLoading(true);
            const response = await fetch(`/api/parse/result/${documentId}`);

            if (!response.ok) {
                throw new Error('获取解析内容失败');
            }

            const data = await response.json();
            setContent(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : '未知错误');
        } finally {
            setLoading(false);
        }
    };

    const downloadResult = async () => {
        if (!content) return;

        try {
            const response = await fetch(`/api/parse/result/${documentId}/download`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${content.filename}_parsed.json`;
                a.click();
                window.URL.revokeObjectURL(url);
            } else {
                // 如果没有专门的下载端点，就下载当前数据
                const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(content.result, null, 2));
                const downloadAnchorNode = document.createElement('a');
                downloadAnchorNode.setAttribute("href", dataStr);
                downloadAnchorNode.setAttribute("download", `${content.filename}_parsed.json`);
                document.body.appendChild(downloadAnchorNode);
                downloadAnchorNode.click();
                downloadAnchorNode.remove();
            }
        } catch (err) {
            console.error('下载失败:', err);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return 'bg-green-100 text-green-800';
            case 'processing': return 'bg-blue-100 text-blue-800';
            case 'failed': return 'bg-red-100 text-red-800';
            case 'queued': return 'bg-yellow-100 text-yellow-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const renderNutritionInfo = (nutrition: Record<string, any>) => (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(nutrition).map(([key, value]) => (
                <div key={key} className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-sm font-medium text-gray-600 capitalize">
                        {key.replace('_', ' ')}
                    </div>
                    <div className="text-lg font-semibold text-gray-900">
                        {typeof value === 'number' ? value.toFixed(1) : String(value)}
                        {key === 'calories' ? ' kcal' :
                            ['protein', 'carbs', 'fat', 'fiber', 'sugar'].includes(key) ? ' g' :
                                key === 'sodium' ? ' mg' : ''}
                    </div>
                </div>
            ))}
        </div>
    );

    const renderRecipeInfo = (recipe: Record<string, any>) => (
        <div className="space-y-6">
            {recipe.title && (
                <div>
                    <h3 className="font-semibold text-lg mb-2">{String(recipe.title)}</h3>
                </div>
            )}

            <div className="flex flex-wrap gap-4">
                {recipe.prep_time && (
                    <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4 text-gray-500" />
                        <span className="text-sm">准备时间: {String(recipe.prep_time)}</span>
                    </div>
                )}
                {recipe.cook_time && (
                    <div className="flex items-center gap-2">
                        <Timer className="w-4 h-4 text-gray-500" />
                        <span className="text-sm">烹饪时间: {String(recipe.cook_time)}</span>
                    </div>
                )}
                {recipe.servings && (
                    <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-gray-500" />
                        <span className="text-sm">份量: {String(recipe.servings)}</span>
                    </div>
                )}
                {recipe.difficulty && (
                    <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded-full border">
                        {String(recipe.difficulty)}
                    </span>
                )}
            </div>

            {recipe.ingredients && Array.isArray(recipe.ingredients) && recipe.ingredients.length > 0 && (
                <div>
                    <h4 className="font-medium mb-3">配料</h4>
                    <ul className="space-y-1">
                        {recipe.ingredients.map((ingredient: any, index: number) => (
                            <li key={index} className="text-sm flex items-start gap-2">
                                <span className="w-2 h-2 bg-gray-400 rounded-full mt-2 flex-shrink-0" />
                                {String(ingredient)}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {recipe.instructions && Array.isArray(recipe.instructions) && recipe.instructions.length > 0 && (
                <div>
                    <h4 className="font-medium mb-3">制作步骤</h4>
                    <ol className="space-y-3">
                        {recipe.instructions.map((instruction: any, index: number) => (
                            <li key={index} className="text-sm flex gap-3">
                                <span className="bg-blue-100 text-blue-800 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium flex-shrink-0">
                                    {index + 1}
                                </span>
                                <span>{String(instruction)}</span>
                            </li>
                        ))}
                    </ol>
                </div>
            )}
        </div>
    );

    if (loading) {
        return (
            <div className="w-full max-w-4xl mx-auto bg-white rounded-lg shadow-lg">
                <div className="p-6">
                    <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <span className="ml-3">加载解析内容中...</span>
                    </div>
                </div>
            </div>
        );
    }

    if (error || !content) {
        return (
            <div className="w-full max-w-4xl mx-auto bg-white rounded-lg shadow-lg">
                <div className="p-6">
                    <div className="flex items-center justify-center py-8 text-red-600">
                        <AlertCircle className="w-8 h-8 mr-3" />
                        <span>{error || '内容不存在'}</span>
                    </div>
                </div>
            </div>
        );
    }

    const tabClasses = (isActive: boolean) =>
        `px-4 py-2 text-sm font-medium rounded-md transition-colors ${isActive
            ? 'bg-blue-100 text-blue-700'
            : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
        }`;

    return (
        <div className="w-full max-w-4xl mx-auto bg-white rounded-lg shadow-lg">
            {/* Header */}
            <div className="border-b border-gray-200 p-6">
                <div className="flex items-start justify-between">
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                            <FileText className="w-6 h-6" />
                            <h2 className="text-xl font-semibold">{content.filename}</h2>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                            <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(content.status)}`}>
                                {content.status === 'completed' && <CheckCircle className="w-3 h-3 mr-1 inline" />}
                                {content.status}
                            </span>
                            <span>类型: {content.parsing_type}</span>
                            <span>创建: {new Date(content.created_at).toLocaleString()}</span>
                            {content.result?.quality_score && (
                                <div className="flex items-center gap-1">
                                    <Star className="w-4 h-4 text-yellow-500" />
                                    <span>质量: {(content.result.quality_score * 100).toFixed(0)}%</span>
                                </div>
                            )}
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={downloadResult}
                            className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                        >
                            <Download className="w-4 h-4" />
                            下载
                        </button>
                        {onClose && (
                            <button
                                onClick={onClose}
                                className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                            >
                                <X className="w-4 h-4" />
                                关闭
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200">
                <div className="flex space-x-1 p-4">
                    {[
                        { id: 'overview', label: '概览' },
                        { id: 'content', label: '内容' },
                        { id: 'structured', label: '结构化' },
                        { id: 'raw', label: '原始数据' }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={tabClasses(activeTab === tab.id)}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Tab Content */}
            <div className="p-6">
                {activeTab === 'overview' && (
                    <div className="space-y-6">
                        {content.result?.nutrition_info && (
                            <div>
                                <h3 className="font-semibold text-lg mb-4">营养信息</h3>
                                {renderNutritionInfo(content.result.nutrition_info)}
                            </div>
                        )}

                        {content.result?.recipe_info && (
                            <div>
                                <h3 className="font-semibold text-lg mb-4">食谱信息</h3>
                                {renderRecipeInfo(content.result.recipe_info)}
                            </div>
                        )}

                        {content.result?.text_content && (
                            <div>
                                <h3 className="font-semibold text-lg mb-4">文本摘要</h3>
                                <div className="bg-gray-50 p-4 rounded-lg">
                                    <p className="text-sm leading-relaxed">
                                        {content.result.text_content.substring(0, 500)}
                                        {content.result.text_content.length > 500 && '...'}
                                    </p>
                                </div>
                            </div>
                        )}

                        {(!content.result?.nutrition_info && !content.result?.recipe_info && !content.result?.text_content) && (
                            <div className="text-center py-8 text-gray-500">
                                <Eye className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                <p>暂无可展示的内容</p>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'content' && (
                    <div className="h-96 w-full border rounded-md overflow-auto p-4 bg-gray-50">
                        <div className="whitespace-pre-wrap text-sm">
                            {content.result?.content || content.result?.text_content || '暂无文本内容'}
                        </div>
                    </div>
                )}

                {activeTab === 'structured' && (
                    <div className="space-y-6">
                        {content.result?.nutrition_info && (
                            <div>
                                <h4 className="font-medium mb-3">营养成分详情</h4>
                                {renderNutritionInfo(content.result.nutrition_info)}
                            </div>
                        )}

                        {content.result?.recipe_info && (
                            <div>
                                <h4 className="font-medium mb-3">食谱详情</h4>
                                {renderRecipeInfo(content.result.recipe_info)}
                            </div>
                        )}

                        {(!content.result?.nutrition_info && !content.result?.recipe_info) && (
                            <div className="text-center py-8 text-gray-500">
                                <Eye className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                <p>暂无结构化数据</p>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'raw' && (
                    <div className="h-96 w-full border rounded-md overflow-auto">
                        <pre className="p-4 text-xs bg-gray-50">
                            {JSON.stringify(content.result || {}, null, 2)}
                        </pre>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ParsedContentViewer; 