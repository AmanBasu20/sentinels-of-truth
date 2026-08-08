import os
from dotenv import load_dotenv

load_dotenv()
from langgraph.graph import StateGraph, START, END
from alpha_agent import alpha_agent, AgentState
from beta_agent import beta_agent

workflow = StateGraph(AgentState)
workflow.add_node("Scout", alpha_agent)
workflow.add_node("Librarian", beta_agent)

workflow.add_edge(START, "Scout")
workflow.add_edge("Scout", "Librarian")
workflow.add_edge("Librarian", END)

app = workflow.compile()


from database import init_db
init_db()
if __name__ == "__main__":
    
    initial_claim = "The capital of Japan is Kyoto."
    
    final_state = app.invoke({
        "claim": initial_claim,
        "trace": ["System received new claim for processing."] 
    })
    
    print("\n--- INVESTIGATION COMPLETE ---")
    print("Final Verdict:", final_state["report"].status)
    print("Database Action Taken:", final_state["beta_action"])
    
    print("\n--- INVESTIGATION HISTORY ---")
    for log in final_state["trace"]:
        print(f" -> {log}")