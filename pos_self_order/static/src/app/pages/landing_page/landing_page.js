import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { LanguagePopup } from "@pos_self_order/app/components/language_popup/language_popup";
import { Dialog } from "@web/core/dialog/dialog";

export class LandingPage extends Component {
    static template = "pos_self_order.LandingPage";
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.activeSelected = false;
        this.pollingInterval = null;
        this.orders = [];
        this.state = useState({ paymentParams: null, order: null, loadingOrder: false, loading: false, paymentConfirmation: false }); // Added loading state and paymentConfirmation state

        onWillStart(async () => {
            this.state.loading = true; // Set loading to true
            if (this.selfOrder.config.self_ordering_mode === "kiosk") {
                const orders = this.selfOrder.models["pos.order"].getAll();
                for (const order of orders) {
                    order.delete();
                }
                this.selfOrder.selectedOrderUuid = null;
            }
            try {
                const orderRecords = await this.orm.searchRead("pos.order", []);
                this.orders = orderRecords;
                console.log("Fetched pos.orders:", this.orders);
            } catch (error) {
                console.error("Error fetching pos.orders:", error);
            }
            this.selfOrder.rpcLoading = false;
            this.state.loading = false; // Set loading to false
        });

        onMounted(() => {
            this.startPolling();
        });

        onWillUnmount(() => {
            clearInterval(this.pollingInterval);
        });
    }

    get currentLanguage() {
        return this.selfOrder.currentLanguage;
    }

    get languages() {
        return this.selfOrder.config.self_ordering_available_language_ids;
    }

    get activeImage() {
        if (!this.activeSelected) {
            this.activeSelected = true;
            return "active";
        }
        return "";
    }

    get draftOrder() {
        return this.selfOrder.models["pos.order"].filter(
            (o) => o.access_token && o.state === "draft"
        );
    }

    hideBtn(link) {
        const arrayLink = link.url.split("/");
        const routeName = arrayLink[arrayLink.length - 1];

        if (routeName !== "products") {
            return;
        }

        return (
            this.draftOrder.length > 0 && this.selfOrder.config.self_ordering_pay_after === "each"
        );
    }

    clickMyOrder() {
        this.router.navigate(this.draftOrder.length > 0 ? "cart" : "orderHistory");
    }

    clickCustomLink(link) {
        const arrayLink = link.url.split("/");
        const routeName = arrayLink[arrayLink.length - 1];

        if (routeName !== "products") {
            this.router.customLink(link);
            return;
        }

        this.start();
    }

    start() {
        if (
            this.draftOrder.length > 0 &&
            this.selfOrder.config.self_ordering_pay_after === "each"
        ) {
            return;
        }
        if (
            this.selfOrder.config.self_ordering_takeaway &&
            !this.selfOrder.orderTakeAwayState[this.selfOrder.currentOrder.uuid] &&
            this.selfOrder.ordering
        ) {
            this.router.navigate("location");
        } else {
            this.router.navigate("product_list");
        }
    }

    openLanguages() {
        this.dialog.add(LanguagePopup);
    }

    showMyOrderBtn() {
        const ordersNotDraft = this.selfOrder.models["pos.order"].find((o) => o.access_token);
        return this.selfOrder.ordering && ordersNotDraft;
    }

    startPolling() {
        this.pollingInterval = setInterval(() => {
            this.checkUrlForParameters();
        }, 1000);
    }

    async showPaymentParamsDialog(order) {
        // No dialog, use payment confirmation banner instead.
    }

    clearPaymentConfirmation() {
        this.state.paymentConfirmation = false;
    }

    async checkUrlForParameters() {
        const urlParams = new URLSearchParams(window.location.search);
        const paramsToCheck = [
            'replyCode',
            'replyDesc',
            'trans_id',
            'trans_date',
            'storage_id',
            'ExpMonth',
            'ExpYear',
            'client_Wallet_id',
            'recurringSeries_id',
            'voucher',
            'paymentDisplay',
            'merchantID',
            'trans_amount',
            'trans_installments',
            'trans_currency',
            'client_id',
            'trans_refNum',
            'signature',
            'Brand',
            'amount_options',
            'ui_version',
            'disp_recurring',
            'disp_mobile',
        ];

        const extractedParams = {};
        let hasParams = false;
        paramsToCheck.forEach((param) => {
            if (urlParams.has(param)) {
                extractedParams[param] = urlParams.get(param);
                hasParams = true;
            }
        });

        if (hasParams) {
            console.log("Extracted Payment Parameters:", extractedParams);
            this.state.loadingOrder = true;
            try {
                // Fetch the order with the external ID equal to trans_refNum
                const order = await this.orm.searchRead("pos.order", [
                    ["id", "=", extractedParams.trans_refNum]
                ]);

                console.log("Fetched Order:", order);

                // Make sure order is not empty
                if (order && order.length > 0) {
                    this.state.order = order[0]; // Store the fetched order
                    const orderId = order[0].id;

                    // Update the amount_paid field
                    await this.orm.write("pos.order", [orderId], {
                        amount_paid: parseFloat(extractedParams.trans_amount),
                        state: "paid", // Set the state to "paid"
                    });
                    console.log(`Updated order ${orderId} with amount_paid: ${extractedParams.trans_amount}`);
                    this.state.loadingOrder = false;
                    this.state.paymentConfirmation = true;

                } else {
                    console.error("Order not found.");
                }
            }
            catch (error) {
                console.error("Error fetching or updating order:", error);
            }

            clearInterval(this.pollingInterval);
            const newUrl = window.location.origin + window.location.pathname;
            window.history.replaceState({}, document.title, newUrl);
        }
    }
}