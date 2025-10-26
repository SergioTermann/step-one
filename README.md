# 算法监控平台

一个基于Python的分布式算法监控与管理平台，支持多种类型算法的注册、状态监控和资源管理。

## 项目概述

本项目提供了一个完整的算法监控解决方案，支持四大类算法的集成与监控：
- **内置服务**：本地运行的核心算法
- **内置组件**：本地算法组件和模块
- **外置信息代理**：外部信息源的代理服务
- **外置服务代理**：外部服务的代理接口

## 项目结构

```
step1/
├── DESIGN/                     # 设计模板和代码生成
│   ├── template/              # 算法模板文件
│   │   ├── 内置服务/          # 内置服务算法模板
│   │   ├── 内置组件/          # 内置组件算法模板
│   │   ├── 外置信息代理/      # 外置信息代理模板
│   │   └── 外置服务代理/      # 外置服务代理模板
│   ├── 生成框架代码/          # 自动生成的框架代码
│   ├── algorithm_data.json    # 算法元数据配置
│   ├── load_json.py          # JSON配置加载器
│   ├── manage.py             # 项目管理脚本
│   └── monitoring_platform.py # 监控平台主程序
├── monitor/                   # 监控相关组件
│   ├── algorithm_status_monitor.py # 算法状态监控器
│   ├── monitoring_platform.py     # 监控平台实现
│   └── generated_algorithms/       # 生成的算法实例
├── http_connect.py           # HTTP连接和状态上报模块
├── requirements.txt          # 项目依赖
└── 监控界面注册规范.md       # 监控界面注册规范文档
```

## 核心功能

### 1. 算法分类管理
- **内置服务**：K-means聚类、扩展卡尔曼滤波、鸽群优化、微分博弈、鹰鸽博弈、深度强化学习等
- **内置组件**：一致性编队、基于信息素的协同侦察、基于狼群智能的协同打击等
- **外置信息代理**：YOLO目标检测、拍卖算法等
- **外置服务代理**：大模型服务代理等

### 2. 实时状态监控
- 算法运行状态监控（空闲/调用/离线/无法监控/未知状态）
- 系统资源监控（CPU、内存、GPU使用率）
- 网络连接状态监控
- 自动故障检测和报警

### 3. HTTP状态上报
- 基于HTTP协议的状态上报机制
- 支持周期性状态更新
- 详细的算法信息上报（类别、版本、描述、输入输出等）
- 优雅的程序关闭处理

### 4. 动态配置管理
- JSON格式的算法配置文件
- 支持运行时配置更新
- 灵活的参数配置系统

## 安装和配置

### 环境要求
- Python 3.8+
- Windows/Linux/macOS

### 安装依赖
```bash
pip install -r requirements.txt
```

### 主要依赖包
- `requests`: HTTP请求处理
- `psutil`: 系统资源监控
- `pynvml`: NVIDIA GPU监控
- `numpy`: 数值计算
- `threading`: 多线程支持

## 使用指南

### 1. 启动监控平台
```bash
cd DESIGN
python monitoring_platform.py
```

### 2. 运行算法实例
以K-means算法为例：
```bash
cd DESIGN/template/内置服务
python K_means算法.py --server 127.0.0.1 --port 12345 --http-server 180.1.80.3 --http-port 8192
```

### 3. 查看算法状态
```bash
cd monitor
python algorithm_status_monitor.py
```

### 4. 自定义算法集成
1. 在相应的模板目录下创建算法文件
2. 继承HTTPStatusReporter类
3. 实现必要的状态上报功能
4. 更新algorithm_data.json配置

## HTTP状态上报协议

### 上报地址
- 默认服务器：`180.1.80.3:8192`
- 端点：`/resource/webSocketOnMessage`

### 上报数据格式
```json
{
  "name": "算法名称",
  "category": "算法类别",
  "class": "业务类别",
  "subcategory": "算法子类别",
  "version": "版本号",
  "creator": "创建者",
  "description": "算法描述",
  "inputs": [...],
  "outputs": [...],
  "network_info": {
    "ip": "IP地址",
    "port": 端口号,
    "status": "运行状态",
    "last_update_timestamp": 时间戳,
    "cpu_usage": CPU使用率,
    "memory_usage": 内存使用率,
    "gpu_usage": GPU使用率,
    "is_remote": 是否远程
  }
}
```

### 状态值定义
- `空闲`：算法已启动但未执行任务
- `调用`：算法正在执行任务
- `离线`：算法已停止或无法连接
- `无法监控`：无法获取算法状态
- `未知状态`：状态信息不明确

## 算法模板说明

### HTTPStatusReporter类
所有算法模板都集成了HTTPStatusReporter类，提供以下功能：
- 周期性状态上报
- 系统资源监控
- 网络状态管理
- 优雅关闭处理

### 模板结构
```python
class HTTPStatusReporter:
    def __init__(self, server_ip, server_port)
    def start_periodic_reporting(self, name, info, interval)
    def send_status_message(self, name, info)
    def stop_reporting(self)
    def get_cpu_usage(self)
    def get_memory_usage(self)
    def get_gpu_usage(self)
```

## 配置参数

### 命令行参数
- `--server`: 算法服务器IP地址（默认：127.0.0.1）
- `--port`: 算法服务器端口（默认：12345）
- `--http-server`: HTTP状态上报服务器IP（默认：180.1.80.3）
- `--http-port`: HTTP状态上报服务器端口（默认：8192）
- `--report-interval`: 状态上报间隔秒数（默认：30）
- `--algo-ip`: 算法服务IP地址
- `--algo-port`: 算法服务端口

### 环境变量
- `SPECIAL_PARAM`: 特殊配置参数（JSON格式）

## 监控界面注册规范

详细的注册规范请参考 `监控界面注册规范.md` 文档，包含：
- 四大类算法的注册要求
- 字段定义和数据格式
- 上报协议和状态维护
- 资源占用监控标准

## 开发指南

### 添加新算法
1. 在对应的template目录下创建算法文件
2. 导入必要的模块和HTTPStatusReporter
3. 实现算法核心逻辑
4. 集成状态上报功能
5. 更新配置文件

### 自定义状态上报
```python
# 创建HTTP状态上报器
http_reporter = HTTPStatusReporter('180.1.80.3', 8192)

# 构建算法信息
algorithm_info = {
    "category": "算法类别",
    "class": "业务类别",
    "subcategory": "算法子类别",
    # ... 其他信息
}

# 启动周期性上报
http_reporter.start_periodic_reporting("算法名称", algorithm_info, 30)
```

## 故障排除

### 常见问题
1. **连接超时**：检查网络连接和服务器地址
2. **状态上报失败**：验证HTTP服务器配置
3. **资源监控异常**：确认psutil和pynvml安装正确
4. **算法启动失败**：检查依赖包和配置参数

### 日志查看
程序运行时会输出带时间戳的日志信息，便于问题定位。

## 贡献指南

1. Fork项目仓库
2. 创建功能分支
3. 提交代码更改
4. 创建Pull Request

## 许可证

本项目采用MIT许可证，详情请参考LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目Issues
- 邮件联系

---

**注意**：本项目仍在持续开发中，功能和接口可能会有变化。请关注项目更新和文档变更。