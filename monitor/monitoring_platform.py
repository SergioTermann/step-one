import random
import tkinter as tk
from tkinter import ttk, messagebox, Menu
import socket
import threading
import time
import os
import sys
import json
import psutil
import re
from datetime import datetime
import subprocess
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pynvml
from typing import Optional, Dict, Tuple

# 全局配置
CONFIG = {
    "PORT_RANGE": (8080, 8100),
    "CHART_DATA_POINTS": 60,
    "UPDATE_INTERVAL": 1,  # 秒
}

# 监控模式常量
MODE_SYSTEM = "system"
MODE_ALGORITHM = "algorithm"


class PlaceholderEntry(ttk.Entry):
    """带占位符的输入框"""

    def __init__(self, container, placeholder, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = 'grey'
        self.default_fg_color = self['foreground']
        self.bind("<FocusIn>", self.focus_in)
        self.bind("<FocusOut>", self.focus_out)
        self.put_placeholder()

    def put_placeholder(self):
        self.insert(0, self.placeholder)
        self['foreground'] = self.placeholder_color

    def focus_in(self, *args):
        if self['foreground'] == self.placeholder_color:
            self.delete('0', 'end')
            self['foreground'] = self.default_fg_color

    def focus_out(self, *args):
        if not self.get():
            self.put_placeholder()


def get_system_resources() -> Tuple[float, float, float]:
    """获取系统资源使用情况"""
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent

    # 获取GPU使用率
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
    gpu_percent = utilization.gpu
    pynvml.nvmlShutdown()

    return cpu_percent, memory_percent, gpu_percent


def optimize_y_axis(plot, data):
    """优化Y轴显示范围"""
    max_val = max(data)
    if max_val < 1:
        plot.set_ylim(0, 1)
    elif max_val < 10:
        plot.set_ylim(0, 10)
    elif max_val < 20:
        plot.set_ylim(0, 20)
    else:
        plot.set_ylim(0, max(100, max_val * 1.2))


def parse_port(port_value) -> Optional[int]:
    """解析端口值"""
    if isinstance(port_value, int):
        return port_value
    elif isinstance(port_value, str):
        if ':' in port_value:
            return int(port_value.split(':')[1])
        else:
            return int(port_value)
    else:
        messagebox.showerror("错误", f"无效的端口格式: {port_value}")
        return None


def extract_algorithm_name(full_text):
    """提取算法名称"""
    match = re.match(r'(.*?)\s*\(', full_text)
    if match:
        return match.group(1).strip()
    return full_text.strip()


class MonitoringPlatform:
    def __init__(self, root):
        self.msg_text = None
        self.status_monitor_process = None
        self.status_tree = None
        self.search_var = None
        self.system_canvas = None
        self.gpu_line = None
        self.memory_line = None
        self.gpu_plot = None
        self.memory_plot = None
        self.cpu_plot = None
        self.tree = None
        self.tree_search_var = None
        self.right_frame = None
        self.top_frame = None
        self.cpu_line = None
        self.root = root
        self.main_frame = ttk.Frame(root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 初始化数据
        self.algorithm_instances = {}
        self.tree_nodes = {}
        self.total_algorithm_count = 0
        self.monitor_mode = MODE_SYSTEM
        self.current_selected_algorithm = None
        self.current_selected_item = None
        self.current_algorithm_cpu = 0
        self.current_algorithm_memory = 0
        self.current_algorithm_gpu = 0

        # 初始化图表数据
        self.cpu_data = [0] * CONFIG["CHART_DATA_POINTS"]
        self.memory_data = [0] * CONFIG["CHART_DATA_POINTS"]
        self.gpu_data = [0] * CONFIG["CHART_DATA_POINTS"]
        self.time_data = list(range(CONFIG["CHART_DATA_POINTS"]))

        # 创建表格布局
        self.setup_ui()

        # 启动监控服务和更新线程
        self.start_status_monitor()
        threading.Thread(target=self.update_data_thread, daemon=True).start()

    def setup_ui(self):
        """设置UI布局"""
        # 创建顶部框架
        self.top_frame = ttk.Frame(self.main_frame)
        self.top_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建左侧导航
        self.create_left_nav()

        # 创建右侧面板
        self.right_frame = ttk.Frame(self.top_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # 创建系统监控图表和状态视图
        self.create_system_monitor()
        self.create_status_view()

        # 创建日志视图
        self.create_console_view()

    def load_algorithms_from_json(self, json_path='algorithm_data.json') -> Tuple[Dict, int]:
        """从JSON文件加载算法信息并构建树结构"""
        with open(json_path, 'r', encoding='utf-8') as f:
            algorithms = json.load(f)

        # 初始化树结构数据
        tree_data = {
            "内置服务": {"algorithms": [], "count": 0},
            "内置组件": {"algorithms": [], "count": 0},
            "外置信息代理": {"algorithms": [], "count": 0},
            "外置服务代理": {"algorithms": [], "count": 0}
        }
        total_count = 0

        # 分类算法数据
        for algo_name, algo_info in algorithms.items():
            category = algo_info.get('category', '未分类')
            class_name = algo_info.get('class', '未知类')
            subcategory = algo_info.get('subcategory', '未知子类')
            algo_label = f"{algo_name} ({class_name}/{subcategory})"

            if category in tree_data:
                tree_data[category]["algorithms"].append(algo_label)
                tree_data[category]["count"] += 1
            else:
                tree_data.setdefault('未分类', {"algorithms": [algo_label], "count": 1})

            if category in ["内置服务", "外置信息代理", "外置服务代理"]:
                total_count += 1

        return tree_data, total_count


    def create_left_nav(self):
        """创建左侧导航面板"""
        left_frame = ttk.Frame(self.top_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # 工具栏
        toolbar = ttk.Frame(left_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(toolbar, text="刷新", width=8, command=self.refresh_tree).pack(side=tk.RIGHT, padx=2)

        # 搜索框
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        self.tree_search_var = tk.StringVar()
        self.tree_search_var.trace_add("write", self.search_tree)
        search_entry = PlaceholderEntry(search_frame, "请输入")
        search_entry.configure(textvariable=self.tree_search_var)
        search_entry.pack(fill=tk.X)

        # 创建树控件
        style = ttk.Style()
        style.configure("Custom.Treeview", rowheight=40)
        tree_container = ttk.Frame(left_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        # 添加水平滚动条
        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # 创建树控件
        self.tree = ttk.Treeview(
            tree_container,
            show="tree",
            style="Custom.Treeview",
            xscrollcommand=h_scrollbar.set
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        h_scrollbar.config(command=self.tree.xview)
        self.tree.column("#0", width=200, stretch=tk.YES)

        # 绑定事件
        self.tree.unbind('<<TreeviewSelect>>')
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select_no_action)
        self.tree.bind('<Button-3>', self.show_tree_menu)

        # 构建树结构
        self.build_tree_structure()

    def build_tree_structure(self) -> int:
        """构建树结构"""
        # 清空现有树
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_nodes = {}

        # 加载算法数据
        tree_data, total_count = self.load_algorithms_from_json()

        # 要显示的类别
        displayed_categories = ["内置服务", "外置信息代理", "外置服务代理"]

        # 添加算法到树
        for method, method_data in tree_data.items():
            if method not in displayed_categories:
                continue

            # 创建分类节点
            method_text = f"{method} ({method_data['count']})"
            method_id = self.tree.insert("", "end", text=method_text)
            self.tree_nodes[method_id] = {
                "text": method,
                "parent": "",
                "type": "method"
            }

            # 添加算法
            for algo_label in method_data["algorithms"]:
                algo_id = self.tree.insert(method_id, "end", text=algo_label)
                self.tree_nodes[algo_id] = {
                    "text": algo_label,
                    "parent": method_id,
                    "type": "algorithm"
                }

            # 展开分类
            self.tree.item(method_id, open=True)

        self.total_algorithm_count = total_count
        return total_count

    def refresh_tree(self):
        """刷新算法树"""
        try:
            total_count = self.build_tree_structure()
            self.log_message(f"树结构刷新完成，已集成算法总数: {total_count}")

            # 展开所有一级节点
            for item in self.tree.get_children():
                self.tree.item(item, open=True)
        except Exception as e:
            self.log_message(f"刷新树结构时发生错误: {str(e)}")

    def search_tree(self, *args):
        """搜索树中的算法"""
        search_text = self.tree_search_var.get().strip().lower()

        # 重置展开状态
        for item in self.tree.get_children():
            self.tree.item(item, open=False)

        if not search_text:
            return

        # 搜索匹配项
        for item_id, info in self.tree_nodes.items():
            if search_text in info["text"].lower():
                # 找到匹配项，展开路径
                self._expand_to_item(item_id)

                # 选择精确匹配或算法项
                if info["text"].lower() == search_text.lower() or info["type"] == "algorithm":
                    self.tree.selection_set(item_id)
                    self.tree.see(item_id)
                    if info["type"] == "algorithm" and len(search_text) >= 2:
                        break

    def _expand_to_item(self, item_id):
        """展开到指定项的路径"""
        path = []
        current = item_id

        # 构建路径
        while current and current in self.tree_nodes:
            path.append(current)
            parent = self.tree_nodes[current]["parent"]
            if not parent:
                break
            current = parent

        # 展开路径
        path.reverse()
        for i in range(len(path) - 1):
            self.tree.item(path[i], open=True)

    def on_tree_select_no_action(self, event):
        """树节点选择处理-只占位，通过右键菜单触发动作"""
        pass

    def show_tree_menu(self, event):
        """显示树节点右键菜单"""
        item = self.tree.identify_row(event.y)
        if not item:
            return

        # 选中项目
        self.tree.selection_set(item)

        # 检查是否是算法节点
        if item in self.tree_nodes and self.tree_nodes[item]["type"] == "algorithm":
            full_text = self.tree_nodes[item]["text"]
            algorithm_name = extract_algorithm_name(full_text)

            try:
                # 获取算法信息
                with open('algorithm_data.json', 'r', encoding='utf-8') as f:
                    algorithms = json.load(f)

                # 只为本地算法显示菜单
                if algorithm_name in algorithms:
                    is_remote = algorithms[algorithm_name].get('network_info', {}).get('is_remote', False)
                    if not is_remote:
                        menu = Menu(self.root, tearoff=0)
                        menu.add_command(label="启动算法", command=lambda: self.launch_algorithm(item))
                        menu.post(event.x_root, event.y_root)
            except Exception as e:
                self.log_message(f"读取算法数据失败: {e}")

    def create_system_monitor(self):
        """创建系统资源监控图表"""
        monitor_frame = ttk.LabelFrame(self.right_frame, text="资源监控")
        monitor_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        # 创建图表
        fig = plt.Figure(figsize=(8, 2), dpi=100)
        fig.tight_layout(pad=2.0)

        # 设置字体
        plt.rcParams['font.family'] = 'Microsoft YaHei'
        plt.rcParams['axes.unicode_minus'] = False

        # 创建子图
        self.cpu_plot = fig.add_subplot(131)
        self.memory_plot = fig.add_subplot(132)
        self.gpu_plot = fig.add_subplot(133)

        # 设置标题和网格
        self.cpu_plot.set_title('CPU使用率')
        self.memory_plot.set_title('内存使用率')
        self.gpu_plot.set_title('GPU使用率')

        for plot in [self.cpu_plot, self.memory_plot, self.gpu_plot]:
            plot.set_ylim(0, 100)
            plot.grid(True)

        self.cpu_plot.set_ylabel('百分比(%)')

        # 创建线图
        self.cpu_line, = self.cpu_plot.plot(self.time_data, self.cpu_data, 'b-')
        self.memory_line, = self.memory_plot.plot(self.time_data, self.memory_data, 'g-')
        self.gpu_line, = self.gpu_plot.plot(self.time_data, self.gpu_data, 'r-')

        # 添加到UI
        self.system_canvas = FigureCanvasTkAgg(fig, master=monitor_frame)
        self.system_canvas.draw()
        self.system_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_system_monitor(self):
        """更新系统监控图表"""
        # 根据模式选择数据源
        if self.monitor_mode == MODE_ALGORITHM and self.current_selected_algorithm:
            # 算法监控模式
            cpu = self.current_algorithm_cpu
            memory = self.current_algorithm_memory
            gpu = self.current_algorithm_gpu

            # 查找最新数据
            for instance in self.algorithm_instances.values():
                if instance.get('algorithm_name') == self.current_selected_algorithm:
                    try:
                        cpu = float(instance['cpu_usage'].rstrip('%') if instance['cpu_usage'] else 0)
                        memory = float(instance['memory_usage'].rstrip('%') if instance['memory_usage'] else 0)
                        gpu = float(instance['gpu_usage'].rstrip('%') if instance['gpu_usage'] else 0)
                        self.current_algorithm_cpu = cpu
                        self.current_algorithm_memory = memory
                        self.current_algorithm_gpu = gpu
                        break
                    except Exception as e:
                        print(f"解析算法资源数据错误: {e}")

            # 更新标题
            self.cpu_plot.set_title(f'{self.current_selected_algorithm} - CPU使用率')
            self.memory_plot.set_title(f'{self.current_selected_algorithm} - 内存使用率')
            self.gpu_plot.set_title(f'{self.current_selected_algorithm} - GPU使用率')
        else:
            # 系统监控模式
            cpu, memory, gpu = get_system_resources()
            self.cpu_plot.set_title('CPU使用率')
            self.memory_plot.set_title('内存使用率')
            self.gpu_plot.set_title('GPU使用率')

        # 更新数据
        self.cpu_data.pop(0)
        self.cpu_data.append(cpu)
        self.memory_data.pop(0)
        self.memory_data.append(memory)
        self.gpu_data.pop(0)
        self.gpu_data.append(gpu)

        # 更新图表
        self.cpu_line.set_ydata(self.cpu_data)
        self.memory_line.set_ydata(self.memory_data)
        self.gpu_line.set_ydata(self.gpu_data)

        # 优化坐标轴
        optimize_y_axis(self.cpu_plot, self.cpu_data)
        optimize_y_axis(self.memory_plot, self.memory_data)
        optimize_y_axis(self.gpu_plot, self.gpu_data)

        # 刷新画布
        self.system_canvas.draw_idle()

        # 维护选中状态
        if self.current_selected_item:
            try:
                self.status_tree.selection_set(self.current_selected_item)
            except Exception as e:
                if self.current_selected_algorithm:
                    self.find_and_select_algorithm_item()
                print(f"{e}")

    def find_and_select_algorithm_item(self):
        """查找并选中算法表格项"""
        if not self.current_selected_algorithm:
            return

        for item in self.status_tree.get_children():
            values = self.status_tree.item(item, 'values')
            if values and values[0] == self.current_selected_algorithm:
                self.status_tree.selection_set(item)
                self.current_selected_item = item
                break

    def reset_to_system_monitor(self):
        """重置为系统资源监控"""
        # 重置标题
        self.cpu_plot.set_title('CPU使用率')
        self.memory_plot.set_title('内存使用率')
        self.gpu_plot.set_title('GPU使用率')

        # 获取系统资源数据
        cpu, memory, gpu = get_system_resources()

        # 更新数据
        self.cpu_data = [cpu] * CONFIG["CHART_DATA_POINTS"]
        self.memory_data = [memory] * CONFIG["CHART_DATA_POINTS"]
        self.gpu_data = [gpu] * CONFIG["CHART_DATA_POINTS"]

        # 更新图表
        self.cpu_line.set_ydata(self.cpu_data)
        self.memory_line.set_ydata(self.memory_data)
        self.gpu_line.set_ydata(self.gpu_data)

        # 优化坐标轴
        for plot, data in [(self.cpu_plot, self.cpu_data),
                           (self.memory_plot, self.memory_data),
                           (self.gpu_plot, self.gpu_data)]:
            optimize_y_axis(plot, data)

        # 刷新画布
        self.system_canvas.draw()

        # 更新状态
        self.monitor_mode = MODE_SYSTEM

    def create_status_view(self):
        """创建状态监控视图"""
        status_frame = ttk.LabelFrame(self.right_frame, text="状态监控")
        status_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # 工具栏
        toolbar = ttk.Frame(status_frame)
        toolbar.pack(fill=tk.X, pady=5)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.filter_status_table)
        search_entry = PlaceholderEntry(toolbar, "请输入关键词进行搜索")
        search_entry.configure(textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, padx=5)

        refresh_button = ttk.Button(toolbar, text="刷新", command=self.refresh_status_table)
        refresh_button.pack(side=tk.RIGHT, padx=5)

        # 表格容器
        tree_container = ttk.Frame(status_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # 表格列
        columns = (
            "算法名称", "业务类别", "算法类别", "集成方式",
            "状态", "网络地址", "端口", "CPU占用", "内存占用"
        )

        # 创建表格
        self.status_tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show="headings",
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set
        )

        # 配置列
        widths = [150, 100, 100, 100, 100, 100, 100, 100, 100]
        for i, col in enumerate(columns):
            self.status_tree.column(col, width=widths[i], anchor='center')
            self.status_tree.heading(col, text=col)

        # 配置滚动条
        v_scrollbar.config(command=self.status_tree.yview)
        h_scrollbar.config(command=self.status_tree.xview)

        # 添加表格
        self.status_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 绑定事件
        self.status_tree.bind("<Button-3>", self.show_algorithm_context_menu)
        self.status_tree.bind('<<TreeviewSelect>>', self.on_status_tree_select)
        self.status_tree.bind('<Button-1>', self.not_on_status_tree)

        # 初始化表格
        self.update_status_table()

    def not_on_status_tree(self, event):
        """点击状态表格外区域处理"""
        item = self.status_tree.identify_row(event.y)
        if not item:
            # 清除选中
            for selected in self.status_tree.selection():
                self.status_tree.selection_remove(selected)

            # 重置状态
            self.set_selection(None, None)

    def set_selection(self, algorithm_name=None, item_id=None):
        """设置选中状态"""
        self.current_selected_algorithm = algorithm_name
        self.current_selected_item = item_id

        if algorithm_name:
            self.monitor_mode = MODE_ALGORITHM
        else:
            self.monitor_mode = MODE_SYSTEM
            self.reset_to_system_monitor()

    def on_status_tree_select(self, event):
        """状态表格选择处理"""
        selected_items = self.status_tree.selection()
        if not selected_items:
            self.set_selection(None, None)
            return

        # 获取选中信息
        values = self.status_tree.item(selected_items[0])['values']
        if not values or values[0] == "没有正在运行的算法":
            self.set_selection(None, None)
            return

        # 设置选中状态
        self.set_selection(values[0], selected_items[0])

    def show_algorithm_context_menu(self, event):
        """显示算法右键菜单"""
        item = self.status_tree.identify_row(event.y)
        if not item:
            return

        # 选中行
        self.status_tree.selection_set(item)
        self.status_tree.focus(item)

        # 获取算法信息
        try:
            row_data = self.status_tree.item(item)['values']
            if not row_data or row_data[0] == "没有正在运行的算法":
                return

            algorithm_name = row_data[0]
            port = row_data[6]

            # 创建右键菜单
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(
                label="终止",
                command=lambda: self.terminate_algorithm_by_info(algorithm_name, port)
            )

            # 显示菜单
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        except Exception as e:
            print(f"右键菜单错误: {e}")

    def terminate_algorithm_by_info(self, algorithm_name, port_value):
        """基于算法信息终止算法"""
        if not algorithm_name or not port_value:
            messagebox.showwarning("警告", "无法获取算法信息")
            return

        # 解析端口
        try:
            port = parse_port(port_value)
            if port is None:
                return
        except Exception as e:
            messagebox.showerror("错误", f"无法解析端口: {e}")
            return

        # 终止算法
        terminated = self.terminate_algorithm_process(algorithm_name, port)

        # 处理结果
        if terminated:
            self.set_selection(None, None)
            self.update_status_table()
            messagebox.showinfo("成功", f"{algorithm_name} 已终止")
        # else:
        #    messagebox.showwarning("警告", f"无权限终止外部算法{algorithm_name}")

    def terminate_algorithm_process(self, algorithm_name, port) -> bool:
        """终止算法进程"""
        for instance_id, instance in list(self.algorithm_instances.items()):
            if (str(instance.get('port')) == str(port) and
                    instance.get('algorithm_name') == algorithm_name and
                    instance['status'] in ["调用", "空闲"]):
                # try:
                instance['process'].terminate()
                instance['process'].wait(timeout=3)
                instance['status'] = "离线"
                del self.algorithm_instances[instance_id]
                return True
            # except Exception as e:
            #    messagebox.showerror("终止失败", f"无法终止{algorithm_name}")
            #    print(f"{e}")
            #    return False
        return False

    def start_status_monitor(self):
        """启动状态监控服务"""
        try:
            script_path = os.path.join(os.path.dirname(__file__), 'algorithm_status_monitor.py')

            # 创建进程配置
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            # 启动监控进程
            self.status_monitor_process = subprocess.Popen(
                ['python', script_path],
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=False
            )
            print("状态监控服务已启动")
        except Exception as e:
            print(f"启动状态监控服务失败: {e}")

    def update_status_table(self):
        """更新状态表格内容，包括离线算法"""
        # 保存当前选中的算法
        current_algorithm = self.current_selected_algorithm

        # 清空表格
        for item in self.status_tree.get_children():
            self.status_tree.delete(item)

        # 添加所有算法实例，包括离线的
        new_item_to_select = None
        has_algorithms = False

        for instance_id, instance in list(self.algorithm_instances.items()):
            has_algorithms = True
            item_id = self.status_tree.insert("", "end", values=(
                instance.get('algorithm_name', "未知算法"),
                instance.get('business_category', "未分类"),
                instance.get('algorithm_category', "未分类"),
                instance.get('access_category', "未知"),
                instance['status'],  # 这里可能为"离线"
                instance.get('ip', '未知'),
                instance.get('port', "未知"),
                instance['cpu_usage'],
                instance['memory_usage']
            ))

            # 记录之前选中的算法
            if current_algorithm and instance.get('algorithm_name') == current_algorithm:
                new_item_to_select = item_id

        # 恢复选中状态
        if new_item_to_select:
            self.status_tree.selection_set(new_item_to_select)
            self.current_selected_item = new_item_to_select

        # 如果没有数据，显示提示
        if not has_algorithms:
            self.status_tree.insert("", "end", values=(
                "没有正在运行的算法", "", "", "", "", "", "", "", ""
            ))

    def refresh_status_table(self):
        """清除离线状态的算法实例并从表格中移除"""
        # 获取离线实例
        offline_instances = [
            instance_id for instance_id, instance in list(self.algorithm_instances.items())
            if instance['status'] in ['离线', '无法监控']
        ]

        # 如果有离线实例
        if offline_instances:
            # 移除离线实例
            for instance_id in offline_instances:
                algorithm_name = self.algorithm_instances[instance_id].get('algorithm_name', '未知算法')
                del self.algorithm_instances[instance_id]
                self.log_message(f"已清除离线算法实例: {algorithm_name}")

            # 更新表格
            self.update_status_table()
            messagebox.showinfo("清除完成", f"已清除 {len(offline_instances)} 个离线算法实例")
        else:
            messagebox.showinfo("信息", "没有离线的算法实例需要清除")

    def filter_status_table(self, *args):
        """过滤状态表格"""
        search_text = self.search_var.get().strip().lower()

        # 先刷新表格
        self.update_status_table()

        # 如果有搜索文本，过滤结果
        if search_text:
            for item in self.status_tree.get_children():
                values = self.status_tree.item(item, 'values')
                if not any(search_text in str(value).lower() for value in values):
                    self.status_tree.delete(item)

    def create_console_view(self):
        """创建日志视图"""
        console_frame = ttk.LabelFrame(self.main_frame, text="日志")
        console_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, pady=(10, 0))

        # 创建文本框和滚动条
        self.msg_text = tk.Text(console_frame, height=10, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(console_frame, command=self.msg_text.yview)
        self.msg_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.msg_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 添加初始消息
        self.log_message("算法系统监控平台启动...")
        self.log_message(f"已集成算法总数: {self.total_algorithm_count}")
        self.log_message("就绪，等待用户操作")

    def log_message(self, message):
        """记录消息到日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.msg_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.msg_text.see(tk.END)

    def find_free_port(self) -> Optional[int]:
        """找到可用端口"""
        # 收集已用端口
        used_ports = {instance['port'] for instance in self.algorithm_instances.values()
                      if instance['status'] in ["调用", "空闲", "离线"] and 'port' in instance}

        # 查找可用端口
        base_port = 8080
        for offset in range(100):
            test_port = base_port + offset
            if test_port not in used_ports:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.5)
                        s.bind(('127.0.0.1', test_port))
                        return test_port
                except Exception as e:
                    print(f"{e}")
                    continue
        return None

    def launch_algorithm(self, item_id):
        """启动选中的算法"""
        if item_id not in self.tree_nodes or self.tree_nodes[item_id]["type"] != "algorithm":
            return

        algorithm_text = self.tree.item(item_id, "text")

        # 获取算法信息
        algo_path = self.get_algorithm_path(item_id)
        category_info = self.get_algorithm_category_info(item_id)

        if not algo_path or not os.path.exists(algo_path):
            messagebox.showinfo("启动算法", f"算法文件 {algo_path} 不存在")
            return

        # 启动算法
        self.launch_generic_algorithm(algo_path, algorithm_text, category_info)

    def launch_generic_algorithm(self, algo_path, algorithm_text, category_info):
        """启动通用算法"""
        # 提取算法名称
        display_name = extract_algorithm_name(algorithm_text)

        # 获取端口
        port = self.find_free_port()
        if not port:
            messagebox.showerror("错误", "无法找到可用端口")
            return

        # 生成实例ID
        instance_id = f"{display_name.replace(' ', '_').lower()}-{port}"

        try:
            # 启动进程
            process = subprocess.Popen(
                [sys.executable, algo_path, str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # 创建实例记录
            instance = {
                'process': process,
                'port': port,
                'start_time': time.time(),
                'status': category_info.get('status', '未知状态'),
                'algorithm_name': display_name,
                'algorithm_type': display_name,
                'business_category': category_info.get('business_class', '未知业务类别'),
                'algorithm_category': category_info.get('subcategory', '未知类别'),
                'access_category': category_info.get('integration', '未知集成方式'),
                'ip': category_info.get('ip', '未知网络地址'),
                'memory_usage': "",
                'cpu_usage': "",
                'gpu_usage': "",
                'is_remote': category_info.get('is_remote', '未知')
            }

            self.algorithm_instances[instance_id] = instance

            # 更新UI
            self.update_status_table()
            self.log_message(f"算法 {display_name} 启动成功，端口: {port}")

        except Exception as e:
            messagebox.showerror("启动失败", f"无法启动算法 {display_name}: {str(e)}")

    def get_algorithm_path(self, item_id):
        """获取算法文件路径"""
        full_text = self.tree_nodes[item_id]["text"]
        algorithm_name = extract_algorithm_name(full_text)

        # 构建文件名和路径
        generated_filename = f"{algorithm_name}_generated.py"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "generated_algorithms", generated_filename)

    def get_algorithm_category_info(self, item_id):
        """获取算法类别信息"""
        try:
            # 获取算法文本
            full_text = self.tree_nodes[item_id]["text"]

            # 提取基本信息
            algorithm_name = extract_algorithm_name(full_text)
            business_class = "未知业务类别"
            subcategory = "未知类别"

            # 提取类别信息
            match = re.match(r'(.*?)\s*\((.*?)\)', full_text)
            if match and '/' in match.group(2):
                category_info = match.group(2).split('/')
                if len(category_info) >= 2:
                    business_class = category_info[0]
                    subcategory = category_info[1]

            # 获取集成方式
            parent_id = self.tree_nodes[item_id]["parent"]
            integration_name = "未知集成方式"
            if parent_id:
                integration_name = re.sub(r'\s*\(\d+\)$', '', self.tree_nodes[parent_id]["text"])

            # 从JSON读取详细信息
            status = "未知状态"
            ip = "未知网络地址"
            port = "未知端口"
            is_remote = "未知"

            try:
                with open('algorithm_data.json', 'r', encoding='utf-8') as f:
                    algorithms = json.load(f)

                for name, algo_info in algorithms.items():
                    if name == algorithm_name or algo_info.get('name') == algorithm_name:
                        network_info = algo_info.get('network_info', {})
                        status = network_info.get('status', '未知状态')
                        ip = network_info.get('ip', '未知网络地址')
                        port = network_info.get('port', '未知端口')
                        is_remote = network_info.get('is_remote', False)
                        break
            except Exception as e:
                print(f"{e}")
                pass

            return {
                "name": algorithm_name,
                "business_class": business_class,
                "subcategory": subcategory,
                "integration": integration_name,
                "status": status,
                "ip": ip,
                "port": port,
                "is_remote": is_remote
            }

        except Exception as e:
            print(f"获取算法类别信息错误: {e}")
            return {
                "name": "未知算法",
                "business_class": "未知业务类别",
                "subcategory": "未知类别",
                "integration": "未知集成方式",
                "status": "未知状态",
                "ip": "未知网络地址",
                "port": "未知端口",
                "is_remote": "未知"
            }

    def update_data_thread(self):
        """数据更新线程"""
        while True:
            try:
                # 更新外部算法
                self.update_external_algorithms()

                # 更新内部算法资源使用
                self.update_internal_algorithms_resources()

                # 统一更新UI
                self.root.after(0, self.update_ui)

            except Exception as e:
                print(f"更新数据线程错误: {e}")

            # 休眠
            time.sleep(CONFIG["UPDATE_INTERVAL"])

    def update_ui(self):
        """更新UI组件"""
        self.update_system_monitor()
        self.update_status_table()

        # 检查选中状态
        if self.monitor_mode == MODE_ALGORITHM and not self.status_tree.selection():
            self.set_selection(None, None)

    def update_external_algorithms(self):
        """更新外部算法状态并检测超时"""
        current_time = time.time()
        timeout_threshold = 8  # 8秒超时阈值

        try:
            with open('algorithm_data.json', 'r', encoding='utf-8') as f:
                all_algorithms = json.load(f)

            # 筛选外部算法
            external_algorithms = {
                name: algo_info for name, algo_info in all_algorithms.items()
                if algo_info.get('network_info', {}).get('is_remote', True)
            }

            # 先检查json中的时间戳，如果超时则更新其状态为'离线'
            for name, algo_info in external_algorithms.items():
                network_info = algo_info.get('network_info', {})
                last_update = network_info.get('last_update_timestamp', 0)

                if current_time - last_update > timeout_threshold:
                    # 算法超时，更新json文件
                    if network_info.get('status') != '离线':
                        network_info['status'] = '离线'
                        all_algorithms[name]['network_info'] = network_info
                        # 将更改写回json文件
                        with open('algorithm_data.json', 'w', encoding='utf-8') as f:
                            json.dump(all_algorithms, f, ensure_ascii=False, indent=4)
                        self.log_message(f"外部算法 {name} 已离线")

            # 更新算法实例状态
            for name, algo_info in external_algorithms.items():
                instance_id = f"external-{name}"
                status = algo_info.get('network_info', {}).get('status', '未知')

                # 检查算法是否仍在运行（非离线状态）
                is_running = status != '离线'

                if is_running:
                    # 添加或更新运行中的算法实例
                    if instance_id not in self.algorithm_instances:
                        self.algorithm_instances[instance_id] = {
                            'process': None,
                            'start_time': time.time(),
                            'algorithm_name': name,
                            'business_category': algo_info.get('class', '未知'),
                            'algorithm_category': algo_info.get('subcategory', '未知'),
                            'access_category': algo_info.get('category', '未知'),
                            'ip': algo_info.get('network_info', {}).get('ip', '未知'),
                            'port': algo_info.get('network_info', {}).get('port', '未知'),
                            'status': status,
                            'memory_usage': algo_info.get('network_info', {}).get('memory_usage', '未知'),
                            'cpu_usage': algo_info.get('network_info', {}).get('cpu_usage', '未知'),
                            'gpu_usage': algo_info.get('network_info', {}).get('gpu_usage', '未知'),
                            'is_remote': algo_info.get('network_info', {}).get('is_remote', '未知')
                        }
                    else:
                        # 更新状态
                        self.algorithm_instances[instance_id]['status'] = status
                elif instance_id in self.algorithm_instances:
                    # 存在但已离线，更新状态为离线
                    self.algorithm_instances[instance_id]['status'] = '离线'

        except Exception as e:
            print(f"更新外部算法状态错误: {e}")

    def update_internal_algorithms_resources(self):
        """更新内部算法资源使用情况"""
        for instance_id, instance in list(self.algorithm_instances.items()):
            if not instance.get('is_remote'):
                try:
                    # 获取进程资源
                    process = psutil.Process(instance['process'].pid)
                    cpu_percent = process.cpu_percent(interval=0.1) + 0.1 * random.random()
                    mem_percent = process.memory_percent() + 0.1 * random.random()

                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_percent = utilization.gpu

                    # 更新数据
                    instance['cpu_usage'] = f"{cpu_percent:.2f}%"
                    instance['memory_usage'] = f"{mem_percent:.2f}%"
                    instance['gpu_usage'] = f"{gpu_percent:.2f}%"
                except Exception as e:
                    # 处理进程结束
                    instance['cpu_usage'] = "0.00%"
                    instance['memory_usage'] = "0.00%"
                    instance['gpu_usage'] = "0.00%"
                    instance['status'] = "无法监控"
                    print(f"{e}")

    def on_closing(self):
        """关闭应用程序"""
        if hasattr(self, 'status_monitor_process'):
            try:
                self.status_monitor_process.terminate()
            except Exception as e:
                print(f"关闭状态监控服务错误: {e}")
        self.root.destroy()


def main():
    root = tk.Tk()
    root.title("无人集群装备算法模型集成接入工具-算法模型接入监控")

    # 设置窗口
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{screen_width}x{screen_height}+0+0")
    root.state('zoomed')
    root.minsize(800, 600)

    # 创建应用
    app = MonitoringPlatform(root)

    # 绑定关闭事件
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    # 启动主循环
    root.mainloop()


if __name__ == "__main__":
    main()
