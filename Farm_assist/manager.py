from __future__ import division
from flask import Flask, request, jsonify, render_template
import os
import dialogflow_v2beta1 as dialogflow
import requests
import json
import pusher
from dotenv import load_dotenv
import numpy as np
from sklearn.neighbors import NearestNeighbors
import pandas as pd
import predicted
import re
import sys
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import pyaudio
from six.moves import queue
import socket
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(r'C:\Users\Dell\Documents\Plaksha\Data-x\Data-x_Project\krishi_bot\googlecloud.json')
socket.setdefaulttimeout(15)

# retrieve lat long
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from functools import partial

locator = Nominatim(user_agent='myGeocoder')
geocode = RateLimiter(locator.geocode)

def get_geocode(df):
    try:
        location = df.ADDRESS[:200].apply(partial(geocode,timeout=None))
        return location
    except GeocoderTimedOut as e:
        get_geocode()
        

def get_coordinates():
    df=pd.read_csv(r'C:\Users\Dell\Documents\Plaksha\Data-x\Data-x_Project\krishi_bot\Data\mandi_price_data.csv')
    ADDRESS = df.apply(lambda row:'{},{},{}'.format(row.MARKET,row.DISTRICT,row.STATE),axis=1)
    df['ADDRESS'] = ADDRESS
    location = get_geocode(df)
    point = location.apply(lambda loc: tuple(loc.point) if loc else None)
    df[['latitude', 'longitude', 'altitude']] = pd.DataFrame(point.tolist(), index=df.index)
    df.to_csv('price_latlong.csv')
    
app = Flask('KrishiBot')
user_latitude = ''
user_longitude = ''

# initialize Pusher
load_dotenv()
pusher_client = pusher.Pusher(
    app_id=os.getenv('PUSHER_APP_ID'),
    key=os.getenv('PUSHER_KEY'),
    secret=os.getenv('PUSHER_SECRET'),
    cluster=os.getenv('PUSHER_CLUSTER'),
    ssl=True)

@app.route('/')
def index():
    return render_template('home_index.html')

@app.route('/display_chatbot')
def display_chatbot():
    print('chatbot')
    return render_template('chat.html')

@app.route('/send_geolocation', methods=['POST'])
def send_geolocation():
    print('geo')
    global user_latitude 
    global user_longitude 
    user_latitude = request.form['lat']
    user_longitude = request.form['long'] 
    return str('')
    
def detect_intent_texts(project_id, session_id, text, language_code,crop):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)
    if text:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)
        query_input = dialogflow.types.QueryInput(text=text_input)
        knowledgebase_client = dialogflow.KnowledgeBasesClient()
        Parent = knowledgebase_client.project_path(project_id);
        knowledge_base_path = ''
        knowledge_bases = []
        for element in  knowledgebase_client.list_knowledge_bases(parent = Parent):
            knowledge_bases.append(element)
        print(knowledge_bases) 
        if crop == 'wheat':
            knowledge_base_path = knowledge_bases[0].name
        else:
            knowledge_base_path = knowledge_bases[2].name
        query_params = dialogflow.types.QueryParameters(
            knowledge_base_names=[knowledge_base_path])
        response = session_client.detect_intent(
            session=session, query_input=query_input,query_params=query_params)
        print(response.query_result.fulfillment_text)
        return response.query_result.fulfillment_text
 
@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        socketId = request.form['socketId']
    except KeyError:
        socketId = ''
        
    message = request.form['message']
    crop = request.form['crop']
    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
    fulfillment_text = detect_intent_texts(project_id, np.random.rand(1,1), message, 'en',crop)
    response_text = { "message":  fulfillment_text, }

    pusher_client.trigger(
        'KrishBot', 
        'new_message', 
        {
            'human_message': message, 
            'bot_message': fulfillment_text,
        },
        socketId
    )
                        
    return jsonify(response_text)
 
@app.route('/get_market', methods=['GET','POST'])
def get_market():
    userlocation = np.array([[user_latitude, user_longitude]])
    distances, indices = predicted.predict(userlocation)
    market = pd.read_csv('./Data/Markets_LatLong.csv')
    price = pd.read_csv('./Data/price_latlong.csv')
    print(indices)
    nearest_mandi = market.iloc[indices[0][:]]
    print(nearest_mandi)
    price_nearest_mandi = price[price.ADDRESS.isin(nearest_mandi.ADDRESS)]
    market_commodity = price_nearest_mandi[['MARKET','COMMODITY']].drop_duplicates()
    market_commodity_dic = market_commodity.groupby('MARKET').COMMODITY.apply(list)
    return jsonify({'market':list(market_commodity_dic.index),'commodity':list(market_commodity_dic.values)})
   
@app.route('/get_price', methods=['GET','POST'])
def get_price():
    try:
        market = request.form['market']
        commodity = request.form['commodity']
    except KeyError:
        market = ''
        commodity = ''
    df = pd.read_csv('./Data/price_latlong.csv')
    price = df[(df.MARKET == market) &(df.COMMODITY == commodity)]
    variety_price = price[['VARIETY','ARRIVAL_DATE','MIN_PRICE','MAX_PRICE','MODAL_PRICE']]
    variety_date = pd.DataFrame(variety_price.groupby('VARIETY')['ARRIVAL_DATE'].max()).reset_index()
    variety_date_price = variety_date.merge(variety_price,how='inner',on=['ARRIVAL_DATE','VARIETY'])
    print(variety_date_price.to_dict())
    return jsonify(variety_date_price.to_dict())
    

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms


class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk
        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


def listen_print_loop(responses):
    
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue

        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        #
        # If the previous result was longer than this one, we need to print
        # some extra spaces to overwrite the previous result
        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            print(transcript + overwrite_chars)
            print('23')

            # Exit recognition if any of the transcribed phrases could be
            # one of our keywords.
            if re.search(r'\b(exit|quit)\b', transcript, re.I):
                print('Exiting..')
                break

            num_chars_printed+=1
        return transcript + overwrite_chars
        
@app.route('/send_audio', methods=['POST'])
def send_audio():
    # See http://g.co/cloud/speech/docs/languages
    # for a list of supported languages.
    language_code = 'en-IN'  # a BCP-47 language tag
    try:
        socketId = request.form['socketId']
    except KeyError:
        socketId = ''

    client = speech.SpeechClient(credentials = credentials)
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code)
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        interim_results=True, single_utterance = True)

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (types.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests,timeout =20.0)

        # Now, put the transcription responses to use.
        try:
            message = listen_print_loop(responses)
            print(message+'outside')
            #project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
            #fulfillment_text = detect_intent_texts(project_id, np.random.rand(1,1), message, 'en')
            #response_text = {"message":fulfillment_text,"input":message}  
            return jsonify({"input":message})
        except:
            pass
            return jsonify({"input":message})
            
# run Flask app
if __name__ == "__main__":
    app.run()