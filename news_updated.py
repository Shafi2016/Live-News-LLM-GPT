import streamlit as st
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import UnstructuredURLLoader
import requests
import traceback
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

# Streamlit app
st.subheader('Latest News...')

# Access API keys from Streamlit Secrets
openai_api_key = st.secrets["general"]["OPENAI_API_KEY"]
serpapi_api_key = st.secrets["general"]["SERPAPI_API_KEY"]

# st.write("OpenAI API Key:", openai_api_key)
# st.write("SerpAPI Key:", serpapi_api_key)
# Get the number of results, word count, and search query from the user
with st.sidebar:
    num_results = st.number_input("Number of Search Results", min_value=3, max_value=15)
    
    # Add a slider to control the word count for summaries
    word_count = st.slider("Summary Word Count", min_value=100, max_value=300, value=100, step=10)
   

search_query = st.text_input("Search Query", label_visibility="collapsed")
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
    # Validate inputs
    if not search_query.strip():
        st.error("Please provide the missing fields.")
    else:
        try:
            with st.spinner("Please wait..."):
                # Show the top X relevant news articles from the previous week using SerpAPI
                result_dict = search_query_serpapi(search_query, serpapi_api_key, num_results)

                if not result_dict or 'organic_results' not in result_dict:
                    st.error(f"No search results for: {search_query}.")
                else:
                    for i, item in zip(range(num_results), result_dict['organic_results']):
                        raw_date = item.get('date', 'No date available')
                        exact_date = convert_relative_date(raw_date)
                        if exact_date:
                            display_date = f"{raw_date} ({exact_date})"
                        else:
                            display_date = raw_date
                        st.success(f"Title: {item['title']}\n\nLink: {item['link']}\n\nDate: {display_date}\n\nSnippet: {item.get('snippet', 'No snippet available')}")
        except Exception as e:
            log_error(e)

# If 'Search & Summarize' button is clicked
if col2.button("Search & Summarize"):
    # Validate inputs
    if not search_query.strip():
        st.error("Please provide the missing fields.")
    else:
        try:
            with st.spinner("Please wait..."):
                # Show the top X relevant news articles from the previous week using SerpAPI
                result_dict = search_query_serpapi(search_query, serpapi_api_key, num_results)

                if not result_dict or 'organic_results' not in result_dict:
                    st.error(f"No search results for: {search_query}.")
                else:
                    # Load URL data from the top X news search results
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
                        except Exception as e:
                            st.error(f"Failed to load URL: {item['link']}")
                            log_error(e)
                            continue

                        # Initialize the ChatOpenAI module, load and run the summarize chain
                        llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=openai_api_key)
                        prompt_template = PromptTemplate(
                            template=f"Write a summary of the following in {word_count} words:\n\n{{text}}",
                            input_variables=["text"]
                        )
                        chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt_template)

                        try:
                            summary = chain.run(data)
                            raw_date = item.get('date', 'No date available')
                            exact_date = convert_relative_date(raw_date)
                            if exact_date:
                                display_date = f"{raw_date} ({exact_date})"
                            else:
                                display_date = raw_date
                            st.success(f"Title: {item['title']}\n\nLink: {item['link']}\n\nDate: {display_date}\n\nSummary: {summary}")
                        except Exception as e:
                            st.error(f"Failed to summarize article: {item['title']}")
                            log_error(e)
        except Exception as e:
            log_error(e)

# If 'Search & Summarize All' button is clicked
if col3.button("Search & Summarize All"):
    # Validate inputs
    if not search_query.strip():
        st.error("Please provide the missing fields.")
    else:
        try:
            with st.spinner("Please wait..."):
                # Show the top X relevant news articles from the previous week using SerpAPI
                result_dict = search_query_serpapi(search_query, serpapi_api_key, num_results)

                if not result_dict or 'organic_results' not in result_dict:
                    st.error(f"No search results for: {search_query}.")
                else:
                    # Collect all summaries and references
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
                        except Exception as e:
                            st.error(f"Failed to load URL: {item['link']}")
                            log_error(e)
                            continue

                        # Initialize the ChatOpenAI module, load and run the summarize chain
                        llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=openai_api_key)
                        prompt_template = PromptTemplate(
                            template=f"Write a summary of the following in {word_count} words:\n\n{{text}}",
                            input_variables=["text"]
                        )
                        chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt_template)

                        try:
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
