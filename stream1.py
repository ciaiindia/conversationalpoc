import streamlit as st
from app1_copy import qp  # Ensure app1.py defines the pipeline with root component 'input'
from llama_index.core.llms import ChatResponse
import re

# Function to parse SQL query from ChatResponse
def parse_response_to_sql(response: ChatResponse) -> str:
    raw = response.message.content
    try:
        if "SQLQuery:" in raw:
            sql_part = raw.split("SQLQuery:")[-1]
            sql_part = sql_part.split("SQLResult:")[0].split("Answer:")[0].strip()
            cleaned = re.sub(r"^[\\s`]*sql[\\s`]*", "", sql_part, flags=re.IGNORECASE)
            cleaned = cleaned.strip().strip("```").strip()
            return cleaned
        # Handle markdown code blocks
        sql_match = re.search(r"```sql\n(.*?)\n```", raw, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        return "(No SQLQuery section found in response)"
    except Exception as e:
        return f"(Error parsing SQL query: {str(e)})"

# Function to parse final answer from ChatResponse
def parse_final_answer(response: ChatResponse) -> str:
    raw = response.message.content
    try:
        if "Answer:" in raw:
            answer_part = raw.split("Answer:")[-1].strip()
            return answer_part
        return raw.strip()  # Fallback to full content
    except Exception as e:
        return f"(Error parsing final answer: {str(e)})"

st.set_page_config(page_title="SQL Assistant", layout="wide")
st.title("🧠 Natural Language to SQL Assistant")

# Input from user
user_query = st.text_input("Ask your question about Salesmate AI data")

if user_query:
    with st.spinner("Processing your question..."):
        try:
            # Run the query pipeline
            result = qp.run(input=user_query)

            # Extract and display raw response for debugging
            raw_response = ""
            if isinstance(result, ChatResponse):
                raw_response = result.message.content
                print("Raw ChatResponse content:", raw_response)  # Console debug
            else:
                raw_response = str(result)
                print("Raw response (non-ChatResponse):", raw_response)

            # Extract SQL query and final answer
            if isinstance(result, ChatResponse):
                sql_query = parse_response_to_sql(result)
                final_answer = parse_final_answer(result)
            else:
                sql_query = "(Unexpected response type)"
                final_answer = str(result)

            # Fallback messages for empty results
            if not sql_query or sql_query == "":
                sql_query = "(No SQL query generated)"
            if not final_answer or final_answer == "":
                final_answer = "(No answer generated)"

        except Exception as e:
            raw_response = f"(Error: {str(e)})"
            sql_query = "(Error while generating SQL)"
            final_answer = f"Error: {str(e)}"

    # Display the raw response for inspection
    st.subheader("🔍 Raw Response (Debug)")
    st.text_area("Raw ChatResponse content:", raw_response, height=200)

    # Display the generated SQL query
    st.subheader("📄 Generated SQL Query")
    st.code(sql_query, language="sql")

    # Display the final answer
    st.subheader("✅ Final Answer")
    st.write(final_answer)

st.markdown("---")
st.caption("Built with LlamaIndex, Azure OpenAI, and Streamlit")