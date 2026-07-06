"""
infer_rk3588_S1TP.py - RK3588 故障诊断（串口接收波形数据，实时诊断）
通过串口接收波形数据，本地提取特征后推理，回传结果
使用方法: python infer_rk3588_S1TP.py --port /dev/ttyS1 --baud 115200 --cores 3
"""
import numpy as np
import json
import serial
import argparse
import sys
import time
from pathlib import Path
from rknnlite.api import RKNNLite


class FeatureExtractor:
    def __init__(self, fs=1000, max_samples=50000):
        self.fs = fs
        self.max_samples = max_samples
        self.feature_names = [
            "T1_energy", "T2_complexity", "T3_mean", "T4_rms", "T5_std",
            "T6_skewness", "T7_kurtosis", "T8_waveform_factor", "T9_margin_factor",
            "T10_impulse_factor", "T11_peak_factor", "T12_kurtosis_factor",
            "T13_center_freq", "T14_mean_square_freq", "T15_rms_freq",
            "T16_freq_variance", "T17_freq_std",
        ]

    def _ensure_numeric(self, signal):
        signal = np.array(signal, dtype=np.float64).flatten()
        signal = np.nan_to_num(signal, nan=0.0, posinf=0.0, neginf=0.0)
        return signal

    def _resample_signal(self, signal):
        original_len = len(signal)
        if original_len > self.max_samples:
            indices = np.linspace(0, original_len - 1, self.max_samples, dtype=int)
            signal = signal[indices]
        return signal

    def lempel_ziv_complexity(self, sequence):
        if len(sequence) > 10000:
            sequence = sequence[::10]
        median_val = np.median(sequence)
        binary_seq = (sequence > median_val).astype(int).tolist()
        n = len(binary_seq)
        if n == 0:
            return 0
        c, l, i, k, k_max = 1, 1, 0, 1, 1
        while True:
            if i + k - 1 >= n or l + k - 1 >= n:
                break
            if binary_seq[i + k - 1] == binary_seq[l + k - 1]:
                k += 1
                if l + k > n:
                    c += 1
                    break
            else:
                if k > k_max: k_max = k
                i += 1
                if i == l:
                    c += 1
                    l += k_max
                    if l + 1 > n: break
                    i, k, k_max = 0, 1, 1
                else:
                    k = 1
        return c

    def extract_single(self, signal):
        from scipy.stats import skew, kurtosis
        signal = self._ensure_numeric(signal)
        signal = self._resample_signal(signal)
        n = len(signal)
        if n == 0:
            return np.zeros(17, dtype=np.float32)
        features = {}
        features["T1_energy"] = np.sum(np.abs(signal)**2)
        features["T2_complexity"] = self.lempel_ziv_complexity(signal)
        features["T3_mean"] = np.mean(signal)
        features["T4_rms"] = np.sqrt(np.mean(np.abs(signal)**2))
        features["T5_std"] = np.std(signal, ddof=0)
        features["T6_skewness"] = skew(signal, bias=False) if n > 2 else 0
        features["T7_kurtosis"] = kurtosis(signal, bias=False) if n > 3 else 0
        mean_abs = np.abs(features["T3_mean"])
        max_abs = np.max(np.abs(signal))
        sqrt_mean = np.mean(np.sqrt(np.abs(signal)))
        features["T8_waveform_factor"] = features["T4_rms"] / mean_abs if mean_abs > 1e-10 else 0
        features["T9_margin_factor"] = max_abs / (sqrt_mean**2) if sqrt_mean > 1e-10 else 0
        features["T10_impulse_factor"] = max_abs / mean_abs if mean_abs > 1e-10 else 0
        features["T11_peak_factor"] = max_abs / features["T4_rms"] if features["T4_rms"] > 1e-10 else 0
        mean_quad = np.mean(signal**4)
        features["T12_kurtosis_factor"] = mean_quad / (features["T4_rms"]**4) if features["T4_rms"] > 1e-10 else 0
        fft_vals = np.abs(np.fft.fft(signal))**2
        fft_vals = fft_vals[:len(fft_vals)//2]
        freqs = np.fft.fftfreq(n, d=1/self.fs)[:n//2]
        psd_sum = np.sum(fft_vals)
        psd = fft_vals / psd_sum if psd_sum > 1e-10 else fft_vals
        features["T13_center_freq"] = np.sum(freqs*psd)
        features["T14_mean_square_freq"] = np.sum((freqs**2)*psd)
        features["T15_rms_freq"] = np.sqrt(features["T14_mean_square_freq"])
        features["T16_freq_variance"] = np.sum(((freqs-features["T13_center_freq"])**2)*psd)
        features["T17_freq_std"] = np.sqrt(features["T16_freq_variance"])
        return np.array([features[n] for n in self.feature_names], dtype=np.float32)


class FaultPredictor:
    def __init__(self, model_dir="model", model_name="fault_diagnosis_cnn.rknn", cores=1):
        model_dir = Path(model_dir)
        rknn_path = model_dir / model_name
        config_path = model_dir / "model_config.json"

        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.classes = self.config['classes']
        self.feature_mean = np.array(self.config['feature_mean'], dtype=np.float32)
        self.feature_std = np.array(self.config['feature_std'], dtype=np.float32)
        self.feature_std[self.feature_std == 0] = 1.0
        self.extractor = FeatureExtractor(fs=1000, max_samples=50000)

        core_map = {1: RKNNLite.NPU_CORE_0, 2: RKNNLite.NPU_CORE_0_1, 3: RKNNLite.NPU_CORE_0_1_2}
        core_mask = core_map.get(cores, RKNNLite.NPU_CORE_AUTO)

        print(f"[系统] 加载模型: {rknn_path}, NPU核心: {cores}")
        self.rknn = RKNNLite()
        self.rknn.load_rknn(str(rknn_path))
        ret = self.rknn.init_runtime(core_mask=core_mask)
        if ret != 0:
            raise RuntimeError(f"RKNN 初始化失败: {ret}")
        print(f"[系统] 就绪，支持: {self.classes}")

    def predict(self, signal):
        features = self.extractor.extract_single(signal)
        features = (features - self.feature_mean) / self.feature_std
        features = features.reshape(1, -1)
        outputs = self.rknn.inference(inputs=[features])
        logits = outputs[0][0] - np.max(outputs[0][0])
        probs = np.exp(logits) / np.sum(np.exp(logits))
        pred_idx = np.argmax(probs)
        return self.classes[pred_idx], probs[pred_idx] * 100

    def release(self):
        self.rknn.release()


class SerialReceiver:
    def __init__(self, port, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def open(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout,
                                      bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                                      stopbits=serial.STOPBITS_ONE)
            print(f"[串口] 已打开: {self.port} @ {self.baudrate}")
            return True
        except Exception as e:
            print(f"[错误] {e}")
            return False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def read_data(self, num_points):
        raw = self.ser.read(num_points * 4)
        if len(raw) < num_points * 4:
            return None
        return np.frombuffer(raw, dtype=np.float32)

    def read_line_data(self):
        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            return None
        try:
            return np.array([float(x) for x in line.split(',')], dtype=np.float32)
        except:
            return None


def main():
    parser = argparse.ArgumentParser(description="故障诊断 - 串口接收波形数据")
    parser.add_argument('--port', '-p', type=str, default='/dev/ttyS1')
    parser.add_argument('--baud', '-b', type=int, default=115200)
    parser.add_argument('--model_dir', '-m', type=str, default='model')
    parser.add_argument('--model', '-n', type=str, default='fault_diagnosis_cnn.rknn')
    parser.add_argument('--cores', '-c', type=int, default=1, choices=[1, 2, 3])
    parser.add_argument('--mode', type=str, default='ascii', choices=['ascii', 'binary'])
    parser.add_argument('--num_points', '-N', type=int, default=1024)
    args = parser.parse_args()

    predictor = FaultPredictor(args.model_dir, args.model, args.cores)
    receiver = SerialReceiver(args.port, args.baud)
    if not receiver.open():
        predictor.release()
        sys.exit(1)

    print(f"等待数据... Ctrl+C 退出\n")
    try:
        while True:
            signal = receiver.read_data(args.num_points) if args.mode == 'binary' else receiver.read_line_data()
            if signal is None:
                continue
            label, conf = predictor.predict(signal)
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            msg = f"[{ts}] 故障: {label} | 置信度: {conf:.1f}%"
            print(msg)
            receiver.ser.write((msg + "\n").encode())
    except KeyboardInterrupt:
        print("\n退出")
    finally:
        receiver.close()
        predictor.release()


if __name__ == "__main__":
    main()