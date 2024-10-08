import requests
from groq import Groq
import datetime
from flask import Flask, render_template, request
import os


GROQ_API = os.getenv("GROQ_API")
GET_COORDINATES_API = os.getenv("GET_COORDINATES_API")
RAIN_API = os.getenv("RAIN_API")

app = Flask(__name__)


def get_response(location_name_p, month_p):
    client = Groq(api_key=GROQ_API)
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"In {location_name_p}, during {month_p}, what is the estimated rainfall in mm. Just give "
                           f"the whole number, nothing else.",
            }
        ],
        model="llama3-8b-8192",
    )
    precipitation = chat_completion.choices[0].message.content
    return int(precipitation)

def get_crop(location_name_p):
    client = Groq(api_key=GROQ_API)
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": "What is the most grown crop in " + location_name_p + ". Nothing else, just the name of crop",
            }
        ],
        model="llama3-8b-8192",
    )
    return chat_completion.choices[0].message.content

def get_cor(location_name_p):
    url = "https://forward-reverse-geocoding.p.rapidapi.com/v1/search"
    querystring = {
        "q": location_name_p,
        "format": "json",
        "addressdetails": "1",
        "namedetails": "0",
        "accept-language": "en",
        "limit": "5",
        "bounded": "0",
        "polygon_text": "0",
        "polygon_svg": "0",
        "polygon_kml": "0",
        "polygon_geojson": "0",
        "polygon_threshold": "0.0"
    }
    headers = {
        "x-rapidapi-key": GET_COORDINATES_API,
        "x-rapidapi-host": "forward-reverse-geocoding.p.rapidapi.com"
    }
    response_cor = requests.get(url, headers=headers, params=querystring)
    cor_data = response_cor.json()
    first_entry = cor_data[0]
    latitude = first_entry['lat']
    longitude = first_entry['lon']
    coordinates = (latitude, longitude)
    return coordinates

def get_rain(this_coordinates):
    parameters = {
        "lat": this_coordinates[0],
        "lon": this_coordinates[1],
        "appid": RAIN_API,
        "cnt": "30"
    }
    OWN_endpoint = "https://api.openweathermap.org/data/2.5/forecast"
    response = requests.get(OWN_endpoint, params=parameters)
    data = response.json()["list"]

    total_rain = 0
    for entry in data:
        rain_volume = entry.get('rain', {}).get('3h', 0)
        total_rain += rain_volume
    total_rain = total_rain * 10

    return round(total_rain, 2)

def expert_tip(location_p, month_p, usual, actual, crop_p):
    client = Groq(api_key=GROQ_API)
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"This year, in {location_p} during {month_p}, the predicted rainfall is {actual}mm "
                           f"whereas the usual rainfall is {usual}mm. Give 3 suggestion points (each on a new line) keeping in mind the "
                           f"region, the soil type in region and climate for the farmers. Talk specifically about {crop_p} which is the most grown in this month"
                           f"crop in region in the first point. Just 3 total points nothing else. "
                           f"Do not write anything like Here are three suggestion points for. This year, in {location_p} during {month_p}, the predicted rainfall is {actual}mm "
                           f"whereas the usual rainfall is {usual}mm.",
            }
        ],
        model="llama3-8b-8192",
    )
    expert_points = chat_completion.choices[0].message.content
    return expert_points

@app.route('/')
def home():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    location = request.form['location']
    month = datetime.datetime.now().strftime("%B")  # Get current month

    # Call your functions here with the input data
    actual_rain = get_rain(get_cor(location))
    usual_rain = get_response(get_crop(location), month)
    crop = get_crop(location)
    suggestion = expert_tip(location, month, usual_rain, actual_rain, crop)

    result = {
        'location': location,
        'month': month,
        'actual_rain': actual_rain,
        'usual_rain': usual_rain,
        'crop': crop,
        'suggestion': suggestion
    }

    return render_template('results.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
