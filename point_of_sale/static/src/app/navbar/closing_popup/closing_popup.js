import { Dialog } from "@web/core/dialog/dialog";
import { SaleDetailsButton } from "@point_of_sale/app/navbar/sale_details_button/sale_details_button";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { MoneyDetailsPopup } from "@point_of_sale/app/utils/money_details_popup/money_details_popup";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { parseFloat } from "@web/views/fields/parsers";
import { Input } from "@point_of_sale/app/generic_components/inputs/input/input";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { deduceUrl } from "@point_of_sale/utils";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { PaymentMethodBreakdown } from "@point_of_sale/app/components/payment_method_breakdown/payment_method_breakdown";
 
export class ClosePosPopup extends Component {
    static components = { SaleDetailsButton, Input, Dialog, PaymentMethodBreakdown };
    static template = "point_of_sale.ClosePosPopup";
    static props = [
        "orders_details",
        "opening_notes",
        "default_cash_details",
        "non_cash_payment_methods",
        "is_manager",
        "amount_authorized_diff",
        "close",
        "company",
        "total_cash_payment"
    ];
 
    setup() {
        this.pos = usePos();
        this.report = useService("report");
        this.hardwareProxy = useService("hardware_proxy");
        this.dialog = useService("dialog");
        this.ui = useState(useService("ui"));
        this.state = useState(this.getInitialState());
        this.confirm = useAsyncLockedMethod(this.confirm);
    }
    autoFillCashCount() {
        const count = this.props.default_cash_details.amount;
        this.state.payments[this.props.default_cash_details.id].counted =
            this.env.utils.formatCurrency(count, false);
        this.setManualCashInput(count);
    }
    get cashMoveData() {
        const { total, moves } = this.props.default_cash_details.moves.reduce(
            (acc, move, i) => {
                acc.total += move.amount;
                acc.moves.push({
                    id: i,
                    name: move.name,
                    amount: move.amount,
                });
                return acc;
            },
            { total: 0, moves: [] }
        );
        return { total, moves };
    }
    async cashMove() {
        await this.pos.cashMove();
        this.dialog.closeAll();
        this.pos.closeSession();
    }
    getInitialState() {
        const initialState = { notes: "", payments: {} };
        if (this.pos.config.cash_control) {
            initialState.payments[this.props.default_cash_details.id] = {
                counted: "0",
            };
        }
        this.props.non_cash_payment_methods.forEach((pm) => {
            if (pm.type === "bank") {
                initialState.payments[pm.id] = {
                    counted: this.env.utils.formatCurrency(pm.amount, false),
                };
            }
        });
        return initialState;
    }
    async confirm() {
        console.log("confirm")
        if (!this.pos.config.cash_control || this.env.utils.floatIsZero(this.getMaxDifference())) {
            await this.closeSession();
            this.downloadReportZ();
            return;
        }
        if (this.hasUserAuthority()) {
            const response = await ask(this.dialog, {
                title: _t("Payments Difference"),
                body: _t(
                    "The money counted doesn't match what we expected. Want to log the difference for the books?"
                ),
                confirmLabel: _t("Proceed Anyway"),
                cancelLabel: _t("Discard"),
            });
            if (response) {
                this.downloadReportZ();
                await  this.closeSession();
                return;

            }
            return ;
        }
        this.dialog.add(ConfirmationDialog, {
            title: _t("Payments Difference"),
            body: _t(
                "The maximum difference allowed is %s.\nPlease contact your manager to accept the closing difference.",
                this.env.utils.formatCurrency(this.props.amount_authorized_diff)
            ),
        });
        

    }

    async cancel() {
        if (this.canCancel()) {
            this.props.close();
        }
    }
    canConfirm() {
        return Object.values(this.state.payments)
            .map((v) => v.counted)
            .every(this.env.utils.isValidFloat);
    }
    async openDetailsPopup() {
        const action = _t("Cash control - closing");
        this.hardwareProxy.openCashbox(action);
        this.dialog.add(MoneyDetailsPopup, {
            moneyDetails: this.moneyDetails,
            action: action,
            getPayload: (payload) => {
                const { total, moneyDetailsNotes, moneyDetails } = payload;
                this.state.payments[this.props.default_cash_details.id].counted =
                    this.env.utils.formatCurrency(total, false);
                if (moneyDetailsNotes) {
                    this.state.notes = moneyDetailsNotes;
                }
                this.moneyDetails = moneyDetails;
            },
            context: "Closing",
        });
    }
    async downloadSalesReport() {
        return this.report.doAction("point_of_sale.sale_details_report", [this.pos.session.id]);
    }
    setManualCashInput(amount) {
        if (this.env.utils.isValidFloat(amount) && this.moneyDetails) {
            this.state.notes = "";
            this.moneyDetails = null;
        }
    }
    getDifference(paymentId) {
        const counted = this.state.payments[paymentId]?.counted;
        if (!this.env.utils.isValidFloat(counted)) {
            return NaN;
        }
        const expectedAmount =
            paymentId === this.props.default_cash_details?.id
                ? this.props.default_cash_details.amount
                : this.props.non_cash_payment_methods.find((pm) => pm.id === paymentId).amount;
 
        return parseFloat(counted) - expectedAmount;
    }
 
    getMaxDifference() {
        return Math.max(
            ...Object.keys(this.state.payments).map((id) =>
                Math.abs(this.getDifference(parseInt(id)))
            )
        );
    }
    hasUserAuthority() {
        return (
            this.props.is_manager ||
            this.props.amount_authorized_diff == null ||
            this.getMaxDifference() <= this.props.amount_authorized_diff
        );
    }
    canCancel() {
        return true;
    }
    async closeSession() {
        this.pos._resetConnectedCashier();
        if (this.pos.config.customer_display_type === "proxy") {
            const proxyIP = this.pos.getDisplayDeviceIP();
            fetch(`${deduceUrl(proxyIP)}/hw_proxy/customer_facing_display`, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ params: { action: "close" } }),
            }).catch(() => {
                console.log("Failed to send data to customer display");
            });
        }
        // If there are orders in the db left unsynced, we try to sync.
        const syncSuccess = await this.pos.push_orders_with_closing_popup();
        if (!syncSuccess) {
            return;
        }
        if (this.pos.config.cash_control) {
            const response = await this.pos.data.call(
                "pos.session",
                "post_closing_cash_details",
                [this.pos.session.id],
                {
                    counted_cash: parseFloat(
                        this.state.payments[this.props.default_cash_details.id].counted
                    ),
                }
            );
 
            if (!response.successful) {
                return this.handleClosingError(response);
            }
        }
 
        try {
            await this.pos.data.call("pos.session", "update_closing_control_state_session", [
                this.pos.session.id,
                this.state.notes,
            ]);
        } catch (error) {
            // We have to handle the error manually otherwise the validation check stops the script.
            // In case of "rescue session", we want to display the next popup with "handleClosingError".
            // FIXME
            if (!error.data && error.data.message !== "This session is already closed.") {
                throw error;
            }
        }
 
        try {
            const bankPaymentMethodDiffPairs = this.props.non_cash_payment_methods
                .filter((pm) => pm.type == "bank")
                .map((pm) => [pm.id, this.getDifference(pm.id)]);
            const response = await this.pos.data.call("pos.session", "close_session_from_ui", [
                this.pos.session.id,
                bankPaymentMethodDiffPairs,
            ]);
            if (!response.successful) {
                return this.handleClosingError(response);
            }
            location.reload();
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                throw error;
            } else {
                await this.handleClosingControlError();
            }
        }
    }
    async handleClosingControlError() {
        this.dialog.add(
            AlertDialog,
            {
                title: _t("Closing session error"),
                body: _t(
                    "An error has occurred when trying to close the session.\n" +
                        "You will be redirected to the back-end to manually close the session."
                ),
            },
            {
                onClose: () => {
                    this.dialog.add(
                        FormViewDialog,
                        {
                            resModel: "pos.session",
                            resId: this.pos.session.id,
                        },
                        {
                            onClose: async () => {
                                const session = await this.pos.data.read("pos.session", [
                                    this.pos.session.id,
                                ]);
                                if (session[0] && session[0].state === "closed") {
                                    location.reload();
                                } else {
                                    this.pos.redirectToBackend();
                                }
                            },
                        }
                    );
                },
            }
        );
    }
    async handleClosingError(response) {
        this.dialog.add(ConfirmationDialog, {
            title: response.title || "Error",
            body: response.message,
            confirmLabel: _t("Review Orders"),
            cancelLabel: _t("Cancel Orders"),
            confirm: () => {
                if (!response.redirect) {
                    this.props.close();
                    this.pos.onTicketButtonClick();
                }
            },
            cancel: async () => {
                if (!response.redirect) {
                    const ordersDraft = this.pos.models["pos.order"].filter((o) => !o.finalized);
                    await this.pos.deleteOrders(ordersDraft, response.open_order_ids);
                    this.closeSession();
                }
            },
            dismiss: async () => {},
        });
 
        if (response.redirect) {
            window.location.reload();
        }
    }
    getMovesTotalAmount() {
        const amounts = this.props.default_cash_details.moves.map((move) => move.amount);
        return amounts.reduce((acc, x) => acc + x, 0);
    }
    // all the code under here is done by shahd and rami
    // New Function: downloadReportX
     downloadReportX() {
         const reportContent = this.generateReportXContent();
         this.printReportX(reportContent)
     }

     formatDateAndTime(date) {
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${day}-${month}-${year} ${hours}:${minutes}`;
    }
 
    generateReportXContent() {
        let content = "";
        // Header with Company Name and VAT ID
        content += `<div style="display: flex; justify-content: flex-start; margin-bottom: 10px; width: 100%;">
        <div style="font-size: 0.9em; line-height: 0.5; width: 100%;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0;">
                <div style="text-align: right;">Company name:</div>
            <div style="text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%;">${this.pos.company.name}</div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 0;">
                <div style="text-align: right;">Company ID VAT:</div>
                <div style="text-align: left;">${this.pos.company.vat}</div>
            </div>
             <div style="display: flex; justify-content: space-between; margin-top: 0;">
                <div style="text-align: right;">Pos Name:</div>
                <div style="text-align: left;">${this.pos.session.config_id.display_name}</div>
            </div>
        </div>
    </div>\n`;
        
    content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 5px 0; font-size:1px;'></div>\n";
    
    // Format and display Opening Date
    const openingDate = new Date(this.pos.session.start_at);
    const formattedOpeningDate = this.formatDateAndTime(openingDate);
    content += `<div style="display: flex; align-items: flex-start; margin-bottom: 0;">
                <div style="text-align: left; flex: 1;">Opening Date:</div>
                <div style="text-align: right; flex: 1; word-wrap: break-word;">${formattedOpeningDate}</div>
            </div>\n`;
    
    // Format and display Report Date
    const reportDate = new Date();
    const formattedReportDate = this.formatDateAndTime(reportDate);
    content += `<div style="display: flex; align-items: flex-start; margin-bottom: 0;">
                <div style="text-align: left; flex: 1;">Report Date:</div>
                <div style="text-align: right; flex: 1; word-wrap: break-word;">${formattedReportDate}</div>
            </div>\n`;
    
    content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n";
        
       
        
        // Add Payment Method and Tax Information Summary (Combined)
        content += "Payment and Tax Summary:\n";
        content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n";
        content += `<table style='width:100%; border-collapse: collapse; border: 1px solid #000;'>
                <thead style='border-bottom: 1px solid #000;'>
                    <tr>
                        <th style='padding: 5px; text-align: left;'>Payment Method</th>
                        <th style='padding: 5px; text-align: left;'>Amount</th>
                    </tr>
                </thead>
                <tbody>`;
    
        // Cash Payment
        const expectedCash = this.props.default_cash_details.amount || 0.00;
        content += `
                <tr style='border-bottom: 1px solid #eee;'>
                    <td style='padding: 5px; text-align: left;'>Cash</td>
                    <td style='padding: 5px; text-align: left;'>${this.env.utils.formatCurrency(expectedCash)}</td>
                </tr>
            `;
    
        //Online Payment Methods
        let totalPayments = expectedCash;
        this.props.non_cash_payment_methods.forEach(pm => {
            content += `
                    <tr style='border-bottom: 1px solid #eee;'>
                        <td style='padding: 5px; text-align: left;'>${pm.name}</td>
                        <td style='padding: 5px; text-align: left;'>${this.env.utils.formatCurrency(pm.amount)}</td>
                    </tr>
                `;
            totalPayments += pm.amount;
        });
    
        // Calculate total tax
         const totalTax = this.props.total_cash_payment * (this.props.company / 100);
        
        // Calculate total payments without tax
         const totalPaymentsWithoutTax = totalPayments - totalTax;
         
        // Add Total Payments and Total Tax to the table footer
        content += `
                </tbody>
                <tfoot style='border-top: 1px solid #000;'>
                            <tr>
                               <td style='padding: 5px; text-align: left; font-weight: bold;'>Total</td>
                               <td style='padding: 5px; text-align: left;'>${this.env.utils.formatCurrency(totalPayments)}</td>
                            </tr>
                                                 <tr>
                           <td style='padding: 5px; text-align: left; font-weight: bold;'>VAT ${this.props.company}%</td>
                           <td style='padding: 5px; text-align: left;'>${this.env.utils.formatCurrency(totalTax)}</td>
                    </tr>    
                       <tr>
                           <td style='padding: 5px; text-align: left; font-weight: bold;'>Untaxed Amount</td>
                           <td style='padding: 5px; text-align: left;'>${this.env.utils.formatCurrency(totalPaymentsWithoutTax)}</td>
                        </tr>

                 </tfoot>
                </table>
                `;
    
    
        content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n"; // Added extra spacing
    
        // Add notes
        if (this.state.notes) {
            content += "Notes:\n";
            content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n";
            content += `${this.state.notes}\n`;
             content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n"; // Added extra spacing
        }
    
        //Cashier Information in Footer
        if (this.pos.cashier) {
            content += `<div style="display: flex; align-items: flex-start; margin-top: 10px; font-size: 0.9em;">
                           <div style="text-align: left; flex: 1; ">Cashier Name:</div>
                           <div style="text-align: right; flex: 1; word-wrap: break-word;">${this.pos.cashier.name}</div>
                       </div>\n`
        }
    
    
        return content;
    }
    printReportX(reportContent) {
         const printWindow = window.open('', '', 'height=600,width=800');
        if (printWindow) {
            printWindow.document.write('<html><head><title>Report X</title>');
            printWindow.document.write('<style>');
            printWindow.document.write('body { font-family: sans-serif; font-size: 12px; }');
            printWindow.document.write('pre { white-space: pre-wrap; word-wrap: break-word; }'); // Ensure line wrapping
            printWindow.document.write('</style>');
            printWindow.document.write('</head><body>');
            printWindow.document.write(`<pre>${reportContent}</pre>`);
            printWindow.document.write('</body></html>');
            printWindow.document.close();
            printWindow.focus(); // for IE browser
            printWindow.print();
            printWindow.close();
        } else {
            console.error('Failed to open print window. Please allow pop-ups.');
        }
 
   
    }
    downloadReportZ() {
        const reportContent = this.generateReportZContent();
        this.printReportZ(reportContent)
    }        
    totalAmount = 0;

    generateReportZContent() {
        let content = "";
        // Header with Company Name and VAT ID
        content += `<div style="display: flex; justify-content: flex-start; margin-bottom: 10px; width: 100%;">
            <div style="font-size: 0.9em; line-height: 0.5; width: 100%;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0;">
                    <div style="text-align: right;">Company name:</div>
                    <div style="text-align: left;">${this.pos.company.name}</div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 0;">
                    <div style="text-align: right;">Company ID VAT:</div>
                    <div style="text-align: left;">${this.pos.company.vat}</div>
                </div>
                 <div style="display: flex; justify-content: space-between; margin-top: 0;">
                    <div style="text-align: right;">Pos Name:</div>
                    <div style="text-align: left;">${this.pos.session.config_id.display_name}</div>
                </div>
            </div>
        </div>\n`;
    
        content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 5px 0; font-size:1px;'></div>\n";
    
        // Format and display Opening Date
        const openingDate = new Date(this.pos.session.start_at);
        const formattedOpeningDate = this.formatDateAndTime(openingDate);
        content += `<div style="display: flex; align-items: flex-start; margin-bottom: 0;">
                    <div style="text-align: left; flex: 1;">Opening Date:</div>
                    <div style="text-align: right; flex: 1; word-wrap: break-word;">${formattedOpeningDate}</div>
                </div>\n`;
    
        // Format and display Report Date
        const reportDate = new Date();
        const formattedReportDate = this.formatDateAndTime(reportDate);
        content += `<div style="display: flex; align-items: flex-start; margin-bottom: 0;">
                    <div style="text-align: left; flex: 1;">Report Date:</div>
                    <div style="text-align: right; flex: 1; word-wrap: break-word;">${formattedReportDate}</div>
                </div>\n`;
    
        content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n";
    
        // === Orders Details Section ===
        content += "Orders Categories:\n";
        if (this.props.orders_details && Array.isArray(this.props.orders_details.orders) && this.props.orders_details.orders.length > 0) {
            const orders = this.props.orders_details.orders;
    
            // --- Sales Section ---
            content += "<div style='font-weight: bold; margin-top: 10px;'>Sales</div>\n";
            content += `<table style='width:100%; border-collapse: collapse; border: 1px solid #000;'>
                            <thead style='border-bottom: 1px solid #000;'>
                                <tr>
                                    <th style='padding: 5px; text-align: left;'>Category</th>
                                    <th style='padding: 5px; text-align: right;'>Qty</th>
                                    <th style='padding: 5px; text-align: right;'>Amount</th>
                                </tr>
                            </thead>
                            <tbody>`;
            let totalSalesQuantity = 0;
            let totalSalesAmount = 0;
    
            orders.forEach(category => {
                const hasSalesProducts = category.products && category.products.some(line => line.qty > 0);
                if (hasSalesProducts) {
                    let categoryTotalQty = 0;
                    let categoryTotalAmount = 0;
    
                    if (category.products && category.products.length > 0) {
                        const salesProducts = category.products.filter(line => line.qty > 0);
                        salesProducts.forEach(line => {
                            categoryTotalQty += line.qty;
                            categoryTotalAmount += line.price_subtotal_incl;
                        });
                        totalSalesQuantity += categoryTotalQty;
                        totalSalesAmount += categoryTotalAmount;
                    }
                    content += `
                                <tr style='border-bottom: 1px solid #eee;'>
                                    <td style='padding: 5px; text-align: left;'>${category.name}</td>
                                    <td style='padding: 5px; text-align: right;'>${categoryTotalQty}</td>
                                    <td style='padding: 5px; text-align: right;'>${this.env.utils.formatCurrency(categoryTotalAmount)}</td>
                                </tr>
                            `;
                }
            });
            const totalSalesTax = totalSalesAmount * (this.props.company / 100);
            content += `
                                </tbody>
                              <tfoot style='border-top: 1px solid #000;'>
                            <tr>
                                <td style='padding: 5px; text-align: left; font-weight: bold;'>Total</td>
                                <td style='padding: 5px; text-align: right;'>${totalSalesQuantity}</td>
                                <td style='padding: 5px; text-align: right;'>${this.env.utils.formatCurrency(totalSalesAmount)}</td>
                                </tr>
                                <tr>
                                    <td style='padding: 5px; text-align: left; font-weight: bold;'>Tax Amount</td>
                                    <td style='padding: 5px; text-align: right;' colspan='2'>${this.env.utils.formatCurrency(totalSalesTax)}</td>
                                </tr>
                            </tfoot>
                            </table>\n`;
    
    
            content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n";
    
            // --- Refunds Section ---
            content += "<div style='font-weight: bold; margin-top: 10px;'>Refunds</div>\n";
            content += `<table style='width:100%; border-collapse: collapse; border: 1px solid #000;'>
                    <thead style='border-bottom: 1px solid #000;'>
                        <tr>
                            <th style='padding: 5px; text-align: left;'>Category</th>
                            <th style='padding: 5px; text-align: right;'>Qty</th>
                            <th style='padding: 5px; text-align: right;'>Amount</th>
                        </tr>
                    </thead>
                    <tbody>`;
            let totalRefundQuantity = 0;
            let totalRefundAmount = 0;
            orders.forEach(category => {
                const hasRefundProducts = category.products && category.products.some(line => line.qty < 0);
                if (hasRefundProducts) {
                    let categoryTotalQty = 0;
                    let categoryTotalAmount = 0;
                    if (category.products && category.products.length > 0) {
                        const refundProducts = category.products.filter(line => line.qty < 0);
                        refundProducts.forEach(line => {
                            categoryTotalQty += Math.abs(line.qty); // Use Math.abs() here
                            categoryTotalAmount += line.price_subtotal_incl;
                        });
                        totalRefundQuantity += categoryTotalQty;
                        totalRefundAmount += categoryTotalAmount;
                    }
                    content += `
                            <tr style='border-bottom: 1px solid #eee;'>
                                <td style='padding: 5px; text-align: left;'>${category.name}</td>
                                <td style='padding: 5px; text-align: right;'>${categoryTotalQty}</td>
                                <td style='padding: 5px; text-align: right;'>${this.env.utils.formatCurrency(categoryTotalAmount)}</td>
                            </tr>
                        `;
                }
            });
            const totalRefundTax = totalRefundAmount * (this.props.company / 100)
            content += `
                </tbody>
                <tfoot style='border-top: 1px solid #000;'>
                    <tr>
                        <td style='padding: 5px; text-align: left; font-weight: bold;'>Total</td>
                        <td style='padding: 5px; text-align: right;'>${totalRefundQuantity}</td>
                        <td style='padding: 5px; text-align: right;'>${this.env.utils.formatCurrency(totalRefundAmount)}</td>
                    </tr>
                     <tr>
                        <td style='padding: 5px; text-align: left; font-weight: bold;'>Tax Amount</td>
                        <td style='padding: 5px; text-align: right;' colspan='2'>${this.env.utils.formatCurrency(totalRefundTax)}</td>
                    </tr>
                </tfoot>
                </table>\n`;
    
            content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n";
        } else {
            content += "  No orders found.\n";
        }
    
    
        // === Cash Control Summary Section ===
        // Add Payment Method and Tax Information Summary (Combined)
        content += "Payment and Tax Summary:\n";
        content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n";
        content += `<table style='width:100%; border-collapse: collapse; border: 1px solid #000;'>
                    <thead style='border-bottom: 1px solid #000;'>
                        <tr>
                            <th style='padding: 5px; text-align: left;'>Payment Method</th>
                            <th style='padding: 5px; text-align: left;'>Amount</th>
                        </tr>
                    </thead>
                    <tbody>`;
    
        // Cash Payment
        const expectedCash = this.props.default_cash_details.amount || 0.00;
        content += `
                    <tr style='border-bottom: 1px solid #eee;'>
                        <td style='padding: 5px; text-align: left;'>Cash</td>
                        <td style='padding: 5px; text-align: left;'>${this.env.utils.formatCurrency(expectedCash)}</td>
                    </tr>
                `;
    
        //Online Payment Methods
        let totalPayments = expectedCash;
        this.props.non_cash_payment_methods.forEach(pm => {
            content += `
                        <tr style='border-bottom: 1px solid #eee;'>
                            <td style='padding: 5px; text-align: left;'>${pm.name}</td>
                            <td style='padding: 5px; text-align: left;'>${this.env.utils.formatCurrency(pm.amount)}</td>
                        </tr>
                    `;
            totalPayments += pm.amount;
        });
    
        // Calculate total tax
        const totalTax = this.props.total_cash_payment * (this.props.company / 100);
    
        // Calculate total payments without tax
        const totalPaymentsWithoutTax = totalPayments - totalTax;
    
        // Add Total Payments and Total Tax to the table footer
        content += `
                    </tbody>
                    <tfoot style='border-top: 1px solid #000;'>
                                <tr>
                                   <td style='padding: 5px; text-align: left; font-weight: bold;'>Total</td>
                                   <td style='padding: 5px; text-align: left;'>${this.env.utils.formatCurrency(totalPayments)}</td>
                                </tr>
                                                     <tr>
                               <td style='padding: 5px; text-align: left; font-weight: bold;'>VAT ${this.props.company}%</td>
                               <td style='padding: 5px; text-align: left;'>${this.env.utils.formatCurrency(totalTax)}</td>
                        </tr>    
                           <tr>
                               <td style='padding: 5px; text-align: left; font-weight: bold;'>Untaxed Amount</td>
                               <td style='padding: 5px; text-align: left;'>${this.env.utils.formatCurrency(totalPaymentsWithoutTax)}</td>
                            </tr>
    
                     </tfoot>
                    </table>
                    `;
    
        // === Notes Section ===
        if (this.state.notes) {
            content += `\nNotes:\n`;
            content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n";
            content += `  ${this.state.notes}\n`;
            content += "<div style='border-bottom: 1px dashed #000; display: block; margin: 10px 0; font-size:1px;'></div>\n";
        }
    
        //Cashier Information in Footer
        if (this.pos.cashier) {
            content += `<div style="display: flex; align-items: flex-start; margin-top: 10px; font-size: 0.9em;">
                                       <div style="text-align: left; flex: 1; ">Cashier Name:</div>
                                       <div style="text-align: right; flex: 1; word-wrap: break-word;">${this.pos.cashier.name}</div>
                                   </div>\n`
        }
        return content;
    }
    processOrderLines(orders) {
     return orders;
    }
    printReportZ(reportContent) {
        const printWindow = window.open('', '', 'height=600,width=800');
        if (printWindow) {
            printWindow.document.write('<html><head><title>Report Z</title>');
            printWindow.document.write('<style>');
            printWindow.document.write('body { font-family: sans-serif; font-size; }'); // Added font-size: 10px
            printWindow.document.write('pre { white-space: pre-wrap; word-wrap: break-word; }'); // Ensure line wrapping
            printWindow.document.write('</style>');
            printWindow.document.write('</head><body>');
            printWindow.document.write(`<pre>${reportContent}</pre>`);
            printWindow.document.write('</body></html>');
            printWindow.document.close();
            printWindow.focus(); // for IE browser
            printWindow.print();
            printWindow.close();
        } else {
            console.error('Failed to open print window. Please allow pop-ups.');
        }
 
    }
}