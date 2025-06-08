#define LED1  2    // GPIO2 สำหรับ LED1 (Solenoid1)
#define LED2  4    // GPIO4 สำหรับ LED2 (Solenoid2)
#define PUMP  5    // GPIO5 สำหรับปั๊มน้ำ

String inputString = "";

void setup() {
  Serial.begin(9600);
  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);
  pinMode(PUMP, OUTPUT);
  digitalWrite(LED1, LOW);
  digitalWrite(LED2, LOW);
  digitalWrite(PUMP, LOW);
}

void loop() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {
      handleCommand(inputString);
      inputString = "";
    } else {
      inputString += inChar;
    }
  }
}

void handleCommand(String cmd) {
  cmd.trim();
  if (cmd == "LED1_ON") {
    digitalWrite(LED1, HIGH);
    digitalWrite(PUMP, HIGH);
  } else if (cmd == "LED2_ON") {
    digitalWrite(LED1, HIGH);
    digitalWrite(LED2, HIGH);
    digitalWrite(PUMP, HIGH);
  } else if (cmd == "LED1_OFF") {
    digitalWrite(LED1, LOW);
    // ถ้า LED2 ยังติด ปั๊มยังต้องเปิดอยู่
    if (digitalRead(LED2) == LOW) {
      digitalWrite(PUMP, LOW);
    }
  } else if (cmd == "LED2_OFF") {
    digitalWrite(LED2, LOW);
    // ถ้า LED1 ยังติด ปั๊มยังต้องเปิดอยู่
    if (digitalRead(LED1) == LOW) {
      digitalWrite(PUMP, LOW);
    }
  } else if (cmd == "LED_OFF" || cmd == "STOP") {
    digitalWrite(LED1, LOW);
    digitalWrite(LED2, LOW);
    digitalWrite(PUMP, LOW);
  }
}
