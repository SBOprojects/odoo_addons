from odoo import api, fields, models


class Users(models.Model):
    """ Inherit the res.Users model and add a new field """
    _inherit = 'res.users'

    """ Theme Config for night mode """
    mode_check = fields.Boolean(string="Active",
                                help="Enable / Disable checkbox")

    @api.model
    def get_active(self):
        """ Get the value of the mode_check field """
        return self.env.user.mode_check

    @api.model
    def set_active(self):
        """ Set up the mode_check value """
        self.env.user.mode_check = True
        return self.env.user.mode_check

    @api.model
    def set_deactivate(self):
        """ Deactivating the value of mode check field """
        self.env.user.mode_check = False
        return self.env.user.mode_check
