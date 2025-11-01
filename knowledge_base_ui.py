#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
from datetime import datetime
import webbrowser
from PIL import Image, ImageTk
import re

# 导入PDF知识提取模块
try:
    from pdf_knowledge_extractor import PDFKnowledgeExtractor
except ImportError:
    print("错误: 未找到PDF知识提取模块，请确保pdf_knowledge_extractor.py在同一目录下")
    sys.exit(1)

class ModernUI(tk.Tk):
    """现代化知识库界面"""
    
    def __init__(self):
        super().__init__()
        
        # 窗口设置
        self.title("智能知识库系统")
        self.geometry("1200x800")
        self.minsize(900, 600)
        
        # 颜色主题
        self.colors = {
            "primary": "#2c3e50",
            "secondary": "#3498db",
            "accent": "#e74c3c",
            "background": "#ecf0f1",
            "text": "#2c3e50",
            "light_text": "#7f8c8d",
            "success": "#2ecc71",
            "warning": "#f39c12",
            "card_bg": "#ffffff"
        }
        
        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # 配置样式
        self.style.configure("TFrame", background=self.colors["background"])
        self.style.configure("TLabel", background=self.colors["background"], foreground=self.colors["text"])
        self.style.configure("TButton", 
                            background=self.colors["secondary"], 
                            foreground="white", 
                            padding=10, 
                            font=("Arial", 10, "bold"))
        self.style.map("TButton",
                      background=[("active", self.colors["primary"])],
                      foreground=[("active", "white")])
        
        # 创建PDF知识提取器
        self.extractor = PDFKnowledgeExtractor()
        
        # 知识库数据
        self.knowledge_base = {}
        self.current_pdf = None
        
        # 创建UI组件
        self.create_widgets()
        
        # 加载已有知识库
        self.load_knowledge_base()
    
    def create_widgets(self):
        """创建UI组件"""
        # 主框架
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部工具栏
        self.create_toolbar()
        
        # 左侧面板和右侧内容区
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 左侧面板
        self.left_panel = ttk.Frame(self.paned_window, width=300)
        self.paned_window.add(self.left_panel, weight=1)
        
        # 右侧内容区
        self.right_panel = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_panel, weight=3)
        
        # 创建左侧文档列表
        self.create_document_list()
        
        # 创建右侧内容区
        self.create_content_area()
        
        # 状态栏
        self.status_bar = ttk.Label(self.main_frame, text="就绪", anchor=tk.W, 
                                   background="#f0f0f0", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_toolbar(self):
        """创建顶部工具栏"""
        toolbar = ttk.Frame(self.main_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        # 导入PDF按钮
        import_btn = ttk.Button(toolbar, text="导入PDF", command=self.import_pdf)
        import_btn.pack(side=tk.LEFT, padx=5)
        
        # 刷新按钮
        refresh_btn = ttk.Button(toolbar, text="刷新", command=self.refresh_knowledge_base)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # 搜索框
        self.search_var = tk.StringVar()
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
        
        search_label = ttk.Label(search_frame, text="搜索:")
        search_label.pack(side=tk.LEFT, padx=(0, 5))
        
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        search_entry.bind("<Return>", lambda e: self.search_knowledge())
        
        search_btn = ttk.Button(search_frame, text="搜索", command=self.search_knowledge)
        search_btn.pack(side=tk.LEFT)
    
    def create_document_list(self):
        """创建左侧文档列表"""
        # 文档列表标题
        list_header = ttk.Frame(self.left_panel)
        list_header.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        list_title = ttk.Label(list_header, text="知识文档", font=("Arial", 12, "bold"))
        list_title.pack(side=tk.LEFT, padx=5)
        
        # 文档列表
        list_frame = ttk.Frame(self.left_panel)
        list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 创建Treeview用于显示文档
        columns = ("name", "pages", "date")
        self.doc_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # 定义列
        self.doc_tree.heading("name", text="文档名称")
        self.doc_tree.heading("pages", text="页数")
        self.doc_tree.heading("date", text="导入日期")
        
        # 设置列宽
        self.doc_tree.column("name", width=150)
        self.doc_tree.column("pages", width=50)
        self.doc_tree.column("date", width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.doc_tree.yview)
        self.doc_tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置组件
        self.doc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.doc_tree.bind("<<TreeviewSelect>>", self.on_document_select)
    
    def create_content_area(self):
        """创建右侧内容区"""
        # 内容区标题
        content_header = ttk.Frame(self.right_panel)
        content_header.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        self.content_title = ttk.Label(content_header, text="知识内容", font=("Arial", 14, "bold"))
        self.content_title.pack(side=tk.LEFT, padx=5)
        
        # 选项卡
        self.notebook = ttk.Notebook(self.right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 知识点选项卡
        self.knowledge_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.knowledge_frame, text="知识点")
        
        # 概念选项卡
        self.concepts_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.concepts_frame, text="关键概念")
        
        # 图表选项卡
        self.charts_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.charts_frame, text="图表信息")
        
        # 元数据选项卡
        self.metadata_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.metadata_frame, text="文档信息")
        
        # 创建知识点内容
        self.create_knowledge_content()
        
        # 创建概念内容
        self.create_concepts_content()
        
        # 创建图表内容
        self.create_charts_content()
        
        # 创建元数据内容
        self.create_metadata_content()
    
    def create_knowledge_content(self):
        """创建知识点内容区"""
        # 过滤选项
        filter_frame = ttk.Frame(self.knowledge_frame)
        filter_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        filter_label = ttk.Label(filter_frame, text="过滤类型:")
        filter_label.pack(side=tk.LEFT, padx=5)
        
        self.filter_var = tk.StringVar(value="全部")
        filter_types = ["全部", "定义", "方法", "示例", "原因", "特征", "信息"]
        
        for filter_type in filter_types:
            rb = ttk.Radiobutton(filter_frame, text=filter_type, value=filter_type, 
                               variable=self.filter_var, command=self.filter_knowledge)
            rb.pack(side=tk.LEFT, padx=5)
        
        # 知识点列表
        knowledge_list_frame = ttk.Frame(self.knowledge_frame)
        knowledge_list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        
        # 创建知识点列表
        columns = ("id", "type", "importance", "content")
        self.knowledge_tree = ttk.Treeview(knowledge_list_frame, columns=columns, show="headings")
        
        # 定义列
        self.knowledge_tree.heading("id", text="#")
        self.knowledge_tree.heading("type", text="类型")
        self.knowledge_tree.heading("importance", text="重要性")
        self.knowledge_tree.heading("content", text="内容")
        
        # 设置列宽
        self.knowledge_tree.column("id", width=30)
        self.knowledge_tree.column("type", width=60)
        self.knowledge_tree.column("importance", width=60)
        self.knowledge_tree.column("content", width=600)
        
        # 添加滚动条
        scrollbar_y = ttk.Scrollbar(knowledge_list_frame, orient=tk.VERTICAL, command=self.knowledge_tree.yview)
        scrollbar_x = ttk.Scrollbar(knowledge_list_frame, orient=tk.HORIZONTAL, command=self.knowledge_tree.xview)
        self.knowledge_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # 放置组件
        self.knowledge_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 绑定双击事件
        self.knowledge_tree.bind("<Double-1>", self.show_knowledge_detail)
    
    def create_concepts_content(self):
        """创建概念内容区"""
        # 概念列表
        concepts_list_frame = ttk.Frame(self.concepts_frame)
        concepts_list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        
        # 创建概念列表
        columns = ("id", "term", "frequency")
        self.concepts_tree = ttk.Treeview(concepts_list_frame, columns=columns, show="headings")
        
        # 定义列
        self.concepts_tree.heading("id", text="#")
        self.concepts_tree.heading("term", text="概念术语")
        self.concepts_tree.heading("frequency", text="出现频率")
        
        # 设置列宽
        self.concepts_tree.column("id", width=30)
        self.concepts_tree.column("term", width=200)
        self.concepts_tree.column("frequency", width=100)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(concepts_list_frame, orient=tk.VERTICAL, command=self.concepts_tree.yview)
        self.concepts_tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置组件
        self.concepts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_charts_content(self):
        """创建图表内容区"""
        # 图表列表
        charts_list_frame = ttk.Frame(self.charts_frame)
        charts_list_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        
        # 创建图表列表
        columns = ("id", "type", "page", "details")
        self.charts_tree = ttk.Treeview(charts_list_frame, columns=columns, show="headings")
        
        # 定义列
        self.charts_tree.heading("id", text="#")
        self.charts_tree.heading("type", text="类型")
        self.charts_tree.heading("page", text="页码")
        self.charts_tree.heading("details", text="详细信息")
        
        # 设置列宽
        self.charts_tree.column("id", width=30)
        self.charts_tree.column("type", width=60)
        self.charts_tree.column("page", width=60)
        self.charts_tree.column("details", width=300)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(charts_list_frame, orient=tk.VERTICAL, command=self.charts_tree.yview)
        self.charts_tree.configure(yscrollcommand=scrollbar.set)
        
        # 放置组件
        self.charts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_metadata_content(self):
        """创建元数据内容区"""
        # 元数据显示
        metadata_frame = ttk.Frame(self.metadata_frame)
        metadata_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        
        # 创建表格显示元数据
        self.metadata_text = ScrolledText(metadata_frame, wrap=tk.WORD, width=40, height=10)
        self.metadata_text.pack(fill=tk.BOTH, expand=True)
        self.metadata_text.config(state=tk.DISABLED)
    
    def import_pdf(self):
        """导入PDF文件"""
        file_path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        # 更新状态
        self.status_bar.config(text=f"正在处理: {os.path.basename(file_path)}...")
        self.update_idletasks()
        
        # 在后台线程中处理PDF
        threading.Thread(target=self.process_pdf, args=(file_path,), daemon=True).start()
    
    def process_pdf(self, file_path):
        """处理PDF文件"""
        try:
            # 提取知识
            knowledge = self.extractor.extract_from_pdf(file_path)
            
            if "error" in knowledge and knowledge["error"]:
                self.show_error(f"处理PDF时出错: {knowledge['error']}")
                return
            
            # 保存结果
            filename = os.path.basename(file_path)
            base_name = os.path.splitext(filename)[0]
            
            # 确保知识库目录存在
            os.makedirs("knowledge_base", exist_ok=True)
            
            # 保存知识到JSON
            output_path = os.path.join("knowledge_base", f"{base_name}_knowledge.json")
            self.extractor.save_knowledge_to_json(knowledge, output_path)
            
            # 更新知识库
            self.knowledge_base[base_name] = {
                "path": file_path,
                "knowledge_path": output_path,
                "data": knowledge,
                "import_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            # 保存知识库索引
            self.save_knowledge_base_index()
            
            # 更新UI
            self.update_document_list()
            
            # 选择新导入的文档
            for item in self.doc_tree.get_children():
                if self.doc_tree.item(item, "values")[0] == base_name:
                    self.doc_tree.selection_set(item)
                    self.doc_tree.see(item)
                    self.on_document_select(None)
                    break
            
            # 更新状态
            self.status_bar.config(text=f"已成功导入: {filename}")
            
        except Exception as e:
            self.show_error(f"处理PDF时出错: {str(e)}")
            self.status_bar.config(text="导入失败")
    
    def update_document_list(self):
        """更新文档列表"""
        # 清空列表
        for item in self.doc_tree.get_children():
            self.doc_tree.delete(item)
        
        # 添加文档
        for name, info in self.knowledge_base.items():
            pages = info["data"].get("pages_count", 0)
            date = info.get("import_date", "未知")
            self.doc_tree.insert("", tk.END, values=(name, pages, date))
    
    def on_document_select(self, event):
        """文档选择事件处理"""
        selection = self.doc_tree.selection()
        if not selection:
            return
        
        # 获取选中的文档
        item = selection[0]
        name = self.doc_tree.item(item, "values")[0]
        
        if name in self.knowledge_base:
            # 更新当前文档
            self.current_pdf = name
            
            # 更新标题
            self.content_title.config(text=f"知识内容: {name}")
            
            # 更新知识点
            self.update_knowledge_points()
            
            # 更新概念
            self.update_concepts()
            
            # 更新图表
            self.update_charts()
            
            # 更新元数据
            self.update_metadata()
            
            # 切换到知识点选项卡
            self.notebook.select(0)
    
    def update_knowledge_points(self):
        """更新知识点列表"""
        # 清空列表
        for item in self.knowledge_tree.get_children():
            self.knowledge_tree.delete(item)
        
        if not self.current_pdf:
            return
        
        # 获取知识点
        knowledge_points = self.knowledge_base[self.current_pdf]["data"].get("knowledge_points", [])
        
        # 过滤知识点
        filter_type = self.filter_var.get()
        if filter_type != "全部":
            knowledge_points = [kp for kp in knowledge_points if kp["type"] == filter_type]
        
        # 添加知识点
        for i, kp in enumerate(knowledge_points):
            content = kp["content"]
            # 截断长内容
            if len(content) > 100:
                content = content[:97] + "..."
            
            self.knowledge_tree.insert("", tk.END, values=(
                i+1, 
                kp["type"], 
                f"{kp['importance']:.2f}" if "importance" in kp else "N/A", 
                content
            ))
    
    def update_concepts(self):
        """更新概念列表"""
        # 清空列表
        for item in self.concepts_tree.get_children():
            self.concepts_tree.delete(item)
        
        if not self.current_pdf:
            return
        
        # 获取概念
        concepts = self.knowledge_base[self.current_pdf]["data"].get("key_concepts", [])
        
        # 添加概念
        for i, concept in enumerate(concepts):
            self.concepts_tree.insert("", tk.END, values=(
                i+1, 
                concept["term"], 
                concept["frequency"]
            ))
    
    def update_charts(self):
        """更新图表列表"""
        # 清空列表
        for item in self.charts_tree.get_children():
            self.charts_tree.delete(item)
        
        if not self.current_pdf:
            return
        
        # 获取图表
        charts = self.knowledge_base[self.current_pdf]["data"].get("charts_info", [])
        
        # 添加图表
        for i, chart in enumerate(charts):
            chart_type = chart["type"]
            page = chart["page"]
            
            # 详细信息
            if chart_type == "image":
                details = f"尺寸: {chart.get('size', 'N/A')}"
            elif chart_type == "table":
                details = f"行数: {chart.get('rows', 'N/A')}, 列数: {chart.get('columns', 'N/A')}"
            else:
                details = "无详细信息"
            
            self.charts_tree.insert("", tk.END, values=(i+1, chart_type, page, details))
    
    def update_metadata(self):
        """更新元数据"""
        self.metadata_text.config(state=tk.NORMAL)
        self.metadata_text.delete(1.0, tk.END)
        
        if not self.current_pdf:
            self.metadata_text.config(state=tk.DISABLED)
            return
        
        # 获取元数据
        metadata = self.knowledge_base[self.current_pdf]["data"].get("metadata", {})
        
        # 格式化显示
        self.metadata_text.insert(tk.END, "文档信息\n", "heading")
        self.metadata_text.insert(tk.END, "="*50 + "\n\n")
        
        self.metadata_text.insert(tk.END, f"标题: {metadata.get('title', '未知')}\n")
        self.metadata_text.insert(tk.END, f"作者: {metadata.get('author', '未知')}\n")
        self.metadata_text.insert(tk.END, f"主题: {metadata.get('subject', '未知')}\n")
        self.metadata_text.insert(tk.END, f"关键词: {metadata.get('keywords', '未知')}\n")
        self.metadata_text.insert(tk.END, f"页数: {metadata.get('page_count', 0)}\n")
        self.metadata_text.insert(tk.END, f"创建日期: {metadata.get('creation_date', '未知')}\n\n")
        
        # 目录结构
        toc = self.knowledge_base[self.current_pdf]["data"].get("toc", [])
        if toc:
            self.metadata_text.insert(tk.END, "目录结构\n", "heading")
            self.metadata_text.insert(tk.END, "="*50 + "\n\n")
            
            for item in toc:
                indent = "  " * (item["level"] - 1)
                self.metadata_text.insert(tk.END, f"{indent}{item['title']} (第{item['page']}页)\n")
        
        # 文件信息
        self.metadata_text.insert(tk.END, "\n文件信息\n", "heading")
        self.metadata_text.insert(tk.END, "="*50 + "\n\n")
        
        file_path = self.knowledge_base[self.current_pdf]["path"]
        self.metadata_text.insert(tk.END, f"文件路径: {file_path}\n")
        
        # 文件大小
        try:
            size_bytes = os.path.getsize(file_path)
            size_kb = size_bytes / 1024
            size_mb = size_kb / 1024
            
            if size_mb >= 1:
                size_str = f"{size_mb:.2f} MB"
            else:
                size_str = f"{size_kb:.2f} KB"
                
            self.metadata_text.insert(tk.END, f"文件大小: {size_str}\n")
        except:
            self.metadata_text.insert(tk.END, "文件大小: 未知\n")
        
        # 导入日期
        import_date = self.knowledge_base[self.current_pdf].get("import_date", "未知")
        self.metadata_text.insert(tk.END, f"导入日期: {import_date}\n")
        
        # 设置标签样式
        self.metadata_text.tag_configure("heading", font=("Arial", 12, "bold"))
        
        self.metadata_text.config(state=tk.DISABLED)
    
    def filter_knowledge(self):
        """根据类型过滤知识点"""
        self.update_knowledge_points()
    
    def show_knowledge_detail(self, event):
        """显示知识点详情"""
        selection = self.knowledge_tree.selection()
        if not selection:
            return
        
        # 获取选中的知识点
        item = selection[0]
        item_id = int(self.knowledge_tree.item(item, "values")[0]) - 1
        
        if not self.current_pdf:
            return
        
        # 获取知识点
        knowledge_points = self.knowledge_base[self.current_pdf]["data"].get("knowledge_points", [])
        
        # 过滤知识点
        filter_type = self.filter_var.get()
        if filter_type != "全部":
            knowledge_points = [kp for kp in knowledge_points if kp["type"] == filter_type]
        
        if item_id < 0 or item_id >= len(knowledge_points):
            return
        
        # 获取知识点详情
        knowledge_point = knowledge_points[item_id]
        
        # 创建详情窗口
        detail_window = tk.Toplevel(self)
        detail_window.title(f"知识点详情 - {knowledge_point['type']}")
        detail_window.geometry("600x400")
        detail_window.minsize(400, 300)
        
        # 设置模态
        detail_window.transient(self)
        detail_window.grab_set()
        
        # 创建内容
        frame = ttk.Frame(detail_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(frame, text=f"知识点详情 - {knowledge_point['type']}", 
                              font=("Arial", 14, "bold"))
        title_label.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        # 内容
        content_frame = ttk.Frame(frame)
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        content_text = ScrolledText(content_frame, wrap=tk.WORD)
        content_text.pack(fill=tk.BOTH, expand=True)
        content_text.insert(tk.END, knowledge_point["content"])
        content_text.config(state=tk.DISABLED)
        
        # 信息
        info_frame = ttk.Frame(frame)
        info_frame.pack(side=tk.TOP, fill=tk.X, pady=(10, 0))
        
        type_label = ttk.Label(info_frame, text=f"类型: {knowledge_point['type']}")
        type_label.pack(side=tk.LEFT, padx=5)
        
        importance_label = ttk.Label(info_frame, 
                                   text=f"重要性: {knowledge_point['importance']:.2f}" 
                                   if "importance" in knowledge_point else "重要性: N/A")
        importance_label.pack(side=tk.LEFT, padx=5)
        
        # 按钮
        button_frame = ttk.Frame(frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        close_button = ttk.Button(button_frame, text="关闭", 
                                command=detail_window.destroy)
        close_button.pack(side=tk.RIGHT)
    
    def search_knowledge(self):
        """搜索知识库"""
        query = self.search_var.get().strip()
        if not query:
            return
        
        # 创建搜索结果窗口
        search_window = tk.Toplevel(self)
        search_window.title(f"搜索结果: {query}")
        search_window.geometry("800x600")
        search_window.minsize(600, 400)
        
        # 设置模态
        search_window.transient(self)
        search_window.grab_set()
        
        # 创建内容
        frame = ttk.Frame(search_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(frame, text=f"搜索结果: {query}", 
                              font=("Arial", 14, "bold"))
        title_label.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        # 结果列表
        result_frame = ttk.Frame(frame)
        result_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # 创建结果列表
        columns = ("doc", "type", "content")
        result_tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        
        # 定义列
        result_tree.heading("doc", text="文档")
        result_tree.heading("type", text="类型")
        result_tree.heading("content", text="内容")
        
        # 设置列宽
        result_tree.column("doc", width=100)
        result_tree.column("type", width=60)
        result_tree.column("content", width=600)
        
        # 添加滚动条
        scrollbar_y = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=result_tree.yview)
        scrollbar_x = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=result_tree.xview)
        result_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # 放置组件
        result_tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 搜索结果
        results = []
        
        # 搜索知识点
        for doc_name, doc_info in self.knowledge_base.items():
            # 搜索知识点
            for kp in doc_info["data"].get("knowledge_points", []):
                if re.search(query, kp["content"], re.IGNORECASE):
                    results.append({
                        "doc": doc_name,
                        "type": kp["type"],
                        "content": kp["content"][:100] + "..." if len(kp["content"]) > 100 else kp["content"],
                        "full_content": kp["content"]
                    })
            
            # 搜索概念
            for concept in doc_info["data"].get("key_concepts", []):
                if re.search(query, concept["term"], re.IGNORECASE):
                    results.append({
                        "doc": doc_name,
                        "type": "概念",
                        "content": f"概念: {concept['term']} (出现频率: {concept['frequency']})",
                        "full_content": f"概念: {concept['term']} (出现频率: {concept['frequency']})"
                    })
        
        # 添加结果
        for result in results:
            result_tree.insert("", tk.END, values=(
                result["doc"],
                result["type"],
                result["content"]
            ))
        
        # 结果统计
        status_label = ttk.Label(frame, text=f"找到 {len(results)} 个匹配结果")
        status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # 绑定双击事件
        def on_result_double_click(event):
            selection = result_tree.selection()
            if not selection:
                return
            
            # 获取选中的结果
            item = selection[0]
            doc_name = result_tree.item(item, "values")[0]
            
            # 选择对应的文档
            for doc_item in self.doc_tree.get_children():
                if self.doc_tree.item(doc_item, "values")[0] == doc_name:
                    self.doc_tree.selection_set(doc_item)
                    self.doc_tree.see(doc_item)
                    self.on_document_select(None)
                    break
            
            # 关闭搜索窗口
            search_window.destroy()
        
        result_tree.bind("<Double-1>", on_result_double_click)
        
        # 按钮
        button_frame = ttk.Frame(frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        close_button = ttk.Button(button_frame, text="关闭", 
                                command=search_window.destroy)
        close_button.pack(side=tk.RIGHT)
    
    def load_knowledge_base(self):
        """加载知识库"""
        # 知识库索引文件
        index_path = "knowledge_base_index.json"
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                
                # 加载知识库
                for name, info in index.items():
                    # 检查知识文件是否存在
                    if os.path.exists(info["knowledge_path"]):
                        try:
                            with open(info["knowledge_path"], 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            # 添加到知识库
                            self.knowledge_base[name] = {
                                "path": info["path"],
                                "knowledge_path": info["knowledge_path"],
                                "data": data,
                                "import_date": info.get("import_date", "未知")
                            }
                        except:
                            pass
                
                # 更新UI
                self.update_document_list()
                
            except Exception as e:
                self.show_error(f"加载知识库索引失败: {str(e)}")
    
    def save_knowledge_base_index(self):
        """保存知识库索引"""
        # 知识库索引文件
        index_path = "knowledge_base_index.json"
        
        # 构建索引
        index = {}
        for name, info in self.knowledge_base.items():
            index[name] = {
                "path": info["path"],
                "knowledge_path": info["knowledge_path"],
                "import_date": info.get("import_date", "未知")
            }
        
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.show_error(f"保存知识库索引失败: {str(e)}")
    
    def refresh_knowledge_base(self):
        """刷新知识库"""
        self.knowledge_base = {}
        self.load_knowledge_base()
        self.status_bar.config(text="知识库已刷新")
    
    def show_error(self, message):
        """显示错误消息"""
        messagebox.showerror("错误", message)


if __name__ == "__main__":
    # 创建应用
    app = ModernUI()
    app.mainloop()