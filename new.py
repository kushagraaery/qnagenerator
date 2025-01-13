import openai
import streamlit as st
import pandas as pd
from io import BytesIO
import os
from dotenv import load_dotenv
import base64
import requests
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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
        .table-container {
            margin: 20px 0;
        }
        .table-container .stDataFrame {
            border: 1px solid #ddd;
            border-radius: 5px;
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
st.write("🔬 This Q&A generator allows users to fetch answers to predefined queries about pharmaceutical societies by entering the society name in the text box. It uses OpenAI to generate answers specific to the entered society and displays them in a tabular format. Users can download this report as an Excel file or as a CSV file. It updates the data automatically every Monday at 10 AM IST.")

# Define all available society options
all_societies = [
    "FLASCO (Florida Society of Clinical Oncology)", "GASCO (Georgia Society of Clinical Oncology)", "IOS (Indiana Oncology Society)", "IOWA Oncology Society", "MOASC (Medical Oncology Association of Southern California)"
]

# Define questions
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

# Load data from GitHub
existing_data, sha = fetch_excel_from_github()
if existing_data is None:
    existing_data = pd.DataFrame()

# Initialize session state to track dropdown options
if "available_societies" not in st.session_state:
    st.session_state.available_societies = all_societies.copy()

if "report_data" not in st.session_state:
    st.session_state.report_data = pd.DataFrame(columns=existing_data.columns if not existing_data.empty else ["Society Name"])

# Dropdown menu to select a society
selected_society = st.selectbox("Select a Society", st.session_state.available_societies, key="dropdown")

# Column aliases
def alias_columns(df):
    column_aliases = {
        "Society Name": "Society Name",
        "What is the membership count for society_name? Respond with one word (number) only. That should just be an integer nothing like approx or members just a number.": "Membership Count",
        "Does society_name encompasses community sites? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.": "Community Sites",
        "Is society_name influential on state or local policy? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.": "Policy Influence",
        "Does society_name provide engagement opportunity with leadership? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.": "Leadership Engagement",
        "Does society_name provide support for clinical trial recruitment? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.": "Clinical Trial Support",
        "Does society_name provide engagement opportunity with payors? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.": "Payor Engagement",
        "Does society_name include area experts on its board? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.": "Board Experts",
        "Is society_name involved in therapeutic research collaborations? Respond one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.": "Therapeutic Research",
        "Does society_name include top therapeutic area experts on its board? Respond with one word ('yes' or 'no') only plus provide a justification for the answer also after a comma.": "Top Experts",
        "Name the Region where the society_name is from? Just name the Region in word for the answer.": "Region"
    }
    return df.rename(columns=column_aliases)

# Fetch and display data for the selected society
def display_selected_society(selected):
    if selected:

        # Check if the selected society is already in the GitHub file
        if existing_data is not None and not existing_data.empty:
            society_data = existing_data[existing_data["Society Name"] == selected]
            if not society_data.empty:
                st.session_state.report_data = pd.concat([st.session_state.report_data, society_data], ignore_index=True)
                aliased_data = alias_columns(society_data)  # Apply column aliasing here
                st.dataframe(aliased_data)
            else:
                st.warning(f"No existing data found for {selected}.")

# Trigger the display of the selected society
display_selected_society(selected_society)

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

# Function to fetch data for all societies
def fetch_all_societies_data():
    report_data = pd.DataFrame(columns=[
        "Society Name",
        *questions
    ])

    for society in all_societies:
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

        report_data = pd.concat([report_data, pd.DataFrame([society_data])], ignore_index=True)
    

    # Fetch the existing data and SHA from GitHub
    df, sha = fetch_excel_from_github()
    if df is not None and sha is not None:
        # Replace the entire data with the new report_data
        update_report_data(report_data, sha)
    else:
        st.error("Failed to fetch existing data from GitHub.")

def update_report_data(report_data, sha):
    if report_data is not None and sha is not None:
        # Fetch the existing data from GitHub
        df, _ = fetch_excel_from_github()
        if df is not None:
            # Iterate through the new report data
            for _, row in report_data.iterrows():
                society_name = row["Society Name"]
                new_membership_count = row.get(
                    "What is the membership count for society_name? Respond with one word (number) only. That should just be an integer nothing like approx or members just a number.",
                    None
                )

                # Ensure the new membership count is a valid integer
                try:
                    new_membership_count = int(new_membership_count)
                except (ValueError, TypeError):
                    st.warning(f"Invalid membership count for {society_name}, skipping update.")
                    continue  # Skip this entry if the membership count is invalid

                # Check if the society exists in the existing data
                if society_name in df["Society Name"].values:
                    # Update the existing row directly
                    index = df[df["Society Name"] == society_name].index[0]
                    df.loc[index, 
                        "What is the membership count for society_name? Respond with one word (number) only. That should just be an integer nothing like approx or members just a number."
                    ] = new_membership_count
                else:
                    # Append the new row if the society doesn't exist
                    new_row = row.to_dict()
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            # Upload the updated DataFrame back to GitHub
            update_excel_in_github(df, sha)
        else:
            st.error("Failed to fetch the existing data from GitHub.")
    else:
        st.error("No report data or SHA provided for update.")

# Function to convert dataframe to Excel
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

# Button to fetch the existing Excel file
if st.button("View Data"):
    df, sha = fetch_excel_from_github()
    if df is not None:
        aliased_df = alias_columns(df)
        st.success("Data fetched successfully!")
        st.write("Current data with aliased columns:")
        st.dataframe(aliased_df)

        # Add download button for the Excel file
        excel_data = convert_df_to_excel(aliased_df)
        st.download_button(
            label="Download as Excel",
            data=excel_data,
            file_name="data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def send_email(smtp_server, smtp_port, sender_email, sender_password, receiver_email, subject, html_content):
    # Create the email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    # Choose whether to use SSL or TLS
    try:
        if smtp_port == 465:  # Use SSL
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(sender_email, sender_password)
                server.send_message(msg)
        elif smtp_port == 587:  # Use TLS
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(sender_email, sender_password)
                server.send_message(msg)
        return "Email sent successfully!"
    except Exception as e:
        return f"Failed to send email: {e}"

# HTML Table Conversion (for email body)
def dataframe_to_html(df):
    return df.to_html(index=False, border=1, classes="dataframe", justify="center")

# Collect email details from user input
receiver_email = "chouran1@gene.com"
email_subject = "Consolidated Pharma Society Report"

# Set Gmail SMTP server settings
smtp_server = "smtp.gmail.com"  # Gmail SMTP server
smtp_port = 587  # Choose SSL or TLS

# Set your sender email here (e.g., your Gmail)
sender_email = "johnwickcrayons@gmail.com"
sender_password = "afpt eoyt asaq qzjh"

# Send email if button clicked
def update_dashboard():
    if receiver_email and email_subject and sender_email and sender_password:
        df, sha = fetch_excel_from_github()
        html_table = dataframe_to_html(df)
        email_body = f"""
        <html>
        <head>
            <style>
                .dataframe {{
                    font-family: Arial, sans-serif;
                    border-collapse: collapse;
                    width: 100%;
                }}
                .dataframe td, .dataframe th {{
                    border: 1px solid #ddd;
                    padding: 8px;
                }}
                .dataframe tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}
                .dataframe th {{
                    padding-top: 12px;
                    padding-bottom: 12px;
                    text-align: left;
                    background-color: #4CAF50;
                    color: white;
                }}
            </style>
        </head>
        <body>
            <p>Dear Recipient,</p>
            <p>Find the attached consolidated report below:</p>
            {html_table}
            <p>Best regards,<br>Pharma Society Insights Team</p>
        </body>
        </html>
        """
        status = send_email(smtp_server, smtp_port, sender_email, sender_password, receiver_email, email_subject, email_body)
        # Display success or error message
        if "successfully" in status:
            st.success("Successfully Updated Dashboard!")
        else:
            st.error("Error while Updating Dashboard!")

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

# This function will run the job without the lock
def scheduled_job():
    print("Weekly data fetch initiated...")
    fetch_all_societies_data()  # Call your data fetch function
    print("Weekly data fetch completed!")
    update_dashboard()
    print("Dashboard Updated!")

# Function to start the scheduler
def start_scheduler():
    # Create the scheduler and add the job
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_job, 'cron', day_of_week='mon', hour=13, minute=7, timezone="Asia/Kolkata")
    # Start the scheduler
    scheduler.start()

# Start the scheduler in a separate thread
if __name__ == "__main__":
    threading.Thread(target=start_scheduler, daemon=True).start()

st.write("updated 3")
