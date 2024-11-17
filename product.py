from dotenv import load_dotenv
import streamlit as st
import mariadb
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import openai
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
import os

# Load environment variables
load_dotenv()

# Connecting to Database
def init_database(user: str, password: str, host: str, port: str, database: str):
    try:
        # Establishing connection to MariaDB
        conn = mariadb.connect(
            user=user,
            password=password,
            host=host,
            port=int(port),
            database=database
        )
        # Create a cursor object to interact with the database
        cursor = conn.cursor()
        return conn, cursor
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        return None, None

def get_sqlChain(conn, cursor):
    # Get the schema dynamically from the database
    schema = get_schema_from_db(cursor)  # Function to get schema info dynamically

    # Define the template for the SQL generation
    template = """
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database. 
    Based on the table schema below, write a SQL query that would answer the user's question. Take the conversation history into account.

    <SCHEMA>{schema}</SCHEMA>

    Conversation History: {chat_history}

    Write only the SQL query and nothing else. Do not wrap the SQL query in any other text, not even backticks.

    For example:
    Question: which 3 artists have the most tracks?
    SQL Query: SELECT ArtistId, COUNT(*) FROM Track GROUP BY ArtistId ORDER BY track_count DESC LIMIT 3;
    Question: Name 10 artists
    SQL Query: SELECT Name FROM Artist LIMIT 10;

    Your turn:
    note: only give the sql query without messages such as: certainly, of course, etc..
    note: in the sql query don't use the AS/alias Clause, for example don't use "SELECT count(Name) AS CountName FROM Table;", but use like this for example: SELECT count(Name) FROM Table;
    note : RETURNING QUERY THAT HAS  "AS/ALIAS CLAUSE" IS FORBIDEN ,RETURN THE QUERY THAT DON'T HAS AS CLAUSE
    don't use the AS/ALIAS Clause in SQL
    don't use the AS/ALIAS Clause in SQL
    don't use the AS/ALIAS Clause in SQL
    RETURN the query without use any Aliases

    Question: {question}
    without using an alias clause
    SQL Query:
    """

    # Create the prompt using the ChatPromptTemplate, passing the actual schema
    prompt = ChatPromptTemplate.from_template(template)

    # Initialize the language model
    llm = ChatGroq(model="mixtral-8x7b-32768", temperature=0)

    # Create a pipeline with RunnablePassthrough
    schema_runnable = RunnablePassthrough(lambda x: schema)
    prompt_runnable = prompt
    llm_runnable = llm
    parser_runnable = StrOutputParser()

    # Return a Runnable sequence
    return schema_runnable | prompt_runnable | llm_runnable | parser_runnable

def get_schema_from_db(cursor):
    # Function to fetch schema information from the database
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    schema = ""
    for table in tables:
        table_name = table[0]
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        schema += f"Table: {table_name}\n"
        for column in columns:
            schema += f"Column: {column[0]}, Type: {column[1]}\n"
        schema += "\n"
    return schema

def get_response(user_query, conn, cursor, chat_history):
    # Get SQL chain
    sql_chain = get_sqlChain(conn, cursor)

    # Define the template for the natural language generation
    template = """
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the database.
    Based on the table schema below, question, sql query, and sql response, write a natural language response.
    <SCHEMA>{schema}</SCHEMA>

    Conversation History: {chat_history}
    SQL Query: <SQL>{query}</SQL>
    User question: {question}
    SQL Response: {response}"""

    # Create the prompt using the ChatPromptTemplate, passing the actual schema
    prompt = ChatPromptTemplate.from_template(template)

    # Initialize the language model
    llm = ChatGroq(model="mixtral-8x7b-32768", temperature=0)

    # Create a chain pipeline & Create a pipeline with RunnablePassthrough
    prompt_runnable = prompt
    llm_runnable = llm
    parser_runnable = StrOutputParser()

    # Get schema and generate SQL query
    schema = get_schema_from_db(cursor)
    result = sql_chain.invoke({"chat_history": chat_history, "question": user_query, "schema": schema})

    # Debug: Print the raw SQL query before execution
    print("Generated SQL Query (Raw):", result)

    # Ensure query is safe and handle special characters (escaping backslashes, underscores)
    result = result.replace("\\", "\\\\")  # Double escape backslashes
    result = result.replace("_", "\\_")    # Escape underscores

    # Debug: Print the escaped SQL query
    print("Generated SQL Query (Escaped):", result)

    try:
        # Execute the SQL query
        cursor.execute(result)
        response = cursor.fetchall()

        if response:
            # Convert response to a formatted string
            response = "\n".join([str(row) for row in response])
        else:
            response = "No results found."

    except mariadb.ProgrammingError as e:
        # Capture and log the specific error
        print("SQL Execution Error:", e)
        response = f"Error executing query: {e}"

    # Return the response after running the query and processing it
    chain = (
        RunnablePassthrough()
        .assign(query=sql_chain)
        .assign(schema=lambda _: schema)
        .assign(response=lambda vars: str(response).replace("\\", ""))
        | prompt_runnable
        | llm_runnable
        | parser_runnable
    )
    return chain.invoke({"chat_history": chat_history, "question": user_query, "schema": schema})

# Initialize chat history if not present
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [AIMessage(content="Hello, I'm SQL Assistant. Ask me anything about your database.")]

# Streamlit UI setup
st.set_page_config(page_title='Chat With MariaDB', page_icon=":speech_balloon:")
st.title('Chat With MariaDB Databases')

# Sidebar settings for connection
with st.sidebar:
    st.subheader("Settings")
    st.write('This is a simple chat with MariaDB. Connect to the Database and start chatting!')
    st.text_input("Host", value='localhost', key='Host')
    st.text_input("Port", value='3306', key='Port')
    st.text_input("UserName", value='root', key='UserName')
    st.text_input("Password", type='password', value='', key='Password')
    st.text_input("Database", value='', key='Database')

    # If the button is clicked, connect to the database
    if st.button('Connect'):
        with st.spinner('Connecting to Database....'):
            conn, cursor = init_database(st.session_state['UserName'], st.session_state['Password'], st.session_state['Host'], st.session_state['Port'], st.session_state['Database'])
            st.session_state.conn = conn
            st.session_state.cursor = cursor
            st.success('Connected to Database!')

# Display the chat history
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)

# Handle user input
user_query = st.chat_input('Type a message.....')
if user_query and user_query.strip() != "":
    st.session_state.chat_history.append(HumanMessage(content=user_query))

    with st.chat_message("Human"):
        st.markdown(user_query)

    with st.chat_message("AI"):
        # Invoke the SQL chain with schema, chat history, and the user query
        response = get_response(user_query, st.session_state.conn, st.session_state.cursor, st.session_state.chat_history)
        
        # Convert response to string if needed
        if isinstance(response, (list, tuple)):
            response = "\n".join([str(item) for item in response])
        elif not isinstance(response, str):
            response = str(response)

        # Display the SQL response
        st.markdown(response)
    
    st.session_state.chat_history.append(AIMessage(content=response))
