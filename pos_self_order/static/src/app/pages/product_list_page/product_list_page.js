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
        this.state = useState({ products: [], loading: false });


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
             this.fetchProducts();
        }, () => [this.selfOrder.currentCategory])

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

    async fetchProducts() {
          this.state.loading = true;
        try {
          const category = this.selfOrder.currentCategory;
          let products;
          if (!category) {
               products = await this.getUncategorizedProducts();
          }
          else if (typeof category.parent_id === 'object' && category.parent_id !== null ) {
               products = this.selfOrder.productByCategIds[category.id] || [];
          }
          else {
               products = await this.getProductsForParentCategory(category);
          }
  
           this.state.products = products;
        } finally{
               this.state.loading = false;
        }
      }


    getProductsForCategory() {
         return this.state.products;
    }


    async getUncategorizedProducts() {
        const uncategorized = [];
        if (!this.selfOrder.allProducts) return uncategorized;
        
        const productTemplateIds = [];
        for(const product of this.selfOrder.allProducts) {
            if (!product.categ_id) {
               productTemplateIds.push(product._raw.product_tmpl_id)
            }
        }
        
          if(productTemplateIds.length == 0) return [];

        const productTemplates = await this.orm.searchRead("product.template", [
          ["id", "in", productTemplateIds]
        ]);

          const modifierProductTemplateIds = productTemplates
              .filter((template) => template.is_modifier)
              .map((template) => template.id);

        for (const product of this.selfOrder.allProducts) {
           if(!product.categ_id && !modifierProductTemplateIds.includes(product._raw.product_tmpl_id)){
            uncategorized.push(product);
           }
       }
       return uncategorized;
    }


      async getProductsForParentCategory(parentCategory) {
        let allProducts = [];
    
        if (this.selfOrder.productByCategIds[parentCategory.id]) {
            allProducts.push(...(this.selfOrder.productByCategIds[parentCategory.id] || []));
        }
        if (parentCategory.child_ids && parentCategory.child_ids.length > 0) {
           for (const childCategory of parentCategory.child_ids) {
                if (this.selfOrder.productByCategIds[childCategory.id]) {
                allProducts.push(...(this.selfOrder.productByCategIds[childCategory.id] || []));
              }
            }
         }

        
        if (allProducts.length === 0) return [];

         const productTemplateIds = allProducts.map(product => product._raw.product_tmpl_id);


        const productTemplates = await this.orm.searchRead("product.template", [
           ["id", "in", productTemplateIds]
        ]);

         const modifierProductTemplateIds = productTemplates
           .filter((template) => template.is_modifier)
           .map((template) => template.id);

        const filteredProducts = allProducts.filter(product => !modifierProductTemplateIds.includes(product._raw.product_tmpl_id));

          return filteredProducts;
    }
    hasChildCategories(category) {
        return this.selfOrder.availableCategories.some(c => c.parent_id === category.id);
    }

    getChildCategories(category) {
        return this.selfOrder.availableCategories.filter(c => c.parent_id === category.id);
    }
}