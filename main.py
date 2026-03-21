import threading
import queue
import serial
import time


class SerialReader(threading.Thread):
    def __init__(self, serial_port, queues, stop_event):
        super().__init__(daemon=True)
        self.serial_port = serial_port
        self.queues = queues
        self.stop_event = stop_event

    def run(self):
        try:
            while not self.stop_event.is_set():
                data = self.serial_port.readline().decode(errors="ignore").strip()
                if data:
                    for q in self.queues:
                        q.put(data)
        except serial.SerialException:
            self.stop_event.set()


class MonitorThread(threading.Thread):
    def __init__(self, monitor_name, keyword, data_queue, report_queue, stop_event):
        super().__init__(daemon=True)
        self.monitor_name = monitor_name
        self.keyword = keyword
        self.data_queue = data_queue
        self.report_queue = report_queue
        self.stop_event = stop_event

    def run(self):
        while not self.stop_event.is_set():
            try:
                data = self.data_queue.get(timeout=0.5)
                if self.keyword in data:
                    ts = time.strftime("%d-%m-%Y %H:%M:%S")
                    print(f"{self.monitor_name} found '{self.keyword}'!")
                    self.report_queue.put((self.keyword, ts))
                if "End" in data:
                    time.sleep(0.1)
                    self.stop_event.set()
            except queue.Empty:
                continue


class ReportThread(threading.Thread):
    def __init__(self, report_queue, keywords, stop_event):
        super().__init__(daemon=True)
        self.report_queue = report_queue
        self.stop_event = stop_event
        self.counts = {k: [] for k in keywords}

    def run(self):
        while not self.stop_event.is_set():
            try:
                keyword, timestamp = self.report_queue.get(timeout=0.5)
                self.counts[keyword].append(timestamp)
            except queue.Empty:
                continue

        self._print_report()

    def _print_report(self):
        print("-----------------")
        print("REPORT:")
        for keyword, timestamps in self.counts.items():
            print(f"{keyword}: {len(timestamps)} lan")
            for t in timestamps:
                print(f"    {t}")
        print("-----------------")
        input("Nhan Enter de thoat...") 


class SerialMonitorApp:
    def __init__(self, port, baudrate=115200):
        self.ser        = serial.Serial(port, baudrate, timeout=1)
        print(f"Da mo thanh cong {port} | Baudrate: {baudrate}")
        self.stop_event = threading.Event()
        self.q1         = queue.Queue()
        self.q2         = queue.Queue()
        self.q_report   = queue.Queue()

    def run(self):
        keywords = ["Ampere", "Computing"]

        threads = [
            SerialReader(self.ser, [self.q1, self.q2], self.stop_event),
            MonitorThread("Monitor 1", "Ampere",    self.q1, self.q_report, self.stop_event),
            MonitorThread("Monitor 2", "Computing", self.q2, self.q_report, self.stop_event),
            ReportThread(self.q_report, keywords, self.stop_event),
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        self.ser.close()
        print("Chuong trinh ket thuc!")


if __name__ == "__main__":
    port = input("Nhap so cong COM (vi du: 4): ").strip()
    port = f"COM{port}"
    try:
        app = SerialMonitorApp(port, 115200)
        app.run()
    except serial.SerialException as e:
        print(f"Khong the mo {port}: {e}")
        input("Nhan Enter de thoat...") 