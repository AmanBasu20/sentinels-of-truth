import streamlit as st
import requests

API_URL = "https://sentinels-backend.onrender.com/api/verify"

st.set_page_config(page_title="Sentinels of Truth", page_icon="🛡️", layout="centered")

st.title("🛡️ Sentinels of Truth")
st.markdown("### Fact-Checking & Knowledge Management System for Indian News Agencies")
st.write("Submit an **Unverified Claim** below. Our multi-agent system will independently research the claim against live web data, cross-reference our **Ground Truth** database, and manage long-term memory based on strict consensus criteria.")

claim = st.text_input("Enter an unverified news claim to investigate:", placeholder="e.g., The ISRO Chandrayaan-4 mission launches next month.")

if st.button("Verify Claim"):
    if not claim.strip():
        st.warning("Please enter a claim to investigate.")
    else:
        with st.spinner("Agents are investigating... Please wait."):
            try:
                response = requests.post(API_URL, json={"claim": claim})
                response.raise_for_status() 
                
                data = response.json()
                
                st.divider()
                st.subheader("Investigation Results")
                
                verdict = data.get("verdict")
                if verdict == "VERIFIED":
                    st.success(f"**Verdict:** {verdict}")
                elif verdict == "FALSE":
                    st.error(f"**Verdict:** {verdict}")
                else:
                    st.warning(f"**Verdict:** {verdict}")
                    
                col1, col2 = st.columns(2)
                col1.metric(label="Confidence Score", value=f"{data.get('confidence', 0) * 100}%")
                col2.info(f"**Database Action:** {data.get('action_taken')}")
                
                with st.expander("View Agent Trace History"):
                    for step in data.get("history", []):
                        st.write(f"🔹 {step}")
                        
            except requests.exceptions.ConnectionError:
                st.error("Error: Could not connect to the backend API. Is the FastAPI server running?")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")