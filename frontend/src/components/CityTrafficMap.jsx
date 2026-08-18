import React, { useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  LocateFixed,
  Maximize2,
  Minimize2,
  Navigation,
  RotateCcw,
  SlidersHorizontal,
} from 'lucide-react';

const NAGPUR_CENTER = [21.1360, 79.0780];
const NAGPUR_ZONES = [
  { id: 'ALL', label: 'All network' },
  { id: 'CENTRAL', label: 'Central' },
  { id: 'NORTH', label: 'North' },
  { id: 'EAST', label: 'East' },
  { id: 'SOUTH', label: 'South' },
  { id: 'WEST', label: 'West' },
];

const FALLBACK_JUNCTIONS = [
  ['NGP_J01_SITABULDI', 'Sitabuldi Interchange', 21.1458, 79.0882, 'CENTRAL'],
  ['NGP_J02_VARIETIES_SQ', 'Varieties Square', 21.1415, 79.0835, 'CENTRAL'],
  ['NGP_J03_RAHATE_COLONY', 'Rahate Colony Square', 21.1298, 79.0765, 'SOUTH'],
  ['NGP_J04_AJNI_SQ', 'Ajni Square', 21.1185, 79.0712, 'SOUTH'],
  ['NGP_J05_CHHATRAPATI_SQ', 'Chhatrapati Square', 21.1072, 79.0628, 'SOUTH'],
].map(([id, name, lat, lng, zone]) => ({
  id, name, lat, lng, zone, corridor: 'Wardha Road', status: 'live',
  signal: 'PHASE 1', telemetry: 'Offline simulation', approaches: 4,
}));

function getZone(corridorId = '') {
  const corridor = corridorId.replace('CORR_', '');
  if (corridor.includes('NORTH')) return 'NORTH';
  if (corridor.includes('EAST')) return 'EAST';
  if (corridor.includes('SOUTH') || corridor.includes('AIRPORT')) return 'SOUTH';
  if (corridor.includes('WEST')) return 'WEST';
  return 'CENTRAL';
}

function getStatus(junction) {
  if (junction.emergency_active || ['HIGH', 'CRITICAL'].includes(junction.risk_category)) return 'attention';
  if (!junction.last_seen_timestamp) return 'offline';
  return 'live';
}

const STATUS_META = {
  live: { label: 'Live', color: '#29d49a' },
  attention: { label: 'Attention', color: '#ffb547' },
  offline: { label: 'Awaiting feed', color: '#7691a9' },
};

export default function CityTrafficMap({ junctions, selectedJunctionId, onSelectJunction }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeZone, setActiveZone] = useState('ALL');

  const networkJunctions = useMemo(() => {
    const configured = junctions
      .filter((junction) => junction.coordinates?.latitude && junction.coordinates?.longitude)
      .map((junction) => {
        const status = getStatus(junction);
        return {
          id: junction.junction_id,
          name: junction.name,
          lat: junction.coordinates.latitude,
          lng: junction.coordinates.longitude,
          zone: getZone(junction.corridor_id),
          corridor: junction.corridor_id?.replace('CORR_', '').replaceAll('_', ' ') || 'Nagpur network',
          status,
          signal: junction.emergency_active ? 'EMERGENCY PRIORITY' : `PHASE ${junction.active_phase_id || 1}`,
          telemetry: junction.last_seen_timestamp ? 'Telemetry streaming' : 'Awaiting edge feed',
          approaches: junction.approaches_count || 4,
        };
      });
    return configured.length ? configured : FALLBACK_JUNCTIONS;
  }, [junctions]);

  const visibleJunctions = useMemo(
    () => networkJunctions.filter((junction) => activeZone === 'ALL' || junction.zone === activeZone),
    [activeZone, networkJunctions],
  );

  const statusCounts = useMemo(() => networkJunctions.reduce((counts, junction) => {
    counts[junction.status] += 1;
    return counts;
  }, { live: 0, attention: 0, offline: 0 }), [networkJunctions]);

  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return undefined;
    const map = L.map(mapContainerRef.current, {
      center: NAGPUR_CENTER,
      zoom: 12,
      zoomControl: false,
      attributionControl: false,
    });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
    }).addTo(map);
    mapInstanceRef.current = map;
    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return undefined;
    const layer = L.layerGroup().addTo(map);

    visibleJunctions.forEach((junction) => {
      const meta = STATUS_META[junction.status];
      const selected = junction.id === selectedJunctionId;
      const icon = L.divIcon({
        className: 'gati-network-marker',
        html: `<span class="gati-network-marker__halo ${selected ? 'is-selected' : ''}" style="--marker-color:${meta.color}"></span><span class="gati-network-marker__core" style="--marker-color:${meta.color}"></span>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });
      const marker = L.marker([junction.lat, junction.lng], { icon }).addTo(layer);
      marker.bindTooltip(
        `<strong>${junction.name}</strong><br/><span style="color:${meta.color}">${meta.label}</span> · ${junction.signal}<br/><span>${junction.corridor}</span>`,
        { direction: 'top', offset: [0, -14], className: 'map-tooltip' },
      );
      marker.on('click', () => onSelectJunction(junction.id));
    });

    if (visibleJunctions.length > 1) {
      map.fitBounds(visibleJunctions.map((junction) => [junction.lat, junction.lng]), {
        padding: [28, 28], maxZoom: activeZone === 'ALL' ? 12 : 14,
      });
    } else if (visibleJunctions[0]) {
      map.setView([visibleJunctions[0].lat, visibleJunctions[0].lng], 14);
    }
    return () => layer.remove();
  }, [activeZone, onSelectJunction, selectedJunctionId, visibleJunctions]);

  useEffect(() => {
    if (mapInstanceRef.current) setTimeout(() => mapInstanceRef.current?.invalidateSize(), 150);
  }, [isExpanded]);

  const resetMap = () => {
    setActiveZone('ALL');
    mapInstanceRef.current?.setView(NAGPUR_CENTER, 12);
  };

  return (
    <section className="card network-card" aria-label="Nagpur city traffic network">
      <div className="network-card__header">
        <div className="network-title-group">
          <span className="network-title-icon"><Navigation size={16} /></span>
          <div>
            <h2>Nagpur traffic network</h2>
            <p>{networkJunctions.length} junctions · citywide operating view</p>
          </div>
        </div>
        <div className="network-controls" aria-label="Map controls">
          <button type="button" className="map-control" onClick={() => mapInstanceRef.current?.zoomIn()} aria-label="Zoom in">+</button>
          <button type="button" className="map-control" onClick={() => mapInstanceRef.current?.zoomOut()} aria-label="Zoom out">−</button>
          <button type="button" className="map-control map-control--label" onClick={resetMap}><RotateCcw size={13} /> Reset</button>
          <button type="button" className="map-control map-control--label" onClick={() => setIsExpanded((value) => !value)}>
            {isExpanded ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
            {isExpanded ? 'Compact' : 'Expand'}
          </button>
        </div>
      </div>

      <div className="network-summary" aria-label="Network status summary">
        <div><strong>{networkJunctions.length}</strong><span>Configured</span></div>
        <div className="network-summary__live"><strong>{statusCounts.live}</strong><span>Streaming</span></div>
        <div className="network-summary__attention"><strong>{statusCounts.attention}</strong><span>Need attention</span></div>
        <div className="network-summary__offline"><strong>{statusCounts.offline}</strong><span>Awaiting edge feed</span></div>
      </div>

      <div className="network-filter-row">
        <span className="network-filter-label"><SlidersHorizontal size={14} /> View zone</span>
        <div className="network-filter-options" role="group" aria-label="Filter Nagpur network by zone">
          {NAGPUR_ZONES.map((zone) => (
            <button
              type="button"
              key={zone.id}
              className={activeZone === zone.id ? 'network-filter active' : 'network-filter'}
              onClick={() => setActiveZone(zone.id)}
              aria-pressed={activeZone === zone.id}
            >
              {zone.label}
            </button>
          ))}
        </div>
      </div>

      <div className={isExpanded ? 'network-map is-expanded' : 'network-map'} ref={mapContainerRef} />

      <div className="network-footer">
        <div className="network-legend" aria-label="Marker legend">
          {Object.entries(STATUS_META).map(([status, meta]) => (
            <span key={status}><i style={{ background: meta.color }} />{meta.label}</span>
          ))}
        </div>
        <button type="button" className="network-selected" onClick={() => {
          const selected = networkJunctions.find((junction) => junction.id === selectedJunctionId);
          if (selected) mapInstanceRef.current?.flyTo([selected.lat, selected.lng], 14, { duration: 0.7 });
        }}>
          <LocateFixed size={14} /> Locate selected junction
        </button>
      </div>
    </section>
  );
}
