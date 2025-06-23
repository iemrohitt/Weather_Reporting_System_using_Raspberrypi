import RPi.GPIO as GPIO	
from RPLCD.i2c import CharLCD
import dht11
from smbus import SMBus
from time import sleep
import requests
import pandas as pd
from Sklenar. linear model imports Linear Regression
import numpy as np

# ==== CONFIGURATION ====
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

DHT11_PIN = 4
RAIN_SENSOR_PIN = 17
GPIO.setup(RAIN_SENSOR_PIN, GPIO.IN)

lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1,
cols=16, rows=2, charmap='A02', auto_linebreaks=False)

dht_sensor = dht11.DHT11(pin=DHT11_PIN)
bus = SMBus(1)
BMP180_ADDR = 0x77

CHANNEL_ID = "2921297"
READ_API_KEY = "B7FH3YZCM8W4HX1U"
WRITE_API_KEY = "OJKPZ2MJ4F84N9FE"
BASE_URL = "https://api.thingspeak.com"

# ==== LCD LOADING ====
lcd. write_string ("System Loading")
lcd.cursor_pos = (1, 0)
for i in range(16):
lcd.write_string(".")
sleep(0.1)
lcd.clear()
lcd.write_string("Wait..")
sleep(2)
lcd.clear()

# ==== FUNCTIONS ====
def read_dht11():
 result = dht_sensor.read()
 if result.is_valid():
temp = result.temperature
hum = result.humidity
print (f"DHT11 => Temp: {temp}C Humidity: {hum}%")
return temp, hum
return None, None
def read_bmp180():
try:
bus. write_byte_data (BMP180_ADDR, 0xF4, 0x2E)
sleep(0.005)
ut = (bus.read_byte_data(BMP180_ADDR, 0xF6) << 8) + bus.read_byte_data(BMP180_ADDR, 0xF7)
bus.write_byte_data(BMP180_ADDR, 0xF4, 0x34)
sleep(0.005)
 up = (bus.read_byte_data(BMP180_ADDR, 0xF6) << 8) + bus.read_byte_data(BMP180_ADDR, 0xF7)
pressure = up
print(f"BMP180 => Pressure: {pressure} hPa")
return int(pressure)
except Exception as e:
print("BMP180 error:", e)
return None

def read_rain():
rain = GPIO.input(RAIN_SENSOR_PIN)
print("Rain Detected" if rain == 0 else "No Rain")
return 1 if rain == 0 else 0

def safe_post(url, data, retries=3):
for i in range(retries):
try:
response = requests.post(url, data=data, timeout=10)
if response.status_code == 200:
return response
else:
print(f"POST failed (status {response.status_code}): {response.text}")
except Exception as e:
print(f"Attempt {i+1} POST error:", e)
sleep(3)
print("All retry attempts for POST failed.")
return None
def safe_get(url, retries=3):
for i in range(retries):
try:
response = requests.get(url, timeout=10)
if response.status_code == 200:
return response
else:
print(f"GET failed (status {response.status_code}): {response.text}")
except Exception as e:
print(f"Attempt {i+1} GET error:", e)
sleep(3)
print("All retry attempts for GET failed.")
return None
def send_actual_to_thingspeak(temp, hum, pres, rain):
url = f"{BASE_URL}/update"
data = {
'api_key': WRITE_API_KEY,
'field1': temp,
'field2': hum,
'field3': pres,
'field4': rain
}
response = safe_post(url, data)
if response:
print("Actual data sent to ThingSpeak.")

def send_predictions_to_thingspeak(p1, p2, p3, p4):
url = f"{BASE_URL}/update"
data = {
'api_key': WRITE_API_KEY,
'field5': p1,
'field6': p2,
'field7': p3,
'field8': p4
}
response = safe_post(url, data)
if response:
print(f"Predicted data sent: T={p1}, H={p2}, P={p3}, R={p4}")
def fetch_data_from_thingspeak():
url = f"{BASE_URL}/channels/{CHANNEL_ID}/feeds.json?api_key={READ_API_KEY}&results=40"
response = safe_get(url)
if response:
feeds = response.json()["feeds"]
df = pd.DataFrame(feeds)
df = df[["field1", "field2", "field3", "field4"]].dropna()
df = df.astype(float)
return df
return None

def make_predictions(df):
try:
X = df.index.values.reshape(-1, 1)
preds = []
for field in ['field1', 'field2', 'field3', 'field4']:
y = df[field].values
model = LinearRegression()
model.fit(X, y)
pred = model.predict([[len(X)]])
preds.append(round(pred[0]))
return preds
except Exception as e:
print("Prediction error:", e)
return [0, 0, 0, 0]


# ==== MAIN LOOP ====
try:
while True:

# Step 1: Read actual sensors
temperature, humidity = read_dht11()
pressure = read_bmp180()
rain_status = read_rain()

# Step 2: Display actual data
 lcd.clear()
 lcd.write_string(f"T:{temperature}C H:{humidity}%")
 lcd.cursor_pos = (1, 0)
 lcd.write_string(f"P:{pressure} R:{'Yes' if rain_status else 'No'}")

# Step 3: Send actual to ThingSpeak
if None not in (temperature, humidity, pressure):
send_actual_to_thingspeak(temperature, humidity, pressure, rain_status)
# Step 4: Predict values
df = fetch_data_from_thingspeak()
if df is not None:
pred_temp, pred_hum, pred_pres, pred_rain = make_predictions(df)

# Step 5: Display prediction
print(f"Predicted => Temp: {pred_temp}C, Hum: {pred_hum}%, Pres: {pred_pres}, Rain: {pred_rain}")
send_predictions_to_thingspeak(pred_temp, pred_hum, pred_pres, pred_rain)
sleep(15)  # ThingSpeak rate limit
except KeyboardInterrupt:
print("Exiting...")
lcd.clear()
GPIO.cleanup()
