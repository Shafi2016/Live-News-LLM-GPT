import streamlit as st
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import UnstructuredURLLoader
import requests
import traceback
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

# Custom CSS to expand the main content area and reduce white space
st.markdown("""
    <style>
        /* Increase the width of the main content and sidebar */
        .main {
            max-width: 100%; /* Increase this percentage to make the content area wider */
            margin: 0 auto;
            padding-left: 20px;
            padding-right: 20px;
        }
        .sidebar .element-container img {
            margin-left: auto;
            margin-right: auto;
            display: block;
        }
        .sidebar {
            width: 25%; /* Adjust the width of the sidebar */
        }
    </style>
""", unsafe_allow_html=True)

# Access API keys from Streamlit Secrets
openai_api_key = st.secrets["general"]["OPENAI_API_KEY"]
serpapi_api_key = st.secrets["general"]["SERPAPI_API_KEY"]

# Organize the sidebar with the logo and search settings
with st.sidebar:
    st.image("https://raw.githubusercontent.com/Shafi2016/Live-News-LLM-GPT/main/logo.PNG", width=250)  # Adjust the width as needed
    st.header("Search Settings")
    num_results = st.number_input("Number of Search Results", min_value=1, max_value=15, value=3)
    word_count = st.slider("Summary Word Count", min_value=100, max_value=300, value=100, step=10)

# Add a custom header for the main section
st.markdown("""
    <div style="background-color:#0077a8;padding:10px;border-radius:5px;width:100%;max-width:1200px;margin: 0 auto;">
        <h1 style="color:white;">SpotLight News</h1>
        <p style="color:white; font-size:18px; white-space: nowrap; text-align:center;">Spotlight the stories that matter with quick summaries and curated insights, delivered instantly.</p>
    </div>
""", unsafe_allow_html=True)

# Add input for search query, ensuring it aligns with the header
search_query = st.text_input("What news are you looking for today?", label_visibility="collapsed", key="search", help="Enter your search query here.")
st.markdown("<style>div.stTextInput > div > input {width: 100%; max-width: 1200px; margin: 0 auto;}</style>", unsafe_allow_html=True)


# Add a row of buttons
col1, col2, col3 = st.columns([1, 1, 1])

# Function to log errors
def log_error(e):
    st.error(f"Exception occurred: {str(e)}")
    st.error(traceback.format_exc())

# Function to convert relative dates to exact dates
def convert_relative_date(relative_date_str):
    today = datetime.today()
    
    if 'hour' in relative_date_str:
        hours_ago = int(relative_date_str.split()[0])
        exact_date = today - timedelta(hours=hours_ago)
    elif 'day' in relative_date_str:
        days_ago = int(relative_date_str.split()[0])
        exact_date = today - timedelta(days=days_ago)
    elif 'week' in relative_date_str:
        weeks_ago = int(relative_date_str.split()[0])
        exact_date = today - timedelta(weeks=weeks_ago)
    elif 'month' in relative_date_str:
        months_ago = int(relative_date_str.split()[0])
        exact_date = today - relativedelta(months=months_ago)
    elif 'year' in relative_date_str:
        years_ago = int(relative_date_str.split()[0])
        exact_date = today - relativedelta(years=years_ago)
    else:
        exact_date = None  # Return None if unable to parse
    
    return exact_date.strftime("%Y-%m-%d") if exact_date else None

# Function to perform a Google search query using SerpAPI
def search_query_serpapi(query, serpapi_api_key, num_results):
    try:
        params = {
            "engine": "google",
            "q": query,
            "num": num_results,
            "api_key": serpapi_api_key
        }
        response = requests.get("https://serpapi.com/search", params=params)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        log_error(e)
        return None

# If the 'Search' button is clicked
if col1.button("Search"):
    if not search_query.strip():
        st.error("Please provide the missing fields.")
    else:
        try:
            with st.spinner("Please wait..."):
                result_dict = search_query_serpapi(search_query, serpapi_api_key, num_results)
                if not result_dict or 'organic_results' not in result_dict:
                    st.error(f"No search results for: {search_query}.")
                else:
                    for i, item in zip(range(num_results), result_dict['organic_results']):
                        raw_date = item.get('date', 'No date available')
                        exact_date = convert_relative_date(raw_date)
                        display_date = f"{raw_date} ({exact_date})" if exact_date else raw_date
                        st.success(f"**Title:** {item['title']}\n\n**Link:** {item['link']}\n\n**Date:** {display_date}\n\n**Snippet:** {item.get('snippet', 'No snippet available')}")
        except Exception as e:
            log_error(e)

# If 'Search & Summarize' button is clicked
if col2.button("Search & Summarize"):
    if not search_query.strip():
        st.error("Please provide the missing fields.")
    else:
        try:
            with st.spinner("Please wait..."):
                result_dict = search_query_serpapi(search_query, serpapi_api_key, num_results)
                if not result_dict or 'organic_results' not in result_dict:
                    st.error(f"No search results for: {search_query}.")
                else:
                    for i, item in zip(range(num_results), result_dict['organic_results']):
                        try:
                            loader = UnstructuredURLLoader(
                                urls=[item['link']],
                                ssl_verify=False,
                                headers={
                                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
                                }
                            )
                            data = loader.load()
                            llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=openai_api_key)
                            prompt_template = PromptTemplate(template=f"Write a summary of the following in {word_count} words:\n\n{{text}}", input_variables=["text"])
                            chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt_template)
                            summary = chain.run(data)
                            raw_date = item.get('date', 'No date available')
                            exact_date = convert_relative_date(raw_date)
                            display_date = f"{raw_date} ({exact_date})" if exact_date else raw_date
                            st.success(f"**Title:** {item['title']}\n\n**Link:** {item['link']}\n\n**Date:** {display_date}\n\n**Summary:** {summary}")
                        except Exception as e:
                            st.error(f"Failed to summarize article: {item['title']}")
                            log_error(e)
        except Exception as e:
            log_error(e)

# If 'Search & Summarize All' button is clicked
if col3.button("Search & Summarize All"):
    if not search_query.strip():
        st.error("Please provide the missing fields.")
    else:
        try:
            with st.spinner("Please wait..."):
                result_dict = search_query_serpapi(search_query, serpapi_api_key, num_results)
                if not result_dict or 'organic_results' not in result_dict:
                    st.error(f"No search results for: {search_query}.")
                else:
                    combined_summary = ""
                    references = []
                    for i, item in zip(range(num_results), result_dict['organic_results']):
                        try:
                            loader = UnstructuredURLLoader(
                                urls=[item['link']],
                                ssl_verify=False,
                                headers={
                                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
                                }
                            )
                            data = loader.load()
                            llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=openai_api_key)
                            prompt_template = PromptTemplate(template=f"Write a summary of the following in {word_count} words:\n\n{{text}}", input_variables=["text"])
                            chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt_template)
                            summary = chain.run(data)
                            combined_summary += f"{summary}\n\n"
                            references.append(item['link'])
                        except Exception as e:
                            st.error(f"Failed to summarize article: {item['title']}")
                            log_error(e)

                    # Display the combined summary and references
                    st.markdown("### Combined Summary")
                    st.write(combined_summary)
                    st.markdown("### References")
                    for i, link in enumerate(references, 1):
                        st.write(f"{i}. [Link to article]({link})")
        except Exception as e:
            log_error(e)
