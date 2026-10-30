import os
import yaml
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"

DEFAULT_CONFIG: Dict[str, Any] = {
    "server": {
        "host": "0.0.0.0",
        "web_port": 8000,
        "syslog_udp_port": 1514,
        "syslog_tcp_port": 1514,
        "enable_tcp": True,
        "enable_udp": True,
    },
    "database": {
        "path": "data/syslog_analyzer.db",
        "retention_days": 30,
    },
    "alerts": {
        "cooldown_seconds": 60,
        "auto_acknowledge_minutes": 0,
        "sound_alert_enabled": True,
    },
    "notifications": {
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
        },
        "slack": {
            "enabled": False,
            "webhook_url": "",
            "channel": "#network-alerts",
        },
        "discord": {
            "enabled": False,
            "webhook_url": "",
        },
        "ms_teams": {
            "enabled": False,
            "webhook_url": "",
        },
        "generic_webhook": {
            "enabled": False,
            "webhook_url": "",
            "headers": {},
        },
        "email": {
            "enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "use_tls": True,
            "username": "",
            "password": "",
            "from_email": "netlog-alerts@company.com",
            "to_emails": [],
        },
    },
    "rules": {
        "high_cpu_threshold": 85,
        "high_mem_threshold": 85,
    },
}

class ConfigManager:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance.load()
        return cls._instance

    def load(self) -> Dict[str, Any]:
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    user_cfg = yaml.safe_load(f) or {}
                    self._config = self._deep_merge(DEFAULT_CONFIG.copy(), user_cfg)
            except Exception as e:
                print(f"[Config] Error loading config.yaml: {e}. Using defaults.")
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()
            self.save()
        return self._config

    def save(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print(f"[Config] Error saving config.yaml: {e}")

    def get(self, *keys, default=None) -> Any:
        curr = self._config
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return default
        return curr

    def set(self, keys: List[str], value: Any):
        curr = self._config
        for k in keys[:-1]:
            if k not in curr or not isinstance(curr[k], dict):
                curr[k] = {}
            curr = curr[k]
        curr[keys[-1]] = value
        self.save()

    def update_notifications(self, notif_data: Dict[str, Any]):
        if "notifications" not in self._config:
            self._config["notifications"] = {}
        for k, v in notif_data.items():
            self._config["notifications"][k] = v
        self.save()

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    def _deep_merge(self, base: dict, update: dict) -> dict:
        for k, v in update.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                base[k] = self._deep_merge(base[k], v)
            else:
                base[k] = v
        return base

# Global singleton
cfg = ConfigManager()
