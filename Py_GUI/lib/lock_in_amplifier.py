import numpy as np
from scipy.signal import hilbert, butter, filtfilt


def lowpass_filter(signal, cutoff, fs, order=4):
    nyq = 0.5 * fs

    if cutoff >= nyq:
        cutoff = 0.45 * fs

    if cutoff <= 0:
        raise ValueError("Cutoff must be > 0")

    b, a = butter(order, cutoff / nyq, btype="low")
    return filtfilt(b, a, signal)


def _demodulate(signal, ref_cos, ref_sin, fs, cutoff, use_filter):
    x_mix = signal * ref_cos
    y_mix = signal * ref_sin

    if use_filter:
        x_mix = lowpass_filter(x_mix, cutoff, fs)
        y_mix = lowpass_filter(y_mix, cutoff, fs)

    i_val = 2.0 * np.mean(x_mix)
    q_val = 2.0 * np.mean(y_mix)
    amplitude = np.sqrt(i_val**2 + q_val**2)
    phase = np.arctan2(q_val, i_val)

    return amplitude, phase, i_val, q_val


def lock_in_amplifier(
    reference_signal,
    input_signal,
    freq,
    fs,
    use_generated=False,
    use_filter=True,
):
    """
    Digital lock-in that returns results comparable to the FFT path.

    Returns:
        amplitude_dB : input/reference gain in dB
        phase        : input-reference phase in radians
        I, Q         : input signal demodulated components
    """

    if len(reference_signal) != len(input_signal):
        raise ValueError("Signals must have same length")

    if len(input_signal) == 0:
        raise ValueError("Signal is empty")

    ref_sig = reference_signal - np.mean(reference_signal)
    input_sig = input_signal - np.mean(input_signal)

    n_samples = len(input_sig)

    if use_generated:
        t = np.arange(n_samples) / fs
        ref_cos = np.cos(2 * np.pi * freq * t)
        ref_sin = np.sin(2 * np.pi * freq * t)
    else:
        ref_rms = np.sqrt(np.mean(ref_sig**2))
        if ref_rms == 0:
            raise ValueError("Reference signal has zero amplitude")

        ref_cos = ref_sig / ref_rms
        analytic = hilbert(ref_cos)
        ref_sin = np.imag(analytic)

    # After mixing, the desired component is near DC and the undesired term is near 2*f.
    # Keep the LPF comfortably below 2*f while still tracking the sweep point.
    min_bandwidth = max(fs / n_samples, 1.0)
    cutoff = min(max(freq * 0.25, min_bandwidth), 0.45 * fs)

    ref_amp, ref_phase, _, _ = _demodulate(ref_sig, ref_cos, ref_sin, fs, cutoff, use_filter)
    input_amp, input_phase, i_val, q_val = _demodulate(
        input_sig, ref_cos, ref_sin, fs, cutoff, use_filter
    )

    gain = input_amp / (ref_amp + 1e-12)
    amplitude_dB = 20 * np.log10(max(gain, 1e-12))
    phase = np.angle(np.exp(1j * (input_phase - ref_phase)))

    return amplitude_dB, phase, i_val, q_val
