import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import json
import re
import os
from load_json import ComponentGenerator
import copy
import datetime
from tkinter import simpledialog


def generate_symbol_type_string(data, algorithm_name):
    algorithm = data[algorithm_name]
    result_parts = []

    if "inputs" in algorithm:
        for input_item in algorithm["inputs"]:
            if "symbol" in input_item and "type" in input_item and input_item["symbol"]:
                result_parts.append(f"{input_item['type']} {input_item['symbol']}")

                # Process outputs
    if "outputs" in algorithm:
        for output_item in algorithm["outputs"]:
            if "symbol" in output_item and "type" in output_item and output_item["symbol"]:
                result_parts.append(f"{output_item['type']} &{output_item['symbol']}")

                # Join all parts with commas
    result = ", ".join(result_parts)
    return result


def get_algorithm_categories(data, algorithm_name):
        if algorithm_name not in data:
            return f"Error: Algorithm '{algorithm_name}' not found"

        algorithm = data[algorithm_name]
        result = ""

        if "category" in algorithm:
            result += f"{algorithm['category']}"
        else:
            result += "Category: Not specified"

        return result


def get_algorithm_metadata(data, algorithm_name):
    if algorithm_name not in data:
        return f"Error: Algorithm '{algorithm_name}' not found"

    algorithm = data[algorithm_name]
    metadata = {}

    # Extract creator
    if "creator" in algorithm:
        metadata["creator"] = algorithm["creator"]
    else:
        metadata["creator"] = "Not specified"

    # Extract version
    if "version" in algorithm:
        metadata["version"] = algorithm["version"]
    else:
        metadata["version"] = "Not specified"

    # Extract version
    if "description" in algorithm:
        metadata["description"] = algorithm["description"]
    else:
        metadata["description"] = "Not specified"

    if "new_algo_name" in algorithm:
        metadata["new_algo_name"] = algorithm["new_algo_name"]
    else:
        metadata["new_algo_name"] = "Not specified"
    if "english_name" in algorithm:
        metadata["english_name"] = algorithm["english_name"]
    else:
        metadata["english_name"] = "Not specified"

    return metadata


class AlgorithmIntegrationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("无人集群装备算法模型集成接入工具-算法模型集成设计")
        self.root.geometry("1400x800")
        # 应用蓝色主题
        self.style = ttk.Style()
        self.style.theme_use('clam')  # 使用clam主题作为基础
        self.category_name = None
        # 定义颜色方案
        self.bg_color = "#E6F2FF"  # 浅蓝背景
        self.frame_color = "#F0F7FF"  # 更浅的蓝灰色
        self.button_color = "#4A90E2"  # 蓝色按钮
        self.text_color = "#333333"  # 深灰色文本
        # 在其他变量初始化的地方添加
        self.version_var = None
        # 应用蓝色主题
        self.style = ttk.Style()
        self.style.theme_use('clam')  # 使用clam主题作为基础

        # 配置样式
        self.style.configure("TFrame", background=self.frame_color)
        self.style.configure("CustomFrame.TFrame", background=self.frame_color, bordercolor=self.frame_color)
        self.style.configure("TLabel", background=self.frame_color, foreground=self.text_color)

        # 按钮样式
        self.style.configure("TButton", background=self.button_color, foreground="white", font=('Arial', 10, 'bold'), padding=5)
        self.style.map("TButton", background=[('active', '#357ABD'), ('pressed', '#2C6AB0')])

        # 树形菜单样式
        self.style.configure("Treeview", background="white", foreground=self.text_color, rowheight=30, fieldbackground=self.frame_color)
        self.style.configure("Treeview.Heading", background=self.button_color, foreground="white", font=('Arial', 10, 'bold'))

        # 设置背景
        self.root.configure(background=self.bg_color)

        self.is_running = False
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 当前模式和选中的算法
        self.current_mode = None
        self.current_algorithm = None

        # 跟踪当前选择的算法 (无论从树形菜单还是表格选择的)
        self.selected_algorithm = None

        self.operation_class = None
        # 加载算法数据
        self.load_algorithm_data()

        # 创建左右面板
        self.create_left_menu()
        self.create_content_area()

        # 初始化时清空描述区域
        self.clear_detail_area()
        self.add_input_button = None

    def open_add_generator(self):
        # 获取当前选择的项目
        selected_items = self.tree.selection()
        selected_item = selected_items[0]
        selected_text = self.tree.item(selected_item)['text']
        parent_item = self.tree.parent(selected_item)
        category = selected_text
        try:
            # 加载当前的算法数据
            with open("algorithm_data.json", "r", encoding="utf-8") as file:
                all_algorithms = json.load(file)

                # 如果选择的是具体算法（有父节点）
            if parent_item:
                # 复制现有算法
                original_algo_name = selected_text
                algo_data = all_algorithms.get(original_algo_name, {})

                # 生成新的算法名称（副本）
                new_algo_name = original_algo_name
                counter = 1
                while new_algo_name in all_algorithms:
                    new_algo_name = f"{original_algo_name}-副本{counter}"
                    counter += 1

                    # 深拷贝算法数据并更新名称相关信息
                new_algo_data = copy.deepcopy(algo_data)
                new_algo_data['create_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_algo_data['maintainer'] = os.getlogin()  # 获取当前系统用户名
                new_algo_data['version'] = "1.0"  # 重置版本

                # 添加到算法数据中
                all_algorithms[new_algo_name] = new_algo_data

                # 如果选择的是算法分类（没有父节点）
            else:
                category = selected_text
                # 创建空模板算法
                new_algo_name = f"新算法-{category}"
                counter = 1
                while new_algo_name in all_algorithms:
                    new_algo_name = f"新算法-{category}-{counter}"
                    counter += 1

                new_algo_data = {
                    "name": new_algo_name,
                    "category": category,
                    "version": "1.0",
                    "creator": os.getlogin(),
                    "create_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "description": "新创建的算法模板",
                    "inputs": [],
                    "outputs": [],
                    "config": {},
                    "dependencies": [],
                    "performance": {},
                    "implementation": {},
                    "environment": {},
                    "limitations": [],
                    "references": [],
                    "examples": []
                }

                all_algorithms[new_algo_name] = new_algo_data

                # 保存更新后的算法数据
            with open("algorithm_data.json", "w", encoding="utf-8") as file:
                json.dump(all_algorithms, file, ensure_ascii=False, indent=4)

                # 重新加载树形菜单
            self.load_algorithm_data()
            self.populate_tree()

            # 可选：自动选中新创建的算法
            for category_node in self.tree.get_children():
                if self.tree.item(category_node)['text'] == category:
                    for algo_node in self.tree.get_children(category_node):
                        if self.tree.item(algo_node)['text'] == new_algo_name:
                            self.tree.selection_set(algo_node)
                            self.tree.focus(algo_node)
                            break

            messagebox.showinfo("提示", f"已成功创建 {new_algo_name}")

        except Exception as e:
            messagebox.showerror("错误", f"创建算法时发生错误: {str(e)}")

    def generate_algorithm_code(self):
        """生成算法代码"""
        if not self.selected_algorithm:
            messagebox.showinfo("提示", "请先选择一个算法")
            return

        base_param = get_algorithm_metadata(self.algorithm_data, self.selected_algorithm)
        category = get_algorithm_categories(self.algorithm_data, self.selected_algorithm)

        # 获取英文名称并处理：移除空格和连字符
        raw_english_name = base_param.get('english_name', 'DefaultAlgorithm')
        english_name = raw_english_name.replace(' ', '').replace('-', '')

        # 创建带版本号的名称
        if category == '内置服务':
            versioned_name = 'AlgSrv_' + f"{english_name}"
        elif category == '外置信息代理':
            versioned_name = 'AlgInfoProxy_' + f"{english_name}"
        elif category == '外置服务代理':
            versioned_name = 'AlgSrvProxy_' + f"{english_name}"
        # 确定算法的类别和模版文件路径
        algo_data = self.algorithm_data.get(self.selected_algorithm, {})
        category = algo_data.get("category", "未分类")
        # 构建模版文件路径
        template_path = os.path.join("template", category, f"{self.selected_algorithm}.py")

        # 检查模版文件是否存在
        if not os.path.exists(template_path):
            messagebox.showerror("错误", f"未找到算法 {self.selected_algorithm, template_path} 的模版文件")
            return

            # 读取模版文件内容
        with open(template_path, 'r', encoding='utf-8') as file:
            template_code = file.read()

            # 准备输入参数
        input_params = algo_data.get("inputs", [])

        # 生成输入参数声明
        input_param_declarations = []
        for param in input_params:
            param_name = param.get("name", "")
            param_type = param.get("type", "Any")
            input_param_declarations.append(f"{param_name}: {param_type}")

            # 生成输出参数
        output_params = algo_data.get("outputs", [])
        output_param_declarations = []
        for param in output_params:
            param_name = param.get("name", "")
            param_type = param.get("type", "Any")
            output_param_declarations.append(f"{param_name}: {param_type}")

            # 构建函数签名
        function_signature = f"def {versioned_name}({', '.join(input_param_declarations)}):"

        # 替换模版中的函数签名
        generated_code = re.sub(r'def\s+\w+\s*\(.*?\)\s*->\s*dict:', function_signature, template_code)

        generated_code = re.sub(r'TemplateClass', f'{versioned_name}', generated_code)

        # 替换所有扩展卡尔曼滤波算法 函数名为 versioned_name
        generated_code = re.sub(r'TemplateFunc\s*\(', f'{versioned_name}(', generated_code)

        # 替换创建类实例的代码
        generated_code = re.sub(r'ekf\s*=\s*TemplateFunc', f'ekf = {versioned_name}', generated_code)

        generated_code = re.sub(r'\${SPECIAL_PARAM}', str(algo_data), generated_code)

        # 创建生成的代码文件夹
        generated_dir = os.path.join("生成框架代码", category, self.selected_algorithm)
        os.makedirs(generated_dir, exist_ok=True)

        # 生成目标文件路径
        generated_file_path = os.path.join(generated_dir, f'{versioned_name}_generated.py')

        # 写入生成的代码
        with open(generated_file_path, 'w', encoding='utf-8') as file:
            file.write(generated_code)

            # 弹出成功提示，并提供文件路径
        message = (
            f"算法代码生成成功！\n"
            f"文件路径: {generated_file_path}\n\n"
            f"算法名称: {versioned_name}\n"
            f"输入参数: {', '.join(input_param_declarations)}\n"
            f"输出参数: {', '.join(output_param_declarations)}"
        )
        messagebox.showinfo("生成成功", message)

    def handle_generate_button(self):
        """根据算法类型决定调用哪个生成方法"""
        if not self.selected_algorithm:
            messagebox.showinfo("提示", "请先选择一个算法")
            return
        category = get_algorithm_categories(self.algorithm_data, self.selected_algorithm)
        if category == '内置组件':
            self.generate_component()
        else:
            self.generate_algorithm_code()
        # 如果你有明确的方式判断某个算法是否需要内置组件，可以在这里添加判断条件
        # 这里假设所有算法都需要内置组件，也可以给用户提供选择

    def generate_component(self):
        """只生成内置组件，不生成Python文件"""
        if not self.selected_algorithm:
            messagebox.showinfo("提示", "请先选择一个算法")
            return

        # 调用ComponentGenerator生成内置组件
        component_generator = ComponentGenerator(self.selected_algorithm)
        initial_type = generate_symbol_type_string(self.algorithm_data, self.selected_algorithm)
        meta_data = get_algorithm_metadata(self.algorithm_data, self.selected_algorithm)
        component_generator.generate_code(initial_type, meta_data)
        messagebox.showinfo("成功", f"算法 '{self.selected_algorithm}' 的内置组件生成成功！")

    def load_algorithm_data(self):
        """从JSON文件加载算法数据"""
        try:
            # 尝试从文件加载数据
            if os.path.exists("algorithm_data.json"):
                with open("algorithm_data.json", "r", encoding="utf-8") as file:
                    self.algorithm_data = json.load(file)

                    # 从加载的数据中提取算法类别
                self.algorithm_categories = {}
                for algo_name, algo_info in self.algorithm_data.items():
                    category = algo_info.get("category", "未分类")
                    if category not in self.algorithm_categories:
                        self.algorithm_categories[category] = []
                    self.algorithm_categories[category].append(algo_name)
            else:
                # 如果文件不存在，初始化为空数据
                self.algorithm_data = {}
                self.algorithm_categories = {}
                messagebox.showwarning("警告", "找不到算法数据文件 (algorithm_data.json)，将使用空数据初始化。")
        except Exception as e:
            # 出错时显示错误并初始化空数据
            messagebox.showerror("错误", f"加载算法数据时出错: {str(e)}")
            self.algorithm_data = {}
            self.algorithm_categories = {}

    def delete_selected_algorithm(self):
        """删除选中的算法"""
        # 获取当前选中的算法
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的算法")
            return

        selected_item = selected_items[0]
        selected_text = self.tree.item(selected_item)['text']
        parent_item = self.tree.parent(selected_item)

        # 检查是否选择了具体算法（有父节点）
        if not parent_item:
            messagebox.showwarning("警告", "请选择具体的算法，而非算法分类")
            return

        # 确认删除
        confirm = messagebox.askyesno("确认删除", f"确定要删除算法 '{selected_text}' 吗？\n此操作不可撤销。")
        if not confirm:
            return

        try:
            # 更新算法数据JSON文件
            with open("algorithm_data.json", "r", encoding="utf-8") as file:
                all_algorithms = json.load(file)

            # 删除算法
            if selected_text in all_algorithms:
                del all_algorithms[selected_text]

                # 保存更新后的算法数据
                with open("algorithm_data.json", "w", encoding="utf-8") as file:
                    json.dump(all_algorithms, file, ensure_ascii=False, indent=4)

                # 重新加载算法数据
                self.load_algorithm_data()

                # 重新填充树形菜单
                self.populate_tree()

                # 清空详细信息区域
                self.clear_detail_area()

                messagebox.showinfo("成功", f"算法 '{selected_text}' 已删除")

            else:
                messagebox.showwarning("警告", f"未找到算法 '{selected_text}' 的信息")

        except Exception as e:
            messagebox.showerror("错误", f"删除算法时发生错误: {str(e)}")

    def create_left_menu(self):
        """创建左侧菜单"""
        left_frame = ttk.Frame(self.main_frame, style="CustomFrame.TFrame", width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        header_frame = ttk.Frame(left_frame, style="CustomFrame.TFrame")
        header_frame.pack(anchor=tk.W, fill=tk.X, pady=5)

        add_button = ttk.Button(header_frame, text="添加", command=self.open_add_generator)
        delete_button = ttk.Button(header_frame, text="删除", command=self.delete_selected_algorithm)
        delete_button.pack(side=tk.RIGHT, padx=5)
        add_button.pack(side=tk.RIGHT, padx=5)

        search_frame = ttk.Frame(left_frame, style="CustomFrame.TFrame")
        search_frame.pack(fill=tk.X, pady=5)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search)

        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=('Arial', 10), background="white")
        search_entry.pack(fill=tk.X)

        tree_frame = ttk.Frame(left_frame, style="CustomFrame.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, selectmode='browse', show='tree')
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.populate_tree()
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

    def populate_tree(self, search_term=None):
        """填充树形菜单，支持搜索过滤"""
        # 清空现有项目
        for item in self.tree.get_children():
            self.tree.delete(item)

            # 如果没有搜索词，显示全部类别和算法
        if not search_term:
            for category, algorithms in self.algorithm_categories.items():
                category_node = self.tree.insert("", "end", text=category)
                for algo in algorithms:
                    self.tree.insert(category_node, "end", text=algo)
            return

            # 搜索处理（不区分大小写）
        search_term = search_term.lower()
        filtered_data = {}

        # 筛选符合条件的算法（算法名称或创建人包含搜索词）
        for category, algorithms in self.algorithm_categories.items():
            filtered_algos = []
            for algo_name in algorithms:
                algo_data = self.algorithm_data.get(algo_name, {})
                creator = algo_data.get("creator", "").lower()

                # 检查算法名称或创建人是否包含搜索词
                if search_term in algo_name.lower() or search_term in creator:
                    filtered_algos.append(algo_name)

                    # 如果该类别下有符合条件的算法，添加到结果中
            if filtered_algos:
                filtered_data[category] = filtered_algos

                # 显示筛选后的结果
        for category, algorithms in filtered_data.items():
            category_node = self.tree.insert("", "end", text=category)
            for algo in algorithms:
                self.tree.insert(category_node, "end", text=algo)

    def on_search(self, *args):
        """当搜索框文本变化时触发"""
        search_term = self.search_var.get().strip()
        self.populate_tree(search_term)
        self.update_table_search(search_term)

    def update_table_search(self, search_term):
        """根据搜索条件更新表格显示"""
        # 清空表格
        for item in self.table.get_children():
            self.table.delete(item)

            # 如果没有搜索词，不显示任何算法（保持现有逻辑）
        if not search_term:
            return

            # 搜索处理（不区分大小写）
        search_term = search_term.lower()

        # 筛选并显示匹配的算法
        for algo_name, algo_data in self.algorithm_data.items():
            creator = algo_data.get("creator", "").lower()

            # 检查算法名称或创建人是否包含搜索词
            if search_term in algo_name.lower() or search_term in creator:
                # 向表格添加算法基本信息
                self.table.insert("", "end", values=(
                    algo_name,
                    algo_data.get("version", "1.0"),
                    algo_data.get("creator", "未知"),
                    algo_data.get("create_time", ""),
                    algo_data.get("maintainer", "未知"),
                    algo_data.get("update_time", "")
                ))

    def save_algorithm_name(self):
        """保存算法名称和英文名称"""
        if not self.current_algorithm:
            messagebox.showwarning("警告", "请先选择一个算法")
            return

        try:
            new_algorithm_name = self.algorithm_name_var.get().strip()
            new_algorithm_english_name = self.algorithm_english_name_var.get().strip()
            new_developer = self.developer_var.get().strip()
            new_version = self.version_var.get().strip()  # 新增：获取版本信息
            new_algo_name = self.new_algo_var.get().strip()
            if not new_algorithm_name:
                messagebox.showwarning("警告", "算法名称不能为空")
                return

                # 加载现有算法数据
            with open("algorithm_data.json", "r", encoding="utf-8") as file:
                all_algorithms = json.load(file)

                # 检查新名称是否已存在
            if new_algorithm_name in all_algorithms and new_algorithm_name != self.current_algorithm:
                messagebox.showwarning("警告", f"算法名称 {new_algorithm_name} 已存在")
                return

                # 更新算法名称
            if self.current_algorithm in all_algorithms:
                # 深拷贝算法数据
                algorithm_data = all_algorithms[self.current_algorithm]
                del all_algorithms[self.current_algorithm]

                # 更新算法名称和相关信息
                algorithm_data['name'] = new_algorithm_name
                algorithm_data['english_name'] = new_algorithm_english_name
                algorithm_data['maintainer'] = new_developer
                algorithm_data['version'] = new_version  # 新增：更新版本信息
                algorithm_data['update_time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                algorithm_data['new_algo_name'] = new_algo_name

                # 使用新名称保存算法数据
                all_algorithms[new_algorithm_name] = algorithm_data

                # 保存到JSON文件
                with open("algorithm_data.json", "w", encoding="utf-8") as file:
                    json.dump(all_algorithms, file, ensure_ascii=False, indent=4)

                    # 更新内存中的算法数据
                self.algorithm_data = all_algorithms
                self.current_algorithm = new_algorithm_name
                self.selected_algorithm = new_algorithm_name

                # 重新加载树形菜单
                self.load_algorithm_data()
                self.populate_tree()

                # 找到并选中新名称的算法节点
                for category_node in self.tree.get_children():
                    for algo_node in self.tree.get_children(category_node):
                        if self.tree.item(algo_node)['text'] == new_algorithm_name:
                            self.tree.selection_set(algo_node)
                            self.tree.focus(algo_node)
                            break

                messagebox.showinfo("成功", f"算法信息已更新")

        except Exception as e:
            messagebox.showerror("错误", f"保存算法信息时发生错误: {str(e)}")

    def create_content_area(self):
        """创建右侧内容区域"""
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 按钮区域
        button_area = ttk.Frame(content_frame)
        button_area.pack(fill=tk.X, pady=5)

        # 仅添加"生成"按钮
        self.run_button = ttk.Button(button_area, text="生成", command=self.handle_generate_button, width=10)

        self.run_button.pack(side=tk.LEFT, padx=5)

        # 创建底部信息区域
        bottom_frame = ttk.Frame(content_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        # 左侧区域（算法名称 + 算法描述 + 算法详细配置）
        left_frame = ttk.Frame(bottom_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # 算法名称编辑区域
        name_frame = ttk.LabelFrame(left_frame, text="算法名称")
        name_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        # 中文名称
        chinese_name_label = ttk.Label(name_frame, text="中文名称:")
        chinese_name_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')

        # 创建算法名称变量和输入框
        self.algorithm_name_var = tk.StringVar()
        self.algorithm_name_entry = ttk.Entry(name_frame, textvariable=self.algorithm_name_var, width=50)
        self.algorithm_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        # 英文名称
        english_name_label = ttk.Label(name_frame, text="英文名称:")
        english_name_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')

        # 创建算法英文名称变量和输入框
        self.algorithm_english_name_var = tk.StringVar()
        self.algorithm_english_name_entry = ttk.Entry(name_frame, textvariable=self.algorithm_english_name_var, width=50)
        self.algorithm_english_name_entry.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        # 创建者
        developer_label = ttk.Label(name_frame, text="创建者:")
        developer_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')

        # 创建创建者变量和输入框
        self.developer_var = tk.StringVar()
        self.developer_entry = ttk.Entry(name_frame, textvariable=self.developer_var, width=50)
        self.developer_entry.grid(row=2, column=1, padx=5, pady=5, sticky='ew')

        # 版本
        version_label = ttk.Label(name_frame, text="版本:")
        version_label.grid(row=3, column=0, padx=5, pady=5, sticky='w')

        # 创建版本变量和输入框
        self.version_var = tk.StringVar()
        self.version_entry = ttk.Entry(name_frame, textvariable=self.version_var, width=50)
        self.version_entry.grid(row=3, column=1, padx=5, pady=5, sticky='ew')

        # 新函数
        new_algo_label = ttk.Label(name_frame, text="接口函数名:")
        new_algo_label.grid(row=4, column=0, padx=5, pady=5, sticky='w')

        # 创建新函数输入框
        self.new_algo_var = tk.StringVar()
        self.new_algo_entry = ttk.Entry(name_frame, textvariable=self.new_algo_var, width=50)
        self.new_algo_entry.grid(row=4, column=1, padx=5, pady=5, sticky='ew')

        # 保存名称按钮位置需要修改到第4行
        name_save_btn = ttk.Button(name_frame, text="保存基本信息", command=self.save_algorithm_name)
        name_save_btn.grid(row=5, column=1, padx=5, pady=5, sticky='e')

        name_frame.grid_columnconfigure(1, weight=1)
        # 算法描述
        desc_frame = ttk.LabelFrame(left_frame, text="算法描述")
        desc_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        self.description_text = tk.Text(desc_frame, height=10, width=40)
        self.description_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 描述区域的保存按钮
        desc_inner_frame = ttk.Frame(desc_frame)
        desc_inner_frame.pack(fill=tk.BOTH, expand=True)
        desc_save_btn = ttk.Button(desc_inner_frame, text="保存描述", command=self.save_algorithm_description)
        desc_save_btn.pack(side=tk.BOTTOM, pady=5)

        # 右侧区域（输入/输出接口）
        right_frame = ttk.Frame(bottom_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # 输入接口
        input_frame = ttk.LabelFrame(right_frame, text="")
        input_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 0))

        # 创建一个子框架用于标签和按钮
        input_header_frame = ttk.Frame(input_frame)
        input_header_frame.pack(fill=tk.X)

        # 输入接口标签
        input_label = ttk.Label(input_header_frame, text="输入参数列表", font=('Arial', 10, 'bold'))
        input_label.pack(side=tk.LEFT, padx=(10, 5))

        # 输入接口按钮区域
        input_button_frame = ttk.Frame(input_header_frame)
        input_button_frame.pack(side=tk.RIGHT)

        add_input_button = ttk.Button(input_button_frame, text="添加", command=lambda: self.add_parameter(is_input=True), width=5)
        add_input_button.pack(side=tk.LEFT, padx=2)

        delete_input_button = ttk.Button(input_button_frame, text="删除", command=lambda: self.delete_parameter(is_input=True), width=5)
        delete_input_button.pack(side=tk.LEFT, padx=2)
        # 创建输入接口表格
        input_columns = ("参数名称", "符号", "类型", "量纲", "描述")
        self.input_table = ttk.Treeview(input_frame, columns=input_columns, show="headings", height=10)

        for col in input_columns:
            self.input_table.heading(col, text=col)
            self.input_table.column(col, width=100, anchor="center")

        input_scrollbar = ttk.Scrollbar(input_frame, orient="vertical", command=self.input_table.yview)
        self.input_table.configure(yscrollcommand=input_scrollbar.set)

        self.input_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        input_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定双击事件
        self.input_table.bind('<Double-1>', self.on_double_click)

        # 输出接口同样处理
        output_frame = ttk.LabelFrame(right_frame, text="")
        output_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, pady=(0, 0))

        # 创建一个子框架用于标签和按钮
        output_header_frame = ttk.Frame(output_frame)
        output_header_frame.pack(fill=tk.X)

        # 输出接口标签
        output_label = ttk.Label(output_header_frame, text="输出参数列表", font=('Arial', 10, 'bold'))
        output_label.pack(side=tk.LEFT, padx=(10, 5))

        # 输出接口按钮区域
        output_button_frame = ttk.Frame(output_header_frame)
        output_button_frame.pack(side=tk.RIGHT)

        add_output_button = ttk.Button(output_button_frame, text="添加", command=lambda: self.add_parameter(is_input=False), width=5)
        add_output_button.pack(side=tk.LEFT, padx=2)

        delete_output_button = ttk.Button(output_button_frame, text="删除", command=lambda: self.delete_parameter(is_input=False), width=5)
        delete_output_button.pack(side=tk.LEFT, padx=2)

        # 输出接口表格
        output_columns = ("参数名称", "符号", "类型", "量纲", "描述")
        self.output_table = ttk.Treeview(output_frame, columns=output_columns, show="headings", height=10)

        # 设置列标题和宽度
        for col in output_columns:
            self.output_table.heading(col, text=col)
            self.output_table.column(col, width=100, anchor="center")
        # 添加滚动条
        output_scrollbar = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_table.yview)
        self.output_table.configure(yscrollcommand=output_scrollbar.set)

        # 布局
        self.output_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        # 为输入和输出表格添加双击事件
        self.output_table.bind('<Double-1>', self.on_double_click)
        # # 在输入接口区域添加按钮
        # add_input_button = ttk.Button(input_frame, text="添加输入参数", command=lambda: self.edit_parameter_advanced(is_input=True))
        # add_input_button.pack(side=tk.BOTTOM)
        #
        # # 在输出接口区域添加按钮
        # add_output_button = ttk.Button(output_frame, text="添加输出参数", command=lambda: self.edit_parameter_advanced(is_input=False))
        # add_output_button.pack(side=tk.BOTTOM)

    def save_algorithm_description(self):
        """保存算法描述"""
        if not self.current_algorithm:
            messagebox.showwarning("警告", "请先选择一个算法")
            return
        try:
            # 获取描述文本
            new_description = self.description_text.get(1.0, tk.END).strip()
            # 加载现有算法数据
            with open("algorithm_data.json", "r", encoding="utf-8") as file:
                all_algorithms = json.load(file)

                # 更新描述
            if self.current_algorithm in all_algorithms:
                all_algorithms[self.current_algorithm]["description"] = new_description

                # 更新修改时间
                all_algorithms[self.current_algorithm]["update_time"] = datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S")

                # 保存到JSON文件
            with open("algorithm_data.json", "w", encoding="utf-8") as file:
                json.dump(all_algorithms, file, ensure_ascii=False, indent=4)

                # 更新内存中的算法数据
            self.algorithm_data = all_algorithms
            messagebox.showinfo("成功", f"算法 {self.current_algorithm} 的描述已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存描述时发生错误: {str(e)}")

    def save_algorithm_config(self):
        """保存算法配置"""
        if not self.current_algorithm:
            messagebox.showwarning("警告", "请先选择一个算法")
            return
        try:
            # 获取配置文本
            config_text = self.config_text.get(1.0, tk.END).strip()
            # 加载现有算法数据
            with open("algorithm_data.json", "r", encoding="utf-8") as file:
                all_algorithms = json.load(file)
            # 解析配置文本并更新
            if self.current_algorithm in all_algorithms:
                # 更新各个配置区域
                sections = {
                    "【基本信息】": "basic_info",
                    "【配置参数】": "config",
                    "【依赖项】": "dependencies",
                    "【性能指标】": "performance",
                    "【实现细节】": "implementation",
                    "【运行环境】": "environment",
                    "【限制条件】": "limitations",
                    "【参考资料】": "references",
                    "【使用示例】": "examples"
                }
                for section_title, config_key in sections.items():
                    if section_title in config_text:
                        section_content = config_text.split(section_title)[1].split("【")[0].strip()
                        if section_content:
                            if config_key in ["config", "performance", "implementation", "environment"]:
                                # 对于字典类型的配置
                                config_dict = {}
                                for line in section_content.split('\n'):
                                    if '：' in line or ':' in line:
                                        key, value = re.split('：|:', line.strip('•\s'), 1)
                                        config_dict[key.strip()] = value.strip()
                                all_algorithms[self.current_algorithm][config_key] = config_dict
                            elif config_key in ["dependencies", "limitations", "references", "examples"]:
                                # 对于列表类型的配置
                                config_list = [line.strip('•\s') for line in section_content.split('\n') if
                                               line.strip()]
                                all_algorithms[self.current_algorithm][config_key] = config_list

                                # 更新修改时间
                all_algorithms[self.current_algorithm]["update_time"] = datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S")
                # 保存到JSON文件
            with open("algorithm_data.json", "w", encoding="utf-8") as file:
                json.dump(all_algorithms, file, ensure_ascii=False, indent=4)
                # 更新内存中的算法数据
            self.algorithm_data = all_algorithms
            messagebox.showinfo("成功", f"算法 {self.current_algorithm} 的配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置时发生错误: {str(e)}")

    def update_algorithm_json_type(self, row_item, new_type):
        try:
            updated_algorithm_data = copy.deepcopy(self.algorithm_data)

            if not self.current_algorithm:
                messagebox.showwarning("警告", "请先选择一个算法")
                return

            row_values = self.input_table.item(row_item, 'values')
            algo_data = updated_algorithm_data[self.current_algorithm]
            inputs = algo_data.get("inputs", [])

            for param in inputs:
                param["type"] = new_type
                break

            json_path = os.path.join('algorithm_data.json')
            with open(json_path, "w", encoding="utf-8") as file:
                json.dump(updated_algorithm_data, file, ensure_ascii=False, indent=4)

            self.algorithm_data = updated_algorithm_data
            messagebox.showinfo("提示", f"参数 {row_values[0]} 的类型已更新为 {new_type}")

        except Exception as e:
            messagebox.showerror("错误", f"更新JSON文件时发生错误: {str(e)}")

    def update_algorithm_json_name(self, row_item, new_name):
        try:
            updated_algorithm_data = copy.deepcopy(self.algorithm_data)

            if not self.current_algorithm:
                messagebox.showwarning("警告", "请先选择一个算法")
                return

            row_values = self.input_table.item(row_item, 'values')

            algo_data = updated_algorithm_data[self.current_algorithm]
            inputs = algo_data.get("inputs", [])

            for param in inputs:
                param["name"] = new_name
                break

            json_path = os.path.join('algorithm_data.json')
            with open(json_path, "w", encoding="utf-8") as file:
                json.dump(updated_algorithm_data, file, ensure_ascii=False, indent=4)

            self.algorithm_data = updated_algorithm_data
            messagebox.showinfo("提示", f"参数名已从 {row_values[0]} 更新为 {new_name}")

        except Exception as e:
            messagebox.showerror("错误", f"更新JSON文件时发生错误: {str(e)}")

    def update_algorithm_json_symbol(self, row_item, new_symbol):
        try:
            updated_algorithm_data = copy.deepcopy(self.algorithm_data)

            if not self.current_algorithm:
                messagebox.showwarning("警告", "请先选择一个算法")
                return

            row_values = self.input_table.item(row_item, 'values')

            algo_data = updated_algorithm_data[self.current_algorithm]
            inputs = algo_data.get("inputs", [])

            for param in inputs:
                param["symbol"] = new_symbol
                break

            json_path = os.path.join('algorithm_data.json')
            with open(json_path, "w", encoding="utf-8") as file:
                json.dump(updated_algorithm_data, file, ensure_ascii=False, indent=4)

            self.algorithm_data = updated_algorithm_data

            messagebox.showinfo("提示", f"参数 {row_values[0]} 的符号已更新为 {new_symbol}")

        except Exception as e:
            messagebox.showerror("错误", f"更新JSON文件时发生错误: {str(e)}")

    def update_algorithm_json_description(self, row_item, new_description):
        try:
            updated_algorithm_data = copy.deepcopy(self.algorithm_data)

            if not self.current_algorithm:
                messagebox.showwarning("警告", "请先选择一个算法")
                return

            row_values = self.input_table.item(row_item, 'values')

            algo_data = updated_algorithm_data[self.current_algorithm]
            inputs = algo_data.get("inputs", [])

            for param in inputs:
                param["description"] = new_description
                break

            json_path = os.path.join('algorithm_data.json')
            with open(json_path, "w", encoding="utf-8") as file:
                json.dump(updated_algorithm_data, file, ensure_ascii=False, indent=4)

            self.algorithm_data = updated_algorithm_data

            messagebox.showinfo("提示", f"参数 {row_values[0]} 的描述已更新")

        except Exception as e:
            messagebox.showerror("错误", f"更新JSON文件时发生错误: {str(e)}")

    def on_double_click(self, event):
        """处理表格双击编辑事件并更新JSON"""
        # 确定是哪个表格被点击
        if event.widget == self.input_table:
            table = self.input_table
            update_methods = {
                0: self.update_algorithm_json_name,
                1: self.update_algorithm_json_symbol,
                2: self.update_algorithm_json_type,
                3: self.update_algorithm_json_description
            }
        elif event.widget == self.output_table:
            table = self.output_table
            update_methods = {
                0: self.update_algorithm_json_name,
                1: self.update_algorithm_json_symbol,
                2: self.update_algorithm_json_type,
                3: self.update_algorithm_json_description
            }
        else:
            return

        # 获取点击的列和行
        region = table.identify("region", event.x, event.y)
        if region != "cell":
            return

        # 获取点击的单元格
        column = table.identify_column(event.x)
        row = table.identify_row(event.y)

        # 确定列索引
        col_index = int(column[1:]) - 1

        # 处理"类型"列（第三列）
        if col_index == 2:  # 类型列
            # 创建弹出下拉框
            type_combo = ttk.Combobox(table, values=self.PARAMETER_TYPES, state="readonly")

            # 设置当前值
            current_values = list(table.item(row, 'values'))
            current_value = current_values[col_index]
            type_combo.set(current_value)

            # 定位和显示下拉框
            x, y, width, height = table.bbox(row, column)
            type_combo.place(x=x, y=y, width=width, height=height)
            type_combo.focus_set()

            def on_select(event):
                # 更新表格值
                current = type_combo.get()
                current_values[col_index] = current
                table.item(row, values=current_values)

                # 更新JSON数据
                update_methods[col_index](row, type_combo.get())
                type_combo.destroy()

            type_combo.bind('<<ComboboxSelected>>', on_select)
            type_combo.bind('<FocusOut>', lambda e: type_combo.destroy())

        # 处理其他列（参数名、符号、描述）
        elif col_index in [0, 1, 3, 4]:  # 参数名、符号、描述列
            # 创建输入框
            edit_entry = ttk.Entry(table)

            # 获取单元格位置
            x, y, width, height = table.bbox(row, column)
            edit_entry.place(x=x, y=y, width=width, height=height)

            # 获取当前值
            current_values = list(table.item(row, 'values'))
            current_value = current_values[col_index]

            # 设置初始值
            edit_entry.insert(0, current_value)
            edit_entry.focus_set()
            edit_entry.select_range(0, tk.END)

            def on_enter(event):
                # 更新表格值
                current_values[col_index] = edit_entry.get()
                table.item(row, values=current_values)

                # 调用对应的更新方法
                update_methods[col_index](row, edit_entry.get())

                edit_entry.destroy()

            def on_focusout(event):
                # 更新表格值
                current_values[col_index] = edit_entry.get()
                table.item(row, values=current_values)

                # 调用对应的更新方法
                update_methods[col_index](row, edit_entry.get())

                edit_entry.destroy()

            edit_entry.bind('<Return>', on_enter)
            edit_entry.bind('<FocusOut>', on_focusout)

    def clear_detail_area(self):
        """清空详细信息区域"""
        # 清空描述
        self.description_text.config(state=tk.NORMAL)
        self.description_text.delete(1.0, tk.END)
        self.description_text.config(state=tk.DISABLED)

        # 清空输入/输出表格
        for item in self.input_table.get_children():
            self.input_table.delete(item)
        for item in self.output_table.get_children():
            self.output_table.delete(item)

    def on_tree_select(self, event):
        """处理树形菜单选择事件"""
        selected_items = self.tree.selection()
        if not selected_items:
            return

        item_id = selected_items[0]
        item_text = self.tree.item(item_id)['text']
        # 检查是否选择了类别
        if not self.tree.parent(item_id):  # 如果没有父节点，则是类别
            # 获取该类别下的所有算法
            algos_in_category = []
            for algo_id in self.tree.get_children(item_id):
                algo_name = self.tree.item(algo_id)['text']
                algos_in_category.append(algo_name)

            self.clear_detail_area()
            self.current_algorithm = None
            self.current_mode = None
            self.selected_algorithm = None

            # 清空算法名称和英文名称输入框
            self.algorithm_name_var.set('')
            self.algorithm_english_name_var.set('')
        else:  # 选择了算法项
            # 获取算法名称
            algo_name = item_text
            self.selected_algorithm = algo_name
            self.current_algorithm = algo_name

            # 尝试从JSON文件加载算法详细信息
            try:
                with open("algorithm_data.json", "r", encoding="utf-8") as file:
                    all_algorithms = json.load(file)

                    # 检查是否存在该算法
                    if algo_name in all_algorithms:
                        # 更新算法信息
                        self.algorithm_data[algo_name] = all_algorithms[algo_name]

                        # 更新算法名称输入框
                        self.algorithm_name_var.set(algo_name)

                        # 特别处理英文名称，如果没有设置则显示为空
                        english_name = all_algorithms[algo_name].get('english_name', '')
                        self.algorithm_english_name_var.set(english_name)

                        # 更新算法详细信息（默认为只读模式）
                        self.update_algorithm_info(algo_name, self.current_mode == "edit")
                    else:
                        messagebox.showwarning("警告", f"未找到算法 '{algo_name}' 的详细信息")
            except FileNotFoundError:
                messagebox.showerror("错误", "找不到算法数据文件 (algorithm_data.json)")
            except json.JSONDecodeError:
                messagebox.showerror("错误", "算法数据文件格式错误")

    def update_io_tables(self, algo_data):
        """更新输入/输出接口表格，支持编辑"""
        # 定义数据类型列表
        self.PARAMETER_TYPES = ["int", "float", "double", "str", "bool", "unsigned int", "std::vector<int>"]

        # 清空表格
        for item in self.input_table.get_children():
            self.input_table.delete(item)
        for item in self.output_table.get_children():
            self.output_table.delete(item)

            # 添加输入参数
        for param in algo_data.get("inputs", []):
            self.input_table.insert("", "end", values=(
                param.get("name", ""),
                param.get("symbol", ""),
                param.get("type", ""),
                param.get("dimension", ""),  # Add the dimension field
                param.get("description", "")
            ))

            # 添加输出参数
        for param in algo_data.get("outputs", []):
            self.output_table.insert("", "end", values=(
                param.get("name", ""),
                param.get("symbol", ""),
                param.get("type", ""),
                param.get("dimension", ""),  # Add the dimension field
                param.get("description", "")
            ))

            # 为输入和输出表格添加双击编辑事件
        self.input_table.bind("<Double-1>", self.on_double_click)
        self.output_table.bind("<Double-1>", self.on_double_click)

    def update_algorithm_info(self, algo_name, editable=True):
        """更新算法信息"""
        # 获取算法数据
        algo_data = self.algorithm_data.get(algo_name, {})
        if not algo_data:
            messagebox.showinfo("提示", f"没有找到算法 '{algo_name}' 的信息")
            return

        # 更新描述和配置
        state = tk.NORMAL if editable else tk.DISABLED

        # 清空并更新描述
        self.description_text.config(state=tk.NORMAL)
        self.description_text.delete(1.0, tk.END)
        self.description_text.insert(tk.END, algo_data.get("description", ""))
        self.description_text.config(state=state)

        # 更新算法名称、英文名称、创建者和版本信息
        self.algorithm_name_var.set(algo_name)
        self.algorithm_english_name_var.set(algo_data.get('english_name', ''))
        self.developer_var.set(algo_data.get('maintainer', ''))
        self.new_algo_var.set(algo_data.get('new_algo_name', ''))
        self.version_var.set(algo_data.get('version', '1.0'))  # 新增：显示版本信息

        # 基本信息部分
        # 更新配置 - 大幅扩展显示的信息内容
        config_text = f"算法名称: {algo_name}\n"
        config_text += f"英文名称: {algo_data.get('english_name', '未设置')}\n"  # 显示英文名称
        config_text += f"版本: {algo_data.get('version', '1.0')}\n"
        config_text += f"类别: {algo_data.get('category', '未分类')}\n"
        config_text += f"创建人: {algo_data.get('creator', '未知')}\n"

        # 描述和配置默认为可编辑状态
        self.description_text.config(state=tk.NORMAL)
        # 更新输入/输出表格
        self.update_io_tables(algo_data)

    def add_parameter(self, is_input=True):
        """通用的添加参数方法"""
        if not self.current_algorithm:
            messagebox.showwarning("警告", "请先选择一个算法")
            return

        try:
            # 使用对话框获取新参数信息
            param_name = simpledialog.askstring("添加参数", "请输入参数名称:")
            if not param_name:
                return

            # 创建默认参数模板
            new_param = {"name": param_name, "symbol": "", "type": "Any", "description": ""}

            # 更新算法数据JSON
            with open("algorithm_data.json", "r", encoding="utf-8") as file:
                all_algorithms = json.load(file)

            # 添加新参数到输入或输出列表
            if self.current_algorithm in all_algorithms:
                key = "inputs" if is_input else "outputs"
                params = all_algorithms[self.current_algorithm].get(key, [])
                params.append(new_param)
                all_algorithms[self.current_algorithm][key] = params

                # 保存更新后的数据
                with open("algorithm_data.json", "w", encoding="utf-8") as file:
                    json.dump(all_algorithms, file, ensure_ascii=False, indent=4)

                # 更新表格显示
                table = self.input_table if is_input else self.output_table
                table.insert("", "end", values=(
                    new_param["name"],
                    new_param["symbol"],
                    new_param["type"],
                    new_param["description"]
                ))

                # 更新内存中的算法数据
                self.algorithm_data = all_algorithms
                messagebox.showinfo("成功", f"已添加{'输入' if is_input else '输出'}参数 {param_name}")

        except Exception as e:
            messagebox.showerror("错误", f"添加参数时发生错误: {str(e)}")

    def delete_parameter(self, is_input=True):
        """通用的删除参数方法"""
        if not self.current_algorithm:
            messagebox.showwarning("警告", "请先选择一个算法")
            return

            # 获取选中的参数
        table = self.input_table if is_input else self.output_table
        selected_item = table.selection()
        if not selected_item:
            messagebox.showwarning("警告", f"请选择要删除的{'输入' if is_input else '输出'}参数")
            return

        try:
            # 获取要删除的参数名
            param_name = table.item(selected_item)['values'][0]

            # 更新算法数据JSON
            with open("algorithm_data.json", "r", encoding="utf-8") as file:
                all_algorithms = json.load(file)

                # 删除参数
            if self.current_algorithm in all_algorithms:
                key = "inputs" if is_input else "outputs"
                params = all_algorithms[self.current_algorithm].get(key, [])
                params = [param for param in params if param['name'] != param_name]
                all_algorithms[self.current_algorithm][key] = params

                # 保存更新后的数据
                with open("algorithm_data.json", "w", encoding="utf-8") as file:
                    json.dump(all_algorithms, file, ensure_ascii=False, indent=4)

                    # 从表格中删除
                table.delete(selected_item)

                # 更新内存中的算法数据
                self.algorithm_data = all_algorithms
                messagebox.showinfo("成功", f"已删除{'输入' if is_input else '输出'}参数 {param_name}")

        except Exception as e:
            messagebox.showerror("错误", f"删除参数时发生错误: {str(e)}")


def main():
    root = tk.Tk()
    # 导入简单对话框模块
    import tkinter.simpledialog
    style = ttk.Style()
    style.configure("Treeview", rowheight=25)
    app = AlgorithmIntegrationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
