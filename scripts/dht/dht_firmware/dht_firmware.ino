#include <Wire.h>

#define DHT12_ADDR 0x5C

void setup() {
    Serial.begin(115200);
    Wire.begin(4, 5);  // SDA=GPIO4(D2), SCL=GPIO5(D1)
    delay(100);
}

void loop() {
    Wire.beginTransmission(DHT12_ADDR);
    Wire.write(0x00);
    if (Wire.endTransmission() != 0) {
        Serial.println("I2C fail");
        delay(3000);
        return;
    }

    Wire.requestFrom(DHT12_ADDR, (uint8_t)5);
    if (Wire.available() < 5) {
        Serial.println("short read");
        delay(3000);
        return;
    }

    uint8_t data[5];
    for (int i = 0; i < 5; i++) data[i] = Wire.read();

    uint8_t sum = data[0] + data[1] + data[2] + data[3];
    if (sum != data[4]) {
        Serial.println("checksum fail");
        delay(3000);
        return;
    }

    float hum  = data[0] + data[1] * 0.1f;
    float temp = data[2] + (data[3] & 0x7F) * 0.1f;
    if (data[3] & 0x80) temp = -temp;

    Serial.print(temp, 1);
    Serial.print(" C  ");
    Serial.print(hum, 1);
    Serial.println(" %");
    delay(100);
}
