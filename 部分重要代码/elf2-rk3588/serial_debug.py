"""
serial_debug.py - 串口调试工具，查看DSP SCI-C发来的原始数据
使用方法: python serial_debug.py --port /dev/ttyUSB0 --baud 9600
"""
import serial
import argparse
import time


def main():
    parser = argparse.ArgumentParser(description="串口调试工具")
    parser.add_argument('--port', '-p', type=str, default='/dev/ttyUSB0', help='串口设备')
    parser.add_argument('--baud', '-b', type=int, default=9600, help='波特率')
    args = parser.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.5)
        print(f"已连接 {args.port} @ {args.baud}")
        print("等待数据... (按 Ctrl+C 退出)\n")
    except Exception as e:
        print(f"串口连接失败: {e}")
        return

    try:
        while True:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"[{time.strftime('%H:%M:%S')}] 收到 {len(data)}B:")
                
                # 打印十六进制
                hex_str = data.hex()
                for i in range(0, len(hex_str), 64):
                    print(f"  {hex_str[i:i+64]}")
                
                # 查找 AA 55 开头的数据包
                for i in range(len(data) - 1):
                    if data[i] == 0xAA and data[i+1] == 0x55:
                        if i + 5 <= len(data):
                            cmd = data[i+2]
                            dlen = (data[i+3] << 8) | data[i+4]
                            total = 5 + dlen + 1 + 2
                            print(f"  发现数据包: AA 55  cmd=0x{cmd:02X}  len={dlen}  总长={total}")
                            
                            if cmd == 0x21:
                                print(f"    -> DSP特征数据包")
                            elif cmd == 0x22:
                                print(f"    -> PC本地特征数据包")
                
                # 尝试打印ASCII
                try:
                    ascii_str = data.decode('ascii', errors='replace')
                    if any(c.isprintable() for c in ascii_str):
                        print(f"  ASCII: {ascii_str[:200]}")
                except:
                    pass
                
                print()
            
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n退出")
    finally:
        ser.close()


if __name__ == "__main__":
    main()