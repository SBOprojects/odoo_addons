import { _t } from "@web/core/l10n/translation";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { parseFloat } from "@web/views/fields/parsers";
import { enhancedButtons } from "@point_of_sale/app/generic_components/numpad/numpad";
import { PaymentScreenPaymentLines } from '@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines';
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

// kad_shahd
import { sendTransactionRequest } from '@point_of_sale_1/app/screens/payment_screen/payment_functions';
patch(PaymentScreenPaymentLines.prototype, {
    setup() {
        this.pos = usePos();

        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        this.selectedPaymentLines = []; // Initialize the array


    }
    ,

    async selectLine(paymentline) {

        this.props.selectLine(paymentline.uuid);

        if (paymentline.payment_method_id?.type === 'cash') {
            this.selectedPaymentLines.push(paymentline);
            await this.checkPaymentLinesAmountSum(this.selectedPaymentLines);
            this.notification.add(
                _t("cash Payment line selected."),
                { type: "success" }
            );
        }
        

        const tarminal_name = paymentline.payment_method_id?.use_payment_terminal;
        if (tarminal_name === 'nayax') {


            const api_key = paymentline.payment_method_id?.api_key;
            const public_api_key = paymentline.payment_method_id?.public_api_key;
            console.log('****************************')
            const amount = paymentline.get_amount();
            const adjustedAmount = Math.round(amount * 100);
            const absoluteAmount = Math.abs(adjustedAmount);


            const vuid = paymentline.pos_order_id.uuid; // Replace with actual dynamic value if needed
            const tranType = adjustedAmount >= 0 ? 1 : 53;

            let result;
            try {
                result = await sendTransactionRequest(absoluteAmount, vuid, api_key, tranType, public_api_key);
                // Check if the sendTransactionRequest was successful
                if (!result) { // Assume falsy value (null, undefined) indicates failed request
                    this.notification.add(
                        _t("Could not connect to the payment terminal. Please check your network connection or IP configuration."),
                        { type: "danger" }
                    );
                    return; // Stop execution as request failed.
                }
            } catch (error) {
                console.error("Error during transaction request");
                this.notification.add(
                    _t("Could not connect to the payment terminal. Please check your network connection or IP configuration."),
                    { type: "danger" }
                );
                await this.props.deleteLine(paymentline.uuid);
                return; // Stop execution due to error
            }
            console.log(result.result.statusCode);
            if (result.result.statusCode == 0) {
                this.selectedPaymentLines.push(paymentline);
                await this.checkPaymentLinesAmountSum(this.selectedPaymentLines);
                this.notification.add(
                    _t("Payment completed successfully."),
                    {
                        type: "success",
                        sticky: true,
                        timeout: 600000,

                    }
                );
            }
            else {
                if (result.result.statusCode == 998) {
                    console.log('sendPaymentCancel')
                    this.notification.add(
                        _t("The transaction was cancelled by the payment terminal."),
                        {
                            type: "danger",
                            sticky: true,
                            timeout: 600000,
                        }
                    );
                    await this.props.deleteLine(paymentline.uuid);
                }
                else {

                    console.log('sendPaymentCancel')
                    this.notification.add(
                        _t("online Payment failed for this resone: " + result.result.statusMessage),
                        {
                            type: "danger",
                            sticky: true,
                            timeout: 600000,
                        }
                    );
                }
            }
        }



        if (this.ui.isSmall) {
            this.dialog.add(NumberPopup, {
                title: _t("New amount"),
                buttons: enhancedButtons(),
                startingValue: this.env.utils.formatCurrency(paymentline.get_amount(), false),
                getPayload: (num) => {
                    this.props.updateSelectedPaymentline(parseFloat(num));
                },
            });
        }
    },

    async checkPaymentLinesAmountSum(selectedPaymentLines) {
        // Calculate the total amount of selected payment lines
        const totalAmount = selectedPaymentLines.reduce((sum, line) => {
            return sum + line.get_amount();
        }, 0);
        console.log('****************************')
        console.log(selectedPaymentLines)
        const dueAmount = selectedPaymentLines[0].pos_order_id.amount_total;

        const roundedTotalAmount = Math.round(totalAmount * 100) / 100;
        const roundedDueAmount = Math.round(dueAmount * 100) / 100;

        // Log the amounts for debugging purposes
        console.log("Total of selected payment lines:", roundedTotalAmount);
        console.log("Due amount:", roundedDueAmount);

        // Check if the rounded amounts match
        if (roundedTotalAmount >= roundedDueAmount) {
            // If the amounts match, activate the validateOrder method
            console.log("Amount matches, validating order.");
            this.pos.validateOrder()
        
        } else {
            // If the amounts don't match, do nothing
            console.log("Amount does not match due amount.");
        }
    }


}
);
