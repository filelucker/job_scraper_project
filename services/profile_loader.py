import os
import json
from typing import Dict, Any, Optional

DEFAULT_PROFILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "candidate_profile.json")

class CandidateProfile:
    _instance = None
    _data: Dict[str, Any] = {}

    def __init__(self, profile_path: Optional[str] = None):
        self.profile_path = profile_path or DEFAULT_PROFILE_PATH
        self.load()

    def load(self) -> Dict[str, Any]:
        if os.path.exists(self.profile_path):
            with open(self.profile_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {
                "first_name": "Md",
                "last_name": "Moniruzzaman",
                "full_name": "Md Moniruzzaman",
                "email": "contact@moniruz.dev",
                "phone": "+8801721915013",
                "location": "Dhaka, Bangladesh",
                "city": "Dhaka",
                "country": "Bangladesh",
                "urls": {
                    "linkedin": "https://www.linkedin.com/in/mon000/",
                    "github": "https://github.com/filelucker",
                    "portfolio": "https://moniruz.dev/"
                }
            }
        return self._data

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

def get_candidate_profile(profile_path: Optional[str] = None) -> CandidateProfile:
    return CandidateProfile(profile_path)
