# -*- coding: utf-8 -*-
import time
import threading
import sys
from flask import Flask, jsonify
from flask_cors import CORS # 【新增】导入CORS

# 假设 DM_CAN.py 和 serial 在您的环境中可用
try:
    from DM_CAN import *
    import serial
except ImportError as e:
    print(f"错误: 缺少必要的库 ({e})。请确保已安装 pyserial 并且 DM_CAN.py 文件存在。")
    sys.exit(1)

# --- 1. GripperController 类 ---
# 封装所有硬件控制逻辑
class GripperController:
    """
    一个线程安全的类，用于控制夹爪电机并管理其状态。
    """
    def __init__(self, port, baud_rate, motor_can_id, motor_master_id, min_angle, max_angle, move_torque):
        # --- 参数配置 ---
        self.port = port
        self.baud_rate = baud_rate
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.move_torque = move_torque

        # --- 硬件对象 ---
        self.motor = Motor(DM_Motor_Type.DM4310, motor_can_id, motor_master_id)
        self.serial_device = None
        self.motor_control = None

        # --- 状态管理 ---
        self.mode = "stopped"  # 可选值: "stopped", "grasping", "releasing", "reciprocating"
        self.current_position = 0.0
        self.current_torque = 0.0
        self.is_connected = False
        self._lock = threading.Lock() # 线程锁，用于安全地更新状态

        # --- 线程控制 ---
        self._stop_event = threading.Event()
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)

    def connect(self):
        """初始化串口，配置并使能电机，然后启动控制线程。"""
        if self.is_connected:
            print("警告: 已经连接。")
            return True
        try:
            print(f"正在尝试打开串口: {self.port}...")
            self.serial_device = serial.Serial(self.port, self.baud_rate, timeout=0.5)
            print(f"成功打开串口: {self.port} @ {self.baud_rate}")

            self.motor_control = MotorControl(self.serial_device)
            self.motor_control.addMotor(self.motor)

            print("正在切换电机到 MIT 控制模式...")
            if not self.motor_control.switchControlMode(self.motor, Control_Type.MIT):
                raise RuntimeError("无法切换电机到 MIT 模式")
            
            print("正在使能电机...")
            self.motor_control.enable(self.motor)
            print("电机已使能。")
            
            self.is_connected = True
            self._stop_event.clear()
            self._control_thread.start()
            print("控制循环线程已启动。")
            return True
        except Exception as e:
            print(f"[严重错误] 连接失败: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """停止控制线程，禁用电机并关闭串口。"""
        if not self.is_connected:
            return
        print("正在断开连接...")
        self._stop_event.set() # 发送停止信号给线程
        self._control_thread.join(timeout=2) # 等待线程结束

        if self.motor_control and self.motor.isEnable:
            print("正在禁用电机...")
            self.motor_control.controlMIT(self.motor, 0, 1.0, 0, 0, 0)
            time.sleep(0.05)
            self.motor_control.disable(self.motor)
        
        if self.serial_device and self.serial_device.is_open:
            self.serial_device.close()
            print("串口已关闭。")
        
        self.is_connected = False
        print("已安全断开。")

    def _control_loop(self):
        """在后台线程中运行的电机主控制循环。"""
        direction = 1
        print("控制循环开始...")
        while not self._stop_event.is_set():
            loop_start_time = time.time()
            
            # 从电机获取反馈
            pos = self.motor.getPosition()
            tor = self.motor.getTorque()

            if pos is None or tor is None:
                time.sleep(0.02)
                continue
            
            # 使用锁来安全地更新和读取状态
            with self._lock:
                self.current_position = pos
                self.current_torque = tor
                current_mode = self.mode
            
            # --- 核心状态机逻辑 ---
            tau_cmd = 0.0
            if current_mode == "grasping":
                tau_cmd = -self.move_torque
                if self.current_position <= self.min_angle:
                    self.stop() # 到达位置后自动停止
            elif current_mode == "releasing":
                tau_cmd = self.move_torque
                if self.current_position >= self.max_angle:
                    self.stop() # 到达位置后自动停止
            elif current_mode == "reciprocating":
                if self.current_position >= self.max_angle:
                    direction = -1
                elif self.current_position <= self.min_angle:
                    direction = 1
                tau_cmd = direction * self.move_torque
            
            # 发送指令
            self.motor_control.controlMIT(self.motor, kp=0.0, kd=1.0, q=0.0, dq=0.0, tau=tau_cmd)
            
            # 保持循环频率
            time.sleep(max(0, 0.02 - (time.time() - loop_start_time)))
        print("控制循环已停止。")

    # --- 公共API方法 ---
    def grasp(self):
        print("[API] 接收到 '抓取' 指令")
        with self._lock:
            self.mode = "grasping"
        return {"status": "ok", "mode": "grasping"}

    def release(self):
        print("[API] 接收到 '释放' 指令")
        with self._lock:
            self.mode = "releasing"
        return {"status": "ok", "mode": "releasing"}

    def reciprocate(self):
        print("[API] 接收到 '往复运动' 指令")
        with self._lock:
            self.mode = "reciprocating"
        return {"status": "ok", "mode": "reciprocating"}

    def stop(self):
        print("[API] 接收到 '停止' 指令")
        with self._lock:
            self.mode = "stopped"
        return {"status": "ok", "mode": "stopped"}

    def get_status(self):
        with self._lock:
            # 【修复】将 numpy.float32 转换为标准的 Python float 类型，以便JSON序列化
            status = {
                "is_connected": self.is_connected,
                "mode": self.mode,
                "position": float(self.current_position),
                "torque": float(self.current_torque)
            }
        return status

# --- 2. Flask API 服务器 ---
app = Flask(__name__)
CORS(app) # 【新增】为整个应用启用CORS

# --- 电机配置 ---
# !!! 您可以在这里修改您的参数 !!!
controller = GripperController(
    port='/dev/ttyACM0',
    baud_rate=921600,
    motor_can_id=0x01,
    motor_master_id=0x11,
    min_angle=-3.78,
    max_angle=-3.05,
    move_torque=0.8
)

# --- API 端点定义 ---
@app.route('/grasp', methods=['POST'])
def api_grasp():
    return jsonify(controller.grasp())

@app.route('/release', methods=['POST'])
def api_release():
    return jsonify(controller.release())

@app.route('/reciprocate', methods=['POST'])
def api_reciprocate():
    return jsonify(controller.reciprocate())

@app.route('/stop', methods=['POST'])
def api_stop():
    return jsonify(controller.stop())

@app.route('/status', methods=['GET'])
def api_status():
    return jsonify(controller.get_status())

# --- 3. 主程序入口 ---
if __name__ == '__main__':
    print("="*50)
    print("夹爪电机 HTTP API 服务器")
    print("="*50)
    # 首先，连接到硬件
    if controller.connect():
        # 如果硬件连接成功，启动Flask Web服务器
        # use_reloader=False 对于多线程和硬件访问的程序是必须的
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    else:
        print("\n无法启动API服务器，因为硬件连接失败。请检查设备和配置。")

    # 当服务器停止时（例如按 Ctrl+C），执行清理
    print("\n服务器正在关闭...")
    controller.disconnect()
    print("程序已退出。")
