import os
import operator
from dotenv import load_dotenv
from typing import TypedDict, List, Optional, Literal
from pydantic import BaseModel, Field

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from typing import TypedDict, List, Optional, Literal, Annotated

class VerificationReport(BaseModel):
    claim: str = Field(description="The claim being investigated.")
    subject: str = Field(
        description="The core topic and its scope, EXCLUDING the specific entity being claimed. Format: '[Attribute] + [Context/Scope]'. Examples: Claim: 'Denali is the tallest mountain in the US' -> Subject: 'tallest mountain in the us'. Claim: 'Jupiter is the largest planet in our solar system' -> Subject: 'largest planet in our solar system'."
    )
    status: Literal["VERIFIED", "FALSE", "UNVERIFIED"] = Field(description="The verdict.")
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(description="Short explanation of the verdict.")
    sources: List[str] = Field(description="URLs or sources that support this report.")

class AgentState(TypedDict):
    claim: str
    subject: Optional[str]
    report: Optional[VerificationReport]
    beta_action: Optional[str]
    trace: Annotated[List[str], operator.add]

@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic."""
    search = TavilySearch(max_results=3)
    results = search.invoke(query)
    return str(results)

def alpha_agent(state: AgentState) -> dict:
    claim = state["claim"]
    
    search_results = web_search.invoke(claim)
    
    llm = ChatGroq(model_name="llama-3.1-8b-instant")
    structured_llm = llm.with_structured_output(VerificationReport)
    
    prompt = f"""
    You are Agent Alpha, "The Scout" — an investigative fact-checker for an Indian news agency.
    Investigate the following claim using the provided web evidence.
    
    Claim: "{claim}"
    Web Search Evidence: {search_results}

    CRITICAL INSTRUCTION FOR SUBJECT GENERATION:
    Your 'subject' field must extract the underlying topic, stripping away the specific claim being made. 
    Examples:
    - Claim: "Tokyo is the capital of Japan" -> Subject: "capital of japan"
    - Claim: "Kyoto is the capital of Japan" -> Subject: "capital of japan"
    - Claim: "Mount Everest is the tallest mountain" -> Subject: "tallest mountain on earth"
    - Claim: "K2 is the tallest mountain" -> Subject: "tallest mountain on earth"
    """
    
    report: VerificationReport = structured_llm.invoke([SystemMessage(content=prompt)])

    alpha_log = f"Alpha investigated '{claim}' and concluded: {report.status}."
    
    return {
        "subject": report.subject,
        "report": report,
        "trace": [alpha_log]
    }