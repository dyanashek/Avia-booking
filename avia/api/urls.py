from django.urls import include, path

from api import views as api_views

app_name = "api"

urlpatterns = [
    path("products/", api_views.ProductsView.as_view(), name="products"),
    path("cart/", api_views.CartView.as_view(), name="cart"),
    path("cart-quantity/", api_views.CartQuantityView.as_view(), name="cart_quantity"),
    path("change-favorites/", api_views.ChangeFavoritesView.as_view(), name="change_favorites"),
    path("add-to-cart/", api_views.AddToCartView.as_view(), name="add_to_cart"),  
    path("decrease-from-cart/", api_views.DecreaseFromCartView.as_view(), name="decrease_from_cart"),
    path("delete-from-cart/", api_views.DeleteFromCartView.as_view(), name="delete_from_cart"),
    path("order-detail/<int:pk>/", api_views.OrderDetailView.as_view(), name="order_detail"),
    path("favorites/", api_views.FavoritesView.as_view(), name="favorites"),
    path("verify-user/", api_views.verify_user, name="verify_user"),
]