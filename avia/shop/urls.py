from django.urls import include, path
from shop import views as shop_views
from django.views.generic import TemplateView


app_name = "shop"


urlpatterns = [
    path("", shop_views.ProductListView.as_view(), name="catalog"),
    path("product/<int:pk>/", shop_views.ProductDetailView.as_view(), name="product_detail"),
    path("cart/", shop_views.CartListView.as_view(), name="cart"),
    path("get-subcategories/", shop_views.get_subcategories, name="get_subcategories"),
    path("favorites/", shop_views.FavoritesListView.as_view(), name="favorites"),
    path("orders/", shop_views.OrderHistoryView.as_view(), name="orders"),
    path("create-order/", shop_views.create_order, name="create_order"),
    path("repeat-order/<int:id>/", shop_views.repeat_order, name="repeat_order"),
    path("error/", TemplateView.as_view(template_name="client/views/profile/error.html"), name="error"),
]