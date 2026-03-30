import numpy as np
# FFT-based amplitude and phase extraction for MEMS testbench
# the input signal is expected to be the raw ADC data with volt units (after conversion from digital counts)
def fft_amplitude_phase(adc1, adc2, fs, f_ref):
    """
    Extract amplitude and phase at target frequency
    """

    N = len(adc1)

    # windowing (VERY IMPORTANT)
    window = np.hanning(N)
    adc1 = adc1 * window
    adc2 = adc2 * window

    fft1 = np.fft.fft(adc1)
    fft2 = np.fft.fft(adc2)

    freqs = np.fft.fftfreq(N, d=1/fs)

    idx = np.argmin(np.abs(freqs - f_ref))

    A1 = np.abs(fft1[idx])
    A2 = np.abs(fft2[idx])

    gain = A2 / (A1 + 1e-12)
    amplitude_dB = 20 * np.log10(gain)

    phase = np.angle(fft2[idx]) - np.angle(fft1[idx])

    return amplitude_dB, phase, A2, A1