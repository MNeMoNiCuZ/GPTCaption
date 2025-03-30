import os
import json
from typing import Any, Dict, Optional

class StringManager:
    _instance = None
    _strings: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StringManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._strings:
            self.load_strings()
    
    def load_strings(self):
        """Load strings from the language file."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        lang_file = os.path.join(script_dir, 'language_english.json')
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self._strings = json.load(f)
        except Exception as e:
            print(f"Error loading language file: {e}")
            self._strings = {}
    
    def get(self, key_path: str, **kwargs) -> str:
        """
        Get a string by its dot-separated path.
        Example: get("ui.window.title")
        Optional format parameters can be provided as kwargs.
        """
        try:
            # Navigate through the nested dictionary
            value = self._strings
            for key in key_path.split('.'):
                value = value[key]
            
            # If format parameters are provided, format the string
            if kwargs and isinstance(value, str):
                return value.format(**kwargs)
            return value
        except (KeyError, AttributeError):
            # Return the key path if string not found
            return key_path
    
    def get_raw(self, key_path: str) -> Optional[Any]:
        """Get the raw value without any formatting."""
        try:
            value = self._strings
            for key in key_path.split('.'):
                value = value[key]
            return value
        except (KeyError, AttributeError):
            return None

# Global instance
strings = StringManager() 