"""Product catalog management page."""

from pydantic import ValidationError
import streamlit as st

from app.components.common import render_header, require_business_context
from app.components.forms import handle_validation_error, parse_comma_separated
from core.models import ProductCreate, ProductUpdate
from services.product_service import product_service


def render_products_page() -> None:
    """Render the product catalog and management interface."""
    render_header(
        "🛍️ Product Catalog Management",
        "Add, view, edit, and organize products for your AI support assistant.",
    )

    biz = require_business_context()
    if not biz:
        return

    products = product_service.get_products_by_business(biz.business_id)

    tabs = st.tabs(["📦 Product Catalog", "➕ Add New Product", "✏️ Edit Product"])

    # 1. PRODUCT CATALOG TAB
    with tabs[0]:
        st.subheader(f"Products for {biz.name} ({len(products)})")

        if not products:
            st.info("No products found for this business. Switch to the **Add New Product** tab to add items.")
        else:
            # Display catalog items in expanders
            for prod in products:
                with st.expander(f"**{prod.name}** — {prod.currency} {prod.price:.2f}" if prod.price is not None else f"**{prod.name}**"):
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.markdown(f"**Category:** {prod.category or 'Uncategorized'}")
                        st.markdown(f"**Availability:** `{prod.availability or 'in_stock'}`")
                        st.markdown(f"**Returnable:** {'✅ Yes' if prod.returnable else '❌ No'}")
                        if prod.description:
                            st.write(f"*{prod.description}*")

                    with col2:
                        st.markdown(f"**Sizes:** {', '.join(prod.sizes) if prod.sizes else 'None'}")
                        st.markdown(f"**Colors:** {', '.join(prod.colors) if prod.colors else 'None'}")
                        if prod.product_url:
                            st.markdown(f"**URL:** [{prod.product_url}]({prod.product_url})")

                    with col3:
                        st.caption(f"ID: `{prod.product_id}`")
                        # Delete with confirmation
                        delete_key = f"del_confirm_{prod.product_id}"
                        if st.checkbox("Confirm Delete", key=delete_key):
                            if st.button("🗑️ Delete Product", key=f"btn_del_{prod.product_id}", type="primary"):
                                if product_service.delete_product(prod.product_id, business_id=biz.business_id):
                                    st.success(f"Product '{prod.name}' deleted.")
                                    st.rerun()

    # 2. ADD NEW PRODUCT TAB
    with tabs[1]:
        st.subheader("Add a Product")
        with st.form("add_product_form", clear_on_submit=True):
            p_name = st.text_input("Product Name *", placeholder="e.g. Classic Denim Jacket")
            p_category = st.text_input("Category", placeholder="e.g. Outerwear / Jackets")
            p_desc = st.text_area("Product Description", placeholder="e.g. 100% cotton premium washed denim jacket.")

            col1, col2 = st.columns(2)
            with col1:
                p_price = st.number_input("Price", min_value=0.0, step=1.0, value=0.0, format="%.2f")
            with col2:
                p_curr = st.text_input("Currency Code", value="USD")

            col3, col4 = st.columns(2)
            with col3:
                p_sizes = st.text_input("Sizes (comma-separated)", placeholder="e.g. S, M, L, XL")
            with col4:
                p_colors = st.text_input("Colors (comma-separated)", placeholder="e.g. Indigo Blue, Washed Black")

            col5, col6 = st.columns(2)
            with col5:
                p_avail = st.selectbox("Availability", ["in_stock", "low_stock", "out_of_stock"], index=0)
            with col6:
                p_returnable = st.checkbox("Return Eligible", value=True)

            p_url = st.text_input("Product URL", placeholder="https://store.example.com/products/denim-jacket")

            submit_add = st.form_submit_button("Save Product", type="primary")

            if submit_add:
                try:
                    create_data = ProductCreate(
                        business_id=biz.business_id,
                        name=p_name,
                        description=p_desc or None,
                        category=p_category or None,
                        price=p_price,
                        currency=p_curr or "USD",
                        sizes=parse_comma_separated(p_sizes),
                        colors=parse_comma_separated(p_colors),
                        availability=p_avail,
                        returnable=p_returnable,
                        product_url=p_url or None,
                    )
                    saved_prod = product_service.create_product(create_data)
                    st.success(f"✅ Product **{saved_prod.name}** added successfully!")
                    st.rerun()
                except ValidationError as e:
                    handle_validation_error(e)
                except Exception as e:
                    st.error(f"Error adding product: {str(e)}")

    # 3. EDIT PRODUCT TAB
    with tabs[2]:
        st.subheader("Edit Existing Product")
        if not products:
            st.info("No products available to edit.")
        else:
            prod_options = {p.product_id: f"{p.name} (${p.price:.2f})" if p.price is not None else p.name for p in products}
            selected_pid = st.selectbox(
                "Select Product to Edit:",
                options=list(prod_options.keys()),
                format_func=lambda pid: prod_options.get(pid, pid),
            )

            selected_prod = product_service.get_product(selected_pid, business_id=biz.business_id)

            if selected_prod:
                with st.form(f"edit_prod_form_{selected_prod.product_id}"):
                    e_name = st.text_input("Product Name *", value=selected_prod.name)
                    e_category = st.text_input("Category", value=selected_prod.category or "")
                    e_desc = st.text_area("Product Description", value=selected_prod.description or "")

                    col1, col2 = st.columns(2)
                    with col1:
                        e_price = st.number_input(
                            "Price",
                            min_value=0.0,
                            step=1.0,
                            value=selected_prod.price if selected_prod.price is not None else 0.0,
                            format="%.2f",
                        )
                    with col2:
                        e_curr = st.text_input("Currency Code", value=selected_prod.currency or "USD")

                    col3, col4 = st.columns(2)
                    with col3:
                        e_sizes = st.text_input("Sizes (comma-separated)", value=", ".join(selected_prod.sizes))
                    with col4:
                        e_colors = st.text_input("Colors (comma-separated)", value=", ".join(selected_prod.colors))

                    col5, col6 = st.columns(2)
                    avail_options = ["in_stock", "low_stock", "out_of_stock"]
                    current_avail_idx = avail_options.index(selected_prod.availability) if selected_prod.availability is not None and selected_prod.availability in avail_options else 0
                    with col5:
                        e_avail = st.selectbox("Availability", avail_options, index=current_avail_idx)
                    with col6:
                        e_returnable = st.checkbox("Return Eligible", value=selected_prod.returnable)

                    e_url = st.text_input("Product URL", value=selected_prod.product_url or "")

                    submit_edit = st.form_submit_button("Update Product", type="primary")

                    if submit_edit:
                        try:
                            update_data = ProductUpdate(
                                name=e_name,
                                description=e_desc or None,
                                category=e_category or None,
                                price=e_price,
                                currency=e_curr or "USD",
                                sizes=parse_comma_separated(e_sizes),
                                colors=parse_comma_separated(e_colors),
                                availability=e_avail,
                                returnable=e_returnable,
                                product_url=e_url or None,
                            )
                            updated_p = product_service.update_product(
                                selected_prod.product_id,
                                update_data,
                                business_id=biz.business_id,
                            )
                            if updated_p:
                                st.success(f"✅ Product **{updated_p.name}** updated successfully!")
                                st.rerun()
                        except ValidationError as e:
                            handle_validation_error(e)
                        except Exception as e:
                            st.error(f"Error updating product: {str(e)}")
