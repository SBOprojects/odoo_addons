import { Component } from "@odoo/owl";
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class OptionPopup extends Component {
    static template = "point_of_sale.OptionPopup";
    static props = {
        title: { type: String, optional: false }, // Title for the popup
        options: { type: Array, optional: false }, // Array of options { label: String, value: String }
        confirm: Function, // Function to call when an option is selected
        closePopup: Function, // Function to close the popup
    };

    setup() {
        this.selectedOption = useState({ value: null });
    }

    /**
     * Handles the confirmation when the user selects an option.
     */
    confirmSelection() {
        if (this.selectedOption.value) {
            this.props.confirm(this.selectedOption.value); // Call the confirm function with the selected value
            this.props.closePopup(); // Close the popup
        } else {
            this.env.services.notification.add(
                _t("Please select an option before proceeding."),
                { type: "warning" }
            );
        }
    }

    /**
     * Handles the cancellation of the popup.
     */
    cancelPopup() {
        this.props.closePopup();
    }
}
