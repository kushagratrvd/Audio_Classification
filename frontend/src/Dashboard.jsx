// Dashboard.jsx
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import './Dashboard.css';

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
L.Marker.prototype.options.icon = DefaultIcon;

const Dashboard = ({ onLogout }) => {
  const [incidents, setIncidents] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(
          'http://127.0.0.1:8000/api/v1/incidents',
          {
            headers: {
              'admin-secret': 'police123',
            },
          }
        );
        const sortedData = response.data.sort((a, b) => b.id - a.id);
        setIncidents(sortedData);
      } catch (error) {
        console.error('Access Denied or Error:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityClass = (sev) => {
    if (sev === 'High') return 'severity-pill severity-high';
    if (sev === 'Medium') return 'severity-pill severity-medium';
    return 'severity-pill severity-low';
  };

  return (
    <div className="dashboard-root">
      {/* HEADER */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <div className="dashboard-logo">🚓</div>
          <div>
            <h2 className="dashboard-title">Responder Dashboard</h2>
            <p className="dashboard-subtitle">Real-time Monitoring</p>
          </div>
          <div className="dashboard-badge">
            <span className="dashboard-badge-dot" />
            {incidents.length}
          </div>
        </div>

        <button onClick={onLogout} className="dashboard-logout-btn">
          Logout
        </button>
      </div>

      {/* MAP SECTION */}
      <div className="dashboard-map-section">
        <MapContainer
          center={[20.5937, 78.9629]}
          zoom={5}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="© OpenStreetMap contributors"
          />
          {incidents.map((incident) => (
            <Marker
              key={incident.id}
              position={[
                parseFloat(incident.latitude),
                parseFloat(incident.longitude),
              ]}
            >
              <Popup>
                <div className="popup-content">
                  <strong className="popup-title">
                    #{incident.id} - {incident.severity} Risk
                  </strong>
                  <br />
                  <span className="popup-time">
                    {new Date(incident.timestamp).toLocaleString()}
                  </span>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      {/* LOGS SECTION */}
      <div className="dashboard-logs-section">
        <div className="logs-header">
          <h3 className="logs-title">📋 Recent Alerts</h3>
          <span className="logs-count">{incidents.length}</span>
        </div>

        <div className="logs-table-wrapper">
          <table className="logs-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Time</th>
                <th>Severity</th>
                <th>Location</th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((inc) => (
                <tr key={inc.id} className="logs-row">
                  <td className="logs-id">#{inc.id}</td>
                  <td className="logs-time">
                    {new Date(inc.timestamp).toLocaleTimeString()}
                  </td>
                  <td>
                    <span className={getSeverityClass(inc.severity)}>
                      {inc.severity}
                    </span>
                  </td>
                  <td className="logs-location">
                    {inc.latitude}, {inc.longitude}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
