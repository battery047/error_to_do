"""
串口工作线程 - 发送CSV数据到DSP，接收特征结果
"""
import time
import struct
import threading
from typing import Optional, List
from datetime import datetime

import serial
import serial.tools.list_ports
import numpy as np
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from .constants import (
    PACKET_HEADER, PACKET_FOOTER,
    SAMPLES_PER_PACKET, SEND_INTERVAL_MS,
    CMD_START_SEND, CMD_STOP_SEND, CMD_REQUEST_RESULT,
    CMD_RESET, CMD_ACK, CMD_NACK,
    CMD_DATA_LENGTH, CMD_WAVEFORM_DATA,
    RSP_FEATURE_DATA, RSP_STATUS_MSG,
    FEATURE_SHORT_NAMES,
)


class SerialWorker(QThread):
    """串口通信线程"""

    connection_status = Signal(bool, str)
    send_progress = Signal(int, int, str)
    send_complete = Signal(bool, str)
    data_received = Signal(list, float)
    raw_log = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._serial: Optional[serial.Serial] = None
        self._is_running = False
        self._send_requested = False
        self._waveform_data: Optional[np.ndarray] = None

        self._mutex = QMutex()
        self._serial_lock = threading.Lock()
        self._rx_buffer = bytearray()

        self.port = "COM3"
        self.baudrate = 9600
        self.bytesize = 8
        self.stopbits = 1
        self.parity = "N"
        self.timeout = 0.1
        self.send_interval_ms = SEND_INTERVAL_MS

    def set_serial_params(self, port: str, baudrate: int):
        self.port = port
        self.baudrate = baudrate

    def connect(self) -> bool:
        try:
            locker = QMutexLocker(self._mutex)
            if self._serial and self._serial.is_open:
                self._serial.close()

            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                stopbits=self.stopbits,
                parity=self.parity,
                timeout=self.timeout,
                write_timeout=0.5,
            )

            if self._serial.is_open:
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
                msg = f"已连接 {self.port} @ {self.baudrate} bps"
                self.connection_status.emit(True, msg)
                self.raw_log.emit(f"[系统] {msg}")
                return True

        except serial.SerialException as e:
            self.connection_status.emit(False, f"连接失败: {e}")
            self.error_occurred.emit(f"串口连接错误: {e}")
        except Exception as e:
            self.error_occurred.emit(f"连接失败: {e}")

        return False

    def disconnect(self):
        self.stop()
        self.wait(2000)
        locker = QMutexLocker(self._mutex)
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self.connection_status.emit(False, "已断开连接")
        self.raw_log.emit("[系统] 串口已关闭")

    def stop(self):
        self._is_running = False
        self._send_requested = False

    def set_waveform_data(self, data: np.ndarray):
        locker = QMutexLocker(self._mutex)
        self._waveform_data = data.astype(np.float64).flatten().copy()
        n = len(self._waveform_data)
        self.raw_log.emit(f"[系统] 波形数据已加载: {n} 个采样点")

    def send_waveform(self, data: np.ndarray = None):
        if data is not None:
            self.set_waveform_data(data)
        locker = QMutexLocker(self._mutex)
        if self._waveform_data is None or len(self._waveform_data) == 0:
            self.error_occurred.emit("没有波形数据可发送")
            return
        self._send_requested = True

    def send_features_packet(self, features: np.ndarray):
        """发送17个特征值到RK3566（通过DSP SCI-C转发）"""
        # payload = features.astype(np.float32).tobytes()
        payload = features.astype(np.float32).tobytes()
        data_len = len(payload)
        length_bytes = struct.pack('>H', data_len)
        packet = PACKET_HEADER + b'\x22' + length_bytes + payload
        checksum = sum(packet) & 0xFF
        packet += bytes([checksum]) + PACKET_FOOTER

        with self._serial_lock:
            if self._serial and self._serial.is_open:
                self._serial.write(packet)
                self._serial.flush()
                


        # 打印特征值
        log_lines = [f"[发送] 本地特征已发送(CMD=0x22):"]
        for name, val in zip(FEATURE_SHORT_NAMES, features):
            log_lines.append(f"  {name}: {val:.6f}")
        self.raw_log.emit("\n".join(log_lines))

    def run(self):
        self._is_running = True

        if not self._serial or not self._serial.is_open:
            self.error_occurred.emit("串口未打开，无法启动线程")
            return

        self.raw_log.emit("[系统] 通信线程已启动")

        while self._is_running:
            try:
                if self._send_requested:
                    self._mutex.lock()
                    try:
                        self._send_requested = False
                        send_data = self._waveform_data
                    finally:
                        self._mutex.unlock()

                    if send_data is not None and len(send_data) > 0:
                        self._do_send_waveform(send_data)

                if self._serial.in_waiting > 0:
                    with self._serial_lock:
                        try:
                            data = self._serial.read(self._serial.in_waiting)
                            self.raw_log.emit(f"[接收] 原始数据 {len(data)}B: {data.hex()}")
                            self._rx_buffer.extend(data)
                            self._process_rx_buffer()
                        except serial.SerialException as e:
                            self.error_occurred.emit(f"读取错误: {e}")

                self.msleep(5)

            except Exception as e:
                self.error_occurred.emit(f"线程异常: {e}")
                self.msleep(100)

        self.raw_log.emit("[系统] 通信线程已停止")

    def _do_send_waveform(self, data: np.ndarray):
            self._rx_buffer.clear()
            self.raw_log.emit("[接收] 已清空缓冲区")

            # data_clipped = np.clip(data, -10.0, 10.0)
            # int_data = (data_clipped / 10.0 * 32767).astype(np.int16)
            
            data_clipped = np.clip(data, -100.0, 100.0)
            int_data = (data_clipped / 100.0 * 32767).astype(np.int16)

            total_samples = len(int_data)
            total_packets = (total_samples + SAMPLES_PER_PACKET - 1) // SAMPLES_PER_PACKET

            self.raw_log.emit(f"[发送] 总采样点: {total_samples}, 分包数: {total_packets}, 电压范围: [{data.min():.3f}, {data.max():.3f}]V")

            try:
                self.raw_log.emit("[发送] >>> CMD_START (0x01)")
                with self._serial_lock:
                    self._serial.write(CMD_START_SEND)
                    self._serial.flush()
                self.msleep(50)

                len_payload = struct.pack('<I', total_samples)
                self.raw_log.emit(f"[发送] >>> 数据长度: {total_samples} (0x{total_samples:08X})")
                self._send_packet(CMD_DATA_LENGTH, len_payload)
                self.msleep(20)

                for i in range(total_packets):
                    if not self._is_running:
                        break
                    start_idx = i * SAMPLES_PER_PACKET
                    end_idx = min(start_idx + SAMPLES_PER_PACKET, total_samples)
                    chunk = int_data[start_idx:end_idx]
                    self._send_packet(CMD_WAVEFORM_DATA, chunk.tobytes())

                    if i % 5 == 0 or i == total_packets - 1:
                        progress_pct = (i + 1) / total_packets * 100
                        self.send_progress.emit(
                            i + 1, total_packets,
                            f"发送 {i+1}/{total_packets} ({progress_pct:.0f}%)"
                        )
                    self.msleep(self.send_interval_ms)

                self.raw_log.emit("[发送] >>> CMD_STOP (0x02)")
                with self._serial_lock:
                    self._serial.write(CMD_STOP_SEND)
                    self._serial.flush()
                self.msleep(20)

                self.raw_log.emit("[发送] >>> CMD_REQUEST (0x03)")
                with self._serial_lock:
                    self._serial.write(CMD_REQUEST_RESULT)
                    self._serial.flush()
                self._dsp_start_time = time.time()  # 记录请求发送时间
                self.send_complete.emit(True, f"发送完成: {total_samples}点, {total_packets}包")
                self.raw_log.emit("[发送] 数据已全部发送，等待DSP返回特征值...")

            except serial.SerialException as e:
                self.send_complete.emit(False, f"发送失败: {e}")
            except Exception as e:
                self.send_complete.emit(False, f"未知错误: {e}")

    def _send_packet(self, cmd: bytes, payload: bytes):
        data_len = len(payload)
        length_bytes = struct.pack('>H', data_len)

        packet = PACKET_HEADER + cmd + length_bytes + payload
        checksum = sum(packet) & 0xFF
        packet += bytes([checksum]) + PACKET_FOOTER

        preview = packet[:12].hex()
        self.raw_log.emit(f"[发送] 包 {len(packet)}B | CMD=0x{cmd.hex()} | LEN={data_len} | {preview}...")

        with self._serial_lock:
            if self._serial and self._serial.is_open:
                self._serial.write(packet)
                self._serial.flush()

    def _process_rx_buffer(self):
        MIN_LEN = 5

        while len(self._rx_buffer) >= MIN_LEN:
            header_idx = -1
            for i in range(len(self._rx_buffer) - 1):
                if self._rx_buffer[i] == 0xAA and self._rx_buffer[i+1] == 0x55:
                    header_idx = i
                    break

            if header_idx == -1:
                if len(self._rx_buffer) > 0:
                    self.raw_log.emit(f"[接收] 丢弃无效数据: {self._rx_buffer.hex()}")
                self._rx_buffer.clear()
                break

            if header_idx > 0:
                garbage = bytes(self._rx_buffer[:header_idx])
                self.raw_log.emit(f"[接收] 丢弃帧头前数据: {garbage.hex()}")
                self._rx_buffer = self._rx_buffer[header_idx:]

            if len(self._rx_buffer) < 5:
                break

            cmd = self._rx_buffer[2]
            data_len = (self._rx_buffer[3] << 8) | self._rx_buffer[4]
            total_len = 5 + data_len + 1 + 2

            self.raw_log.emit(f"[接收] CMD=0x{cmd:02X}, LEN={data_len}, 需要={total_len}B, 有={len(self._rx_buffer)}B")

            if total_len > 1024:
                self.raw_log.emit(f"[接收] 长度异常 {total_len}，丢弃")
                self._rx_buffer.pop(0)
                continue

            if len(self._rx_buffer) < total_len:
                self.raw_log.emit(f"[接收] 等待更多数据...")
                break

            packet = bytes(self._rx_buffer[:total_len])
            self.raw_log.emit(f"[接收] 完整包: {packet.hex()}")
            self._rx_buffer = self._rx_buffer[total_len:]

            if packet[-2] != 0x55 or packet[-1] != 0xAA:
                self.raw_log.emit(f"[接收] 帧尾不匹配! 实际={packet[-2:].hex()}")
                continue

            received_cs = packet[-3]
            calc_cs = sum(packet[:-3]) & 0xFF
            if received_cs != calc_cs:
                self.raw_log.emit(f"[接收] 校验失败! 收到={received_cs:02X}, 计算={calc_cs:02X}")
                continue

            payload = packet[5:-3]
            self.raw_log.emit(f"[接收] OK! 数据={len(payload)}B")

            if cmd == 0x21:
                self._parse_features(payload)
            elif cmd == 0x22:
                try:
                    msg = payload.decode('ascii', errors='replace')
                except Exception:
                    msg = payload.hex()
                self.raw_log.emit(f"[DSP] {msg}")
            elif cmd == 0x06:
                self.raw_log.emit("[DSP] ACK")
            elif cmd == 0x15:
                self.raw_log.emit("[DSP] NACK")
            elif cmd == 0x05 and data_len == 4:
                time_ms = struct.unpack('<f', payload[:4])[0]
                self.raw_log.emit(f"[DSP] 特征提取耗时: {time_ms:.2f}ms")                

    def _parse_features(self, payload: bytes):
        if len(payload) < 68:
            self.raw_log.emit(f"[接收] 特征数据长度不足: {len(payload)}")
            return

        features = []
        for i in range(17):
            offset = i * 4
            val = struct.unpack('<f', payload[offset:offset+4])[0]
            features.append(val)

        timestamp = time.time()

        log_lines = [f"[接收] DSP特征值 @ {datetime.now().strftime('%H:%M:%S.%f')[:-3]}:"]
        for name, val in zip(FEATURE_SHORT_NAMES, features):
            log_lines.append(f"  {name}: {val:.6f}")
        self.raw_log.emit("\n".join(log_lines))

        # 计算DSP耗时
        dsp_time_ms = 0.0
        if hasattr(self, '_dsp_start_time'):
            dsp_time_ms = (timestamp - self._dsp_start_time) * 1000
            self.raw_log.emit(f"[DSP] 总耗时(含通信): {dsp_time_ms:.2f}ms")

        self.data_received.emit(features, dsp_time_ms)

    @staticmethod
    def get_available_ports() -> List[str]:
        try:
            ports = serial.tools.list_ports.comports()
            return [p.device for p in sorted(ports)]
        except Exception:
            return []