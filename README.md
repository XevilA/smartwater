#### 1\. **การเชื่อมต่อแบบ Dual Mode**

-   ✅ รองรับ Serial (USB) และ WiFi
-   ✅ Auto-detect Serial ports
-   ✅ เปลี่ยนการเชื่อมต่อได้ง่าย

#### 2\. **Manual Control ที่ใช้งานง่าย**

-   ✅ ปุ่มใหญ่ สีสันสวยงาม
-   ✅ แสดง Progress bar และเวลาคงเหลือ
-   ✅ ตั้งเวลารดน้ำเป็นนาที
-   ✅ คำนวณปริมาณน้ำอัตโนมัติ

#### 3\. **ระบบตั้งเวลาอัตโนมัติ**

-   ✅ ตั้งได้หลายตารางเวลา
-   ✅ เลือกวันที่ต้องการรดน้ำ
-   ✅ เลือกโหมดน้ำ/น้ำ+ปุ๋ย
-   ✅ Enable/Disable แต่ละตาราง
-   ✅ Repeat รายสัปดาห์

#### 4\. **ประวัติการรดน้ำ**

-   ✅ บันทึกทุกครั้งที่รดน้ำ
-   ✅ Filter ตามวัน/สัปดาห์/เดือน
-   ✅ Export เป็น CSV
-   ✅ แสดงสถิติการใช้น้ำ

#### 5\. **การตั้งค่าระบบ**

-   ✅ Flow rate (ลิตร/นาที)
-   ✅ ระยะเวลาเริ่มต้น
-   ✅ ระยะเวลาสูงสุด (Safety)
-   ✅ Auto stop เมื่อขาดการเชื่อมต่อ

#### 6\. **UI ที่สวยงาม**

-   ✅ Tab interface
-   ✅ Icons และสีสันที่เข้าใจง่าย
-   ✅ Real-time clock
-   ✅ System log แบบ colored
-   ✅ Responsive design

### 🌐 ฟีเจอร์ของ ESP32:

#### 1\. **WiFi Features**

-   ✅ Access Point mode สำหรับตั้งค่าครั้งแรก
-   ✅ เชื่อมต่อ WiFi ที่มีอยู่ได้
-   ✅ Web interface สำหรับควบคุม
-   ✅ บันทึกการตั้งค่า WiFi ใน Flash

#### 2\. **Web Interface**

-   ✅ ควบคุมผ่านมือถือ/คอมพิวเตอร์
-   ✅ ดูสถานะระบบ Real-time
-   ✅ ตั้งค่า WiFi ผ่านหน้าเว็บ
-   ✅ Responsive design

#### 3\. **การเชื่อมต่อ**

-   ✅ Serial command (9600 baud)
-   ✅ TCP Socket (Port 80)
-   ✅ HTTP REST API
-   ✅ รองรับหลาย client พร้อมกัน

### 📖 วิธีการติดตั้งและใช้งาน:

#### สำหรับ ESP32:

1.  **Upload โค้ดไปยัง ESP32**
2.  **การเชื่อมต่อครั้งแรก:**
    -   ESP32 จะสร้าง WiFi AP: "ESP32_Irrigation"
    -   Password: "12345678"
    -   เข้า <http://192.168.4.1> เพื่อตั้งค่า

#### สำหรับ Python GUI:

1.  **ติดตั้ง Dependencies:**

bash

```
pip install PyQt6 pyserial
```

1.  **รันโปรแกรม:**

bash

```
python enhanced_irrigation_gui.py
```

1.  **การเชื่อมต่อ:**
    -   คลิก "Connect"
    -   เลือก Serial หรือ WiFi
    -   Serial: เลือก COM port
    -   WiFi: ใส่ IP address ของ ESP32

### 💡 การใช้งานพื้นฐาน:

#### Manual Mode:

1.  เลือกโหมด (น้ำ/น้ำ+ปุ๋ย)
2.  ตั้งเวลา (นาที)
3.  กด Start Watering
4.  ดู Progress และเวลาคงเหลือ

#### Auto Mode:

1.  ตั้งเวลาเริ่ม
2.  ตั้งระยะเวลา
3.  เลือกวันที่ต้องการ
4.  เลือกโหมด
5.  กด Add Schedule

### 🔧 ฟีเจอร์ขั้นสูง:

1.  **Test System** - ทดสอบวาล์วและปั๊ม
2.  **Export History** - ส่งออกข้อมูลเพื่อวิเคราะห์
3.  **Multi-Schedule** - ตั้งเวลาได้หลายช่วง
4.  **Remote Control** - ควบคุมผ่าน WiFi จากที่ไหนก็ได้ในเครือข่าย
5.  **Auto-Save** - บันทึกการตั้งค่าและตารางเวลาอัตโนมัติ
