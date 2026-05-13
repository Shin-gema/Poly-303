from src.screen.screen_controller import SceneController

class InstrumentController(SceneController):
    def __init__(self, sm, instrument):
        self.instrument      = instrument
        self.current_group   = "envelope"
        self.selected_param  = 0        # index dans le groupe courant
        super().__init__(sm)

    def _register_scenes(self):
        self.sm.register_scene("inst_params",   self._draw_params)
        self.sm.register_scene("inst_envelope", self._draw_envelope)

    # ── Navigation ────────────────────────────────────────────────────────────

    def set_group(self, group_name):
        """Change de groupe, remet la sélection à zéro."""
        self.current_group  = group_name
        self.selected_param = 0
        scene = "inst_envelope" if group_name == "envelope" else "inst_params"
        self.set_scene(scene)
        self.refresh()

    def select_param(self, index):
        params = self._get_current_params()
        self.selected_param = index % len(params)
        self.refresh()

    def on_param_select(self, direction):
        """Appelé par un encodeur : +1 / -1."""
        self.select_param(self.selected_param + direction)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_current_params(self):
        """Retourne la liste ordonnée des (key, meta) du groupe courant."""
        group = self.instrument.params._editable_params.get(self.current_group, {})
        return list(group.items())

    def _get_value(self, key):
        """Lit la valeur courante sur l'objet params."""
        return getattr(self.instrument.params, key, None)

    def _format_value(self, key, meta, value):
        if value is None:
            return "?"
        if meta["type"] == "bool":
            return "ON" if value else "OFF"
        if meta["type"] == "str":
            return str(value)
        # float
        if meta["max"] <= 1.0:
            return f"{value * 100:.0f}%"
        return f"{value:.0f}"

    # ── Scène générique (filter, oscillator, accent…) ─────────────────────────

    def _draw_params(self, sm):
        params  = self._get_current_params()
        sel     = self.selected_param

        # Header
        sm.text(0, 1, self.current_group.upper())
        sm.line(0, 10, 127, 10)

        ROW_H   = 8
        VISIBLE = 6
        half    = VISIBLE // 2
        start   = max(0, min(sel - half, len(params) - VISIBLE))
        end     = min(len(params), start + VISIBLE)

        for i in range(start, end):
            key, meta = params[i]
            value     = self._get_value(key)
            label     = key[:8].upper()
            formatted = self._format_value(key, meta, value)
            is_sel    = i == sel
            y         = 12 + (i - start) * ROW_H

            if is_sel:
                sm.draw.rectangle((0, y - 1, 127, y + ROW_H - 2), fill=1)
                fg = 0
            else:
                fg = 1

            sm.text(2,   y, label,     fill=fg)
            sm.text(75,  y, formatted, fill=fg)

            # Barre de progression
            if meta["type"] not in ("bool", "str"):
                mn, mx  = meta["min"], meta["max"]
                ratio   = (value - mn) / (mx - mn) if value is not None else 0
                bar_w   = round(ratio * 44)
                bx, by  = 78 - 46, y + 1

                if is_sel:
                    sm.draw.rectangle((bx, by, bx + 44, by + 5), fill=0, outline=0)
                    sm.draw.rectangle((bx, by, bx + bar_w, by + 5), fill=0)
                    # barre en négatif sur fond blanc
                    sm.draw.rectangle((bx + 1, by + 1, bx + bar_w - 1, by + 4), fill=0)
                else:
                    sm.draw.rectangle((bx, by, bx + 44, by + 5), outline=1, fill=0)
                    if bar_w > 0:
                        sm.draw.rectangle((bx, by, bx + bar_w, by + 5), fill=1)

            sm.text(110, y, formatted, fill=fg)

    # ── Scène enveloppe (vue courbe) ──────────────────────────────────────────

    def _draw_envelope(self, sm):
        p      = self.instrument.params
        params = self._get_current_params()   # [attack, decay, sustain, release]
        sel    = self.selected_param

        sm.text(0, 1, "ENVELOPE")
        sm.line(0, 10, 127, 10)

        x0, y0, w, h   = 2, 12, 124, 36
        sustain_hold    = 0.25
        total           = p.attack + p.decay + sustain_hold + p.release
        if total <= 0:
            total = 1.0

        def tx(val): return x0 + int(val / total * w)
        def ty(val): return y0 + h - int(val * h)

        xa = tx(p.attack)
        xd = tx(p.attack + p.decay)
        xs = tx(p.attack + p.decay + sustain_hold)
        xe = tx(total)

        points   = [
            (x0, y0 + h),
            (xa, y0),
            (xd, ty(p.sustain)),
            (xs, ty(p.sustain)),
            (xe, y0 + h),
        ]
        segments = [(0,1,0),(1,2,1),(2,3,2),(3,4,3)]

        for p_start, p_end, param_idx in segments:
            x1, y1 = points[p_start]
            x2, y2 = points[p_end]

            if param_idx != sel:
                steps = max(abs(x2-x1), abs(y2-y1), 1)
                for i in range(0, steps, 3):
                    t  = i / steps
                    px = int(x1 + t*(x2-x1))
                    py = int(y1 + t*(y2-y1))
                    sm.draw.point((px, py), fill=1)
            else:
                sm.line(x1, y1, x2, y2)

        sm.line(x0, y0 + h, xe, y0 + h)
        sm.line(0, 51, 127, 51)

        # Valeurs en bas : seulement les 4 params de l'enveloppe
        col_w = 32
        for i, (key, meta) in enumerate(params):
            value     = self._get_value(key)
            formatted = self._format_value(key, meta, value)
            x         = 2 + i * col_w
            is_sel    = i == sel

            if is_sel:
                sm.draw.rectangle((x - 1, 52, x + col_w - 2, 63), fill=1)
                fg = 0
            else:
                fg = 1

            sm.text(x,     53, key[0].upper(), fill=fg)
            sm.text(x + 7, 53, formatted,      fill=fg)