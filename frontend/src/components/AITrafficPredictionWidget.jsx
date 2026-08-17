import React, { useState } from 'react';
import {
  TrendingUp,
  Cloud,
  Thermometer,
  Wind,
  Clock,
  AlertTriangle,
  CheckCircle2,
  BarChart2,
  Calendar,
  Sparkles,
} from 'lucide-react';

export default function AITrafficPredictionWidget() {
  const [timeframe, setTimeframe] = useState('today'); // 'today' | 'week'
  const [selectedHour, setSelectedHour] = useState('09:00');
  const [selectedDay, setSelectedDay] = useState('Mon');

  // Hourly traffic forecast data for Today
  const HOURLY_FORECAST = [
    { time: '09:00', percent: 95, status: 'PEAK', type: 'high', pcu: 48, note: 'Morning Rush: Wardha Rd to Sitabuldi' },
    { time: '10:00', percent: 81, status: 'PEAK', type: 'high', pcu: 41, note: 'Office Commute Inflow' },
    { time: '11:00', percent: 47, status: 'MODERATE', type: 'med', pcu: 23, note: 'Fluid Inter-City Flow' },
    { time: '12:00', percent: 48, status: 'MODERATE', type: 'med', pcu: 24, note: 'Steady Mid-Day Commerce' },
    { time: '13:00', percent: 59, status: 'MODERATE', type: 'med', pcu: 29, note: 'Lunch Hour Surge' },
    { time: '14:00', percent: 57, status: 'MODERATE', type: 'med', pcu: 28, note: 'Steady Flow' },
    { time: '15:00', percent: 47, status: 'MODERATE', type: 'med', pcu: 23, note: 'Optimal Travel Window' },
    { time: '16:00', percent: 57, status: 'MODERATE', type: 'med', pcu: 28, note: 'Early School & College Exit' },
    { time: '17:00', percent: 92, status: 'PEAK', type: 'high', pcu: 46, note: 'Evening Peak Congestion Surge' },
    { time: '18:00', percent: 89, status: 'PEAK', type: 'high', pcu: 45, note: 'Central Ave & Sitabuldi Commercial Rush' },
    { time: '19:00', percent: 86, status: 'PEAK', type: 'high', pcu: 43, note: 'Outbound Arterial Rush' },
    { time: '20:00', percent: 95, status: 'PEAK', type: 'high', pcu: 48, note: 'Dinner & Market Peak Inflow' },
  ];

  // 7-Day Weekly traffic forecast data
  const WEEKLY_FORECAST = [
    { day: 'Mon', date: '18 Aug', percent: 92, status: 'PEAK', type: 'high', pcu: 46, note: 'Monday Morning City-Wide Resumption' },
    { day: 'Tue', date: '19 Aug', percent: 78, status: 'MODERATE', type: 'med', pcu: 38, note: 'Normal Mid-Week Volume' },
    { day: 'Wed', date: '20 Aug', percent: 74, status: 'MODERATE', type: 'med', pcu: 36, note: 'Smooth Commercial Transit' },
    { day: 'Thu', date: '21 Aug', percent: 82, status: 'PEAK', type: 'high', pcu: 40, note: 'Pre-Weekend Logistics Movement' },
    { day: 'Fri', date: '22 Aug', percent: 96, status: 'PEAK', type: 'high', pcu: 49, note: 'Friday Evening Rush & Weekend Getaway' },
    { day: 'Sat', date: '23 Aug', percent: 68, status: 'MODERATE', type: 'med', pcu: 33, note: 'Retail Market Surge at Sitabuldi' },
    { day: 'Sun', date: '24 Aug', percent: 42, status: 'LOW', type: 'low', pcu: 20, note: 'Light Leisure Traffic along Wardha Rd' },
  ];

  const currentItem = timeframe === 'today'
    ? HOURLY_FORECAST.find((h) => h.time === selectedHour) || HOURLY_FORECAST[0]
    : WEEKLY_FORECAST.find((d) => d.day === selectedDay) || WEEKLY_FORECAST[0];

  return (
    <div
      className="card"
      style={{
        backgroundColor: '#0c1424',
        border: '1px solid #1e2d45',
        borderRadius: '14px',
        padding: '20px 24px',
        color: '#f8fafc',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.45)',
        marginBottom: '24px',
      }}
    >
      {/* ─── Top Header: Title & Today/Week Switcher ─── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <TrendingUp size={22} style={{ color: '#38bdf8' }} />
          <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0, color: '#f8fafc', letterSpacing: '0.2px' }}>
            AI Traffic Prediction
          </h2>
        </div>

        {/* Timeframe Toggle Buttons (Today / Week) */}
        <div
          style={{
            display: 'flex',
            backgroundColor: '#162238',
            borderRadius: '8px',
            padding: '3px',
            border: '1px solid #233554',
          }}
        >
          <button
            onClick={() => setTimeframe('today')}
            style={{
              backgroundColor: timeframe === 'today' ? '#6366f1' : 'transparent',
              color: timeframe === 'today' ? '#ffffff' : '#94a3b8',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 16px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            Today
          </button>
          <button
            onClick={() => setTimeframe('week')}
            style={{
              backgroundColor: timeframe === 'week' ? '#6366f1' : 'transparent',
              color: timeframe === 'week' ? '#ffffff' : '#94a3b8',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 16px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            Week
          </button>
        </div>
      </div>

      {/* ─── Weather Context Bar ─── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#101a2f',
          border: '1px solid #1e2f4d',
          borderRadius: '10px',
          padding: '10px 16px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', fontSize: '13px', fontWeight: 600 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8' }}>
            <Cloud size={16} />
            <span>Cloudy</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f87171' }}>
            <Thermometer size={16} />
            <span>32°C</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#34d399' }}>
            <Wind size={16} />
            <span>16 km/h</span>
          </div>
        </div>
        <span style={{ fontSize: '12px', color: '#94a3b8', fontStyle: 'italic' }}>
          Weather affects traffic patterns
        </span>
      </div>

      {/* ─── Forecast Section (Hourly / Weekly Timeline) ─── */}
      <div style={{ marginBottom: '22px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '12px',
            fontWeight: 700,
            color: '#94a3b8',
            marginBottom: '14px',
            letterSpacing: '0.6px',
          }}
        >
          <Clock size={14} />
          <span>{timeframe === 'today' ? 'HOURLY FORECAST' : '7-DAY WEEKLY FORECAST'}</span>
        </div>

        {/* Horizontal Timeline Scroll Container */}
        <div
          style={{
            display: 'flex',
            gap: '12px',
            overflowX: 'auto',
            paddingBottom: '8px',
            scrollbarWidth: 'thin',
          }}
        >
          {timeframe === 'today'
            ? HOURLY_FORECAST.map((item) => {
                const isSelected = selectedHour === item.time;
                const isPeak = item.type === 'high';

                return (
                  <div
                    key={item.time}
                    onClick={() => setSelectedHour(item.time)}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      cursor: 'pointer',
                      padding: '8px 10px',
                      borderRadius: '12px',
                      minWidth: '58px',
                      border: isSelected ? '1.5px solid #38bdf8' : '1.5px solid transparent',
                      backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.08)' : 'transparent',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    {/* Time Label */}
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: isSelected ? 700 : 500,
                        color: isSelected ? '#38bdf8' : '#94a3b8',
                        marginBottom: '8px',
                      }}
                    >
                      {item.time}
                    </span>

                    {/* Capsule / Circle Indicator */}
                    {isPeak ? (
                      <div
                        style={{
                          width: '26px',
                          height: '46px',
                          borderRadius: '14px',
                          backgroundColor: '#f472b6',
                          boxShadow: '0 0 12px rgba(244, 114, 182, 0.4)',
                          marginBottom: '8px',
                        }}
                      />
                    ) : (
                      <div
                        style={{
                          width: '26px',
                          height: '26px',
                          borderRadius: '50%',
                          backgroundColor: '#facc15',
                          boxShadow: '0 0 10px rgba(250, 204, 21, 0.3)',
                          margin: '10px 0 10px 0',
                        }}
                      />
                    )}

                    {/* Percentage Label */}
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 700,
                        color: isPeak ? '#f472b6' : '#facc15',
                      }}
                    >
                      {item.percent}%
                    </span>

                    {/* PEAK tag */}
                    {item.status === 'PEAK' && (
                      <span
                        style={{
                          fontSize: '9px',
                          fontWeight: 700,
                          color: '#f472b6',
                          letterSpacing: '0.4px',
                          marginTop: '2px',
                        }}
                      >
                        PEAK
                      </span>
                    )}
                  </div>
                );
              })
            : WEEKLY_FORECAST.map((item) => {
                const isSelected = selectedDay === item.day;
                const isPeak = item.type === 'high';
                const isLow = item.type === 'low';

                return (
                  <div
                    key={item.day}
                    onClick={() => setSelectedDay(item.day)}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      cursor: 'pointer',
                      padding: '8px 12px',
                      borderRadius: '12px',
                      minWidth: '68px',
                      border: isSelected ? '1.5px solid #38bdf8' : '1.5px solid transparent',
                      backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.08)' : 'transparent',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: isSelected ? 700 : 500,
                        color: isSelected ? '#38bdf8' : '#94a3b8',
                        marginBottom: '2px',
                      }}
                    >
                      {item.day}
                    </span>
                    <span style={{ fontSize: '10px', color: '#64748b', marginBottom: '8px' }}>
                      {item.date}
                    </span>

                    {/* Capsule / Circle Indicator */}
                    {isPeak ? (
                      <div
                        style={{
                          width: '26px',
                          height: '46px',
                          borderRadius: '14px',
                          backgroundColor: '#f472b6',
                          boxShadow: '0 0 12px rgba(244, 114, 182, 0.4)',
                          marginBottom: '8px',
                        }}
                      />
                    ) : isLow ? (
                      <div
                        style={{
                          width: '26px',
                          height: '26px',
                          borderRadius: '50%',
                          backgroundColor: '#34d399',
                          boxShadow: '0 0 10px rgba(52, 211, 153, 0.3)',
                          margin: '10px 0 10px 0',
                        }}
                      />
                    ) : (
                      <div
                        style={{
                          width: '26px',
                          height: '26px',
                          borderRadius: '50%',
                          backgroundColor: '#facc15',
                          boxShadow: '0 0 10px rgba(250, 204, 21, 0.3)',
                          margin: '10px 0 10px 0',
                        }}
                      />
                    )}

                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: 700,
                        color: isPeak ? '#f472b6' : isLow ? '#34d399' : '#facc15',
                      }}
                    >
                      {item.percent}%
                    </span>

                    {item.status === 'PEAK' && (
                      <span
                        style={{
                          fontSize: '9px',
                          fontWeight: 700,
                          color: '#f472b6',
                          marginTop: '2px',
                        }}
                      >
                        PEAK
                      </span>
                    )}
                  </div>
                );
              })}
        </div>
      </div>

      {/* ─── AI Recommendations Section ─── */}
      <div style={{ marginBottom: '18px' }}>
        <div
          style={{
            fontSize: '12px',
            fontWeight: 700,
            color: '#94a3b8',
            marginBottom: '10px',
            letterSpacing: '0.6px',
          }}
        >
          AI RECOMMENDATIONS
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {/* Recommendation 1: Peak Alert */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              backgroundColor: 'rgba(234, 179, 8, 0.12)',
              border: '1px solid rgba(234, 179, 8, 0.3)',
              borderRadius: '8px',
              padding: '10px 14px',
              fontSize: '13px',
              color: '#fef08a',
            }}
          >
            <AlertTriangle size={16} style={{ color: '#eab308', flexShrink: 0 }} />
            <span>Peak traffic expected between <strong>17:00-20:00</strong>. Consider alternate routes.</span>
          </div>

          {/* Recommendation 2: Best Travel Window */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              backgroundColor: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: '8px',
              padding: '10px 14px',
              fontSize: '13px',
              color: '#a7f3d0',
            }}
          >
            <CheckCircle2 size={16} style={{ color: '#10b981', flexShrink: 0 }} />
            <span>Best travel window: <strong>11:00-14:00</strong> with minimal congestion.</span>
          </div>

          {/* Recommendation 3: Optimization Action */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              backgroundColor: 'rgba(2, 132, 199, 0.12)',
              border: '1px solid rgba(2, 132, 199, 0.3)',
              borderRadius: '8px',
              padding: '10px 14px',
              fontSize: '13px',
              color: '#bae6fd',
            }}
          >
            <BarChart2 size={16} style={{ color: '#38bdf8', flexShrink: 0 }} />
            <span>Signal timing optimized for current traffic patterns.</span>
          </div>
        </div>
      </div>

      {/* ─── Footer Status ─── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderTop: '1px solid #1e2d45',
          paddingTop: '12px',
          fontSize: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontWeight: 600 }}>
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#10b981',
              boxShadow: '0 0 8px #10b981',
            }}
          />
          <span>AI Model Active</span>
        </div>

        <div style={{ color: '#94a3b8' }}>
          Accuracy: <strong style={{ color: '#38bdf8' }}>94.2%</strong>
        </div>
      </div>
    </div>
  );
}
