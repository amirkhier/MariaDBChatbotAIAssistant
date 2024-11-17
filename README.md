# Chat with MariaDB Database

A Streamlit-based application that provides an interactive chat interface for querying MariaDB databases using natural language. This app leverages the LangChain framework and ChatGroq model to translate user queries into SQL, making it accessible to users without SQL knowledge.

## Features
- **Interactive Chat**: Users can interact with the MariaDB database using natural language.
- **Dynamic SQL Query Generation**: The app generates SQL queries based on the conversation history and the database schema.
- **Natural Language Responses**: Converts SQL responses into user-friendly language.
- **Customizable Database Connection**: Connect to different databases by configuring settings in the sidebar.

## Prerequisites

- **Python 3.7+**
- **MariaDB Server** (running locally or remotely)
- **Environment Variables** for secure information management.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/amirkhier/MariaDBAssistantChatbot.git
   cd MariaDBAssistantChatbot
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables by creating a `.env` file in the root directory. Add your credentials and configuration:
   ```plaintext
   OPENAI_API_KEY =<YOUR_OPENAI_API_KEY>
   LANGCHAIN_API_KEY =<YOUR_LANGCHAIN_API_KEY>
   GROQ_API_KEY = <YOUR_GROQ_API_KEY>
   LANGCHAIN_TRACING_V2=true
   
   ```

## Usage

1. **Run the application:**
   ```bash
   streamlit run product.py
   ```

2. **Connect to Database:**
   Use the sidebar to input your database host, port, username, password, and database name, then click `Connect`.

3. **Start Chatting:**
   Type your questions or queries in the chat box to receive insights from your database. The app will automatically generate and execute the SQL required to answer your questions.

## Code Explanation

### Key Modules

#### 1. Database Connection

```python
def init_database(user: str, password: str, host: str, port: str, database: str):
    # Connects to MariaDB and returns the connection and cursor.
```

This function establishes a secure connection to the MariaDB database. If the connection fails, it returns `None`.

#### 2. SQL Query Chain

```python
def get_sqlChain(conn, cursor):
    # Creates a dynamic SQL query template based on the database schema.
```

The `get_sqlChain` function dynamically generates SQL queries. It utilizes `ChatPromptTemplate` and `ChatGroq` to create and execute a pipeline that interprets natural language and generates SQL queries accordingly.

#### 3. Schema Extraction

```python
def get_schema_from_db(cursor):
    # Retrieves the database schema to inform the SQL query generation process.
```

This function retrieves tables and columns from the database schema to provide structure information for generating appropriate SQL queries.

#### 4. Response Generation

```python
def get_response(user_query, conn, cursor, chat_history):
    # Generates an SQL query, executes it, and formats the results into a response.
```

This function takes the user's question and conversation history, generates the necessary SQL query, executes it, and returns the result in a natural language format.

### Streamlit Interface

The app uses Streamlit for UI, setting up a chat interface where users can interact with the database through questions and receive responses in real-time.

## Flow Diagram 
![image](https://github.com/user-attachments/assets/efc5538a-aa88-452b-8f27-03d37e53bbb7)

## Contributions
Feel free to open issues or submit pull requests to improve the application.


