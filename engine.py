import json
import copy

class SystemDynamicsEngine:
    """System Dynamics simulation engine using Stock-Flow-Feedback paradigm."""
    
    def __init__(self, model_path="model_aerodyn.json"):
        self.model = self._load_model(model_path)
        self.history = []
        self.current_time = 0
        self.dt = self.model.get("system", {}).get("time", {}).get("dt", 0.25)
        
    def _load_model(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading model: {e}")
            return self._default_model()
    
    def _default_model(self):
        """Fallback model structure."""
        return {
            "stocks": {},
            "flows": {},
            "parameters": {},
            "feedback_loops": [],
            "system": {"time": {"dt": 1, "horizon": 10}}
        }
    
    def get_stock_value(self, stock_id):
        """Get current value of a stock."""
        return self.model["stocks"].get(stock_id, {}).get("value", 0)
    
    def get_parameter_value(self, param_id):
        """Get current value of a parameter."""
        return self.model["parameters"].get(param_id, {}).get("value", 0)
    
    def update_parameter(self, param_id, value):
        """Update a parameter value."""
        if param_id in self.model["parameters"]:
            self.model["parameters"][param_id]["value"] = value
            return True
        return False
    
    def apply_scenario(self, scenario_name):
        """Load a predefined scenario."""
        scenarios = self.model.get("scenarios", {})
        if scenario_name in scenarios:
            scenario = scenarios[scenario_name]
            for param, value in scenario.get("parameters", {}).items():
                self.update_parameter(param, value)
            return True
        return False
    
    def _evaluate_formula(self, formula_str):
        """
        Evaluate a flow formula with current stocks and parameters.
        Simple interpreter for safety (limited eval).
        """
        # Create local namespace with current values
        namespace = {}
        
        # Add all stock values
        for stock_id, stock in self.model["stocks"].items():
            namespace[stock_id] = stock["value"]
        
        # Add all parameter values
        for param_id, param in self.model["parameters"].items():
            namespace[param_id] = param["value"]
        
        try:
            # Safe evaluation (limited to math operations)
            result = eval(formula_str, {"__builtins__": {}}, namespace)
            return float(result)
        except Exception as e:
            print(f"Formula error: {formula_str} -> {e}")
            return 0.0
    
    def step(self):
        """Execute one simulation step using Euler method."""
        # Calculate all flow rates
        flow_values = {}
        for flow_id, flow in self.model["flows"].items():
            rate = self._evaluate_formula(flow["formula"])
            flow_values[flow_id] = rate
        
        # Update all stocks based on flows
        for flow_id, rate in flow_values.items():
            flow = self.model["flows"][flow_id]
            
            # Flow OUT (from stock)
            if flow["from"] is not None:
                from_stock = flow["from"]
                if from_stock in self.model["stocks"]:
                    self.model["stocks"][from_stock]["value"] -= rate * self.dt
            
            # Flow IN (to stock)
            if flow["to"] is not None:
                to_stock = flow["to"]
                if to_stock in self.model["stocks"]:
                    self.model["stocks"][to_stock]["value"] += rate * self.dt
        
        # Apply constraints (non-negativity)
        for stock_id in self.model["stocks"]:
            self.model["stocks"][stock_id]["value"] = max(0, self.model["stocks"][stock_id]["value"])
        
        # Record history
        self.current_time += self.dt
        self.history.append({
            "time": round(self.current_time, 2),
            "stocks": {sid: s["value"] for sid, s in self.model["stocks"].items()}
        })
        
        return self.model
    
    def simulate(self, horizon=None):
        """Run simulation for specified time horizon."""
        if horizon is None:
            horizon = self.model.get("system", {}).get("time", {}).get("horizon", 10)
        
        steps = int(horizon / self.dt)
        for _ in range(steps):
            self.step()
        
        return self.history
    
    def reset(self, model_path=None):
        """Reset simulation to initial state."""
        if model_path:
            self.model = self._load_model(model_path)
        else:
            # Reload from file
            self.__init__(model_path or "model_aerodyn.json")
        self.history = []
        self.current_time = 0
    
    def get_feedback_loops(self):
        """Return all defined feedback loops."""
        return self.model.get("feedback_loops", [])
    
    def detect_loop_type(self, loop_path):
        """
        Detect if a loop is reinforcing or balancing.
        Count negative polarities in path.
        """
        # This is a simplified version - full implementation would track
        # the signs of relationships between variables
        return "reinforcing"  # Placeholder
    
    def export_model(self, path="model_modified.json"):
        """Save current model state to file."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.model, f, indent=2)
        return True
