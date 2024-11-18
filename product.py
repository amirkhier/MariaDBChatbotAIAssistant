from dotenv import load_dotenv
import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
import os

# Load environment variables
load_dotenv()



# Connecting to Database
def init_database(user: str, password: str, host: str, port: str, database: str) -> SQLDatabase:
    db_uri = f"mariadb+mariadbconnector://{user}:{password}@{host}:{port}/{database}"
    return SQLDatabase.from_uri(db_uri)

def get_sqlChain(db):
    # Get the schema dynamically from the database
    schema = db.get_table_info()

    # Define the template for the SQL generation
    template = """
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database. 
    Based on the table schema below, write a SQL query that would answer the user's question. Take the conversation history into account.

    <SCHEMA>{schema}</SCHEMA>

    Conversation History: {chat_history}

    Write only the SQL query and nothing else. Do not wrap the SQL query in any other text, not even backticks.

    For example:
    Question: which 3 artists have the most tracks?
    SQL Query: SELECT ArtistId, COUNT(*) as track_count FROM Track GROUP BY ArtistId ORDER BY track_count DESC LIMIT 3;
    Question: Name 10 artists
    SQL Query: SELECT Name FROM Artist LIMIT 10;

    Your turn:
    note: only give the sql query without messages such as: certainly, of course, etc..
    note: in the sql query don't use the AS/alias Clause, for example don't use "SELECT count(Name) AS CountName FROM Table;", but use like this for example: SELECT count(Name) FROM Table;
    note : RETURNING QUERY THAT HAS  "AS/ALIAS CLAUSE" IS FORBIDEN ,RETURN THE QUERY THAT DON'T HAS AS CLAUSE
    don't use the AS/ALIAS Clause in SQL
    don't use the AS/ALIAS Clause in SQL
    don't use the AS/ALIAS Clause in SQL
    RETURN the query without any Aliases clauses

    Question: {question}
    SQL Query:
    """

    # Create the prompt using the ChatPromptTemplate, passing the actual schema
    prompt = ChatPromptTemplate.from_template(template)

    # Initialize the language model
    llm = ChatGroq(model="mixtral-8x7b-32768", temperature=0)
    # llm = ChatOpenAI(model="gpt-4o-mini")

    # Create a pipeline with RunnablePassthrough
    schema_runnable = RunnablePassthrough(lambda x: schema)
    prompt_runnable = prompt
    llm_runnable = llm
    parser_runnable = StrOutputParser()

    # Return a Runnable sequence
    return schema_runnable | prompt_runnable | llm_runnable | parser_runnable


#defining fucntion that has responses is transformation from query to natural language result :
def get_response(user_query : str , db :SQLDatabase , chat_history :list):
    sql_chain = get_sqlChain(db)
    # Define the template for the natural language generation
    template = """
    You are a data analyst at . You are interacting with a user who is asking you questions about the database.
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
    #"chat_history": st.session_state.chat_history,"question": user_query,"schema" : schema
    chain = (
    RunnablePassthrough()
    .assign(query=sql_chain)
    .assign(schema=lambda _: db.get_table_info())
    .assign(response=lambda vars: db.run(sql_chain.invoke({"chat_history": chat_history,"question": user_query,"schema" : db.get_table_info()})).replace("\\",""))
    | prompt_runnable
    | llm_runnable
    | parser_runnable
     )
    return chain.invoke({"chat_history": chat_history,"question": user_query,"schema" : db.get_table_info()})




# Initialize chat history if not present
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [AIMessage(content="Hello I'm SQL Assistant. Ask me Anything About your database.")]

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
            db = init_database(st.session_state['UserName'], st.session_state['Password'], st.session_state['Host'], st.session_state['Port'], st.session_state['Database'])
            st.session_state.db = db
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
        
        # schema = st.session_state.db.get_table_info()
        # # Invoke the SQL chain with schema, chat history, and the user query
        # sql_chain = get_sqlChain(st.session_state.db)
        

        response = get_response(user_query,st.session_state.db,st.session_state.chat_history)
        # response = sql_chain.invoke({"chat_history": st.session_state.chat_history,"question": user_query,"schema" : schema})
        # Display the SQL response
        st.markdown(response)
    
    st.session_state.chat_history.append(AIMessage(content=response))
