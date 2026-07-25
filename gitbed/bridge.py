import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

CACHE_FILE_PATH = ".gitbed_rules.json"

DEFAULT_RULES = [
    {
        "rule_id": "standard_macro_pin",
        "match_pattern": r"(#define\s+{signal}_PIN\s+){old_pin}",
        "replace_pattern": r"\g<1>{new_pin}",
        "description": "Matches standard #define SIGNAL_PIN OLD_PIN declarations",
    },
    {
        "rule_id": "standard_macro_signal",
        "match_pattern": r"(#define\s+{signal}\s+){old_pin}",
        "replace_pattern": r"\g<1>{new_pin}",
        "description": "Matches standard #define SIGNAL OLD_PIN declarations",
    },
    {
        "rule_id": "constexpr_pin_assignment",
        "match_pattern": r"(constexpr\s+\w+\s+{signal}\s*=\s*){old_pin}",
        "replace_pattern": r"\g<1>{new_pin}",
        "description": "Matches C++ constexpr pin declarations",
    },
]


class BridgeCache:
    """Manages loading, persisting, and applying deterministic bridge rules."""

    def __init__(self, cache_file: str = CACHE_FILE_PATH):
        self.cache_file = cache_file
        self.rules: List[Dict[str, str]] = []
        self._load_cache()

    def _load_cache(self):
        self.rules = list(DEFAULT_RULES)
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    custom_rules = json.load(f)
                    for rule in custom_rules:
                        if rule not in self.rules:
                            self.rules.append(rule)
                logger.info(f"Loaded {len(self.rules)} bridge rules from '{self.cache_file}'")
            except Exception as exc:
                logger.warning(f"Could not load bridge cache file: {exc}")

    def save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, indent=2)
            logger.info(f"Saved {len(self.rules)} bridge rules to '{self.cache_file}'")
        except Exception as exc:
            logger.warning(f"Could not save bridge cache file: {exc}")

    def apply_rules(self, code: str, diff_data: dict) -> Tuple[bool, str, Optional[str]]:
        signal = diff_data.get("signal_name", "")
        old_pin = diff_data.get("old_pin", "")
        new_pin = diff_data.get("new_pin", "")

        if not signal or not new_pin:
            return False, code, None

        for rule in self.rules:
            pattern_str = rule.get("match_pattern", "")
            replace_str = rule.get("replace_pattern", "")

            # Interpolate pattern variables
            try:
                formatted_pattern = pattern_str.format(
                    signal=re.escape(signal),
                    old_pin=re.escape(old_pin) if old_pin else r"\w+",
                )
                formatted_replace = replace_str.format(new_pin=new_pin)

                if re.search(formatted_pattern, code):
                    updated_code = re.sub(formatted_pattern, formatted_replace, code)
                    if updated_code != code and new_pin in updated_code:
                        logger.info(f"Cache HIT: Applied bridge rule '{rule.get('rule_id')}'")
                        return True, updated_code, rule.get("rule_id")
            except Exception as exc:
                logger.debug(f"Rule match error for '{rule.get('rule_id')}': {exc}")

        return False, code, None

    def add_rule(self, rule_data: dict):
        rule_id = rule_data.get("rule_id")
        if not rule_id or not rule_data.get("match_pattern") or not rule_data.get("replace_pattern"):
            return

        # Check if rule exists
        for existing in self.rules:
            if existing.get("rule_id") == rule_id:
                return

        self.rules.append(rule_data)
        self.save_cache()
        logger.info(f"Synthesized and cached new bridge rule '{rule_id}'")
