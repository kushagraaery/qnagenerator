import openai
import streamlit as st
import pandas as pd
from io import BytesIO
import os
from dotenv import load_dotenv
import base64
import requests
import json

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Streamlit UI Enhancements
st.set_page_config(page_title="Pharma Society QnA Report Generator", page_icon="💊")

# Inline CSS for styling
st.markdown("""
    <style>
        /* General app styles */
        body {
            background-color: #f9f9f9;
            font-family: "Arial", sans-serif;
        }
        .main-header {
            font-size: 3rem;
            color: #FFA500;
            text-align: center;
            margin-bottom: 1rem;
            animation: fadeIn 6s;
        }
        .prompt-buttons button {
            background-color: #007bff;
            color: white;
            border: none;
            font-size: 1rem;
            padding: 10px 15px;
            border-radius: 5px;
            margin: 5px;
            cursor: pointer;
            transition: background-color 0.3s, transform 0.3s;
        }
        .prompt-buttons button:hover {
            background-color: #0056b3;
            transform: scale(1.05);
        }
        .table-container {
            margin: 20px 0;
        }
        .table-container .stDataFrame {
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .download-btn {
            display: inline-block;
            background-color: #28a745;
            color: white;
            padding: 10px 20px;
            font-size: 1rem;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 10px;
            transition: background-color 0.3s, transform 0.3s;
        }
        .download-btn:hover {
            background-color: #218838;
            transform: scale(1.05);
        }
        .fadeIn {
            animation: fadeIn 2s;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    </style>
""", unsafe_allow_html=True)

# Pharma Society Q&A Generator Section
st.markdown('<div class="main-header">💊 Pharma Society QnA Report Generator</div>', unsafe_allow_html=True)
st.write("🔬 This Q&A generator allows users to fetch answers to predefined queries about pharmaceutical societies by entering the society name in the text box. It uses OpenAI to generate answers specific to the entered society and displays them in a tabular format. Users can download this report as an Excel file.")

# Step 1: Initialize session state to track selected societies and report data
if "selected_societies" not in st.session_state:
    st.session_state.selected_societies = []
if "report_data" not in st.session_state:
    st.session_state.report_data = pd.DataFrame(columns=[
        "Society Name",
        "What is the membership count for society_name? Respond with one word (number) only. That should just be an integer nothing like approx or members just a number.",
        "Does society_name encompasses community sites? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
        "Is society_name influential on state or local policy? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
        "Does society_name provide engagement opportunity with leadership? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
        "Does society_name provide support for clinical trial recruitment? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
        "Does society_name provide engagement opportunity with payors? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
        "Does society_name include area experts on its board? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
        "Is society_name involved in therapeutic research collaborations? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
        "Does society_name include top therapeutic area experts on its board? Respond with one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
        "Name the Region where the society_name is from? Just name the Region in word for the answer."
    ])

# Define all available society options
all_societies = ["FLASCO (Florida Society of Clinical Oncology)", "GASCO (Georgia Society of Clinical Oncology)", " IOS (Indiana Oncology Society)", "IOWA Oncology Society", "MOASC (Medical Oncology Association of Southern California)"]

# Step 2: Filter dropdown options to exclude already selected societies
available_societies = [society for society in all_societies if society not in st.session_state.selected_societies]
society_name = st.selectbox("Select the Pharmaceutical Society Name:", [""] + available_societies)

# Define updated pharma-specific questions for the society
questions = [
    "What is the membership count for society_name? Respond with one word (number) only. That should just be an integer nothing like approx or members just a number.",
    "Does society_name encompasses community sites? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
    "Is society_name influential on state or local policy? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
    "Does society_name provide engagement opportunity with leadership? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
    "Does society_name provide support for clinical trial recruitment? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
    "Does society_name provide engagement opportunity with payors? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
    "Does society_name include area experts on its board? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
    "Is society_name involved in therapeutic research collaborations? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
    "Does society_name include top therapeutic area experts on its board? Respond with one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.",
    "Name the Region where the society_name is from? Just name the Region in word for the answer."
]

# Step 3: Generate the report only if a new society name is selected
if society_name and society_name not in st.session_state.selected_societies:
    st.session_state.selected_societies.append(society_name)

    # Prepare a list to store the answers for the selected society
    society_data = {"Society Name": society_name}
    for question in questions:
        society_data[question] = ""

    # Replace the placeholder in questions with the selected society name
    modified_questions = [question.replace("society_name", society_name) for question in questions]
    print(modified_questions)
    # Fetch data from OpenAI API for each modified question
    with st.spinner("Retrieving data..."):
        for i, question in enumerate(modified_questions):
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": question}]
                )
                answer = response["choices"][0]["message"]["content"].strip()
                society_data[questions[i]] = answer  # Add answer to corresponding column
                print(answer)
            except Exception as e:
                st.error(f"Error with '{question}': {e}")
                society_data[questions[i]] = "Error"

    # Append new society data to the report
    st.session_state.report_data = pd.concat([st.session_state.report_data, pd.DataFrame([society_data])], ignore_index=True)

# Add a caching mechanism to fetch consistent answers for societies
def fetch_all_societies():
    with st.spinner("Retrieving data..."):
        for society in available_societies:
            if society not in st.session_state.selected_societies:
                st.session_state.selected_societies.append(society)

                # Check if the society already exists in session state cache
                if "society_cache" not in st.session_state:
                    st.session_state.society_cache = {}

                # If society data is not cached, fetch it from OpenAI
                if society not in st.session_state.society_cache:
                    society_data = {"Society Name": society}
                    modified_questions = [q.replace("society_name", society) for q in questions]

                    for i, question in enumerate(modified_questions):
                        try:
                            response = openai.ChatCompletion.create(
                                model="gpt-3.5-turbo",
                                messages=[{"role": "user", "content": question}]
                            )
                            answer = response["choices"][0]["message"]["content"].strip()
                            society_data[questions[i]] = answer
                        except Exception as e:
                            st.error(f"Error with '{question}': {e}")
                            society_data[questions[i]] = "Error"

                    # Cache the society data
                    st.session_state.society_cache[society] = society_data
                else:
                    # Use cached data
                    society_data = st.session_state.society_cache[society]

                # Append the society data to the report
                st.session_state.report_data = pd.concat(
                    [st.session_state.report_data, pd.DataFrame([society_data])],
                    ignore_index=True
                )

# Place the button above the download button
if st.button("Retrieve New Data"):
    fetch_all_societies()

# Display the report and provide the download button if data exists
if not st.session_state.report_data.empty:
    st.write("Consolidated Tabular Report:")
    st.dataframe(st.session_state.report_data)

    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Consolidated Report")
        return output.getvalue()

    excel_data = to_excel(st.session_state.report_data)

    st.download_button(
        label="Download Consolidated Report",
        data=excel_data,
        file_name="Consolidated_Pharma_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Add your GitHub token in the .env file
GITHUB_REPO = "kushagraaery/qnagenerator"  # Replace with your GitHub repo
FILE_PATH = "Pharma_Society_Report.xlsx"  # Path to the Excel file in the repo

# GitHub API URL
BASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"

# Helper function to fetch Excel file from GitHub
def fetch_excel_from_github():
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(BASE_URL, headers=headers)
    if response.status_code == 200:
        content = response.json()
        file_data = base64.b64decode(content["content"])
        df = pd.read_excel(BytesIO(file_data))
        sha = content["sha"]  # Required for updating the file
        return df, sha
    else:
        st.error("Failed to fetch the Excel file from GitHub.")
        return None, None

# Helper function to update Excel file in GitHub
def update_excel_in_github(df, sha):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    # Convert DataFrame to binary Excel content
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    file_content = output.getvalue()
    # Prepare API payload
    payload = {
        "message": "Updated Excel file via Streamlit",
        "content": base64.b64encode(file_content).decode("utf-8"),
        "sha": sha
    }
    response = requests.put(BASE_URL, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        st.success("Data updated successfully!")
    else:
        st.error(f"Failed to update the data: {response.text}")

# Initialize session state for report data
if "report_data" not in st.session_state:
    st.session_state.report_data = pd.DataFrame(columns=["Society Name", "Question", "Answer"])

# Button to fetch the existing Excel file
if st.button("View Data"):
    df, sha = fetch_excel_from_github()
    if df is not None:
        st.session_state.report_data = df
        st.success("Data fetched successfully!")
        st.write("Current data:")
        st.dataframe(df)

# Button to update Excel file in GitHub
if st.button("Update Report Data"):
    if "report_data" in st.session_state:
        report_data = st.session_state.report_data
        
        # Fetch the existing data and SHA from GitHub
        df, sha = fetch_excel_from_github()
        if df is not None and sha is not None:
            # Iterate through the societies in the current session state data
            for index, row in report_data.iterrows():
                society_name = row["Society Name"]
                new_membership_count = row.get(
                    "What is the membership count for society_name? Respond with one word (number) only. That should just be an integer nothing like approx or members just a number.",
                    None
                )
                
                # Ensure the count is a valid number
                try:
                    new_membership_count = int(new_membership_count)
                except (ValueError, TypeError):
                    continue  # Skip if not a valid integer
                
                # Check if the society exists in the fetched Excel data
                if society_name in df["Society Name"].values:
                    existing_row = df[df["Society Name"] == society_name].iloc[0]
                    
                    existing_membership_count = existing_row[
                        "What is the membership count for society_name? Respond with one word (number) only. That should just be an integer nothing like approx or members just a number."
                    ]
                    
                    try:
                        existing_membership_count = int(existing_membership_count)
                        # Calculate the average of the existing and new counts
                        averaged_count = (existing_membership_count + new_membership_count) // 2
                    except (ValueError, TypeError):
                        # If the existing value is not a valid number, use the new count
                        averaged_count = new_membership_count

                    # Update the membership count in the DataFrame
                    df.loc[df["Society Name"] == society_name, "What is the membership count for society_name? Respond with one word (number) only. That should just be an integer nothing like approx or members just a number."] = averaged_count
                else:
                    # If the society is not in the Excel file, append it
                    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

            # Update the Excel file in GitHub
            update_excel_in_github(df, sha)
        else:
            st.error("Failed to fetch data from GitHub.")
    else:
        st.error("No report data found to update.")

# Chatbot 2.0 Section with Enhanced Styling and Animations
st.markdown('<div class="main-header">🤖 Chatbot 2.0 - Fine-Tuned on Report Data</div>', unsafe_allow_html=True)
st.markdown("📋 This chatbot uses OpenAI and the **consolidated report** data to answer your queries.")

# Custom CSS for chatbot styling and animations
st.markdown("""
    <style>
        .chat-container {
            border: 2px solid #007bff;
            border-radius: 10px;
            padding: 15px;
            background-color: #f8f9fa;
            margin-bottom: 20px;
        }
        .chat-container h3 {
            color: #007bff;
            margin-bottom: 10px;
        }
        .user-message, .assistant-message {
            display: flex;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        .user-message {
            animation: slideInRight 0.5s;
        }
        .assistant-message {
            animation: slideInLeft 0.5s;
        }
        .chat-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin-right: 10px;
            background-size: cover;
        }
        .user-avatar {
            background-image: url('https://via.placeholder.com/40/007bff/ffffff?text=U');
        }
        .assistant-avatar {
            background-image: url('https://via.placeholder.com/40/28a745/ffffff?text=A');
        }
        .chat-bubble {
            max-width: 75%;
            padding: 10px 15px;
            border-radius: 15px;
            font-size: 0.95rem;
            box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.1);
        }
        .user-message .chat-bubble {
            background-color: #007bff;
            color: white;
            border-top-left-radius: 0;
        }
        .assistant-message .chat-bubble {
            background-color: #e9ecef;
            color: #212529;
            border-top-right-radius: 0;
        }
        .fadeIn {
            animation: fadeIn 0.8s ease-in-out;
        }
        @keyframes slideInRight {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideInLeft {
            from { transform: translateX(-100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for Chatbot 2.0 messages
if "messages_2" not in st.session_state:
    st.session_state["messages_2"] = [
        {"role": "assistant", "content": "I am here to answer questions based on your consolidated report. How can I help you?"}
    ]

# Chatbot 2.0 input box
chat_input_2 = st.chat_input("Ask a question about the consolidated report...")

# Format the report data as a context for OpenAI
def format_report_for_context(df):
    if df.empty:
        return "No report data is currently available."
    context = "Here is the consolidated report data:\n"
    for _, row in df.iterrows():
        context += f"Society Name: {row['Society Name']}\n"
        for col in df.columns[1:]:  # Skip 'Society Name'
            context += f"  {col}: {row[col]}\n"
        context += "\n"
    return context.strip()

# Generate a response from OpenAI based on the report and user query
def generate_openai_response(query, report_context):
    try:
        # Construct a dynamic prompt
        prompt = f"""
         You are an AI assistant fine-tuned to answer questions based on a pharmaceutical society consolidated report. 
         Use the following report data to answer user queries accurately if the information exists in the report.
         If the query cannot be answered using the report, respond using your general knowledge i.e. using chat-gpt model:
        
        {report_context}
        
        User's question: {query}
        
        Respond concisely using the data provided.
        """
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            #   model="gpt-4",
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}]
        )
        return response.choices[0]["message"]["content"].strip()
    except Exception as e:
        return f"Error generating response: {e}"

# Predefined Prompt Buttons in a grid
st.markdown('<div class="prompt-buttons">', unsafe_allow_html=True)
cols = st.columns(3)

with cols[0]:
    if st.button("List down all the societies inside the Report."):
        chat_input_2 = "List down all the societies inside the Report only if there is report data."
with cols[1]:
    if st.button("Which Society do you think is the best out of all and why?"):
        chat_input_2 = "Which Society do you think is the best out of all and why only if there is report data?"
with cols[2]:
    if st.button("Tell me the society names with highest and lowest count of membership."):
        chat_input_2 = "Tell me the society names with highest and lowest count of membership only if there is report data."
st.markdown('</div>', unsafe_allow_html=True)

# Process Chatbot 2.0 input
if chat_input_2:
    st.session_state["messages_2"].append({"role": "user", "content": chat_input_2})

    # Specify the path to your Excel file
    df, sha = fetch_excel_from_github()

    # Prepare report data as context
    report_context = format_report_for_context(df)

    # Generate a response using OpenAI
    with st.spinner("Generating response..."):
        bot_reply_2 = generate_openai_response(chat_input_2, report_context)

    st.session_state["messages_2"].append({"role": "assistant", "content": bot_reply_2})

# Display Chatbot 2.0 conversation with new styling
for msg in st.session_state["messages_2"]:
    if msg["role"] == "user":
        st.markdown(
            f"""
            <div class="user-message">
                <div class="chat-avatar user-avatar"></div>
                <div class="chat-bubble">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True
        )
    elif msg["role"] == "assistant":
        st.markdown(
            f"""
            <div class="assistant-message">
                <div class="chat-avatar assistant-avatar"></div>
                <div class="chat-bubble">{msg["content"]}</div>
            </div>
            """, unsafe_allow_html=True
        )
st.markdown('</div>', unsafe_allow_html=True)

# Header section
st.markdown('<div class="main-header">💬 Pharma Insights Chatbot </div>', unsafe_allow_html=True)
st.markdown('💡 This app features a chatbot powered by OpenAI for answering society-related queries.', unsafe_allow_html=True)

# Predefined Prompt Buttons in a grid
st.markdown('<div class="prompt-buttons">', unsafe_allow_html=True)
cols = st.columns(3)

prompt = None

with cols[0]:
    if st.button("What are the top 10 oncology societies in California actively supporting clinical trials and research initiatives?"):
        prompt = "What are the top 10 oncology societies in California actively supporting clinical trials and research initiatives?"
with cols[1]:
    if st.button("Which Oncology Society in the World has the largest membership network and reach?"):
        prompt = "Which Oncology Society in the World has the largest membership network and reach?"
with cols[2]:
    if st.button("Which Oncology Societies in California collaborate with pharmaceutical companies for drug development initiatives?"):
        prompt = "Which Oncology Societies in California collaborate with pharmaceutical companies for drug development initiatives?"

# Add additional buttons in another row
cols = st.columns(3)
with cols[0]:
    if st.button("List the Oncology Societies in California that offer leadership opportunities for healthcare professionals."):
        prompt = "List the Oncology Societies in California that offer leadership opportunities for healthcare professionals."
with cols[1]:
    if st.button("Which Oncology Societies in California are most active in influencing state healthcare policies?"):
        prompt = "Which Oncology Societies in California are most active in influencing state healthcare policies?"
with cols[2]:
    if st.button("Identify oncology societies in California that provide resources or support for community-based oncology practices."):
        prompt = "Identify oncology societies in California that provide resources or support for community-based oncology practices."
st.markdown('</div>', unsafe_allow_html=True)

# Chat Input Section
user_input = st.chat_input("Ask a question or select a prompt...")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I assist you today?"}]

# Append user input or prompt to chat history
if prompt or user_input:
    user_message = prompt if prompt else user_input
    st.session_state["messages"].append({"role": "user", "content": user_message})

    # Query OpenAI API with the current messages
    with st.spinner("Generating response..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=st.session_state["messages"]
            )
            bot_reply = response.choices[0]["message"]["content"]
            st.session_state["messages"].append({"role": "assistant", "content": bot_reply})
        except Exception as e:
            bot_reply = f"Error retrieving response: {e}"
            st.session_state["messages"].append({"role": "assistant", "content": bot_reply})

# Display chat history sequentially
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])
