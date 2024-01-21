
import streamlit as st


st.set_page_config(
        page_title="Recap Master",
        page_icon='favicon.ico', 
        layout="wide", 
    )

import base64

from bs4 import BeautifulSoup
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse
from textwrap import dedent
from pytube import YouTube
from deep_translator import GoogleTranslator
from gtts import gTTS


import transformers
from transformers import T5ForConditionalGeneration, T5Tokenizer


from gensim.summarization.summarizer import summarize

def gensim_summarize(text_content, percent):
    summary = summarize(text_content, ratio=(int(percent) / 100), split=False).replace("\n", " ")
    return summary

import nltk
from string import punctuation
from heapq import nlargest
nltk.download('punkt')
nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

def nltk_summarize(text_content, percent):
    tokens = word_tokenize(text_content)
    stop_words = stopwords.words('english')
    punctuation_items = punctuation + '\n'

    word_frequencies = {}
    for word in tokens:
        if word.lower() not in stop_words:
            if word.lower() not in punctuation_items:
                if word not in word_frequencies.keys():
                    word_frequencies[word] = 1
                else:
                    word_frequencies[word] += 1
    max_frequency = max(word_frequencies.values())

    for word in word_frequencies.keys():
        word_frequencies[word] = word_frequencies[word] / max_frequency
    sentence_token = sent_tokenize(text_content)
    sentence_scores = {}
    for sent in sentence_token:
        sentence = sent.split(" ")
        for word in sentence:
            if word.lower() in word_frequencies.keys():
                if sent not in sentence_scores.keys():
                    sentence_scores[sent] = word_frequencies[word.lower()]
                else:
                    sentence_scores[sent] += word_frequencies[word.lower()]

    select_length = int(len(sentence_token) * (int(percent) / 100))
    summary = nlargest(select_length, sentence_scores, key=sentence_scores.get)
    final_summary = [word for word in summary]
    summary = ' '.join(final_summary)
    return summary

import spacy
from spacy.lang.en.stop_words import STOP_WORDS
import en_core_web_sm
nlp = en_core_web_sm.load()
def spacy_summarize(text_content, percent):
    stop_words = list(STOP_WORDS)
    punctuation_items = punctuation + '\n'
    nlp = spacy.load('en_core_web_sm')

    nlp_object = nlp(text_content)
    word_frequencies = {}
    for word in nlp_object:
        if word.text.lower() not in stop_words:
            if word.text.lower() not in punctuation_items:
                if word.text not in word_frequencies.keys():
                    word_frequencies[word.text] = 1
                else:
                    word_frequencies[word.text] += 1
                    
    max_frequency = max(word_frequencies.values())
    for word in word_frequencies.keys():
        word_frequencies[word] = word_frequencies[word] / max_frequency
    sentence_token = [sentence for sentence in nlp_object.sents]
    sentence_scores = {}
    for sent in sentence_token:
        sentence = sent.text.split(" ")
        for word in sentence:
            if word.lower() in word_frequencies.keys():
                if sent not in sentence_scores.keys():
                    sentence_scores[sent] = word_frequencies[word.lower()]
                else:
                    sentence_scores[sent] += word_frequencies[word.lower()]

    select_length = int(len(sentence_token) * (int(percent) / 100))
    summary = nlargest(select_length, sentence_scores, key=sentence_scores.get)
    final_summary = [word.text for word in summary]
    summary = ' '.join(final_summary)
    return summary

import math
from nltk import sent_tokenize, word_tokenize, PorterStemmer
from nltk.corpus import stopwords

def _generate_summary(sentences, sentenceValue, threshold):
    sentence_count = 0
    summary = ''

    for sentence in sentences:
        if sentence[:15] in sentenceValue and sentenceValue[sentence[:15]] >= (threshold):
            summary += " " + sentence
            sentence_count += 1

    return summary

def _find_average_score(sentenceValue) -> int:
    """
    Find the average score from the sentence value dictionary
    :rtype: int
    """
    sumValues = 0
    for entry in sentenceValue:
        sumValues += sentenceValue[entry]

    average = (sumValues / len(sentenceValue))

    return average

def _score_sentences(tf_idf_matrix) -> dict:
    """
    score a sentence by its word's TF
    Basic algorithm: adding the TF frequency of every non-stop word in a sentence divided by total no of words in a sentence.
    :rtype: dict
    """

    sentenceValue = {}

    for sent, f_table in tf_idf_matrix.items():
        total_score_per_sentence = 0

        count_words_in_sentence = len(f_table)
        for word, score in f_table.items():
            total_score_per_sentence += score

        sentenceValue[sent] = total_score_per_sentence / count_words_in_sentence

    return sentenceValue

def _create_tf_idf_matrix(tf_matrix, idf_matrix):
    tf_idf_matrix = {}

    for (sent1, f_table1), (sent2, f_table2) in zip(tf_matrix.items(), idf_matrix.items()):

        tf_idf_table = {}

        for (word1, value1), (word2, value2) in zip(f_table1.items(),
                                                    f_table2.items()):  
            tf_idf_table[word1] = float(value1 * value2)

        tf_idf_matrix[sent1] = tf_idf_table

    return tf_idf_matrix

def _create_idf_matrix(freq_matrix, count_doc_per_words, total_documents):
    idf_matrix = {}

    for sent, f_table in freq_matrix.items():
        idf_table = {}

        for word in f_table.keys():
            idf_table[word] = math.log10(total_documents / float(count_doc_per_words[word]))

        idf_matrix[sent] = idf_table

    return idf_matrix

def _create_documents_per_words(freq_matrix):
    word_per_doc_table = {}

    for sent, f_table in freq_matrix.items():
        for word, count in f_table.items():
            if word in word_per_doc_table:
                word_per_doc_table[word] += 1
            else:
                word_per_doc_table[word] = 1

    return word_per_doc_table

def _create_tf_matrix(freq_matrix):
    tf_matrix = {}

    for sent, f_table in freq_matrix.items():
        tf_table = {}

        count_words_in_sentence = len(f_table)
        for word, count in f_table.items():
            tf_table[word] = count / count_words_in_sentence

        tf_matrix[sent] = tf_table

    return tf_matrix

def _create_frequency_matrix(sentences):
    frequency_matrix = {}
    stopWords = set(stopwords.words("english"))
    ps = PorterStemmer()

    for sent in sentences:
        freq_table = {}
        words = word_tokenize(sent)
        for word in words:
            word = word.lower()
            word = ps.stem(word)
            if word in stopWords:
                continue

            if word in freq_table:
                freq_table[word] += 1
            else:
                freq_table[word] = 1

        frequency_matrix[sent[:15]] = freq_table

    return frequency_matrix

def get_key_from_dict(val,dic):
    key_list=list(dic.keys())
    val_list=list(dic.values())
    ind=val_list.index(val)
    return key_list[ind]

import nltk
from string import punctuation
from heapq import nlargest
nltk.download('punkt')
nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

def nltk_summarize(text_content, percent):
    tokens = word_tokenize(text_content)
    stop_words = stopwords.words('english')
    punctuation_items = punctuation + '\n'

    word_frequencies = {}
    for word in tokens:
        if word.lower() not in stop_words:
            if word.lower() not in punctuation_items:
                if word not in word_frequencies.keys():
                    word_frequencies[word] = 1
                else:
                    word_frequencies[word] += 1
    max_frequency = max(word_frequencies.values())

    for word in word_frequencies.keys():
        word_frequencies[word] = word_frequencies[word] / max_frequency
    sentence_token = sent_tokenize(text_content)
    sentence_scores = {}
    for sent in sentence_token:
        sentence = sent.split(" ")
        for word in sentence:
            if word.lower() in word_frequencies.keys():
                if sent not in sentence_scores.keys():
                    sentence_scores[sent] = word_frequencies[word.lower()]
                else:
                    sentence_scores[sent] += word_frequencies[word.lower()]

    select_length = int(len(sentence_token) * (int(percent) / 100))
    summary = nlargest(select_length, sentence_scores, key=sentence_scores.get)
    final_summary = [word for word in summary]
    summary = ' '.join(final_summary)
    return summary


hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 


file_ = open("app_logo.png", "rb")
contents = file_.read()
data_url = base64.b64encode(contents).decode("utf-8")
file_.close()

centered_logo = f"""
    <div style="display: flex; justify-content: center; align-items: center; margin-top: 0;">
        <img src='data:image/png;base64,{data_url}' alt="App Logo" height="180" width="260"/>
    </div>
"""

st.markdown(centered_logo, unsafe_allow_html=True)
page_bg_img = """
        <style>
        .stApp {
        background-color: #F9EBEA;
        background-size: cover;
        }
        </style>
        """
st.markdown(page_bg_img, unsafe_allow_html=True)

url = st.text_input('# **Video URL**', 'https://www.youtube.com/watch?v=4HGNqFdaD34&t=1s')

from bs4 import BeautifulSoup
import requests
r = requests.get(url)
soup = BeautifulSoup(r.text)

link = soup.find_all(name="title")[0]
title = str(link)
title = title.replace("<title>","")
title = title.replace("</title>","")
title = title.replace("&amp;","&")

value = title
st.info("### " + value)
st.video(url)

col1, col2 = st.columns(2)  # Create two columns
with col1:
        sumtype = st.selectbox(
            'Type Of Summarization',
            options=['Extractive', 'Abstractive'])


if sumtype == 'Extractive':     
    with col2:
            sumalgo = st.selectbox(
                'Select Specification',
                options=['Word Matcher', 'Talk Analyzer', 'Sentence Detector', 'Key Finder'])

    with col1:       
        st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)

        length = st.radio(
            'Select Length [Summary]',
            options=['20%', '40%', '60%', '80%', '100%'])

    with col2: 
        languages_dict = {'en':'English' ,'af':'Afrikaans' ,'sq':'Albanian' ,'am':'Amharic' ,'ar':'Arabic' ,'hy':'Armenian' ,'az':'Azerbaijani' ,'eu':'Basque' ,'be':'Belarusian' ,'bn':'Bengali' ,'bs':'Bosnian' ,'bg':'Bulgarian' ,'ca':'Catalan' ,'ceb':'Cebuano' ,'ny':'Chichewa' ,'zh-cn':'Chinese (simplified)' ,'zh-tw':'Chinese (traditional)' ,'co':'Corsican' ,'hr':'Croatian' ,'cs':'Czech' ,'da':'Danish' ,'nl':'Dutch' ,'eo':'Esperanto' ,'et':'Estonian' ,'tl':'Filipino' ,'fi':'Finnish' ,'fr':'French' ,'fy':'Frisian' ,'gl':'Galician' ,'ka':'Georgian' ,'de':'German' ,'el':'Greek' ,'gu':'Gujarati' ,'ht':'Haitian creole' ,'ha':'Hausa' ,'haw':'Hawaiian' ,'he':'Hebrew' ,'hi':'Hindi' ,'hmn':'Hmong' ,'hu':'Hungarian' ,'is':'Icelandic' ,'ig':'Igbo' ,'id':'Indonesian' ,'ga':'Irish' ,'it':'Italian' ,'ja':'Japanese' ,'jw':'Javanese' ,'kn':'Kannada' ,'kk':'Kazakh' ,'km':'Khmer' ,'ko':'Korean' ,'ku':'Kurdish (kurmanji)' ,'ky':'Kyrgyz' ,'lo':'Lao' ,'la':'Latin' ,'lv':'Latvian' ,'lt':'Lithuanian' ,'lb':'Luxembourgish' ,'mk':'Macedonian' ,'mg':'Malagasy' ,'ms':'Malay' ,'ml':'Malayalam' ,'mt':'Maltese' ,'mi':'Maori' ,'mr':'Marathi' ,'mn':'Mongolian' ,'my':'Myanmar (burmese)' ,'ne':'Nepali' ,'no':'Norwegian' ,'or':'Odia' ,'ps':'Pashto' ,'fa':'Persian' ,'pl':'Polish' ,'pt':'Portuguese' ,'pa':'Punjabi' ,'ro':'Romanian' ,'ru':'Russian' ,'sm':'Samoan' ,'gd':'Scots gaelic' ,'sr':'Serbian' ,'st':'Sesotho' ,'sn':'Shona' ,'sd':'Sindhi' ,'si':'Sinhala' ,'sk':'Slovak' ,'sl':'Slovenian' ,'so':'Somali' ,'es':'Spanish' ,'su':'Sundanese' ,'sw':'Swahili' ,'sv':'Swedish' ,'tg':'Tajik' ,'ta':'Tamil' ,'te':'Telugu' ,'th':'Thai' ,'tr':'Turkish' ,'uk':'Ukrainian' ,'ur':'Urdu' ,'ug':'Uyghur' ,'uz':'Uzbek' ,'vi':'Vietnamese' ,'cy':'Welsh' ,'xh':'Xhosa' ,'yi':'Yiddish' ,'yo':'Yoruba' ,'zu':'Zulu'}
        add_selectbox = st.selectbox(
            "Select Language",
            ( 'English' ,'Afrikaans' ,'Albanian' ,'Amharic' ,'Arabic' ,'Armenian' ,'Azerbaijani' ,'Basque' ,'Belarusian' ,'Bengali' ,'Bosnian' ,'Bulgarian' ,'Catalan' ,'Cebuano' ,'Chichewa' ,'Chinese (simplified)' ,'Chinese (traditional)' ,'Corsican' ,'Croatian' ,'Czech' ,'Danish' ,'Dutch' ,'Esperanto' ,'Estonian' ,'Filipino' ,'Finnish' ,'French' ,'Frisian' ,'Galician' ,'Georgian' ,'German' ,'Greek' ,'Gujarati' ,'Haitian creole' ,'Hausa' ,'Hawaiian' ,'Hebrew' ,'Hindi' ,'Hmong' ,'Hungarian' ,'Icelandic' ,'Igbo' ,'Indonesian' ,'Irish' ,'Italian' ,'Japanese' ,'Javanese' ,'Kannada' ,'Kazakh' ,'Khmer' ,'Korean' ,'Kurdish (kurmanji)' ,'Kyrgyz' ,'Lao' ,'Latin' ,'Latvian' ,'Lithuanian' ,'Luxembourgish' ,'Macedonian' ,'Malagasy' ,'Malay' ,'Malayalam' ,'Maltese' ,'Maori' ,'Marathi' ,'Mongolian' ,'Myanmar (burmese)' ,'Nepali' ,'Norwegian' ,'Odia' ,'Pashto' ,'Persian' ,'Polish' ,'Portuguese' ,'Punjabi' ,'Romanian' ,'Russian' ,'Samoan' ,'Scots gaelic' ,'Serbian' ,'Sesotho' ,'Shona' ,'Sindhi' ,'Sinhala' ,'Slovak' ,'Slovenian' ,'Somali' ,'Spanish' ,'Sundanese' ,'Swahili' ,'Swedish' ,'Tajik' ,'Tamil' ,'Telugu' ,'Thai' ,'Turkish' ,'Ukrainian' ,'Urdu' ,'Uyghur' ,'Uzbek' ,'Vietnamese' ,'Welsh' ,'Xhosa' ,'Yiddish' ,'Yoruba' ,'Zulu')
        )



    if st.button('Summarize'):
         st.success(dedent("""### \U0001F4DD Summary
         """))

         url_data = urlparse(url)
         id = url_data.query[2::]

         def generate_transcript(id):
                 transcript = YouTubeTranscriptApi.get_transcript(id)
                 script = ""

                 for text in transcript:
                         t = text["text"]
                         if t != '[Music]':
                                 script += t + " "

                 return script, len(script.split())
         transcript, no_of_words = generate_transcript(id)

         if sumalgo == 'Word Matcher':
             summ = gensim_summarize(transcript, int(length[:2]))


         if sumalgo == 'Talk Analyzer':
             summ = nltk_summarize(transcript, int(length[:2]))


         if sumalgo == 'Sentence Detector':
             summ = spacy_summarize(transcript, int(length[:2]))

         if sumalgo == 'Key Finder':
             sentences = sent_tokenize(transcript)
             total_documents = len(sentences)
             sentences = sent_tokenize(transcript)
             total_documents = len(sentences)

             freq_matrix = _create_frequency_matrix(sentences)

             tf_matrix = _create_tf_matrix(freq_matrix)

             count_doc_per_words = _create_documents_per_words(freq_matrix)

             idf_matrix = _create_idf_matrix(freq_matrix, count_doc_per_words, total_documents)

             tf_idf_matrix = _create_tf_idf_matrix(tf_matrix, idf_matrix)

             sentence_scores = _score_sentences(tf_idf_matrix)

             threshold = _find_average_score(sentence_scores)

             summary = _generate_summary(sentences, sentence_scores, 1.0 * threshold)
            
             summ = summary
              
         translated = GoogleTranslator(source='auto', target= get_key_from_dict(add_selectbox,languages_dict)).translate(summ)
         html_str3 = f"""
                    <style>
                    p.a {{
                    text-align: justify;
                    }}
                    </style>
                    <p class="a">{translated}</p>
                    """
         st.markdown(html_str3, unsafe_allow_html=True)

         st.success("###  \U0001F50A Play For Audio Summary")
         no_support = ['Amharic', 'Azerbaijani', 'Basque', 'Belarusian', 'Cebuano', 'Chichewa', 'Chinese (simplified)', 'Chinese (traditional)', 'Corsican', 'Frisian', 'Galician', 'Georgian', 'Haitian creole', 'Hausa', 'Hawaiian', 'Hmong', 'Igbo', 'Irish', 'Kazakh', 'Kurdish (kurmanji)', 'Kyrgyz', 'Lao', 'Lithuanian', 'Luxembourgish', 'Malagasy', 'Maltese', 'Maori', 'Mongolian', 'Odia', 'Pashto', 'Persian', 'Punjabi', 'Samoan', 'Scots gaelic', 'Sesotho', 'Shona', 'Sindhi', 'Slovenian', 'Somali', 'Tajik', 'Uyghur', 'Uzbek', 'Xhosa', 'Yiddish', 'Yoruba', 'Zulu']
         if add_selectbox in no_support:
             st.warning(" \U000026A0 \xa0 Audio Support for this language is currently unavailable\n")
             lang_warn = GoogleTranslator(source='auto', target= get_key_from_dict(add_selectbox,languages_dict)).translate("\U000026A0 \xa0 Audio Support for this language is currently unavailable")
             st.warning(lang_warn)
         else:
             speech = gTTS(text = translated,lang=get_key_from_dict(add_selectbox,languages_dict), slow = False)
             speech.save('user_trans.mp3')          
             audio_file = open('user_trans.mp3', 'rb')    
             audio_bytes = audio_file.read()    
             st.audio(audio_bytes, format='audio/ogg',start_time=0)



elif sumtype == 'Abstractive':
     
     languages_dict = {'en':'English' ,'af':'Afrikaans' ,'sq':'Albanian' ,'am':'Amharic' ,'ar':'Arabic' ,'hy':'Armenian' ,'az':'Azerbaijani' ,'eu':'Basque' ,'be':'Belarusian' ,'bn':'Bengali' ,'bs':'Bosnian' ,'bg':'Bulgarian' ,'ca':'Catalan' ,'ceb':'Cebuano' ,'ny':'Chichewa' ,'zh-cn':'Chinese (simplified)' ,'zh-tw':'Chinese (traditional)' ,'co':'Corsican' ,'hr':'Croatian' ,'cs':'Czech' ,'da':'Danish' ,'nl':'Dutch' ,'eo':'Esperanto' ,'et':'Estonian' ,'tl':'Filipino' ,'fi':'Finnish' ,'fr':'French' ,'fy':'Frisian' ,'gl':'Galician' ,'ka':'Georgian' ,'de':'German' ,'el':'Greek' ,'gu':'Gujarati' ,'ht':'Haitian creole' ,'ha':'Hausa' ,'haw':'Hawaiian' ,'he':'Hebrew' ,'hi':'Hindi' ,'hmn':'Hmong' ,'hu':'Hungarian' ,'is':'Icelandic' ,'ig':'Igbo' ,'id':'Indonesian' ,'ga':'Irish' ,'it':'Italian' ,'ja':'Japanese' ,'jw':'Javanese' ,'kn':'Kannada' ,'kk':'Kazakh' ,'km':'Khmer' ,'ko':'Korean' ,'ku':'Kurdish (kurmanji)' ,'ky':'Kyrgyz' ,'lo':'Lao' ,'la':'Latin' ,'lv':'Latvian' ,'lt':'Lithuanian' ,'lb':'Luxembourgish' ,'mk':'Macedonian' ,'mg':'Malagasy' ,'ms':'Malay' ,'ml':'Malayalam' ,'mt':'Maltese' ,'mi':'Maori' ,'mr':'Marathi' ,'mn':'Mongolian' ,'my':'Myanmar (burmese)' ,'ne':'Nepali' ,'no':'Norwegian' ,'or':'Odia' ,'ps':'Pashto' ,'fa':'Persian' ,'pl':'Polish' ,'pt':'Portuguese' ,'pa':'Punjabi' ,'ro':'Romanian' ,'ru':'Russian' ,'sm':'Samoan' ,'gd':'Scots gaelic' ,'sr':'Serbian' ,'st':'Sesotho' ,'sn':'Shona' ,'sd':'Sindhi' ,'si':'Sinhala' ,'sk':'Slovak' ,'sl':'Slovenian' ,'so':'Somali' ,'es':'Spanish' ,'su':'Sundanese' ,'sw':'Swahili' ,'sv':'Swedish' ,'tg':'Tajik' ,'ta':'Tamil' ,'te':'Telugu' ,'th':'Thai' ,'tr':'Turkish' ,'uk':'Ukrainian' ,'ur':'Urdu' ,'ug':'Uyghur' ,'uz':'Uzbek' ,'vi':'Vietnamese' ,'cy':'Welsh' ,'xh':'Xhosa' ,'yi':'Yiddish' ,'yo':'Yoruba' ,'zu':'Zulu'}
     add_selectbox = st.selectbox(
         "Select Language",
         ( 'English' ,'Afrikaans' ,'Albanian' ,'Amharic' ,'Arabic' ,'Armenian' ,'Azerbaijani' ,'Basque' ,'Belarusian' ,'Bengali' ,'Bosnian' ,'Bulgarian' ,'Catalan' ,'Cebuano' ,'Chichewa' ,'Chinese (simplified)' ,'Chinese (traditional)' ,'Corsican' ,'Croatian' ,'Czech' ,'Danish' ,'Dutch' ,'Esperanto' ,'Estonian' ,'Filipino' ,'Finnish' ,'French' ,'Frisian' ,'Galician' ,'Georgian' ,'German' ,'Greek' ,'Gujarati' ,'Haitian creole' ,'Hausa' ,'Hawaiian' ,'Hebrew' ,'Hindi' ,'Hmong' ,'Hungarian' ,'Icelandic' ,'Igbo' ,'Indonesian' ,'Irish' ,'Italian' ,'Japanese' ,'Javanese' ,'Kannada' ,'Kazakh' ,'Khmer' ,'Korean' ,'Kurdish (kurmanji)' ,'Kyrgyz' ,'Lao' ,'Latin' ,'Latvian' ,'Lithuanian' ,'Luxembourgish' ,'Macedonian' ,'Malagasy' ,'Malay' ,'Malayalam' ,'Maltese' ,'Maori' ,'Marathi' ,'Mongolian' ,'Myanmar (burmese)' ,'Nepali' ,'Norwegian' ,'Odia' ,'Pashto' ,'Persian' ,'Polish' ,'Portuguese' ,'Punjabi' ,'Romanian' ,'Russian' ,'Samoan' ,'Scots gaelic' ,'Serbian' ,'Sesotho' ,'Shona' ,'Sindhi' ,'Sinhala' ,'Slovak' ,'Slovenian' ,'Somali' ,'Spanish' ,'Sundanese' ,'Swahili' ,'Swedish' ,'Tajik' ,'Tamil' ,'Telugu' ,'Thai' ,'Turkish' ,'Ukrainian' ,'Urdu' ,'Uyghur' ,'Uzbek' ,'Vietnamese' ,'Welsh' ,'Xhosa' ,'Yiddish' ,'Yoruba' ,'Zulu')
     )
     
     
     if st.button('Summarize'):
          st.success(dedent("""### \U0001F4DD Summary
    """))

          
          url_data = urlparse(url)
          id = url_data.query[2::]

          def generate_transcript(id):
               transcript = YouTubeTranscriptApi.get_transcript(id)
               script = ""

               for text in transcript:
                    t = text["text"]
                    if t != '[Music]':
                         script += t + " "

               return script, len(script.split())
          transcript, no_of_words = generate_transcript(id)

          model = T5ForConditionalGeneration.from_pretrained("t5-base")
          tokenizer = T5Tokenizer.from_pretrained("t5-base")
          inputs = tokenizer.encode("summarize: " + transcript, return_tensors="pt", max_length=512, truncation=True)
          
          outputs = model.generate(
              inputs, 
              max_length=150, 
              min_length=40, 
              length_penalty=2.0, 
              num_beams=4, 
              early_stopping=True)
          
          summ = tokenizer.decode(outputs[0])
          translated = GoogleTranslator(source='auto', target= get_key_from_dict(add_selectbox,languages_dict)).translate(summ)
          html_str3 = f"""
<style>
p.a {{
text-align: justify;
}}
</style>
<p class="a">{translated}</p>
"""
          st.markdown(html_str3, unsafe_allow_html=True)

          st.success("###  \U0001F50A Play For Audio Summary")
          no_support = ['Amharic', 'Azerbaijani', 'Basque', 'Belarusian', 'Cebuano', 'Chichewa', 'Chinese (simplified)', 'Chinese (traditional)', 'Corsican', 'Frisian', 'Galician', 'Georgian', 'Haitian creole', 'Hausa', 'Hawaiian', 'Hmong', 'Igbo', 'Irish', 'Kazakh', 'Kurdish (kurmanji)', 'Kyrgyz', 'Lao', 'Lithuanian', 'Luxembourgish', 'Malagasy', 'Maltese', 'Maori', 'Mongolian', 'Odia', 'Pashto', 'Persian', 'Punjabi', 'Samoan', 'Scots gaelic', 'Sesotho', 'Shona', 'Sindhi', 'Slovenian', 'Somali', 'Tajik', 'Uyghur', 'Uzbek', 'Xhosa', 'Yiddish', 'Yoruba', 'Zulu']
          if add_selectbox in no_support:
              st.warning(" \U000026A0 \xa0 Audio Support for this language is currently unavailable\n")
              lang_warn = GoogleTranslator(source='auto', target= get_key_from_dict(add_selectbox,languages_dict)).translate("\U000026A0 \xa0 Audio Support for this language is currently unavailable")
              st.warning(lang_warn)
          else:
              speech = gTTS(text = translated,lang=get_key_from_dict(add_selectbox,languages_dict), slow = False)
              speech.save('user_trans.mp3')          
              audio_file = open('user_trans.mp3', 'rb')    
              audio_bytes = audio_file.read()    
              st.audio(audio_bytes, format='audio/ogg',start_time=0)





