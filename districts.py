"""One approximate representative town point per district; not district centroids.

The district name is our own metadata: Open-Meteo accepts coordinates, not districts.
Replace these points or add a grid in a later phase for better spatial coverage.
"""

DISTRICTS = [
    {"district": "Thiruvananthapuram", "location": "Thiruvananthapuram", "latitude": 8.5241, "longitude": 76.9366},
    {"district": "Kollam", "location": "Kollam", "latitude": 8.8932, "longitude": 76.6141},
    {"district": "Pathanamthitta", "location": "Pathanamthitta", "latitude": 9.2648, "longitude": 76.7870},
    {"district": "Alappuzha", "location": "Alappuzha", "latitude": 9.4981, "longitude": 76.3388},
    {"district": "Kottayam", "location": "Kottayam", "latitude": 9.5916, "longitude": 76.5222},
    {"district": "Idukki", "location": "Painavu", "latitude": 9.8494, "longitude": 76.9730},
    {"district": "Ernakulam", "location": "Kakkanad", "latitude": 10.0159, "longitude": 76.3419},
    {"district": "Thrissur", "location": "Thrissur", "latitude": 10.5276, "longitude": 76.2144},
    {"district": "Palakkad", "location": "Palakkad", "latitude": 10.7867, "longitude": 76.6548},
    {"district": "Malappuram", "location": "Malappuram", "latitude": 11.0510, "longitude": 76.0711},
    {"district": "Kozhikode", "location": "Kozhikode", "latitude": 11.2588, "longitude": 75.7804},
    {"district": "Wayanad", "location": "Kalpetta", "latitude": 11.6103, "longitude": 76.0828},
    {"district": "Kannur", "location": "Kannur", "latitude": 11.8745, "longitude": 75.3704},
    {"district": "Kasaragod", "location": "Kasaragod", "latitude": 12.4996, "longitude": 74.9869},
]

DISTRICT_NAMES = [point["district"] for point in DISTRICTS]
