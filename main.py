import src.ringPixel as ringPixel
import src.rotaryEncoder as rotaryEncoder

from src.screen.screen_manager import ScreenManager
from src.screen.sequencer_controller import SequencerController
from src.screen.instrument_controller import InstrumentController


import src.button as button

import sequencer
import instrument.instrument as instrument
import instrument.tb303 as tb303

from time import sleep

if __name__ == "__main__":
    pixel = ringPixel.PixelRing(pixel_pin=ringPixel.board.D21, num_pixels=16)
    encoder = rotaryEncoder.Encoder(clk_pin=17, dt_pin=18, sw_pin=27, min_position=0, max_position=16)
    freqEncoder = rotaryEncoder.Encoder(clk_pin=24, dt_pin=23, sw_pin=22, min_position=0, max_position=240)
    
    play_button = button.button(pin=13)
    shift_button = button.button(pin=16)
    prev_button = button.button(pin=15)
    next_button = button.button(pin=14)

    params = tb303.TB303Parameter(
        waveform="saw",
        cutoff=400.0,
        resonance=0.85,
        env_mod=0.7,
        decay=0.15,
    )

    seq = sequencer.sequencer()
    seq.pixel = pixel
    seq.instrument = tb303.TB303Instrument(params=params)

    screen = ScreenManager(width=128, height=64)
    seq_ctrl  = SequencerController(screen, seq)
    instrument_ctrl = InstrumentController(screen, seq.instrument)
    seq_ctrl.show_play()
    
    def encoder_rotate_callback(position):
        if seq.mode == sequencer.mode.NOTE_SELECTION:
            seq.on_selection_rotate(position)

        elif seq.mode == sequencer.mode.NOTE_EDITING:
            seq.on_edit_rotate(position)
        elif seq.mode == sequencer.mode.INSTRUMENT_EDITING:
            seq.instrument.set_parameter_value(position)
            instrument_ctrl.refresh()
        else:
            seq.on_division_rotate(position)

    def sync_frequency_encoder_range():
        if seq.mode == sequencer.mode.SEQUENCE:
            if seq.frequency_target == "volume":
                freqEncoder.set_range(0, 100, rotaryEncoder.enum.BLOCK, sync_position=seq.volume)
            else:
                bpm_position = max(0, min(240, (seq.bpm - 30) // 2))
                freqEncoder.set_range(0, 240, rotaryEncoder.enum.BLOCK, sync_position=bpm_position)
        elif seq.mode == sequencer.mode.NOTE_EDITING:
            freqEncoder.set_range(0, 100, rotaryEncoder.enum.BLOCK, sync_position=seq.selected_note_velocity)
        else:
            freqEncoder.set_range(0, 240, rotaryEncoder.enum.BLOCK, sync_position=max(0, min(240, (seq.bpm - 30) // 2)))

    encoder.on_rotate(encoder_rotate_callback)
    

    def on_division_click(position):
        seq.on_division_click(position)
        if seq.mode == sequencer.mode.NOTE_EDITING:
            # Passage en édition de note : plage MIDI 0..127 (continuous)
            encoder.set_range(0, 127, rotaryEncoder.enum.CONTINUOUS, sync_position=(seq.selected_note_value if seq.selected_note_value is not None else 0))
            seq_ctrl.show_edit()
        elif seq.mode == sequencer.mode.NOTE_SELECTION:
            # Sélection de note : plage continue selon la division
            max_pos = (seq.tracks[seq.current_track].division - 1) if seq.tracks[seq.current_track].division > 0 else 15
            encoder.set_range(0, max_pos, rotaryEncoder.enum.CONTINUOUS, sync_position=(seq.selected_note if seq.selected_note is not None else 0))
            seq_ctrl.show_note()
        elif seq.mode == sequencer.mode.INSTRUMENT_EDITING:
            # Mode édition instrument : cycler vers le paramètre suivant
            seq.instrument.cycle_parameter(1)
            info = seq.instrument.get_parameter_info(seq.instrument.params.selected_component, seq.instrument.params.selected_parameter)
            encoder.set_range(int(info["min"]), int(info["max"]), rotaryEncoder.enum.BLOCK, sync_position=int(seq.instrument.get_parameter_position()), step =info["step"])
            instrument_ctrl.on_param_select(+1)
            instrument_ctrl.refresh()
        else:
            # Mode normal (sequence) : encoder bloqué 0..16
            encoder.set_range(0, 16, rotaryEncoder.enum.BLOCK, sync_position=seq.tracks[seq.current_track].division)
            seq_ctrl.show_play()
    encoder.on_click(on_division_click)

    def on_frequency_rotate(position):
        if seq.mode == sequencer.mode.SEQUENCE:
            seq.on_frequency_rotate(position)
            sync_frequency_encoder_range()
        elif seq.mode == sequencer.mode.NOTE_EDITING:
            seq.on_velocity_rotate(position)
            sync_frequency_encoder_range()

    freqEncoder.on_rotate(on_frequency_rotate)

    def on_frequency_click(position):
        seq.on_frequency_click(position)
        if seq.mode == sequencer.mode.SEQUENCE:
            seq.toggle_frequency_target()
            sync_frequency_encoder_range()


    freqEncoder.on_click(on_frequency_click)

    def play_button_clicked():
        if seq.is_playing:
            seq.pause()
        else:
            seq.play()


    def shift_button_clicked():
        seq.mode = sequencer.mode((seq.mode.value + 1) % len(sequencer.mode))
        if seq.mode == sequencer.mode.NOTE_EDITING:
            seq.mode = sequencer.mode((seq.mode.value + 1) % len(sequencer.mode))

        if seq.mode == sequencer.mode.NOTE_SELECTION:
            max_pos = (seq.tracks[seq.current_track].division - 1) if seq.tracks[seq.current_track].division > 0 else 15
            encoder.set_range(0, max_pos, rotaryEncoder.enum.CONTINUOUS, sync_position=(seq.selected_note if seq.selected_note is not None else 0))
            seq_ctrl.show_note()
            return
        if seq.mode == sequencer.mode.INSTRUMENT_EDITING:
            info = seq.instrument.get_parameter_info(seq.instrument.params.selected_component, seq.instrument.params.selected_parameter)
            encoder.set_range(int(info["min"]), int(info["max"]), rotaryEncoder.enum.BLOCK, sync_position=int(seq.instrument.get_parameter_position()), step =info["step"])
            instrument_ctrl.set_group(seq.instrument.params.selected_component)
            print("Shift button clicked - Mode:", seq.mode)
            return
        encoder.set_range(0, 16, rotaryEncoder.enum.BLOCK, sync_position=seq.tracks[seq.current_track].division)
        seq_ctrl.show_play()

        sync_frequency_encoder_range()


    def next_button_clicked():
        print("Next button clicked")
        if seq.mode == sequencer.mode.SEQUENCE:
            seq.current_track = (seq.current_track + 1) % len(seq.tracks)
            print(f"Current track: {seq.current_track}")
        if seq.mode == sequencer.mode.INSTRUMENT_EDITING:
            seq.instrument.cycle_component(1)
            info = seq.instrument.get_parameter_info(seq.instrument.params.selected_component, seq.instrument.params.selected_parameter)
            encoder.set_range(int(info["min"]), int(info["max"]), rotaryEncoder.enum.BLOCK, sync_position=int(seq.instrument.get_parameter_position()), step =info["step"])
            instrument_ctrl.set_group(seq.instrument.params.selected_component)
            print("Next button clicked - Mode:", seq.mode)

    def prev_button_clicked():
        print("Previous button clicked")
        if seq.mode == sequencer.mode.SEQUENCE:
            seq.current_track = (seq.current_track - 1) % len(seq.tracks)
            print(f"Current track: {seq.current_track}")
        if seq.mode == sequencer.mode.INSTRUMENT_EDITING:
            seq.instrument.cycle_component(-1)
            info = seq.instrument.get_parameter_info(seq.instrument.params.selected_component, seq.instrument.params.selected_parameter)
            encoder.set_range(int(info["min"]), int(info["max"]), rotaryEncoder.enum.BLOCK, sync_position=int(seq.instrument.get_parameter_position()), step =info["step"])
            instrument_ctrl.set_group(seq.instrument.params.selected_component)
            print("Previous button clicked - Mode:", seq.mode)

    play_button.on_click(play_button_clicked)
    shift_button.on_click(shift_button_clicked)
    next_button.on_click(next_button_clicked)
    prev_button.on_click(prev_button_clicked)

    try:
        while True:
            screen.render()

            sleep(0.1)

    except KeyboardInterrupt:
        pixel.fill((0, 0, 0))