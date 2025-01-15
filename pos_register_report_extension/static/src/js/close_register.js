/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/close_pos_popup";

patch(ClosePosPopup.prototype, "pos_close_register_extension.ClosePosPopup", {
    setup() {
        this._super(...arguments);
        console.log('pos_close_register_extension: ClosePosPopup setup');
    },
    willStart() {
        console.log('pos_close_register_extension: ClosePosPopup willStart');
        return this._super(...arguments);
    },
});