import { Component, useEffect, useRef, onWillStart, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";
import { useService, useChildRef } from "@web/core/utils/hooks";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { _t } from "@web/core/l10n/translation";


export class ProductListPage extends Component {
    static template = "pos_self_order.ProductListPage";
    static components = { ProductCard, OrderWidget };
    static props = {};

    setup() {
        this.selfOrder = useSelfOrder();
        this.dialog = useService("dialog");
        this.router = useService("router");
        this.productsList = useRef("productsList");
        this.categoryList = useRef("categoryList");
        this.currentProductCard = useChildRef();
        this.orm = useService("orm");
        this.state = useState({
            loading: false,
            products: [], // Single array to hold all products
            initialLoading: true,
        });

        useEffect(
            () => {
                if (!this.productsList.el) {
                    return;
                }
                if (this.selfOrder.lastEditedProductId) {
                    this.scrollTo(this.currentProductCard, { behavior: "instant" });
                }
            },
            () => []
        );

        useEffect(
            () => {
                const category = this.selfOrder.currentCategory;
                if (!category) {
                    return;
                }
                const categBtn = document.querySelector(`[href="#scrollspy_${category.id}"]`);

                if (!categBtn) {
                    return;
                }

                this.categoryList.el.scroll({
                    left:
                        categBtn.offsetLeft +
                        categBtn.offsetWidth / 2 -
                        window.innerWidth / 2,
                    behavior: "smooth",
                });
            },
            () => [this.selfOrder.currentCategory, this.selfOrder.availableCategories]
        );

        useEffect(() => {
            if (this.state.initialLoading) {
                this.fetchData();
            }
        }, () => [this.selfOrder.currentCategory]);

        onWillStart(async () => {
            await this.selfOrder.computeAvailableCategories();
            // Fill productByCategIds map during setup
            this.selfOrder.productByCategIds = {};
            for (const category of this.selfOrder.availableCategories) {
                const products = category["<-product.product.pos_categ_ids"] || [];
                this.selfOrder.productByCategIds[category.id] = products;
            }
            this.selfOrder.currentCategoryStack = [null];
            this.selfOrder.currentCategory = null;
        });
    }

    getCategoriesToDisplay() {
        const currentCategory = this.selfOrder.currentCategoryStack[this.selfOrder.currentCategoryStack.length - 1];

        if (!currentCategory) {
            return this.selfOrder.availableCategories.filter(categ => !categ.parent_id);
        } else {
            return currentCategory.child_ids || [];
        }
    }

    onCategoryClick(category) {
        this.selfOrder.currentCategory = category;
        this.selfOrder.currentCategoryStack.push(category)
    }

    navigateBack() {
        if (this.selfOrder.currentCategoryStack.length > 1) {
            this.selfOrder.currentCategoryStack.pop();
            this.selfOrder.currentCategory = this.selfOrder.currentCategoryStack[this.selfOrder.currentCategoryStack.length - 1];

            
           
       } else {
             this.selfOrder.currentCategory = null;
             
         }
    }

    scrollTo(ref = null, { behavior = "smooth" } = {}) {
        this.productsList.el.scroll({
            top: ref?.el ? ref.el.offsetTop - this.productsList.el.offsetTop : 0,
            behavior,
        });
    }

    review() {
        this.router.navigate("cart");
    }

    back() {
        if (this.selfOrder.config.self_ordering_mode !== "kiosk") {
            this.router.navigate("default");
            return;
        }

        this.dialog.add(CancelPopup, {
            title: _t("Cancel order"),
            confirm: () => {
                this.router.navigate("default");
            },
        });
    }

    async fetchData() {
        this.state.initialLoading = false;
        try {
            await this.selfOrder.getOrdersFromServer();
        }
        catch (error) {
            console.error("error while loading initial data in the product page:", error);
        } finally {
            await this.fetchProducts();
        }
    }

    async fetchProducts() {
        this.state.loading = true;
        try {
            const category = this.selfOrder.currentCategory;
            if (!category) {
                this.state.products = await this.getUncategorizedProducts();
            } else {
                this.state.products = this.getProductsForCategory(category);
            }
        } finally {
            this.state.loading = false;
        }
    }

    getProductsForCategory(category) {
        if (!category) {
            return [];
        }

        if (this.selfOrder.productByCategIds[category.id]) {
            return this.selfOrder.productByCategIds[category.id];
        }

        return [];
    }

    async getUncategorizedProducts() {
        const uncategorized = [];
        if (!this.selfOrder.allProducts) return uncategorized;

        const productTemplateIds = [];
        for (const product of this.selfOrder.allProducts) {
            if (!product.categ_id) {
                productTemplateIds.push(product._raw.product_tmpl_id)
            }
        }

         if (productTemplateIds.length === 0) {
            return [];
         }

         const productTemplates = await this.orm.searchRead("product.template", [
           ["id", "in", productTemplateIds]
         ]);

        const modifierProductTemplateIds = productTemplates
            .filter((template) => template.is_modifier)
            .map((template) => template.id);

        for (const product of this.selfOrder.allProducts) {
            if (!product.categ_id && !modifierProductTemplateIds.includes(product._raw.product_tmpl_id)) {
                uncategorized.push(product);
            }
        }

        return uncategorized;
    }
}