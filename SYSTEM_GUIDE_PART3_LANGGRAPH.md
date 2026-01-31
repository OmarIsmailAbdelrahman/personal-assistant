## LangGraph Integration Guide

### What is LangGraph?

LangGraph is a library for building stateful, multi-actor applications with LLMs. It extends LangChain with:
- **State management**: Track conversation state across turns
- **Cycles**: Loop until conditions are met
- **Controllability**: Define exact agent behavior with graphs  
- **Human-in-the-loop**: Pause for user confirmation
- **Streaming**: Stream tokens/intermediate steps
- **Memory**: Persist state to databases

**Why use it?** More control than AutoGPT-style agents, but less manual work than pure prompting.

---

### Current vs LangGraph Architecture

#### Current (Gemini Direct):
```
User Message → Gemini API → Response → Done
```

Simple but limited:
- No tools/function calling
- No multi-step reasoning
- No state management beyond conversation history

#### With LangGraph:
```
User Message → LangGraph State Graph → [Research → Reason → Respond] → Done
                                        ↓
                                   Tools (search, calc, DB query)
```

Powerful capabilities:
- Multi-step workflows
- Tool calling (web search, calculator, database queries)
- State tracking (what has been done, what's next)
- Conditional branches (if user asks X, do Y)

---

### Implementation Steps

#### Step 1: Install LangGraph

```bash
# Add to requirements.txt
langgraph==0.0.26
langchain==0.1.0
langchain-google-genai==0.0.6
```

```bash
# Rebuild containers
docker-compose down
docker-compose up --build
```

---

#### Step 2: Define Agent State

Create `app/services/langgraph_agent.py`:

```python
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """State that we'll pass through the graph"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # Add more state as needed
    user_id: str
    conversation_id: str
    next_step: str  # Control flow
```

---

#### Step 3: Create Graph Nodes

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0.7
)

def should_use_tools(state: AgentState) -> bool:
    """Decide if we need to use tools"""
    last_message = state['messages'][-1].content.lower()
    
    # Check for keywords that require tools
    if any(keyword in last_message for keyword in ['search', 'calculate', 'find', 'lookup']):
        return True
    return False

def route_after_llm(state: AgentState) -> str:
    """Decide what to do after LLM responds"""
    if should_use_tools(state):
        return "use_tools"
    else:
        return "end"

# Node 1: Call LLM
def call_llm(state: AgentState) -> AgentState:
    """Generate response using LLM"""
    response = llm.invoke(state['messages'])
    state['messages'].append(response)
    return state

# Node 2: Use tools (web search, calculator, etc.)
def use_tools(state: AgentState) -> AgentState:
    """Execute tools based on LLM request"""
    # Example: web search
    from langchain_community.tools import DuckDuckGoSearchRun
    
    search = DuckDuckGoSearchRun()
    last_message = state['messages'][-1].content
    
    # Extract search query from LLM response
    # (In production, use function calling for this)
    search_results = search.run(last_message)
    
    # Add results back to state
    state['messages'].append(
        SystemMessage(content=f"Search results: {search_results}")
    )
    
    # Call LLM again with search results
    final_response = llm.invoke(state['messages'])
    state['messages'].append(final_response)
    
    return state

# Build the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("llm", call_llm)
workflow.add_node("tools", use_tools)

# Set entry point
workflow.set_entry_point("llm")

# Add conditional edges
workflow.add_conditional_edges(
    "llm",
    route_after_llm,
    {
        "use_tools": "tools",
        "end": END
    }
)

# If we used tools, end after that
workflow.add_edge("tools", END)

# Compile the graph
agent = workflow.compile()
```

---

#### Step 4: Replace Gemini Direct Call in Agent Runner

Update `app/services/agent_runner.py`:

```python
from app.services.langgraph_agent import agent, AgentState
from langchain_core.messages import HumanMessage, AIMessage

def _run_langgraph_agent(
    conversation_context: list,
    user_text: str,
    user_id: str,
    conversation_id: str
) -> str:
    """
    Run the LangGraph agent instead of direct Gemini call
    """
    # Convert our context to LangChain messages
    messages = []
    for msg in conversation_context:
        if msg['role'] == 'user':
            messages.append(HumanMessage(content=msg['parts'][0]))
        elif msg['role'] == 'model':
            messages.append(AIMessage(content=msg['parts'][0]))
    
    # Add the latest user message
    messages.append(HumanMessage(content=user_text))
    
    # Create initial state
    initial_state = AgentState(
        messages=messages,
        user_id=user_id,
        conversation_id=conversation_id,
        next_step="start"
    )
    
    # Run the graph
    result = agent.invoke(initial_state)
    
    # Extract final AI response
    final_message = result['messages'][-1]
    return final_message.content

# In execute_agent_run, replace:
# response_text = _run_gemini_agent(...)
# with:
response_text = _run_langgraph_agent(
    conversation_context,
    user_text,
    str(agent_run.conversation.user_id),
    str(agent_run.conversation_id)
)
```

---

#### Step 5: Add Function Calling (Advanced)

For structured tool use:

```python
from langchain.tools import tool
from langchain_core.messages import ToolMessage

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression. Use this when user asks for calculations."""
    try:
        result = eval(expression)  # Use safe_eval in production!
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def web_search(query: str) -> str:
    """Search the web for information. Use this when user asks about current events or facts."""
    from langchain_community.tools import DuckDuckGoSearchRun
    search = DuckDuckGoSearchRun()
    return search.run(query)

@tool
def query_database(sql: str) -> str:
    """Query the database for user's past conversations or data."""
    # Execute safe SQL query on your DB
    # Return results
    pass

# Bind tools to LLM
tools = [calculate, web_search, query_database]
llm_with_tools = llm.bind_tools(tools)

def call_llm_with_tools(state: AgentState) -> AgentState:
    """LLM decides which tools to call"""
    response = llm_with_tools.invoke(state['messages'])
    
    # Check if LLM wants to call tools
    if response.tool_calls:
        # Execute tool calls
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            tool_args = tool_call['args']
            
            # Find and execute the tool
            tool = next(t for t in tools if t.name == tool_name)
            result = tool.invoke(tool_args)
            
            # Add tool result to messages
            state['messages'].append(ToolMessage(
                content=result,
                tool_call_id=tool_call['id']
            ))
        
        # Call LLM again with tool results
        final_response = llm_with_tools.invoke(state['messages'])
        state['messages'].append(final_response)
    else:
        state['messages'].append(response)
    
    return state
```

---

### LangGraph Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER MESSAGE ARRIVES                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   ENTRY: Load State  │
              │                      │
              │ • Conversation history
              │ • User context       │
              │ • Previous tool calls│
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │    NODE: LLM Call    │
              │                      │
              │ LLM analyzes request │
              │ and decides action   │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  CONDITIONAL EDGE    │
              │                      │
              │ Does LLM need tools? │
              └──────┬───────┬───────┘
                     │       │
          ┌──────────┘       └──────────┐
          │ YES                      NO  │
          ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│ NODE: Tool Calls │          │    END: Return   │
│                  │          │                  │
│ • Web search     │          │ Final response   │
│ • Calculator     │          │ to user          │
│ • DB query       │          └──────────────────┘
│ • API calls      │
└─────────┬────────┘
          │
          ▼
┌──────────────────┐
│ NODE: LLM with   │
│   Tool Results   │
│                  │
│ Synthesize final │
│ answer           │
└─────────┬────────┘
          │
          ▼
┌──────────────────┐
│  END: Return     │
│                  │
│ Final response   │
└──────────────────┘
```

---

### Advanced: Multi-Agent Workflow

For complex tasks, use multiple specialized agents:

```python
# Define specialized agents
class ResearchAgentState(AgentState):
    research_results: list[str]

class WritingAgentState(AgentState):
    draft: str

# Research Agent
def research_node(state: ResearchAgentState):
    # Use web search tool
    results = web_search_tool.invoke(state['messages'][-1].content)
    state['research_results'].append(results)
    return state

# Writing Agent
def writing_node(state: WritingAgentState):
    # Use LLM to write based on research
    prompt = f"Write a response based on: {state['research_results']}"
    response = llm.invoke(prompt)
    state['draft'] = response.content
    return state

# Review Agent
def review_node(state: AgentState):
    # Check quality, ask for revisions if needed
    ...

# Build multi-agent workflow
workflow = StateGraph(AgentState)
workflow.add_node("research", research_node)
workflow.add_node("write", writing_node)
workflow.add_node("review", review_node)

workflow.add_edge("research", "write")
workflow.add_edge("write", "review")
workflow.add_conditional_edges(
    "review",
    lambda state: "write" if state.get('needs_revision') else END
)
```

---

### Testing LangGraph Integration

```python
# Test script: test_langgraph.py
from app.services.langgraph_agent import agent, AgentState
from langchain_core.messages import HumanMessage

def test_simple_question():
    state = AgentState(
        messages=[HumanMessage(content="What is 25 * 47?")],
        user_id="test",
        conversation_id="test",
        next_step="start"
    )
    
    result = agent.invoke(state)
    print(result['messages'][-1].content)
    # Should use calculator tool and return 1175

def test_web_search():
    state = AgentState(
        messages=[HumanMessage(content="What's the weather in London today?")],
        user_id="test",
        conversation_id="test",
        next_step="start"
    )
    
    result = agent.invoke(state)
    print(result['messages'][-1].content)
    # Should use web search and provide current weather

# Run tests
test_simple_question()
test_web_search()
```

---

### Logging & Debugging

LangGraph provides built-in callbacks for monitoring:

```python
from langchain.callbacks import StdOutCallbackHandler

# Add callback to see execution flow
result = agent.invoke(
    initial_state,
    config={"callbacks": [StdOutCallbackHandler()]}
)

# Outputs:
# > Entering node: llm
# > LLM call: What is 25 * 47?
# > Tool call: calculate(25 * 47)
# > Result: 1175
# > Entering node: tools
# > Exiting: Final answer
```

---

### Persistent State with Checkpointing

Save agent state to resume later:

```python
from langgraph.checkpoint.postgres import PostgresCheckpointSaver

# Use your database for checkpoints
checkpointer = PostgresCheckpointSaver(
    connection_string=settings.DATABASE_URL
)

# Compile with checkpointing
agent = workflow.compile(checkpointer=checkpointer)

# Run with thread_id to save/resume
result = agent.invoke(
    initial_state,
    config={"configurable": {"thread_id": str(conversation_id)}}
)

# Later, resume from same thread_id
# Agent will have full memory of previous executions
```

---

### LangGraph Benefits Summary

| Feature | Direct Gemini | With LangGraph |
|---------|---------------|----------------|
| **Tools** | ❌ No | ✅ Yes (calculator, search, DB) |
| **Multi-step** | ❌ Single turn | ✅ Complex workflows |
| **State** | ❌ Just history | ✅ Custom state tracking |
| **Control** | ❌ Black box | ✅ Exact flow definition |
| **Debugging** | ❌ Hard | ✅ Step-by-step visibility |
| **Human-in-loop** | ❌ No | ✅ Can pause for approval |
| **Streaming** | ❌ No | ✅ Token-by-token |

---

