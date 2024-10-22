import streamlit as st
import openai
import pdfplumber
from docx import Document
import pandas as pd
import requests

# Set your OpenAI API key here (replace with environment variables in production)
openai.api_key = 'sk-GG-7tTWL9Omh8bpbp4PHnEeIiugnYnWxOfOoV20iHGT3BlbkFJ-hkJetHOyh6OCTFuf1FJ10hWSW6_jdeVYLvUCkWvEA'

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

# Function to interact with GPT-3.5-turbo to dynamically extract information
def extract_dynamic_info_from_document(document_text, dynamic_query):
    response = openai.ChatCompletion.create(
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
        max_tokens=1500,
        temperature=0.2
    )
    return response['choices'][0]['message']['content'].strip()

# Load the OEDI dataset for county ordinances
@st.cache_data
def load_oedi_data():
    return pd.read_csv(r'C:\Users\SundeepYalamanchili\Documents\Ordinance\Solar Ordinance.csv')

# Load the Municode dataset (separate from OEDI)
@st.cache_data
def load_municode_data():
    return pd.read_csv(r'C:\Users\SundeepYalamanchili\Documents\Ordinance\municode.csv')

# Load the ALP dataset (states, counties, and their URLs)
@st.cache_data
def load_alp_data():
    return pd.read_csv(r'C:\Users\SundeepYalamanchili\Documents\Ordinance\alp_links.csv')

# Function to convert a name to the proper URL format (lowercase and replace spaces with underscores)
def format_name_for_url(name):
    return name.strip().lower().replace(" ", "_")

# Function to construct the Municode URL for the selected state and county
def construct_county_url(state_id, county_name):
    formatted_county = format_name_for_url(county_name)
    return f"https://library.municode.com/{state_id}/{formatted_county}"

# Function to check if the county exists on Municode
def county_exists_on_municode(state_id, county_name):
    county_url = construct_county_url(state_id, county_name)
    try:
        response = requests.get(county_url)
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        return False

# Streamlit UI
st.title("Solar Ordinance Processor and Search")

# --- File Upload Section for Ordinance Document Processing ---
st.header("Upload Your Ordinance Document")
uploaded_file = st.file_uploader("Upload a PDF or DOCX ordinance document", type=["pdf", "docx"])

if uploaded_file is not None:
    # Extract text based on file type
    file_type = uploaded_file.name.split('.')[-1].lower()
    
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
            extracted_info = extract_dynamic_info_from_document(ordinance_text, dynamic_query)
            st.subheader(f"Extracted Information for: {dynamic_query}")
            st.write(extracted_info)

            # Store the extracted information in the session state for later use
            st.session_state['extracted_info'] = extracted_info
    else:
        # Notify the user if no text was extracted
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
            # Only display relevant fields (without 'Feature Type', 'Value', 'Value Type')
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

    # Select state
    selected_state_municode = st.selectbox(
        "Select a State (Municode)",
        data_municode['State Name'].unique(),  # Use the exact format from the dataset
        index=list(data_municode['State Name'].unique()).index(st.session_state['selected_state_municode'])
        if st.session_state['selected_state_municode'] else 0
    )

    # If the selected state changes, reset the selected county
    if selected_state_municode != st.session_state['selected_state_municode']:
        st.session_state['selected_county_municode'] = None

    # Update session state for state
    st.session_state['selected_state_municode'] = selected_state_municode

    # Filter counties based on the selected state
    filtered_counties_municode = data_municode[data_municode['State Name'] == selected_state_municode]['County'].dropna().unique()

    # Select county
    selected_county_municode = st.selectbox(
        "Select a County",
        filtered_counties_municode,
        index=list(filtered_counties_municode).index(st.session_state['selected_county_municode'])
        if st.session_state['selected_county_municode'] else 0
    )

    # Update session state for county
    st.session_state['selected_county_municode'] = selected_county_municode

    # Check if the selected county exists on Municode
    if st.button("Check Availability and Show Page"):
        if county_exists_on_municode(st.session_state['selected_state_municode'].lower(), st.session_state['selected_county_municode'].lower()):
            county_url = construct_county_url(st.session_state['selected_state_municode'].lower(), st.session_state['selected_county_municode'].lower())
            st.write(f"Displaying the page for: {county_url}")
            
            # Display the county page in an iframe
            st.components.v1.iframe(county_url, height=600, scrolling=True)
        else:
            st.write(f"Selected county '{st.session_state['selected_county_municode']}' is not available on Municode.")

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
        # Fetch the URL from the dataset
        alp_url = county_data_alp.iloc[0]['URL']

        # Debugging: Log the URL to see if it's being fetched correctly
        st.write(f"Fetched URL: {alp_url}")

        # Display the ALP ordinance
        st.subheader(f"ALP Ordinance for {selected_county_alp}, {selected_state_alp}")
        
        # Display the link as a clickable hyperlink
        st.markdown(f"Visit the ordinance page: [Click here]({alp_url})", unsafe_allow_html=True)
        
        # Optionally, embed the page in an iframe
        st.components.v1.iframe(alp_url, height=600, scrolling=True)
    else:
        st.write(f"No ALP ordinances found for {selected_county_alp}, {selected_state_alp}.")
