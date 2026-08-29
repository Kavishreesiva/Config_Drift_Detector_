import os
import json
import google.generativeai as genai

def get_fallback_analysis(drift: dict) -> dict:
    """
    Generates a high-quality local analysis for a drift in case Gemini API is not configured.
    """
    key = drift['key']
    old = drift['old_value']
    new = drift['new_value']
    severity = drift['severity']
    
    explanation = f"Configuration '{key}' was modified."
    impact = "Potential change in system behavior or security profile."
    risk_level = "Low"
    recommendation = "Review the change to ensure it aligns with operational requirements."
    
    key_lower = key.lower()
    
    if 'port' in key_lower:
        explanation = f"Network port changed from '{old}' to '{new}'."
        impact = "Changes the port the service listens on. Can cause connectivity issues or conflict with other services."
        risk_level = "High" if severity == "Breaking" else "Medium"
        recommendation = f"Verify firewall rules allow incoming traffic on port '{new}' and that no other services are using this port."
        
    elif 'ssl' in key_lower or 'tls' in key_lower or 'cert' in key_lower:
        explanation = f"SSL/TLS security setting '{key}' changed."
        impact = "Altering security protocols may expose data in transit, disable encryption, or cause client connection handshakes to fail."
        risk_level = "Critical"
        recommendation = "Ensure SSL certificates are valid and secure protocols (TLS 1.2/1.3) are enforced. Do not disable SSL in production."
        
    elif 'password' in key_lower or 'secret' in key_lower or 'key' in key_lower or 'token' in key_lower or 'auth' in key_lower:
        explanation = "Authentication credentials or security keys have been modified."
        impact = "A change in credentials, API keys, or secrets can lock out legitimate services, or point to unauthorized access attempts if not planned."
        risk_level = "Critical"
        recommendation = "Validate that the credentials/keys are rotated securely and match authorized access patterns. Avoid committing secrets to Git."
        
    elif 'db' in key_lower or 'database' in key_lower:
        explanation = f"Database configuration '{key}' changed from '{old}' to '{new}'."
        impact = "Points the application to a different database instance or modifies database access parameters. Could result in data mismatch, connectivity failures, or data loss."
        risk_level = "Critical"
        recommendation = "Verify the database connection string and credentials. Ensure the target database is healthy and has the correct schema."
        
    elif 'debug' in key_lower:
        explanation = f"Debug mode changed from '{old}' to '{new}'."
        if str(new).lower() in ['true', '1', 'yes']:
            impact = "Enabling debug mode in production exposes detailed stack traces, environment variables, and sensitive logs to end-users."
            risk_level = "High"
            recommendation = "Disable debug mode (set to false) in production environments immediately."
        else:
            impact = "Disabling debug mode improves security and reduces logging overhead."
            risk_level = "Low"
            recommendation = "Ensure sufficient centralized logging is active to diagnose issues in production without debug logs."
            
    elif 'timeout' in key_lower:
        explanation = f"Timeout setting '{key}' changed from '{old}' to '{new}'."
        impact = "Modifies the time the system waits for an operation to complete. High values cause resource exhaustion; low values cause premature request failures."
        risk_level = "Medium"
        recommendation = "Tune timeout parameters based on average latency and SLA. Monitor for timeout exceptions or leakages."
        
    elif 'retry' in key_lower:
        explanation = f"Retry policy setting '{key}' changed from '{old}' to '{new}'."
        impact = "Alters how the application handles transient errors. Too many retries can overwhelm backend services (thundering herd); too few retries can degrade user experience."
        risk_level = "Medium"
        recommendation = "Implement exponential backoff with jitter for retries. Do not retry indefinitely on non-transient errors."
        
    elif 'memory' in key_lower or 'limit' in key_lower or 'pool' in key_lower:
        explanation = f"Resource limit '{key}' adjusted from '{old}' to '{new}'."
        impact = "Changes memory or connection limits. Lower limits can cause Out-Of-Memory (OOM) errors or service exhaustion; excessively high limits can starve other processes."
        risk_level = "Medium"
        recommendation = "Perform load testing to establish optimal resource ceilings. Monitor container and host CPU/memory usage."
        
    elif 'cache' in key_lower:
        explanation = f"Cache configuration '{key}' modified."
        impact = "Affects data retrieval performance and consistency. Misconfigured caching can cause stale data or overload databases."
        risk_level = "Medium"
        recommendation = "Review Cache-Control policies, Time-To-Live (TTL) values, and cache eviction strategies."
        
    elif severity == "Cosmetic":
        explanation = f"Cosmetic metadata configuration '{key}' updated from '{old}' to '{new}'."
        impact = "No operational impact on system functionality or performance. Changes are descriptive or presentation-oriented."
        risk_level = "Low"
        recommendation = "Verify document accuracy and check if spelling is correct."
        
    return {
        'key': key,
        'explanation': explanation,
        'impact': impact,
        'risk_level': risk_level,
        'recommendation': recommendation
    }

def analyze_drifts(drifts: list, api_key: str = None) -> list:
    """
    Analyzes list of drifts using Gemini API.
    Falls back to high-quality rule-based analysis if API key is not available or call fails.
    """
    if not drifts:
        return []
        
    # Check for api_key from arguments, then environment
    key_to_use = api_key or os.environ.get("GEMINI_API_KEY")
    
    if not key_to_use:
        # No key, run local rule-based analyzer
        return [{**d, **get_fallback_analysis(d)} for d in drifts]
        
    try:
        # Configure the Gemini API
        genai.configure(api_key=key_to_use)
        
        # Prepare the input for Gemini
        drifts_input = []
        for d in drifts:
            drifts_input.append({
                'key': d['key'],
                'type': d['type'],
                'old_value': str(d['old_value']),
                'new_value': str(d['new_value']),
                'severity': d['severity']
            })
            
        prompt = f"""
You are an expert DevOps, Site Reliability, and Cloud Security Engineer.
Analyze the following list of configuration drifts (differences) detected between an intended (baseline) configuration file and an actual (live) configuration file.

Configuration Drifts to analyze:
{json.dumps(drifts_input, indent=2)}

For each drift, perform a detailed assessment and provide:
1. `explanation`: A clear explanation of what changed in plain language.
2. `impact`: The potential operational, performance, or security impact this change has on the running system.
3. `risk_level`: The risk classification of this change. Choose strictly from: 'Low', 'Medium', 'High', 'Critical'.
4. `recommendation`: A clear, actionable fix or verification recommendation.

You must return a valid JSON array matching the keys of the input.
Response format must be exactly a JSON array of objects, like this:
[
  {{
    "key": "example.key",
    "explanation": "Brief description of change",
    "impact": "Operational or security impact",
    "risk_level": "Low/Medium/High/Critical",
    "recommendation": "Step-by-step fix suggestion"
  }}
]

Make your analysis specific to the configuration key names (e.g. ports, SSL settings, database settings, retry flags, etc.).
Ensure you output ONLY a valid JSON array. Do not wrap the JSON output in markdown blocks or write any introductory text.
"""
        
        # Try to use gemini-1.5-flash
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Parse the JSON response
        try:
            results = json.loads(response.text.strip())
            # Map results by key
            analysis_map = {item['key']: item for item in results if 'key' in item}
            
            # Merge with original drifts
            analyzed_drifts = []
            for d in drifts:
                key = d['key']
                if key in analysis_map:
                    analyzed_drifts.append({
                        **d,
                        'explanation': analysis_map[key].get('explanation'),
                        'impact': analysis_map[key].get('impact'),
                        'risk_level': analysis_map[key].get('risk_level', 'Medium'),
                        'recommendation': analysis_map[key].get('recommendation')
                    })
                else:
                    # Fallback for individual item if missing in AI response
                    fallback = get_fallback_analysis(d)
                    analyzed_drifts.append({**d, **fallback})
                    
            return analyzed_drifts
            
        except (json.JSONDecodeError, AttributeError) as e:
            # If JSON parsing failed, try to regex-extract or fallback
            print(f"Failed to parse Gemini response as JSON: {e}. Response text: {response.text}")
            return [{**d, **get_fallback_analysis(d)} for d in drifts]
            
    except Exception as e:
        print(f"Gemini API call failed: {e}")
        # Call failed, use local rules
        return [{**d, **get_fallback_analysis(d)} for d in drifts]

def generate_remediation_scripts(drifts: list, intended_content: str, actual_content: str, file_format: str = "json", api_key: str = None) -> dict:
    """
    Generates Auto-Remediation scripts (Shell script, Ansible Playbook, Cisco IOS CLI commands, and Reconciled Config).
    Uses Gemini AI when available, otherwise constructs fallback templates.
    """
    key_to_use = api_key or os.environ.get("GEMINI_API_KEY")
    
    # Fallback default generator
    def get_fallback_remediation():
        bash_lines = ["#!/bin/bash", "# Auto-generated Drift Remediation Script by Config Drift Detector", "echo 'Applying Configuration Drift Fixes...'"]
        cisco_cli_lines = ["! Auto-Generated Cisco IOS Network CLI Remediation Script", "configure terminal"]
        ansible_tasks = []
        
        for d in drifts:
            k = d.get('key')
            old_val = d.get('old_value')
            new_val = d.get('new_value')
            t = d.get('type')
            
            if t == "Value Changed" or t == "Configuration Removed":
                bash_lines.append(f"# Fix for {k}: restore to '{old_val}'")
                bash_lines.append(f"echo 'Restoring {k} = {old_val}'")
                cisco_cli_lines.append(f"! Revert {k}")
                cisco_cli_lines.append(f"{k} {old_val if old_val is not None else ''}")
                ansible_tasks.append({
                    "name": f"Restore configuration setting {k}",
                    "setting": k,
                    "target_value": old_val,
                    "action": "update"
                })
            elif t == "Configuration Added":
                bash_lines.append(f"# Fix for {k}: remove unwanted setting '{new_val}'")
                bash_lines.append(f"echo 'Removing key {k}'")
                cisco_cli_lines.append(f"! Remove unapproved setting {k}")
                cisco_cli_lines.append(f"no {k}")
                ansible_tasks.append({
                    "name": f"Remove unapproved configuration setting {k}",
                    "setting": k,
                    "action": "remove"
                })
                
        cisco_cli_lines.append("end")
        cisco_cli_lines.append("write memory")
        
        bash_script = "\n".join(bash_lines) + "\n\necho 'Remediation completed successfully!'"
        cisco_cli_script = "\n".join(cisco_cli_lines)
        
        ansible_yaml = "---\n- name: Auto-Remediate Configuration Drift\n  hosts: localhost\n  tasks:\n"
        for task in ansible_tasks:
            ansible_yaml += f"    - name: {task['name']}\n      ansible.builtin.debug:\n        msg: \"Reverting {task['setting']} to target state ({task.get('target_value', 'removed')})\"\n"
            
        return {
            "shell_script": bash_script,
            "ansible_playbook": ansible_yaml,
            "cisco_ios_cli": cisco_cli_script,
            "reconciled_config": intended_content
        }

    if not key_to_use or not drifts:
        return get_fallback_remediation()

    try:
        genai.configure(api_key=key_to_use)
        prompt = f"""
You are an expert Network Engineer & DevOps Specialist (CCNA / CCNP / Ansible / Linux).
Given the following configuration drifts:
{json.dumps(drifts, indent=2)}

Original Intended Configuration:
{intended_content}

Generate:
1. `shell_script`: An executable Bash shell script (`#!/bin/bash`) that reverts these drifts on Linux servers.
2. `ansible_playbook`: A valid Ansible YAML playbook (`---`) to remediate these drifts across remote nodes.
3. `cisco_ios_cli`: Executable Cisco IOS CLI router/switch terminal commands (`configure terminal ... end write memory`) to revert CCNA networking & ACL drifts.
4. `reconciled_config`: The clean, correct configuration string that aligns live state back to intended state.

Return strictly JSON with keys "shell_script", "ansible_playbook", "cisco_ios_cli", and "reconciled_config".
Do not include markdown code block formatting in the output. Return raw JSON object.
"""
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text.strip())
        return {
            "shell_script": data.get("shell_script", get_fallback_remediation()["shell_script"]),
            "ansible_playbook": data.get("ansible_playbook", get_fallback_remediation()["ansible_playbook"]),
            "cisco_ios_cli": data.get("cisco_ios_cli", get_fallback_remediation()["cisco_ios_cli"]),
            "reconciled_config": data.get("reconciled_config", intended_content)
        }
    except Exception as e:
        print(f"Gemini Auto-Remediation failed: {e}")
        return get_fallback_remediation()

def perform_cybersecurity_audit(drifts: list) -> dict:
    """
    Performs automated cybersecurity and CCNA network infrastructure threat analysis on drifts.
    Maps changes to OWASP Top 10, PCI-DSS 4.1, CIS Benchmarks, and CCNA Network Protocol Security Rules.
    """
    audit_results = {
        "cyber_threat_level": "LOW",
        "threat_count": 0,
        "owasp_violations": [],
        "pci_dss_violations": [],
        "cis_benchmark_warnings": [],
        "network_port_alerts": [],
        "ccna_protocol_alerts": [],
        "security_score": 100
    }
    
    if not drifts:
        return audit_results

    threat_count = 0
    deductions = 0

    for d in drifts:
        key = str(d.get("key", "")).lower()
        old_val = str(d.get("old_value", ""))
        new_val = str(d.get("new_value", ""))

        # 1. CCNA Network Protocols & Cisco IOS Security (ACL, VLAN, OSPF, BGP, Port Security)
        if any(w in key for w in ['vlan', 'ospf', 'bgp', 'access-list', 'access-group', 'switchport', 'trunk', 'port-security', 'shutdown', 'nat', 'ip route']):
            threat_count += 1
            deductions += 25
            audit_results["ccna_protocol_alerts"].append({
                "protocol": "CCNA Enterprise Network Control",
                "setting": d["key"],
                "description": f"Critical network routing/ACL drift detected in '{d['key']}' ({old_val} -> {new_val}). Could cause VLAN hopping, routing loop, or unauthorized ACL bypass."
            })

        # 2. SSL/TLS Encryption (PCI-DSS 4.1 & OWASP A02 Cryptographic Failures)
        if 'ssl' in key or 'tls' in key or 'cert' in key or 'require_ssl' in key:
            threat_count += 1
            deductions += 25
            audit_results["pci_dss_violations"].append({
                "requirement": "PCI-DSS 4.1 (Encryption in Transit)",
                "setting": d["key"],
                "description": f"Setting '{d['key']}' changed from '{old_val}' to '{new_val}'. Disabling TLS/SSL exposes traffic to Man-In-The-Middle (MITM) packet sniffing."
            })

        # 3. Network Port Binding & Backdoor Check (CIS Benchmark & Network Security)
        if 'port' in key or 'host' in key:
            threat_count += 1
            deductions += 20
            audit_results["network_port_alerts"].append({
                "setting": d["key"],
                "old_value": old_val,
                "new_value": new_val,
                "alert": f"Network listening address modified ({old_val} -> {new_val}). Requires updating firewall ingress rules & security groups."
            })

        # 4. Security Misconfiguration & Debug Mode (OWASP A05:2021)
        if 'debug' in key or 'anonymous' in key or 'firewall' in key:
            threat_count += 1
            deductions += 20
            audit_results["owasp_violations"].append({
                "category": "OWASP A05: Security Misconfiguration",
                "setting": d["key"],
                "description": f"Misconfiguration detected in '{d['key']}' ({new_val}). Debug mode or disabled firewalls expose raw stack traces and system endpoints to public scanners."
            })

        # 5. Credential & Secret Exposure (OWASP A07 & CIS Benchmark)
        if 'password' in key or 'secret' in key or 'jwt' in key or 'token' in key or 'user' in key:
            threat_count += 1
            deductions += 25
            audit_results["cis_benchmark_warnings"].append({
                "control": "CIS Benchmark 5.2 (Identity & Credential Protection)",
                "setting": d["key"],
                "warning": f"Credential/Key change detected in '{d['key']}'. Ensure unauthorized admin accounts or leaked JWT secrets are rotated immediately."
            })

    audit_results["threat_count"] = threat_count
    audit_results["security_score"] = max(0, 100 - deductions)
    
    if audit_results["security_score"] < 50:
        audit_results["cyber_threat_level"] = "CRITICAL / SEVERE"
    elif audit_results["security_score"] < 75:
        audit_results["cyber_threat_level"] = "HIGH THREAT"
    elif audit_results["security_score"] < 90:
        audit_results["cyber_threat_level"] = "MEDIUM RISK"
    else:
        audit_results["cyber_threat_level"] = "LOW RISK"

    return audit_results

def predict_security_attack_patterns(drifts: list, history: list = None) -> dict:
    """
    Predicts multi-stage attack patterns and future security risks based on current drifts and historical changes.
    Recognizes threat sequences like:
    - Sequence A: Port Modification + Firewall Override + Credential Change (Backdoor Account & Lateral Movement Attack)
    - Sequence B: SSL/TLS Disabled + Remote DB URL Changed + Firewall Open (Data Exfiltration / Man-In-The-Middle Attack)
    - Sequence C: Connection Limits Lowered + Debug Mode Enabled + Timeouts Increased (DoS / Resource Exhaustion Attack)
    """
    predictive_report = {
        "has_attack_pattern": False,
        "predicted_attack_vector": "Normal Operational Baseline",
        "attack_risk_level": "LOW",
        "predicted_future_score": 10,
        "pattern_matches": [],
        "preventive_countermeasures": [],
        "sequence_chain": []
    }
    
    if not drifts:
        return predictive_report

    # Collect all keys involved in current run + recent history
    current_keys = [str(d.get("key", "")).lower() for d in drifts]
    all_historical_keys = list(current_keys)
    
    if history:
        for h in history[:5]:
            for hd in h.get("drifts", []):
                all_historical_keys.append(str(hd.get("key", "")).lower())

    def has_key(keys_list, terms):
        return any(any(term in k for term in terms) for k in keys_list)

    has_port = has_key(all_historical_keys, ['port', 'host', 'listen'])
    has_firewall = has_key(all_historical_keys, ['firewall', 'ufw', 'access-list', 'acl', 'secgroup'])
    has_user = has_key(all_historical_keys, ['user', 'password', 'secret', 'admin', 'auth'])
    has_ssl = has_key(all_historical_keys, ['ssl', 'tls', 'cert', 'require_ssl'])
    has_db = has_key(all_historical_keys, ['db', 'database', 'url', 'postgres'])
    has_debug = has_key(all_historical_keys, ['debug', 'anonymous', 'trace'])
    has_limit = has_key(all_historical_keys, ['max', 'limit', 'timeout', 'pool', 'retry'])

    sequence_chain = []
    pattern_matches = []
    countermeasures = []
    future_score = 20

    # Pattern 1: Unauthorized Access & Backdoor Persistence Attack
    if has_port and (has_user or has_firewall):
        predictive_report["has_attack_pattern"] = True
        future_score += 40
        if has_port:
            sequence_chain.append("Day 1: Port / Listening Host Modified")
        if has_firewall:
            sequence_chain.append("Day 2: Firewall / ACL Rules Relaxed or Overridden")
        if has_user:
            sequence_chain.append("Day 3: Security Credentials / Admin User Altered")
            
        pattern_matches.append({
            "pattern_name": "Backdoor Access & Lateral Movement Sequence",
            "severity": "CRITICAL ATTACK RISK",
            "description": "Detected a progressive multi-stage sequence involving port changes, firewall alterations, and credential edits. This pattern strongly indicates adversary lateral movement to establish a persistent backdoor.",
            "predicted_impact": "Potential unauthorized remote shell execution, unmonitored administrative access, and complete cloud server takeover."
        })
        
        countermeasures.append("Rotate all admin keys/passwords immediately and execute 'cisco_remediate.cfg' or 'fix_drift.sh'.")
        countermeasures.append("Inspect active system connections with 'netstat -tulpn' or 'ss -tulpn' for unauthorized listening sockets.")

    # Pattern 2: Data Exfiltration & MITM Eavesdropping Pathway
    if (has_ssl or has_db) and (has_firewall or has_port):
        predictive_report["has_attack_pattern"] = True
        future_score += 35
        if has_ssl:
            sequence_chain.append("Phase 1: Data-In-Transit TLS Encryption Disabled")
        if has_db:
            sequence_chain.append("Phase 2: Remote Database Connection Host Shifted")
        if has_firewall or has_port:
            sequence_chain.append("Phase 3: Network Security Boundaries Relaxed")
            
        pattern_matches.append({
            "pattern_name": "Data Exfiltration & Packet Eavesdropping (MITM) Pathway",
            "severity": "HIGH ATTACK RISK",
            "description": "Combining unencrypted traffic settings (ssl: false) with modified database URLs or network ports opens a direct vector for packet sniffing and database hijacking.",
            "predicted_impact": "Exposure of unencrypted customer PII/PCI data over public network streams, triggering regulatory compliance fines."
        })
        
        countermeasures.append("Enforce strict TLS 1.3 encryption across all database and API endpoints.")
        countermeasures.append("Audit external database host IP addresses against trusted subnet whitelist.")

    # Pattern 3: DoS Amplification / System Instability Attack
    if has_debug and (has_limit or has_port):
        predictive_report["has_attack_pattern"] = True
        future_score += 25
        sequence_chain.append("Phase 1: Debug Mode Activated in Production")
        sequence_chain.append("Phase 2: Operational Timeouts / Resource Limits Altered")
        
        pattern_matches.append({
            "pattern_name": "Resource Exhaustion & DoS Vulnerability Pattern",
            "severity": "MEDIUM-HIGH RISK",
            "description": "Active debug flags combined with modified connection limits expose detailed stack traces to public scanners and risk memory leaks.",
            "predicted_impact": "Application crash under mild traffic load due to memory leak or thread starvation."
        })
        
        countermeasures.append("Turn off debug logging (debug: false) and restore baseline connection pool settings.")

    # Assign results
    predictive_report["predicted_future_score"] = min(100, future_score)
    predictive_report["pattern_matches"] = pattern_matches
    predictive_report["preventive_countermeasures"] = countermeasures
    predictive_report["sequence_chain"] = sequence_chain
    
    if future_score >= 75:
        predictive_report["predicted_attack_vector"] = "High Threat Multi-Stage Attack Pattern Detected"
        predictive_report["attack_risk_level"] = "CRITICAL PREDICTED THREAT"
    elif future_score >= 50:
        predictive_report["predicted_attack_vector"] = "Medium-High Security Vulnerability Projection"
        predictive_report["attack_risk_level"] = "HIGH PREDICTED THREAT"
    elif future_score >= 30:
        predictive_report["predicted_attack_vector"] = "Minor Operational Risk Projection"
        predictive_report["attack_risk_level"] = "MODERATE RISK"
    else:
        predictive_report["predicted_attack_vector"] = "Clean Configuration Trajectory"
        predictive_report["attack_risk_level"] = "LOW RISK"

    return predictive_report

def answer_drift_chat(user_message: str, drifts: list = None, api_key: str = None) -> str:
    """
    Answers user questions regarding configuration drift, infrastructure risk, and remediation.
    Uses Gemini API when available, otherwise falls back to a typo-tolerant conversational assistant.
    """
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and (len(env_key) < 20 or "YOUR_" in env_key or "invalid" in env_key):
        env_key = None
        
    key_to_use = api_key or env_key

    def get_rule_reply():
        msg_lower = user_message.lower().strip()
        drift_count = len(drifts) if drifts else 0
        
        # Fuzzy matcher helper
        def contains_any(words):
            for w in words:
                if w in msg_lower:
                    return True
                if len(w) >= 4:
                    for token in msg_lower.split():
                        clean_token = ''.join(c for c in token if c.isalnum())
                        if len(clean_token) >= 3 and (clean_token in w or w in clean_token):
                            return True
            return False

        # Identity / Location / Who are you / Where are you
        if any(phrase in msg_lower for phrase in ['where', 'who are', 'what are you', 'your name', 'where are u', 'who r u', 'location']):
            return f"🤖 I am **Drift AI**, your intelligent DevOps & Infrastructure Security Assistant built into **Config Drift Detector**! I am hosted on your local server (`http://127.0.0.1:8001`) with **{drift_count} drift(s)** currently in context."

        # Greetings
        elif contains_any(['hello', 'hi', 'hey', 'greetings', 'good morning', 'good evening']):
            return f"Hello! 👋 I am **Drift AI**, your DevOps & Cybersecurity Assistant. You currently have **{drift_count} active drift(s)** loaded. How can I help you analyze or remediate them?"

        # Firewall & Network (handles 'firewall', 'irewaall', 'firewal', 'ufw', 'iptables', 'security group')
        elif contains_any(['firewall', 'firewal', 'irewall', 'irewaall', 'ufw', 'iptables', 'secgroup']):
            return ("🛡️ **Firewall & Network Configuration**:\n"
                    "When port numbers change (e.g. 8080 -> 9090), your firewall will block incoming connections unless updated.\n"
                    "• **Ubuntu/Debian (ufw)**: `sudo ufw allow 9090/tcp`\n"
                    "• **RHEL/CentOS**: `sudo firewall-cmd --add-port=9090/tcp --permanent && sudo firewall-cmd --reload`\n"
                    "• **AWS**: Update your Security Group Inbound Rules for port 9090.")

        # SSL / TLS / Security (handles 'ssl', 'tls', 'security', 'secutiy', 'password', 'auth', 'secret', 'cyber')
        elif contains_any(['ssl', 'tls', 'cert', 'security', 'secutiy', 'cyber', 'encrypt', 'password', 'auth', 'secret']):
            return ("🔐 **Security Risk Assessment**:\n"
                    "Disabling SSL/TLS or changing database credentials in live environments exposes data in transit to Man-In-The-Middle (MITM) attacks and breaches compliance rules (PCI-DSS/HIPAA). Always enforce TLS 1.2/1.3 in production.")

        # Fix / Remediation / Script
        elif contains_any(['fix', 'remediate', 'script', 'ansible', 'bash', 'reconciliation']):
            return ("⚡ **Auto-Remediation Helper**:\n"
                    "You can generate automated fix scripts in 1 click! Click the **'⚡ Auto-Remediate (AI Fix)'** button at the top of the Analysis Results section to download Bash scripts and Ansible playbooks.")

        # Port
        elif contains_any(['port', 'ports', 'pord']):
            return ("🌐 **Port Configuration Change**:\n"
                    "Changing server or database listening ports alters how clients and load balancers route traffic. Ensure reverse proxies (NGINX/HAProxy) and firewalls are synchronized.")

        # Database
        elif contains_any(['db', 'database', 'postgres', 'mysql', 'mongo']):
            return ("🗄️ **Database Drift Analysis**:\n"
                    "Database URL or connection pool changes can result in immediate 500 Internal Server Errors or data mismatch if connected to a wrong target database instance.")

        # Help / What can you do
        elif contains_any(['help', 'what can', 'features', 'options']):
            return ("💡 **What I Can Do**:\n"
                    "1. Analyze **Firewall** rules & port changes.\n"
                    "2. Evaluate **Security** & SSL risks.\n"
                    "3. Explain **Database** configuration drifts.\n"
                    "4. Guide you on **Auto-Fixing** with Ansible & Bash scripts.\n"
                    "5. Answer general DevOps & SRE questions!")

        # Why / Explanation / General questions
        elif contains_any(['why', 'what', 'how', 'explain', 'reason', 'anything']):
            if drifts:
                keys = [d.get('key', 'setting') for d in drifts[:3]]
                return (f"🧐 **Drift Analysis Summary**:\n"
                        f"Your configuration has **{drift_count} drift(s)** detected in settings: `{', '.join(keys)}`.\n"
                        "These changes alter the runtime environment of your service. Ask me about specific keys like 'port', 'ssl', or 'firewall' for details!")
            else:
                return ("🔍 **No Drifts Loaded Yet**:\n"
                        "Please upload your **Intended** and **Actual** configuration files on the Drift Analysis page and click **'Analyze Drift'** first. Once analyzed, I will evaluate every single change for you!")

        # Default fallback
        else:
            if drifts:
                return f"🤖 **Drift AI**: I reviewed your question about '{user_message}'. I have **{drift_count} active drift(s)** in context. Ask me about **firewall**, **ports**, **security risks**, or **how to fix**!"
            else:
                return f"🤖 **Drift AI**: Hello! I am your DevOps Assistant. Ask me about **firewalls**, **ports**, **security risks**, **who I am**, or click **'Analyze Drift'** to analyze files!"

    if not key_to_use:
        return get_rule_reply()

    try:
        genai.configure(api_key=key_to_use)
        context_str = json.dumps(drifts or [], indent=2)
        prompt = f"""
You are "Drift AI", an expert DevOps, Cybersecurity, and Site Reliability AI assistant.
Answer the user's question clearly, concisely, and helpfully.

Current Configuration Drifts Context:
{context_str}

User Question: {user_message}

Provide a direct, friendly, and technical answer. Keep code snippets short if requested.
"""
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini Chat error: {e}")
        return get_rule_reply()


