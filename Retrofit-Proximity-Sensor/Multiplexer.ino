#include <SoftwareSerial.h>

SoftwareSerial port1(2, 3);   
SoftwareSerial port2(4, 5);   
SoftwareSerial port3(6, 7);   

SoftwareSerial* sensors[3] = {&port1, &port2, &port3};
float distances[3] = {0.0, 0.0, 0.0};

const unsigned long READ_TIMEOUT = 80; 

void setup() {
  Serial.begin(115200);
  
  for (int i = 0; i < 3; i++) {
    sensors[i]->begin(115200);
    
    sensors[i]->listen();
    sensors[i]->println("sensorStart"); 
    delay(50);
  }
  
  Serial.println("--- Arduino Multiplexer Ready ---");
}

void loop() {
  for (int i = 0; i < 3; i++) {
    float result = readSensorData(i);
    
    if (result > 0.01) {
      distances[i] = result;
    }
  }

  // Transmit the packet to the Pi in the [S1, S2, S3] format
  Serial.print("[");
  Serial.print(distances[0], 2); Serial.print(", ");
  Serial.print(distances[1], 2); Serial.print(", ");
  Serial.print(distances[2], 2);
  Serial.println("]");
}

float readSensorData(int sensorIndex) {
  sensors[sensorIndex]->listen();
  
  while(sensors[sensorIndex]->available() > 0) { 
    sensors[sensorIndex]->read(); 
  }

  unsigned long startTime = millis();
  String buffer = "";

  while (millis() - startTime < READ_TIMEOUT) {
    if (sensors[sensorIndex]->available()) {
      char c = sensors[sensorIndex]->read();
      buffer += c;

      if (c == '\n') {
        if (buffer.indexOf("Range") != -1) {
          return parseDistance(buffer);
        } else {
          buffer = ""; 
        }
      }
    }
  }
  
  return -1.0;
}

float parseDistance(String raw) {
  int idx = raw.indexOf("Range");
  if (idx != -1) {
    String val = raw.substring(idx + 5);
    val.trim();
    return val.toFloat();
  }
  return -1.0;
}