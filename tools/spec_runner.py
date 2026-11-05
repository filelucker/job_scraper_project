"""
Spec Runner for api-anything JSON specifications.
Executes operations defined in api-anything site specs using Python direct HTTP
(Tier 1) with optional browser fallback (Tier 2).
"""

import re
import json
from typing import Dict, Any, List, Optional
import requests


def extract_json_path(data: Any, path: Optional[str]) -> Any:
    """Extracts a sub-object from nested dictionaries/lists using dot-notation."""
    if not path or not data:
        return data

    parts = path.split(".")
    current = data

    for part in parts:
        if current is None:
            return None
        # Handle wildcard array extraction like elements[*] or elements[0]
        array_match = re.match(r"^([^\[]+)\[(\*|\d+)\]$", part)
        if array_match:
            prop_name, idx_str = array_match.groups()
            if isinstance(current, dict):
                current = current.get(prop_name)
            else:
                return None

            if not isinstance(current, list):
                return None

            if idx_str == "*":
                # Flatten / map across list
                continue
            else:
                idx = int(idx_str)
                current = current[idx] if idx < len(current) else None
        else:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

    return current


class SpecRunner:
    """Loads and executes operations defined in api-anything site specs."""

    def __init__(self, spec_source: Any):
        """
        spec_source can be:
        - A filepath string (e.g. 'tools/api_anything/sites/ashby.json')
        - A dictionary already loaded
        """
        if isinstance(spec_source, str):
            with open(spec_source, "r", encoding="utf-8") as f:
                self.spec = json.load(f)
        elif isinstance(spec_source, dict):
            self.spec = spec_source
        else:
            raise ValueError("spec_source must be a filepath string or dictionary")

        self.name = self.spec.get("name", "unknown")
        self.operations: Dict[str, Dict[str, Any]] = {
            op["name"]: op for op in self.spec.get("operations", [])
        }

    def get_operation(self, operation_name: str) -> Optional[Dict[str, Any]]:
        return self.operations.get(operation_name)

    def execute(
        self,
        operation_name: str,
        params: Optional[Dict[str, Any]] = None,
        cookies: Optional[Dict[str, str]] = None,
        session: Optional[requests.Session] = None,
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        Executes a spec operation via Tier 1 (plain HTTP requests).
        Resolves slots, parameters, and extracts response data.
        """
        op = self.get_operation(operation_name)
        if not op:
            raise ValueError(f"Operation '{operation_name}' not found in spec '{self.name}'. Available: {list(self.operations.keys())}")

        params = params or {}
        cookies = cookies or {}
        req_def = op.get("request", {})
        method = req_def.get("method", "GET").upper()
        raw_url = req_def.get("url", "")
        headers = dict(req_def.get("headers", {}))
        body = req_def.get("body")

        # 1. Parameter substitution in URL
        url = raw_url
        for k, v in params.items():
            url = url.replace(f"%7B{k}%7D", str(v)).replace(f"{{{k}}}", str(v))

        # 2. Process slots
        slots = op.get("slots", [])
        for slot in slots:
            # Handle cookie refs (e.g. cookie:JSESSIONID -> header:csrf-token)
            cookie_ref = slot.get("ref")
            if cookie_ref and cookie_ref.startswith("cookie:"):
                cookie_name = cookie_ref.split(":", 1)[1]
                cookie_val = cookies.get(cookie_name, "")
                if slot.get("transform") == "strip-quotes":
                    cookie_val = cookie_val.strip("\"'")
                for at in slot.get("at", []):
                    if at.startswith("header:"):
                        h_name = at.split(":", 1)[1]
                        headers[h_name] = cookie_val

            # Handle param substitution in headers or body
            param_name = slot.get("param")
            if param_name and param_name in params:
                param_val = params[param_name]
                template = slot.get("template")
                final_val = template.replace(f"{{{param_name}}}", str(param_val)) if template else str(param_val)

                for at in slot.get("at", []):
                    if at.startswith("header:"):
                        h_name = at.split(":", 1)[1]
                        headers[h_name] = final_val

        # 3. Process body parameter substitutions
        if body and isinstance(body, str):
            for k, v in params.items():
                body = body.replace(f"{{{k}}}", str(v))

        # 4. Execute HTTP Request (Tier 1)
        sess = session or requests.Session()
        resp = sess.request(
            method=method,
            url=url,
            headers=headers,
            data=body.encode("utf-8") if isinstance(body, str) else body,
            cookies=cookies,
            timeout=timeout
        )

        resp.raise_for_status()

        # 5. Extract response according to spec response schema
        resp_def = op.get("response", {})
        resp_format = resp_def.get("format", "json")

        if resp_format == "json":
            data = resp.json()
            extract_expr = resp_def.get("extract")
            extracted = extract_json_path(data, extract_expr)
            return {
                "status": resp.status_code,
                "data": extracted,
                "raw_json": data
            }
        else:
            return {
                "status": resp.status_code,
                "text": resp.text
            }

