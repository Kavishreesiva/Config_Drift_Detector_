import os
import json
import uuid
import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException, Header, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Import helper modules
try:
    from backend.detector import detect_drift
    from backend.ai_analyzer import analyze_drifts, generate_remediation_scripts, answer_drift_chat, perform_cybersecurity_audit, predict_security_attack_patterns
    from backend.report_generator import generate_markdown_report, generate_pdf_report
except ImportError:
    # Handle if run directly or as a module
    from detector import detect_drift
    from ai_analyzer import analyze_drifts, generate_remediation_scripts, answer_drift_chat, perform_cybersecurity_audit, predict_security_attack_patterns
    from report_generator import generate_markdown_report, generate_pdf_report

app = FastAPI(
    title="Config Drift Detector API",
    description="Backend API for comparing JSON/YAML configurations and performing AI impact analysis."
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# Pydantic Schemas
class AnalyzeRequest(BaseModel):
    intended_content: str = Field(..., description="Content of the intended config file")
    actual_content: str = Field(..., description="Content of the actual/live config file")
    intended_name: str = Field("intended_config.json", description="Filename of the intended config")
    actual_name: str = Field("actual_config.json", description="Filename of the actual config")
    file_format: str = Field("auto", description="File format: json, yaml, or auto")
    api_key: Optional[str] = Field(None, description="Optional Gemini API key override")

class ExportRequest(BaseModel):
    intended_file: str
    actual_file: str
    risk_score: int
    drifts: List[Dict[str, Any]]

class RemediateRequest(BaseModel):
    drifts: List[Dict[str, Any]]
    intended_content: str
    actual_content: str
    file_format: Optional[str] = "json"
    api_key: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    drifts: Optional[List[Dict[str, Any]]] = None
    api_key: Optional[str] = None

class SaveBaselineRequest(BaseModel):
    name: str = Field("production_baseline.json", description="Baseline name")
    content: str = Field(..., description="Baseline content")
    file_format: str = Field("auto", description="Format: json, yaml, cisco")

class CollectorScanRequest(BaseModel):
    actual_content: str = Field(..., description="Live collected config content")
    actual_name: str = Field("live_collected_config.json", description="Live config filename")
    file_format: str = Field("auto", description="File format")
    api_key: Optional[str] = Field(None, description="Gemini API Key")

BASELINE_FILE = os.path.join(BASE_DIR, "baseline.json")

def load_active_baseline() -> Dict[str, Any]:
    if not os.path.exists(BASELINE_FILE):
        return {}
    try:
        with open(BASELINE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_active_baseline(data: Dict[str, Any]):
    try:
        with open(BASELINE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to save baseline: {e}")

# Helper: Load/Save History
def load_history() -> List[Dict[str, Any]]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(entry: Dict[str, Any]):
    history = load_history()
    # Insert at the beginning so recent is first
    history.insert(0, entry)
    # Limit to 50 entries
    history = history[:50]
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Failed to save history: {e}")

def get_current_timestamp() -> str:
    try:
        return datetime.datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    except Exception:
        return datetime.datetime.now().astimezone().isoformat()

# Endpoints
@app.post("/api/analyze")
async def analyze_config_drift(req: AnalyzeRequest):
    try:
        # 1. Compare files using DeepDiff
        drifts = detect_drift(req.intended_content, req.actual_content, req.file_format)
        
        # 2. Run AI Analysis (or rule-based fallback)
        analyzed_drifts = analyze_drifts(drifts, req.api_key)
        
        # 3. Calculate statistics
        total_drifts = len(analyzed_drifts)
        breaking_count = sum(1 for d in analyzed_drifts if d.get("severity") == "Breaking")
        functional_count = sum(1 for d in analyzed_drifts if d.get("severity") == "Functional")
        cosmetic_count = sum(1 for d in analyzed_drifts if d.get("severity") == "Cosmetic")
        
        # Risk score formula
        if total_drifts == 0:
            risk_score = 0
        else:
            score = (breaking_count * 30) + (functional_count * 10) + (cosmetic_count * 2)
            if breaking_count > 0:
                score = max(50, score)
            risk_score = min(100, score)
            
        # 4. Perform Cybersecurity & Network Threat Audit
        cyber_audit = perform_cybersecurity_audit(analyzed_drifts)
        
        # 5. Perform Predictive Security Attack Pattern Recognition
        history_runs = load_history()
        predictive_analysis = predict_security_attack_patterns(analyzed_drifts, history_runs)
        
        # 6. Save to history
        history_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": get_current_timestamp(),
            "intended_file": req.intended_name,
            "actual_file": req.actual_name,
            "total_drifts": total_drifts,
            "breaking_count": breaking_count,
            "functional_count": functional_count,
            "cosmetic_count": cosmetic_count,
            "risk_score": risk_score,
            "cyber_audit": cyber_audit,
            "predictive_analysis": predictive_analysis,
            "drifts": analyzed_drifts
        }
        save_history(history_entry)
        
        # Return results
        return history_entry
        
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/api/baseline/save")
async def save_baseline(req: SaveBaselineRequest):
    try:
        entry = {
            "name": req.name,
            "content": req.content,
            "file_format": req.file_format,
            "timestamp": get_current_timestamp()
        }
        save_active_baseline(entry)
        return {
            "status": "success",
            "message": f"Production Baseline '{req.name}' saved successfully in database!",
            "baseline": entry
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save baseline: {str(e)}")

@app.get("/api/baseline/get")
async def get_baseline():
    baseline = load_active_baseline()
    if not baseline:
        return {"has_baseline": False, "message": "No active baseline saved."}
    return {"has_baseline": True, "baseline": baseline}

LIVE_FILE_PATH = os.path.join(BASE_DIR, "data", "live_server_config.txt")

@app.post("/api/collector/scan")
async def run_collector_scan(req: CollectorScanRequest):
    try:
        baseline = load_active_baseline()
        if not baseline or not baseline.get("content"):
            raise HTTPException(
                status_code=400, 
                detail="No active baseline found! Click '[CREATE BASELINE]' on the UI first to save your production baseline."
            )
            
        intended_content = baseline["content"]
        intended_name = baseline.get("name", "active_baseline.json")
        
        # Real Live Disk File Collector: Reads actual live server config file from disk if present!
        actual_content = req.actual_content
        actual_name = req.actual_name
        
        if os.path.exists(LIVE_FILE_PATH):
            try:
                with open(LIVE_FILE_PATH, "r", encoding="utf-8") as lf:
                    disk_content = lf.read().strip()
                    if disk_content:
                        actual_content = disk_content
                        actual_name = "backend/data/live_server_config.txt (Real Disk File)"
            except Exception:
                pass
                
        file_format = req.file_format if req.file_format != "auto" else baseline.get("file_format", "auto")
        
        # 1. Compare live collected config with saved baseline
        drifts = detect_drift(intended_content, actual_content, file_format)
        analyzed_drifts = analyze_drifts(drifts, req.api_key)
        
        total_drifts = len(analyzed_drifts)
        breaking_count = sum(1 for d in analyzed_drifts if d.get("severity") == "Breaking")
        functional_count = sum(1 for d in analyzed_drifts if d.get("severity") == "Functional")
        cosmetic_count = sum(1 for d in analyzed_drifts if d.get("severity") == "Cosmetic")
        
        if total_drifts == 0:
            risk_score = 0
        else:
            score = (breaking_count * 30) + (functional_count * 10) + (cosmetic_count * 2)
            if breaking_count > 0:
                score = max(50, score)
            risk_score = min(100, score)
            
        cyber_audit = perform_cybersecurity_audit(analyzed_drifts)
        history_runs = load_history()
        predictive_analysis = predict_security_attack_patterns(analyzed_drifts, history_runs)
        
        result_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": get_current_timestamp(),
            "intended_file": f"📌 Baseline ({intended_name})",
            "actual_file": f"🤖 Live Collector ({req.actual_name})",
            "total_drifts": total_drifts,
            "breaking_count": breaking_count,
            "functional_count": functional_count,
            "cosmetic_count": cosmetic_count,
            "risk_score": risk_score,
            "cyber_audit": cyber_audit,
            "predictive_analysis": predictive_analysis,
            "drifts": analyzed_drifts
        }
        
        save_history(result_entry)
        return result_entry
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Collector scan failed: {str(e)}")

@app.post("/api/export/pdf")
async def export_pdf(req: ExportRequest):
    try:
        data = {
            "intended_file": req.intended_file,
            "actual_file": req.actual_file,
            "risk_score": req.risk_score,
            "drifts": req.drifts
        }
        pdf_bytes = generate_pdf_report(data)
        
        # Return as downloadable attachment
        filename = f"drift_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {str(e)}")

@app.post("/api/export/markdown")
async def export_markdown(req: ExportRequest):
    try:
        data = {
            "intended_file": req.intended_file,
            "actual_file": req.actual_file,
            "risk_score": req.risk_score,
            "drifts": req.drifts
        }
        md_text = generate_markdown_report(data)
        return {"markdown": md_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate markdown: {str(e)}")

try:
    from backend.netmiko_agent import fetch_live_config_via_netmiko, apply_netmiko_remediation
except ImportError:
    pass

@app.post("/api/remediate/ssh")
async def execute_ssh_self_healing(req: Dict[str, Any]):
    """
    Connects via Netmiko SSH directly onto Cisco Router/Switch CLI and applies auto-healing commands.
    """
    commands = req.get("commands", ["interface GigabitEthernet0/1", "no shutdown", "ip access-list extended SEC_ACL", "deny ip any any"])
    host = req.get("host", "192.168.1.1")
    username = req.get("username", "admin")
    password = req.get("password", "cisco123")
    
    result = apply_netmiko_remediation(commands, host=host, username=username, password=password)
    return {
        "status": result["status"],
        "message": f"Autonomous Netmiko SSH Self-Healing executed on Cisco device ({host})!",
        "executed_commands": result["executed_commands"],
        "device_response": result["output"]
    }

@app.post("/api/netmiko/fetch")
async def fetch_cisco_netmiko(req: Dict[str, Any]):
    """
    Fetches live 'show running-config' directly from a Cisco Router/Switch via Netmiko SSH.
    """
    host = req.get("host", "192.168.1.1")
    username = req.get("username", "admin")
    password = req.get("password", "cisco123")
    
    result = fetch_live_config_via_netmiko(host=host, username=username, password=password)
    return result

@app.post("/api/webhook/notify")
async def send_slack_webhook(req: Dict[str, Any]):
    """
    Simulates ChatOps incident alert dispatching to Slack / Microsoft Teams / Discord.
    """
    channel = req.get("channel", "#security-alerts")
    risk_score = req.get("risk_score", 90)
    
    return {
        "status": "sent",
        "message": f"🚨 Security Incident Webhook Alert dispatched to ChatOps channel '{channel}'!",
        "payload_sent": {
            "channel": channel,
            "text": f"🚨 *CRITICAL DRIFT ALERT*: Risk Score {risk_score}/100 detected on production server! Reconcile immediately.",
            "bot_name": "DriftDetector Shield Bot"
        }
    }

@app.get("/api/history")
async def get_history():
    return load_history()

@app.post("/api/history/clear")
async def clear_history():
    try:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        return {"status": "success", "message": "History cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/history/{run_id}")
async def delete_history_entry(run_id: str):
    try:
        history = load_history()
        updated = [h for h in history if h.get("id") != run_id]
        if len(updated) == len(history):
            raise HTTPException(status_code=404, detail="History entry not found")
        with open(HISTORY_FILE, "w") as f:
            json.dump(updated, f, indent=2)
        return {"status": "success", "message": "Entry deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/remediate")
async def remediate_config_drift(req: RemediateRequest):
    try:
        scripts = generate_remediation_scripts(
            drifts=req.drifts,
            intended_content=req.intended_content,
            actual_content=req.actual_content,
            file_format=req.file_format or "json",
            api_key=req.api_key
        )
        return scripts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate remediation scripts: {str(e)}")

@app.post("/api/chat")
async def chat_drift_assistant(req: ChatRequest):
    try:
        reply = answer_drift_chat(
            user_message=req.message,
            drifts=req.drifts,
            api_key=req.api_key
        )
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# Root & Static serving logic
@app.get("/")
async def serve_home():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Config Drift Detector API is running, but frontend/index.html was not found. Please build the frontend."}

# Mount static files (js, css, etc.) if frontend directory exists
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
else:
    # Create frontend dir dynamically so mounting won't crash later
    os.makedirs(FRONTEND_DIR, exist_ok=True)
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
