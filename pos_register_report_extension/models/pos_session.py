# pos_close_register_extension/models/pos_session.py
from odoo import models

class PosSession(models.Model):
    _inherit = "pos.session"

    def action_pos_session_close(self):
        # Your custom Python logic before closing
        print("Custom actions before closing the session")

        res = super().action_pos_session_close()

        # Your custom Python logic after closing
        print("Custom actions after closing the session")

        return res