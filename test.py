import streamlit as st
import openai
import pdfplumber
from docx import Document
import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Debugging: Check if API key is loaded
if client.api_key:
    st.write("API Key loaded successfully.")
else:
    st.error("Error: API Key not loaded. Please check your .env file or set the key manually.")

# Function to extract text from PDF using pdfplumber
def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# Function to extract text from DOCX using python-docx
def extract_text_from_docx(file):
    doc = Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return "\n".join(full_text)

# Function to dynamically extract information with truncation logic
def extract_dynamic_info_from_document(document_text, dynamic_query):
    try:
        # Truncate document text to fit within token limits
        MAX_TEXT_LENGTH = 10000  # Leave room for query and response
        if len(document_text) > MAX_TEXT_LENGTH:
            document_text = document_text[:MAX_TEXT_LENGTH]

        logging.info(f"Extracting information for query: {dynamic_query}")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an assistant that dynamically extracts specific details from ordinance documents based on user input."
                },
                {
                    "role": "user",
                    "content": f"Based on the following document, please extract relevant information related to: {dynamic_query}.\n\nDocument:\n{document_text}"
                }
            ],
            max_tokens=1000,  # Adjust to fit within token limit
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error with OpenAI API request: {e}")
        st.error(f"Error with OpenAI API request: {e}")
        return ""

# Streamlit UI for document processing
st.header("Upload Your Ordinance Document")
uploaded_file = st.file_uploader("Upload a PDF or DOCX ordinance document", type=["pdf", "docx"])

if uploaded_file is not None:
    # Extract text based on file type
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    with st.spinner("Extracting document text..."):
        if file_type == 'pdf':
            ordinance_text = extract_text_from_pdf(uploaded_file)
        elif file_type == 'docx':
            ordinance_text = extract_text_from_docx(uploaded_file)
        else:
            st.error("Unsupported file format!")
            ordinance_text = ""

    if ordinance_text:
        # Display extracted text (optional)
        st.subheader("Extracted Text from Document")
        st.text_area("Document Text", ordinance_text, height=300)

        # Allow user to input a dynamic query for ordinance extraction
        dynamic_query = st.text_input("Enter the query you want to extract information for (e.g., Setbacks, Decommissioning, etc.)")

        if dynamic_query:
            # Extract relevant information based on dynamic query
            with st.spinner("Extracting information from the document..."):
                extracted_info = extract_dynamic_info_from_document(ordinance_text, dynamic_query)
            st.subheader(f"Extracted Information for: {dynamic_query}")
            st.write(extracted_info)

            # Store the extracted information in the session state for later use
            st.session_state['extracted_info'] = extracted_info
    else:
        st.warning("Text extraction failed. Please check the uploaded document.")
else:
    st.info("Please upload a PDF or DOCX ordinance document to proceed.")


# --- OEDI Dataset Ordinance Search Section ---
if 'active_section' not in st.session_state:
    st.session_state['active_section'] = None
if 'selected_state_oedi' not in st.session_state:
    st.session_state['selected_state_oedi'] = None
if 'selected_county_oedi' not in st.session_state:
    st.session_state['selected_county_oedi'] = None
if 'selected_state_municode' not in st.session_state:
    st.session_state['selected_state_municode'] = None
if 'selected_county_municode' not in st.session_state:
    st.session_state['selected_county_municode'] = None
if 'selected_state_alp' not in st.session_state:
    st.session_state['selected_state_alp'] = None
if 'selected_county_alp' not in st.session_state:
    st.session_state['selected_county_alp'] = None

if st.button("Check available County Ordinances from OEDI Dataset"):
    st.session_state['active_section'] = 'oedi'

if st.button("Check County Ordinances from Municode"):
    st.session_state['active_section'] = 'municode'

if st.button("Check County Ordinances from ALP"):
    st.session_state['active_section'] = 'alp'

# --- OEDI Section ---
if st.session_state['active_section'] == 'oedi':
    st.header("Search Solar Ordinances by State and County (OEDI Dataset)")

    # Load the OEDI dataset
    data_oedi = load_oedi_data()

    # Select state
    selected_state_oedi = st.selectbox(
        "Select a State",
        data_oedi['State'].unique(),
        index=list(data_oedi['State'].unique()).index(st.session_state['selected_state_oedi'])
        if st.session_state['selected_state_oedi'] else 0
    )

    # If the selected state changes, reset the selected county
    if selected_state_oedi != st.session_state['selected_state_oedi']:
        st.session_state['selected_county_oedi'] = None

    # Update session state for state
    st.session_state['selected_state_oedi'] = selected_state_oedi

    # Filter counties based on the selected state
    filtered_counties_oedi = data_oedi[data_oedi['State'] == selected_state_oedi]['County'].dropna().unique()

    # Select county
    selected_county_oedi = st.selectbox(
        "Select a County",
        filtered_counties_oedi,
        index=list(filtered_counties_oedi).index(st.session_state['selected_county_oedi'])
        if st.session_state['selected_county_oedi'] else 0
    )

    # Update session state for county
    st.session_state['selected_county_oedi'] = selected_county_oedi

    # Display ordinance data for the selected county
    county_data_oedi = data_oedi[
        (data_oedi['State'] == selected_state_oedi) & (data_oedi['County'] == selected_county_oedi)
    ]

    if not county_data_oedi.empty:
        st.subheader(f"Solar Ordinance for {selected_county_oedi}, {selected_state_oedi}")
        for _, row in county_data_oedi.iterrows():
            st.write(f"**Citation**: {row['Citation']}")
            st.write(f"**Comment**: {row['Comment']}")
            st.write(f"**Ordinance Year**: {row['Ordinance Year']}")
            st.write("---")
    else:
        st.write(f"No solar ordinances found for {selected_county_oedi}, {selected_state_oedi}.")




# --- Municode Section ---
elif st.session_state['active_section'] == 'municode':
    st.header("Check Available Ordinances from Municode")

    # Load Municode data
    data_municode = load_municode_data()

    # Ensure 'State' and 'County' columns exist in the dataset
    if 'State' not in data_municode.columns or 'County' not in data_municode.columns:
        st.error("The Municode dataset must have 'State' and 'County' columns.")
        st.stop()

    # Initialize session state variables if they do not exist
    if 'selected_state_municode' not in st.session_state:
        st.session_state['selected_state_municode'] = None
    if 'selected_county_municode' not in st.session_state:
        st.session_state['selected_county_municode'] = None

    # Get unique states
    states = sorted(data_municode['State'].dropna().unique())

    # Select state
    selected_state_municode = st.selectbox(
        "Select a State",
        states,
        index=states.index(st.session_state['selected_state_municode'])
        if st.session_state['selected_state_municode'] in states else 0
    )

    # Update session state for state
    st.session_state['selected_state_municode'] = selected_state_municode

    # Filter counties based on the selected state
    filtered_counties = sorted(data_municode[data_municode['State'] == selected_state_municode]['County'].dropna().unique())

    # Handle case where no counties are found
    if not filtered_counties:
        st.warning(f"No counties found for the state: {selected_state_municode}. Please select another state.")
        st.stop()

    # Select county
    selected_county_municode = st.selectbox(
        "Select a County",
        filtered_counties,
        index=filtered_counties.index(st.session_state['selected_county_municode'])
        if st.session_state['selected_county_municode'] in filtered_counties else 0
    )

    # Update session state for county
    st.session_state['selected_county_municode'] = selected_county_municode

    # Function to construct the Municode URL
    def construct_municode_url(state_name, county_name):
        state_short_name = state_name[:2].lower()  # Use the first two characters of the state name
        formatted_county = county_name.replace(" ", "_").lower()  # Replace spaces with underscores and convert to lowercase
        return f"https://library.municode.com/{state_short_name}/{formatted_county}"

    # Generate and display the link
    if st.button("Generate Link"):
        county_url = construct_municode_url(selected_state_municode, selected_county_municode)
        st.subheader(f"Municode Ordinance for {selected_county_municode}, {selected_state_municode}")
        st.markdown(f"Visit the ordinance page: [Click here]({county_url})", unsafe_allow_html=True)


# --- ALP Section ---
elif st.session_state['active_section'] == 'alp':
    st.header("Check Available Ordinances from American Legal Publishing")

    # Load ALP data
    data_alp = load_alp_data()

    # Select state
    selected_state_alp = st.selectbox(
        "Select a State (ALP)",
        data_alp['State'].unique(),
        index=list(data_alp['State'].unique()).index(st.session_state['selected_state_alp'])
        if st.session_state['selected_state_alp'] else 0
    )

    # If the selected state changes, reset the selected county
    if selected_state_alp != st.session_state['selected_state_alp']:
        st.session_state['selected_county_alp'] = None

    # Update session state for state
    st.session_state['selected_state_alp'] = selected_state_alp

    # Filter counties based on the selected state
    filtered_counties_alp = data_alp[data_alp['State'] == selected_state_alp]['County'].dropna().unique()

    # Select county
    selected_county_alp = st.selectbox(
        "Select a County",
        filtered_counties_alp,
        index=list(filtered_counties_alp).index(st.session_state['selected_county_alp'])
        if st.session_state['selected_county_alp'] else 0
    )

    # Update session state for county
    st.session_state['selected_county_alp'] = selected_county_alp

    # Filter the dataset for the selected state and county
    county_data_alp = data_alp[
        (data_alp['State'] == selected_state_alp) & (data_alp['County'] == selected_county_alp)
    ]

    if not county_data_alp.empty:
        alp_url = county_data_alp.iloc[0]['URL']
        st.write(f"Fetched URL: {alp_url}")
        st.subheader(f"ALP Ordinance for {selected_county_alp}, {selected_state_alp}")
        st.markdown(f"Visit the ordinance page: [Click here]({alp_url})", unsafe_allow_html=True)
        st.components.v1.iframe(alp_url, height=600, scrolling=True)
    else:
        st.write(f"No ALP ordinances found for {selected_county_alp}, {selected_state_alp}.")
