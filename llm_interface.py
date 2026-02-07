"""
GenAI Integration Module for Model Factory
Provides:
1. Natural Language to JSON model editing
2. Ethical audit system for feedback loop analysis
"""

import json
import os

class LLMInterface:
    """Interface for LLM-powered features."""
    
    def __init__(self, use_openai=False):
        self.use_openai = use_openai
        if use_openai:
            # Placeholder for OpenAI integration
            self.api_key = os.getenv("OPENAI_API_KEY")
    
    def natural_language_to_json(self, command, current_model):
        """
        Translate natural language commands into JSON model modifications.
        
        Supports French and English commands with flexible syntax.
        """
        import re
        
        command_lower = command.lower()
        suggestions = []
        
        # Extract all numbers from command
        numbers = re.findall(r'[-+]?\d*\.?\d+', command)
        
        # Get all parameters for fuzzy matching
        params = current_model.get("parameters", {})
        
        # === PATTERN 1: Parameter Value Changes ===
        # Keywords: set, increase, reduce, augmente, diminue, mettre, passer
        action_keywords = ["set", "increase", "reduce", "raise", "lower", "change",
                          "augmente", "diminue", "mettre", "passer", "modifier", "fixer"]
        
        if any(keyword in command_lower for keyword in action_keywords):
            # Try to match with each parameter
            for param_id, param_data in params.items():
                # Create searchable variations
                param_variations = [
                    param_id,
                    param_id.replace("_", " "),
                    param_id.replace("_", ""),
                    # Common French translations
                    param_id.replace("investment", "investissement"),
                    param_id.replace("pressure", "pression"),
                    param_id.replace("rate", "taux"),
                ]
                
                # Check if any variation is in the command
                if any(var in command_lower for var in param_variations):
                    if numbers:
                        value = float(numbers[0])
                        
                        # Handle percentages
                        if "%" in command or "pourcent" in command_lower:
                            value = value / 100.0
                        
                        # Handle relative changes (increase/decrease)
                        if "increase" in command_lower or "augmente" in command_lower:
                            current_val = param_data.get("value", 0)
                            value = current_val + value
                        elif "reduce" in command_lower or "diminue" in command_lower or "decrease" in command_lower:
                            current_val = param_data.get("value", 0)
                            value = max(0, current_val - value)
                        
                        # Clamp to range if defined
                        param_range = param_data.get("range", [0, 10])
                        value = max(param_range[0], min(param_range[1], value))
                        
                        suggestions.append({
                            "type": "update_parameter",
                            "parameter": param_id,
                            "value": value,
                            "description": f"Set {param_id} to {value}"
                        })
                        break  # Only match first parameter
        
        # === PATTERN 2: Scenario Keywords ===
        # High/Low/Medium qualifiers
        scenario_map = {
            "high": 0.8, "élevé": 0.8, "fort": 0.8, "haut": 0.8,
            "medium": 0.5, "moyen": 0.5, "modéré": 0.5,
            "low": 0.2, "faible": 0.2, "bas": 0.2
        }
        
        for keyword, value in scenario_map.items():
            if keyword in command_lower:
                # Try to find which parameter this applies to
                for param_id in params.keys():
                    if param_id.replace("_", " ") in command_lower:
                        suggestions.append({
                            "type": "update_parameter",
                            "parameter": param_id,
                            "value": value,
                            "description": f"Set {param_id} to {keyword} ({value})"
                        })
                        break
        
        # === PATTERN 3: Add Tax/Flow ===
        if ("tax" in command_lower or "taxe" in command_lower) and numbers:
            tax_rate = float(numbers[0]) / 100.0
            suggestions.append({
                "type": "add_flow",
                "flow_id": "export_tax",
                "flow_data": {
                    "from": "contract_pipeline",
                    "to": None,
                    "formula": f"contract_pipeline * {tax_rate}",
                    "description": f"Export tax at {tax_rate*100}%"
                },
                "description": f"Add export tax flow at {tax_rate*100}%"
            })
        
        # === PATTERN 4: Load Scenario ===
        scenarios = current_model.get("scenarios", {})
        for scenario_name in scenarios.keys():
            if scenario_name.replace("_", " ") in command_lower:
                suggestions.append({
                    "type": "load_scenario",
                    "scenario": scenario_name,
                    "description": f"Load scenario: {scenario_name}"
                })
        
        # Return results
        if not suggestions:
            # Generate helpful examples based on available parameters
            param_examples = list(params.keys())[:3]
            examples = [
                f"Set {param_examples[0]} to 0.8" if param_examples else "Set investment to 0.8",
                "Add 15% tax",
                "Set regulatory pressure to high"
            ]
            
            return {
                "success": False,
                "message": f"Could not parse command. Try:\n" + "\n".join(f"  • {ex}" for ex in examples),
                "suggestions": []
            }
        
        return {
            "success": True,
            "message": f"Found {len(suggestions)} modification(s)",
            "suggestions": suggestions
        }
    
    def apply_suggestion(self, suggestion, engine):
        """Apply a suggested modification to the engine."""
        try:
            if suggestion["type"] == "update_parameter":
                param = suggestion["parameter"]
                value = suggestion["value"]
                engine.update_parameter(param, value)
                return True, f"Updated {param} to {value}"
            
            elif suggestion["type"] == "add_flow":
                flow_id = suggestion["flow_id"]
                flow_data = suggestion["flow_data"]
                engine.model["flows"][flow_id] = flow_data
                return True, f"Added flow: {flow_id}"
            
            elif suggestion["type"] == "load_scenario":
                scenario_name = suggestion["scenario"]
                success = engine.apply_scenario(scenario_name)
                if success:
                    return True, f"Loaded scenario: {scenario_name}"
                else:
                    return False, f"Scenario not found: {scenario_name}"
            
            return False, "Unknown suggestion type"
        
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def ethical_audit(self, model):
        """
        Analyze the model for ethical risks based on feedback loops.
        
        Returns insights about:
        - Reinforcing loops that may cause runaway growth
        - Balancing loops that may collapse critical stocks
        - Ethical constraint violations
        """
        
        feedback_loops = model.get("feedback_loops", [])
        stocks = model.get("stocks", {})
        parameters = model.get("parameters", {})
        
        risks = []
        insights = []
        
        # Check reputation stock
        reputation = stocks.get("reputation_capital", {}).get("value", 100)
        if reputation < 50:
            risks.append({
                "level": "HIGH",
                "category": "Reputation",
                "message": "Reputation Capital is critically low. This may trigger regulatory backlash.",
                "recommendation": "Increase ethical_compliance_index or reduce autonomous_lethal_capacity"
            })
        elif reputation < 70:
            risks.append({
                "level": "MEDIUM",
                "category": "Reputation",
                "message": "Reputation Capital is declining.",
                "recommendation": "Monitor ethical compliance closely"
            })
        
        # Check lethal capacity
        lethal_cap = stocks.get("autonomous_lethal_capacity", {}).get("value", 0)
        if lethal_cap > 50:
            risks.append({
                "level": "HIGH",
                "category": "Ethical",
                "message": f"High autonomous lethal deployment ({lethal_cap} systems).",
                "recommendation": "Consider human oversight requirements per AI Act"
            })
        
        # Analyze feedback loops
        for loop in feedback_loops:
            if loop["type"] == "reinforcing":
                insights.append({
                    "loop": loop["id"],
                    "type": "Reinforcing",
                    "analysis": f"{loop['description']} - This creates exponential growth. Monitor for sustainability.",
                    "risk": "May lead to overshooting limits (market saturation, regulatory caps)"
                })
            else:
                insights.append({
                    "loop": loop["id"],
                    "type": "Balancing",
                    "analysis": f"{loop['description']} - This limits growth.",
                    "risk": "Strong balancing may cause system collapse if not managed"
                })
        
        # Check parameter extremes
        backlash = parameters.get("backlash_coefficient", {}).get("value", 0)
        if backlash > 0.5:
            risks.append({
                "level": "MEDIUM",
                "category": "Public Perception",
                "message": "High backlash coefficient detected. Public opposition is strong.",
                "recommendation": "Invest in transparency and ethical communication"
            })
        
        return {
            "risks": risks,
            "insights": insights,
            "ethical_status": "COMPLIANT" if not any(r["level"] == "HIGH" for r in risks) else "AT_RISK"
        }


# Helper function for demo
def demo_llm_capabilities():
    """Demonstrate LLM features without requiring API keys."""
    print("=== LLM Interface Demo ===")
    
    interface = LLMInterface(use_openai=False)
    
    # Test commands
    test_commands = [
        "Increase AI investment rate to 0.8",
        "Add a 15% export tax on autonomous weapons",
        "Set regulatory pressure to 0.7"
    ]
    
    dummy_model = {
        "parameters": {
            "ai_investment_rate": {"value": 0.5},
            "regulatory_pressure": {"value": 0.4}
        }
    }
    
    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        result = interface.natural_language_to_json(cmd, dummy_model)
        print(f"Result: {result}")


if __name__ == "__main__":
    demo_llm_capabilities()
