import { PosStore } from '@point_of_sale/app/store/pos_store';
import { patch } from "@web/core/utils/patch";



// customizing the selectOrderLine method to set the numpadMode to "price" when a line is selected 
patch(PosStore.prototype, {

selectOrderLine(order, line) {
    order.select_orderline(line);
    this.numpadMode = "price";
} 
});