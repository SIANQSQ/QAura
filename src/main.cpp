#include <WiFi.h>
#include <WebServer.h>
#include <FastLED.h>

#define LED_PIN     4       // WS2812B数据引脚
#define LED_COUNT   42      // LED数量
#define PORT        80      // HTTP端口

const char* ssid = "屈圣桥的iPhone";     // 修改为你的WiFi名称
const char* password = "qsq060823"; // 修改为你的WiFi密码

WebServer server(PORT);
CRGB leds[LED_COUNT];

// 灯光模式枚举
enum LightMode { 
  OFF, 
  STATIC_COLOR, 
  RAINBOW, 
  BREATHING, 
  COLOR_WIPE,
  FIRE,
  CONFETTI,
  THEATER_CHASE
};

LightMode currentMode = OFF;
CRGB currentColor = CRGB::White; // 默认白色
uint8_t brightness = 100;        // 默认亮度
uint8_t speed = 50;              // 默认速度
uint8_t hue = 0;                 // 色相值

// 函数前置声明
void Fire2012();
void updateLEDs();



void loop() {
  server.handleClient();
  updateLEDs();
}

void handleRoot() {
  server.send(200, "text/plain", "WS2812B Controller (FastLED) Ready");
}

void handleSetMode() {
  if (server.hasArg("mode")) {
    int mode = server.arg("mode").toInt();
    currentMode = static_cast<LightMode>(mode);
    server.send(200, "text/plain", "Mode set: " + String(mode));
  } else {
    server.send(400, "text/plain", "Missing mode parameter");
  }
}

void handleSetColor() {
  if (server.hasArg("r") && server.hasArg("g") && server.hasArg("b")) {
    uint8_t r = server.arg("r").toInt();
    uint8_t g = server.arg("g").toInt();
    uint8_t b = server.arg("b").toInt();
    currentColor = CRGB(r, g, b);
    server.send(200, "text/plain", "Color set");
  } else {
    server.send(400, "text/plain", "Missing color parameters");
  }
}

void handleSetBrightness() {
  if (server.hasArg("value")) {
    brightness = server.arg("value").toInt();
    FastLED.setBrightness(brightness);
    server.send(200, "text/plain", "Brightness set: " + String(brightness));
  } else {
    server.send(400, "text/plain", "Missing brightness parameter");
  }
}

void handleSetSpeed() {
  if (server.hasArg("value")) {
    speed = server.arg("value").toInt();
    server.send(200, "text/plain", "Speed set: " + String(speed));
  } else {
    server.send(400, "text/plain", "Missing speed parameter");
  }
}

// 火焰效果函数
void Fire2012() {
  // COOLING: 冷却速率 (0-100)
  // SPARKING: 火花率 (0-100)
  #define COOLING  55
  #define SPARKING 120
  
  static byte heat[LED_COUNT];
  
  // Step 1: 冷却每个单元
  for (int i = 0; i < LED_COUNT; i++) {
    heat[i] = qsub8(heat[i], random8(0, ((COOLING * 10) / LED_COUNT) + 2));
  }
  
  // Step 2: 从底部向上传播热量
  for (int k = LED_COUNT - 1; k >= 2; k--) {
    heat[k] = (heat[k - 1] + heat[k - 2] + heat[k - 2]) / 3;
  }
  
  // Step 3: 随机添加新火花
  if (random8() < SPARKING) {
    int y = random8(7);
    heat[y] = qadd8(heat[y], random8(160, 255));
  }
  
  // Step 4: 将热量映射到LED颜色
  for (int j = 0; j < LED_COUNT; j++) {
    CRGB color = HeatColor(heat[j]);
    int pixelnumber = j;
    leds[pixelnumber] = color;
  }
}

void updateLEDs() {
  static unsigned long lastUpdate = 0;
  unsigned long now = millis();
  static uint8_t offset = 0;
  
  // 根据速度参数控制更新频率
  if (now - lastUpdate < map(speed, 0, 100, 50, 5)) {
    return;
  }
  lastUpdate = now;
  
  switch(currentMode) {
    case OFF:
      FastLED.clear();
      FastLED.show();
      break;
      
    case STATIC_COLOR:
      fill_solid(leds, LED_COUNT, currentColor);
      FastLED.show();
      break;
      
    case RAINBOW:
      // 彩虹效果
      fill_rainbow(leds, LED_COUNT, hue++);
      FastLED.show();
      break;
      
    case BREATHING: {
      // 用大括号创建局部作用域
      static uint8_t breathVal = 0;
      static bool breathDir = true;
      
      CRGB breathColor = currentColor;
      breathColor.fadeLightBy(255 - breathVal);
      
      fill_solid(leds, LED_COUNT, breathColor);
      FastLED.show();
      
      if(breathDir) {
        breathVal++;
        if(breathVal >= 254) breathDir = false;
      } else {
        breathVal--;
        if(breathVal <= 1) breathDir = true;
      }
      break;
    }
      
    case COLOR_WIPE: {
      // 颜色擦除效果
      static uint8_t wipePos = 0;
      leds[wipePos] = currentColor;
      FastLED.show();
      wipePos = (wipePos + 1) % LED_COUNT;
      fadeToBlackBy(leds, LED_COUNT, 10);
      break;
    }
      
    case FIRE:
      // 火焰效果
      Fire2012();
      FastLED.show();
      break;
      
    case CONFETTI: {
      // 五彩纸屑效果
      fadeToBlackBy(leds, LED_COUNT, 10);
      int pos = random16(LED_COUNT);
      leds[pos] = CHSV(random8(), 200, 255);
      FastLED.show();
      break;
    }
      
    case THEATER_CHASE: {
      // 剧院追逐效果
      static uint8_t chaseOffset = 0;
      for (int i = 0; i < LED_COUNT; i++) {
        if ((i + chaseOffset) % 3 == 0) {
          leds[i] = currentColor;
        } else {
          leds[i] = CRGB::Black;
        }
      }
      FastLED.show();
      chaseOffset = (chaseOffset + 1) % 3;
      break;
    }
  }
}

void setup() {
  Serial.begin(115200);
  FastLED.addLeds<WS2812B, LED_PIN, GRB>(leds, LED_COUNT);
  FastLED.setBrightness(brightness);
  FastLED.show(); // 初始化LED为关闭状态
  
  // 连接WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // 设置HTTP路由
  server.on("/", handleRoot);
  server.on("/set_mode", handleSetMode);
  server.on("/set_color", handleSetColor);
  server.on("/set_brightness", handleSetBrightness);
  server.on("/set_speed", handleSetSpeed);
  
  server.begin();
  Serial.println("HTTP server started");
}