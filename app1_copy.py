from llama_index.core import Settings
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.core.prompts import BasePromptTemplate
import re

azure_openai_endpoint = "https://atu.openai.azure.com/"
azure_openai_api_key = "ba864158627b4fb4aaa72bc755fe7c72"
azure_openai_model_gpt4 = "gpt-4o-20240513"
azure_openai_model_gpt3 = "gpt-35-turbo-0613"
deployment = "gpt-4o-atu"
endpoint = "https://ciaiaiservicesgpt4.openai.azure.com/"
model_name = "gpt-4o"
deployment = "gpt-4o-atu"

subscription_key = "<your-api-key>"
api_version = "2024-12-01-preview"

llm = AzureOpenAI(
            model="gpt-4o",
            deployment_name=deployment,
            api_key=azure_openai_api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
            temperature=0.0001,
            seed=42
     )

EMBED_MODEL = AzureOpenAIEmbedding(
    model="text-embedding-ada-002",
    deployment_name="ResearchmateAI-Embeddings",
    api_key="817dce22f5a548b8b11fe0b6a3cf2c36",
    azure_endpoint="https://ciaiaiservices.openai.azure.com/",
    api_version="2024-05-01-preview"
)
Settings.embed_model = EMBED_MODEL

Settings.llm = llm

import urllib
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, select
from llama_index.core import SQLDatabase
from llama_index.core.query_engine import NLSQLTableQueryEngine

# Azure SQL connection parameters
server = "ciai-test-sql-server.database.windows.net"
database = "marketaccess-db"
username = "ciai-test-sql-admin"
password = "Ssr@Rrr123"
driver = "{ODBC Driver 17 for SQL Server}"  # Latest driver recommended

# Format connection parameters for URL encoding
params = urllib.parse.quote_plus(
    f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30"
)

# Create the connection string for Azure SQL
azure_sql_uri = f"mssql+pyodbc:///?odbc_connect={params}"

engine = create_engine(azure_sql_uri)

sql_database = SQLDatabase(engine, schema='dbo')

import json
from typing import List
from pydantic import BaseModel, Field

# Define the TableInfo model
class TableInfo(BaseModel):
    """Information regarding a structured table."""
    table_name: str = Field(
        ..., description="table name (must be underscores and NO spaces)"
    )
    table_summary: str = Field(
        ..., description="short, concise summary/caption of the table"
    )

# Your mapping from period to table ID
PERIOD_TO_TABLE_ID = {
    "C12M": "00_C12M",
    "C13W": "01_C13W",
    "C1M": "02_C1M",
    "C1W": "03_C1W",
    "C3M": "04_C3M",
    "C4W": "05_C4W",
    "C6M": "06_C6M",
}


def get_table_infos_from_json(json_path: str) -> List[TableInfo]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    table_infos = []
    for table in data.get("tables", []):
        table_name = table.get("db_table_name", "")
        description = table.get("description", "")
        if table_name and description:
            table_infos.append(TableInfo(table_name=table_name, table_summary=description))
    return table_infos

# Example usage:
file_path = r"C:\Users\AkhilNarasimhaS\OneDrive - CustomerInsights.AI, Inc\Documents\NewARch TESTING\Salmate ai\salesmate-ai-json 3.json"
table_infos = get_table_infos_from_json(file_path)
for t in table_infos:
    print(t)

from llama_index.core.objects import (
    SQLTableNodeMapping,
    ObjectIndex,
    SQLTableSchema,
)
from llama_index.core import SQLDatabase, VectorStoreIndex

table_node_mapping = SQLTableNodeMapping(sql_database)
print('table node mapping created')

table_infos = get_table_infos_from_json(file_path)  # Loads Final_New_Salesmate
table_schema_objs = [
    SQLTableSchema(table_name=t.table_name, context_str=t.table_summary)
    for t in table_infos
]
print('table schema objs created')

obj_index = ObjectIndex.from_objects(
    table_schema_objs,
    table_node_mapping,
    VectorStoreIndex,
)
print('obj index created')

obj_retriever = obj_index.as_retriever(similarity_top_k=1)  # Only one table
print('obj retriever created')

from llama_index.core.retrievers import SQLRetriever
from typing import List
from llama_index.core.query_pipeline import FnComponent

sql_retriever = SQLRetriever(sql_database)


def get_table_context_str(table_schema_objs: List[SQLTableSchema]):
    """Get table context string."""
    context_strs = []
    for table_schema_obj in table_schema_objs:
        table_info = sql_database.get_single_table_info(
            table_schema_obj.table_name
        )
        if table_schema_obj.context_str:
            table_opt_context = " The table description is: "
            table_opt_context += table_schema_obj.context_str
            table_info += table_opt_context

        context_strs.append(table_info)
    return "\n\n".join(context_strs)


table_parser_component = FnComponent(fn=get_table_context_str)

from llama_index.core.prompts.default_prompts import DEFAULT_TEXT_TO_SQL_PROMPT
from llama_index.core import PromptTemplate
from llama_index.core.query_pipeline import FnComponent
from llama_index.core.llms import ChatResponse


import re
from llama_index.core.llms import ChatResponse

def parse_response_to_sql(response: ChatResponse) -> str:
    raw = response.message.content
    print("sql_output_parser input:", raw)
    sql_part = raw.split("SQLQuery:")[-1]
    cleaned = re.sub(r"^[\\s`]*sql[\\s`]*", "", sql_part, flags=re.IGNORECASE)
    cleaned = cleaned.split("SQLResult:")[0].strip().strip("```").strip()
    print("Parsed SQL Query:", cleaned)
    return cleaned

sql_parser_component = FnComponent(fn=parse_response_to_sql)

text2sql_prompt = DEFAULT_TEXT_TO_SQL_PROMPT.partial_format(
    dialect=engine.dialect.name
)

CUSTOM_TEXT_TO_SQL_TPL = """
Given an input question, create a syntactically correct {dialect} query to run, then look at the results and return the answer. Use only the table '[Final_New_Salesmate1]' and its columns as described in the schema. You can order the results by a relevant column to return the most interesting examples.

Never query for all columns; select only relevant columns based on the question. Use column names exactly as provided (e.g., [VELTASSA TRX], [HCP Name], [WEEK_ENDING_DATE]). Qualify column names with the table name when needed.

Use the following format, each on a new line:
Question: Question here
SQLQuery: SQL Query to run
SQLResult: Result of the SQLQuery
Answer: Final answer here

Only use the table listed below:
{schema}

Question: {query_str}
SQLQuery:
IMPORTANT RULES:
    1. Generate a SINGLE valid T-SQL SELECT query for the table [Final_New_Salesmate1].
    2. Return JUST the SQL query without markdown, code block markers, or extra text.
    3. Use ONLY column names from the schema (e.g., [VELTASSA TRX], [LOKELMA TRX], [HCP Name], [WEEK_ENDING_DATE], [MONTH_ENDING_DATE], [TRX Complete Month Flag], [NRX Complete Month Flag], [Claims Complete Month Flag]).
    4. ALWAYS enclose column names in square brackets.
    5. Use SELECT TOP N for limiting rows (e.g., 'top 5') or non-aggregated queries; default to TOP 10 for 'highest' queries if no number is specified.
    6. NEVER use LIMIT; it is invalid in SQL Server.
    7. For aggregate queries (e.g., SUM, COUNT) asking for a single total, do NOT use GROUP BY.
    8. For queries with non-aggregated columns (e.g., [HCP Name]), include those columns in GROUP BY.
    9. Use LIKE '%NAME%' for territory, HCP Name, or location names in capital letters (e.g., '%COLUMBUS%').
    10. For partial text matching, use LIKE '%TERM%' in capital letters.
    11. For 'top' or 'highest', SELECT entity and metric, ORDER BY metric DESC.
    12. For time-based filtering, use [WEEK_ENDING_DATE] for weekly queries and [MONTH_ENDING_DATE] for monthly or longer periods.
    13. For weekly queries (e.g., 'past week' or 'last week'):
        - Find the maximum [WEEK_ENDING_DATE] using a subquery:
          (SELECT MAX([WEEK_ENDING_DATE]) FROM [Final_New_Salesmate1])
        - Define the week as [WEEK_ENDING_DATE] BETWEEN DATEADD(DAY, -6, max_date) AND max_date
        
    14. For monthly queries (e.g., 'last month' or 'previous month'):
        - Find the maximum [MONTH_ENDING_DATE] where the relevant flag = 1 using a subquery:
          (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1)
        - Define the month as [MONTH_ENDING_DATE] BETWEEN DATEADD(MONTH, -1, DATEADD(MONTH, DATEDIFF(MONTH, 0, max_date), 0)) AND max_date
        - Include [TRX Complete Month Flag] = 1 for TRx queries (and similarly for NRx/Claims).
    15. Map other time periods to date ranges using [MONTH_ENDING_DATE]:
        - 'past year' or 'last 12 months':
            [MONTH_ENDING_DATE] BETWEEN DATEADD(MONTH, -12, (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1)) AND (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1)
        - 'current half' or 'last 6 months':
            [MONTH_ENDING_DATE] BETWEEN DATEADD(MONTH, -6, (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1)) AND (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1)
        - 'previous half':
            [MONTH_ENDING_DATE] BETWEEN DATEADD(MONTH, -12, (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1)) AND DATEADD(MONTH, -6, (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1))
        - 'current quarter' or 'last 3 months':
            [MONTH_ENDING_DATE] BETWEEN DATEADD(MONTH, -3, (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1)) AND (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1)
        - 'previous quarter':
            [MONTH_ENDING_DATE] BETWEEN DATEADD(MONTH, -6, (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1)) AND DATEADD(MONTH, -3, (SELECT MAX([MONTH_ENDING_DATE]) FROM [Final_New_Salesmate1] WHERE [TRX Complete Month Flag] = 1))
    16. For decline calculations, calculate (PreviousPeriod - CurrentPeriod) and sort DESC.
    17. For percentage growth, calculate ((CurrentPeriod - PreviousPeriod) / NULLIF(PreviousPeriod, 0)) * 100.
    18. Apply flag filters based on the metric only if the query has month :
        - For [VELTASSA TRX] or [LOKELMA TRX], add [TRX Complete Month Flag] = 1 to the WHERE clause.
        - For [VELTASSA NRX] or [LOKELMA NRX], add [NRX Complete Month Flag] = 1 to the WHERE clause.
        - For [VELTASSA DISPENSED CLAIMS] or [LOKELMA DISPENSED CLAIMS], add [Claims Complete Month Flag] = 1 to the WHERE clause.
    19. For weekly queries (e.g., 'total TRx past week'):
        SELECT
            SUM([VELTASSA TRX]) AS TotalTRx
        FROM [table_name]
        WHERE [WEEK_ENDING_DATE] BETWEEN 
                DATEADD(DAY, -6, (SELECT MAX([WEEK_ENDING_DATE]) FROM [table_name])) 
                AND (SELECT MAX([WEEK_ENDING_DATE]) FROM [table_name]);
    20. For monthly queries (e.g., 'total TRx last month for HCP'):
        SELECT
            SUM([VELTASSA TRX]) AS TotalTRx
        FROM [table_name]
        WHERE [HCP Name] LIKE '%HCP_NAME%'
            AND [MONTH_ENDING_DATE] BETWEEN 
                DATEADD(MONTH, -1, DATEADD(MONTH, DATEDIFF(MONTH, 0, (SELECT MAX([MONTH_ENDING_DATE]) FROM [table_name] WHERE [TRX Complete Month Flag] = 1)), 0)) 
                AND (SELECT MAX([MONTH_ENDING_DATE]) FROM [table_name] WHERE [TRX Complete Month Flag] = 1)
            AND [TRX Complete Month Flag] = 1;
    21. For top-N queries (e.g., 'top HCPs for Veltassa TRx'):
        SELECT TOP 10
            [HCP Name],
            SUM([VELTASSA TRX]) AS TotalTRx
        FROM [table_name]
        WHERE [MONTH_ENDING_DATE] BETWEEN 
                DATEADD(MONTH, -12, (SELECT MAX([MONTH_ENDING_DATE]) FROM [table_name] WHERE [TRX Complete Month Flag] = 1)) 
                AND (SELECT MAX([MONTH_ENDING_DATE]) FROM [table_name] WHERE [TRX Complete Month Flag] = 1)
            AND [TRX Complete Month Flag] = 1
        GROUP BY [HCP Name]
        ORDER BY TotalTRx DESC;
    22. For comparison questions (e.g., 'Compare Veltassa TRx for Columbus and Louisville for last month'):
        SELECT
            SUM([VELTASSA TRX]) AS TotalVeltassaTRX,
            [Territory Name]
        FROM [table_name]
        WHERE [MONTH_ENDING_DATE] BETWEEN 
                DATEADD(MONTH, -1, DATEADD(MONTH, DATEDIFF(MONTH, 0, (SELECT MAX([MONTH_ENDING_DATE]) FROM [table_name] WHERE [TRX Complete Month Flag] = 1)), 0)) 
                AND (SELECT MAX([MONTH_ENDING_DATE]) FROM [table_name] WHERE [TRX Complete Month Flag] = 1)
            AND ([Territory Name] LIKE '%COLUMBUS%' OR [Territory Name] LIKE '%LOUISVILLE%')
            AND [TRX Complete Month Flag] = 1
        GROUP BY [Territory Name];
    23. Ensure the query is syntactically complete, closing all parentheses, CTEs, and statements with a semicolon.
    24. If the question cannot be converted to a valid query, return an empty string.
    25. ALWAYS use the table name as [table_name] without additional prefixes or variations.
    26. If no data is available for the specified period, ensure the Answer section explains that no data was found for the most recent complete week or month.
    27.     - For "last N months" (e.g., 'last 8 months'):
        [MONTH_ENDING_DATE] BETWEEN 
            DATEADD(MONTH, -N, (SELECT MAX([MONTH_ENDING_DATE]) FROM [Table_name] WHERE [TRX Complete Month Flag] = 1)) 
            AND (SELECT MAX([MONTH_ENDING_DATE]) FROM [table_name] WHERE [TRX Complete Month Flag] = 1)

"""

CUSTOM_TEXT_TO_SQL_PROMPT = PromptTemplate(CUSTOM_TEXT_TO_SQL_TPL)
custom_filled = CUSTOM_TEXT_TO_SQL_PROMPT.partial_format(dialect=engine.dialect.name)


from llama_index.core.query_pipeline import (
    QueryPipeline as QP,
    Link,
    InputComponent,
    CustomQueryComponent,
)

# In app1.py, replace the response_synthesis_prompt definition
response_synthesis_prompt_str = (
    "Given an input question, an SQL query, and the query results, produce a structured response.\n"
    "Input:\n"
    "- Query: {query_str}\n"
    "- SQL Query: {sql_query}\n"
    "- SQL Result: {context_str}\n"
    "Output the response in the following exact format, with each section on a new line:\n"
    "SQLQuery: {sql_query}\n"
    "SQLResult: {context_str}\n"
    "Answer: Provide only the final answer here\n"
    "Do not modify or omit any sections.\n"
)
response_synthesis_prompt = PromptTemplate(response_synthesis_prompt_str)


from llama_index.core.query_pipeline import FnComponent

def debug_text2sql(response):
    print("text2sql_llm output:", response.message.content)
    return response

debug_text2sql_component = FnComponent(fn=debug_text2sql)

# Modify parse_response_to_sql for debugging
def parse_response_to_sql(response: ChatResponse) -> str:
    raw = response.message.content
    print("sql_output_parser input:", raw)
    try:
        sql_part = raw.split("SQLQuery:")[-1]
        cleaned = re.sub(r"^[\\s`]*sql[\\s`]*", "", sql_part, flags=re.IGNORECASE)
        cleaned = cleaned.split("SQLResult:")[0].strip().strip("```").strip()
        print("Parsed SQL Query:", cleaned)
        return cleaned
    except IndexError:
        print("Failed to parse SQL query from:", raw)
        return ""

sql_parser_component = FnComponent(fn=parse_response_to_sql)

# Add debug for response_synthesis_llm inputs
def debug_response_synthesis(query_str, sql_query, context_str):
    print("Inputs to response_synthesis_llm:", {
        "query_str": query_str,
        "sql_query": sql_query,
        "context_str": context_str
    })
    # Format the prompt manually to verify
    formatted_prompt = response_synthesis_prompt.format(
        query_str=query_str,
        sql_query=sql_query,
        context_str=context_str
    )
    print("Formatted response_synthesis_prompt:", formatted_prompt)
    return {"query_str": query_str, "sql_query": sql_query, "context_str": context_str}

debug_response_synthesis_component = FnComponent(fn=debug_response_synthesis)

# QueryPipeline setup
qp = QP(
    modules={
        "input": InputComponent(),
        "table_retriever": obj_retriever,
        "table_output_parser": table_parser_component,
        "text2sql_prompt": custom_filled,
        "text2sql_llm": llm,
        "debug_text2sql": debug_text2sql_component,
        "sql_output_parser": sql_parser_component,
        "sql_retriever": sql_retriever,
        "response_synthesis_prompt": response_synthesis_prompt,
        "debug_response_synthesis": debug_response_synthesis_component,
        "response_synthesis_llm": llm,
    },
    verbose=True,
)

# Define pipeline links
qp.add_chain(["input", "table_retriever", "table_output_parser"])
qp.add_link("input", "text2sql_prompt", dest_key="query_str")
qp.add_link("table_output_parser", "text2sql_prompt", dest_key="schema")
qp.add_chain(["text2sql_prompt", "text2sql_llm", "debug_text2sql", "sql_output_parser", "sql_retriever"])
qp.add_link("sql_output_parser", "debug_response_synthesis", dest_key="sql_query")
qp.add_link("sql_retriever", "debug_response_synthesis", dest_key="context_str")
qp.add_link("input", "debug_response_synthesis", dest_key="query_str")
qp.add_link("debug_response_synthesis", "response_synthesis_prompt")
qp.add_link("sql_output_parser", "response_synthesis_prompt", dest_key="sql_query")
qp.add_link("sql_retriever", "response_synthesis_prompt", dest_key="context_str")
qp.add_link("input", "response_synthesis_prompt", dest_key="query_str")
qp.add_link("response_synthesis_prompt", "response_synthesis_llm")


import streamlit as st

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





