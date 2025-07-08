#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Thông tin WiFi
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Thông tin Odoo server
const char* odoo_url = "http://your-odoo-server.com/api/error/report";

// Định nghĩa các lỗi
struct Error {
  String code;
  String description;
  String solution;
};

Error errors[] = {
  {"E-01", "High voltage error", "Check supply voltage"},
  {"E-02", "Low-Voltage error", "Check supply voltage"},
  {"E-03", "CPU communication fault", "Check the cable, check the connection of the connector to the operation panel"},
  {"E-04", "Pedel connection fault", "Check the cable, check the connection of the connector to the operation pedal"},
  {"E-05", "Main shaft rotation fault", "Check weather the main shaft motor is locked by turning the pulley, Check the connection of the main shaft motor encoder cable to connector, Check the connection of the main shaft motor power cable to connector"},
  {"E-06", "Reverse feed stitching lever operation time is exceeded", "hen re-turn ON the power"},
  {"E-07", "Encoder Z-phase detection fault", "Check the connection of the motor encoder cable to the connector"},
  {"E-08", "Solenoid overcurrent", "Check wheather the solenoid has failed"},
  {"E-09", "Encoder AB-phase detection fault", "Check the connection of the motor encoder cable to the connector"},
  {"E-10", "Main shaft motor overcurrent error", "Then re-turn ON the power"},
  {"E-11", "Machine head tilting error", "Raise the maching head, Then turn the power OFF and re-turn power ON, Check weather the machine head tilt switch has broken"},
  {"E-12", "Main shaft rotation fault", "Check the connection o the main shaft motor encoder cable to connector, Check the connection of the main shaft motor power cable to connector"},
  {"E-13", "Communication fault between the main CPU and the presser motor C...", "Check weather the presser motor is locked, Check the connection of the presser motor cable to the connector"},
  {"E-14", "Presser motor overcurrent error", "Check weather the presser motor is locked, Check the connection of the presser motor cable to the connector"},
  {"E-15", "Presser motor origin retrieval error", "Check weather the presser motor is locked, Check the connection of the origin sensor to the connector"},
  {"E-16", "Crystal oscillator fault", "Change the panel PCB with new one"},
  {"E-17", "ACK error", "Check the connection of the USB flash memory, Check if any file on the USB flash memory is not corrupt, Change the panel PCB with new one"}
};

const int ERROR_COUNT = sizeof(errors) / sizeof(errors[0]);

// Định nghĩa các máy (mã máy và tên)
struct Machine {
  String code;
  String serial;
};

Machine machines[] = {
  {"MC001", "A154-1"},
  {"MC002", "AK-84-1"},
  {"MC003", "AK-118-1"}
  // Thêm các máy khác tương ứng với Odoo của bạn
};

const int MACHINE_COUNT = sizeof(machines) / sizeof(machines[0]);

void setup() {
  Serial.begin(115200);
  
  // Kết nối WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
  
  // Hiển thị menu
  printMenu();
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    // Xử lý lệnh
    if (input == "menu") {
      printMenu();
    } else if (input == "machines") {
      printMachines();
    } else if (input.startsWith("error ")) {
      // Format: error <machine_code> <error_number>
      String params = input.substring(6);
      int spaceIndex = params.indexOf(' ');
      if (spaceIndex > 0) {
        String machineCode = params.substring(0, spaceIndex);
        int errorIndex = params.substring(spaceIndex + 1).toInt() - 1;
        
        if (errorIndex >= 0 && errorIndex < ERROR_COUNT) {
          int machineIndex = getMachineIndex(machineCode);
          if (machineIndex != -1) {
            sendErrorReport(machines[machineIndex], errors[errorIndex]);
          } else {
            Serial.println("Mã máy không hợp lệ! Gõ 'machines' để xem danh sách máy.");
          }
        } else {
          Serial.println("Lỗi không hợp lệ! Vui lòng chọn từ 1 đến " + String(ERROR_COUNT));
        }
      } else {
        Serial.println("Định dạng lệnh không đúng! Sử dụng: error <machine_code> <error_number>");
      }
    } else {
      Serial.println("Lệnh không hợp lệ! Gõ 'menu' để xem hướng dẫn.");
    }
  }
}

void printMenu() {
  Serial.println("\n=== MENU MÔ PHỎNG LỖI ===");
  Serial.println("Gõ 'menu' để hiển thị menu này");
  Serial.println("Gõ 'machines' để xem danh sách máy");
  Serial.println("Gõ 'error <machine_code> <error_number>' để gửi lỗi");
  Serial.println("\nDanh sách lỗi:");
  for (int i = 0; i < ERROR_COUNT; i++) {
    Serial.println(String(i + 1) + ". " + errors[i].code + " - " + errors[i].description);
  }
  Serial.println("========================\n");
}

void printMachines() {
  Serial.println("\n=== DANH SÁCH MÁY ===");
  for (int i = 0; i < MACHINE_COUNT; i++) {
    Serial.println(machines[i].code + " (" + machines[i].serial + ")");
  }
  Serial.println("=====================\n");
}

int getMachineIndex(String code) {
  for (int i = 0; i < MACHINE_COUNT; i++) {
    if (machines[i].code == code) return i;
  }
  return -1;
}

void sendErrorReport(Machine machine, Error error) {
  if(WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(odoo_url);
    http.addHeader("Content-Type", "application/json");
    
    // Tạo JSON payload
    StaticJsonDocument<200> doc;
    doc["error_code"] = error.code;
    doc["description"] = error.description;
    doc["checked"] = error.solution;
    doc["machine_code"] = machine.code;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    Serial.println("\nĐang gửi lỗi cho máy: " + machine.code + " (" + machine.serial + ")");
    Serial.println("Mã lỗi: " + error.code);
    Serial.println("Mô tả: " + error.description);
    Serial.println("Cách khắc phục: " + error.solution);
    
    // Gửi request
    int httpResponseCode = http.POST(jsonString);
    
    if(httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("HTTP Response code: " + String(httpResponseCode));
      Serial.println("Response: " + response);
    } else {
      Serial.println("Lỗi khi gửi HTTP request!");
    }
    
    http.end();
  }
  else {
    Serial.println("Không có kết nối WiFi!");
  }
} 