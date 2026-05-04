class CommandSenderMixin:
    def start_aq(self):
        return self.send("START ADC")

    def stop_aq(self):
        return self.send("STOP ADC")

    def set_buffer(self, size):
        return self.send(f"BUF,{size}")

    def set_sampling_rate(self, rate):
        return self.send(f"ADC SAMP,{rate}")

    def set_adc_resolution(self, resolution):
        if isinstance(resolution, str):
            resolution = resolution.strip().replace("-bit", "")

        resolution = int(resolution)
        if resolution not in (10, 12, 14, 16):
            return False

        return self.send(f"ADC RES,{resolution}")

    def start_gen(self):
        return self.send("DAC START")

    def stop_gen(self):
        return self.send("DAC STOP")

    def set_dac_freq(self, freq):
        return self.send(f"DAC FREQ,{freq}")

    def set_board_mode(self, mode, send_now=True):
        normalized = str(mode).strip().upper()
        if normalized not in {"PE", "PR"}:
            raise ValueError(f"Unsupported board mode: {mode}")

        self.board_mode = normalized

        if send_now:
            return self.send(f"MODE,{normalized}")
        return True

    def sync_board_mode(self):
        return self.send(f"MODE,{self.board_mode}")

    def set_actuator_mode(self, mode, send_now=True):
        normalized = str(mode).strip().upper()
        if normalized not in {"DDS", "FG", "STM32"}:
            raise ValueError(f"Unsupported actuator mode: {mode}")

        self.actuator_mode = normalized

        if send_now:
            return self.send(f"ACTUATOR,{normalized}")
        return True

    def sync_actuator_mode(self):
        return self.send(f"ACTUATOR,{self.actuator_mode}")

    def set_pe_gain(self, gain_index, send_now=True):
        index = int(gain_index)
        if index < 0 or index > 3:
            raise ValueError(f"Unsupported PE gain index: {gain_index}")

        self.pe_gain_index = index
        if send_now:
            return self.send(f"PE GAIN,{index}")
        return True

    def sync_pe_gain(self):
        return self.send(f"PE GAIN,{self.pe_gain_index}")

    def reset_outputs_to_default(self):
        ok = True
        ok = self.stop_aq() and ok
        ok = self.stop_gen() and ok
        ok = self.set_board_mode("PE") and ok
        ok = self.set_actuator_mode("STM32") and ok
        ok = self.set_pe_gain(0) and ok
        return ok
