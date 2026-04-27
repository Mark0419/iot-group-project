from pigpio_dht import DHT11
import time

# Initialize the sensor on GPIO 17
# Note: pigpio uses BCM GPIO numbers, not physical pin numbers!
gpio_pin = 17
sensor = DHT11(gpio_pin)

print(f"Starting Hardware-DMA sensor read on GPIO {gpio_pin}. Press Ctrl+C to quit.")

while True:
    try:
        # The read() function automatically handles retries and timing
        result = sensor.read()
        
        # The result is a dictionary containing the data and a 'valid' flag
        if result.get('valid'):
            temp = result.get('temp_c')
            hum = result.get('humidity')
            print(f"Success! Temperature: {temp}°C, Humidity: {hum}%")
        else:
            print("Checksum failed or missed signal. Retrying...")
            
    except TimeoutError:
        print("Sensor not responding. Check wiring to GPIO 17.")
    except Exception as e:
        print(f"Error: {e}")
        
    # Wait 2 seconds before the next read
    time.sleep(2)
