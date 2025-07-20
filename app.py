import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import openai
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

# Load API keys from environment variables only
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WEATHERAPI_KEY = os.getenv('WEATHERAPI_KEY')

if not OPENAI_API_KEY or not WEATHERAPI_KEY:
    raise RuntimeError('OPENAI_API_KEY and WEATHERAPI_KEY must be set as environment variables.')

openai.api_key = OPENAI_API_KEY

# Helper: Get the User's Public IP
def get_public_ip():
    try:
        resp = requests.get('https://ipapi.co/ip/')
        if resp.status_code == 200:
            return resp.text.strip()
    except Exception:
        pass
    return None

# Helper: Get location from IP using ip-api.com
def get_location_from_ip(ip):
    try:
        resp = requests.get(f'https://ipapi.co/{ip}/json/')
        data = resp.json()
        if 'city' in data and 'region' in data and 'country_name' in data:
            return data['city'], data['region'], data['country_name']
    except Exception:
        pass
    return None, None, None

# Helper: Get weather from WeatherAPI
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
    user_ip = get_public_ip()

    # Build conversation context
    messages = [
        {"role": "system", "content": "You are a helpful weather assistant."}
    ]
    # Add conversation history (last 10 messages)
    for msg in conversation_history[-10:]:
        role = "user" if msg["sender"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["text"]})
    # Add current message
    messages.append({"role": "user", "content": user_message})

    # Check if user asks for weather in their location
    if 'weather' in user_message.lower() and 'my location' in user_message.lower():
        city, region, country = get_location_from_ip(user_ip)
        if city:
            weather = get_weather(city)
            if weather:
                weather_text = f"It's {weather['current']['temp_c']}°C and {weather['current']['condition']['text']} in {city}, {region}, {country}."
            else:
                weather_text = "Sorry, I couldn't fetch the weather for your location."
        else:
            weather_text = "Sorry, I couldn't determine your location."
        # Add weather info as a system message for context
        messages.append({"role": "system", "content": f"Weather info: {weather_text}"})

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    reply = response.choices[0].message.content
    return jsonify({"response": reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 