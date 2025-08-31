# backend/schemas/__init__.py

# products
from .products import ProductCreate, ProductUpdate, ProductOut, StockUpdate

# users
from .users import RegisterPayload, RegisterResponse, LoginPayload, LoginResponse

# orders (שימי לב לשמות המדויקים שקיימים אצלך)
from .orders import (
    OrderCreate, OrderUpdate, OrderResponse, OrderStatus,
    OrderItemIn, OrderItemResponse, OrderStatusUpdate,
)

# order items
from .order_items import OrderItemCreate, OrderItemUpdate, OrderItemOut

# geo
from .cities import CityCreate, CityUpdate, CityOut
from .districts import DistrictCreate, DistrictUpdate, DistrictOut

# m2m links
from .supplier_cities import SupplierCityLink, SupplierCityLinkOut
from .supplier_districts import SupplierDistrictLink, SupplierDistrictLinkOut
from .owner_supplier_links import (
    OwnerSupplierLinkCreate, OwnerSupplierLinkUpdate, OwnerSupplierLinkOut, LinkStatus
)

__all__ = [
    # products
    "ProductCreate", "ProductUpdate", "ProductOut", "StockUpdate",
    # users
    "RegisterPayload", "RegisterResponse", "LoginPayload", "LoginResponse",
    # orders
    "OrderCreate", "OrderUpdate", "OrderResponse", "OrderStatus",
    "OrderItemIn", "OrderItemResponse", "OrderStatusUpdate",
    # order items
    "OrderItemCreate", "OrderItemUpdate", "OrderItemOut",
    # geo
    "CityCreate", "CityUpdate", "CityOut",
    "DistrictCreate", "DistrictUpdate", "DistrictOut",
    # m2m links
    "SupplierCityLink", "SupplierCityLinkOut",
    "SupplierDistrictLink", "SupplierDistrictLinkOut",
    # owner-supplier links
    "OwnerSupplierLinkCreate", "OwnerSupplierLinkUpdate", "OwnerSupplierLinkOut", "LinkStatus",
]
