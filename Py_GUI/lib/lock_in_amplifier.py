import numpy as np
from scipy.signal import hilbert, butter, filtfilt


# ---------------- LOW PASS FILTER ----------------
def lowpass_filter(signal, cutoff, fs, order=4):
    nyq = 0.5 * fs # Nyquist frequency ()

    if cutoff >= nyq:
        cutoff = 0.45 * fs

    if cutoff <= 0:
        raise ValueError("Cutoff must be > 0")

    b, a = butter(order, cutoff / nyq, btype='low')
    return filtfilt(b, a, signal)


# ---------------- LOCK-IN AMPLIFIER ----------------
def lock_in_amplifier(reference_signal,
                     input_signal,
                     freq,
                     fs,
                     use_generated=False,
                     use_filter=True):
    """
    Research-grade digital lock-in amplifier

    Parameters:
        reference_signal : measured reference (e.g. DAC output)
        input_signal     : measured signal (e.g. MEMS)
        freq             : reference frequency (Hz)
        fs               : sampling frequency (Hz)
        use_generated    : use ideal sin/cos instead of measured reference
        use_filter       : apply low-pass filter

    Returns:
        amplitude (Volts)
        phase (radians)
        I, Q (debug)
    """

    if len(reference_signal) != len(input_signal):
        raise ValueError("Signals must have same length")

    if len(input_signal) == 0:
        raise ValueError("Signal is empty")

    # -------- REMOVE DC OFFSET --------
    ref_sig = reference_signal - np.mean(reference_signal)
    input_sig = input_signal - np.mean(input_signal)

    N = len(input_sig)

    # -------- REFERENCE GENERATION --------
    if use_generated:
        t = np.arange(N) / fs
        ref_cos = np.cos(2 * np.pi * freq * t)
        ref_sin = np.sin(2 * np.pi * freq * t)

    else:
        # Normalize reference (RMS = 1)
        rms = np.sqrt(np.mean(ref_sig**2))
        if rms == 0:
            raise ValueError("Reference signal has zero amplitude")

        ref_cos = ref_sig / (rms * np.sqrt(2))

        # Hilbert transform → perfect quadrature
        analytic = hilbert(ref_cos)
        ref_sin = np.imag(analytic)

        # Optional: normalize input same way
        input_sig = input_sig / (rms * np.sqrt(2))

    # -------- MIXING --------
    X = input_sig * ref_cos
    Y = input_sig * ref_sin

    # -------- LOW-PASS FILTER --------
    if use_filter:
        cutoff = min(freq * 2, 0.45 * fs) # 2x reference or 0.45*fs
        X = lowpass_filter(X, cutoff, fs)
        Y = lowpass_filter(Y, cutoff, fs)

    # -------- DEMODULATION --------
    I = (2.0 / N) * np.sum(X)
    Q = (2.0 / N) * np.sum(Y)

    # -------- OUTPUT --------
    amplitude = np.sqrt(I**2 + Q**2)
    phase = np.arctan2(Q, I)

    return amplitude, phase, I, Q