#include <WiFi.h>
#include <WebServer.h>
#include <FastLED.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>


#define LED1_PIN     4       // WS2812B数据引脚    
#define LED2_PIN     18 
#define LED3_PIN     19
#define LED4_PIN     21 
#define LED5_PIN     22
#define LED6_PIN     23
#define LED7_PIN     25
#define LED8_PIN     26

#define PORT        80      // HTTP端口

#define LED1_COUNT 55
#define LED2_COUNT 55
#define LED3_COUNT 55
#define LED4_COUNT 55
#define LED5_COUNT 55
#define LED6_COUNT 55
#define LED7_COUNT 55
#define LED8_COUNT 55
uint16_t LED_COUNT[9] = {0,LED1_COUNT,LED2_COUNT,LED3_COUNT,LED4_COUNT,LED5_COUNT,LED6_COUNT,LED7_COUNT,LED8_COUNT};
int8_t LED_DeltaHUE[9] = {0,1,-1,1,1,1,1,1,1};

// 定义连接到MAX9812输出的ADC引脚
#define MAX9812_OUTPUT_PIN 34  // ESP32的ADC1_CH6引脚

// 采样参数
#define SAMPLE_RATE 1000       // 采样率(Hz)
#define SAMPLES_PER_READ 10    // 每次读取的样本数

const char* ssid = "屈圣桥的iPhone";     // 修改为你的WiFi名称
const char* password = "qsq060823"; // 修改为你的WiFi密码



WebServer server(PORT);
CRGB LED1[LED1_COUNT];
CRGB LED2[LED2_COUNT];
CRGB LED3[LED3_COUNT];
CRGB LED4[LED4_COUNT];
CRGB LED5[LED5_COUNT];
CRGB LED6[LED6_COUNT];
CRGB LED7[LED7_COUNT];
CRGB LED8[LED8_COUNT];
// 灯光模式枚举
enum LightMode { 
  OFF, 
  STATIC_COLOR, 
  RAINBOW, 
  BREATHING, 
  COLOR_WIPE,
  VOLUM_MAP,
  CONFETTI,
  THEATER_CHASE
};

LightMode currentMode = VOLUM_MAP;
CRGB currentColor = CRGB::White; // 默认白色
uint8_t brightness = 100;        // 默认亮度
uint8_t speed = 50;              // 默认速度
uint8_t hue[9] = {0};                 // 色相值
uint8_t target = 1;
uint8_t LEDMode[9]={2,2,2,2,2,2,2,2,2};
uint16_t MIDLED[9]={0,1+LED1_COUNT/2,1+LED2_COUNT/2,1+LED3_COUNT/2,1+LED4_COUNT/2,1+LED5_COUNT/2,1+LED6_COUNT/2,1+LED7_COUNT/2,1+LED8_COUNT/2};
// 函数前置声明
void updateLEDs();
void handleSetTarget();




void handleRoot() {
  server.send(200, "text/plain", "WS2812B Controller (FastLED) Ready");
}

void handleSetMode() {
  handleSetTarget();
  if (server.hasArg("mode")) {
    int mode = server.arg("mode").toInt();
    LEDMode[target] = static_cast<LightMode>(mode);
    server.send(200, "text/plain", "Mode set: " + String(mode));
  } else {
    server.send(400, "text/plain", "Missing mode parameter");
  }
}

void handleSetColor() {
  handleSetTarget();
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

void handleSetTarget() {
  if (server.hasArg("target")) {
    target = server.arg("target").toInt();
    server.send(200, "text/plain", "Target set: " + String(target));
  } else {
    server.send(400, "text/plain", "Missing target parameter");
  }
}

void updateLED(CRGB* led,uint8_t LEDlabel)
{
  switch(LEDMode[LEDlabel]) 
  {
    case OFF:
      fill_solid(led, LED_COUNT[LEDlabel], CRGB::Black);
      break;
      
    case STATIC_COLOR:
      fill_solid(led, LED_COUNT[LEDlabel], currentColor);
      break;
      
    case RAINBOW:
      // 彩虹效果
      fill_rainbow(led, LED_COUNT[LEDlabel], hue[LEDlabel]++);
      break;
      
    case BREATHING: {
      // 用大括号创建局部作用域
      static uint8_t breathVal = 0;
      static bool breathDir = true;
      
      CRGB breathColor = currentColor;
      breathColor.fadeLightBy(255 - breathVal);
      
      fill_solid(LED1, LED1_COUNT, breathColor);
      fill_solid(LED2, LED2_COUNT, breathColor);
      
      if(breathDir) {
        breathVal++;
        if(breathVal >= 254) breathDir = false;
      } else {
        breathVal--;
        if(breathVal <= 1) breathDir = true;
      }
      break;
    }
    case VOLUM_MAP:
      {
              // 读取多个样本并计算平均值，减少噪声影响
        int total = 0;
        for (int i = 0; i < SAMPLES_PER_READ; i++) {
          total += analogRead(MAX9812_OUTPUT_PIN);
          delayMicroseconds(1000000 / SAMPLE_RATE);  // 控制采样率
        }
        
        int averageValue = total / SAMPLES_PER_READ;
        
        // 将ADC值转换为电压 (假设参考电压为3.3V)
        int voltage = averageValue * (54 / 4095.0);
        Serial.print(voltage);
        FastLED.clear();
        fill_rainbow(LED2, voltage, hue[LEDlabel]);
        
        // 短延迟，控制输出速率
        delay(50);
        break;
      }

}
}

void updateLEDs() 
{
  static unsigned long lastUpdate = 0;
  unsigned long now = millis();
  static uint8_t offset = 0;
  
  // 根据速度参数控制更新频率
  if (now - lastUpdate < map(speed, 0, 100, 50, 5)) {
    return;
  }
  lastUpdate = now;
  updateLED(LED1,1);
  updateLED(LED2,2);
  updateLED(LED3,3);
  updateLED(LED4,4);
  updateLED(LED5,5);
  updateLED(LED6,6);
  updateLED(LED7,7);
  updateLED(LED8,8);
  FastLED.show();
  }





void bootEffect() 
{
  static uint8_t rl=55;
  uint16_t maxled = 0;
  for(int n =1;n<=8;n++)
  {
    maxled=maxled>LED_COUNT[n] ? maxled : LED_COUNT[n]; 
  }
  for(int t=0;t<=1;t++)
  {
    for (int i=maxled;i>=0;i--)
    {
      FastLED.clear();
      if(i<LED_COUNT[1])LED1[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[1])LED1[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[1])LED1[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[1])LED1[i+3]=CRGB(7,0,0);
      if(i<LED_COUNT[2])LED2[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[2])LED2[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[2])LED2[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[2])LED2[i+3]=CRGB(7,0,0);
      if(i<LED_COUNT[3])LED3[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[3])LED3[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[3])LED3[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[3])LED3[i+3]=CRGB(7,0,0);
      if(i<LED_COUNT[4])LED4[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[4])LED4[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[4])LED4[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[4])LED4[i+3]=CRGB(7,0,0);
      if(i<LED_COUNT[5])LED4[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[5])LED4[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[5])LED4[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[5])LED4[i+3]=CRGB(7,0,0);
      if(i<LED_COUNT[6])LED4[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[6])LED4[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[6])LED4[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[6])LED4[i+3]=CRGB(7,0,0);
      if(i<LED_COUNT[7])LED4[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[7])LED4[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[7])LED4[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[7])LED4[i+3]=CRGB(7,0,0);
      if(i<LED_COUNT[8])LED4[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[8])LED4[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[8])LED4[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[8])LED4[i+3]=CRGB(7,0,0);
      FastLED.show();
      delay(8);
    }
  }
  FastLED.clear();
  FastLED.show();
  delay(500);
  for (int i=maxled/2;i>=0;i--)
  {
    for(int n=1;n<=8;n++)
    {
      if (MIDLED[n]>=1) MIDLED[n]--;
    }
    LED1[MIDLED[1]]=CRGB::Red;
    LED1[LED_COUNT[1]-MIDLED[1]]=CRGB::Red;
    LED2[MIDLED[2]]=CRGB::Red;
    LED2[LED_COUNT[2]-MIDLED[2]]=CRGB::Red;
    LED3[MIDLED[3]]=CRGB::Red;
    LED3[LED_COUNT[3]-MIDLED[3]]=CRGB::Red;
    LED4[MIDLED[4]]=CRGB::Red;
    LED4[LED_COUNT[4]-MIDLED[4]]=CRGB::Red;
    LED5[MIDLED[5]]=CRGB::Red;
    LED5[LED_COUNT[5]-MIDLED[5]]=CRGB::Red;
    LED6[MIDLED[6]]=CRGB::Red;
    LED6[LED_COUNT[6]-MIDLED[6]]=CRGB::Red;
    LED7[MIDLED[7]]=CRGB::Red;
    LED7[LED_COUNT[7]-MIDLED[7]]=CRGB::Red;
    LED8[MIDLED[8]]=CRGB::Red;
    LED8[LED_COUNT[8]-MIDLED[8]]=CRGB::Red;
    FastLED.show();
    delay(60);
  }
  FastLED.clear();
}


void setup() {
  Serial.begin(115200);
  FastLED.addLeds<WS2812B, LED1_PIN, GRB>(LED1, LED1_COUNT);
  FastLED.addLeds<WS2812B, LED2_PIN, GRB>(LED2, LED2_COUNT);
  FastLED.addLeds<WS2812B, LED3_PIN, GRB>(LED3, LED3_COUNT);
  FastLED.addLeds<WS2812B, LED4_PIN, GRB>(LED4, LED4_COUNT);
  FastLED.addLeds<WS2812B, LED5_PIN, GRB>(LED5, LED5_COUNT);
  FastLED.addLeds<WS2812B, LED6_PIN, GRB>(LED6, LED6_COUNT);
  FastLED.addLeds<WS2812B, LED7_PIN, GRB>(LED7, LED7_COUNT);
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
  server.on("/set_target",handleSetTarget);
  server.on("/set_mode", handleSetMode);
  server.on("/set_color", handleSetColor);
  server.on("/set_brightness", handleSetBrightness);
  server.on("/set_speed", handleSetSpeed);
  
  server.begin();
  Serial.println("HTTP server started");




  // 配置ADC
  analogSetAttenuation(ADC_11db);  // 设置衰减，可测量更大范围的电压
  analogSetWidth(12);              // 设置ADC分辨率为12位(0-4095)
  
  Serial.println("MAX9812 ADC读取示例开始");
  Serial.print("采样率: ");
  Serial.print(SAMPLE_RATE);
  Serial.println(" Hz");
  
  bootEffect();
}

void loop() {
  server.handleClient();
  updateLEDs();
}

