"""
文件验证和安全检查工具
确保上传文件的安全性和有效性
"""

import os
import mimetypes
import hashlib
import magic
from typing import Tuple, Optional, List
from pathlib import Path

from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class FileValidator:
    """文件验证器"""
    
    # 允许的MIME类型
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/x-pdf',
        'application/acrobat',
        'applications/vnd.pdf',
        'text/pdf',
        'text/x-pdf'
    }
    
    # 危险文件扩展名
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.com', '.cmd', '.scr', '.pif', '.vbs', '.vbe', 
        '.js', '.jse', '.ws', '.wsf', '.wsc', '.jar', '.app', '.deb', 
        '.pkg', '.dmg', '.rpm', '.msi', '.msix', '.ps1', '.psm1'
    }
    
    # PDF 文件头签名
    PDF_SIGNATURES = [
        b'%PDF-1.',  # 标准PDF头
        b'%PDF-2.',  # PDF 2.0
    ]
    
    def __init__(self):
        self.max_file_size = settings.max_file_size
        self.allowed_extensions = [f".{ext.lower()}" for ext in settings.allowed_extensions]
    
    def validate_file(self, file_path: str, original_filename: str) -> Tuple[bool, Optional[str]]:
        """
        完整的文件验证
        
        Args:
            file_path: 文件路径
            original_filename: 原始文件名
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # 1. 检查文件是否存在
            if not os.path.exists(file_path):
                return False, "文件不存在"
            
            # 2. 检查文件大小
            is_valid, error = self._validate_file_size(file_path)
            if not is_valid:
                return False, error
            
            # 3. 检查文件扩展名
            is_valid, error = self._validate_extension(original_filename)
            if not is_valid:
                return False, error
            
            # 4. 检查文件MIME类型
            is_valid, error = self._validate_mime_type(file_path)
            if not is_valid:
                return False, error
            
            # 5. 检查文件内容签名
            is_valid, error = self._validate_file_signature(file_path)
            if not is_valid:
                return False, error
            
            # 6. 检查文件完整性
            is_valid, error = self._validate_pdf_structure(file_path)
            if not is_valid:
                return False, error
            
            # 7. 安全扫描
            is_valid, error = self._security_scan(file_path, original_filename)
            if not is_valid:
                return False, error
            
            logger.info(f"文件验证通过: {original_filename}")
            return True, None
            
        except Exception as e:
            logger.error(f"文件验证出错: {e}")
            return False, f"文件验证出错: {str(e)}"
    
    def _validate_file_size(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """验证文件大小"""
        try:
            file_size = os.path.getsize(file_path)
            
            if file_size == 0:
                return False, "文件为空"
            
            if file_size > self.max_file_size:
                max_mb = self.max_file_size / (1024 * 1024)
                current_mb = file_size / (1024 * 1024)
                return False, f"文件过大: {current_mb:.1f}MB，最大允许 {max_mb:.1f}MB"
            
            return True, None
            
        except OSError as e:
            return False, f"无法读取文件大小: {e}"
    
    def _validate_extension(self, filename: str) -> Tuple[bool, Optional[str]]:
        """验证文件扩展名"""
        file_ext = Path(filename).suffix.lower()
        
        # 检查是否为危险扩展名
        if file_ext in self.DANGEROUS_EXTENSIONS:
            return False, f"危险的文件类型: {file_ext}"
        
        # 检查是否在允许列表中
        if file_ext not in self.allowed_extensions:
            allowed_str = ', '.join(self.allowed_extensions)
            return False, f"不支持的文件类型: {file_ext}，允许的类型: {allowed_str}"
        
        return True, None
    
    def _validate_mime_type(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """验证MIME类型"""
        try:
            # 使用 python-magic 库检测MIME类型
            mime_type = magic.from_file(file_path, mime=True)
            
            if mime_type not in self.ALLOWED_MIME_TYPES:
                return False, f"不支持的MIME类型: {mime_type}"
            
            return True, None
            
        except Exception as e:
            # 降级到mimetypes模块
            try:
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type not in self.ALLOWED_MIME_TYPES:
                    return False, f"不支持的MIME类型: {mime_type}"
                return True, None
            except Exception:
                logger.warning(f"MIME类型检测失败: {e}")
                return True, None  # 如果检测失败，允许通过后续验证
    
    def _validate_file_signature(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """验证文件头签名"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(32)  # 读取前32字节
                
                # 检查PDF签名
                for signature in self.PDF_SIGNATURES:
                    if header.startswith(signature):
                        return True, None
                
                return False, "文件签名不匹配，可能不是有效的PDF文件"
                
        except Exception as e:
            return False, f"无法读取文件头: {e}"
    
    def _validate_pdf_structure(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """验证PDF文件结构"""
        try:
            import fitz  # pymupdf
            
            # 尝试打开PDF文件
            doc = fitz.open(file_path)
            
            # 检查是否有页面
            if len(doc) == 0:
                doc.close()
                return False, "PDF文件没有页面"
            
            # 检查是否被加密且无法打开
            if doc.needs_pass:
                doc.close()
                return False, "PDF文件被密码保护"
            
            # 检查是否有严重损坏
            try:
                # 尝试访问第一页
                page = doc[0]
                page.get_text()
            except Exception as e:
                doc.close()
                return False, f"PDF文件可能损坏: {e}"
            
            doc.close()
            return True, None
            
        except Exception as e:
            return False, f"PDF结构验证失败: {e}"
    
    def _security_scan(self, file_path: str, filename: str) -> Tuple[bool, Optional[str]]:
        """安全扫描"""
        try:
            # 1. 检查文件名中的可疑字符
            suspicious_chars = ['<', '>', '|', '&', ';', '$', '`']
            if any(char in filename for char in suspicious_chars):
                return False, "文件名包含可疑字符"
            
            # 2. 检查路径遍历攻击
            if '..' in filename or '/' in filename or '\\' in filename:
                return False, "文件名包含路径遍历字符"
            
            # 3. 检查文件名长度
            if len(filename) > 255:
                return False, "文件名过长"
            
            # 4. 检查是否为隐藏文件
            if filename.startswith('.'):
                return False, "不允许上传隐藏文件"
            
            # 5. 简单的恶意内容检测
            is_clean, error = self._scan_malicious_content(file_path)
            if not is_clean:
                return False, error
            
            return True, None
            
        except Exception as e:
            logger.warning(f"安全扫描出错: {e}")
            return True, None  # 安全扫描失败时允许通过
    
    def _scan_malicious_content(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """扫描恶意内容"""
        try:
            # 检查文件中是否包含可疑的JavaScript或脚本
            with open(file_path, 'rb') as f:
                content = f.read(1024 * 100)  # 读取前100KB
                content_str = content.decode('utf-8', errors='ignore').lower()
                
                # 检查可疑关键词
                suspicious_keywords = [
                    'javascript:', '/javascript', 'vbscript:', '/vbscript',
                    'onload=', 'onerror=', 'onclick=', 'eval(',
                    'document.write', 'window.open', 'location.href',
                    '<script', '</script>', '<iframe', '</iframe>'
                ]
                
                for keyword in suspicious_keywords:
                    if keyword in content_str:
                        return False, f"检测到可疑内容: {keyword}"
            
            return True, None
            
        except Exception as e:
            logger.warning(f"恶意内容扫描失败: {e}")
            return True, None
    
    def get_file_hash(self, file_path: str) -> str:
        """计算文件哈希值"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败: {e}")
            return ""
    
    def get_file_info(self, file_path: str, original_filename: str) -> dict:
        """获取文件详细信息"""
        try:
            stat = os.stat(file_path)
            
            return {
                "filename": original_filename,
                "file_path": file_path,
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_time": stat.st_ctime,
                "modified_time": stat.st_mtime,
                "extension": Path(original_filename).suffix.lower(),
                "mime_type": magic.from_file(file_path, mime=True) if magic else None,
                "file_hash": self.get_file_hash(file_path)
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return {}


def validate_upload_file(file_path: str, original_filename: str) -> Tuple[bool, Optional[str], dict]:
    """
    验证上传的文件
    
    Args:
        file_path: 文件路径
        original_filename: 原始文件名
        
    Returns:
        (is_valid, error_message, file_info)
    """
    validator = FileValidator()
    
    # 验证文件
    is_valid, error = validator.validate_file(file_path, original_filename)
    
    # 获取文件信息
    file_info = validator.get_file_info(file_path, original_filename)
    
    return is_valid, error, file_info


def is_safe_filename(filename: str) -> bool:
    """检查文件名是否安全"""
    # 基本安全检查
    if not filename or filename in ['.', '..']:
        return False
    
    # 检查长度
    if len(filename) > 255:
        return False
    
    # 检查可疑字符
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\', '\x00']
    if any(char in filename for char in dangerous_chars):
        return False
    
    # 检查控制字符
    if any(ord(char) < 32 for char in filename):
        return False
    
    return True


def sanitize_filename(filename: str) -> str:
    """清理文件名"""
    import re
    
    # 移除路径部分
    filename = os.path.basename(filename)
    
    # 替换危险字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # 移除控制字符
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # 限制长度
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    
    # 确保不为空
    if not filename:
        filename = "unknown_file"
    
    return filename 