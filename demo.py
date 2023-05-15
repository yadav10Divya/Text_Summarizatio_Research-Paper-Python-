import streamlit as st
import pandas as pd

import PyPDF2
import cv2
import pyttsx3
from PIL import Image
import base64
import tempfile
import sqlite3
import hashlib
import pdfplumber
import re
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.tokenizers import Tokenizer

import nltk

nltk.download('punkt')

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False


# DB Management


conn = sqlite3.connect('data.db')
c = conn.cursor()


# DB  Functions


def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(name TEXT,email TEXT,mobile TEXT,username TEXT,password TEXT)')


def add_userdata(name, email, mobile, username, password):
    c.execute('INSERT INTO userstable(name,email,mobile,username,password) VALUES (?,?,?,?,?)',
              (name, email, mobile, username, password))
    conn.commit()


def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    return data


def view_all_users():
    c.execute('SELECT * FROM userstable')
    data = c.fetchall()
    return data


def pdf_info(read_pdf):
    pdf_info_dict = {}
    pdf_info = {}
    for key, value in read_pdf.metadata.items():
        pdf_info_dict[re.sub('/', "", key)] = value
        return pdf_info_dict



def summarize(text, per):
    import spacy
    from spacy.lang.en.stop_words import STOP_WORDS
    from string import punctuation
    from heapq import nlargest

    # check if input text is empty
    if not text:
        return ""

    nlp = spacy.load('en_core_web_sm')
    doc = nlp(text)
    tokens = [token.text for token in doc]
    word_frequencies = {}
    for word in doc:
        if word.text.lower() not in list(STOP_WORDS):
            if word.text.lower() not in punctuation:
                if word.text not in word_frequencies.keys():
                    word_frequencies[word.text] = 1
                else:
                    word_frequencies[word.text] += 1
    max_frequency = max(word_frequencies.values())
    for word in word_frequencies.keys():
        word_frequencies[word] = word_frequencies[word] / max_frequency
    sentence_tokens = [sent for sent in doc.sents]

    # check if there are sentences to summarize
    if not sentence_tokens:
        return ""

    sentence_scores = {}
    for sent in sentence_tokens:
        for word in sent:
            if word.text.lower() in word_frequencies.keys():
                if sent not in sentence_scores.keys():
                    sentence_scores[sent] = word_frequencies[word.text.lower()]
                else:
                    sentence_scores[sent] += word_frequencies[word.text.lower()]
    select_length = int(len(sentence_tokens) * per)
    summary = nlargest(select_length, sentence_scores, key=sentence_scores.get)
    final_summary = [word.text for word in summary]
    summary = ' '.join(final_summary)  # separate sentences with spaces
    return summary



def main():
    year = None


    st.title("Text Summarization")

    menu = ["Home", "Login", "SignUp"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Home":
        st.subheader("Home")

    elif choice == "Login":
        # st.subheader("Login Section")

        username = st.sidebar.text_input("User Name")
        password = st.sidebar.text_input("Password", type='password')
        if st.sidebar.checkbox("Login"):
            # if password == '12345':
            create_usertable()
            hashed_pswd = make_hashes(password)

            result = login_user(username, check_hashes(password, hashed_pswd))
            menu1 = ["By PDF", "By URL"]
            choice1 = st.sidebar.selectbox("Menu", menu1)

            if result:
                st.title("")

                if choice1 == "By PDF":
                    st.subheader("Upload an PDF")
                    uploaded_file = st.file_uploader("Upload Files", type=['pdf'])
                    # st.write(uploaded_file)
                    if uploaded_file is not None:
                        base64_pdf = base64.b64encode(uploaded_file.read()).decode('utf-8')
                        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="800" height="800" type="application/pdf"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)

                        from PyPDF2 import PdfReader
                        reader = PdfReader(uploaded_file)

                        text_combined = ""
                        for page in reader.pages:
                            text = page.extract_text()
                            if text:
                                text_combined += text + "\n"

                        # Find the index of the abstract keyword
                        abstract_index = None
                        for i, line in enumerate(text_combined.split("\n")):
                            if line.lower().startswith("abstract"):
                                abstract_index = i
                                break

                            if line.startswith("Abstract"):
                                abstract_index = i
                                break

                        # Extract the text above the abstract index
                        if abstract_index is not None:
                            title = " ".join(text_combined.split("\n")[:abstract_index])
                        else:
                            title = " ".join(text_combined.split("\n"))

                        # Check if the title is empty and search for lowercase "abstract" as well
                        if not title:
                            for i, line in enumerate(text_combined.split("\n")):
                                if line.lower().startswith("abstract"):
                                    abstract_index = i
                                    break

                            if abstract_index is not None:
                                title = " ".join(text_combined.split("\n")[:abstract_index])
                            else:
                                title = " ".join(text_combined.split("\n"))
                        length = (len(reader.pages))
                        x = 0  # Initialize x with a default value
                        #
                        # header_text = extract_header(uploaded_file)
                        #
                        # # Print the extracted header text
                        # st.write("Extracted Header Text:")
                        # st.write(header_text)

                        for i in range(length):
                            page = reader.pages[i]
                            text = page.extract_text()
                            # st.write(text)

                            if text.count("CONCLUSION") >= 1:
                                x = text.index("CONCLUSION")
                                break  # Exit the loop once "CONCLUSION" is found
                            elif text.count("Conclusion") >= 1:
                                x = text.index("Conclusion")
                                break  # Exit the loop once "Conclusion" is found

                            # if x == 0:
                            #     st.write(".")

                        if text.count("References") > 0:
                            r = text.index("References")
                        elif text.count("REFERENCES") > 0:
                            r = text.index("REFERENCES")
                        else:
                            r = None

                        y = text[x:r].strip()  # Remove leading and trailing spaces

                        y = re.sub(r'^(CONCLUSIONS?|Conclusion[s]?)', '', y).strip()


                        parser1 = PlaintextParser.from_string(y, Tokenizer("english"))
                        summarizer = LsaSummarizer()
                        csummary = summarizer(parser1.document, 2)  # summarize to one sentence
                        string1 = str(csummary)
                        simple_text = ''.join(e for e in string1 if e.isalnum() or e.isspace()).lower()[8:]



                        # for title
                        # page1 = reader.pages[0]
                        # text1 = page1.extract_text().split("\n")
                        #
                        # # Combine all lines from the start to the abstract
                        # start_index = 0
                        # abstract_index = 0
                        # for i, line in enumerate(text1):
                        #     if line.lower().startswith("abstract"):
                        #         abstract_index = i
                        #         break
                        #
                        # title = " ".join(text1[start_index:abstract_index])



                        # for year

                        first_page = reader.pages[0]
                        text = first_page.extract_text()

                        # Search for the publication year in the text
                        year = 2014
                        for word in text.split():
                            if word.isdigit() and len(word) == 4:
                                year = int(word)
                                break



                        st.subheader('My Table')

                        def load_data():
                            return pd.DataFrame(
                                {
                                    "Title": [title],
                                    "Publication year": [year],
                                    "Conclusion": [y],
                                    "Summarised Conclusion": [simple_text],

                                }
                            )

                        df = load_data()
                        st.table(df.style.set_properties(
                            **{'max-height': '300px', 'max-width': '100%', 'border-collapse': 'collapse',
                               'border': '2px solid #ccc'})
                                 .set_table_styles([{'selector': 'th', 'props': [('background-color', '#f2f2f2'),
                                                                                 ('border', '2px solid #ccc'),
                                                                                 ('font-weight', 'bold'),
                                                                                 ('font-size', '22px')]},
                                                    {'selector': 'td', 'props': [('border', '2px solid #ccc')]}])
                                 )

                        # conclusion in speech
                        def text_to_speech(text):
                            # Initialize the text-to-speech engine
                            engine = pyttsx3.init()

                            # Convert the text to speech
                            engine.say(text)
                            engine.runAndWait()

                        if st.button("Techniques in speech"):
                            text_to_speech(simple_text)



                elif choice1 == "By URL":
                    st.subheader("Enter an URL")
                    url = st.text_input("Enter url")
                    if st.checkbox("submit"):
                        st.subheader("Entered URL is:")
                        st.write(url)
                        from newspaper import Article

                        url = url
                        article = Article(url)
                        article.download()
                        article.parse()
                        article.text

                        summarize(article.text, 0.05)


            else:
                st.warning("Incorrect Username/Password")

    elif choice == "SignUp":
        st.subheader("Create New Account")
        new_name = st.text_input("Enter Name")
        new_email = st.text_input("Email")
        new_mobile = st.text_input("Mobile No")
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type='password')

        if st.button("Signup"):
            create_usertable()
            add_userdata(new_name, new_email, new_mobile, new_user, make_hashes(new_password))
            st.success("You have successfully created a valid Account")
            st.info("Go to Login Menu to login")


# elif choice == "Text To Speech":
# 	st.subheader("Text To Speech Conversion")
# 	new_text = st.text_input("Enter Text")
#
# 	if st.button("Text to speech"):
# 		text_speech = pyttsx3.init()
# 		text_speech.setProperty("rate", 150)
# 		text_speech.say(new_text)
# 		text_speech.runAndWait()


if __name__ == '__main__':
    main()
