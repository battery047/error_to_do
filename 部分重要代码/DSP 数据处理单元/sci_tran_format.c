void send_features(float *features, Uint16 uart) {
    Uint16 buf[76];
    Uint16 i;

    buf[0] = 0xAA; buf[1] = 0x55; buf[2] = 0x21; buf[3] = 0x00; buf[4] = 0x44;

    for (i = 0; i < 17; i++) {
        Uint32 raw = *((Uint32*)&features[i]);
        buf[5 + i*4 + 0] = raw & 0xFF;
        buf[5 + i*4 + 1] = (raw >> 8) & 0xFF;
        buf[5 + i*4 + 2] = (raw >> 16) & 0xFF;
        buf[5 + i*4 + 3] = (raw >> 24) & 0xFF;
    }

    Uint16 cs = 0;
    for (i = 0; i < 73; i++) cs += buf[i];
    buf[73] = cs & 0xFF;
    buf[74] = 0x55;
    buf[75] = 0xAA;

    if (uart == 0) {
        for (i = 0; i < 76; i++) SCIB_SendChar(buf[i]);
    } else {
        for (i = 0; i < 76; i++) SCIC_SendChar(buf[i]);
    }
}

void send_process_time(Uint16 uart, float time_ms) {
    Uint16 buf[13];
    Uint16 i;

    buf[0] = 0xAA; buf[1] = 0x55; buf[2] = 0x05; buf[3] = 0x00; buf[4] = 0x04;

    Uint32 raw = *(Uint32*)&time_ms;
    buf[5] = raw & 0xFF; buf[6] = (raw >> 8) & 0xFF;
    buf[7] = (raw >> 16) & 0xFF; buf[8] = (raw >> 24) & 0xFF;

    Uint16 cs = 0;
    for (i = 0; i < 9; i++) cs += buf[i];
    buf[9] = cs & 0xFF;
    buf[10] = 0x55;
    buf[11] = 0xAA;

    if (uart == 0) {
        for (i = 0; i < 12; i++) SCIB_SendChar(buf[i]);
    } else {
        for (i = 0; i < 12; i++) SCIC_SendChar(buf[i]);
    }
}