# -*- coding: utf-8 -*-
import time
import threading
import sys
import asyncio
import websockets
import json

# Assume DM_CAN.py and serial are available in your environment
try:
    from DM_CAN import *
    import serial
except ImportError as e:
    print(f"Error: Missing required libraries ({e}). Please ensure pyserial is installed and DM_CAN.py exists.")
    sys.exit(1)

# --- 1. GripperController Class ---
class GripperController:
    # 【MODIFIED】 Initialize min/max angles to None, add calibration state
    def __init__(self, port, baud_rate, motor_can_id, motor_master_id, move_torque):
        self.port = port
        self.baud_rate = baud_rate
        self.motor = Motor(DM_Motor_Type.DM4310, motor_can_id, motor_master_id)
        
        # --- Calibration & State ---
        self.min_angle = None
        self.max_angle = None
        self.is_calibrated = False
        self.move_torque = move_torque
        
        self.serial_device = None
        self.motor_control = None
        self.mode = "stopped"
        self.current_position = 0.0
        self.current_torque = 0.0
        self.is_connected = False
        self.target_position = 0.0
        self.manual_kp = 5.0

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)

    def connect(self):
        if self.is_connected: return True
        try:
            print("Attempting to open serial port...")
            self.serial_device = serial.Serial(self.port, self.baud_rate, timeout=0.5)
            print("Successfully opened serial port.")
            self.motor_control = MotorControl(self.serial_device)
            self.motor_control.addMotor(self.motor)
            print("Switching motor to MIT control mode...")
            if not self.motor_control.switchControlMode(self.motor, Control_Type.MIT):
                raise RuntimeError("Failed to switch motor to MIT mode")
            print("Enabling motor...")
            self.motor_control.enable(self.motor)
            
            initial_pos = self.motor.getPosition()
            self.target_position = initial_pos if initial_pos is not None else 0.0
            self.current_position = self.target_position
            
            print(f"Motor enabled. Initial position: {self.current_position:.2f}")
            self.is_connected = True
            self._stop_event.clear()
            self._control_thread.start()
            print("Control loop thread has started.")
            return True
        except Exception as e:
            print(f"[FATAL ERROR] Connection failed: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        # ... (disconnect logic remains the same)
        if not self.is_connected: return
        print("Disconnecting...")
        self._stop_event.set()
        self._control_thread.join(timeout=2)
        if self.motor_control and self.motor.isEnable:
            print("Disabling motor...")
            self.motor_control.controlMIT(self.motor, 0, 1.0, 0, 0, 0)
            time.sleep(0.05)
            self.motor_control.disable(self.motor)
        if self.serial_device and self.serial_device.is_open:
            self.serial_device.close()
            print("Serial port closed.")
        self.is_connected = False
        print("Safely disconnected.")


    def _control_loop(self):
        direction = 1
        print("Control loop started...")
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
                current_target_pos = self.target_position
                current_move_torque = self.move_torque
                is_calibrated = self.is_calibrated

            # 【MODIFIED】 If not calibrated, only 'manual' and 'stopped' modes are allowed
            if not is_calibrated and current_mode not in ["manual", "stopped"]:
                print(f"Warning: Action '{current_mode}' denied. System not calibrated.")
                self.set_mode("stop") # Force stop
                current_mode = "stopped"

            tau_cmd = 0.0
            if current_mode == "manual":
                self.motor_control.controlMIT(self.motor, kp=self.manual_kp, kd=1.0, q=current_target_pos, dq=0.0, tau=0.0)
                time.sleep(max(0, 0.02 - (time.time() - loop_start_time)))
                continue

            # These modes only run if calibrated
            if current_mode == "grasping":
                tau_cmd = -current_move_torque
                if self.current_position <= self.min_angle: self.set_mode("stop")
            elif current_mode == "releasing":
                tau_cmd = current_move_torque
                if self.current_position >= self.max_angle: self.set_mode("stop")
            elif current_mode == "reciprocating":
                if self.current_position >= self.max_angle: direction = -1
                elif self.current_position <= self.min_angle: direction = 1
                tau_cmd = direction * current_move_torque
            
            self.motor_control.controlMIT(self.motor, kp=0.0, kd=1.0, q=0.0, dq=0.0, tau=tau_cmd)
            time.sleep(max(0, 0.02 - (time.time() - loop_start_time)))
        print("Control loop stopped.")

    def set_move_torque(self, new_torque):
        with self._lock:
            self.move_torque = max(0.1, min(2.0, new_torque))
        print(f"[WebSocket] Drive torque has been set to: {self.move_torque:.2f} Nm")

    # 【MODIFIED】 set_mode now handles calibration commands
    def set_mode(self, command, value=None):
        # --- Calibration Commands ---
        if command == "set_min":
            with self._lock:
                self.min_angle = self.current_position
            print(f"[Calibration] Minimum angle set to: {self.min_angle:.2f}")
            return
        if command == "set_max":
            with self._lock:
                self.max_angle = self.current_position
            print(f"[Calibration] Maximum angle set to: {self.max_angle:.2f}")
            return
        if command == "confirm_calibration":
            with self._lock:
                if self.min_angle is not None and self.max_angle is not None:
                    # Ensure min_angle is always less than max_angle
                    if self.min_angle > self.max_angle:
                        self.min_angle, self.max_angle = self.max_angle, self.min_angle
                    self.is_calibrated = True
                    self.mode = "stopped"
                    print(f"Calibration confirmed! Range: {self.min_angle:.2f} to {self.max_angle:.2f}")
                else:
                    print("Calibration confirmation failed: Min or Max angle not set.")
            return

        # --- Operational Commands ---
        if command == "set_torque" and value is not None:
            self.set_move_torque(float(value))
            return
        if command == "set_position" and value is not None:
            with self._lock:
                self.mode = "manual"
                # If calibrated, clamp to limits. If not, don't clamp.
                min_lim = self.min_angle if self.is_calibrated else -100
                max_lim = self.max_angle if self.is_calibrated else 100
                self.target_position = max(min_lim, min(max_lim, value))
            print(f"[WebSocket] Received command: 'set_position', target: {self.target_position:.2f}")
            return

        mode_map = {"grasp": "grasping", "release": "releasing", "reciprocate": "reciprocating", "stop": "stopped"}
        new_mode = mode_map.get(command)
        if new_mode:
            print(f"[WebSocket] Received command: '{command}', setting mode to: '{new_mode}'")
            with self._lock: self.mode = new_mode
        else:
            print(f"[WebSocket] Received unknown command: '{command}'")

    def get_status(self):
        with self._lock:
            status = {
                "is_connected": self.is_connected,
                "mode": self.mode,
                "position": float(self.current_position),
                "torque": float(self.current_torque),
                "min_angle": float(self.min_angle) if self.min_angle is not None else None,
                "max_angle": float(self.max_angle) if self.max_angle is not None else None,
                "target_position": float(self.target_position),
                "move_torque": float(self.move_torque),
                "is_calibrated": self.is_calibrated, # 【NEW】 Broadcast calibration state
            }
        return status

# --- 2. WebSocket Server Logic (command_handler is now simpler) ---
CONNECTED_CLIENTS = set()
async def status_broadcaster(controller):
    # ... (broadcaster logic remains the same)
    while True:
        if CONNECTED_CLIENTS:
            status_data = controller.get_status()
            message = json.dumps({"type": "status", "data": status_data})
            await asyncio.gather(*[client.send(message) for client in CONNECTED_CLIENTS])
        await asyncio.sleep(0.1)


async def command_handler(websocket, controller):
    CONNECTED_CLIENTS.add(websocket)
    print(f"Client {websocket.remote_address} connected.")
    try:
        status_data = controller.get_status()
        await websocket.send(json.dumps({"type": "status", "data": status_data}))
        async for message in websocket:
            data = json.loads(message)
            command = data.get("command")
            value = data.get("value")
            if command:
                controller.set_mode(command, value)
    except websockets.exceptions.ConnectionClosed:
        print(f"Client {websocket.remote_address} disconnected.")
    finally:
        CONNECTED_CLIENTS.remove(websocket)

async def main():
    # 【MODIFIED】 Controller is now initialized without min/max angles
    controller = GripperController(
        port='/dev/ttyACM0',
        baud_rate=921600,
        motor_can_id=0x01,
        motor_master_id=0x11,
        move_torque=0.8
    )
    if not controller.connect():
        print("\nCould not start WebSocket server due to hardware connection failure.")
        return
    handler_with_controller = lambda ws: command_handler(ws, controller)
    server_task = websockets.serve(handler_with_controller, "0.0.0.0", 8765)
    broadcast_task = asyncio.create_task(status_broadcaster(controller))
    print("="*50)
    print("Gripper Motor WebSocket Server")
    print(f"Listening on ws://0.0.0.0:8765...")
    print("="*50)
    try:
        await asyncio.gather(server_task, broadcast_task)
    finally:
        print("\nServer is shutting down...")
        controller.disconnect()
        print("Program exited.")

# --- 3. Main Program Entry Point ---
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected (Ctrl+C).")