import streamlit as st
import pandas as pd
from google.cloud import firestore
from google.oauth2 import service_account
import json
key_dict = json.loads(st.secrets["textkey"])
creds = service_account.Credentials.from_service_account_info(key_dict)
db = firestore.Client(credentials=creds, project="products-project1")
dbProducts = db.collection("products")


st.title("Productos Dashboard")

# Cache para optimizar lecturas
@st.cache_data
def get_all_products():
    products_ref = list(dbProducts.stream())
    products_dict = [
        {
            "código": p.id,
            "name": p.to_dict().get("name", ""),
            "price": float(p.to_dict().get("price", 0.0)),
            "stock": int(p.to_dict().get("stock", 0)),
            "stock_min": int(p.to_dict().get("stock_min", 0)),
            "stock_max": int(p.to_dict().get("stock_max", 0)),
        }
        for p in products_ref
    ]
    return pd.DataFrame(products_dict)

def clear_cache():
    st.cache_data.clear()

def update_product_fields(code, updates):
    """Actualiza múltiples campos de un producto."""
    doc_ref = dbProducts.document(code)
    if doc_ref.get().exists:
        # Actualizar solo campos válidos
        for field in updates:
            if field == "price":
                updates[field] = float(updates[field])
            elif field in ["stock", "stock_min", "stock_max"]:
                updates[field] = int(updates[field])
        doc_ref.update(updates)
        st.success(f"Producto con código '{code}' actualizado correctamente.")
        clear_cache()
    else:
        st.error(f"El producto con código '{code}' no existe.")

def add_product(code, name, price, stock, stock_min, stock_max):
    """Agrega un nuevo producto."""
    doc_ref = dbProducts.document(code)
    if not doc_ref.get().exists:
        doc_ref.set({
            "name": name,
            "price": float(price),
            "stock": int(stock),
            "stock_min": int(stock_min),
            "stock_max": int(stock_max)
        })
        st.success(f"Producto '{name}' agregado correctamente.")
        clear_cache()
    else:
        st.error(f"El producto con código '{code}' ya existe.")

def delete_product(code):
    """Elimina un producto de la base de datos."""
    doc_ref = dbProducts.document(code)
    if doc_ref.get().exists:
        doc_ref.delete()
        st.success(f"Producto con código '{code}' eliminado correctamente.")
        clear_cache()
    else:
        st.error(f"El producto con código '{code}' no existe.")

# Sidebar para seleccionar la operación
operation = st.sidebar.selectbox(
    "Selecciona una operación",
    ["Agregar Producto", "Mostrar Todos los Registros", "Actualizar Producto", "Eliminar Producto"]
)

if operation == "Agregar Producto":
    st.sidebar.subheader("Agregar Producto")
    code = st.sidebar.text_input("Código del Producto")
    name = st.sidebar.text_input("Nombre del Producto")
    price = st.sidebar.number_input("Precio", min_value=0.0, step=0.01, format="%.2f")
    stock = st.sidebar.number_input("Existencias", min_value=0, step=1)
    stock_min = st.sidebar.number_input("Stock Mínimo", min_value=0, step=1)
    stock_max = st.sidebar.number_input("Stock Máximo", min_value=0, step=1)

    if st.sidebar.button("Agregar"):
        if code and name:
            add_product(code, name, price, stock, stock_min, stock_max)
        else:
            st.sidebar.error("Todos los campos son obligatorios.")

elif operation == "Mostrar Todos los Registros":
    st.subheader("Todos los Registros")
    products_df = get_all_products()
    if not products_df.empty:
        st.dataframe(products_df)
    else:
        st.info("No hay registros en la base de datos.")

elif operation == "Actualizar Producto":
    st.sidebar.subheader("Actualizar Producto")

    # Cargar todos los productos
    products_df = get_all_products()
    if not products_df.empty:
        # Seleccionar el producto por nombre
        product_name = st.sidebar.selectbox(
            "Selecciona el Producto a Actualizar",
            options=products_df["name"].tolist()
        )

        # Filtrar para obtener el código del producto
        selected_product = products_df[products_df["name"] == product_name].iloc[0]
        code = selected_product["código"]

        # Mostrar información del producto
        st.subheader(f"Información del Producto: {product_name}")
        product_df = pd.DataFrame(selected_product).reset_index()
        product_df.columns = ["Campo", "Valor"]
        st.dataframe(product_df)

        # Seleccionar campos a actualizar
        valid_fields = ["name", "price", "stock", "stock_min", "stock_max"]
        selected_fields = st.sidebar.multiselect(
            "Selecciona los Campos a Actualizar",
            valid_fields
        )

        # Crear espacio para ingresar los nuevos valores
        updates = {}
        for field in selected_fields:
            current_value = selected_product[field]
            if field == "price":
                new_value = st.number_input(
                    f"Nuevo valor para '{field}'",
                    value=float(current_value),
                    min_value=0.0,
                    step=0.01,
                    format="%.2f"
                )
            elif field in ["stock", "stock_min", "stock_max"]:
                new_value = st.number_input(
                    f"Nuevo valor para '{field}'",
                    value=int(current_value),
                    min_value=0,
                    step=1
                )
            else:
                new_value = st.text_input(f"Nuevo valor para '{field}'", value=str(current_value))
            if new_value != "":
                updates[field] = new_value

        # Botón para actualizar
        if st.button("Actualizar"):
            if updates:
                update_product_fields(code, updates)
            else:
                st.warning("No se han ingresado cambios para actualizar.")
    else:
        st.info("No hay productos disponibles para actualizar.")

elif operation == "Eliminar Producto":
    st.sidebar.subheader("Eliminar Producto")
    code = st.sidebar.text_input("Código del Producto a Eliminar")
    if st.sidebar.button("Eliminar"):
        if code:
            delete_product(code)
        else:
            st.sidebar.error("Debes ingresar un código válido.")

