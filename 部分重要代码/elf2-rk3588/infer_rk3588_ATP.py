"""
infer_rk3588_ATP.py - RK3588 故障诊断
功能: 模型加载一次，持续监听CSV文件夹，多线程特征提取加速
使用方法: python infer_rk3588_ATP.py --watch_dir ./csv_input --cores 3 --model fault_diagnosis_cnn_rk3588.rknn
"""
import numpy as np
import json
import argparse
import sys
import os
import time
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from rknnlite.api import RKNNLite


class FeatureExtractor:
    def __init__(self, fs=1000, max_samples=50000):
        self.fs = fs
        self.max_samples = max_samples

    def _resample_signal(self, signal):
        original_len = len(signal)
        if original_len > self.max_samples:
            indices = np.linspace(0, original_len - 1, self.max_samples, dtype=int)
            signal = signal[indices]
        return signal

    def _lempel_ziv_complexity(self, sequence):
        n = len(sequence)
        if n > 10000:
            sequence = sequence[::10]
            n = len(sequence)
        median_val = np.median(sequence)
        binary_seq = (sequence > median_val).astype(np.int8).tolist()
        if n == 0:
            return 0.0
        c = 1
        l = 1
        i = 0
        k = 1
        k_max = 1
        while True:
            if i + k >= n or l + k >= n:
                break
            if binary_seq[i + k] == binary_seq[l + k]:
                k += 1
                if l + k > n:
                    c += 1
                    break
            else:
                if k > k_max:
                    k_max = k
                i += 1
                if i == l:
                    c += 1
                    l += k_max
                    if l + 1 > n:
                        break
                    i = 0
                    k = 1
                    k_max = 1
                else:
                    k = 1
        return float(c)

    def extract(self, signal: np.ndarray) -> np.ndarray:
        from scipy.stats import skew, kurtosis

        signal = np.asarray(signal, dtype=np.float64).flatten()
        signal = np.nan_to_num(signal, nan=0.0, posinf=0.0, neginf=0.0)

        n = len(signal)
        if n == 0:
            return np.zeros(17, dtype=np.float32)

        if n > self.max_samples:
            indices = np.linspace(0, n - 1, self.max_samples, dtype=int)
            signal = signal[indices]
            n = len(signal)

        feat = np.zeros(17, dtype=np.float32)

        abs_signal = np.abs(signal)
        mean_val = float(np.mean(signal))
        rms = float(np.sqrt(np.mean(signal ** 2)))
        max_abs = float(np.max(abs_signal))

        feat[0] = float(np.sum(signal ** 2))
        feat[1] = self._lempel_ziv_complexity(signal)
        feat[2] = mean_val
        feat[3] = rms
        feat[4] = float(np.std(signal, ddof=0))
        feat[5] = float(skew(signal, bias=False)) if n > 2 else 0.0
        feat[6] = float(kurtosis(signal, bias=False)) if n > 3 else 0.0

        eps = 1e-12
        mean_abs = float(np.mean(abs_signal))
        sqrt_mean = float(np.mean(np.sqrt(abs_signal)))

        feat[7] = rms / mean_abs if mean_abs > eps else 0.0
        feat[8] = max_abs / (sqrt_mean ** 2) if sqrt_mean > eps else 0.0
        feat[9] = max_abs / mean_abs if mean_abs > eps else 0.0
        feat[10] = max_abs / rms if rms > eps else 0.0
        feat[11] = float(np.mean(signal ** 4)) / (rms ** 4) if rms > eps else 0.0

        fft_vals = np.abs(np.fft.fft(signal)) ** 2
        half = len(fft_vals) // 2
        fft_vals = fft_vals[:half]
        freqs = np.fft.fftfreq(n, d=1.0 / self.fs)[:half]

        psd_sum = np.sum(fft_vals)
        psd = fft_vals / psd_sum if psd_sum > eps else fft_vals

        center_freq = float(np.sum(freqs * psd))
        mean_sq_freq = float(np.sum((freqs ** 2) * psd))

        feat[12] = center_freq
        feat[13] = mean_sq_freq
        feat[14] = float(np.sqrt(mean_sq_freq))
        feat[15] = float(np.sum(((freqs - center_freq) ** 2) * psd))
        feat[16] = float(np.sqrt(feat[15]))

        return feat


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
        self._rknn_lock = threading.Lock()

        max_workers = min(8, (os.cpu_count() or 4))
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        core_map = {1: RKNNLite.NPU_CORE_0, 2: RKNNLite.NPU_CORE_0_1, 3: RKNNLite.NPU_CORE_0_1_2}
        core_mask = core_map.get(cores, RKNNLite.NPU_CORE_AUTO)

        print(f"[系统] 加载模型: {rknn_path}, NPU核心: {cores}, 线程池: {max_workers}")
        self.rknn = RKNNLite()
        self.rknn.load_rknn(str(rknn_path))
        ret = self.rknn.init_runtime(core_mask=core_mask)
        if ret != 0:
            raise RuntimeError(f"RKNN 初始化失败: {ret}")
        print(f"[系统] 就绪，支持: {self.classes}")

    def predict(self, signal: np.ndarray):
        t0 = time.time()
        features = self.extractor.extract(signal)
        t1 = time.time()

        features = (features - self.feature_mean) / self.feature_std
        features = features.reshape(1, -1)

        with self._rknn_lock:
            outputs = self.rknn.inference(inputs=[features])
        t2 = time.time()

        logits = outputs[0][0]
        logits = logits - np.max(logits)
        probs = np.exp(logits) / np.sum(np.exp(logits))

        pred_idx = np.argmax(probs)
        label = self.classes[pred_idx]
        confidence = float(probs[pred_idx] * 100)

        return {
            'label': label,
            'confidence': confidence,
            'probabilities': dict(zip(self.classes, (probs * 100).tolist())),
            'time_feature_ms': (t1 - t0) * 1000,
            'time_inference_ms': (t2 - t1) * 1000,
            'time_total_ms': (t2 - t0) * 1000,
        }

    def release(self):
        self._executor.shutdown(wait=True)
        with self._rknn_lock:
            self.rknn.release()
        print("[系统] 已释放")


class CSVWatcher(threading.Thread):
    def __init__(self, watch_dir, predictor, check_interval=0.5, output_dir=None):
        super().__init__(daemon=True)
        self.watch_dir = Path(watch_dir)
        self.predictor = predictor
        self.check_interval = check_interval
        self.output_dir = Path(output_dir) if output_dir else self.watch_dir / "results"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._stop_event = threading.Event()
        self._processed = set()

    def stop(self):
        self._stop_event.set()

    def run(self):
        import pandas as pd

        print(f"[监听] 目录: {self.watch_dir}")
        print(f"[监听] 结果: {self.output_dir}")
        print(f"[监听] 等待 CSV 文件...")

        while not self._stop_event.is_set():
            try:
                csv_files = sorted(
                    [f for f in self.watch_dir.glob("*.csv") if f not in self._processed],
                    key=lambda x: x.stat().st_mtime
                )

                for csv_path in csv_files:
                    time.sleep(0.2)

                    try:
                        df = pd.read_csv(csv_path, header=None, nrows=60000)
                        if df.shape[1] < 2:
                            print(f"[警告] {csv_path.name}: 列数不足")
                            self._processed.add(csv_path)
                            continue

                        signal = pd.to_numeric(df.iloc[:, 1], errors='coerce').values
                        signal = np.nan_to_num(signal, nan=0.0)

                        if len(signal) < 100:
                            print(f"[警告] {csv_path.name}: 数据太短")
                            self._processed.add(csv_path)
                            continue

                        t0 = time.time()
                        result = self.predictor.predict(signal)

                        print(f"\n{'='*50}")
                        print(f"文件: {csv_path.name} ({len(signal)}点)")
                        print(f"结果: {result['label']} ({result['confidence']:.1f}%)")
                        print(f"耗时: 特征{result['time_feature_ms']:.1f}ms "
                              f"+ 推理{result['time_inference_ms']:.1f}ms "
                              f"= 总计{result['time_total_ms']:.1f}ms")
                        print(f"各类概率:")
                        for cls, prob in sorted(result['probabilities'].items(),
                                                 key=lambda x: x[1], reverse=True)[:5]:
                            bar = '#' * int(prob / 2)
                            print(f"  {cls:15s}: {prob:5.1f}% {bar}")
                        print(f"{'='*50}")

                        result_file = self.output_dir / f"{csv_path.stem}_result.json"
                        with open(result_file, 'w') as f:
                            json.dump({
                                'file': csv_path.name,
                                'samples': len(signal),
                                'label': result['label'],
                                'confidence': result['confidence'],
                                'probabilities': result['probabilities'],
                                'time_ms': {
                                    'feature': round(result['time_feature_ms'], 2),
                                    'inference': round(result['time_inference_ms'], 2),
                                    'total': round(result['time_total_ms'], 2),
                                },
                                'timestamp': datetime.now().isoformat(),
                            }, f, ensure_ascii=False, indent=2)

                    except Exception as e:
                        print(f"[错误] {csv_path.name}: {e}")

                    self._processed.add(csv_path)

                if len(self._processed) > 1000:
                    existing = set(self.watch_dir.glob("*.csv"))
                    self._processed = self._processed & existing

                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[监听] 异常: {e}")
                time.sleep(5)


def main():
    parser = argparse.ArgumentParser(description="故障诊断 - CSV持续运行模式")
    parser.add_argument('--watch_dir', '-w', type=str, required=True)
    parser.add_argument('--model_dir', '-m', type=str, default='model')
    parser.add_argument('--model', '-n', type=str, default='fault_diagnosis_cnn.rknn')
    parser.add_argument('--cores', '-c', type=int, default=1, choices=[1, 2, 3])
    parser.add_argument('--output_dir', '-o', type=str, default=None)
    parser.add_argument('--interval', '-i', type=float, default=0.5)
    args = parser.parse_args()

    watch_dir = Path(args.watch_dir)
    if not watch_dir.exists():
        print(f"目录不存在: {watch_dir}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"故障诊断 - 持续运行")
    print(f"{'='*60}")

    predictor = FaultPredictor(args.model_dir, args.model, args.cores)

    watcher = CSVWatcher(
        watch_dir=str(watch_dir),
        predictor=predictor,
        check_interval=args.interval,
        output_dir=args.output_dir,
    )
    watcher.start()

    print(f"\n[系统] 将CSV放入 {watch_dir} 自动处理，Ctrl+C 停止\n")

    try:
        while watcher.is_alive():
            watcher.join(1)
    except KeyboardInterrupt:
        print("\n停止...")
        watcher.stop()
        watcher.join(5)

    predictor.release()
    print("已停止")


if __name__ == "__main__":
    main()