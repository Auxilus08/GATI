import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Navigation, Maximize2, Minimize2, RotateCcw, Layers } from 'lucide-react';

export default function CityTrafficMap({
  junctions,
  selectedJunctionId,
  onSelectJunction,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef({});
  const polylineRef = useRef(null);
  const [isExpanded, setIsExpanded] = useState(false);

  // Exact GPS Coordinates for Nagpur Smart City Wardha Road Corridor Intersections
  const NAGPUR_JUNCTION_COORDS = [
    {
      id: 'NGP_J01_SITABULDI',
      name: 'Sitabuldi Interchange',
      lat: 21.1458,
      lng: 79.0882,
      traffic: '38 Vehicles',
      signal: 'GREEN (32s)',
      color: '#10b981',
      description: 'Major Interchange • Wardha Rd & Central Ave',
    },
    {
      id: 'NGP_J02_VARIETIES_SQ',
      name: 'Varieties Square',
      lat: 21.1415,
      lng: 79.0835,
      traffic: '22 Vehicles',
      signal: 'RED (14s)',
      color: '#ef4444',
      description: 'Commercial Arterial (+450m)',
    },
    {
      id: 'NGP_J03_RAHATE_COLONY',
      name: 'Rahate Colony Square',
      lat: 21.1298,
      lng: 79.0765,
      traffic: '19 Vehicles',
      signal: 'GREEN (28s)',
      color: '#10b981',
      description: 'Medical & Hospital Zone (+1050m)',
    },
    {
      id: 'NGP_J04_AJNI_SQ',
      name: 'Ajni Square',
      lat: 21.1185,
      lng: 79.0712,
      traffic: '34 Vehicles',
      signal: 'RED (22s)',
      color: '#ef4444',
      description: 'Railway Station & Flyover (+1850m)',
    },
    {
      id: 'NGP_J05_CHHATRAPATI_SQ',
      name: 'Chhatrapati Square',
      lat: 21.1072,
      lng: 79.0628,
      traffic: '21 Vehicles',
      signal: 'GREEN (35s)',
      color: '#10b981',
      description: 'Outer Ring Rd & Airport Arterial (+2800m)',
    },
  ];

  // Initialize Real Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return; // already initialized

    const map = L.map(mapContainerRef.current, {
      center: [21.1265, 79.0755], // Centered over Nagpur Wardha Road Corridor
      zoom: 13,
      zoomControl: false, // We provide custom styled zoom buttons
      attributionControl: false,
    });

    // Dark Matter Map Tiles with fallback
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
    }).addTo(map);

    // Corridor Arterial Polyline connecting the 5 junctions along Wardha Road
    const corridorPoints = NAGPUR_JUNCTION_COORDS.map((j) => [j.lat, j.lng]);
    const polyline = L.polyline(corridorPoints, {
      color: '#0284c7',
      weight: 5,
      opacity: 0.8,
      dashArray: '8, 8',
    }).addTo(map);
    polylineRef.current = polyline;

    // Add Junction Markers
    NAGPUR_JUNCTION_COORDS.forEach((j) => {
      const isSelected = j.id === selectedJunctionId;
      const isGreen = j.signal.includes('GREEN');

      const customIcon = L.divIcon({
        className: 'custom-leaflet-marker',
        html: `
          <div style="
            position: relative;
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
          ">
            <div style="
              position: absolute;
              width: ${isSelected ? '32px' : '22px'};
              height: ${isSelected ? '32px' : '22px'};
              border-radius: 50%;
              background: ${isGreen ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'};
              border: ${isSelected ? '2px solid #38bdf8' : 'none'};
              animation: ${isSelected ? 'pulse 2s infinite' : 'none'};
            "></div>
            <div style="
              width: 14px;
              height: 14px;
              border-radius: 50%;
              background: ${isGreen ? '#10b981' : '#ef4444'};
              border: 2px solid #ffffff;
              box-shadow: 0 0 10px ${isGreen ? '#10b981' : '#ef4444'};
            "></div>
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([j.lat, j.lng], { icon: customIcon }).addTo(map);
      marker.bindTooltip(
        `<strong>${j.name}</strong><br/><span style="color:${j.color}">${j.signal}</span> • ${j.traffic}`,
        { direction: 'top', offset: [0, -10], className: 'map-tooltip' }
      );

      marker.on('click', () => {
        onSelectJunction(j.id);
      });

      markersRef.current[j.id] = marker;
    });

    mapInstanceRef.current = map;

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update selected junction pan & marker highlight
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const selected = NAGPUR_JUNCTION_COORDS.find((j) => j.id === selectedJunctionId);
    if (selected) {
      mapInstanceRef.current.panTo([selected.lat, selected.lng], { animate: true, duration: 0.8 });
    }
  }, [selectedJunctionId]);

  // Handle Container Resize
  useEffect(() => {
    if (mapInstanceRef.current) {
      setTimeout(() => {
        mapInstanceRef.current.invalidateSize();
      }, 250);
    }
  }, [isExpanded]);

  const handleZoomIn = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.zoomIn();
  };

  const handleZoomOut = () => {
    if (mapInstanceRef.current) mapInstanceRef.current.zoomOut();
  };

  const handleResetCorridor = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([21.1265, 79.0755], 13);
    }
  };

  return (
    <div
      className="card"
      style={{
        padding: '14px 16px',
        marginBottom: 0,
        backgroundColor: '#0a101d',
        border: '1px solid #1e293b',
        borderRadius: '12px',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      {/* Sleek Compact Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Navigation size={15} className="text-blue" />
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
            Real Nagpur City Map (Wardha Road Smart Corridor)
          </span>
          <span style={{ fontSize: '11px', color: '#64748b' }}>• Real GPS Coordinates</span>
        </div>

        {/* Compact Controls: Zoom, Reset, and Expand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {/* Zoom Buttons */}
          <button
            onClick={handleZoomIn}
            title="Zoom In"
            style={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              color: '#f8fafc',
              width: '26px',
              height: '26px',
              borderRadius: '5px',
              fontSize: '15px',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            +
          </button>
          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            style={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              color: '#f8fafc',
              width: '26px',
              height: '26px',
              borderRadius: '5px',
              fontSize: '15px',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            −
          </button>

          {/* Reset Corridor Button */}
          <button
            onClick={handleResetCorridor}
            title="Center Corridor"
            style={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              color: '#38bdf8',
              padding: '0 8px',
              height: '26px',
              borderRadius: '5px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <RotateCcw size={11} /> Reset
          </button>

          {/* Toggle Expand / Compact Height */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Compact View' : 'Expand Map'}
            style={{
              backgroundColor: isExpanded ? 'rgba(56, 189, 248, 0.15)' : '#1e293b',
              border: `1px solid ${isExpanded ? '#38bdf8' : '#334155'}`,
              color: isExpanded ? '#38bdf8' : '#cbd5e1',
              padding: '0 8px',
              height: '26px',
              borderRadius: '5px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            {isExpanded ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
            {isExpanded ? 'Compact' : 'Expand'}
          </button>
        </div>
      </div>

      {/* Real Map Container - Sleek height (180px compact, 340px expanded) */}
      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: isExpanded ? '340px' : '180px',
          borderRadius: '8px',
          overflow: 'hidden',
          border: '1px solid #1e293b',
          transition: 'height 0.3s ease',
          backgroundColor: '#070d18',
        }}
      />

      {/* Sleek Mini-Bar with Quick Jump Chips */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginTop: '8px',
          overflowX: 'auto',
          paddingBottom: '2px',
        }}
      >
        <span style={{ fontSize: '11px', color: '#64748b', whiteSpace: 'nowrap' }}>Jump to:</span>
        {NAGPUR_JUNCTION_COORDS.map((j) => {
          const isSelected = selectedJunctionId === j.id;
          const isGreen = j.signal.includes('GREEN');
          return (
            <button
              key={j.id}
              onClick={() => onSelectJunction(j.id)}
              style={{
                backgroundColor: isSelected ? 'rgba(2, 132, 199, 0.25)' : '#131d2e',
                border: `1px solid ${isSelected ? '#38bdf8' : '#1e293b'}`,
                color: isSelected ? '#38bdf8' : '#94a3b8',
                padding: '3px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: isSelected ? 700 : 500,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: isGreen ? '#10b981' : '#ef4444',
                }}
              />
              {j.name.replace(' Square', ' Sq').replace(' Interchange', '')}
            </button>
          );
        })}
      </div>
    </div>
  );
}
