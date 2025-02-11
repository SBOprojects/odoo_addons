import { ConnectionLostError } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { ClosePosPopup } from '@point_of_sale/app/navbar/closing_popup/closing_popup';
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {

    // all the code under here is done by shahd and rami
    // New Function: downloadReportX
    downloadReportX() {
        const reportContent = this.generateReportXContent();
        this.printReportX(reportContent);
    },

    formatDateAndTime(date) {
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${day}-${month}-${year} ${hours}:${minutes}`;
    },

    generateReportXContent() {
        let content = "";
        // Header with Company Name and VAT ID
        content += `<div style="display: flex; justify-content: flex-start; margin-bottom: 10px; width: 100%;">
        <div style="font-size: 0.9em; line-height: 0.5; width: 100%;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0;">
                <div style="text-align: right;">Company name:</div>
            <div style="text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%;">${this.props.orders_details.company_name}</div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 0;">
                <div style="text-align: right;">Company ID VAT:</div>
                <div style="text-align: left;">${this.props.orders_details.company_vat}</div>
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
        const totalTax = this.props.orders_details.total_cash_payment * (this.props.orders_details.company / 100);

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
                           <td style='padding: 5px; text-align: left; font-weight: bold;'>VAT ${this.props.orders_details.company}%</td>
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
                       </div>\n`;
        }


        return content;
    },
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
    },
    downloadReportZ() {
        const reportContent = this.generateReportZContent();
        this.printReportZ(reportContent);
    },
    totalAmount: 0,

    generateReportZContent() {
        let content = "";
        // Header with Company Name and VAT ID
        content += `<div style="display: flex; justify-content: flex-start; margin-bottom: 10px; width: 100%;">
            <div style="font-size: 0.9em; line-height: 0.5; width: 100%;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0;">
                    <div style="text-align: right;">Company name:</div>
                    <div style="text-align: left;">${this.props.orders_details.company_name}</div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 0;">
                    <div style="text-align: right;">Company ID VAT:</div>
                    <div style="text-align: left;">${this.props.orders_details.company_vat}</div>
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
            const totalSalesTax = totalSalesAmount * (this.props.orders_details.company / 100);
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
            const totalRefundTax = totalRefundAmount * (this.props.orders_details.company / 100);
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
        const totalTax = this.props.orders_details.total_cash_payment * (this.props.orders_details.company / 100);

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
                               <td style='padding: 5px; text-align: left; font-weight: bold;'>VAT ${this.props.orders_details.company}%</td>
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
                                   </div>\n`;
        }
        return content;
    },
    processOrderLines(orders) {
        return orders;
    },
    printReportZ(reportContent) {
        const printWindow = window.open('', '', 'height=600,width=800');
        if (printWindow) {
            printWindow.document.write('<html><head><title>Report Z</title>');
            printWindow.document.write('<style>');
            printWindow.document.write('body { font-family: sans-serif; font-size: 12px; }'); // Added font-size: 10px
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
});