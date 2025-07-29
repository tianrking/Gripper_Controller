# -*- coding: utf-8 -*-
import time
import threading
import sys
import asyncio
import websockets
import json

# 假设 DM_CAN.py 和 serial 在您的环境中可用
try:
    from DM_CAN import *
    import serial
except ImportError as e:
    print(f"错误: 缺少必要的库 ({e})。请确保已安装 pyserial 并且 DM_CAN.py 文件存在。")
    sys.exit(1)

# --- 1. GripperController 类 ---
class GripperController:
    def __init__(self, port, baud_rate, motor_can_id, motor_master_id, min_angle, max_angle, move_torque):
        self.port = port
        self.baud_rate = baud_rate
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.move_torque = move_torque
        self.motor = Motor(DM_Motor_Type.DM4310, motor_can_id, motor_master_id)
        self.serial_device = None
        self.motor_control = None
        self.mode = "stopped"
        self.current_position = 0.0
        self.current_torque = 0.0
        self.is_connected = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)

    def connect(self):
        if self.is_connected: return True
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
        if not self.is_connected: return
        print("正在断开连接...")
        self._stop_event.set()
        self._control_thread.join(timeout=2)
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
        direction = 1
        print("控制循环开始...")
        while not self._stop_event.is_set():
            loop_start_time = time.time()
            pos = self.motor.getPosition()
            tor = self.motor.getTorque()
            if pos is None or tor is None:
                time.sleep(0.02)
                continue
            with self._lock:
                self.current_position = pos
                self.current_torque = tor
                current_mode = self.mode
            tau_cmd = 0.0
            # 【重要】这里的状态检查使用动名词 (grasping, releasing, etc.)
            if current_mode == "grasping":
                tau_cmd = -self.move_torque
                if self.current_position <= self.min_angle: self.set_mode("stop")
            elif current_mode == "releasing":
                tau_cmd = self.move_torque
                if self.current_position >= self.max_angle: self.set_mode("stop")
            elif current_mode == "reciprocating":
                if self.current_position >= self.max_angle: direction = -1
                elif self.current_position <= self.min_angle: direction = 1
                tau_cmd = direction * self.move_torque
            
            self.motor_control.controlMIT(self.motor, kp=0.0, kd=1.0, q=0.0, dq=0.0, tau=tau_cmd)
            time.sleep(max(0, 0.02 - (time.time() - loop_start_time)))
        print("控制循环已停止。")

    # 【修复】修改 set_mode 函数，将指令动词映射到内部状态动名词
    def set_mode(self, command):
        """接收外部指令并设置正确的内部模式。"""
        mode_map = {
            "grasp": "grasping",
            "release": "releasing",
            "reciprocate": "reciprocating",
            "stop": "stopped"
        }
        
        new_mode = mode_map.get(command)

        if new_mode:
            print(f"[WebSocket] 接收到指令: '{command}', 设置模式为: '{new_mode}'")
            with self._lock:
                self.mode = new_mode
        else:
            print(f"[WebSocket] 接收到未知指令: '{command}'")

    def get_status(self):
        with self._lock:
            status = {
                "is_connected": self.is_connected,
                "mode": self.mode,
                "position": float(self.current_position),
                "torque": float(self.current_torque)
            }
        return status

# --- 2. WebSocket 服务器逻辑 ---
CONNECTED_CLIENTS = set()

async def status_broadcaster(controller):
    while True:
        if CONNECTED_CLIENTS:
            status_data = controller.get_status()
            message = json.dumps({"type": "status", "data": status_data})
            await asyncio.gather(
                *[client.send(message) for client in CONNECTED_CLIENTS]
            )
        await asyncio.sleep(0.1)

async def command_handler(websocket, controller):
    CONNECTED_CLIENTS.add(websocket)
    print(f"客户端 {websocket.remote_address} 已连接。")
    try:
        async for message in websocket:
            data = json.loads(message)
            command = data.get("command")
            if command:
                # 直接将收到的指令交给 set_mode 处理
                controller.set_mode(command)
    except websockets.exceptions.ConnectionClosed:
        print(f"客户端 {websocket.remote_address} 已断开。")
    finally:
        CONNECTED_CLIENTS.remove(websocket)

async def main():
    controller = GripperController(
        port='/dev/ttyACM0',
        baud_rate=921600,
        motor_can_id=0x01,
        motor_master_id=0x11,
        min_angle=-3.78,
        max_angle=-3.05,
        move_torque=0.8
    )

    if not controller.connect():
        print("\n无法启动WebSocket服务器，因为硬件连接失败。")
        return

    handler_with_controller = lambda ws: command_handler(ws, controller)

    server_task = websockets.serve(handler_with_controller, "0.0.0.0", 8765)
    broadcast_task = asyncio.create_task(status_broadcaster(controller))

    print("="*50)
    print("夹爪电机 WebSocket 服务器")
    print(f"正在 ws://0.0.0.0:8765 上监听...")
    print("="*50)

    try:
        await asyncio.gather(server_task, broadcast_task)
    finally:
        print("\n服务器正在关闭...")
        controller.disconnect()
        print("程序已退出。")

# --- 3. 主程序入口 ---
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n检测到程序中断 (Ctrl+C)。")
