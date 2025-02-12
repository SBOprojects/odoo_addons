/** @odoo-module **/
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

// Define colors in a static object
const pos_colors = {
    background: "rgb(0, 0, 0)",
    product_background: " #f2f2f2",
    text_color: "rgb(0, 0, 0)",
    price_color: " #ffca00",
    selected_orderline: " #777777",
    info_color: " #B3B7BF",
    numpad_button_hover: " #ffca00",
    popup_background: "rgb(255, 255, 255)",
    popup_button: " #ffca00",
    highlight_color: "rgb(163, 163, 163)",
    modal_button: " #ffca00",
    light_gray_background: "rgb(0, 0, 0)",
    light_gray_notes: " #c1c3c6",
    paymentline_selected: " #707375",
    next_button: "rgb(0, 0, 0)",
    payment_button_background: "rgb(255, 255, 255)",
    numpad_text_color: "black"

};

patch(Navbar.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this._OnNightTrue(); // Apply dark mode directly
    },

    //Added a function for click button change the pos color to black
    async _OnNightTrue(){
        var pos_element = document.querySelector('.pos')
        var pos_product_list_modifier = document.createElement('style')
        pos_product_list_modifier.innerHTML = `
            .pos { color: ${pos_colors.text_color}; background-color: ${pos_colors.background}; }
            .pos .product { background-color: ${pos_colors.product_background} !important; border: thin solid ${pos_colors.text_color}; border-radius: 5px; }
            .pos .product-list { background-color: ${pos_colors.product_background} !important; }
            .pos .product .price-tag { color: ${pos_colors.price_color} !important; }
            .pos .product-content .product-name { color: ${pos_colors.text_color}; }
            .pos .order { background-color: ${pos_colors.product_background}; }
            .pos .rightpane { background-color: ${pos_colors.product_background}; }
            .pos .rightpane-header { background-color: ${pos_colors.product_background}; }
            .pos .pos-content .product-screen .leftpane .pads .control-buttons .fw-bolder { color: ${pos_colors.text_color}; }
            .pos .breadcrumb-button { color: ${pos_colors.text_color}; }
             .pos .form-control { color: black }
            .pos .category-simple-button { background-color: ${pos_colors.product_background} !important; }
            .pos .sb-product .pos-search-bar { background-color: ${pos_colors.product_background} !important; }
            .pos .pos-search-bar input, .pos .partner-list .pos-search-bar input { color: ${pos_colors.text_color}; }
            .pos .orderline .selected { background-color: ${pos_colors.selected_orderline} !important; }
            .pos .info-list { color: ${pos_colors.info_color} !important; }
            .pos .info-list em { color: ${pos_colors.info_color} !important; }
            .pos .control-button { background-color: ${pos_colors.product_background} !important; }
            .pos .numpad button { background-color: ${pos_colors.product_background}; color: ${pos_colors.numpad_text_color}; }
            .pos .numpad button:hover { background-color: ${pos_colors.numpad_button_hover} !important; }
            .pos .button.validation:hover { background-color: ${pos_colors.numpad_button_hover} !important; }
            .pos .button.next.validation { background-color: ${pos_colors.product_background}; color: ${pos_colors.text_color}; }
            .pos .o_payment_successful h1 { color: ${pos_colors.text_color}; }
            .pos .top-content-center h1 { color: ${pos_colors.text_color}; }
            .pos .pay-order-button { background-color: ${pos_colors.product_background} !important; }
            .pos .cc .button { background-color: ${pos_colors.product_background}; color: ${pos_colors.text_color}; }
            .pos .actionpad .button:hover { background-color: ${pos_colors.numpad_button_hover} !important; }
             .pos .control-button:hover {background-color: ${pos_colors.numpad_button_hover} !important;}
            .pos .modal-dialog .popup { background-color: ${pos_colors.popup_background} !important; }
            .pos .popup .button { background: ${pos_colors.popup_button}; color: black !important; }
            .ticket-screen .controls button { background-color: ${pos_colors.text_color}; color: black; }
            .ticket-screen .pos-search-bar .filter { color: black; }
            .ticket-screen .pos-search-bar .filter .options { border-radius: 5px; }
             .pos .order-container {background-color: ${pos_colors.product_background} !important}
            .pos .order-summary {background-color: ${pos_colors.product_background} !important}
             .pos .order-summary .subentry { color: ${pos_colors.text_color} !important }
            .pos .pos-content .product-screen .leftpane .pads .control-button .fa-undo { color: ${pos_colors.text_color} !important; }
           .pos .partner-list {color:black;}
            .pos .partner-list .table-hover thead > tr {background-color: ${pos_colors.product_background};color:white}
            .pos .partner-list tr.partner-line:hover {background-color: ${pos_colors.numpad_button_hover}}
           .pos .partner-list tr.partner-line.highlight {background-color: ${pos_colors.highlight_color}}
           .screen .screen-content{background-color: ${pos_colors.light_gray_background}}
           .pos .partner-list .ms-auto i {color:black;}
           .pos .partner-list .ms-auto input {color: #2a2b2d;}
           .screen .top-content .button.highlight {background-color: ${pos_colors.highlight_color} !important;border-color: ${pos_colors.product_background} !important;}
            .screen .top-content {background-color: ${pos_colors.product_background}}
             .pos .close-pos-popup header{background-color:rgb(56, 57, 58)}
             .pos .popup .title{background-color:rgb(56, 57, 58)}
            .pos .close-pos-popup .closing-notes {background-color: ${pos_colors.light_gray_notes}}
            .pos .opening-cash-control .opening-cash-notes {background-color: ${pos_colors.light_gray_notes}}
            .paymentmethods .button{background: ${pos_colors.payment_button_background}}
           .payment-screen .main-content{background: ${pos_colors.product_background}}
           .pos .paymentline {background: ${pos_colors.product_background}}
           .pos .paymentline.selected {background: ${pos_colors.paymentline_selected}}
            .pos .screen .button.next:not(.highlight) {background: ${pos_colors.next_button};color: ${pos_colors.highlight_color};}
           .receipt-screen .default-view {background: ${pos_colors.product_background}}
            .pos .pay-order-button {background-color:rgb(0, 0, 0) !important;}
               .receipt-screen .default-view .actions .send-email input {background: #666668;color: ${pos_colors.text_color};}
            .receipt-screen .default-view .actions .buttons .button{background: #666668}
            .receipt-screen .default-view .actions .send-email button.send {background: ${pos_colors.highlight_color};color:black}
           .pos .pos-receipt-container > div {color:black}
           .pos .popup.popup-error .button{background: ${pos_colors.modal_button}}
            .pos .orders .order-row:nth-child(n) {background: ${pos_colors.product_background}}
             .pos .orders .order-row.highlight{background: ${pos_colors.highlight_color}}
            .pos .orders .order-row:hover {background: ${pos_colors.numpad_button_hover};}
            .pos .pos-content .product-screen .leftpane .bg-100 {background-color: ${pos_colors.light_gray_notes} !important;}
            .payment-screen .payment-buttons .button {background: ${pos_colors.product_background};color: ${pos_colors.text_color};}
           .payment-screen .payment-buttons .button:hover {background: ${pos_colors.numpad_button_hover}}
           .paymentmethod{color:black;}
            .o_notification_body {color:black;}
           .modal-title{color:black;}
           .modal-header{color:black;}
           .modal-content{background: ${pos_colors.product_background}; color:black;}
           .modal-body {color:black;}
          .modal-body .button:hover{background: ${pos_colors.numpad_button_hover};}
          .modal-header .btn{background: ${pos_colors.modal_button}; color:white;}
          .modal-footer .btn{background: ${pos_colors.modal_button}; color:white;}
         .search-more-button .btn{background: ${pos_colors.next_button}; color:black;}
         .pos-receipt .order-container .orderline {background-color:white;}
         .payment-infos{background-color: ${pos_colors.product_background};}
        `;
        pos_element.parentNode.insertBefore(pos_product_list_modifier, pos_element);
    },
});