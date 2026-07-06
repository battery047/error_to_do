"""
特征提取器 - 本地提取17种特征(用于与DSP结果对比验证)
"""
import numpy as np
from scipy.stats import skew, kurtosis
from typing import Dict, List

from .constants import FEATURE_NAMES


class FeatureExtractor:
    """17种故障特征提取器"""

    def __init__(self, fs: int = 1000):
        self.fs = fs

    def extract(self, signal: np.ndarray) -> Dict[str, float]:
        signal = np.asarray(signal, dtype=np.float64).flatten()
        n = len(signal)

        if n == 0:
            return {name: np.nan for name in FEATURE_NAMES}

        features = {}

        # ========== 时域特征 ==========
        mean_val = float(np.mean(signal))
        abs_signal = np.abs(signal)
        mean_abs = float(np.mean(abs_signal))
        max_abs = float(np.max(abs_signal))
        rms = float(np.sqrt(np.mean(np.abs(signal) ** 2)))
        std_val = float(np.std(signal, ddof=0))

        features["T1_能量"] = float(np.sum(np.abs(signal) ** 2))
        features["T2_LZ复杂度"] = self._lempel_ziv_complexity(signal)
        features["T3_均值"] = mean_val
        features["T4_均方根"] = rms
        features["T5_标准差"] = std_val
        features["T6_偏度"] = float(skew(signal, bias=False)) if n > 2 else 0.0
        features["T7_峭度"] = float(kurtosis(signal, bias=False)) if n > 3 else 0.0

        # ========== 无量纲特征 ==========
        eps = 1e-12
        sqrt_mean = float(np.mean(np.sqrt(abs_signal)))

        features["T8_波形因子"] = rms / mean_abs if mean_abs > eps else 0.0
        features["T9_裕度因子"] = max_abs / (sqrt_mean ** 2) if sqrt_mean > eps else 0.0
        features["T10_脉冲因子"] = max_abs / mean_abs if mean_abs > eps else 0.0
        features["T11_峰值因子"] = max_abs / rms if rms > eps else 0.0

        mean_quad = float(np.mean(signal ** 4))
        rms_quad = rms ** 4
        features["T12_峭度因子"] = mean_quad / rms_quad if rms_quad > eps else 0.0

        # ========== 频域特征 ==========
        fft_vals = np.abs(np.fft.fft(signal)) ** 2
        fft_vals = fft_vals[:len(fft_vals) // 2]
        freqs = np.fft.fftfreq(n, d=1.0 / self.fs)[:n // 2]

        psd_sum = np.sum(fft_vals)
        psd = fft_vals / psd_sum if psd_sum > eps else fft_vals

        center_freq = float(np.sum(freqs * psd))
        mean_square_freq = float(np.sum((freqs ** 2) * psd))

        features["T13_中心频率"] = center_freq
        features["T14_均方频率"] = mean_square_freq
        features["T15_均方根频率"] = float(np.sqrt(mean_square_freq))
        features["T16_频率方差"] = float(np.sum(((freqs - center_freq) ** 2) * psd))
        features["T17_频率标准差"] = float(np.sqrt(features["T16_频率方差"]))

        return features

    def _lempel_ziv_complexity(self, signal: np.ndarray) -> float:
        n = len(signal)
        if n <= 1:
            return 0.0

        if n > 10000:
            step = n // 10000
            signal = signal[::step]
            n = len(signal)

        median = np.median(signal)
        binary = (signal > median).astype(np.int8).tolist()

        c = 1
        length = 1
        i = 0
        k = 1
        k_max = 1

        while True:
            if i + k >= n or length + k >= n:
                break
            if binary[i + k] == binary[length + k]:
                k += 1
                if length + k > n:
                    c += 1
                    break
            else:
                if k > k_max:
                    k_max = k
                i += 1
                if i == length:
                    c += 1
                    length += k_max
                    if length + 1 > n:
                        break
                    i = 0
                    k = 1
                    k_max = 1
                else:
                    k = 1

        return float(c)

    def extract_batch(self, signals: List[np.ndarray]) -> List[Dict[str, float]]:
        return [self.extract(s) for s in signals]

    def features_to_array(self, features: Dict[str, float]) -> np.ndarray:
        arr = np.zeros(len(FEATURE_NAMES))
        for i, name in enumerate(FEATURE_NAMES):
            val = features.get(name, np.nan)
            arr[i] = val if not np.isnan(val) else 0.0
        return arr