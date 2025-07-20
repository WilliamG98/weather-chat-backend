import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import openai
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WEATHERAPI_KEY = os.getenv('WEATHERAPI_KEY')

if not OPENAI_API_KEY or not WEATHERAPI_KEY:
    raise RuntimeError('OPENAI_API_KEY and WEATHERAPI_KEY must be set as environment variables.')

openai.api_key = OPENAI_API_KEY

# get location from IP using ip-api.com
def get_location_from_ip(ip):
    try:
        resp = requests.get(f'https://ipapi.co/{ip}/json/')
        data = resp.json()
        if 'city' in data and 'region' in data and 'country_name' in data:
            return data['city'], data['region'], data['country_name']
    except Exception:
        pass
    return None, None, None

# get weather from WeatherAPI
def get_weather(city):
    url = f'http://api.weatherapi.com/v1/current.json?key={WEATHERAPI_KEY}&q={city}'
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.json()
    return None

# Main chat endpoint
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    conversation_history = data.get('history', [])
    user_ip = data.get('user_ip', '')  # Get IP from frontend

    # Get user's location and weather automatically
    city, region, country = get_location_from_ip(user_ip)
    weather_info = ""
    if city:
        weather = get_weather(city)
        if weather:
            weather_info = f"Current weather in {city}, {region}, {country}: {weather['current']['temp_c']}°C and {weather['current']['condition']['text']}."
        else:
            weather_info = f"Location detected: {city}, {region}, {country}. Weather data unavailable."
    else:
        weather_info = "Unable to determine your location."

    # Build conversation context
    messages = [
        {"role": "system", "content": f"You are a helpful weather assistant. User's current location and weather: {weather_info}"}
    ]
    # Add conversation history (last 10 messages)
    for msg in conversation_history[-10:]:
        role = "user" if msg["sender"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["text"]})
    # Add current message
    messages.append({"role": "user", "content": user_message})

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    reply = response.choices[0].message.content
    return jsonify({"response": reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 