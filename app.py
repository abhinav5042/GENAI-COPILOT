import os, time
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
load_dotenv()

st.set_page_config(page_title="PM Copilot", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

@st.cache_resource
def init_llms():
    gpt = ChatOpenAI(model="gpt-4o", temperature=0.4, api_key=os.environ.get("OPENAI_API_KEY",""))
    gemini = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.environ.get("GOOGLE_API_KEY",""))
    groq_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3, api_key=os.environ.get("GROQ_API_KEY",""))
    return gpt, gemini, groq_llm

def prd_agent(idea):
    gpt,_,_ = init_llms()
    return gpt.invoke([SystemMessage(content="You are a senior PM. Write a full PRD with sections: Overview, Problem Statement, Proposed Solution, Target Users, Functional Requirements, Non-Functional Requirements, Success Metrics, Out of Scope. Use bullet points."), HumanMessage(content=f"Product: {idea}")]).content

def market_agent(idea):
    _, gemini, groq_llm = init_llms()
    system = "You are a market analyst. Provide: Market Sizing (TAM/SAM/SOM with assumptions), Competitive Landscape (3-5 real competitors with strengths/weaknesses), Key Market Trends (3-4 trends), Go-to-Market Recommendation (1-2 paragraphs with real numbers)."
    try:
        return gemini.invoke([SystemMessage(content=system), HumanMessage(content=f"Product: {idea}")]).content
    except Exception:
        return groq_llm.invoke([SystemMessage(content=system), HumanMessage(content=f"Product: {idea}")]).content

def stories_agent(idea, prd=""):
    _,_,groq_llm = init_llms()
    return groq_llm.invoke([SystemMessage(content="You are an Agile PM. Generate 8-12 user stories grouped in Epics. Format each as: ### Story N: Title\n**As a** user **I want** goal **so that** benefit.\n**Acceptance Criteria:**\n- [ ] item\n**Story Points:** N\n**Priority:** High/Medium/Low"), HumanMessage(content=f"Product: {idea}\nPRD: {prd[:1000]}")]).content

def risk_agent(idea, market=""):
    _,_,groq_llm = init_llms()
    return groq_llm.invoke([SystemMessage(content="You are a risk consultant. Generate tables for Technical Risks, Market Risks, Execution Risks with columns: Risk|Severity|Likelihood|Mitigation. Then list Top 3 Priority Risks."), HumanMessage(content=f"Product: {idea}\nMarket: {market[:800]}")]).content

def route(q, idea, outputs, history):
    gpt, gemini, groq_llm = init_llms()
    ql = q.lower()
    if any(k in ql for k in ["story","epic","backlog","acceptance","sprint"]): llm,a,b = groq_llm,"Groq/Llama","badge-groq"; sys="You are an Agile PM assistant."
    elif any(k in ql for k in ["market","competitor","pricing","tam","gtm","revenue"]): llm,a,b = gemini,"Gemini Flash","badge-gemini"; sys="You are a market analyst."
    elif any(k in ql for k in ["risk","threat","mitigation","challenge"]): llm,a,b = groq_llm,"Groq/Llama","badge-groq"; sys="You are a risk consultant."
    else: llm,a,b = gpt,"GPT-4o","badge-gpt"; sys="You are a senior PM."
    ctx = f"Product: {idea}\n" + (f"PRD: {outputs.get('prd','')[:500]}\n" if outputs.get('prd') else "")
    return llm.invoke([SystemMessage(content=sys), HumanMessage(content=f"{ctx}\nQuestion: {q}")]).content, a, b

for k,v in {"idea":"","outputs":{},"conv":[],"done":False,"t":None}.items():
    if k not in st.session_state: st.session_state[k]=v

with st.sidebar:
    st.markdown("## 🧠 PM Copilot")
    st.divider()
    st.markdown("🟦 **GPT-4o** — PRD\n\n🟩 **Gemini Flash** — Market *(free)*\n\n🟪 **Groq/Llama** — Stories + Risk *(free)*")
    st.divider()
    ok = st.text_input("OpenAI Key", value=os.environ.get("OPENAI_API_KEY",""), type="password")
    gg = st.text_input("Google Key (free → aistudio.google.com)", value=os.environ.get("GOOGLE_API_KEY",""), type="password")
    gk = st.text_input("Groq Key (free → console.groq.com)", value=os.environ.get("GROQ_API_KEY",""), type="password")
    if ok: os.environ["OPENAI_API_KEY"]=ok
    if gg: os.environ["GOOGLE_API_KEY"]=gg
    if gk: os.environ["GROQ_API_KEY"]=gk
    if st.session_state.done:
        st.divider()
        st.success(f"✅ Done in {st.session_state.t:.1f}s")
        if st.button("🔄 New Product"): [st.session_state.update({k:v}) for k,v in {"idea":"","outputs":{},"conv":[],"done":False,"t":None}.items()]; st.rerun()
    st.divider()
    st.caption("IE5374 · Spring 2026")

st.markdown("# 🧠 PM Copilot")
st.markdown("*Multi-Agent Product Management Assistant*")

tabs = st.tabs(["💬 Chat","📄 PRD","📊 Market","🗂 Stories","⚠️ Risks"])

with tabs[0]:
    if not st.session_state.done:
        idea = st.text_area("Product idea", placeholder="e.g. Fitness tracking app for remote workers with team challenges...", height=100, label_visibility="collapsed")
        ex = st.selectbox("Or try:", ["","AI code review tool","Freelance PM marketplace","Mental wellness app","B2B invoice SaaS"], label_visibility="collapsed")
        if ex and not idea: idea=ex
        if st.button("🚀 Generate PM Suite", type="primary"):
            if not idea.strip(): st.warning("Enter a product idea first.")
            elif not all([os.environ.get("OPENAI_API_KEY"), os.environ.get("GOOGLE_API_KEY"), os.environ.get("GROQ_API_KEY")]): st.error("Add all three API keys in the sidebar.")
            else:
                st.session_state.idea = idea.strip()
                t0 = time.time()
                with st.status("Orchestrating agents...", expanded=True) as s:
                    st.write("🟦 GPT-4o → PRD..."); st.session_state.outputs["prd"] = prd_agent(idea); st.write("✅ PRD done")
                    st.write("🟩 Gemini Flash → Market..."); st.session_state.outputs["market"] = market_agent(idea); st.write("✅ Market done")
                    st.write("🟪 Groq → Stories..."); st.session_state.outputs["stories"] = stories_agent(idea, st.session_state.outputs["prd"]); st.write("✅ Stories done")
                    st.write("🟪 Groq → Risks..."); st.session_state.outputs["risks"] = risk_agent(idea, st.session_state.outputs["market"]); st.write("✅ Risks done")
                    s.update(label="✅ All done!", state="complete")
                st.session_state.t = time.time()-t0; st.session_state.done=True
                st.session_state.conv.append({"role":"assistant","content":f"✅ PM suite ready in {st.session_state.t:.1f}s — switch to any tab above!","agent":"System"})
                st.rerun()
    else:
        st.markdown(f"**Product:** `{st.session_state.idea}`"); st.divider()
        for m in st.session_state.conv:
            if m["role"]=="user": st.markdown(f"**You:** {m['content']}")
            else: st.markdown(f"**{m.get('agent','PM Copilot')}:** {m['content']}")
        with st.form("cf", clear_on_submit=True):
            c1,c2=st.columns([5,1])
            with c1: ui=st.text_input("Ask",placeholder="Refine anything...",label_visibility="collapsed")
            with c2: send=st.form_submit_button("Send →")
        if send and ui:
            st.session_state.conv.append({"role":"user","content":ui})
            with st.spinner("Thinking..."): r,a,_ = route(ui,st.session_state.idea,st.session_state.outputs,st.session_state.conv)
            st.session_state.conv.append({"role":"assistant","content":r,"agent":a}); st.rerun()
        st.markdown("**Quick:**")
        qc=st.columns(4)
        for i,q in enumerate(["Add admin story","Biggest risk?","Expand competitors","Pricing model?"]):
            with qc[i]:
                if st.button(q,key=f"q{i}"):
                    st.session_state.conv.append({"role":"user","content":q})
                    r,a,_=route(q,st.session_state.idea,st.session_state.outputs,st.session_state.conv)
                    st.session_state.conv.append({"role":"assistant","content":r,"agent":a}); st.rerun()

for tab,badge,label,title,key,fn,dl in [
    (tabs[1],"GPT-4o","Generated by GPT-4o","📄 PRD","prd",lambda:prd_agent(st.session_state.idea),"PRD.md"),
    (tabs[2],"Gemini Flash","Generated by Gemini Flash","📊 Market Analysis","market",lambda:market_agent(st.session_state.idea),"Market.md"),
    (tabs[3],"Groq/Llama","Generated by Groq/Llama","🗂 User Stories","stories",lambda:stories_agent(st.session_state.idea,st.session_state.outputs.get("prd","")),"Stories.md"),
    (tabs[4],"Groq/Llama","Generated by Groq/Llama","⚠️ Risk Assessment","risks",lambda:risk_agent(st.session_state.idea,st.session_state.outputs.get("market","")),"Risks.md"),
]:
    with tab:
        if not st.session_state.done: st.info("Generate a suite first in the Chat tab.")
        else:
            st.markdown(f"**{label}** | **Product:** {st.session_state.idea}"); st.divider()
            st.markdown(st.session_state.outputs.get(key,""))
            c1,c2=st.columns(2)
            with c1: st.download_button("⬇️ Download",data=st.session_state.outputs.get(key,""),file_name=dl,mime="text/markdown")
            with c2:
                if st.button("🔄 Regenerate",key=f"r_{key}"):
                    with st.spinner("Regenerating..."): st.session_state.outputs[key]=fn()
                    st.rerun()