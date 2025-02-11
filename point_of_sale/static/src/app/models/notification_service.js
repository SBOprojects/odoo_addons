import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
// kad_shahd

export class NotificationUtility extends Component{

    setup() {
        // Initialize the notification service
        this.notification = useService("notification");

        // Check if the service is available before proceeding
        if (!this.notification) {
            console.error("Notification service not available.");
            return;
        }
    }

    success() {
        if (this.notification) {
            this.notification.add("Cashier not found, unable to proceed.", { type: "warning" });
        }
    }

    error() {
        if (this.notification) {
            this.notification.add("Cashier not found, unable to proceed.", { type: "warning" });
        }
    }

    warning() {
        if (this.notification) {
            this.notification.add("Cashier not found, unable to proceed.", { type: "warning" });
        }
    }

    info() {
        if (this.notification) {
            this.notification.add("Cashier not found, unable to proceed.", { type: "warning" });
        }
    }
}
