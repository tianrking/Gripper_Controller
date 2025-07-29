# 夹爪电机网页控制器 (Gripper Motor Web Controller)

这是一个通过 WebSocket 实现实时网页控制达妙电机（DM-J4310-2EC）的上位机项目。项目采用 Python 作为后端，控制电机硬件，并通过 React 构建了一个美观、专业的 PC 端控制面板。

## 🎥 Demo

<p align="center">
  <img src="https://github.com/tianrking/SmartClaw-Console/raw/refs/heads/main/output.gif" alt="Project Demo GIF" width="100%">
</p>
<p align="center">
  <em>Project Feature Demo: Startup Calibration, Manual Control, and Automatic Mode Switching</em>
</p>

<p align="center">
  <img src="https://github.com/tianrking/SmartClaw-Console/raw/refs/heads/main/output2.gif" alt="Project Demo GIF" width="100%">
</p>
<p align="center">
  <em>Project Feature Demo: Working</em>
</p>

<p align="center">
  <img src="https://github.com/tianrking/SmartClaw-Console/raw/refs/heads/main/output3.gif" alt="Project Demo GIF" width="100%">
</p>
<p align="center">
  <em>Project Feature Demo: Simulation</em>
</p>



## ✨ 主要功能

- **启动时标定**: 引导用户手动设置夹爪的物理极限，确保运动范围的精确性。
- **实时通信**: 基于 WebSocket，实现前端与硬件之间的低延迟双向通信。
- **PC优化仪表盘**: 使用 React 构建的现代化、美观的两栏式网页布局，专为电脑访问优化。
- **多种控制模式**:
    - **自动模式**: 一键执行抓取、释放、往复运动。
    - **手动模式**: 通过拖动滑块，实时、精确控制夹爪的开合角度。
- **实时参数调节**:
    - **力矩调节**: 在网页上实时调整力矩模式下的驱动力矩大小。
- **状态实时显示**: 在网页上实时展示电机的当前模式、位置、反馈力矩等核心状态。

## 📂 项目结构

```
.
├── backend/         # Python 后端代码
│   ├── DM_CAN.py    # 电机驱动库 (核心)
│   └── server_ws_manual.py  # 主运行程序 (最新的WebSocket版本)
├── frontend/        # React 前端代码
│   ├── src/
│   │   ├── App.jsx  # React 主组件
│   │   └── App.css  # 主样式文件
│   └── package.json # 前端依赖
└── README.md        # 本文档
```

## 🛠️ 环境准备 (Prerequisites)

在开始之前，请确保您的系统已安装以下软件：

1.  **Python 3.8+**
2.  **Node.js v16+** 和 **npm**
3.  硬件连接：确保达妙电机已通过串口正确连接到您的计算机。

## 🚀 安装与启动

### 1. 克隆项目仓库

打开一个新的终端，并运行以下命令：

```bash
git clone https://github.com/tianrking/SmartClaw-Console
cd SmartClaw-Console 
```

### 2. 后端配置

```bash
# 进入后端目录
cd backend

# (推荐) 创建并激活Python虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装Python依赖
pip install websockets pyserial numpy
```
**重要提示**: 您需要修改 `backend/server_ws_manual.py` 文件中的串口号（`port`）以匹配您的硬件。
- **如何查找串口号？**
  1. 将您的 USB CAN 设备连接到电脑。
  2. 在终端中运行以下命令，它会列出所有可能的串口设备：
     ```bash
     ls /dev | grep -E 'ttyUSB|ttyACM'
     ```
  3. 命令的输出结果（例如 `ttyACM0` 或 `ttyUSB0`）就是您需要的串口名称。
  4. 将 `server_ws_manual.py` 文件中 `port='/dev/ttyACM0'` 这一行的值修改为您找到的名称。

### 3. 前端配置

```bash
# 返回项目根目录
cd ..
# 进入前端目录
cd frontend

# 安装Node.js依赖
npm install
```

### 4. 启动项目

为了运行此项目，您需要同时启动后端服务和前端服务。建议使用两个独立的终端窗口来分别管理它们。

**终端 1: 启动后端服务**

```bash
# 确保您位于项目根目录
# 激活虚拟环境 (如果已创建)
source backend/venv/bin/activate

# 运行 Python WebSocket 服务器
python3 backend/server_ws_manual.py
```
*您应该会看到服务器启动并开始监听 `ws://0.0.0.0:8765` 的日志。请保持此终端窗口运行。*

**终端 2: 启动前端服务**

```bash
# 打开一个新的终端窗口，并确保您位于项目根目录
cd frontend

# 运行 React 开发服务器
npm run dev
```
*您会看到一个本地网址（通常是 `http://localhost:5173`）。在浏览器中打开此地址。*

## 🎮 操作流程

### 1. 硬件标定 (Calibration)

当您第一次在浏览器中打开前端页面时，会首先进入**标定界面**。这是确保软件控制范围与夹爪物理极限精确匹配的关键一步。

1.  **手动控制**: 界面上会有一个“手动控制位置”的滑块。拖动此滑块，可以自由地移动夹爪。
2.  **设定最小值 (闭合极限)**: 将夹爪**完全闭合**到其物理极限位置，然后点击 **`Set as MIN (Closed)`** 按钮。您会看到“Recorded Min”字段更新为当前的位置读数。
3.  **设定最大值 (张开极限)**: 将夹爪**完全张开**到其物理极限位置，然后点击 **`Set as MAX (Open)`** 按钮。“Recorded Max”字段将会更新。
4.  **确认标定**: 当最小值和最大值都已设定后，点击绿色的 **`Confirm Calibration & Begin Operation`** 按钮。

完成以上步骤后，系统将保存标定范围，并自动跳转到主控制面板。

### 2. 主控制面板

在主控制面板中，您可以执行所有高级操作，如自动抓取、往复运动以及实时调节力矩和位置。

## 📡 WebSocket API 接口说明

- **服务器地址**: `ws://127.0.0.1:8765`
- **通信格式**: JSON

### ➡️ 前端 -> 后端 (发送指令)

| 指令 (`command`) | 值 (`value`) | 描述 |
| :--------------- | :----------- | :--- |
| **标定指令** | | |
| `set_min` | `null` | 将电机当前位置记录为最小值（闭合极限）。 |
| `set_max` | `null` | 将电机当前位置记录为最大值（张开极限）。 |
| `confirm_calibration` | `null` | 确认标定，完成设置并进入主控制面板。 |
| **操作指令** | | |
| `grasp`          | `null`       | 执行抓取动作。 |
| `release`        | `null`       | 执行释放动作。 |
| `reciprocate`    | `null`       | 执行往复运动。 |
| `stop`           | `null`       | 停止所有运动。 |
| `set_position`   | `float`      | 切换到手动模式，并设定目标位置。|
| `set_torque`     | `float`      | 设定力矩模式下的驱动力矩。|

### ⬅️ 后端 -> 前端 (广播状态)

后端会以约 10Hz 的频率，持续向所有连接的客户端广播状态信息。

*消息格式:*
```json
{
  "type": "status",
  "data": {
    "is_connected": true,
    "mode": "manual",
    "position": -3.49,
    "torque": 1.25,
    "min_angle": -3.78,
    "max_angle": -3.05,
    "target_position": -3.5,
    "move_torque": 0.8,
    "is_calibrated": true // 关键状态：决定前端显示哪个界面
  }
}
