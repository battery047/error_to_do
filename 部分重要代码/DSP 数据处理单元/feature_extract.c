#include "feature_extract.h"
#include <string.h>

float g_fft_buffer[FFT_SIZE];
Uint32 g_fft_index = 0;
Uint32 g_total_count = 0;
OnlineStats g_stats;
float g_features[FEATURE_COUNT];

void FE_Init(void) { FE_Reset(); }

void FE_Reset(void) {
    Uint32 i;
    for (i = 0; i < FFT_SIZE; i++) g_fft_buffer[i] = 0.0f;
    g_fft_index = 0;
    g_total_count = 0;
    g_stats.sum = 0.0f;
    g_stats.sum_sq = 0.0f;
    g_stats.sum_abs = 0.0f;
    g_stats.sum_sqrt = 0.0f;

    g_stats.sum_quad = 0.0f;  // qiuhe youhua

    g_stats.min_val = 1e9f;
    g_stats.max_val = -1e9f;
    g_stats.m3 = 0.0f;
    g_stats.m4 = 0.0f;
    g_stats.count = 0;
    for (i = 0; i < FEATURE_COUNT; i++) g_features[i] = 0.0f;
}
//qiuhe youhua forward version
//void FE_AddSample(float sample) {
//    float abs_sample = fabsf(sample);
//    g_stats.sum += sample;
//    g_stats.sum_sq += abs_sample * abs_sample;
//    g_stats.sum_abs += abs_sample;
//    g_stats.sum_sqrt += sqrtf(abs_sample);
//    if (sample < g_stats.min_val) g_stats.min_val = sample;
//    if (sample > g_stats.max_val) g_stats.max_val = sample;
//    g_stats.count++;
//    g_fft_buffer[g_fft_index] = sample;
//    g_fft_index = (g_fft_index + 1) % FFT_SIZE;
//    g_total_count++;
//}
//qiuhe youhua
void FE_AddSample(float sample) {
    float abs_sample = fabsf(sample);
    g_stats.sum += sample;
    g_stats.sum_sq += abs_sample * abs_sample;
    g_stats.sum_abs += abs_sample;
    g_stats.sum_sqrt += sqrtf(abs_sample);
    g_stats.sum_quad += sample * sample * sample * sample;
    if (sample < g_stats.min_val) g_stats.min_val = sample;
    if (sample > g_stats.max_val) g_stats.max_val = sample;
    g_stats.count++;
    g_fft_buffer[g_fft_index] = sample;
    g_fft_index = (g_fft_index + 1) % FFT_SIZE;
    g_total_count++;
}
void FE_AddSampleBlock(int *samples, Uint16 count, float v_range) {
    Uint16 i;
    for (i = 0; i < count; i++)
        FE_AddSample((float)samples[i] / 32767.0f * v_range);
}

Uint32 FE_GetSampleCount(void) { return g_total_count; }

static void simple_fft(float *real, float *imag, int n) {
    int i, j, k, m;
    for (i = 0; i < n; i++) imag[i] = 0.0f;
    j = 0;
    for (i = 1; i < n - 1; i++) {
        k = n >> 1;
        while (k <= j) { j -= k; k >>= 1; }
        j += k;
        if (i < j) { float tr = real[i]; real[i] = real[j]; real[j] = tr; }
    }
    for (m = 2; m <= n; m <<= 1) {
        float wm_r = cosf(-2.0f * 3.14159265f / m);
        float wm_i = sinf(-2.0f * 3.14159265f / m);
        for (i = 0; i < n; i += m) {
            float w_r = 1.0f, w_i = 0.0f;
            for (j = 0; j < m/2; j++) {
                int idx1 = i + j, idx2 = i + j + m/2;
                float u_r = real[idx1], u_i = imag[idx1];
                float v_r = w_r*real[idx2] - w_i*imag[idx2];
                float v_i = w_r*imag[idx2] + w_i*real[idx2];
                real[idx1] = u_r + v_r; imag[idx1] = u_i + v_i;
                real[idx2] = u_r - v_r; imag[idx2] = u_i - v_i;
                float tmp = w_r*wm_r - w_i*wm_i;
                w_i = w_r*wm_i + w_i*wm_r;
                w_r = tmp;
            }
        }
    }
}

static void sort_float(float *arr, Uint32 n) {
    Uint32 i, j;
    for (i = 0; i < n - 1; i++) {
        for (j = i + 1; j < n; j++) {
            if (arr[i] > arr[j]) {
                float tmp = arr[i];
                arr[i] = arr[j];
                arr[j] = tmp;
            }
        }
    }
}

static float lz_complexity(float *signal, Uint32 n) {
    static Uint16 binary[512];
    static float sorted[512];
    Uint32 i, nn;
    float median;
    Uint32 c, l, idx, k, kmax;

    if (n <= 1) return 0.0f;

    nn = (n > 512) ? 512 : n;
    for (i = 0; i < nn; i++) sorted[i] = signal[i];

    sort_float(sorted, nn);
    if (nn % 2 == 0) {
        median = (sorted[nn/2 - 1] + sorted[nn/2]) / 2.0f;
    } else {
        median = sorted[nn/2];
    }

    for (i = 0; i < nn; i++) {
        binary[i] = (sorted[i] > median) ? 1 : 0;
    }

    c = 1; l = 1; idx = 0; k = 1; kmax = 1;
    while (1) {
        if (idx + k >= nn || l + k >= nn) break;
        if (binary[idx + k] == binary[l + k]) {
            k++;
            if (l + k > nn) { c++; break; }
        } else {
            if (k > kmax) kmax = k;
            idx++;
            if (idx == l) {
                c++;
                l += kmax;
                if (l + 1 > nn) break;
                idx = 0; k = 1; kmax = 1;
            } else {
                k = 1;
            }
        }
    }
    return (float)c;
}

//static float lz_complexity(float *signal, Uint32 n) {
//    static Uint16 binary[512];
//    static float sorted[512];
//    Uint32 i, nn;
//    float median;
//    Uint32 c, l, idx, k, kmax;
//
//    if (n <= 1) return 0.0f;
//
//    /* 降采样 */
//    if (n > 10000) {
//        Uint32 step = n / 10000;
//        nn = n / step;
//        for (i = 0; i < nn; i++) sorted[i] = signal[i * step];
//    } else {
//        nn = n;
//        for (i = 0; i < nn; i++) sorted[i] = signal[i];
//    }
//
//    /* 排序求中位数 (与PyTorch np.median一致) */
//    sort_float(sorted, nn);
//    if (nn % 2 == 0) {
//        median = (sorted[nn/2 - 1] + sorted[nn/2]) / 2.0f;
//    } else {
//        median = sorted[nn/2];
//    }
//
//    /* 二值化 */
//    for (i = 0; i < nn; i++) {
//        binary[i] = (sorted[i] > median) ? 1 : 0;
//    }
//
//    /* LZ算法 */
//    c = 1; l = 1; idx = 0; k = 1; kmax = 1;
//    while (1) {
//        if (idx + k >= nn || l + k >= nn) break;
//        if (binary[idx + k] == binary[l + k]) {
//            k++;
//            if (l + k > nn) { c++; break; }
//        } else {
//            if (k > kmax) kmax = k;
//            idx++;
//            if (idx == l) {
//                c++;
//                l += kmax;
//                if (l + 1 > nn) break;
//                idx = 0; k = 1; kmax = 1;
//            } else {
//                k = 1;
//            }
//        }
//    }
//    return (float)c;
//}

void FE_ExtractFromBuffer(float *features) {
    float eps = 1e-10f;
    Uint32 n = g_total_count, i;
    if (n == 0) { for (i = 0; i < FEATURE_COUNT; i++) features[i] = 0.0f; return; }

    float mean_val = g_stats.sum / n;
    float rms = sqrtf(g_stats.sum_sq / n);
    float var = g_stats.sum_sq / n - mean_val * mean_val;
    float std_val = sqrtf(var > 0 ? var : 0);
    float mean_abs = g_stats.sum_abs / n;
    float sqrt_mean = g_stats.sum_sqrt / n;
    float max_abs = fmaxf(fabsf(g_stats.max_val), fabsf(g_stats.min_val));

    /* T1_energy: sum(|x|²) - 与PyTorch一致 */
    features[0] = g_stats.sum_sq;
    features[2] = mean_val;
    features[3] = rms;
    features[4] = std_val;

    /* LZ复杂度: 用全部数据，中位数二值化 */
    features[1] = lz_complexity(g_fft_buffer, (n < FFT_SIZE) ? n : FFT_SIZE);

    /* 偏度/峭度: 用全部FFT缓冲区的点 */
    float m3 = 0, m4 = 0;
    Uint32 kn = (n < FFT_SIZE) ? n : FFT_SIZE;
    for (i = 0; i < kn; i++) {
        float diff = g_fft_buffer[i] - mean_val;
        float d2 = diff * diff;
        m3 += d2 * diff;
        m4 += d2 * d2;
    }
    features[5] = (kn > 2 && std_val > eps) ? (m3/kn)/(std_val*std_val*std_val) : 0.0f;
    features[6] = (kn > 3 && std_val > eps) ? (m4/kn)/(std_val*std_val*std_val*std_val) - 3.0f : 0.0f;

    /* 无量纲因子 */
    features[7]  = (mean_abs > eps) ? rms / mean_abs : 0.0f;
    features[8]  = (sqrt_mean > eps) ? max_abs / (sqrt_mean*sqrt_mean) : 0.0f;
    features[9]  = (mean_abs > eps) ? max_abs / mean_abs : 0.0f;
    features[10] = (rms > eps) ? max_abs / rms : 0.0f;
//    features[11] = (rms > eps) ? (m4/kn)/(rms*rms*rms*rms) : 0.0f;
    features[11] = (rms > eps) ? (g_stats.sum_quad / n) / (rms*rms*rms*rms) : 0.0f;

    /* 频域特征: 用全部FFT缓冲区的点做512点FFT */
    static float fr[FFT_SIZE], fi[FFT_SIZE];
    Uint32 fn = (n < FFT_SIZE) ? n : FFT_SIZE;
    for (i = 0; i < fn; i++) fr[i] = g_fft_buffer[i];
    for (i = fn; i < FFT_SIZE; i++) fr[i] = 0.0f;
    simple_fft(fr, fi, FFT_SIZE);
    Uint32 half = FFT_SIZE / 2;
    float ps = 0, cf = 0, msf = 0, fv = 0;
    for (i = 0; i < half; i++) {
        float mag = fr[i]*fr[i] + fi[i]*fi[i];
        float freq = (float)i / FFT_SIZE * SAMPLE_FS;
        ps += mag; cf += freq * mag; msf += freq * freq * mag;
    }
    if (ps > eps) { cf /= ps; msf /= ps; }
    for (i = 0; i < half; i++) {
        float mag = fr[i]*fr[i] + fi[i]*fi[i];
        float freq = (float)i / FFT_SIZE * SAMPLE_FS;
        float psd_norm = (ps > eps) ? (mag/ps) : mag;
        fv += (freq-cf)*(freq-cf) * psd_norm;
    }
    features[12] = cf;
    features[13] = msf;
    features[14] = sqrtf(msf);
    features[15] = fv;
    features[16] = sqrtf(fv);
}

void FE_Extract(float *signal, Uint32 n, float *features) {
    FE_Reset();
    Uint32 i;
    for (i = 0; i < n; i++) FE_AddSample(signal[i]);
    FE_ExtractFromBuffer(features);
}
