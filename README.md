# 🌾 AgriOS — Powered by Databricks

> **The full-stack AI operating system for Indian farmers.**  
> From soil to sale — every decision, data-driven. Every insight, delivered in the farmer's own language.

---

## 🚀 What is AgriOS?

AgriOS is an end-to-end intelligent agriculture platform built to transform how Indian farmers plan, grow, and sell. It combines real-time data ingestion, machine learning, physics-based crop models, and multilingual AI — all orchestrated on **Databricks**, the unified data intelligence platform that serves as the beating heart of every single component in this system.

This isn't a dashboard. This is a farmer's operating system.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATABRICKS LAKEHOUSE                     │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  Soil    │  │  Mandi   │  │ Weather  │  │  RAG / LLM   │   │
│  │  Data    │  │  Prices  │  │  Live    │  │  Delta Lake  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       │              │              │                │           │
│  ┌────▼──────────────▼──────────────▼────────────────▼──────┐  │
│  │              Delta Lake (Single Source of Truth)          │  │
│  └────────────────────────┬──────────────────────────────────┘  │
│                            │                                     │
│         ┌──────────────────▼──────────────────┐                 │
│         │        Databricks AutoML             │                 │
│         │    Random Forest — Crop Advisor      │                 │
│         └──────────────────┬──────────────────┘                 │
│                            │                                     │
│    ┌───────────────────────▼──────────────────────────────┐     │
│    │  GDD Model │ Weed Model │ Nitrogen Model │ Moisture  │     │
│    └───────────────────────┬──────────────────────────────┘     │
│                            │                                     │
│         ┌──────────────────▼──────────────────┐                 │
│         │   Sarvam VLM + Hindi LLM (RAG)       │                 │
│         │   Multilingual Farmer Interface       │                 │
│         └─────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Core Modules

### 1. 🌍 Soil Intelligence — SoilGrids API (ISRIC)

We ingest real-time soil composition data using the **SoilGrids REST API** by ISRIC (International Soil Reference and Information Centre) — a globally trusted, high-resolution soil data platform. For any given GPS coordinate on a farmer's field, we pull:

- Soil texture (sand, silt, clay percentages)
- Organic carbon content
- pH levels (0–30cm, 30–60cm, 60–100cm depth profiles)
- Bulk density and cation exchange capacity (CEC)
- Nitrogen, phosphorus, and potassium availability

This soil data is streamed directly into **Databricks Delta Lake**, where it is joined with weather and geospatial data to build a holistic feature store for downstream ML models. Databricks' distributed ingestion pipelines ensure that soil data across thousands of farms is processed in parallel, at scale, in real time.

---

### 2. 🌱 Crop Recommendation — Databricks AutoML (Random Forest)

This is where **Databricks AutoML earns its crown.**

Using the rich feature set derived from soil data, historical weather patterns, regional geolocation, and seasonal context, we trained a **Random Forest classifier** entirely within **Databricks AutoML** — with zero boilerplate. AutoML handled:

- Automated feature engineering and selection
- Hyperparameter search across hundreds of tree configurations
- Cross-validation and model comparison via MLflow experiment tracking
- One-click model registration to the **Databricks Model Registry**

The result: a production-grade crop recommendation engine that tells the farmer exactly which crop will thrive on their land this season — with confidence scores and explanations. The model is served via a **Databricks Model Serving endpoint**, making it callable in milliseconds from any part of the application.

**Databricks didn't just host this model. It built it.**

---

### 3. 📊 Live Mandi Prices — Agmarknet / data.gov.in API

Why grow a crop if you don't know what it'll sell for?

We fetch live commodity prices directly from the **Indian Government's Agmarknet portal** (`data.gov.in`), the official Agriculture Marketing Information System Network maintained by the Ministry of Agriculture & Farmers Welfare. This gives us:

- Daily wholesale minimum, maximum, and modal prices
- Data from 4,000+ regulated APMC mandis across 26 states
- Prices for 500+ commodities — grains, pulses, vegetables, spices, and more

This live price feed is ingested into **Databricks Structured Streaming**, processed and cleaned in real time, and stored in Delta Lake. Farmers receive not just crop recommendations but **market-aware crop recommendations** — knowing which crop will fetch the best price at their nearest mandi on harvest day.

---

### 4. 🌡️ Crop Growth Modeling — GDD with Rainfall Factors

We implement a **Growing Degree Days (GDD)** model to predict crop phenological stages — from germination to harvest — with the precision of agronomy science.

**GDD Formula:**
```
GDD = max(0, ((T_max + T_min) / 2) - T_base)
```

Where `T_base` is crop-specific (e.g., 10°C for wheat, 8°C for rice).

But we go beyond vanilla GDD. Standard GDD ignores rainfall — a critical oversight for Indian agriculture. We extend the model with the following correction factors:

- **Rainfall Reduction Factor (RRF):** On rainy days, cloud cover reduces solar radiation and temperature, lowering evapotranspiration (ET) demand. We apply a rainfall-weighted dampening coefficient to the daily GDD accumulation.
- **Precipitation-Adjusted Evapotranspiration (ET₀):** Using the Penman-Monteith reference ET equation with live weather inputs (temperature, relative humidity, wind speed, solar radiation), we calculate actual crop water demand vs. supply.
- **Soil-Water Potential Modifier:** Integrates soil field capacity (from SoilGrids) with cumulative rainfall to adjust the effective growing environment.
- **Photoperiod Sensitivity Flag:** For photoperiod-sensitive crops (e.g., short-day crops like soybean), day-length is calculated from latitude/longitude and applied as a binary stage-gate modifier.

All of this is computed on **Databricks notebooks** using distributed PySpark, allowing us to run GDD projections across every field in our system simultaneously — not one farm at a time.

---

### 5. 🌿 Weed Pressure Model — Mathematical Simulation

Weed competition is one of the leading causes of yield loss in Indian agriculture. We model weed pressure using a **hyperbolic yield-loss function**:

```
YL = (I × WD) / (1 + I × WD / A)
```

Where:
- `YL` = Yield Loss (%)
- `I`  = Initial slope of yield loss (crop-weed competition coefficient)
- `WD` = Weed density (plants/m²)
- `A`  = Asymptotic maximum yield loss (%)

We further extend this with a **critical weed-free period (CWFP)** calculator, which tells the farmer precisely how many days post-germination the crop must be kept weed-free to prevent economic damage. This is parameterized by crop type, soil nutrient availability, and GDD accumulation rate.

We also include a **simulation mode** — farmers (or agronomists) can input hypothetical weed densities and competition coefficients to project yield loss under different management scenarios. All simulations run on Databricks compute, with results persisted back to Delta Lake for auditing and advisory generation.

---

### 6. 🧪 Nitrogen Management Model — Mathematical Simulation

Nitrogen is the most limiting nutrient in Indian soils. We implement a **nitrogen balance model** that computes:

```
N_available = N_soil + N_fertilizer + N_mineralised - N_leached - N_crop_uptake
```

Where `N_mineralised` is estimated from soil organic carbon (from SoilGrids) and temperature using an Arrhenius-style thermal correction:

```
N_min = k × SOC × e^(-Ea / (R × T))
```

Farmers receive precise fertilizer application recommendations (dose, split schedule, and type) derived from this balance — reducing over-application, cutting costs, and preventing environmental runoff.

The **simulation capability** allows modeling of different fertilizer strategies — organic vs. synthetic, single vs. split application — before any money is spent. Databricks powers these scenario simulations at scale, enabling district-level nitrogen advisory programs, not just individual farm recommendations.

---

### 7. 💧 Soil Moisture Tracking — Live Weather Data

We integrate with a **live weather API** (OpenWeatherMap / IMD feeds) to track real-time atmospheric conditions and compute dynamic soil moisture estimates using a simplified **water balance model**:

```
SM(t) = SM(t-1) + Rainfall(t) - ET₀(t) - Runoff(t) - Deep_Percolation(t)
```

Live inputs used:
- **Temperature** (T_max, T_min) for ET calculation
- **Relative Humidity** for vapour pressure deficit
- **Wind Speed** for aerodynamic resistance
- **Precipitation** for direct soil recharge
- **Solar Radiation** (estimated from cloud cover) for potential ET

Soil moisture outputs drive irrigation advisories: when to irrigate, how much, and which method (drip vs. flood vs. sprinkler) is most efficient for the crop stage and soil type. All live weather streams are ingested, transformed, and served via **Databricks Delta Live Tables** — ensuring data quality guarantees and zero-latency freshness for real-time advisory generation.

---

### 8. 🤖 RAG-Powered Advisory — Delta Lake + Databricks Vector Search

The farmer's knowledge assistant is built on **Retrieval-Augmented Generation (RAG)**, grounded entirely in **Databricks Delta Lake**.

Our agricultural knowledge base — encompassing crop guides, pest management protocols, government scheme information, soil health advisories, and seasonal calendars — is chunked, embedded, and indexed using **Databricks Vector Search**, a native managed vector store built directly into the Lakehouse.

When a farmer asks a question (in Hindi or any supported Indic language), the pipeline:
1. Encodes the query using a multilingual embedding model
2. Performs semantic similarity search against the Delta Lake-backed vector index
3. Retrieves the top-K relevant knowledge chunks
4. Passes them as context to the LLM for grounded, hallucination-resistant response generation

Because the knowledge base lives in **Delta Lake**, it benefits from ACID transactions, schema enforcement, versioning, and time-travel — meaning advisory content can be updated in real time without touching the serving pipeline. The entire RAG pipeline is orchestrated via **Databricks Workflows**, with automated refresh jobs that keep the vector index synchronized with the latest agronomic guidance.

---

### 9. 🗣️ Multilingual AI Interface — Sarvam AI (VLM + Hindi LLM)

India's farmers speak in their language. So does AgriOS.

We power the entire conversational and visual interface using **Sarvam AI** — India's sovereign, full-stack AI platform purpose-built for Indic languages.

**Why Sarvam?**
- **Sarvam-M / Sarvam LLM:** A state-of-the-art multilingual LLM with deep Hindi proficiency, trained on 2 trillion Indic tokens across 10 major Indian languages. It outperforms models many times its size on Indic benchmarks, handles code-mixed text (Hinglish), and understands agricultural vocabulary in regional dialects.
- **Sarvam Vision (VLM):** A 3B parameter vision-language model supporting Indian language document understanding, OCR, and visual crop analysis. Farmers can photograph a diseased leaf, a soil sample, or a hand-written land record — and get an intelligent response in Hindi.
- **Saaras V3 (Speech-to-Text):** Real-time transcription across 22 Indian languages. Farmers simply speak; the system listens and understands.
- **Text-to-Speech:** Agronomic advisories are read back to farmers in natural, expressive Hindi — making the platform accessible to the 60%+ of rural India that prefers audio over text.
- **Sarvam Translate:** All system outputs can be translated across 22 official Indian languages with document-level context preservation.

The Sarvam API is called from within **Databricks notebooks and model serving endpoints**, making the Indic AI layer a first-class citizen of the Databricks Lakehouse pipeline — not a bolted-on afterthought.

---

## ⚡ Why Databricks is Everything

Let's be clear: **Databricks is not a tool we used. Databricks is the platform this entire system runs on.**

| Layer | Databricks Role |
|---|---|
| Data Ingestion | Delta Live Tables for streaming soil, weather, mandi, and sensor data |
| Feature Engineering | Spark-powered distributed transformations on millions of records |
| Model Training | AutoML — one-click Random Forest with full MLflow tracking |
| Model Serving | Real-time REST endpoints via Databricks Model Serving |
| Knowledge Store | Delta Lake — ACID-compliant, versioned, queryable knowledge base |
| Vector Search | Native Databricks Vector Search for RAG retrieval |
| Orchestration | Databricks Workflows for scheduling, monitoring, alerting |
| Simulation Engine | Databricks notebooks for GDD, weed, and nitrogen simulation jobs |
| Governance | Unity Catalog for data lineage, access control, and audit trails |
| Scalability | From one farm to one million — Databricks scales without re-architecture |

Every API call, every model inference, every farmer query passes through the Databricks Lakehouse. It is the soil that every component in this system grows from.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Unified Data Platform | **Databricks Lakehouse** |
| Data Storage | **Delta Lake** |
| ML Training | **Databricks AutoML** (Random Forest) |
| ML Tracking | **MLflow** (native in Databricks) |
| Streaming | **Databricks Delta Live Tables** |
| Vector Search | **Databricks Vector Search** |
| Orchestration | **Databricks Workflows** |
| Soil Data | **SoilGrids API (ISRIC)** |
| Mandi Prices | **Agmarknet / data.gov.in API** (Ministry of Agriculture & Farmers Welfare, GoI) |
| Weather Data | **Live Weather API** (OpenWeatherMap / IMD) |
| LLM (Hindi/Indic) | **Sarvam AI** (Sarvam-M, Sarvam 30B) |
| Vision-Language Model | **Sarvam Vision** (VLM with Indic OCR) |
| Speech Recognition | **Saaras V3** (Sarvam AI — 22 Indian languages) |
| Text-to-Speech | **Sarvam TTS** |
| Translation | **Sarvam Translate** |
| RAG Framework | Custom RAG on Delta Lake + Databricks Vector Search |
| Crop Growth Model | GDD + ET₀ + Rainfall Correction Factors |
| Weed Model | Hyperbolic Yield-Loss Function + CWFP Calculator |
| Nitrogen Model | N-Balance + Arrhenius Mineralisation |
| Moisture Model | Soil Water Balance (live weather inputs) |

---

## 🌐 Data Sources

| Data | Source |
|---|---|
| Soil composition & properties | [SoilGrids — ISRIC](https://soilgrids.org) |
| Daily mandi commodity prices | [Agmarknet / data.gov.in](https://data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi) |
| Live weather (temp, humidity, wind, radiation, rainfall) | OpenWeatherMap API / IMD feeds |
| Agricultural knowledge base | Curated agronomic literature, ICAR publications, Krishi Vigyan Kendra guides |

---

## 👥 Team

Built with 💚 for Indian farmers.  
Powered by **Databricks** — from the soil up.

---

## 📄 License

MIT License — because good ideas should grow freely.
