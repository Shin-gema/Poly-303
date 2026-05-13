from src.screen.screen_controller import SceneController

class SequencerController(SceneController):

    def __init__(self, sm, seq):
        self.seq = seq
        super().__init__(sm)

    def _register_scenes(self):
        self.sm.register_scene("seq_play", self._draw_play)
        self.sm.register_scene("seq_note", self._draw_note)
        self.sm.register_scene("seq_edit", self._draw_edit)

    # ── Activation ────────────────────────────────────────────────────────────

    def show_play(self):
        self.set_scene("seq_play")
        self.refresh()

    def show_note(self):
        self.set_scene("seq_note")
        self.refresh()

    def show_edit(self):
        self.set_scene("seq_edit")
        self.refresh()

    def show_instrument(self):
        # TODO : faire une classe InstrumentController pour gérer ça
        pass

    # ── Draw functions ────────────────────────────────────────────────────────

    def _draw_play(self, sm):
        t = self.seq.tracks[self.seq.current_track]
        sm.text(0, 0, f"Seq - playing: {'Yes' if self.seq.is_playing else 'No'}")
        sm.line(0, 12, 127, 12)
        sm.text(0, 12,  f"BPM:{self.seq.bpm} {'*' if self.seq.frequency_target == 'bpm' else ''}")
        sm.vline(64, 12, 24)  # Séparateur BPM/Volume
        sm.text(66, 12, f"Vol:{self.seq.volume} {'*' if self.seq.frequency_target == 'volume' else ''}")
        sm.line(0, 24, 127, 24)
        col_width = 128 // 4
        for i in range(4):
            track_idx = i
            if track_idx < len(self.seq.tracks):
                sm.vline((i + 1) * col_width, 24, 64)
                track = self.seq.tracks[track_idx]
                sm.text(i * col_width + 2, 28, f"T{track_idx + 1}")
                sm.text(i * col_width + 2, 39, f"D:{track.division}")
        ## display ^ for the selected track
        if self.seq.current_track is not None:
            sm.text(self.seq.current_track * col_width + 12, 48, "*")

    def _draw_note(self, sm):
        t         = self.seq.tracks[self.seq.current_track]
        pattern   = t.pattern
        selected  = self.seq.selected_note or 0
        division  = t.division

        ROW_H     = 12
        VISIBLE   = 4          # nombre de lignes affichables
        COL_IDX   = 2          # x : numéro de note
        COL_NAME  = 16         # x : nom de note
        COL_VEL   = 50         # x : barre de vélocité
        COL_VAL   = 100        # x : valeur numérique vélocité
        BAR_MAX_W = 46         # largeur max de la barre

        # Header
        sm.text(0, 0, f"T{self.seq.current_track + 1}  NOTE {selected + 1}/{division}")
        sm.line(0, 10, 127, 10)

        # Fenêtre glissante centrée sur la sélection
        half    = VISIBLE // 2
        start   = max(0, min(selected - half, division - VISIBLE))
        end     = min(division, start + VISIBLE)

        for i in range(start, end):
            y      = 12 + (i - start) * ROW_H
            midi   = pattern[i] if i < len(pattern) else 0
            note   = self.seq.midi_note_to_name(midi)
            is_sel = i == selected

            if is_sel:
                # Inversion vidéo
                sm.draw.rectangle(
                    (0, y - 1, 127, y + ROW_H - 2),
                    fill=1
                )
                fg = 0    # texte noir sur fond blanc
            else:
                fg = 1    # texte blanc sur fond noir

            sm.text(COL_IDX,  y, str(i + 1),  fill=fg)
            sm.text(COL_NAME, y, note,         fill=fg)

            # Barre de vélocité
            vel_w = round(t.velocity / 100 * BAR_MAX_W)
            if is_sel:
                sm.draw.rectangle((COL_VEL, y + 1, COL_VEL + BAR_MAX_W, y + ROW_H - 3), fill=0)
                sm.draw.rectangle((COL_VEL, y + 1, COL_VEL + vel_w,     y + ROW_H - 3), fill=0, outline=0)
                # barre en négatif : on redessine en noir sur le fond blanc
                sm.draw.rectangle((COL_VEL, y + 2, COL_VEL + vel_w,     y + ROW_H - 3), fill=0)
            else:
                sm.draw.rectangle((COL_VEL, y + 2, COL_VEL + BAR_MAX_W, y + ROW_H - 3), outline=1, fill=0)
                sm.draw.rectangle((COL_VEL, y + 2, COL_VEL + vel_w,     y + ROW_H - 3), fill=1)

            sm.text(COL_VAL, y, str(t.velocity), fill=fg)

    def _draw_edit(self, sm):
        t      = self.seq.tracks[self.seq.current_track]
        idx    = self.seq.selected_note or 0
        midi   = self.seq.selected_note_value or 0
        note   = self.seq.midi_note_to_name(midi)
        vel    = t.velocity
        octave = (midi // 12) - 1
        semi   = midi % 12

        sm.text(0, 1, f"EDIT  NOTE {idx + 1}/{t.division}")
        sm.line(0, 12, 127, 12)

        sm.text(0, 15, f"{note}  midi:{midi}")
        sm.line(0, 26, 127, 26)

        sm.text(0, 29, f"Vel  {vel}")

        BAR_X, BAR_Y, BAR_H = 2, 41, 6
        BAR_W  = 124
        filled = round(vel / 100 * BAR_W)

        sm.draw.rectangle(
            (BAR_X, BAR_Y, BAR_X + BAR_W, BAR_Y + BAR_H),
            fill=0, outline=1
        )
        if filled > 0:
            sm.draw.rectangle(
                (BAR_X, BAR_Y, BAR_X + filled, BAR_Y + BAR_H),
                fill=1
            )

        sm.line(0, 50, 127, 50)

        sm.text(0,  52, f"oct {octave}")
        sm.text(50, 52, f"semi {semi}")