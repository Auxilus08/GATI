import React, { useState } from 'react';
import { MapPin, Navigation, Compass, Layers, ShieldCheck, Activity } from 'lucide-react';

export default function CityTrafficMap({
  junctions,
  selectedJunctionId,
  onSelectJunction,
}) {
  const [mapLayer, setMapLayer] = useState('traffic'); // 'traffic' | 'corridor' | 'satellite'

  // Nagpur Wardha Road Arterial Corridor Coordinates (Mapped to 800x480 SVG Canvas)
  const NAGPUR_JUNCTION_NODES = [
    {
      id: 'NGP_J01_SITABULDI',
      name: 'Sitabuldi Interchange',
      area: 'Central Business District & Metro Interchange',
      x: 180,
      y: 120,
      trafficLevel: 'Heavy (38 Vehicles)',
      status: 'GREEN (32s Left)',
      color: '#10b981',
      crowdPCU: 24.5,
    },
    {
      id: 'NGP_J02_VARIETIES_SQ',
      name: 'Varieties Square',
      area: 'Cinema & Commercial Zone (450m ahead)',
      x: 320,
      y: 180,
      trafficLevel: 'Moderate (22 Vehicles)',
      status: 'RED (14s Left)',
      color: '#ef4444',
      crowdPCU: 18.2,
    },
    {
      id: 'NGP_J03_RAHATE_COLONY',
      name: 'Rahate Colony Square',
      area: 'Medical College & Residential Link (+600m)',
      x: 460,
      y: 250,
      trafficLevel: 'Moderate (19 Vehicles)',
      status: 'GREEN (28s Left)',
      color: '#10b981',
      crowdPCU: 15.0,
    },
    {
      id: 'NGP_J04_AJNI_SQ',
      name: 'Ajni Square',
      area: 'Railway Station & Flyover Junction (+800m)',
      x: 600,
      y: 320,
      trafficLevel: 'Heavy (34 Vehicles)',
      status: 'RED (22s Left)',
      color: '#ef4444',
      crowdPCU: 28.4,
    },
    {
      id: 'NGP_J05_CHHATRAPATI_SQ',
      name: 'Chhatrapati Square',
      area: 'Ring Road & Airport Arterial Highway (+950m)',
      x: 720,
      y: 400,
      trafficLevel: 'Moderate (21 Vehicles)',
      status: 'GREEN (35s Left)',
      color: '#10b981',
      crowdPCU: 17.5,
    },
  ];

  return (
    <div className="card" style={{ padding: '20px', marginBottom: '24px', backgroundColor: '#0b1322', border: '1px solid #1e293b' }}>
      {/* Map Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Navigation size={18} className="text-blue" />
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
              Live Nagpur City Traffic Map (Wardha Road Smart Corridor)
            </h3>
          </div>
          <p style={{ fontSize: '12px', color: '#94a3b8', margin: '3px 0 0 0' }}>
            Click any junction circle on the map to switch cameras and see live traffic conditions.
          </p>
        </div>

        {/* Map Filter Controls in Plain Words */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setMapLayer('traffic')}
            style={{
              backgroundColor: mapLayer === 'traffic' ? 'rgba(56, 189, 248, 0.2)' : '#1e293b',
              border: `1px solid ${mapLayer === 'traffic' ? '#38bdf8' : '#334155'}`,
              color: mapLayer === 'traffic' ? '#38bdf8' : '#cbd5e1',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            🚦 Live Signals
          </button>
          <button
            onClick={() => setMapLayer('corridor')}
            style={{
              backgroundColor: mapLayer === 'corridor' ? 'rgba(52, 211, 153, 0.2)' : '#1e293b',
              border: `1px solid ${mapLayer === 'corridor' ? '#34d399' : '#334155'}`,
              color: mapLayer === 'corridor' ? '#34d399' : '#cbd5e1',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            🌊 Green Wave Route
          </button>
        </div>
      </div>

      {/* Interactive Map Canvas Container */}
      <div style={{ position: 'relative', width: '100%', height: '340px', backgroundColor: '#070d18', borderRadius: '10px', overflow: 'hidden', border: '1px solid #1e293b' }}>
        <svg viewBox="0 0 840 480" style={{ width: '100%', height: '100%' }}>
          {/* Map Grid Lines */}
          <defs>
            <pattern id="mapGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1" />
            </pattern>
            {/* Pulsing Signal Glow Filters */}
            <filter id="greenGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="redGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          <rect width="840" height="480" fill="#070d18" />
          <rect width="840" height="480" fill="url(#mapGrid)" />

          {/* Nagpur City Landmarks (Waterbody / Ambazari / Railway / Metro) */}
          {/* Maharajbagh Green Area */}
          <path d="M 60,80 Q 140,50 160,110 T 110,180 Z" fill="rgba(16, 185, 129, 0.06)" stroke="rgba(16, 185, 129, 0.2)" strokeWidth="1" />
          <text x="90" y="110" fill="rgba(52, 211, 153, 0.4)" fontSize="11" fontWeight="600">🌳 Maharajbagh Zoo & Park</text>

          {/* Nagpur Metro Viaduct Line (Orange Line running along Wardha Road) */}
          <path
            d="M 180,120 L 320,180 L 460,250 L 600,320 L 720,400"
            fill="none"
            stroke="rgba(249, 115, 22, 0.35)"
            strokeWidth="8"
            strokeDasharray="6 4"
          />
          <text x="630" y="385" fill="rgba(249, 115, 22, 0.7)" fontSize="10" fontWeight="600">🚇 Nagpur Metro (Aqua/Orange Line)</text>

          {/* Major Connecting Secondary Roads */}
          {/* Central Avenue East-West */}
          <line x1="20" y1="120" x2="360" y2="120" stroke="rgba(255,255,255,0.08)" strokeWidth="10" />
          <text x="40" y="135" fill="#64748b" fontSize="10">Central Avenue (Railway Station Link)</text>

          {/* North Ambazari Road Cross Link */}
          <line x1="200" y1="290" x2="520" y2="200" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
          <text x="240" y="275" fill="#64748b" fontSize="9">North Ambazari Road</text>

          {/* Ring Road at Chhatrapati Square */}
          <line x1="560" y1="460" x2="820" y2="330" stroke="rgba(255,255,255,0.08)" strokeWidth="12" />
          <text x="730" y="445" fill="#64748b" fontSize="10">Nagpur Outer Ring Road</text>

          {/* Main Arterial Road Highway (Wardha Road Corridor) */}
          <path
            d="M 180,120 L 320,180 L 460,250 L 600,320 L 720,400"
            fill="none"
            stroke="#1e293b"
            strokeWidth="20"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Active Traffic Highway Center Line */}
          <path
            d="M 180,120 L 320,180 L 460,250 L 600,320 L 720,400"
            fill="none"
            stroke={mapLayer === 'corridor' ? '#10b981' : '#38bdf8'}
            strokeWidth="6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Animated Green Wave Pulse Particles along Wardha Road */}
          <circle cx="250" cy="150" r="4" fill="#ffffff">
            <animate attributeName="opacity" values="0.2;1;0.2" dur="1.5s" repeatCount="indefinite" />
          </circle>
          <circle cx="390" cy="215" r="4" fill="#ffffff">
            <animate attributeName="opacity" values="0.2;1;0.2" dur="1.5s" begin="0.3s" repeatCount="indefinite" />
          </circle>
          <circle cx="530" cy="285" r="4" fill="#ffffff">
            <animate attributeName="opacity" values="0.2;1;0.2" dur="1.5s" begin="0.6s" repeatCount="indefinite" />
          </circle>
          <circle cx="660" cy="360" r="4" fill="#ffffff">
            <animate attributeName="opacity" values="0.2;1;0.2" dur="1.5s" begin="0.9s" repeatCount="indefinite" />
          </circle>

          {/* Interactive Junction Signal Pins */}
          {NAGPUR_JUNCTION_NODES.map((node) => {
            const isSelected = selectedJunctionId === node.id;
            const isGreen = node.status.includes('GREEN');

            return (
              <g
                key={node.id}
                onClick={() => onSelectJunction(node.id)}
                style={{ cursor: 'pointer' }}
              >
                {/* Outer Selection Highlight Ring */}
                {isSelected && (
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r="28"
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="3"
                    strokeDasharray="4 3"
                  >
                    <animateTransform
                      attributeName="transform"
                      type="rotate"
                      from={`0 ${node.x} ${node.y}`}
                      to={`360 ${node.x} ${node.y}`}
                      dur="8s"
                      repeatCount="indefinite"
                    />
                  </circle>
                )}

                {/* Outer Glow Halo */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="18"
                  fill={isGreen ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'}
                />

                {/* Main Node Circle */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="12"
                  fill={isGreen ? '#10b981' : '#ef4444'}
                  stroke="#ffffff"
                  strokeWidth="2.5"
                  filter={isGreen ? 'url(#greenGlow)' : 'url(#redGlow)'}
                />

                {/* Signal Text Badge inside node */}
                <text
                  x={node.x}
                  y={node.y + 4}
                  fill="#ffffff"
                  fontSize="9"
                  fontWeight="bold"
                  textAnchor="middle"
                >
                  {isGreen ? 'GO' : 'STOP'}
                </text>

                {/* Junction Name Label Card */}
                <rect
                  x={node.x - 65}
                  y={node.y - 42}
                  width="130"
                  height="26"
                  rx="5"
                  fill={isSelected ? '#0284c7' : '#1e293b'}
                  stroke={isSelected ? '#38bdf8' : '#334155'}
                  strokeWidth="1"
                />
                <text
                  x={node.x}
                  y={node.y - 25}
                  fill="#f8fafc"
                  fontSize="10"
                  fontWeight="bold"
                  textAnchor="middle"
                >
                  {node.name}
                </text>

                {/* Traffic Level Subtitle below node */}
                <rect
                  x={node.x - 55}
                  y={node.y + 20}
                  width="110"
                  height="16"
                  rx="3"
                  fill="rgba(0,0,0,0.7)"
                />
                <text
                  x={node.x}
                  y={node.y + 32}
                  fill={isGreen ? '#34d399' : '#f87171'}
                  fontSize="9"
                  fontWeight="600"
                  textAnchor="middle"
                >
                  {node.trafficLevel}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Map Legend (Bottom Right Overlay in Simple Words) */}
        <div style={{ position: 'absolute', bottom: '12px', right: '12px', backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid #334155', borderRadius: '8px', padding: '10px 14px', backdropFilter: 'blur(4px)' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#f8fafc', marginBottom: '6px' }}>
            Map Traffic Signals:
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#34d399' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10b981' }} />
              <strong>GREEN:</strong> Vehicles Moving Freely
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f87171' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#ef4444' }} />
              <strong>RED:</strong> Waiting at Red Light
            </div>
          </div>
        </div>

        {/* Selected Junction Callout (Top Left Overlay) */}
        <div style={{ position: 'absolute', top: '12px', left: '12px', backgroundColor: 'rgba(2, 132, 199, 0.15)', border: '1px solid #0284c7', borderRadius: '6px', padding: '6px 12px' }}>
          <span style={{ fontSize: '11px', color: '#38bdf8', fontWeight: 600 }}>
            📍 Selected Junction on Map: <strong>{NAGPUR_JUNCTION_NODES.find((n) => n.id === selectedJunctionId)?.name || 'Sitabuldi'}</strong>
          </span>
        </div>
      </div>
    </div>
  );
}
