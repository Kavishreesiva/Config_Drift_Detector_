# 🛡️ Config Drift Detector

### Team 04 | UC ID: IM-04 | Infra Maintenance Category

### Infinite Computer Solutions Placement Drive | June 2026

---

## 👥 Team Members

| Name | Roll No | Branch |
|--------|----------|----------|
| Pappala Devi Sai Charan | 23U41A0542 | CSE |
| Pentakota Tanuja | 23U41A0545 | CSE |
| Bevara Lize | 23U41A4405 | CSD |
| Peela Divya Santhoshi Lakshmi | 24U45A0423 | ECE |

---

## Overview

The AI-Powered Configuration Drift Detector identifies configuration differences between intended and actual system configurations. It analyzes files, detects drifts, calculates risk scores, and generates reports.

---

## Features

- Configuration Drift Detection
- Risk Assessment
- Dashboard Analytics
- PDF Report Export
- Markdown Report Export
- History Tracking
- Gemini AI Integration

---

## Technology Stack

### Frontend
- HTML
- CSS
- JavaScript

### Backend
- Python
- FastAPI

### AI
- Google Gemini API

---

## Project Structure

```text
actual/
intended/
backend/
frontend/
```

## Setup Instructions

### Clone Repository

```bash
git clone https://github.com/saicharan-122/Config-Drift-Detector.git
```

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Run Application

```bash
uvicorn app:app --reload
```

Application will run at:

```text
http://localhost:8000
```

---

## Architecture Overview

```text
Frontend
    |
    v
FastAPI Backend
    |
    v
Drift Detection Engine
    |
    v
Gemini AI Analysis
```

---

## Assumptions

- Configuration files are valid JSON/YAML.
- Users provide intended and actual configurations.
- Internet connection is available for Gemini AI features.

---

## Limitations

- Supports limited configuration formats.
- Free deployment may sleep after inactivity.
- Gemini AI analysis depends on API availability.

---
## Demo Video:
https://drive.google.com/file/d/1YuDMNKHKDWDsYXBzEhrLmPhyHQWeOpty/view?usp=drivesdk

---

## Project Links

GitHub Repository:
https://github.com/saicharan-122/Config-Drift-Detector

Live Application:
https://config-drift-detector.onrender.com
---
