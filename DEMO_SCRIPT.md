# GATI Live Demo Script & Pitch Guide

This document defines the exact step-by-step sequence of actions and talking points to present during a live demonstration of GATI to hackathon judges, municipal commissioners, and traffic police authorities.

---

## 1. Pitch Narrative & Positioning (1 Minute)

> **Headline:** *"GATI is a governance-ready AI retrofit layer that transforms existing Indian city CCTV cameras into real-time adaptive traffic signals and live risk analytics — without new camera procurement and without cloud GPU bills."*

### Key Anchors to State:
1. **Target Scale:** Tailored for a Tier-1 Indian city like **Nagpur (~100 signalized junctions)**.
2. **The Indian Reality:** No lane discipline, 2-wheelers/autos filtering laterally, dense queues, and intermittent network connectivity.
3. **Core Architectural Principle:** **Edge-First + Metadata-Only Upstream**. All YOLOv8/ByteTrack inference runs directly on roadside edge hardware (Jetson Orin Nano / RK3588). Only lightweight JSON metadata (< 5 KB/s) is sent upstream.
4. **Honesty & Provability:** No faked RL claims, no invented historical accident datasets. Everything displayed is mathematically derived from real CCTV tracks.

---

## 2. Live Demo Step-by-Step Flow (3 Minutes)

### Step 1: Terminal Execution & Pipeline Boot
- **Action:** Open terminal and run:
  ```bash
  python scripts/run_live_demo.py
  ```
- **What to Point At:**
  - Emphasize the live console output showing **Max-Pressure phase decisions**, minimum/maximum green safety guardrails, and real-time PCU calculations.
  - Highlight the measured **Before vs. After evidence summary** (showing vehicular delay reduction and fuel/CO2 savings computed directly from tracked PCUs).

### Step 2: Open the 3-Panel Operator Dashboard (`http://localhost:3000` or demo URL)

#### **Panel 1: Live Junction View (Perception & Phasing HUD)**
- **Action:** Click on the **Live Junction View** tab.
- **What to Point At:**
  - **CCTV Video Viewport:** Point out the bounding boxes labeled with Indian vehicle taxonomy (`two_wheeler`, `auto_rickshaw`, `car`, `bus`, `truck`).
  - **Lane-Free Approach Cards:** Show that queue lengths ($m$) and vehicle counts are aggregated **per approach ROI polygon** rather than virtual lane tripwires, directly accommodating Indian lateral filtering.
  - **Signal HUD:** Point out the active phase (Green/Amber/Red) and the dynamic countdown timers respecting the 15s min-green / 60s max-green safety bounds.

#### **Panel 2: Command View (Governance & Before/After Proof)**
- **Action:** Switch to the **Command View** tab.
- **What to Point At:**
  - **Headline KPI Banner:** Highlight the headline numbers at the top:
    - **~30.8% Average Wait Time Reduction**
    - **~31.9% Peak Queue Length Reduction**
    - Fuel & Carbon emissions avoided.
  - **Signal Phase Timing Comparison:** Show the comparison chart comparing the rigid fixed-time baseline (40s/40s pre-timed) against GATI's dynamic Max-Pressure allocation.
  - **Manual Operator Override Demonstration:**
    - Enter Operator ID (e.g. `POLICE_ICCC_402`) and Reason (e.g. `VIP Convoy Clearance`).
    - Select Phase 2 and click **"Lock Phase"**.
    - Show the UI immediately locking the phase, displaying the remaining override timer (300s max safety ceiling), and logging a permanent record in the **Override Audit Trail**.
    - Click **"Release Control"** to demonstrate immediate fail-safe handover back to autonomous Max-Pressure.

#### **Panel 3: Predictive & Risk View (Proactive Intelligence & Ethics)**
- **Action:** Switch to the **Predictive / Risk View** tab.
- **What to Point At:**
  - **Short-Horizon Congestion Forecast Chart:** Point to the 10, 15, and 30-minute queue projection curves generated via Holt's linear trend with damping.
  - **Live Kinematic Surrogate Safety Indicators:** Explain that the risk score (0–100) is derived from **real trajectory kinematics** (speed variance, abrupt decelerations $a < -3.5\text{m/s}^2$, and near-miss spatial conflict proxies $\text{TTC} < 1.5\text{s}$).
  - **Stalled Vehicle Incident Feed:** Point out how stationary vehicles ($< 1.5\text{m}$ displacement for $> 20\text{s}$) trigger instant high-severity alerts.
  - **Data Integrity & Privacy Badge:** Point to the visible **"COMING SOON"** label for multi-year police FIR accident GIS records, explaining that GATI refuses to fake historical accident data.

---

## 3. Failure Modes & Graceful Degradation (1 Minute)

Explain how GATI handles real Indian field failure modes:

| Failure Mode | Graceful Degradation Response |
| :--- | :--- |
| **All-Approaches Gridlock** | If all approaches are saturated (> 25 PCU), Max-Pressure falls back to deterministic fixed-time cyclical rotation to avoid algorithm thrashing. |
| **Adverse Weather / Dust / Fog** | If detection confidence drops below 0.40, system holds last known-good state, alerts the ICCC operator, and prevents erratic signal switching. |
| **4G / WAN Network Drop** | Edge controller continues 100% autonomous local signal actuation; telemetry is cached in local circular buffer and synced upon reconnect. |
| **Operator Abandoned Lock** | Overrides automatically expire after a 300-second safety timeout, preventing forgotten manual holds. |

---

## 4. Closing Statement & Cost Impact

> *"For a city like Nagpur with 100 signalized junctions, GATI delivers over 94% cost savings compared to traditional video-streaming ICCCs: saving ₹1.8 Crore annually on 4G bandwidth and ₹3.0 Crore annually on cloud GPU servers, while cutting commuter wait times by over 30%."*
