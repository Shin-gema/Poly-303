import src.ringPixel as ringPixel
import src.rotaryEncoder as rotaryEncoder
import src.screen as screen

import src.button as button

import observer
import sequencer
import instrument.instrument as instrument
import instrument.tb303 as tb303

from time import sleep

if __name__ == "__main__":
    pixel = ringPixel.PixelRing(pixel_pin=ringPixel.board.D21, num_pixels=16)
    encoder = rotaryEncoder.Encoder(clk_pin=17, dt_pin=18, sw_pin=27, min_position=0, max_position=16)
    freqEncoder = rotaryEncoder.Encoder(clk_pin=24, dt_pin=23, sw_pin=22, min_position=0, max_position=240)

    screen_manager = screen.ScreenManager(width=128, height=64)
    
    play_button = button.button(pin=13)
    shift_button = button.button(pin=16)
    prev_button = button.button(pin=15)
    next_button = button.button(pin=14)


    def render_play_scene(manager):
        manager.draw_rectangle(0, 17, 127, 30)

    def render_note_scene(manager):
        manager.draw_rectangle(0, 17, 127, 30)

    screen_manager.add_scene("play", [
        {"type": "text", "x": 5, "y": 5, "text": "Mode : Sequence"},
        {"type": "text", "x": 5, "y": 19, "text": "Division : {division}"},
        {"type": "text", "x": 5, "y": 34, "text": "BPM : {bpm}{bpm_arrow}"},
        {"type": "text", "x": 5, "y": 45, "text": "Volume : {volume}{volume_arrow}"}
    ], variables={"division": 0, "bpm": 120, "status": "pause", "volume": 100, "bpm_arrow": " <-", "volume_arrow": ""}, render_callback=render_play_scene)

    screen_manager.add_scene("note", [
        {"type": "text", "x": 5, "y": 5, "text": "Mode : Note"},
        {"type": "text", "x": 5, "y": 19, "text": "Selected note : {selected_note}"},
        {"type": "text", "x": 5, "y": 34, "text": "Note MIDI : {note_name} - {selected_note_value}"},
        {"type": "text", "x": 5, "y": 45, "text": "Note velocite : {note_velocity}"}
    ], variables={"selected_note": "-", "note_name": "-", "selected_note_value": "-", "note_velocity": 100}, render_callback=render_note_scene)

    screen_manager.set_scene("play")

    params = tb303.TB303Params(
        waveform="saw",
        cutoff=400.0,
        resonance=0.85,
        env_mod=0.7,
        decay=0.15,
    )

    seq = sequencer.sequencer()
    seq.pixel = pixel
    seq.screen_manager = screen_manager
    seq.instrument = tb303.TB303Instrument(params=params)
    
    # Attacher les callbacks
    def encoder_rotate_callback(position):
        if seq.mode == sequencer.mode.NOTE_SELECTION:
            seq.on_selection_rotate(position)
            screen_manager.set_variable("selected_note", seq.selected_note if seq.selected_note is not None else "-", scene_name="note")
            screen_manager.set_variable("note_name", seq.midi_note_to_name(seq.selected_note_value), scene_name="note")
            screen_manager.set_variable("selected_note_value", seq.selected_note_value if seq.selected_note_value is not None else "-", scene_name="note")
            screen_manager.set_variable("note_velocity", seq.selected_note_velocity, scene_name="note")
        elif seq.mode == sequencer.mode.NOTE_EDITING:
            seq.on_edit_rotate(position)
            screen_manager.set_variable("note_name", seq.midi_note_to_name(seq.selected_note_value), scene_name="note")
            screen_manager.set_variable("selected_note_value", seq.selected_note_value if seq.selected_note_value is not None else "-", scene_name="note")
        else:
            seq.on_division_rotate(position)
            screen_manager.set_variable("division", seq.tracks[0].division, scene_name="play")
            screen_manager.set_variable("division", seq.tracks[0].division, scene_name="note")

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
        elif seq.mode == sequencer.mode.NOTE_SELECTION:
            # Sélection de note : plage continue selon la division
            max_pos = (seq.tracks[0].division - 1) if seq.tracks[0].division > 0 else 15
            encoder.set_range(0, max_pos, rotaryEncoder.enum.CONTINUOUS, sync_position=(seq.selected_note if seq.selected_note is not None else 0))
        else:
            # Mode normal (sequence) : encoder bloqué 0..16
            encoder.set_range(0, 16, rotaryEncoder.enum.BLOCK, sync_position=seq.tracks[0].division)
    encoder.on_click(on_division_click)

    def on_frequency_rotate(position):
        if seq.mode == sequencer.mode.SEQUENCE:
            seq.on_frequency_rotate(position)
            screen_manager.set_variable("bpm", seq.bpm, scene_name="play")
            screen_manager.set_variable("volume", seq.volume, scene_name="play")
            screen_manager.set_variable("frequency_target", seq.frequency_target, scene_name="play")
            sync_frequency_encoder_range()
        elif seq.mode == sequencer.mode.NOTE_EDITING:
            seq.on_velocity_rotate(position)
            screen_manager.set_variable("note_velocity", seq.selected_note_velocity, scene_name="note")
            sync_frequency_encoder_range()

    freqEncoder.on_rotate(on_frequency_rotate)

    def on_frequency_click(position):
        seq.on_frequency_click(position)
        if seq.mode == sequencer.mode.SEQUENCE:
            seq.toggle_frequency_target()
            screen_manager.set_variable("frequency_target", seq.frequency_target, scene_name="play")
            sync_frequency_encoder_range()

    freqEncoder.on_click(on_frequency_click)

    def play_button_clicked():
        if seq.is_playing:
            seq.pause()
        else:
            seq.play()

    def sync_scene_to_state():
        target_scene = "note" if seq.mode != sequencer.mode.SEQUENCE else "play"
        if screen_manager.current_scene != target_scene:
            screen_manager.set_scene(target_scene)

        bpm_arrow = " <-" if seq.mode == sequencer.mode.SEQUENCE and seq.frequency_target == "bpm" else ""
        volume_arrow = " <-" if seq.mode == sequencer.mode.SEQUENCE and seq.frequency_target == "volume" else ""

        screen_manager.set_variable("bpm", seq.bpm, scene_name="play")
        screen_manager.set_variable("volume", seq.volume, scene_name="play")
        screen_manager.set_variable("division", seq.tracks[0].division, scene_name="play")
        screen_manager.set_variable("status", "play" if seq.is_playing else "pause", scene_name="play")
        screen_manager.set_variable("bpm_arrow", bpm_arrow, scene_name="play")
        screen_manager.set_variable("volume_arrow", volume_arrow, scene_name="play")
        screen_manager.set_variable("selected_note", seq.selected_note if seq.selected_note is not None else "-", scene_name="note")
        screen_manager.set_variable("note_name", seq.midi_note_to_name(seq.selected_note_value), scene_name="note")
        screen_manager.set_variable("note_velocity", seq.selected_note_velocity, scene_name="note")
        sync_frequency_encoder_range()

    def shift_button_clicked():
        seq.mode = sequencer.mode.NOTE_SELECTION if seq.mode == sequencer.mode.SEQUENCE else sequencer.mode.SEQUENCE
        if seq.mode == sequencer.mode.NOTE_SELECTION:
            max_pos = (seq.tracks[0].division - 1) if seq.tracks[0].division > 0 else 15
            encoder.set_range(0, max_pos, rotaryEncoder.enum.CONTINUOUS, sync_position=(seq.selected_note if seq.selected_note is not None else 0))
        else:
            encoder.set_range(0, 16, rotaryEncoder.enum.BLOCK, sync_position=seq.tracks[0].division)

        sync_scene_to_state()
        sync_frequency_encoder_range()
        print("Shift button clicked - Mode:", seq.mode)

    def next_button_clicked():
        print("Next button clicked")
        seq.current_track = (seq.current_track + 1) % len(seq.tracks)
        print(f"Current track: {seq.current_track}")
        sync_scene_to_state()

    def prev_button_clicked():
        print("Previous button clicked")
        seq.current_track = (seq.current_track - 1) % len(seq.tracks)
        print(f"Current track: {seq.current_track}")
        sync_scene_to_state()

    play_button.on_click(play_button_clicked)
    shift_button.on_click(shift_button_clicked)
    next_button.on_click(next_button_clicked)
    prev_button.on_click(prev_button_clicked)

    try:
        while True:
            sync_scene_to_state()
            screen_manager.render_template()
    except KeyboardInterrupt:
        pixel.fill((0, 0, 0))