# GATI — Governance-ready AI Traffic Intelligence Platform

[![Scale Target](https://img.shields.io/badge/Target%20Scale-Nagpur%20(50--150%20Junctions)-0284c7.svg)](#scale-target--core-principles)
[![Architecture](https://img.shields.io/badge/Architecture-Edge--First%20%7C%20Retrofit-10b981.svg)](#architecture-overview)
[![License](https://img.shields.io/badge/License-MIT-gray.svg)](LICENSE)

GATI is an edge-first, retrofit-ready intelligent traffic control and predictive analytics platform engineered for Indian Tier-1/Tier-2 cities (such as **Nagpur**, with ~50–150 signalized junctions).

---

## 📖 Key Living Documents
Before contributing or evaluating the architecture, please read:
- 📑 **[`DECISIONS.md`](./DECISIONS.md)** — Chronological audit trail of all non-trivial engineering, modeling, and infrastructure choices.
- 🗺️ **[`FLOW.md`](./FLOW.md)** — Living High-Level (HLD) and Low-Level (LLD) design snapshot, bandwidth/cost calculations, and module status.

---

## 🎯 Core Principles & Nagpur-Scale Constraints
1. **Retrofit-First:** Works with existing municipal CCTV and ANPR camera feeds without requiring expensive new camera hardware.
2. **Edge-First (< 5 KB/s Upstream Bandwidth):** Heavy computer vision detection and queue tracking run locally at the roadside edge. Only compact structured JSON telemetry is sent over standard 4G/WAN to the central server. Raw video is **never** continuously streamed to the cloud.
3. **Honesty Over Impressiveness:** Relies on robust, auditable baselines (Max-Pressure signal actuation with safety guardrails, Indian Standard IRC PCU weighting, and Holt-Winters forecasting).
4. **Cost-Conscious:** Sized for a municipal procurement budget (~₹50L–₹70L Capex for 100 junctions, ~₹45k/month Opex total).

---

## 🏗️ Repository Layout

The codebase is organized into clean, modular components allowing 3–4 engineers to build in parallel:

```text
.
├── config/                  # Centralized system constants & per-junction geometries (NO hardcoded logic)
│   ├── default_config.yaml  # PCU multipliers, min/max green guardrails, thresholds
│   ├── junctions/           # Per-junction YAML files (Sitabuldi, Varieties Sq, etc.)
│   └── settings.py          # Dynamic Pydantic configuration loader
├── edge/                    # Runs locally at each roadside cabinet / edge compute box
│   ├── vision/              # Quantized detector, tracker, Indian PCU engine, emergency detector
│   ├── controller/          # Max-Pressure signal optimizer & safety state machine
│   └── telemetry/           # Compact JSON telemetry publisher with offline buffering
├── central/                 # Runs at the City Integrated Command & Control Centre (ICCC)
│   ├── api/                 # FastAPI ingestion backend & WebSocket real-time broadcast
│   ├── analytics/           # Forecasting (Holt's), anomaly Z-score detection, Junction Risk Index
│   └── coordinator/         # Arterial corridor green wave synchronization
├── simulation/              # Multi-junction Nagpur traffic & telemetry simulation harness
├── frontend/                # React (Vite) operator console and green wave control dashboard
├── DECISIONS.md             # Architecture & engineering decision log
├── FLOW.md                  # HLD & LLD living specification
└── requirements.txt         # Python dependencies
```

---

## 🚀 Quickstart & Local Setup

### 1. Install Backend Dependencies
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Start the Central FastAPI Ingestion Server
```bash
uvicorn central.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Run the Nagpur Multi-Junction Traffic Simulator
In a separate terminal:
```bash
python -m simulation.city_simulator
```

### 4. Start the Operator Dashboard (React)
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.
