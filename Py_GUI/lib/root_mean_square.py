import numpy as np
# RMS amplitude and gain calculations for MEMS testbench
# the input signal is expected to be the raw ADC data with volt units (after conversion from digital counts)
def rms_amplitude(signal):
    """
    Compute RMS amplitude of a signal (Volts)
    """
    signal = signal - np.mean(signal)
    return np.sqrt(np.mean(signal**2))


def compute_rms_amplitude(adc1, adc2):
    """
    Compute RMS amplitude for two signals
    """
    v_ref = rms_amplitude(adc1)
    v_sig = rms_amplitude(adc2)
    amp_dB = 20 * np.log10(v_sig / (v_ref + 1e-12))  # add small value to avoid log(0)
    return amp_dB, v_sig, v_ref