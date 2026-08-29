import json
import re
import yaml
from deepdiff import DeepDiff

def parse_cisco_ios(content: str) -> dict:
    """
    Parses Cisco IOS configuration text into a structured dictionary.
    Handles top-level commands, sub-block indented commands (interfaces, routers, vlans), and access lists.
    """
    config_dict = {}
    current_block = None
    
    for line in content.splitlines():
        line_str = line.strip('\r\n')
        # Skip empty lines or comment lines
        if not line_str or line_str.startswith('!') or line_str.startswith('#'):
            continue
            
        # Check indentation level (2 or more leading spaces or a tab indicates sub-command)
        is_indented = line.startswith(' ') or line.startswith('\t')
        
        if is_indented and current_block:
            sub_cmd = line_str.strip()
            # Store under current block
            if isinstance(config_dict[current_block], dict):
                # Split key and value if possible (e.g. "ip address 192.168.1.1 255.255.255.0")
                parts = sub_cmd.split(' ', 1)
                sub_key = parts[0]
                sub_val = parts[1] if len(parts) > 1 else True
                
                # If sub_key already exists, convert to list or aggregate
                if sub_key in config_dict[current_block]:
                    existing = config_dict[current_block][sub_key]
                    if isinstance(existing, list):
                        existing.append(sub_val)
                    else:
                        config_dict[current_block][sub_key] = [existing, sub_val]
                else:
                    config_dict[current_block][sub_key] = sub_val
            elif isinstance(config_dict[current_block], list):
                config_dict[current_block].append(sub_cmd)
        else:
            # Top-level command block
            parts = line_str.split(' ', 1)
            cmd_key = line_str
            
            # Special handling for repetitive blocks like interface, router, vlan, line, access-list
            if parts[0] in ['interface', 'router', 'vlan', 'line', 'ip', 'access-list', 'crypto', 'class-map', 'policy-map']:
                current_block = line_str
                if current_block not in config_dict:
                    config_dict[current_block] = {}
            else:
                current_block = None
                key = parts[0]
                val = parts[1] if len(parts) > 1 else True
                config_dict[key] = val
                
    return config_dict

def parse_config(content: str, file_format: str) -> dict:
    """
    Parses configuration content (JSON, YAML, or Cisco IOS) into a Python dictionary.
    """
    if not content or not content.strip():
        return {}
        
    file_format = (file_format or "").lower()
    
    if file_format in ['cisco', 'ios', 'cfg']:
        return parse_cisco_ios(content)
    elif file_format in ['json']:
        return json.loads(content)
    elif file_format in ['yaml', 'yml']:
        return yaml.safe_load(content) or {}
    else:
        # Auto-detect: check if content looks like Cisco IOS config
        if any(keyword in content for keyword in ['interface ', 'router ospf', 'ip address ', 'hostname ', 'vlan ', 'enable secret']):
            try:
                return parse_cisco_ios(content)
            except Exception:
                pass
                
        # Try JSON first, then YAML
        try:
            return json.loads(content)
        except Exception:
            try:
                return yaml.safe_load(content) or {}
            except Exception:
                # Fallback to Cisco IOS parser if text with newlines
                try:
                    return parse_cisco_ios(content)
                except Exception:
                    raise ValueError("Unsupported format or invalid syntax. Please upload valid JSON, YAML, or Cisco IOS configuration.")

def clean_path(path_str: str) -> str:
    """
    Converts DeepDiff path syntax like root['server']['port'] or root['settings'][0]['name']
    into a cleaner dot notation: server.port or settings[0].name.
    """
    # Remove 'root' prefix
    if path_str.startswith("root"):
        path_str = path_str[4:]
    
    def bracket_replacer(match):
        val = match.group(1)
        if val.isdigit():
            return f"[{val}]"
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            val = val[1:-1]
        return f".{val}"
        
    path_str = re.sub(r"\[([^\]]+)\]", bracket_replacer, path_str)
    
    # Clean up double dots and leading/trailing dots
    path_str = path_str.replace("..", ".")
    if path_str.startswith("."):
        path_str = path_str[1:]
    if path_str.endswith("."):
        path_str = path_str[:-1]
        
    return path_str

def get_severity(key_path: str) -> str:
    """
    Categorizes the severity based on the key name.
    - Breaking: SSL, Port, Database, Authentication, Security settings, CCNA Critical Networking (IP, Subnet, OSPF, BGP, VLAN, ACL, Shutdown, HTTP)
    - Functional: Timeout, Memory, Retry, Cache, Performance settings, STP, HSRP, NTP, DNS, SNMP
    - Cosmetic: Labels, Descriptions, Display names, comments, etc. (Default fallback)
    """
    key_lower = key_path.lower()
    
    # Breaking terms (System Security & Critical CCNA Networking parameters)
    breaking_terms = [
        'ssl', 'tls', 'port', 'db', 'database', 'auth', 'password', 'passwd',
        'key', 'secret', 'security', 'cert', 'token', 'credential', 'username',
        'allow', 'deny', 'firewall', 'admin', 'encrypt', 'http',
        # CCNA & Cisco Networking Critical Keys
        'ip address', 'ip', 'address', 'subnet', 'vlan', 'ospf', 'bgp', 'eigrp', 'access-list',
        'access-group', 'switchport mode', 'switchport access', 'trunk', 'switchport',
        'port-security', 'shutdown', 'enable secret', 'crypto', 'vpn', 'nat', 'ip route'
    ]
    
    # Functional terms (Operational & Networking protocols)
    functional_terms = [
        'timeout', 'memory', 'retry', 'cache', 'max', 'min', 'size', 'limit',
        'pool', 'interval', 'debug', 'enable', 'disabled', 'host', 'url',
        'endpoint', 'connection', 'thread', 'worker', 'buffer', 'period',
        'policy', 'mode', 'strategy', 'target', 'directory', 'path', 'hostname',
        # CCNA & Networking Operational Keys
        'spanning-tree', 'stp', 'hsrp', 'vrrp', 'ntp', 'dns', 'snmp', 'logging',
        'duplex', 'speed', 'mtu', 'banner', 'clock', 'description'
    ]
    
    # Check breaking first
    if any(term in key_lower for term in breaking_terms):
        return 'Breaking'
        
    # Check functional
    if any(term in key_lower for term in functional_terms):
        return 'Functional'
        
    # Default is Cosmetic
    return 'Cosmetic'

def detect_drift(intended_content: str, actual_content: str, file_format: str) -> list:
    """
    Compares the intended configuration with actual configuration and returns a list of drifts.
    """
    intended = parse_config(intended_content, file_format)
    actual = parse_config(actual_content, file_format)
    
    # Run DeepDiff
    # verbose_level=2 returns the values of the changes
    diff = DeepDiff(intended, actual, ignore_order=True, verbose_level=2)
    drifts = []
    
    # 1. Values Changed
    if 'values_changed' in diff:
        for path, change in diff['values_changed'].items():
            cleaned_key = clean_path(path)
            drifts.append({
                'key': cleaned_key,
                'type': 'Value Changed',
                'old_value': change.get('old_value'),
                'new_value': change.get('new_value'),
                'severity': get_severity(cleaned_key)
            })
            
    # 2. Dictionary Items Added (Exist in actual/live, but not in intended)
    if 'dictionary_item_added' in diff:
        # In deepdiff, value is in the new dict
        for path in diff['dictionary_item_added']:
            cleaned_key = clean_path(path)
            # Find value in actual
            val = diff['dictionary_item_added'][path]
            drifts.append({
                'key': cleaned_key,
                'type': 'Configuration Added',
                'old_value': None,
                'new_value': val,
                'severity': get_severity(cleaned_key)
            })
            
    # 3. Dictionary Items Removed (Exist in intended, but missing in actual/live)
    if 'dictionary_item_removed' in diff:
        for path in diff['dictionary_item_removed']:
            cleaned_key = clean_path(path)
            val = diff['dictionary_item_removed'][path]
            drifts.append({
                'key': cleaned_key,
                'type': 'Configuration Removed',
                'old_value': val,
                'new_value': None,
                'severity': get_severity(cleaned_key)
            })
            
    # 4. Type changes
    if 'type_changes' in diff:
        for path, change in diff['type_changes'].items():
            cleaned_key = clean_path(path)
            drifts.append({
                'key': cleaned_key,
                'type': 'Type Changed',
                'old_value': f"{change.get('old_value')} ({change.get('old_type').__name__})",
                'new_value': f"{change.get('new_value')} ({change.get('new_type').__name__})",
                'severity': get_severity(cleaned_key)
            })
            
    return drifts

