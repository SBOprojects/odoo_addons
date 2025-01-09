import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { PopupTable } from "@pos_self_order/app/components/popup_table/popup_table";
import { _t } from "@web/core/l10n/translation";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";

export class CartPage extends Component {
    static template = "pos_self_order.CartPage";
    static components = { PopupTable, OrderWidget };
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.state = useState({
            selectTable: false,
            cancelConfirmation: false,
        });
    }

    get lines() {
        const lines = this.selfOrder.currentOrder.lines;
        return lines ? lines : [];
    }

    get linesToDisplay() {
        const selfOrder = this.selfOrder;
        const order = selfOrder.currentOrder;

        if (
            selfOrder.config.self_ordering_pay_after === "meal" &&
            Object.keys(order.changes).length > 0
        ) {
            return order.unsentLines;
        } else {
            return this.lines;
        }
    }

    getLineChangeQty(line) {
        const currentQty = line.qty;
        const lastChange = this.selfOrder.currentOrder.uiState.lineChanges[line.uuid];
        return !lastChange ? currentQty : currentQty - lastChange.qty;
    }

    async pay() {
        const orderingMode = this.selfOrder.config.self_ordering_service_mode;
        const type = this.selfOrder.config.self_ordering_mode;
        const takeAway = this.selfOrder.currentOrder.takeaway;

        // Basic checks:
        if (this.selfOrder.rpcLoading || !this.selfOrder.verifyCart()) {
            return;
        }

        // Table assignment logic for "table" mode:
        if (
            type === "mobile" &&
            orderingMode === "table" &&
            !takeAway &&
            !this.selfOrder.currentTable
        ) {
            this.state.selectTable = true;
            return;
        } else {
            this.selfOrder.currentOrder.update({
                table_id: this.selfOrder.currentTable,
            });
        }



        // this.selfOrder.rpcLoading = true;
        // await this.selfOrder.confirmOrder();  // <--- ensures `amount_total` is now correct
        // this.selfOrder.rpcLoading = false;

        // 2) Generate your Nayax signature (same as you do in ConfirmationPage)
        const hash = await this.generateHash();

        console.log("Hash value: ", hash);
        console.log("here-------------------");
        // 3) Open Nayax page directly (just like openNayaxPage)
        this.redirectToNayax(hash);

        // DO NOT navigate to the confirmation screen.
    }
    async generateHash() {
        const amount = this.selfOrder.currentOrder.get_total_with_tax() || 0;
        const id = this.selfOrder.currentOrder.id || 0;
        console.log(amount);
        console.log(id);

        // Convert the input string into a Uint8Array
        const encoder = new TextEncoder();
        const data = encoder.encode(`6312841${id}180${amount}ILSPurchase0he-ilauto39YVLZ32VH`);

        // Use the SubtleCrypto API to generate the SHA-256 hash
        const hashBuffer = await window.crypto.subtle.digest('SHA-256', data);

        // Convert the ArrayBuffer to a Base64 string
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashBase64 = btoa(String.fromCharCode(...hashArray));

        // Return the encoded Base64 hash
        return decodeURIComponent(hashBase64);
    }
    redirectToNayax(signature) {
        // If you need the order ID and amount:
        const orderId = this.selfOrder.currentOrder.id || 0;
        const amount = this.selfOrder.currentOrder.get_total_with_tax() || 0;
        console.log("Redirecting to Nayax...");
        console.log(orderId);
        console.log(amount);
        console.log(signature);
        console.log(this.selfOrder.currentOrder);
        // Build your URLSearchParams (same as your <form> hidden fields)
        const params = new URLSearchParams({
            merchantID: "6312841",
            url_redirect: "",
            url_notify: "",
            trans_comment: "",
            trans_refNum: orderId,
            Brand: "",
            trans_installments: "1",
            amount_options: "",
            ui_version: "8",
            trans_type: "0",
            trans_amount: amount,
            trans_currency: "ILS",
            disp_paymentType: "",
            disp_payFor: "Purchase",
            disp_recurring: "0",
            disp_lng: "he-il",
            disp_mobile: "auto",
            signature: signature,
        });

        // Redirect to Nayax
        window.location.href = `https://uiservices.ecom.nayax.com/hosted//?${params.toString()}`;
    }


    selectTable(table) {
        if (table) {
            this.selfOrder.currentOrder.update({
                table_id: table,
            });
            this.selfOrder.currentTable = table;
            this.router.addTableIdentifier(table);
            this.pay();
        }

        this.state.selectTable = false;
    }

    getPrice(line) {
        const childLines = line.combo_line_ids;
        if (childLines.length == 0) {
            return line.get_display_price();
        } else {
            let price = 0;
            for (const child of childLines) {
                price += child.get_display_price();
            }
            return price;
        }
    }

    canChangeQuantity(line) {
        const order = this.selfOrder.currentOrder;
        const lastChange = order.uiState.lineChanges[line.uuid];

        if (!lastChange) {
            return true;
        }

        return lastChange.qty < line.qty;
    }

    canDeleteLine(line) {
        const lastChange = this.selfOrder.currentOrder.uiState.lineChanges[line.uuid];
        return !lastChange ? true : lastChange.qty !== line.qty;
    }

    async removeLine(line) {
        const lastChange = this.selfOrder.currentOrder.uiState.lineChanges[line.uuid];

        if (!this.canDeleteLine(line)) {
            return;
        }

        if (lastChange) {
            line.qty = lastChange.qty;
            line.setDirty();
        } else {
            this.selfOrder.removeLine(line);
        }
    }

    async _changeQuantity(line, increase) {
        if (!increase && !this.canChangeQuantity(line)) {
            return;
        }

        if (!increase && line.qty === 1) {
            this.removeLine(line.uuid);
            return;
        }
        increase ? line.qty++ : line.qty--;
        for (const cline of this.selfOrder.currentOrder.lines) {
            if (cline.combo_parent_uuid === line.uuid) {
                this._changeQuantity(cline, increase);
                cline.setDirty();
            }
        }

        line.setDirty();
    }

    async changeQuantity(line, increase) {
        await this._changeQuantity(line, increase);
    }

    clickOnLine(line) {
        const order = this.selfOrder.currentOrder;
        this.selfOrder.editedLine = line;

        if (order.state === "draft" && !order.lastChangesSent[line.uuid]) {
            this.selfOrder.selectedOrderUuid = order.uuid;

            if (line.combo_line_ids.length > 0) {
                this.router.navigate("combo_selection", { id: line.product_id });
            } else {
                this.router.navigate("product", { id: line.product_id });
            }
        } else {
            this.selfOrder.notification.add(_t("You cannot edit a posted orderline !"), {
                type: "danger",
            });
        }
    }
}
