import requests
import streamlit as st

API = "http://127.0.0.1:8000"
st.set_page_config(page_title="Retail Operations Copilot", page_icon="🏏", layout="wide")
st.title("Punjab Sports Mart | Operations Copilot")
st.caption("Policy-backed triage, CSV evidence, and safe escalation for store teams.")

try:
    requests.get(f"{API}/health", timeout=2).raise_for_status()
    online = True
except requests.RequestException:
    online = False
    st.error("Backend is offline. Start FastAPI using the command in README.md.")

triage_tab, analytics_tab, evaluation_tab = st.tabs(["Issue triage", "Retail analytics", "Public evaluation"])
with triage_tab:
    with st.form("triage_form"):
        role = st.selectbox("Your role", ["Cashier", "Inventory Associate", "Store Manager", "Regional Manager", "Customer Service", "Unknown"])
        issue = st.text_area("Describe the issue", placeholder="Example: English Willow Cricket Bat is out of stock again at Store ST002. Why is this happening?", height=120)
        submitted = st.form_submit_button("Analyze issue", disabled=not online)
    if submitted:
        if len(issue.strip()) < 3:
            st.warning("Describe the issue in at least three characters.")
        else:
            try:
                response = requests.post(f"{API}/triage", json={"issue": issue, "role": role}, timeout=60)
                response.raise_for_status()
                result = response.json()
            except requests.RequestException as exc:
                st.error(f"Request failed: {exc}")
                result = None
        if submitted and len(issue.strip()) >= 3 and result:
            a, b, c, d = st.columns(4)
            a.metric("Category", result["category"])
            b.metric("Priority", result["priority"])
            c.metric("Confidence", f"{result['confidence']:.0%}")
            d.metric("Escalation", "Required" if result["escalation"]["required"] else "Not required")
            st.markdown(result["answer"])
            if result["escalation"]["required"]:
                st.warning(f"Route to {result['escalation']['team']}: {result['escalation']['reason']}")
            if result["follow_up_question"]:
                st.info(result["follow_up_question"])
            st.write("**Policy citations**", result["citations"])
            st.write("**CSV files used**", result["data_used"] or "None")
            if result.get("analytics_table"):
                st.dataframe(result["analytics_table"], use_container_width=True)
            with st.expander("How the result was produced"):
                st.write(" → ".join(result["agent_trace"]))
                st.caption(f"Response mode: {result['model_used']} | PII masked: {result['pii_masked']}")
            with st.expander("Mock escalation/ticket payload (not submitted)"):
                st.json(result.get("escalation_summary", result.get("ticket_preview", {})))
                st.json(result.get("ticket_preview", {}))
with analytics_tab:
    if online:
        try:
            dashboard = requests.get(f"{API}/dashboard", timeout=10).json()
            st.subheader("Operations snapshot")
            st.metric("Active cases", dashboard["active_case_count"])
            dc1, dc2 = st.columns(2)
            with dc1:
                st.caption("Priority distribution")
                st.bar_chart(dashboard["priority_distribution"], x="priority_label", y="cases")
                st.caption("Cases by region")
                st.bar_chart(dashboard["region_distribution"], x="region", y="active_cases")
            with dc2:
                st.caption("Category distribution")
                st.bar_chart(dashboard["category_distribution"], x="category_label", y="cases")
            st.caption("Dashboard data: " + ", ".join(dashboard["data_used"]))
        except requests.RequestException as exc:
            st.warning(f"Dashboard data unavailable: {exc}")
    st.write("Ask about recent incidents, quality trends, or an inventory SKU. Time windows use the case-study anchor: 10 Oct 2026, 12:00 IST.")
    question = st.text_input("Analytics question", "Show unresolved P1 and P2 incidents from the last 24 hours grouped by store.")
    if st.button("Run analytics", disabled=not online):
        if len(question.strip()) < 3:
            st.warning("Enter an analytics question in at least three characters.")
        else:
            try:
                response = requests.post(f"{API}/analytics", json={"question": question}, timeout=20)
                response.raise_for_status()
                result = response.json()
                st.write(result["answer"])
                st.write("CSV data used:", result["data_used"])
                if result["table"]:
                    st.dataframe(result["table"], use_container_width=True)
            except requests.RequestException as exc:
                st.error(f"Analytics request failed: {exc}")

with evaluation_tab:
    st.write("Run all 11 supplied public prompts. Predictions are written to `outputs/predictions.csv`.")
    if st.button("Run public test cases", disabled=not online):
        try:
            response = requests.post(f"{API}/evaluate", timeout=120)
            response.raise_for_status()
            result = response.json()
            st.subheader("Metrics")
            st.dataframe([{"Metric": k.replace("_", " ").title(), "Result": f"{v:.1%}"} for k, v in result["metrics"].items()], hide_index=True, use_container_width=True)
            st.dataframe(result["cases"], use_container_width=True)
            st.success(f"Predictions saved to {result['predictions_file']}")
        except requests.RequestException as exc:
            st.error(f"Evaluation failed: {exc}")
