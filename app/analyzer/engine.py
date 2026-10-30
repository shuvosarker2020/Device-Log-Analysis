import time
import logging
from typing import Optional, Tuple, List
from app.core.models import NormalizedLog, AlertEvent
from app.analyzer.rules import DEFAULT_RULES, AlertRule
from app.config import cfg

logger = logging.getLogger("NetLogIQ.Analyzer")

class AnalyzerEngine:
    def __init__(self):
        self.rules: List[AlertRule] = list(DEFAULT_RULES)
        # In-memory alert cooldown tracker: key -> last_alert_time
        self._alert_cooldowns = {}

    def analyze(self, log: NormalizedLog) -> Tuple[NormalizedLog, Optional[AlertEvent]]:
        """
        Analyze a normalized log message:
        1. Categorize event (REBOOT, POWER_SUPPLY, HIGH_CPU, etc.)
        2. Evaluate critical rules
        3. Create AlertEvent if matched and apply cooldown suppression
        """
        full_text = f"{log.mnemonic} {log.clean_message} {log.raw_message}"
        matched_rule: Optional[AlertRule] = None

        # Test against rules
        for rule in self.rules:
            if rule.matches(full_text):
                matched_rule = rule
                log.event_category = rule.category
                if rule.severity_override is not None:
                    # Apply severity override if it is more critical
                    if rule.severity_override < log.severity:
                        log.severity = rule.severity_override
                        log.severity_name = rule.name
                break

        # If no rule matched, but severity is naturally critical (0=Emergency, 1=Alert, 2=Critical)
        is_alert_condition = False
        rule_name = "System Critical Event"
        category = log.event_category

        if matched_rule:
            is_alert_condition = True
            rule_name = matched_rule.name
            log.is_alert = True
            log.alert_rule = matched_rule.name
        elif log.severity <= 2:
            is_alert_condition = True
            rule_name = f"High Severity Syslog ({log.severity_name})"
            log.is_alert = True
            log.alert_rule = rule_name

        if not is_alert_condition:
            return log, None

        # Check cooldown to prevent alert storm
        cooldown_sec = cfg.get("alerts", "cooldown_seconds", default=60)
        cooldown_key = f"{log.hostname or log.source_ip}:{category}:{rule_name}"
        now = time.time()
        last_alert_time = self._alert_cooldowns.get(cooldown_key, 0)

        should_notify = (now - last_alert_time) >= cooldown_sec
        if should_notify:
            self._alert_cooldowns[cooldown_key] = now

        alert = AlertEvent(
            source_ip=log.source_ip,
            hostname=log.hostname,
            vendor=log.vendor,
            rule_name=rule_name,
            category=category,
            severity=log.severity,
            severity_name=log.severity_name,
            message=log.clean_message or log.raw_message,
            status="ACTIVE",
            metadata={"cooldown_suppressed": not should_notify} if hasattr(AlertEvent, "metadata") else {}
        )

        return log, alert if should_notify else None

analyzer_engine = AnalyzerEngine()
