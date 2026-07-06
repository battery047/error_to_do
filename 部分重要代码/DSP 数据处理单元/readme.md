feature_extract.h及feature_extract.c为DSP端个特征提取的计算功能函数封装

sci_tran_format.c中为通信格式
void send_features(float *features, Uint16 uart); 自定义通信格式

void send_process_time(Uint16 uart, float time_ms);自定义测试通信格式


