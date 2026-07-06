# error_to_do

基于DSP与边缘AI的电力电子设备非侵入式故障诊断系统。采用TMS320F28335实时采集信号并在线提取17种时频域特征，RK3566/3588部署CNN模型推理，实现嵌入式端到端诊断闭环。核心特性：非侵入式架构、故障触发诊断(<50ms)、8KB内存特征提取、跨平台特征一致性校准。配套PySide6上位机，支持波形可视化、串口调试、批量测试。识别准确率>99%。

## error_to_do_assist

上位机软件，基于 Python/PySide6 开发，负责波形数据加载、串口通信、批量测试、性能评估和文件传输。

### 项目结构
```bash
error_to_do_assist/
├── main.py                         # 主程序入口
├── resources/
│   └── __init__.py                 # 资源管理器
├── ui/
│   ├── __init__.py
│   ├── main_window.py              # 主窗口（左侧导航+右侧容器）
│   ├── log_page.py                 # 日志页面（波形图+特征表+通信日志）
│   ├── serial_debug_page.py        # 设备管理页面
│   ├── settings_page.py            # 设置页面（CSV导入+串口配置+发送控制+SSH设置）
│   ├── batch_test_page.py          # 批量测试页面
│   ├── storage_page.py             # 存储页面
│   ├── evaluation_page.py          # 性能评估页面
│   ├── file_transfer_page.py       # 文件传输页面（本地+SSH远程）
│   └── about_page.py               # 关于页面
├── core/
│   ├── __init__.py
│   ├── serial_worker.py            # 串口工作线程（发送/接收）
│   ├── device_manager.py           # 设备管理器
│   ├── settings_manager.py         # 设置管理器（settings.ini读写）
│   ├── ssh_manager.py              # SSH/SFTP连接管理器
│   ├── constants.py                # 常量定义
│   └── feature_extractor.py        # 本地特征提取（与DSP对比）
├── signal_control/
│   ├── __init__.py
│   ├── log_controller.py           # 日志控制器
│   ├── devices_controller.py       # 设备控制器
│   ├── settings_controller.py      # 设置控制器
│   └── storage_controller.py       # 存储控制器
├── devices_list/
│   └── devices.json
├── settings/
│   └── settings.ini
├── logs/
├── storage/
└── models/
```

### 功能页面

接收日志: 波形显示、DSP/本地特征对比、通信日志
串口调试: 设备管理与串口调试
设置: CSV数据导入、串口参数配置、发送控制、SSH连接设置
批量调试: 文件夹CSV批量发送，记录DSP特征和耗时
终端存储读取: 终端数据存储与读取
性能评估: 合并上位机与RK3588日志，计算准确率/精确率/召回率/F1-Score，显示混淆矩阵和PR曲线
文件传输: 左侧本地文件，右侧SSH远程设备文件，支持双向传输
关于: 版本信息、作者、团队

### 核心模块

serial_worker.py: 串口通信线程，分包发送波形数据到DSP，接收特征结果
ssh_manager.py: SSH/SFTP连接管理，支持远程文件浏览和传输
feature_extractor.py: 本地17维特征提取，用于与DSP特征对比验证
settings_manager.py: INI配置文件读写，保存串口/SSH/CSV参数

### 数据通信协议

帧格式: AA 55 + CMD + LEN(2B) + PAYLOAD + CHECKSUM(1B) + 55 AA

| 方向 | 命令 | 说明 |
|------|------|------|
| 上位机→DSP | 0x01 | 开始发送 |
| 上位机→DSP | 0x02 | 停止发送 |
| 上位机→DSP | 0x03 | 请求特征结果 |
| 上位机→DSP | 0x04 | 数据总长度(4B) |
| 上位机→DSP | 0x10 | 波形数据(int16) |
| 上位机→RK3566 | 0x22 | 本地17维特征(float32×17) |
| DSP→上位机 | 0x21 | DSP提取的17维特征(float32×17) |
| DSP→上位机 | 0x06 | ACK |
| DSP→上位机 | 0x15 | NACK |

### 使用教程

#### 1. 硬件连接

PC上位机通过USB转TTL连接DSP的SCI-B（GPIO14/15），波特率9600
RK3588通过USB转TTL连接DSP的SCI-C（GPIO62/63），波特率9600
RK3588通过网线连接PC，用于SSH文件传输

#### 2. 启动上位机

python main.py

#### 3. 串口连接

切换到"设置"页面 -> "串口与发送"标签页
选择串口号和波特率9600
点击"连接串口"

#### 4. 单文件测试

切换到"设置"页面 -> "数据导入"标签页
点击"浏览"选择CSV文件
设置采样率、电压列等参数
点击"加载并显示波形"
切换到"串口与发送"标签页
点击"发送数据到DSP"
等待DSP返回特征值
可在"接收日志"页面查看波形图和特征对比表

#### 5. 批量测试

切换到"批量调试"页面
点击"浏览"选择CSV文件夹
点击"扫描文件"载入文件列表
设置文件数、发送模式等参数
SSH登录RK3588，运行: python infer_rk3588_batch.py -p /dev/ttyUSB0 -t 100
点击"开始批量发送"
等待发送完成
点击"导出结果"保存上位机日志
RK3588会自动保存推理结果到system_test_logs/

#### 6. 性能评估

切换到"性能评估"页面
分别加载上位机导出的JSON和RK3588导出的JSON
点击"合并并计算"
查看准确率、精确率、召回率、F1-Score
点击"显示混淆矩阵"或"显示PR曲线"查看可视化图表
点击"导出评估报告"保存评估结果

#### 7. 文件传输

切换到"设置"页面 -> "SSH设置"标签页
输入RK3588的IP地址、端口、用户名和密码
点击"连接SSH"
切换到"文件传输"页面
左侧为本地文件，右侧为远程设备文件
选中文件后点击"→"上传或"←"下载
双击文件夹进入子目录

### 性能指标

| 指标 | 说明 |
|------|------|
| 单次诊断耗时 | 从DSP检测到波形异常到RK3588输出诊断结果的全流程时间 |
| 特征提取耗时 | DSP对单周期波形计算17种时频域特征的时间 |
| 推理耗时 | RK3588 NPU完成一次CNN推理的时间 |
| 准确率 | 所有诊断结果中判断正确的比例 |
| 精确率 | 诊断为某类故障中真正属于该类的比例（衡量报警可信度） |
| 召回率 | 真实发生的某类故障中被正确诊断的比例（衡量故障发现能力） |
| F1-Score | 精确率与召回率的调和平均，综合衡量诊断可靠性 |

### 环境依赖

Python >=3.8
PySide6, numpy, pandas, pyserial, matplotlib, paramiko, scipy

---

## 技术文档

项目相关的技术说明文档，包括系统架构、算法原理、通信协议等。

---

## 部分重要代码

DSP TMS320F28335 端核心代码，包括SCI串口通信、特征提取算法（feature_extract.c）、主程序（main.c）等。

---

## 授权书

授权书.pdf: 项目授权相关文件。

---

## 演示视频

系统运行演示视频，展示完整工作流程。

---

## model

### model_rknn

RK3588 NPU 部署用的 RKNN 格式模型文件，包含模型权重和配置文件（model_config.json）。

### model_pt

PyTorch 训练框架下的原始模型文件，包含训练代码和模型权重。

### model_onnx

ONNX 中间格式模型文件，用于从 PyTorch 到 RKNN 的模型转换。

---

## 作者

Author: batterymain
Team: 慢慢尝试
(c) 2026 All Rights Reserved
