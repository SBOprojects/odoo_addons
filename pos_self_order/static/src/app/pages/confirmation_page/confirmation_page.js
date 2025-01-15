import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { rpc } from "@web/core/network/rpc";
import { OutOfPaperPopup } from "@pos_self_order/app/components/out_of_paper_popup/out_of_paper_popup";
import { cookie } from "@web/core/browser/cookie";

export class ConfirmationPage extends Component {
    static template = "pos_self_order.ConfirmationPage";
    static props = ["orderAccessToken", "screenMode"];

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.printer = useService("printer");
        this.dialog = useService("dialog");
        this.pollingInterval = null;
        this.previousUrl = null;
        this.confirmedOrder = {};
        this.changeToDisplay = [];

        this.state = useState({
            onReload: true,
            payment: this.props.screenMode === "pay",
            hashValue: '',
            paymentSuccess: false,
            isNayaxPaymentInitiated: false,
            paymentFailed: false,
            paymentError: null,
        });

        onMounted(() => {
            if (this.selfOrder.config.self_ordering_mode === "kiosk") {
                setTimeout(() => {
                    this.setDefautLanguage();
                }, 5000);

                setTimeout(async () => {
                    try {
                        await this.printer.print(OrderReceipt, {
                            data: this.selfOrder.orderExportForPrinting(this.confirmedOrder),
                            formatCurrency: this.selfOrder.formatMonetary,
                        });
                        if (!this.selfOrder.has_paper) {
                            this.updateHasPaper(true);
                        }
                    } catch (e) {
                        if (e.errorCode === "EPTR_REC_EMPTY") {
                            this.dialog.add(OutOfPaperPopup, {
                                title: `No more paper in the printer, please remember your order number: '${this.confirmedOrder.trackingNumber}'.`,
                                close: () => {
                                    this.router.navigate("default");
                                },
                            });
                            this.updateHasPaper(false);
                        } else {
                            console.error(e);
                        }
                    }
                }, 500);
                this.defaultTimeout = setTimeout(() => {
                    this.router.navigate("default");
                }, 30000);
            }
        });

        onWillUnmount(() => {
            clearTimeout(this.defaultTimeout);
            this.stopPolling();
        });

        onWillStart(() => {
            this.initOrder();
            console.log(this.confirmedOrder);
        });
    }

    openNayaxPage(ev) {
        ev.preventDefault();
        const form = ev.target;
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        const url = form.action + "?" + params.toString();
         window.location.href = url;
        this.state.isNayaxPaymentInitiated = true;
       this.startPolling();
    }

    async generateSignature(companyNum, order, merchantHashKey) {
        const data = new TextEncoder().encode(companyNum + order + merchantHashKey);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashBase64 = btoa(String.fromCharCode(...hashArray));
        return hashBase64;
    }

    async checkPaymentStatus(orderId) {
        if (!this.state.isNayaxPaymentInitiated) {
         return;
        }
        try {
            const data = await rpc('/pos-self-order/get_payment_status', {
                order_id: orderId,
            });

          if (data && data.data && data.data.length > 0) {
              const successfulTransactions = data.data.filter(trans => trans.replyCode === "000");
             if(successfulTransactions.length > 0) {
                 this.state.paymentSuccess = true;
                  this.markOrderAsPaidAndCreateNew();
                  this.stopPolling();
              } else {
                    this.state.paymentFailed = true;
                    this.state.paymentError = "Payment was not successful. Please try again.";
                    this.stopPolling();
                    console.log("Payment failed");
                }
            }else {
                this.state.paymentFailed = true;
                this.state.paymentError = "Payment was not successful. Please try again.";
                this.stopPolling();
                console.log("Payment failed");
            }
        } catch (error) {
           console.error('Error fetching payment status:', error);
           this.state.paymentFailed = true;
           this.state.paymentError = "Error checking payment status.";
            this.stopPolling();
        }
    }


    startPolling() {
        this.pollingInterval = setInterval(() => {
            this.checkPaymentStatus(this.confirmedOrder.tracking_number);
        }, 2000);
    }

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    async markOrderAsPaidAndCreateNew() {
       try {
           await this.selfOrder.createNewOrder();
       }
       catch (error) {
           console.error("Error marking the order as paid and creating a new one", error);
        }
    }
    async initOrder() {
        const data = await rpc(`/pos-self-order/get-orders/`, {
            access_token: this.selfOrder.access_token,
            order_access_tokens: [this.props.orderAccessToken],
        });
        this.selfOrder.models.loadData(data);
        const order = this.selfOrder.models["pos.order"].find(
            (o) => o.access_token === this.props.orderAccessToken
        );
        order.tracking_number = "S" + order.tracking_number;
        this.confirmedOrder = order;

        const paymentMethods = this.selfOrder.models["pos.payment.method"].filter(
            (p) => p.is_online_payment
        );

        if (
            !order ||
            (paymentMethods.length > 0 &&
                this.selfOrder.config.self_ordering_mode === "mobile" &&
                this.selfOrder.config.self_ordering_pay_after === "each" &&
                order.state !== "paid")
        ) {
            this.router.navigate("default");
            return;
        }

        this.state.onReload = false;
        const hash = await this.generateHash();
        this.state.hashValue = hash;
        console.log(this.state.hashValue);
    }

    goToPreviousPage() {
        this.router.navigate("cart");
    }

    backToHome() {
        if (window.crypto) {
        } else {
            console.error("Web Crypto API not available");
        }

        this.router.navigate("default");
    }

    async updateHasPaper(state) {
        await rpc("/pos-self-order/change-printer-status", {
            access_token: this.selfOrder.access_token,
            has_paper: state,
        });
        this.selfOrder.has_paper = state;
    }

    setDefautLanguage() {
        const defaultLanguage = this.selfOrder.config.self_ordering_default_language_id;

        if (
            defaultLanguage &&
            this.selfOrder.currentLanguage.code !== defaultLanguage.code &&
            !this.state.onReload &&
            this.selfOrder.config.self_ordering_mode === "kiosk"
        ) {
            cookie.set("frontend_lang", defaultLanguage.code);
            window.location.reload();
            this.state.onReload = true;
            return true;
        }
        return this.state.onReload;
    }

   async generateHash() {
        const amount = this.selfOrder.currentOrder.amount_total || 0;
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
}