"""
Ollama LLM Integration for Model Factory
Provides real AI-powered natural language understanding and ethical auditing.
"""

import json
import requests

class OllamaLLM:
    """Interface for Ollama local LLM."""
    
    def __init__(self, model="llama3.2:3b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.available = self._check_availability()
    
    def _check_availability(self):
        """Check if Ollama is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, prompt, temperature=0.3):
        """Generate text from Ollama."""
        if not self.available:
            return {"error": "Ollama not available"}
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": temperature
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        
        except Exception as e:
            return {"error": str(e)}
    
    def parse_command(self, command, model_params):
        """Use LLM to parse natural language commands into JSON modifications."""
        
        param_list = "\n".join([f"  - {k}: {v.get('description', '')}" for k, v in model_params.items()])
        
        prompt = f"""You are a System Dynamics model configuration assistant.

Available parameters:
{param_list}

User command: "{command}"

Task: Parse this command and return ONLY a valid JSON object with this structure:
{{
  "type": "update_parameter",
  "parameter": "parameter_name",
  "value": 0.8,
  "description": "Brief description"
}}

If the command asks to add a tax or flow, use:
{{
  "type": "add_flow",
  "flow_id": "flow_name",
  "flow_data": {{...}},
  "description": "..."
}}

If you cannot parse it, return:
{{
  "type": "error",
  "message": "Could not understand command"
}}

Return ONLY the JSON, no explanation."""

        result = self.generate(prompt, temperature=0.1)
        
        if "error" in result:
            return None
        
        try:
            # Extract JSON from response
            response_text = result.get("response", "")
            # Try to find JSON object
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            
            return None
        
        except:
            return None
    
    def ethical_audit_analysis(self, model_data):
        """Use LLM for deep ethical analysis of the model."""
        
        stocks_summary = json.dumps({k: v.get("value") for k, v in model_data.get("stocks", {}).items()}, indent=2)
        loops = model_data.get("feedback_loops", [])
        loops_summary = "\n".join([f"  - {l['id']}: {l['description']}" for l in loops])
        
        prompt = f"""You are an AI ethics auditor for a defense contractor's System Dynamics model.

Current System State:
Stocks (key variables):
{stocks_summary}

Feedback Loops:
{loops_summary}

Task: Analyze this system for ethical risks related to autonomous weapons deployment, reputation, and regulatory compliance.

Provide a brief analysis (2-3 sentences) focusing on:
1. Critical ethical risks
2. Systemic vulnerabilities (feedback loops)
3. One concrete recommendation

Keep it concise and actionable."""

        result = self.generate(prompt, temperature=0.4)
        
        if "error" in result:
            return "LLM analysis unavailable. Using heuristic audit."
        
        return result.get("response", "No analysis generated")


# Fallback to pattern matching if Ollama unavailable
from llm_interface import LLMInterface as PatternMatcher

class HybridLLM:
    """Hybrid system: Try Ollama first, fallback to pattern matching."""
    
    def __init__(self):
        self.ollama = OllamaLLM()
        self.pattern_matcher = PatternMatcher()
    
    def parse_command(self, command, current_model):
        """Parse command with LLM if available, else use patterns."""
        
        if self.ollama.available:
            # Try LLM parsing
            result = self.ollama.parse_command(command, current_model.get("parameters", {}))
            
            if result and result.get("type") != "error":
                return {
                    "success": True,
                    "message": "LLM parsed command",
                    "suggestions": [result],
                    "method": "ollama"
                }
        
        # Fallback to pattern matching
        fallback = self.pattern_matcher.natural_language_to_json(command, current_model)
        fallback["method"] = "pattern_matching"
        return fallback
    
    def ethical_audit(self, model):
        """Enhanced ethical audit with LLM insights."""
        
        # Get base heuristic audit
        base_audit = self.pattern_matcher.ethical_audit(model)
        
        # Add LLM analysis if available
        if self.ollama.available:
            llm_analysis = self.ollama.ethical_audit_analysis(model)
            base_audit["llm_analysis"] = llm_analysis
        
        return base_audit
    
    def apply_suggestion(self, suggestion, engine):
        """Apply suggestion (delegate to pattern matcher)."""
        return self.pattern_matcher.apply_suggestion(suggestion, engine)
