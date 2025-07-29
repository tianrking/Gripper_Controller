# Gripper Motor Web Controller

This is a web-based UI project for real-time control of a DM-J4310-2EC motor via WebSocket. The project uses Python for the backend to control the motor hardware and React to build a modern, professional control panel for PC.

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

## ✨ Key Features

- **Startup Calibration**: Guides the user to manually set the physical limits of the gripper, ensuring precise control over the range of motion.
- **Real-time Communication**: Utilizes WebSockets for low-latency, bidirectional communication between the frontend and the hardware.
- **PC-Optimized Dashboard**: A modern and aesthetically pleasing two-column web layout built with React, optimized for desktop access.
- **Multiple Control Modes**:
    - **Automatic Modes**: One-click execution for "Grasp," "Release," and "Reciprocate" actions.
    - **Manual Mode**: Precise, real-time control of the gripper's opening angle by dragging a slider.
- **Real-time Parameter Adjustment**:
    - **Torque Control**: Dynamically adjust the drive torque for torque-based modes directly from the web interface.
- **Live Status Display**: Real-time display of the motor's current mode, position, feedback torque, and other core statuses on the webpage.

## 📂 Project Structure

```
.
├── backend/         # Python backend code
│   ├── DM_CAN.py    # Motor driver library (core)
│   └── server_ws_manual.py  # Main executable (latest WebSocket version)
├── frontend/        # React frontend code
│   ├── src/
│   │   ├── App.jsx  # Main React component
│   │   └── App.css  # Main stylesheet
│   └── package.json # Frontend dependencies
└── README.md        # This document
```

## 🛠️ Prerequisites

Before you begin, ensure your system has the following software installed:

1.  **Python 3.8+**
2.  **Node.js v16+** and **npm**
3.  Hardware Connection: Make sure the Damiao motor is correctly connected to your computer via a serial port.

## 🚀 Installation and Launch

### 1. Clone the Project Repository

Open a new terminal and run the following commands:

```bash
git clone https://github.com/tianrking/SmartClaw-Console
cd SmartClaw-Console 
```

### 2. Backend Configuration

```bash
# Navigate to the backend directory
cd backend

# (Recommended) Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install websockets pyserial numpy
```
**Important Note**: You need to modify the serial port name (`port`) in the `backend/server_ws_manual.py` file to match your hardware.
- **How to find the serial port name?**
  1. Connect your USB-to-CAN device to the computer.
  2. Run the following command in your terminal, which will list all possible serial devices:
     ```bash
     ls /dev | grep -E 'ttyUSB|ttyACM'
     ```
  3. The output of the command (e.g., `ttyACM0` or `ttyUSB0`) is the serial port name you need.
  4. Change the value in the line `port='/dev/ttyACM0'` in the `server_ws_manual.py` file to the name you found.

### 3. Frontend Configuration

```bash
# Navigate back to the project root directory
cd ..
# Navigate to the frontend directory
cd frontend

# Install Node.js dependencies
npm install
```

### 4. Launching the Project

To run this project, you need to start both the backend and frontend services simultaneously. It is recommended to use two separate terminal windows to manage them.

**Terminal 1: Start the Backend Service**

```bash
# Make sure you are in the project's root directory
# Activate the virtual environment (if created)
source backend/venv/bin/activate

# Run the Python WebSocket server
python3 backend/server_ws_manual.py
```
*You should see logs indicating that the server has started and is listening on `ws://0.0.0.0:8765`. Keep this terminal window running.*

**Terminal 2: Start the Frontend Service**

```bash
# Open a new terminal window and make sure you are in the project's root directory
cd frontend

# Run the React development server
npm run dev
```
*You will see a local URL (usually `http://localhost:5173`). Open this address in your browser.*

## 🎮 Operational Workflow

### 1. Hardware Calibration

When you first open the frontend page in your browser, you will be greeted by the **Calibration Screen**. This is a crucial step to ensure that the software's control range accurately matches the gripper's physical limits.

1.  **Manual Control**: Use the "Manual Position Control" slider on the screen to freely move the gripper.
2.  **Set Minimum (Closed Limit)**: Move the gripper to its **fully closed** physical limit, then click the **`Set as MIN (Closed)`** button. You will see the "Recorded Min" field update with the current position reading.
3.  **Set Maximum (Open Limit)**: Move the gripper to its **fully open** physical limit, then click the **`Set as MAX (Open)`** button. The "Recorded Max" field will update.
4.  **Confirm Calibration**: Once both the minimum and maximum values have been set, click the green **`Confirm Calibration & Begin Operation`** button.

After completing these steps, the system will save the calibrated range and automatically transition to the main control panel.

### 2. Main Control Panel

On the main control panel, you can perform all advanced operations, such as automatic grasping, reciprocating motion, and real-time adjustment of torque and position.

## 📡 WebSocket API Specification

- **Server Address**: `ws://127.0.0.1:8765`
- **Communication Format**: JSON

### ➡️ Frontend -> Backend (Sending Commands)

| Command (`command`) | Value (`value`) | Description |
| :--------------- | :----------- | :--- |
| **Calibration Commands** | | |
| `set_min` | `null` | Records the motor's current position as the minimum value (closed limit). |
| `set_max` | `null` | Records the motor's current position as the maximum value (open limit). |
| `confirm_calibration` | `null` | Confirms the calibration, finalizing the setup and proceeding to the main control panel. |
| **Operational Commands** | | |
| `grasp`          | `null`       | Executes the grasp action. |
| `release`        | `null`       | Executes the release action. |
| `reciprocate`    | `null`       | Executes the reciprocating motion. |
| `stop`           | `null`       | Stops all movement. |
| `set_position`   | `float`      | Switches to manual mode and sets the target position. |
| `set_torque`     | `float`      | Sets the drive torque for torque-based modes. |

### ⬅️ Backend -> Frontend (Broadcasting Status)

The backend continuously broadcasts status updates to all connected clients at a frequency of approximately 10Hz.

*Message Format:*
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
    "is_calibrated": true // Critical state: determines which UI screen is displayed
  }
}
