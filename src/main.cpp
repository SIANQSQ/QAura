#include <WiFi.h>
#include <WebServer.h>
#include <FastLED.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
//#include <>


#define LED1_PIN     4       // WS2812B数据引脚    
#define LED2_PIN     18 
#define LED3_PIN     19
#define LED4_PIN     21 
#define LED5_PIN     22
#define LED6_PIN     23
#define LED7_PIN     25
#define LED8_PIN     26

#define PORT        80      // HTTP端口

#define LED1_COUNT 53  //桌子下
#define LED2_COUNT 22  //显示器下
#define LED3_COUNT 28  //显示器上
#define LED4_COUNT 39  //桌子上  
#define LED5_COUNT 33  //桌子侧面
#define LED6_COUNT 0
#define LED7_COUNT 0
#define LED8_COUNT 0
uint16_t LED_COUNT[9] = {0,LED1_COUNT,LED2_COUNT,LED3_COUNT,LED4_COUNT,LED5_COUNT,LED6_COUNT,LED7_COUNT,LED8_COUNT};
int8_t LED_DeltaHUE[9] = {0,1,-1,1,1,1,1,1,1}; //色相变化步长，用于设置彩虹流动方向

CRGB LED_Color[9] = {CRGB::Black,CRGB::Red,CRGB::Green,CRGB::Blue,CRGB::White,CRGB::Yellow,CRGB::Cyan,CRGB::Purple,CRGB::Orange}; //各灯带默认静态颜色
// 定义连接到MAX9812输出的ADC引脚
#define MAX9812_OUTPUT_PIN 34  // ESP32的ADC1_CH6引脚

// 采样参数
#define SAMPLE_RATE 1000       // 采样率(Hz)
#define SAMPLES_PER_READ 10    // 每次读取的样本数

SemaphoreHandle_t ledMutex; 

const char* ssid = "甘雨软糖";     // 修改为你的WiFi名称
const char* password = "qsq20060823"; // 修改为你的WiFi密码



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
  VOLUM_MAP,
  SCREEN
};

LightMode currentMode = VOLUM_MAP;
CRGB currentColor = CRGB::White; // 默认白色
CRGB SCREEN_Color = CRGB::Black;
CRGB AUDIO_Color = CRGB::Black;
uint8_t brightness = 100;        // 默认亮度
uint8_t speed = 50;              // 默认速度
uint8_t hue[9] = {0};                 // 色相值
uint8_t target = 1;
LightMode LED_Mode[9] = {OFF,RAINBOW,RAINBOW,RAINBOW,RAINBOW,RAINBOW,RAINBOW,RAINBOW,RAINBOW}; //各灯带默认模式
//LightMode LED_Mode[9] = {OFF,SCREEN,SCREEN,SCREEN,SCREEN,SCREEN,SCREEN,SCREEN,SCREEN};
uint16_t MIDLED[9]={0,1+LED1_COUNT/2,1+LED2_COUNT/2,1+LED3_COUNT/2,1+LED4_COUNT/2,1+LED5_COUNT/2,1+LED6_COUNT/2,1+LED7_COUNT/2,1+LED8_COUNT/2};
float Peak = 0.0;  // 记录当前音量峰值
bool Use_Audio_Specific_Color = false;
void updateLEDs();


void parseSerialCommand() {
  if (Serial.available() > 0) {
    Serial.println("Listening for serial commands...");
    String input = Serial.readStringUntil('\n'); // 读取直到换行符
    input.trim(); // 去除首尾空白字符
    
    int mode, r, g, b;
    float peak; // 添加peak变量
    if (sscanf(input.c_str(), "%d,%d,%d,%d,%f", &mode, &r, &g, &b, &peak) == 5) {
      // 成功解析了4个整数
      //Serial.printf("解析成功: mode=%d, r=%d, g=%d, b=%d, peak=%f\n", mode, r, g, b, peak);

      // 在这里使用解析后的值
      if(mode == 1)
      {
        SCREEN_Color=CRGB(r, g, b);
      }
      else if(mode == 2)
      {
        if(r != -1 && g != -1 && b != -1) // 如果r, g, b不是-1，则更新currentColor
        {
          AUDIO_Color = CRGB(r, g, b);
          Use_Audio_Specific_Color = true;
        }   
        else
        {
          Use_Audio_Specific_Color = false;
        }
        Peak = peak;
      }
    } 
    else 
    {
      Serial.println("解析失败，格式应为: mode,r,g,b");
    }
  }
}


void handleRoot() {
  server.send(200, "text/plain", "Welcome to QAura");
}

void handleSetMode() {
  if (server.hasArg("mode")&&server.hasArg("channel")) {
    if (xSemaphoreTake(ledMutex, 100 / portTICK_PERIOD_MS) == pdTRUE) {
    int mode = server.arg("mode").toInt();
    if(server.hasArg("sync"))
    {
        int sync = server.arg("sync").toInt();
        if(sync == 1)
        {
            for(int i=1;i<=8;i++)
            {
                LED_Mode[i] = static_cast<LightMode>(mode);
            }
        }
    }
    int channel = server.arg("channel").toInt();
    LED_Mode[channel] = static_cast<LightMode>(mode);
    xSemaphoreGive(ledMutex);  // 释放锁
    server.send(200, "text/plain", "Mode set: " + String(mode));
    } else {
      server.send(500, "text/plain", "Failed to get lock");
    }
  } else {
    server.send(400, "text/plain", "Missing mode parameter");
  }
}

void handleSetColor() {
  if (server.hasArg("channel") && server.hasArg("r") && server.hasArg("g") && server.hasArg("b") && server.hasArg("sync")) {
    if (xSemaphoreTake(ledMutex, 100 / portTICK_PERIOD_MS) == pdTRUE) {
    uint8_t r = server.arg("r").toInt();
    uint8_t g = server.arg("g").toInt();
    uint8_t b = server.arg("b").toInt();
    uint8_t sync = server.arg("sync").toInt(); //
    Serial.print(sync);
    if(sync == 1)
    {
        for(int i=1;i<=8;i++)
        {
            LED_Mode[i] = STATIC_COLOR;
            LED_Color[i] = CRGB(r, g, b);
            Serial.print("change mode");
        }
    }
    else
    {
        int channel = server.arg("channel").toInt();
        LED_Color[channel] = CRGB(r, g, b);
    }
    xSemaphoreGive(ledMutex);  // 释放锁
    server.send(200, "text/plain", "Color set");
    } else {
      server.send(500, "text/plain", "Failed to get lock");
    }
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

void updateLED(CRGB* led, uint8_t LEDlabel) {
  if (xSemaphoreTake(ledMutex, 100 / portTICK_PERIOD_MS) == pdTRUE) {  // 获取锁
    switch (LED_Mode[LEDlabel]) {
      case OFF:
        fill_solid(led, LED_COUNT[LEDlabel], CRGB::Black);
        break;
      case STATIC_COLOR:
        fill_solid(led, LED_COUNT[LEDlabel], LED_Color[LEDlabel]);
        break;
      case RAINBOW:
        fill_rainbow(led, LED_COUNT[LEDlabel], hue[LEDlabel]++);
        break;
      case BREATHING: {
        static uint8_t breathVal = 0;
        static bool breathDir = true;
        CRGB breathColor = currentColor;
        breathColor.fadeLightBy(255 - breathVal);
        fill_solid(led, LED_COUNT[LEDlabel], breathColor);
        if (breathDir) {
          breathVal++;
          if (breathVal >= 254) breathDir = false;
        } else {
          breathVal--;
          if (breathVal <= 1) breathDir = true;
        }
        break;
      }
      case VOLUM_MAP:
        fill_solid(led, LED_COUNT[LEDlabel], CRGB::Black);
        if(Use_Audio_Specific_Color){fill_solid(led, Peak*LED_COUNT[LEDlabel], AUDIO_Color);}
        else{fill_rainbow(led,floor(Peak*LED_COUNT[LEDlabel]), hue[LEDlabel]++);}
        break;
      case SCREEN:
        fill_solid(led, LED_COUNT[LEDlabel], SCREEN_Color);  // 读取SCREEN_Color
        break;
    }
    xSemaphoreGive(ledMutex);  // 释放锁
  }
}

void Server_Task(void *pvParameters) {
  for (;;) {
    server.handleClient();
    vTaskDelay(1);
  }
}

void WIFI_Task(void *pvParameters)
{
  // 连接WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  
  server.on("/", handleRoot);
  server.on("/set_mode", handleSetMode);
  server.on("/set_color", handleSetColor);
  server.on("/set_brightness", handleSetBrightness);
  server.on("/set_speed", handleSetSpeed);
  
  server.begin();
  Serial.println("HTTP server started");
  xTaskCreate(Server_Task, "Server_Task", 4096, NULL, 1, NULL);
  vTaskDelete(NULL);
}

void updateLEDs() 
{
  static unsigned long lastUpdate = 0;
  unsigned long now = millis();
  static uint8_t offset = 0;
  if (now - lastUpdate < map(speed, 0, 100, 50, 5)) {
    return;
  }
  if(LED_Mode[1]==SCREEN || LED_Mode[2]==SCREEN || LED_Mode[3]==SCREEN || LED_Mode[4]==SCREEN || LED_Mode[5]==SCREEN || LED_Mode[6]==SCREEN || LED_Mode[7]==SCREEN || LED_Mode[8]==SCREEN)
  {
    parseSerialCommand();
  }
  if(LED_Mode[1]==VOLUM_MAP || LED_Mode[2]==VOLUM_MAP || LED_Mode[3]==VOLUM_MAP || LED_Mode[4]==VOLUM_MAP || LED_Mode[5]==VOLUM_MAP || LED_Mode[6]==VOLUM_MAP || LED_Mode[7]==VOLUM_MAP || LED_Mode[8]==VOLUM_MAP)
  {
    parseSerialCommand();
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
      if(i<LED_COUNT[5])LED5[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[5])LED5[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[5])LED5[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[5])LED5[i+3]=CRGB(7,0,0);
      if(i<LED_COUNT[6])LED6[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[6])LED6[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[6])LED6[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[6])LED6[i+3]=CRGB(7,0,0);
      if(i<LED_COUNT[7])LED7[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[7])LED7[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[7])LED7[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[7])LED7[i+3]=CRGB(7,0,0);
      if(i<LED_COUNT[8])LED8[i]=CRGB(7,0,0);
      if(i+1<LED_COUNT[8])LED8[i+1]=CRGB::Red;
      if(i+2<LED_COUNT[8])LED8[i+2]=CRGB::Red;
      if(i+3<LED_COUNT[8])LED8[i+3]=CRGB(7,0,0);
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
      if (MIDLED[n]>1) MIDLED[n]--;
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

void LED_Task(void *pvParameters) {
  for (;;) {
    updateLEDs();
    vTaskDelay(1);
  }
}
void setup() {
  Serial.begin(115200);
  ledMutex = xSemaphoreCreateMutex();
  if (ledMutex == NULL) {
    Serial.println("互斥锁创建失败！系统可能内存不足");
  }

  FastLED.addLeds<WS2812B, LED1_PIN, GRB>(LED1, LED1_COUNT);
  FastLED.addLeds<WS2812B, LED2_PIN, GRB>(LED2, LED2_COUNT);
  FastLED.addLeds<WS2812B, LED3_PIN, GRB>(LED3, LED3_COUNT);
  FastLED.addLeds<WS2812B, LED4_PIN, GRB>(LED4, LED4_COUNT);
  FastLED.addLeds<WS2812B, LED5_PIN, GRB>(LED5, LED5_COUNT);
  //FastLED.addLeds<WS2812B, LED6_PIN, GRB>(LED6, LED6_COUNT);
  //FastLED.addLeds<WS2812B, LED7_PIN, GRB>(LED7, LED7_COUNT);
  FastLED.setBrightness(brightness);
  FastLED.show();
  


  // 设置HTTP路由
 

//   analogSetAttenuation(ADC_11db);  // 设置衰减
//   analogSetWidth(12);              // 设置ADC分辨率为12位
  
  // Serial.print("采样率: ");
  // Serial.print(SAMPLE_RATE);
  // Serial.println(" Hz");
  bootEffect();
  xTaskCreatePinnedToCore(WIFI_Task, "WIFI_Task", 2048, NULL, 1, NULL, 0);
  
  xTaskCreatePinnedToCore(LED_Task, "LED_Task", 4096, NULL, 1, NULL, 0);
}



void loop() 
{  
  //server.handleClient();
  //updateLEDs();
  
}

 