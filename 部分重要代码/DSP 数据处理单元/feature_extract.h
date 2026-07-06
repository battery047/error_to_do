#ifndef _FEATURE_EXTRACT_H_
#define _FEATURE_EXTRACT_H_

#include "DSP2833x_Device.h"
#include <math.h>

#define FEATURE_COUNT       17
#define FFT_SIZE            2048   //512 memory excellent
#define SAMPLE_FS           1000.0f

typedef struct {
    float sum;
    float sum_sq;
    float sum_abs;
    float sum_sqrt;
    float sum_quad;   // qiuhe youhua
    float min_val;
    float max_val;
    float m3;
    float m4;
    Uint32 count;
} OnlineStats;

extern float g_fft_buffer[FFT_SIZE];
extern Uint32 g_fft_index;
extern Uint32 g_total_count;
extern OnlineStats g_stats;
extern float g_features[FEATURE_COUNT];

void FE_Init(void);
void FE_Reset(void);
void FE_AddSample(float sample);
void FE_AddSampleBlock(int *samples, Uint16 count, float v_range);
Uint32 FE_GetSampleCount(void);
void FE_Extract(float *signal, Uint32 n, float *features);
void FE_ExtractFromBuffer(float *features);

#endif
