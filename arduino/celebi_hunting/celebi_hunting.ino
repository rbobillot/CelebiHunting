/*

  ShinyCelebiPokemonCrystalVC.ino

  This program is meant to shiny hunt Celebi
  in Pokemon Crystal VC (3DS).
  
  As I counld't RNG abuse him (we don't have enough data for 2G yet),
  I needed to soft reset him.
  This task is quite repetitive, I did it many times for other generations.
  But I got a life, a whole lotta work, and I found out in my 30's,
  that sleeping is awesome (that's why I first got into RNG abuse).

  Hense, my choice was to create a small robot, doing the job for me.

  I first wanted to use a color sensor on the screen,
  and wire my 2DS buttons to an Arduino.
  But, the sensor was kinda broken... plus, this 2DS (with Pokemon Transporter and Bank),
  is my only 2DS/3DS, and I didn't want to make a mess (not sure if the buttons wanted voltage was 1.8V or less or more).

  Therefore, I came up with the idea of using two Servos to push the buttons / touch screen,
  and a webcam detecting the Celebi color (using Python + OpenCV).

*/

#include <Arduino.h>
#include <U8x8lib.h>
#include <Servo.h>

#ifdef U8X8_HAVE_HW_SPI
#include <SPI.h>
#endif
U8X8_SSD1306_128X64_NONAME_HW_I2C u8x8(/* reset=*/ U8X8_PIN_NONE);

Servo touch_screen_servo;
Servo button_a_servo;

int reset_counter = 3900;   // simple index used to increment and display the number of Soft Resets
bool shiny_found = false;   // a flag eventually indicating that shiny Celebi (used to start / pause the program)
bool error_occured = false; // a flag indicating that somthing went wrong (example: Arduino not found while Python tries to communicate)

// Display functions
void show_main_menu();
void show_status(const char *line_1, const char *line_2);

// Servo functions
void click(const char *button);
void click_loop(const char *button, const int times, const int interval /* millis */);
void soft_reset();

// Program logic
const char *check_if_shiny();
void hunt_celebi();

////////////////////////////
//    CELEBI HUNTING
////////////////////////////

void setup(void)
{
  // prepare Servos
  touch_screen_servo.attach(8);
  button_a_servo.attach(9);

  // prepare LCD display
  u8x8.begin();
  u8x8.setPowerSave(0);

  // prepare communication between Arduino and Python program
  Serial.begin(9600);
  Serial.setTimeout(1);
}

void loop(void)
{
  u8x8.setFont(u8x8_font_chroma48medium8_r);
  Serial.flush();

  /*
    First needed to init the Servos
    At their first call, they move by 45 degrees angle (looks like I cannot avoid it),
    then the angle goes back to 0
  */
  touch_screen_servo.write(0);
  button_a_servo.write(0);
  delay(300);

  if (!shiny_found && !error_occured) {
    show_main_menu();
    hunt_celebi();
  }
}

void show_main_menu() {
  u8x8.drawString(0, 2, "Resets:");
  u8x8.drawString(8, 2, String(reset_counter).c_str());
  u8x8.drawString(0, 3, "");

  u8x8.drawString(0, 4, "Hunting...");
}

// Indicates wether the program is still hunting Celebi, or has found it
void show_status(const char *line_1, const char *line_2) {
  u8x8.clearLine(4);
  u8x8.clearLine(5);
  u8x8.drawString(0, 4, line_1);
  if (strlen(line_2)) {
    u8x8.drawString(0, 5, line_2);
  }
}

/*
  Rotates the needed servo, to its desired angle, waits for 300ms
  and rotates it back to 0.

  Each servo is placed beside a button: touch screen, or button 'A'
  As the button's top is above the touch 3DS shield, and touch screen's under,
  the angle needed to click each one, will be different
*/
void click(const char *button) {
  Servo servo;
  int rotation;

  if ("touch_screen" == button) {
    servo = touch_screen_servo;
    rotation = 137;
  } else if ("button_a" == button) {
    servo = button_a_servo;
    rotation = 112;
  } else {
    return ;
  }

  servo.write(rotation);
  delay(300);
  servo.write(0);
}

/*
  Click the desired button N times, spacing each click with a specific interval
*/
void click_loop(const char *button, const int times, const int interval /* millis */) {
  for (int i = 0; i < times; ++i) {
    click(button);
    delay(interval);
  }
}

void soft_reset() {
  click_loop("touch_screen", 2, 800);
  click("button_a");

  ++reset_counter;
}
/*
  That's where the Arduino, and the Python+OpenCV program do communicate, through Serial.
  - Arduino asks for Python program to look for Celebi
  - If the Python program detects Celebi, it sends back a message, telling if the Celebi was shiny or not
  - Arduino waits for the Python program message
  - if Arduino reads no message, it does nothing (avoiding an unwanted soft reset)
*/
const char *check_if_shiny() {
  String readString;

  Serial.println("DETECT"); // asks for Python program, to try to detect Celebi
  show_status("Analyze", "3DS screen...");
  delay(1000); // wait for Python program to detect Celebi

  while (!Serial.available()); // wait for Serial to get a message

  String str = Serial.readString();

  if (str.startsWith("NORMAL"))
    return "NORMAL";
  else if (str.startsWith("SHINY"))
    return "SHINY";
  else
    return "ERROR";
}

/*
  This function is a simple routine,
  it soft resets the 3DS VC game (through touch screen),
  and presses A a few times (skipping game intro, and Celebi event dialogs),
  until the Python+OpenCV program detects a shiny Celebi
*/
void hunt_celebi() {
  u8x8.clearDisplay();
  u8x8.drawString(0, 2, "Resets:");
  u8x8.drawString(0, 4, "Hunting...");

  while (true) {
    u8x8.drawString(8, 2, String(reset_counter).c_str());

    soft_reset();

    show_status("Game start...", "");
    delay(5000);
    
    show_status("Skipping", "game intro...");
    click_loop("button_a", 4, 800);

    show_status("Celebi event...", "");
    click_loop("button_a", 8, 700);

    click("button_a");
    show_status("Waiting for", "Celebi...");

    delay(17000); // wait till the end of the Celebi animation

    const char *shiny_status = check_if_shiny();

    if ("SHINY" == shiny_status) {
      show_status("SHINY FOUND !!!", "");
      shiny_found = true;
      return ;
    } else if ("ERROR" == shiny_status) {
      show_status("ERROR", "");
      error_occured = true; // will cause the program to pause
      return ;
    }

  }
}
