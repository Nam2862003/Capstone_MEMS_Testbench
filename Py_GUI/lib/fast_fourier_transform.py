import numpy as np

def fft_amplitude_phase(adc1, adc2, fs, f_ref):
    """
    Estimate amplitude and phase at the target frequency for the MEMS testbench.
    Applies mean removal and Hann-window amplitude correction.
    """
    adc1 = np.asarray(adc1, dtype=float)
    adc2 = np.asarray(adc2, dtype=float)

    N = len(adc1)

    if N < 4 or fs <= 0:
        return 0.0, 0.0, 0.0, 0.0

    f_ref = np.clip(f_ref, 1e-9, fs / 2)

    adc1 = adc1 - np.mean(adc1)
    adc2 = adc2 - np.mean(adc2)

    window = np.hanning(N)
    adc1_w = adc1 * window
    adc2_w = adc2 * window

    fft1 = np.fft.fft(adc1_w)
    fft2 = np.fft.fft(adc2_w)
    freqs = np.fft.fftfreq(N, d=1 / fs)

    base_idx = np.argmin(np.abs(freqs[:N // 2] - f_ref))

    # Avoid bin 0 because DC phase is not meaningful after mean removal.
    search_range = range(max(1, base_idx - 1), min(N // 2, base_idx + 2))
    idx = max(search_range, key=lambda i: np.abs(fft1[i]))

    scaling_factor = 2.0 / np.sum(window)

    A1 = np.abs(fft1[idx]) * scaling_factor
    A2 = np.abs(fft2[idx]) * scaling_factor

    gain = A2 / (A1 + 1e-12)
    amplitude_dB = 20 * np.log10(gain)

    phase_diff = np.angle(fft2[idx]) - np.angle(fft1[idx])
    phase = (phase_diff + np.pi) % (2 * np.pi) - np.pi

    return amplitude_dB, phase, A2, A1