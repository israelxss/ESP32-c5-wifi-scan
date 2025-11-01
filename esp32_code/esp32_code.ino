#include "WiFi.h"
#include <sstream>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"

#define WIFI_SCAN_TASK_STACK_SIZE 4096
#define WIFI_SCAN_TASK_PRIORITY 1
#define WIFI_SCAN_CORE 0
static SemaphoreHandle_t serialMutex;

static int scan_result = -1;
static bool scan_is_ready = false;
static unsigned long last_scan_time = 0;
const long SCAN_INTERVAL = 3000;

static int current_scan_mode = 0;
static const char* scan_mode_names[] = {"Auto Band"};


void ProcessScanResults() {
    int n = scan_result;

    if (xSemaphoreTake(serialMutex, portMAX_DELAY) == pdTRUE) {
        if (n > 0) {
            Serial.println("SSID,RSSI,CH,Band,MAC,Encryption");

            for (int i = 0; i < n; ++i) {
                std::stringstream output;
                output << "\"" << WiFi.SSID(i).c_str() << "\",";
                output << WiFi.RSSI(i) << ",";
                output << WiFi.channel(i) << ",";

                int channel = WiFi.channel(i);
                if (channel >= 1 && channel <= 14) {
                    output << "2.4GHz" << ",";
                } else if (channel >= 36) {
                    output << "5GHz" << ","; 
                } else {
                    output << "Unknown" << ",";
                }
                
                output << WiFi.BSSIDstr(i).c_str() << ",";

                switch (WiFi.encryptionType(i)) {
                    case WIFI_AUTH_OPEN: output << "Open"; break;
                    case WIFI_AUTH_WEP: output << "WEP"; break;
                    case WIFI_AUTH_WPA_PSK: output << "WPA"; break;
                    case WIFI_AUTH_WPA2_PSK: output << "WPA2"; break;
                    case WIFI_AUTH_WPA_WPA2_PSK: output << "WPA+WPA2"; break;
                    case WIFI_AUTH_WPA2_ENTERPRISE: output << "WPA2-EAP"; break;
                    case WIFI_AUTH_WPA3_PSK: output << "WPA3"; break;
                    case WIFI_AUTH_WPA2_WPA3_PSK: output << "WPA2+WPA3"; break;
                    case WIFI_AUTH_WAPI_PSK: output << "WAPI"; break;
                    default: output << "Unknown";
                }

                Serial.println(output.str().c_str());
            }
        }

        WiFi.scanDelete();
        xSemaphoreGive(serialMutex);
    }
}

void CoreScanTask(void * pvParameters) {
    WiFi.setBandMode(WIFI_BAND_MODE_AUTO);

    while (1) {
        if (scan_result == -1 && millis() - last_scan_time >= SCAN_INTERVAL) { 
            last_scan_time = millis();
            int result = WiFi.scanNetworks(true, false);

            if (result == -1) {
                scan_result = -2; 
            } else if (result >= 0) {
                scan_result = result;
                scan_is_ready = true;
            } else {
                scan_result = -1; 
            }
        }

        if (scan_result == -2) {
            int current_status = WiFi.scanNetworks(false, false);

            if (current_status >= 0) {
                scan_result = current_status;
                scan_is_ready = true;
            } else {

            }
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}


void setup() {
    Serial.begin(115200);
    delay(1000);

    serialMutex = xSemaphoreCreateMutex();

    WiFi.mode(WIFI_STA);
    WiFi.disconnect(true);

    xTaskCreatePinnedToCore(
        CoreScanTask, "WiFiScan", WIFI_SCAN_TASK_STACK_SIZE, NULL, WIFI_SCAN_TASK_PRIORITY, NULL, WIFI_SCAN_CORE
    );
}

void loop() {
    if (scan_is_ready) {
        scan_is_ready = false;
        ProcessScanResults();
        scan_result = -1;
    }
    vTaskDelay(pdMS_TO_TICKS(500));
}