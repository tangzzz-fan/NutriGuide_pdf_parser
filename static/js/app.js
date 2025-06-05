// NutriGuide PDF Parser - 前端交互逻辑
class PDFParserApp {
    constructor() {
        this.selectedFiles = [];
        this.currentBatchId = null;
        this.statsUpdateInterval = null;
        this.historyUpdateInterval = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startPeriodicUpdates();
    }

    setupEventListeners() {
        // 文件上传处理
        const fileInput = document.getElementById('files');
        const fileDropArea = document.getElementById('fileDropArea');
        const uploadForm = document.getElementById('uploadForm');

        // 文件选择
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files);
        });

        // 拖拽处理
        fileDropArea.addEventListener('click', () => {
            fileInput.click();
        });

        fileDropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            fileDropArea.classList.add('drag-over');
        });

        fileDropArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            fileDropArea.classList.remove('drag-over');
        });

        fileDropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            fileDropArea.classList.remove('drag-over');
            const files = Array.from(e.dataTransfer.files).filter(file =>
                file.type === 'application/pdf'
            );
            this.handleFileSelect(files);
        });

        // 表单提交
        uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmit();
        });
    }

    handleFileSelect(files) {
        // 验证文件
        const validFiles = Array.from(files).filter(file => {
            if (file.type !== 'application/pdf') {
                this.showAlert('只支持PDF文件格式', 'warning');
                return false;
            }

            if (file.size > 50 * 1024 * 1024) { // 50MB
                this.showAlert(`文件 ${file.name} 过大（超过50MB限制）`, 'warning');
                return false;
            }

            // 检查是否已存在
            if (this.selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
                this.showAlert(`文件 ${file.name} 已存在`, 'warning');
                return false;
            }

            return true;
        });

        // 添加到选中文件列表
        this.selectedFiles.push(...validFiles);
        this.updateFileList();

        if (validFiles.length > 0) {
            this.showAlert(`已添加 ${validFiles.length} 个文件`, 'success');
        }
    }

    updateFileList() {
        const fileList = document.getElementById('fileList');

        if (this.selectedFiles.length === 0) {
            fileList.innerHTML = '';
            return;
        }

        const html = this.selectedFiles.map((file, index) => `
            <div class="file-item fade-in">
                <div class="file-info">
                    <i class="bi bi-file-earmark-pdf file-icon"></i>
                    <div class="file-details">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                    </div>
                </div>
                <button type="button" class="file-remove" onclick="app.removeFile(${index})" 
                        title="移除文件">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
        `).join('');

        fileList.innerHTML = html;
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateFileList();
        this.showAlert('文件已移除', 'info');
    }

    async handleFormSubmit() {
        if (this.selectedFiles.length === 0) {
            this.showAlert('请先选择要解析的PDF文件', 'warning');
            return;
        }

        const submitBtn = document.getElementById('submitBtn');
        const uploadProgress = document.getElementById('uploadProgress');
        const progressBar = uploadProgress.querySelector('.progress-bar');

        try {
            // 显示上传进度
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>处理中...';
            uploadProgress.style.display = 'block';

            // 准备表单数据
            const parseType = document.getElementById('parseType').value;
            const priority = document.getElementById('priority').value;
            const description = document.getElementById('description').value;

            // 批量上传文件
            let successCount = 0;
            let totalFiles = this.selectedFiles.length;

            for (let i = 0; i < this.selectedFiles.length; i++) {
                const file = this.selectedFiles[i];
                const formData = new FormData();
                formData.append('file', file);
                formData.append('parsing_type', parseType);
                formData.append('priority', priority || 'normal');

                try {
                    // 更新进度
                    const progress = ((i + 1) / totalFiles) * 100;
                    progressBar.style.width = `${progress}%`;
                    progressBar.textContent = `${Math.round(progress)}%`;

                    // 发送请求
                    const response = await fetch('/parse/async', {
                        method: 'POST',
                        body: formData
                    });

                    if (response.ok) {
                        successCount++;
                    } else {
                        const error = await response.json();
                        console.error(`文件 ${file.name} 上传失败:`, error);
                    }
                } catch (error) {
                    console.error(`文件 ${file.name} 上传出错:`, error);
                }
            }

            // 显示结果
            if (successCount === totalFiles) {
                this.showAlert(`成功提交 ${successCount} 个文件进行解析`, 'success');
            } else {
                this.showAlert(`已提交 ${successCount}/${totalFiles} 个文件，部分文件可能失败`, 'warning');
            }

            // 清理
            this.selectedFiles = [];
            this.updateFileList();
            document.getElementById('uploadForm').reset();

            // 刷新数据
            this.loadBatchHistory();
            this.updateStats();

        } catch (error) {
            console.error('批量上传失败:', error);
            this.showAlert('批量上传失败，请重试', 'danger');
        } finally {
            // 恢复界面
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-play-circle me-2"></i>开始批量解析';
            uploadProgress.style.display = 'none';
            progressBar.style.width = '0%';
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.loadBatchHistory(),
            this.updateStats(),
            this.loadRecentTasks()
        ]);
    }

    async loadBatchHistory(page = 1, status = 'all') {
        try {
            const params = new URLSearchParams({
                limit: 10,
                offset: (page - 1) * 10
            });

            if (status !== 'all') {
                params.append('status', status);
            }

            const response = await fetch(`/parse/history?${params}`);
            const data = await response.json();

            this.renderHistoryTable(data.results || []);
            this.renderPagination(data.total || 0, page, 10);

        } catch (error) {
            console.error('加载历史记录失败:', error);
            this.showAlert('加载历史记录失败', 'danger');
        }
    }

    renderHistoryTable(batches) {
        const tbody = document.getElementById('historyTable');

        if (batches.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted py-4">
                        <i class="bi bi-inbox display-4"></i>
                        <div class="mt-2">暂无解析记录</div>
                    </td>
                </tr>
            `;
            return;
        }

        const html = batches.map(batch => {
            const progress = batch.total_files > 0
                ? Math.round((batch.completed_files / batch.total_files) * 100)
                : 0;

            const statusClass = this.getStatusClass(batch.status);
            const duration = this.calculateDuration(batch.created_at, batch.updated_at);

            return `
                <tr>
                    <td>
                        <code class="text-primary">${batch.batch_id.substring(0, 8)}...</code>
                    </td>
                    <td>
                        <span class="badge bg-secondary">${batch.total_files || 0}</span>
                    </td>
                    <td>
                        <span class="badge bg-info">${this.getParseTypeLabel(batch.parsing_type)}</span>
                    </td>
                    <td>
                        <span class="status-badge ${statusClass}">${this.getStatusLabel(batch.status)}</span>
                    </td>
                    <td>
                        <div class="progress-circle" style="background: conic-gradient(var(--primary-color) ${progress * 3.6}deg, #e5e7eb 0deg);">
                            <span class="progress-text">${progress}%</span>
                        </div>
                    </td>
                    <td>
                        <small class="text-muted">${this.formatDateTime(batch.created_at)}</small>
                    </td>
                    <td>
                        <small class="text-muted">${duration}</small>
                    </td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn btn-outline-primary btn-action" 
                                    onclick="app.showBatchDetail('${batch.batch_id}')" 
                                    title="查看详情">
                                <i class="bi bi-eye"></i>
                            </button>
                            <button class="btn btn-outline-success btn-action" 
                                    onclick="app.downloadBatch('${batch.batch_id}')" 
                                    title="下载数据"
                                    ${batch.status !== 'completed' ? 'disabled' : ''}>
                                <i class="bi bi-download"></i>
                            </button>
                            <button class="btn btn-outline-danger btn-action" 
                                    onclick="app.deleteBatch('${batch.batch_id}')" 
                                    title="删除批次">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        tbody.innerHTML = html;
    }

    renderPagination(total, currentPage, pageSize) {
        const totalPages = Math.ceil(total / pageSize);
        const pagination = document.getElementById('historyPagination');

        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        let html = '';

        // 上一页
        html += `
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="app.loadBatchHistory(${currentPage - 1})">
                    <i class="bi bi-chevron-left"></i>
                </a>
            </li>
        `;

        // 页码
        const start = Math.max(1, currentPage - 2);
        const end = Math.min(totalPages, currentPage + 2);

        if (start > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" onclick="app.loadBatchHistory(1)">1</a></li>`;
            if (start > 2) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }

        for (let i = start; i <= end; i++) {
            html += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="app.loadBatchHistory(${i})">${i}</a>
                </li>
            `;
        }

        if (end < totalPages) {
            if (end < totalPages - 1) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            html += `<li class="page-item"><a class="page-link" href="#" onclick="app.loadBatchHistory(${totalPages})">${totalPages}</a></li>`;
        }

        // 下一页
        html += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="app.loadBatchHistory(${currentPage + 1})">
                    <i class="bi bi-chevron-right"></i>
                </a>
            </li>
        `;

        pagination.innerHTML = html;
    }

    async updateStats() {
        try {
            const response = await fetch('/admin/stats/real-time');
            const stats = await response.json();

            document.getElementById('processingCount').textContent = stats.processing || 0;
            document.getElementById('queueCount').textContent = stats.queued || 0;
            document.getElementById('completedToday').textContent = stats.completed_today || 0;
            document.getElementById('successRate').textContent = `${stats.success_rate || 0}%`;

        } catch (error) {
            console.error('更新统计数据失败:', error);
        }
    }

    async loadRecentTasks() {
        try {
            const response = await fetch('/admin/stats/recent-tasks?limit=5');
            const tasks = await response.json();

            const recentTasksContainer = document.getElementById('recentTasks');

            if (tasks.length === 0) {
                recentTasksContainer.innerHTML = `
                    <div class="text-center text-muted py-3">
                        <i class="bi bi-inbox"></i>
                        <div class="mt-1">暂无最近任务</div>
                    </div>
                `;
                return;
            }

            const html = tasks.map(task => `
                <div class="recent-task-item">
                    <div class="task-status-dot ${task.status}"></div>
                    <div class="task-info">
                        <div class="task-name">${task.filename}</div>
                        <div class="task-time">${this.formatTimeAgo(task.updated_at)}</div>
                    </div>
                </div>
            `).join('');

            recentTasksContainer.innerHTML = html;

        } catch (error) {
            console.error('加载最近任务失败:', error);
        }
    }

    startPeriodicUpdates() {
        // 每10秒更新统计数据
        this.statsUpdateInterval = setInterval(() => {
            this.updateStats();
            this.loadRecentTasks();
        }, 10000);

        // 每30秒更新历史记录
        this.historyUpdateInterval = setInterval(() => {
            this.loadBatchHistory(1, 'all');
        }, 30000);
    }

    stopPeriodicUpdates() {
        if (this.statsUpdateInterval) {
            clearInterval(this.statsUpdateInterval);
        }
        if (this.historyUpdateInterval) {
            clearInterval(this.historyUpdateInterval);
        }
    }

    async showBatchDetail(batchId) {
        try {
            const response = await fetch(`/admin/batches/${batchId}`);
            const batch = await response.json();

            const modalBody = document.getElementById('detailModalBody');
            modalBody.innerHTML = this.renderBatchDetail(batch);

            const modal = new bootstrap.Modal(document.getElementById('detailModal'));
            modal.show();

            this.currentBatchId = batchId;

        } catch (error) {
            console.error('加载批次详情失败:', error);
            this.showAlert('加载批次详情失败', 'danger');
        }
    }

    renderBatchDetail(batch) {
        const progress = batch.total_files > 0
            ? Math.round((batch.completed_files / batch.total_files) * 100)
            : 0;

        return `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-muted">基础信息</h6>
                    <table class="table table-sm">
                        <tr><td>批次ID</td><td><code>${batch.batch_id}</code></td></tr>
                        <tr><td>解析类型</td><td>${this.getParseTypeLabel(batch.parsing_type)}</td></tr>
                        <tr><td>创建时间</td><td>${this.formatDateTime(batch.created_at)}</td></tr>
                        <tr><td>状态</td><td><span class="status-badge ${this.getStatusClass(batch.status)}">${this.getStatusLabel(batch.status)}</span></td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6 class="text-muted">处理进度</h6>
                    <div class="mb-2">
                        <div class="d-flex justify-content-between">
                            <span>总体进度</span>
                            <span>${progress}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar" style="width: ${progress}%"></div>
                        </div>
                    </div>
                    <table class="table table-sm">
                        <tr><td>总文件数</td><td>${batch.total_files || 0}</td></tr>
                        <tr><td>已完成</td><td class="text-success">${batch.completed_files || 0}</td></tr>
                        <tr><td>处理中</td><td class="text-warning">${batch.processing_files || 0}</td></tr>
                        <tr><td>失败</td><td class="text-danger">${batch.failed_files || 0}</td></tr>
                    </table>
                </div>
            </div>
            
            ${batch.description ? `
                <div class="mt-3">
                    <h6 class="text-muted">批次描述</h6>
                    <p class="text-muted">${batch.description}</p>
                </div>
            ` : ''}
            
            <div class="mt-3">
                <h6 class="text-muted">文件列表</h6>
                <div class="table-responsive" style="max-height: 300px;">
                    <table class="table table-sm">
                        <thead class="table-light">
                            <tr>
                                <th>文件名</th>
                                <th>状态</th>
                                <th>处理时间</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${(batch.files || []).map(file => `
                                <tr>
                                    <td>
                                        <i class="bi bi-file-earmark-pdf text-danger me-2"></i>
                                        ${file.filename}
                                    </td>
                                    <td>
                                        <span class="status-badge ${this.getStatusClass(file.status)}">${this.getStatusLabel(file.status)}</span>
                                    </td>
                                    <td class="text-muted">${file.updated_at ? this.formatTimeAgo(file.updated_at) : '-'}</td>
                                    <td>
                                        ${file.status === 'completed' ? `
                                            <button class="btn btn-outline-primary btn-sm" onclick="app.downloadFileResult('${file.file_id}')">
                                                <i class="bi bi-download"></i>
                                            </button>
                                        ` : ''}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    async downloadBatch(batchId) {
        try {
            const response = await fetch(`/admin/export/batch/${batchId}`);
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `batch_${batchId}.zip`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                this.showAlert('数据下载开始', 'success');
            } else {
                throw new Error('下载失败');
            }
        } catch (error) {
            console.error('下载批次数据失败:', error);
            this.showAlert('下载失败，请重试', 'danger');
        }
    }

    async deleteBatch(batchId) {
        if (!confirm('确定要删除这个批次吗？此操作不可恢复。')) {
            return;
        }

        try {
            const response = await fetch(`/admin/batches/${batchId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showAlert('批次已删除', 'success');
                this.loadBatchHistory();
            } else {
                throw new Error('删除失败');
            }
        } catch (error) {
            console.error('删除批次失败:', error);
            this.showAlert('删除失败，请重试', 'danger');
        }
    }

    // 工具函数
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDateTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    formatTimeAgo(dateString) {
        const now = new Date();
        const date = new Date(dateString);
        const diff = now - date;

        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        return `${days}天前`;
    }

    calculateDuration(startTime, endTime) {
        if (!endTime) return '-';

        const start = new Date(startTime);
        const end = new Date(endTime);
        const diff = end - start;

        const minutes = Math.floor(diff / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);

        if (minutes > 0) {
            return `${minutes}分${seconds}秒`;
        }
        return `${seconds}秒`;
    }

    getStatusClass(status) {
        const statusMap = {
            'completed': 'status-completed',
            'processing': 'status-processing',
            'failed': 'status-failed',
            'queued': 'status-queued',
            'pending': 'status-queued'
        };
        return statusMap[status] || 'status-queued';
    }

    getStatusLabel(status) {
        const statusMap = {
            'completed': '已完成',
            'processing': '处理中',
            'failed': '失败',
            'queued': '队列中',
            'pending': '等待中'
        };
        return statusMap[status] || '未知';
    }

    getParseTypeLabel(parseType) {
        const typeMap = {
            'auto': '自动识别',
            'nutrition_label': '营养标签',
            'recipe': '食谱',
            'diet_guide': '膳食指南'
        };
        return typeMap[parseType] || parseType;
    }

    showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('alertContainer');
        const alertId = 'alert-' + Date.now();

        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" id="${alertId}">
                <i class="bi bi-${this.getAlertIcon(type)} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        alertContainer.insertAdjacentHTML('beforeend', alertHtml);

        // 3秒后自动关闭
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 3000);
    }

    getAlertIcon(type) {
        const iconMap = {
            'success': 'check-circle',
            'danger': 'exclamation-triangle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return iconMap[type] || 'info-circle';
    }
}

// 全局函数
function exportAll() {
    window.location.href = '/admin/export/all';
}

function refreshStats() {
    app.updateStats();
    app.loadRecentTasks();
    app.showAlert('统计数据已刷新', 'success');
}

function refreshHistory() {
    app.loadBatchHistory();
    app.showAlert('历史记录已刷新', 'success');
}

function clearCompleted() {
    if (confirm('确定要清理所有已完成的任务吗？')) {
        fetch('/admin/cleanup/completed', { method: 'POST' })
            .then(response => {
                if (response.ok) {
                    app.showAlert('已完成任务已清理', 'success');
                    app.loadBatchHistory();
                } else {
                    throw new Error('清理失败');
                }
            })
            .catch(error => {
                console.error('清理失败:', error);
                app.showAlert('清理失败，请重试', 'danger');
            });
    }
}

function filterByStatus(status) {
    app.loadBatchHistory(1, status);
}

function downloadBatchData() {
    if (app.currentBatchId) {
        app.downloadBatch(app.currentBatchId);
    }
}

// 初始化应用
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new PDFParserApp();
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (app) {
        app.stopPeriodicUpdates();
    }
}); 