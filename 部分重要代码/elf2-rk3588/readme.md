# 所包含的文件介绍及使用配置

## serial_debug.py

串口调试工具，监听指定串口，显示收到的原始数据（十六进制和ASCII），自动识别并解析 AA 55 开头的特征数据包。

python serial_debug.py --port /dev/ttyUSB0 --baud 9600

| 参数     | 简写  | 说明     | 默认值          |
| ------ | --- | ------ | ------------ |
| --port | -p  | 串口设备路径 | /dev/ttyUSB0 |
| --baud | -b  | 波特率    | 9600         |

## infer_rk3588_ATP.py

持续监听指定文件夹，检测到新CSV文件后自动读取波形数据、本地提取17维特征、调用RKNN模型推理，结果保存为JSON文件。

python infer_rk3588_ATP.py --watch_dir ./csv_input --cores 3 --model fault_diagnosis_cnn_rk3588.rknn
python infer_rk3588_ATP.py --watch_dir ./csv_input --cores 1

| 参数           | 简写  | 说明             | 默认值                      |
| ------------ | --- | -------------- | ------------------------ |
| --watch_dir  | -w  | 监听的CSV文件夹（必填）  | -                        |
| --model_dir  | -m  | 模型存放目录         | model                    |
| --model      | -n  | RKNN模型文件名      | fault_diagnosis_cnn.rknn |
| --cores      | -c  | NPU核心数 (1/2/3) | 1                        |
| --output_dir | -o  | 结果输出目录         | watch_dir/results        |
| --interval   | -i  | 文件夹扫描间隔(秒)     | 0.5                      |

## infer_rk3588_S1TDP.py

串口接收DSP发来的17维特征数据，直接送入RKNN模型推理，结果通过串口回传。

python infer_rk3588_S1TDP.py --port /dev/ttyUSB0 --baud 9600 --cores 3 --model fault_diagnosis_cnn_rk3588.rknn --mode binary
python infer_rk3588_S1TDP.py --port /dev/ttyS1 --baud 115200 --cores 1

| 参数          | 简写  | 说明                 | 默认值                      |
| ----------- | --- | ------------------ | ------------------------ |
| --port      | -p  | 串口设备路径             | /dev/ttyS1               |
| --baud      | -b  | 波特率                | 115200                   |
| --model_dir | -m  | 模型存放目录             | model                    |
| --model     | -n  | RKNN模型文件名          | fault_diagnosis_cnn.rknn |
| --cores     | -c  | NPU核心数 (1/2/3)     | 1                        |
| --mode      | -   | 数据格式: binary或ascii | binary                   |
| --verbose   | -v  | 显示详细概率分布           | 关闭                       |

## infer_rk3588_S1TP.py

串口接收原始波形数据，本地提取17维特征后送入RKNN模型推理，结果通过串口回传。

python infer_rk3588_S1TP.py --port /dev/ttyUSB0 --baud 115200 --cores 3 --model fault_diagnosis_cnn_rk3588.rknn
python infer_rk3588_S1TP.py --port /dev/ttyS1 --baud 115200 --cores 1

| 参数           | 简写  | 说明                  | 默认值                      |
| ------------ | --- | ------------------- | ------------------------ |
| --port       | -p  | 串口设备路径              | /dev/ttyS1               |
| --baud       | -b  | 波特率                 | 115200                   |
| --model_dir  | -m  | 模型存放目录              | model                    |
| --model      | -n  | RKNN模型文件名           | fault_diagnosis_cnn.rknn |
| --cores      | -c  | NPU核心数 (1/2/3)      | 1                        |
| --mode       | -   | 数据格式: binary或ascii  | ascii                    |
| --num_points | -N  | 每次读取的采样点数(binary模式) | 1024                     |
