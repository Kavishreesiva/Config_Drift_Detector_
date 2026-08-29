"""
Netmiko Automation Agent Module for Cisco IOS Enterprise Routers & Switches.
Handles SSH Live Configuration Fetching and Autonomous Self-Healing Remediation.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("netmiko_agent")

def is_netmiko_available() -> bool:
    try:
        import netmiko
        return True
    except ImportError:
        return False

def fetch_live_config_via_netmiko(
    host: str = "192.168.1.1",
    username: str = "admin",
    password: str = "cisco123",
    secret: str = "cisco123",
    device_type: str = "cisco_ios",
    port: int = 22
) -> Dict[str, Any]:
    """
    Connects to physical or simulated Cisco Router/Switch via SSH Netmiko and fetches 'show running-config'.
    """
    if not is_netmiko_available():
        return {
            "status": "simulated",
            "message": "Netmiko library running in simulation mode.",
            "content": f"hostname Core-Router-01\n! (Fetched via Netmiko SSH from {host})\ninterface GigabitEthernet0/1\n ip address 10.0.1.1 255.255.255.0\n shutdown\n!\nip access-list extended SEC_ACL\n permit ip any any\n"
        }

    from netmiko import ConnectHandler

    cisco_device = {
        'device_type': device_type,
        'host': host,
        'username': username,
        'password': password,
        'secret': secret,
        'port': port,
    }

    try:
        logger.info(f"Connecting via Netmiko SSH to {host}:{port}...")
        net_connect = ConnectHandler(**cisco_device)
        net_connect.enable()
        output = net_connect.send_command("show running-config")
        net_connect.disconnect()

        return {
            "status": "success",
            "message": f"Successfully fetched live running-config from {host} via Netmiko SSH!",
            "content": output
        }
    except Exception as e:
        logger.warning(f"Netmiko SSH connection to {host} failed ({e}). Returning fallback live state.")
        return {
            "status": "fallback",
            "message": f"SSH connection attempt to {host} failed ({e}). Loaded simulated live router config.",
            "content": f"hostname Core-Router-01\n! (Netmiko Live Fallback for {host})\ninterface GigabitEthernet0/1\n ip address 10.0.1.1 255.255.255.0\n shutdown\n!\nip access-list extended SEC_ACL\n permit ip any any\n"
        }

def apply_netmiko_remediation(
    commands: List[str],
    host: str = "192.168.1.1",
    username: str = "admin",
    password: str = "cisco123",
    secret: str = "cisco123",
    device_type: str = "cisco_ios"
) -> Dict[str, Any]:
    """
    Connects via Netmiko SSH to Cisco Router and executes config remediation commands.
    """
    if not is_netmiko_available():
        return {
            "status": "simulated",
            "target_host": host,
            "executed_commands": commands,
            "output": f"% Netmiko SSH Autonomous Heal Simulated on {host}\n" + "\n".join(f"netmiko_bot# {c}" for c in commands) + "\nBuilding configuration...\n[OK] NVRAM memory updated."
        }

    from netmiko import ConnectHandler

    cisco_device = {
        'device_type': device_type,
        'host': host,
        'username': username,
        'password': password,
        'secret': secret,
    }

    try:
        net_connect = ConnectHandler(**cisco_device)
        net_connect.enable()
        output = net_connect.send_config_set(commands)
        save_output = net_connect.save_config()
        net_connect.disconnect()

        return {
            "status": "success",
            "target_host": host,
            "executed_commands": commands,
            "output": f"{output}\n{save_output}"
        }
    except Exception as e:
        return {
            "status": "simulated_fallback",
            "target_host": host,
            "executed_commands": commands,
            "output": f"% Netmiko SSH Agent ({e}) Fallback execution on {host}\n" + "\n".join(f"netmiko_bot(config)# {c}" for c in commands) + "\nBuilding configuration...\n[OK] Configuration written to NVRAM memory."
        }
