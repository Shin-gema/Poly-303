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

    def sync_encoder():
        mode = seq.mode
        
        def get_note_editing_range():
            pos = seq.tracks[seq.current_track].pattern[seq.selected_note] if seq.selected_note is not None and seq.tracks[seq.current_track].pattern else 0
            encoder.set_range(
                0, 
                127, 
                rotaryEncoder.enum.CONTINUOUS, 
                sync_position=pos
            )
        
        def get_note_selection_range():
            max_pos = (seq.tracks[seq.current_track].division - 1) if seq.tracks[seq.current_track].division > 0 else 15
            encoder.set_range(
                0, 
                max_pos, 
                rotaryEncoder.enum.CONTINUOUS, 
                sync_position=(seq.selected_note or 0)
            )
            freqEncoder.set_range(
                0, 
                100, 
                rotaryEncoder.enum.BLOCK, 
                sync_position=seq.tracks[seq.current_track].velocity
            )
        
        def get_instrument_editing_range():
            info = seq.instrument.get_parameter_info(
                seq.instrument.params.selected_component, 
                seq.instrument.params.selected_parameter
            )
            encoder.set_range(
                int(info["min"]), int(info["max"]), 
                rotaryEncoder.enum.BLOCK, 
                sync_position=int(seq.instrument.get_parameter_position()), 
                step=info["step"]
            )
        
        def get_sequence_range():
            encoder.set_range(
                0,
                16,
                rotaryEncoder.enum.BLOCK, 
                sync_position=seq.tracks[seq.current_track].division
            )
            if seq.frequency_target == "volume":
                freqEncoder.set_range(
                    0, 
                    100, 
                    rotaryEncoder.enum.BLOCK, 
                    sync_position=seq.volume
                )
            else:
                bpm_position = max(0, min(240, (seq.bpm - 30) // 2))
                freqEncoder.set_range(
                    0, 
                    240, 
                    rotaryEncoder.enum.BLOCK, 
                    sync_position=bpm_position
                )
        
        switch = {
            sequencer.mode.NOTE_EDITING: get_note_editing_range,
            sequencer.mode.NOTE_SELECTION: get_note_selection_range,
            sequencer.mode.INSTRUMENT_EDITING: get_instrument_editing_range,
            sequencer.mode.SEQUENCE: get_sequence_range,
        }
        
        action = switch.get(mode)
        if action:
            action()
        
    def encoder_rotate_callback(position):
        switch = {
            sequencer.mode.SEQUENCE: lambda: seq.on_division_rotate(position),
            sequencer.mode.NOTE_SELECTION: lambda: seq.on_selection_rotate(position),
            sequencer.mode.NOTE_EDITING: lambda: seq.on_edit_rotate(position),
            sequencer.mode.INSTRUMENT_EDITING: lambda: seq.instrument.set_parameter_value(position),
        }
        action = switch.get(seq.mode)
        if action:
            action()

    def on_division_click(position):
        seq.on_division_click(position)

        def inst_clk_callback(position):
            seq.instrument.cycle_parameter(1)
            instrument_ctrl.on_param_select(+1)
            instrument_ctrl.refresh()
        
        switch = {
            sequencer.mode.SEQUENCE: lambda: seq_ctrl.show_play(),
            sequencer.mode.NOTE_SELECTION: lambda: seq_ctrl.show_note(),
            sequencer.mode.NOTE_EDITING: lambda: seq_ctrl.show_edit(),
            sequencer.mode.INSTRUMENT_EDITING: lambda: inst_clk_callback(position),
        }       
        action = switch.get(seq.mode)
        if action:            
            action()
        sync_encoder()

    encoder.on_rotate(encoder_rotate_callback)
    encoder.on_click(on_division_click)


    def on_frequency_rotate(position):
        switch = {
            sequencer.mode.SEQUENCE: lambda: seq.on_frequency_rotate(position),
            sequencer.mode.NOTE_EDITING: lambda: seq.on_velocity_rotate(position),
        }
        action = switch.get(seq.mode)
        if action:            
            action()
        
    def on_frequency_click(position):
        switch = {
            sequencer.mode.SEQUENCE: lambda: seq.on_frequency_click(position),
        }        
        action = switch.get(seq.mode)
        if action:
            action()

    freqEncoder.on_rotate(on_frequency_rotate)
    freqEncoder.on_click(on_frequency_click)


    def play_button_clicked():
        if seq.is_playing:
            seq.pause()
        else:
            seq.play()

    play_button.on_click(play_button_clicked)


    def shift_button_clicked():
        seq.mode = sequencer.mode((seq.mode.value + 1) % len(sequencer.mode))
        if seq.mode == sequencer.mode.NOTE_EDITING:
            seq.mode = sequencer.mode((seq.mode.value + 1) % len(sequencer.mode))

        switch = {
            sequencer.mode.SEQUENCE: lambda: seq_ctrl.show_play(),
            sequencer.mode.NOTE_SELECTION: lambda: seq_ctrl.show_note(),
            sequencer.mode.INSTRUMENT_EDITING: lambda: instrument_ctrl.set_group(seq.instrument.params.selected_component),
        }
        action = switch.get(seq.mode)
        if action:
            action()
        
        sync_encoder()

    shift_button.on_click(shift_button_clicked)


    def next_button_clicked():
        def inst_clk_callback(position):
            seq.instrument.cycle_component(1)
            instrument_ctrl.set_group(seq.instrument.params.selected_component)
            instrument_ctrl.refresh()

        switch = {
            sequencer.mode.SEQUENCE: lambda: setattr(seq, 'current_track', (seq.current_track + 1) % len(seq.tracks)),
            sequencer.mode.INSTRUMENT_EDITING: lambda: inst_clk_callback(None),
        }
        action = switch.get(seq.mode)
        if action:
            action()
    
    next_button.on_click(next_button_clicked)


    def prev_button_clicked():
        def inst_clk_callback(position):
            seq.instrument.cycle_component(-1)
            instrument_ctrl.set_group(seq.instrument.params.selected_component)
            instrument_ctrl.refresh()

        switch = {
            sequencer.mode.SEQUENCE: lambda: setattr(seq, 'current_track', (seq.current_track - 1) % len(seq.tracks)),
            sequencer.mode.INSTRUMENT_EDITING: lambda: inst_clk_callback(None),
        }
        action = switch.get(seq.mode)
        if action:            
            action()

    prev_button.on_click(prev_button_clicked)

    try:
        while True:
            screen.render()

            sleep(0.1)

    except KeyboardInterrupt:
        pixel.fill((0, 0, 0))