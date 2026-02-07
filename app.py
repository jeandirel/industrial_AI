import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from engine import SystemDynamicsEngine
from streamlit_agraph import agraph, Node, Edge, Config
from ollama_llm import HybridLLM

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="AeroDyn Model Factory", page_icon="🛡️")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* --- GLOBAL THEME (Professional Light) --- */
    .stApp {
        background-color: #ffffff; /* Pure White */
        background-image: radial-gradient(#e5e7eb 1px, transparent 1px);
        background-size: 20px 20px;
        font-family: 'Inter', sans-serif;
    }
    
    /* --- TYPOGRAPHY --- */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        color: #0f172a !important; /* Slate 900 */
        letter-spacing: -0.025em;
    }
    
    h1 {
        font-weight: 800;
        font-size: 2.5rem;
        background: linear-gradient(135deg, #2563eb, #4f46e5); /* Blue to Indigo */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-shadow: none;
    }
    
    h3 {
        color: #334155 !important; /* Slate 700 */
        background: #f1f5f9;
        padding: 8px 16px;
        border-radius: 8px;
        display: inline-block;
        font-size: 1rem;
        border: 1px solid #e2e8f0;
    }
    
    .stCaption {
        color: #64748b !important; /* Slate 500 */
        font-weight: 500;
    }
    
    /* --- CARDS (Clean Light) --- */
    div[data-testid="stMetric"], div[data-testid="stExpander"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0; /* Slate 200 */
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        color: #0f172a;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border-color: #3b82f6;
    }
    
    /*Metric Value*/
    div[data-testid="stMetricValue"] {
        font-weight: 700;
        color: #0f172a !important;
        background: none;
        -webkit-text-fill-color: #0f172a;
    }
    
    /* --- BUTTONS --- */
    .stButton > button {
        background: #f8fafc;
        color: #334155;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        background: #f1f5f9;
        border-color: #94a3b8;
        color: #0f172a;
        transform: translateY(-1px);
    }
    
    button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%);
        color: white !important;
        border: none;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    
    button[kind="primary"]:hover {
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
        transform: translateY(-1px);
    }
    
    /* --- INPUTS --- */
    .stTextInput > div > div > input {
        background-color: #ffffff;
        color: #0f172a;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 0 12px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* --- SIDEBAR --- */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    
    /* --- ALERTS --- */
    .stAlert {
        background-color: #fff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
    }
</style>
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'engine' not in st.session_state:
    st.session_state['engine'] = SystemDynamicsEngine()
    st.session_state['run_sim'] = False
    st.session_state['llm'] = HybridLLM()

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Control Center")
    
    # Scenario Selection
    with st.container():
        st.subheader("📋 Scenarios")
        scenarios = list(st.session_state['engine'].model.get("scenarios", {}).keys())
        selected_scenario = st.selectbox("Select Profile", ["Custom"] + scenarios)
        
        if selected_scenario != "Custom":
            if st.button("Apply Profile", type="primary"):
                st.session_state['engine'].apply_scenario(selected_scenario)
                st.success(f"Loaded: {selected_scenario}")
                st.rerun()
    
    # Simulation Control
    with st.container():
        st.subheader("🎬 Simulation")
        horizon = st.slider("Horizon (years)", 1, 20, 10)
        
        col_run, col_reset = st.columns(2)
        with col_run:
            if st.button("▶ Run", type="primary"):
                engine = st.session_state['engine']
                params = engine.model.get("parameters", {})
                
                engine.reset()
                for param_id, param_data in params.items():
                    engine.update_parameter(param_id, st.session_state.get(f"param_{param_id}", param_data["value"]))
                engine.simulate(horizon=horizon)
                st.success("Done")
                st.rerun()
        with col_reset:
            if st.button("🔄 Reset"):
                st.session_state['engine'] = SystemDynamicsEngine()
                st.rerun()

    # Parameters
    with st.expander("⚙️ Core Parameters", expanded=True):
        engine = st.session_state['engine']
        params = engine.model.get("parameters", {})
        
        for param_id, param_data in params.items():
            min_val, max_val = param_data.get("range", [0, 10])
            current_val = param_data.get("value", 1.0)
            
            new_val = st.slider(
                param_data.get("description", param_id),
                float(min_val), float(max_val), float(current_val),
                key=f"param_{param_id}"
            )
            engine.update_parameter(param_id, new_val)
            
    # Model Builder (Manual Node Addition)
    with st.expander("🛠️ Model Builder"):
        st.caption("Add new elements manually")
        add_type = st.selectbox("Type", ["Stock", "Parameter", "Flow"])
        new_id = st.text_input("ID (e.g., 'marketing_budget')", key="new_node_id").lower().replace(" ", "_")
        
        if add_type == "Stock":
            new_val = st.number_input("Initial Value", value=10.0, key="new_stock_val")
            if st.button("Add Stock"):
                if new_id and new_id not in engine.model["stocks"]:
                    engine.model["stocks"][new_id] = {"value": new_val}
                    st.success(f"Added Stock: {new_id}")
                    st.rerun()
                elif new_id:
                    st.error("ID already exists")
                    
        elif add_type == "Parameter":
            new_val = st.number_input("Value", value=1.0, key="new_param_val")
            if st.button("Add Parameter"):
                if new_id and new_id not in engine.model["parameters"]:
                    engine.model["parameters"][new_id] = {"value": new_val, "range": [0, new_val*5]}
                    st.success(f"Added Param: {new_id}")
                    st.rerun()
                elif new_id:
                    st.error("ID already exists")

        elif add_type == "Flow":
            new_formula = st.text_input("Formula (e.g., 'stock * 0.1')", value="0", key="new_flow_formula")
            if st.button("Add Flow"):
                if new_id and new_id not in engine.model["flows"]:
                    engine.model["flows"][new_id] = {"formula": new_formula, "to": None, "from": None}
                    st.success(f"Added Flow: {new_id}")
                    st.rerun()
                elif new_id:
                    st.error("ID already exists")
    
    # Export
    with st.expander("💾 System Data"):
        st.download_button(
            "Export JSON Model",
            data=json.dumps(engine.model, indent=2),
            file_name="model_aerodyn_modified.json",
            mime="application/json"
        )

# --- HEADER ---
col_logo, col_title = st.columns([1, 5])
with col_title:
    st.title("AeroDyn Model Factory")
    st.caption("Data-Driven System Dynamics & Ethical Governance Engine")

# Ethical Constraints Badge
constraints = engine.model.get("system", {}).get("ethical_constraints", [])
st.info("🔒 **Active Constraints:** " + " • ".join([c.replace("_", " ").title() for c in constraints]))

# --- MAIN DASHBOARD ---
st.markdown("### 📡 System Telemetry")
col_left, col_right = st.columns([2, 3], gap="medium")

# --- LEFT: CAUSAL LOOP DIAGRAM ---
with col_left:
    st.subheader("🔁 Causal Loop Diagram")
    
    feedback_loops = engine.get_feedback_loops()
    
    # Build graph from feedback loops
    nodes_graph = []
    edges_graph = []
    node_ids = set()
    
    # Extract unique nodes from all loops
    for loop in feedback_loops:
        for node_id in loop.get("path", []):
            if node_id not in node_ids:
                node_ids.add(node_id)
                # Color by type (Professional Light)
                color = "#2563eb"  # Blue for stocks
                if node_id in engine.model.get("flows", {}):
                    color = "#059669"  # Emerald 600 for flows
                    
                nodes_graph.append(Node(
                    id=node_id,
                    label=node_id.replace("_", " ").title(),
                    size=25,
                    color=color,
                    # Node aesthetics
                    font={'color': 'white', 'face': 'Inter', 'size': 14},
                    shape='dot',
                    borderWidth=2,
                    borderColor='#ffffff'
                ))
    
    # Create edges from loops
    for loop in feedback_loops:
        path = loop.get("path", [])
        loop_color = "#059669" if loop["type"] == "reinforcing" else "#e11d48" # Emerald/Rose
        
        for i in range(len(path) - 1):
            edges_graph.append(Edge(
                source=path[i],
                target=path[i+1],
                label=loop["id"],
                color=loop_color,
                highlight={'stroke': '#f59e0b'}, # Amber highlight
                strokeWidth=2
            ))
    
    config = Config(
        width="100%",
        height=400,
        directed=True,
        nodeHighlightBehavior=True,
        highlightColor="#F7A072",
        collapsible=False
    )
    
    # Capture selection
    if nodes_graph:
        selected_node_id = agraph(nodes=nodes_graph, edges=edges_graph, config=config)
        
        # --- INTERACTIVE NODE EDITOR (Always Visible) ---
        with st.sidebar:
            st.markdown("---")
            st.subheader("🖊️ Node Editor")
            
            if selected_node_id:
                st.info(f"Editing: **{selected_node_id}**")
                
                # Check Stocks
                if selected_node_id in engine.model.get("stocks", {}):
                    data = engine.model["stocks"][selected_node_id]
                    new_val = st.number_input(
                        "Initial Value", 
                        value=float(data.get("value", 0)),
                        key=f"edit_stock_{selected_node_id}"
                    )
                    if st.button("Update Stock", type="primary"):
                        engine.model["stocks"][selected_node_id]["value"] = new_val
                        st.success("Saved!")
                        st.rerun()
                
                # Check Parameters
                elif selected_node_id in engine.model.get("parameters", {}):
                    data = engine.model["parameters"][selected_node_id]
                    new_val = st.number_input(
                        "Parameter Value",
                        value=float(data.get("value", 1.0)),
                        key=f"edit_param_{selected_node_id}"
                    )
                    if st.button("Update Parameter", type="primary"):
                        engine.update_parameter(selected_node_id, new_val)
                        st.success("Saved!")
                        st.rerun()
                
                # Check Flows
                elif selected_node_id in engine.model.get("flows", {}):
                    data = engine.model["flows"][selected_node_id]
                    new_formula = st.text_area(
                        "Flow Logic",
                        value=data.get("formula", ""),
                        key=f"edit_flow_{selected_node_id}"
                    )
                    if st.button("Update Logic", type="primary"):
                        engine.model["flows"][selected_node_id]["formula"] = new_formula
                        st.success("Saved!")
                        st.rerun()
                
                else:
                    st.warning("Selected element is not editable (might be a system variable).")
            else:
                st.info("👆 Click on a node in the graph to edit its properties here.")
            
            st.markdown("---")
    else:
        st.info("No feedback loops defined")
    
    # Legend
    st.markdown("**Legend**: 🟢 Reinforcing (R) | 🔴 Balancing (B)")
    
    # Loop Details
    with st.expander("📖 Feedback Loop Details"):
        for loop in feedback_loops:
            st.markdown(f"**{loop['id']}** ({loop['type'].upper()})")
            st.caption(loop.get("description", ""))
            st.markdown("---")

# --- RIGHT: STOCK TRENDS ---
with col_right:
    st.subheader("📊 Stock Evolution")
    
    history = engine.history
    
    if history:
        # Convert to DataFrame
        df = pd.DataFrame(history)
        time = df['time']
        
        # Create interactive plot
        fig = go.Figure()
        
        stocks = engine.model.get("stocks", {})
        # Professional Palette: Royal Blue, Orange, Emerald, Violet
        colors = ["#2563eb", "#f97316", "#10b981", "#8b5cf6"]
        
        for idx, stock_id in enumerate(stocks.keys()):
            values = [h["stocks"].get(stock_id, 0) for h in history]
            fig.add_trace(go.Scatter(
                x=time,
                y=values,
                mode='lines',
                name=stock_id.replace("_", " ").title(),
                line=dict(width=3, color=colors[idx % len(colors)]),
                fill='tozeroy',
                fillcolor=f"rgba{tuple(int(colors[idx % len(colors)].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.1,)}"
            ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter, sans-serif", color="#334155"), # Slate 700
            xaxis=dict(showgrid=True, gridcolor='#e2e8f0', zeroline=False), # Slate 200
            yaxis=dict(showgrid=True, gridcolor='#e2e8f0', zeroline=False),
            margin=dict(l=0, r=0, t=10, b=0),
            height=350,
            hovermode='x unified',
            legend=dict(
                orientation="h", 
                y=1.1,
                font=dict(size=12, color="#0f172a")
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run simulation to see trends")

# --- SCENARIO COMPARISON ---
st.markdown("---")
st.subheader("🔄 Scenario Comparison")
st.caption("Compare different parameter settings to see their impact")

col_comp1, col_comp2 = st.columns(2)

with col_comp1:
    st.markdown("**Quick Comparisons**")
    
    if st.button("Compare: Ethics vs Growth"):
        # Run 3 scenarios
        scenarios_to_compare = {
            "Baseline (Current)": {},
            "High Ethics": {"ethical_compliance_index": 9.0, "backlash_coefficient": 0.15},
            "Aggressive Growth": {"reinvestment_rate": 0.9, "ethical_compliance_index": 3.0}
        }
        
        comparison_results = {}
        
        for scenario_name, param_changes in scenarios_to_compare.items():
            # Create temporary engine
            temp_engine = SystemDynamicsEngine()
            
            # Apply parameter changes
            for param, value in param_changes.items():
                temp_engine.update_parameter(param, value)
            
            # Run simulation
            temp_engine.simulate(horizon=10)
            comparison_results[scenario_name] = temp_engine.history
        
        # Store in session state
        st.session_state['comparison'] = comparison_results
        st.success("Comparison complete!")

with col_comp2:
    if 'comparison' in st.session_state and st.session_state['comparison']:
        st.markdown("**Select Stock to Compare**")
        
        stocks = engine.model.get("stocks", {})
        stock_to_compare = st.selectbox(
            "Choose stock:",
            list(stocks.keys()),
            format_func=lambda x: x.replace("_", " ").title()
        )
        
        # Plot comparison
        fig_comp = go.Figure()
        
        for scenario_name, history in st.session_state['comparison'].items():
            df = pd.DataFrame(history)
            time = df['time']
            values = [h["stocks"][stock_to_compare] for h in history]
            
            fig_comp.add_trace(go.Scatter(
                x=time,
                y=values,
                mode='lines',
                name=scenario_name,
                line=dict(width=3)
            ))
        
        fig_comp.update_layout(
            xaxis_title="Time (years)",
            yaxis_title=stock_to_compare.replace("_", " ").title(),
            height=350,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("Click 'Compare' to generate comparison charts")

# --- PERFORMANCE DASHBOARD ---
st.markdown("---")
st.subheader("📈 Performance Dashboard")

col1, col2, col3, col4 = st.columns(4)

stocks = engine.model.get("stocks", {})

with col1:
    lc_val = stocks.get("autonomous_lethal_capacity", {}).get("value", 0)
    st.metric("Lethal Capacity", f"{lc_val:.1f} systems")

with col2:
    rep_val = stocks.get("reputation_capital", {}).get("value", 0)
    delta_color = "normal" if rep_val >= 60 else "inverse"
    st.metric("Reputation", f"{rep_val:.1f}/100", delta_color=delta_color)

with col3:
    pipeline_val = stocks.get("contract_pipeline", {}).get("value", 0)
    st.metric("Contract Pipeline", f"€{pipeline_val:.1f}M")

with col4:
    invest_val = stocks.get("ai_investment_fund", {}).get("value", 0)
    st.metric("AI Investment", f"€{invest_val:.1f}M")

# Alerts
if stocks.get("reputation_capital", {}).get("value", 100) < 50:
    st.warning("⚠️ **Risk Alert**: Reputation below critical threshold (50)")

if stocks.get("autonomous_lethal_capacity", {}).get("value", 0) > 50:
    st.error("🚨 **Ethical Alert**: High lethal deployment may trigger regulatory action")

# --- GENAI INTEGRATION ---
st.markdown("---")
st.header("🤖 GenAI Assistant")

col_nl, col_audit = st.columns(2)

with col_nl:
    st.subheader("💬 Natural Language Commands")
    st.caption("Modify the model using plain English or French")
    
    nl_command = st.text_input(
        "Enter command:",
        placeholder="e.g., 'Increase AI investment to 0.8' or 'Ajoute une taxe de 15%'"
    )
    
    if st.button("Execute Command"):
        if nl_command:
            llm = st.session_state['llm']
            result = llm.parse_command(nl_command, engine.model)
            
            # Show which method was used
            method = result.get("method", "unknown")
            method_emoji = "🤖" if method == "ollama" else "🔧"
            st.caption(f"{method_emoji} Method: {method}")
            
            if result["success"]:
                st.success(result["message"])
                for suggestion in result["suggestions"]:
                    with st.expander(f"✅ {suggestion['description']}"):
                        st.json(suggestion)
                        if st.button(f"Apply: {suggestion['description']}", key=suggestion['description']):
                            success, msg = llm.apply_suggestion(suggestion, engine)
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
            else:
                st.error(result["message"])

with col_audit:
    st.subheader("🔍 Ethical Audit")
    st.caption("AI-powered risk analysis")
    
    if st.button("Run Ethical Audit"):
        llm = st.session_state['llm']
        audit = llm.ethical_audit(engine.model)
        
        # Status badge
        status = audit["ethical_status"]
        if status == "COMPLIANT":
            st.success(f"Status: {status}")
        else:
            st.error(f"Status: {status}")
        
        # LLM Analysis (if available)
        if "llm_analysis" in audit:
            st.markdown("**🤖 AI Analysis:**")
            st.info(audit["llm_analysis"])
            st.markdown("---")
        
        # Risks
        if audit["risks"]:
            st.markdown("**⚠️ Identified Risks:**")
            for risk in audit["risks"]:
                level_emoji = "🔴" if risk["level"] == "HIGH" else "🟡"
                with st.expander(f"{level_emoji} {risk['category']} ({risk['level']})"):
                    st.write(risk["message"])
                    st.info(f"💡 **Recommendation**: {risk['recommendation']}")
        else:
            st.success("No critical risks detected")
        
        # Loop Insights
        if audit["insights"]:
            with st.expander("📊 Feedback Loop Analysis"):
                for insight in audit["insights"]:
                    st.markdown(f"**{insight['loop']}** ({insight['type']})")
                    st.write(f"- {insight['analysis']}")
                    st.caption(f"⚠️ {insight['risk']}")

