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
├── mock_server.py            # 模拟需求端HTTP服务
├── test_client.py            # 测试客户端
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

### 5. 模拟需求端HTTP服务
- 提供完整的HTTP服务模拟环境
- 支持接收和解析算法状态消息
- 实时显示算法运行状态和资源使用情况
- 提供健康检查和服务状态查询接口

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
- `flask`: Web服务框架（用于模拟需求端）

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

### 5. 启动模拟需求端服务
```bash
python mock_server.py
```
服务将在 `http://127.0.0.1:8192` 启动，提供以下端点：
- `/resource/webSocketOnMessage`: 接收算法状态消息
- `/health`: 健康检查
- `/`: 服务信息页面

### 6. 运行测试客户端
```bash
python test_client.py
```
测试客户端将向模拟服务发送测试数据，验证通信功能。

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
- 标准化数据格式
- 连接池管理和代理禁用
- 改进的错误处理机制

### 模板结构
```python
class HTTPStatusReporter:
    def __init__(self, server_ip, server_port)  # 使用requests.Session，禁用代理
    def start_periodic_reporting(self, name, info, interval)
    def send_status_message(self, name, info)  # 标准化数据格式
    def stop_reporting(self)
    def get_cpu_usage(self)      # 返回数值格式（无百分号）
    def get_memory_usage(self)   # 返回数值格式（无百分号）
    def get_gpu_usage(self)      # 返回数值格式（无百分号）
    def get_local_ip(self)       # 获取本地IP地址
```

### 主要改进
- **统一数据格式**：所有资源使用率返回数值格式，便于处理
- **连接优化**：使用requests.Session提高连接效率
- **代理禁用**：避免系统代理干扰通信
- **错误处理**：改进异常处理和日志记录
- **标准化字段**：统一状态消息格式和字段定义

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

## 测试和验证

### 功能测试流程
1. **启动模拟需求端服务**
   ```bash
   python mock_server.py
   ```
   服务将在 `http://127.0.0.1:8192` 启动

2. **运行测试客户端**
   ```bash
   python test_client.py
   ```
   测试客户端将执行以下操作：
   - 发送健康检查请求到 `/health` 端点
   - 发送模拟算法状态数据到 `/resource/webSocketOnMessage` 端点
   - 验证服务器响应和数据接收

3. **验证算法状态上报**
   运行任意算法模板文件，例如：
   ```bash
   cd DESIGN/template/内置服务
   python K_means算法.py --http-server 127.0.0.1 --http-port 8192
   ```
   观察模拟服务的日志输出，确认状态数据正确接收

### 测试数据格式
测试客户端发送的数据包含：
- 算法基本信息（名称、类别、版本等）
- 网络信息（IP、端口、状态）
- 资源使用情况（CPU、内存、GPU）
- 时间戳和其他元数据

### 验证要点
- ✅ HTTP连接建立成功
- ✅ 数据格式符合规范
- ✅ 状态消息正确解析
- ✅ 资源监控数据准确
- ✅ 错误处理机制有效

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