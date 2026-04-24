import random
import time

def read_dht11():
    """Simulates reading temperature and humidity"""
    temperature = round(random.uniform(22.0, 26.0), 1)
    humidity = round(random.uniform(50.0, 60.0), 1)
    return temperature, humidity

if __name__ == "__main__":
    temp, hum = read_dht11()
    if temp:
        print(f"Temperature: {temp}C, Humidity: {hum}%")
