import { _t } from "@web/core/l10n/translation";
import { useErrorHandlers, useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";
import { useService } from "@web/core/utils/hooks";

import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useState, onMounted } from "@odoo/owl";
import { PaymentScreen } from '@point_of_sale/app/screens/payment_screen/payment_screen';
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
        this.invoiceService = useService("account_move");
        this.notification = useService("notification");
        this.hardwareProxy = useService("hardware_proxy");
        this.printer = useService("printer");
        this.payment_methods_from_config = this.pos.config.payment_method_ids
            .slice()
            .sort((a, b) => a.sequence - b.sequence);
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use(this._getNumberBufferConfig);
        useErrorHandlers();
        this.payment_interface = null;
        this.error = false;
        this.pos.validateOrder = this.validateOrder.bind(this);
        this.pos.currentOrder = this.currentOrder

    },


    // kad_shahd
    get allPaymentsAreCash() {
        return this.paymentLines.every(line => line.payment_method_id.type === 'cash');
    },


    // kad_shahd
    get allPaymentsAreBank() {
        return this.paymentLines.every(line => line.payment_method_id.type === 'bank');
    },

    isPaymentComplete() {
        return this.currentOrder.get_due() === 0;
    },




    // kad_shahd :edit  to handel case terminal nayax 
    addNewPaymentLine(paymentMethod) {

        console.log(this.currentOrder.get_due());

        if (
            paymentMethod.type === "pay_later" &&
            (!this.currentOrder.to_invoice ||
                this.pos.data["ir.module.module"].find((m) => m.name === "pos_settle_due")
                    ?.state !== "installed")
        ) {
            this.notification.add(
                _t(
                    "To ensure due balance follow-up, generate an invoice or download the accounting application. "
                ),
                { autocloseDelay: 7000, title: _t("Warning") }
            );
        }


        if (paymentMethod.use_payment_terminal === "nayax") {
            const result = this.currentOrder.add_paymentline(paymentMethod);
            // if (!this.currentOrder.check_paymentlines_rounding()) {
            //     this._display_popup_error_paymentlines_rounding();
            // }

            if (result) {
                this.numberBuffer.reset();
                // Skip sending payment request for Nayax
                console.log("Payment line added for Nayax, but no request sent.");
                return true;
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t("There is already an electronic payment in progress."),
                });
                return false;
            }
        }



        if (this.pos.paymentTerminalInProgress && paymentMethod.use_payment_terminal) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("There is already an electronic payment in progress."),
            });
            return;
        }

        // original function: click_paymentmethods
        const result = this.currentOrder.add_paymentline(paymentMethod);
        // if (!this.currentOrder.check_paymentlines_rounding()) {
        //     this._display_popup_error_paymentlines_rounding();
        // }

        if (result) {
            this.numberBuffer.reset();
            if (paymentMethod.use_payment_terminal) {
                const newPaymentLine = this.paymentLines.at(-1);
                this.sendPaymentRequest(newPaymentLine);
            }
            return true;
        } else {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("There is already an electronic payment in progress."),
            });
            return false;
        }


    },
    updateSelectedPaymentline(amount = false) {
        if (this.paymentLines.every((line) => line.paid)) {
            this.currentOrder.add_paymentline(this.payment_methods_from_config[0]);
        }
        if (!this.selectedPaymentLine) {
            return;
        } // do nothing if no selected payment line
        if (amount === false) {
            if (this.numberBuffer.get() === null) {
                amount = null;
            } else if (this.numberBuffer.get() === "") {
                amount = 0;
            } else {
                amount = this.numberBuffer.getFloat();
            }
        }
        // disable changing amount on paymentlines with running or done payments on a payment terminal
        const payment_terminal = this.selectedPaymentLine.payment_method_id.payment_terminal;
        const hasCashPaymentMethod = this.payment_methods_from_config.some(
            (method) => method.type === "cash"
        );
        if (
            !hasCashPaymentMethod &&
            amount > this.currentOrder.get_due() + this.selectedPaymentLine.amount
        ) {
            this.selectedPaymentLine.set_amount(0);
            this.numberBuffer.set(this.currentOrder.get_due().toString());
            amount = this.currentOrder.get_due();
            this.showMaxValueError();
        }
        if (
            payment_terminal &&
            !["pending", "retry"].includes(this.selectedPaymentLine.get_payment_status())
        ) {
            return;
        }
        if (amount === null) {
            this.deletePaymentLine(this.selectedPaymentLine.uuid);
        } else {
            this.selectedPaymentLine.set_amount(amount);
        }
    },
    async validateOrder(isForceValidate) {
        this.numberBuffer.capture();
        if (await this._isOrderValid(isForceValidate)) {
            // remove pending payments before finalizing the validation
            for (const line of this.paymentLines) {
                if (!line.is_done()) {
                    this.currentOrder.remove_paymentline(line);
                }
            }
            await this._finalizeValidation();
            this.pos.printReceipt()

        }
    },



});