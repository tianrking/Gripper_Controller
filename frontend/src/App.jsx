import React, { useState, useEffect, useRef } from 'react';
import './App.css'; // We'll add new styles here

// WebSocket Server URL
const WEBSOCKET_URL = 'ws://127.0.0.1:8765';

// --- Reusable UI Components ---
const StatusCard = ({ title, value, unit, valueClassName = '' }) => (
  <div className="status-card">
    <h3 className="status-card-title">{title}</h3>
    <p className={`status-card-value ${valueClassName}`}>
      {value} <span className="status-card-unit">{unit}</span>
    </p>
  </div>
);

const ConnectionStatus = ({ isConnected }) => (
  <div className="connection-indicator">
    <div className={`dot ${isConnected ? 'dot-connected' : 'dot-disconnected'}`}></div>
    <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
  </div>
);


// --- 【NEW】 Calibration Screen Component ---
const CalibrationScreen = ({ motorStatus, sendCommand }) => {
  const [tempMin, setTempMin] = useState(null);
  const [tempMax, setTempMax] = useState(null);

  useEffect(() => {
    setTempMin(motorStatus.min_angle);
    setTempMax(motorStatus.max_angle);
  }, [motorStatus.min_angle, motorStatus.max_angle]);

  const handlePositionChange = (e) => {
    const newPosition = parseFloat(e.target.value);
    sendCommand('set_position', newPosition);
  };

  const canConfirm = tempMin !== null && tempMax !== null;

  return (
    <div className="calibration-screen">
      <h1 className="calibration-title">Gripper Calibration Required</h1>
      <p className="calibration-subtitle">Please use the slider to move the gripper to its physical limits and set them.</p>
      
      <div className="calibration-step">
        <label htmlFor="calib-slider" className="slider-label">
          1. Manual Position Control
        </label>
        <input
          id="calib-slider"
          type="range"
          min={-5} // Use a wide, safe range for calibration
          max={5}
          step="0.01"
          value={motorStatus.position}
          onChange={handlePositionChange}
          className="slider"
        />
        <p className="current-pos-display">Current Position: {motorStatus.position.toFixed(3)} rad</p>
      </div>

      <div className="calibration-step">
        <p className="slider-label">2. Set Physical Limits</p>
        <div className="calibration-buttons">
          <button onClick={() => sendCommand('set_min')} className="button calib-button">Set as MIN (Closed)</button>
          <button onClick={() => sendCommand('set_max')} className="button calib-button">Set as MAX (Open)</button>
        </div>
        <div className="calibration-readout">
          <p>Recorded Min: <span>{tempMin !== null ? tempMin.toFixed(3) : 'Not Set'}</span></p>
          <p>Recorded Max: <span>{tempMax !== null ? tempMax.toFixed(3) : 'Not Set'}</span></p>
        </div>
      </div>
      
      <div className="calibration-step">
        <p className="slider-label">3. Confirm and Start</p>
        <button onClick={() => sendCommand('confirm_calibration')} disabled={!canConfirm} className={`button confirm-button ${!canConfirm ? 'disabled-button' : ''}`}>
          Confirm Calibration & Begin Operation
        </button>
      </div>
    </div>
  );
};


// --- Main Control Panel Component ---
const MainControlPanel = ({ motorStatus, sendCommand }) => {
  const isActionActive = motorStatus.mode !== 'stopped' && motorStatus.mode !== 'manual';
  const sliderValue = motorStatus.mode === 'manual' ? motorStatus.target_position : motorStatus.position;

  const handlePositionChange = (e) => {
    const newPosition = parseFloat(e.target.value);
    sendCommand('set_position', newPosition);
  };

  const handleTorqueChange = (e) => {
    const newTorque = parseFloat(e.target.value);
    sendCommand('set_torque', newTorque);
  };

  return (
    <div className="dashboard-container">
      <ConnectionStatus isConnected={motorStatus.is_connected} />
      
      {/* Left Control Column */}
      <div className="control-column">
        <div>
          <header className="header">
            <h1 className="title">Gripper Motor Controller</h1>
            <p className="subtitle">Real-time Control Panel via WebSocket</p>
          </header>

          <div className="control-panel">
            <div className="button-grid">
              <button onClick={() => sendCommand('grasp')} disabled={!motorStatus.is_connected || isActionActive} className={`button grasp-button ${(!motorStatus.is_connected || isActionActive) ? 'disabled-button' : ''}`}>
                Grasp
              </button>
              <button onClick={() => sendCommand('release')} disabled={!motorStatus.is_connected || isActionActive} className={`button release-button ${(!motorStatus.is_connected || isActionActive) ? 'disabled-button' : ''}`}>
                Release
              </button>
              <button onClick={() => sendCommand('reciprocate')} disabled={!motorStatus.is_connected || isActionActive} className={`button reciprocate-button ${(!motorStatus.is_connected || isActionActive) ? 'disabled-button' : ''}`}>
                Reciprocate
              </button>
              <button onClick={() => sendCommand('stop')} disabled={!motorStatus.is_connected || motorStatus.mode === 'stopped'} className={`button stop-button ${(!motorStatus.is_connected || motorStatus.mode === 'stopped') ? 'disabled-button' : ''}`}>
                Stop
              </button>
            </div>
            
            <div className="manual-control-section">
              <label htmlFor="position-slider" className="slider-label">
                Manual Position Control: <span className="slider-value">{sliderValue.toFixed(2)} rad</span>
              </label>
              <input
                id="position-slider"
                type="range"
                min={motorStatus.min_angle}
                max={motorStatus.max_angle}
                step="0.01"
                value={sliderValue}
                onChange={handlePositionChange}
                disabled={!motorStatus.is_connected || isActionActive}
                className="slider"
              />
            </div>

            <div className="manual-control-section" style={{marginTop: '1.5rem'}}>
              <label htmlFor="torque-slider" className="slider-label">
                Set Drive Torque: <span className="slider-value">{motorStatus.move_torque.toFixed(2)} Nm</span>
              </label>
              <input
                id="torque-slider"
                type="range"
                min="0.1"
                max="2.0"
                step="0.05"
                value={motorStatus.move_torque}
                onChange={handleTorqueChange}
                disabled={!motorStatus.is_connected}
                className="slider"
              />
            </div>
          </div>
        </div>
        <footer className="info-footer">
          <p>WebSocket Server: {WEBSOCKET_URL}</p>
        </footer>
      </div>

      {/* Right Status Column */}
      <div className="status-column">
        <div className="status-grid">
          <StatusCard 
            title="Current Mode" 
            value={motorStatus.mode} 
            unit=""
            valueClassName={motorStatus.mode !== 'stopped' ? 'text-active' : 'text-inactive'}
          />
          <StatusCard title="Current Position" value={motorStatus.position.toFixed(2)} unit="rad" />
          <StatusCard title="Feedback Torque" value={motorStatus.torque.toFixed(2)} unit="Nm" />
        </div>
      </div>
    </div>
  );
};


// --- Main App Component ---
export default function App() {
  const [motorStatus, setMotorStatus] = useState({
    mode: 'stopped',
    position: 0.0,
    torque: 0.0,
    min_angle: null,
    max_angle: null,
    target_position: 0.0,
    move_torque: 0.8,
    is_calibrated: false,
  });
  const ws = useRef(null);

  useEffect(() => {
    function connect() {
      ws.current = new WebSocket(WEBSOCKET_URL);
      ws.current.onopen = () => {
        setMotorStatus(prev => ({ ...prev, is_connected: true }));
        console.log('WebSocket Connected');
      }
      ws.current.onclose = () => {
        setMotorStatus(prev => ({ ...prev, is_connected: false }));
        setTimeout(connect, 3000);
      };
      ws.current.onerror = (error) => {
        console.error('WebSocket Error:', error);
        ws.current.close();
      };
      ws.current.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'status') {
          setMotorStatus(prev => ({...prev, ...message.data}));
        }
      };
    }
    connect();
    return () => {
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.close();
      }
    };
  }, []);

  const sendCommand = (command, value = null) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      const message = { command };
      if (value !== null) {
        message.value = value;
      }
      ws.current.send(JSON.stringify(message));
    } else {
      console.error('Cannot send command: WebSocket is not connected.');
    }
  };

  return (
    <div className="app-container">
      {motorStatus.is_calibrated ? (
        <MainControlPanel motorStatus={motorStatus} sendCommand={sendCommand} />
      ) : (
        <CalibrationScreen motorStatus={motorStatus} sendCommand={sendCommand} />
      )}
    </div>
  );
}
