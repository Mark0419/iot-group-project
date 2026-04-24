import Adafruit_DHT

SENSOR = Adafruit_DHT.DHT11
PIN = 4

def read_dht11():
    humidity, temperature = Adafruit_DHT.read_retry(SENSOR, PIN)
    if humidity is not None and temperature is not None:
        return round(temperature, 1), round(humidity, 1)
    else:
        print("Failed to read sensor")
    return None, None

if __name__ == "__main__":
    temp, hum = read_dht11()
    if temp:
        print(f"Temperature: {temp}C, Humidity: {hum}%")
