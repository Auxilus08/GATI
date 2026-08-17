# GATI — Governance-ready AI Traffic Intelligence Platform

[![Scale Target](https://img.shields.io/badge/Target%20Scale-Nagpur%20(50--150%20Junctions)-0284c7.svg)](#scale-target--core-principles)
[![Architecture](https://img.shields.io/badge/Architecture-Edge--First%20%7C%20Retrofit-10b981.svg)](#architecture-overview)
[![Tests](https://img.shields.io/badge/Tests-69%2F69%20Passed-brightgreen.svg)](#test-suite-verification)
[![License](https://img.shields.io/badge/License-MIT-gray.svg)](LICENSE)

> **GATI (Governance-ready AI Traffic Intelligence)** is an edge-first, retrofit software layer that converts existing municipal CCTV and ANPR camera feeds into real-time adaptive traffic signals and proactive risk analytics — requiring zero new camera installations, cutting 4G bandwidth costs by >99%, and delivering measured wait-time reductions of over **30.8%**.

---

## 🌐 Live Vercel Demo

- **Operator Dashboard:** [`https://gati-vercel-stage.vercel.app`](https://gati-vercel-stage.vercel.app)

The Vercel deployment runs the FastAPI API as a serverless function and serves the built React dashboard. Because Vercel does not run long-lived background simulator processes, the hosted demo seeds representative Nagpur junction telemetry on first request.

---

## ⚡ 1-Click Competition Demo Launch

To launch the full system (Central API + City Simulator + React Operator Dashboard) in one click:

```powershell
# Windows PowerShell:
.\launch_demo.ps1

# Or double-click:
launch_demo.bat
```

Once launched:
- **React Operator Dashboard:** `http://localhost:5173`
- **Central FastAPI Swagger Docs:** `http://localhost:8000/docs`

---

## 📖 Key Submission & Presentation Documents

- 📑 **[`TECHNICAL_WRITEUP.md`](./TECHNICAL_WRITEUP.md)** — Comprehensive architecture, mathematical model justifications, measured performance, and DPDP Act 2023 compliance.
- 🎯 **[`PITCH_CHEAT_SHEET.md`](./PITCH_CHEAT_SHEET.md)** — 1-page quick-reference sheet with pitch timings, key statistics to memorize, and winning answers to tough judge questions.
- 🎬 **[`DEMO_SCRIPT.md`](./DEMO_SCRIPT.md)** — Step-by-step presentation script and screen-by-screen walkthrough.
- 📜 **[`DECISIONS.md`](./DECISIONS.md)** — Chronological audit trail of all non-trivial engineering, modeling, and infrastructure choices.
- 🗺️ **[`FLOW.md`](./FLOW.md)** — Living High-Level (HLD) and Low-Level (LLD) design snapshot, bandwidth/cost calculations, and module status.

---

## 🎯 Core Principles & Nagpur-Scale Constraints

1. **Retrofit-First:** Works with existing municipal CCTV and ANPR camera feeds without requiring expensive new camera hardware.
2. **Edge-First (< 5 KB/s Upstream Bandwidth):** Heavy computer vision detection and queue tracking run locally at the roadside edge. Only compact structured JSON telemetry is sent over standard 4G/WAN to the central server. Raw video is **never** continuously streamed to the cloud.
3. **Honesty Over Impressiveness:** Relies on robust, auditable baselines (Max-Pressure signal actuation with safety guardrails, Indian Standard IRC PCU weighting, and Holt-Winters forecasting).
4. **Cost-Conscious:** Sized for a municipal procurement budget (~₹57.96 Lakh 3-Yr TCO for 100 junctions vs. ₹10.5+ Crore for traditional video-streaming ICCCs — **>94% cost reduction**).

---

## 📊 Measured Benchmark Results

| Metric | Baseline Fixed-Time | GATI Max-Pressure | Measured Improvement |
| :--- | :--- | :--- | :--- |
| **Average Vehicular Delay** | 42.5s / PCU | **29.4s / PCU** | **-30.8% Wait Time** |
| **Peak Queue Length** | 112.0 meters | **68.0 meters** | **-31.9% Queue Shrink** |
| **Cellular Bandwidth per Junc** | 16 Mbps continuous | **< 5 KB/s** | **>99.5% Bandwidth Drop** |
| **3-Year TCO (100 Junctions)** | ₹10.5+ Crore | **₹57.96 Lakh** | **~94.5% Cost Reduction** |

---

## 🐳 Docker Deployment

To launch via Docker Compose:

```bash
docker-compose up --build
```

---

## 🧪 Test Suite Verification

Run the full automated unit and integration test suite:

```bash
python -m pytest tests/
```
Output: **69 passed** (100% test pass rate).

