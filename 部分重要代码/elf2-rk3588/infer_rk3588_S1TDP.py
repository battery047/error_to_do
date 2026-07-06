"""
infer_rk3588_S1TDP.py - RK3588 故障诊断（串口接收17维特征直接推理）
接收17维特征数据，直接推理并回传结果
使用方法: python infer_rk3588_S1TDP.py --port /dev/ttyS1 --baud 115200 --cores 3
"""
import numpy as np
import json
import serial
import argparse
import sys
import time
from pathlib import Path
from rknnlite.api import RKNNLite


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

        core_map = {1: RKNNLite.NPU_CORE_0, 2: RKNNLite.NPU_CORE_0_1, 3: RKNNLite.NPU_CORE_0_1_2}
        core_mask = core_map.get(cores, RKNNLite.NPU_CORE_AUTO)

        print(f"[系统] 加载模型: {rknn_path}, NPU核心: {cores}")
        self.rknn = RKNNLite()
        self.rknn.load_rknn(str(rknn_path))
        ret = self.rknn.init_runtime(core_mask=core_mask)
        if ret != 0:
            raise RuntimeError(f"RKNN 初始化失败: {ret}")
        print(f"[系统] 就绪，支持: {self.classes}")

    def predict(self, features: np.ndarray):
        features = (features - self.feature_mean) / self.feature_std
        features = features.reshape(1, -1).astype(np.float32)
        outputs = self.rknn.inference(inputs=[features])
        logits = outputs[0][0] - np.max(outputs[0][0])
        probs = np.exp(logits) / np.sum(np.exp(logits))
        pred_idx = np.argmax(probs)
        return self.classes[pred_idx], probs[pred_idx] * 100, dict(zip(self.classes, probs.tolist()))

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

    def read_features_ascii(self):
        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            return None
        try:
            values = [float(x) for x in line.split(',')]
            if len(values) == 17:
                return np.array(values, dtype=np.float32)
        except:
            pass
        return None

    def read_features_binary(self):
        raw = self.ser.read(68)
        if len(raw) < 68:
            return None
        return np.frombuffer(raw, dtype=np.float32)

    def send_result(self, label, confidence, probs):
        msg = f"{label},{confidence:.1f}\n"
        self.ser.write(msg.encode())


def main():
    parser = argparse.ArgumentParser(description="故障诊断 - 17维特征直接推理")
    parser.add_argument('--port', '-p', type=str, default='/dev/ttyS1')
    parser.add_argument('--baud', '-b', type=int, default=115200)
    parser.add_argument('--model_dir', '-m', type=str, default='model')
    parser.add_argument('--model', '-n', type=str, default='fault_diagnosis_cnn.rknn')
    parser.add_argument('--cores', '-c', type=int, default=1, choices=[1, 2, 3])
    parser.add_argument('--mode', type=str, default='binary', choices=['ascii', 'binary'])
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    predictor = FaultPredictor(args.model_dir, args.model, args.cores)
    receiver = SerialReceiver(args.port, args.baud)
    if not receiver.open():
        predictor.release()
        sys.exit(1)

    print(f"模式: {args.mode}, 等待数据...\n")
    try:
        while True:
            features = receiver.read_features_binary() if args.mode == 'binary' else receiver.read_features_ascii()
            if features is None:
                continue
            t0 = time.time()
            label, conf, probs = predictor.predict(features)
            elapsed = (time.time() - t0) * 1000
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{ts}] 推理: {elapsed:.1f}ms")
            print(f"  故障: {label} ({conf:.1f}%)")
            if args.verbose:
                for cls, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
                    print(f"    {cls}: {prob*100:.1f}%")
            receiver.send_result(label, conf, probs)
    except KeyboardInterrupt:
        print("\n退出")
    finally:
        receiver.close()
        predictor.release()


if __name__ == "__main__":
    main()