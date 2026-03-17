import ftd2xx

dev = ftd2xx.open(0)

dev.resetDevice()
dev.purge()
dev.setUSBParameters(65536,65536)
dev.setLatencyTimer(2)
dev.setBitMode(0xFF,0x40)

print("Reading ADC data...")

buffer = bytearray()
counter = 0

while True:
    data = dev.read(64)

    if len(data) > 0:
        buffer.extend(data)

        while len(buffer) >= 4:

            mems = buffer[0] | (buffer[1] << 8)
            ref  = buffer[2] | (buffer[3] << 8)

            counter += 1
            if counter % 50 == 0:
                print("MEMS:", mems, "REF:", ref)

            del buffer[:4]