#!/usr/bin/env python3
"""
文献上传处理模块
支持Web界面上传和批量处理
"""
import os
import shutil
from werkzeug.utils import secure_filename
from datetime import datetime

class DocumentUploader:
    def __init__(self, upload_folder='food_research_data'):
        self.upload_folder = upload_folder
        self.allowed_extensions = {'txt', 'pdf', 'doc', 'docx', 'md', 'csv', 'json'}
        
        # 确保目录存在
        os.makedirs(f"{upload_folder}/papers", exist_ok=True)
        os.makedirs(f"{upload_folder}/datasets", exist_ok=True)
    
    def allowed_file(self, filename):
        """检查文件格式是否支持"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def upload_single_file(self, file, category='papers'):
        """上传单个文件"""
        if not file or file.filename == '':
            return {'success': False, 'error': '没有选择文件'}
        
        if not self.allowed_file(file.filename):
            return {'success': False, 'error': f'不支持的文件格式，支持: {", ".join(self.allowed_extensions)}'}
        
        # 安全的文件名
        filename = secure_filename(file.filename)
        
        # 避免重名
        base_name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(self.upload_folder, category, filename)):
            filename = f"{base_name}_{counter}{ext}"
            counter += 1
        
        # 保存文件
        filepath = os.path.join(self.upload_folder, category, filename)
        file.save(filepath)
        
        return {
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'size': os.path.getsize(filepath),
            'category': category
        }
    
    def upload_multiple_files(self, files, category='papers'):
        """批量上传文件"""
        results = []
        for file in files:
            result = self.upload_single_file(file, category)
            results.append(result)
        return results
    
    def list_documents(self):
        """列出所有文档"""
        documents = {'papers': [], 'datasets': []}
        
        for category in ['papers', 'datasets']:
            folder_path = os.path.join(self.upload_folder, category)
            if os.path.exists(folder_path):
                for filename in os.listdir(folder_path):
                    filepath = os.path.join(folder_path, filename)
                    if os.path.isfile(filepath):
                        documents[category].append({
                            'filename': filename,
                            'size': os.path.getsize(filepath),
                            'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                        })
        
        return documents
    
    def delete_document(self, filename, category='papers'):
        """删除文档"""
        filepath = os.path.join(self.upload_folder, category, filename)
        
        if not os.path.exists(filepath):
            return {'success': False, 'error': '文件不存在'}
        
        try:
            os.remove(filepath)
            return {'success': True, 'message': f'已删除 {filename}'}
        except Exception as e:
            return {'success': False, 'error': f'删除失败: {str(e)}'}

# 全局上传器实例
uploader = DocumentUploader()
