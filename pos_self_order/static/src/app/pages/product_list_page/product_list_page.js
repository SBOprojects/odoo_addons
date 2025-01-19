import { Component, useEffect, useRef, onWillStart, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { CancelPopup } from "@pos_self_order/app/components/cancel_popup/cancel_popup";
import { useService, useChildRef } from "@web/core/utils/hooks";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { _t } from "@web/core/l10n/translation";

const BATCH_SIZE = 6;

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
        this.observer = null; // Observer for infinite scroll
        this.state = useState({
            loading: false,
            displayedProducts: [], // Products shown to the user
            allProducts: [], // All the products for the category (used for lazy loading)
            loadingMoreProducts: false,
            noMoreProducts: false,
            currentBatchStart: 0, // Track what products to load next,
            initialLoading: true,
            abortController: null, // To abort ongoing fetch requests
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
            return () => {
                if (this.observer) {
                    this.observer.disconnect();
                    this.observer = null;
                }
                //Cancel pending requests
                 if (this.state.abortController){
                     this.state.abortController.abort();
                    this.state.abortController = null;
                  }
            };
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

             // Force a page refresh if navigating to main category
           if (!this.selfOrder.currentCategory) {
              window.location.reload(); // or use a more specific router based refresh
          }
       } else {
              this.selfOrder.currentCategory = null;
        // Force a page refresh if the category stack is empty (we're at the root)
         window.location.reload(); // or use a more specific router based refresh
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
            console.error("error while loading initial data in the product page:", error)
        } finally {
            await this.initializeProductLoading();
        }
    }

    async initializeProductLoading() {
        this.state.loading = true;
        this.state.displayedProducts = []; // Reset when category change
        this.state.currentBatchStart = 0;
        this.state.noMoreProducts = false;
        this.state.allProducts = []; // Initialize the array

       if (this.observer) {
             this.observer.disconnect();
             this.observer = null;
         }
        //Abort any ongoing requests
        if (this.state.abortController){
            this.state.abortController.abort();
             this.state.abortController = null;
         }
        await this.fetchProducts();
        this.observeProducts();
    }

    async fetchProducts() {
        // Abort any ongoing requests before starting a new one
          if (this.state.abortController){
            this.state.abortController.abort();
            this.state.abortController = null;
         }
        this.state.loading = true;
         this.state.abortController = new AbortController(); // Create a new AbortController
        try {

             const category = this.selfOrder.currentCategory;
             let products;
             if (!category) {
               products = await this.getUncategorizedProducts(this.state.abortController.signal); // pass the signal to the fetch methods
            }
            else {
                products = this.getProductsForCategory(category);
            }
            // Here we add the products directly to the state
            this.state.allProducts = products;
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


    async getUncategorizedProducts(signal) { //Pass the abortController signal as a param
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
         ], {signal: signal}); // pass the signal to the orm call to abort

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


    loadMoreProducts = () => {
        if (this.state.loadingMoreProducts || this.state.noMoreProducts || this.state.loading) {
            return;
        }
        if (this.state.allProducts.length <= this.state.currentBatchStart) {
            this.state.noMoreProducts = true;
            return;
        }
        this.state.loadingMoreProducts = true;
        const start = this.state.currentBatchStart;
        const end = start + BATCH_SIZE;
        const nextProducts = this.state.allProducts.slice(start, end);

        if (nextProducts.length === 0) {
            this.state.noMoreProducts = true;
            this.state.loadingMoreProducts = false
            return;
        }
        this.state.displayedProducts = [...this.state.displayedProducts, ...nextProducts];
        this.state.currentBatchStart = end;
        this.state.loadingMoreProducts = false;
    };


    observeProducts() {
        this.observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                this.loadMoreProducts();
            }
        }, { threshold: 0.8 });

        if (this.productsList.el) {
            this.observer.observe(this.productsList.el.lastElementChild);
            //load the first batch of products when the observer is active for the first time.
            this.loadMoreProducts();
        }
    };
}