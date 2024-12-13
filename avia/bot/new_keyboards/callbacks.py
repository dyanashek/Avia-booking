from aiogram.filters.callback_data import CallbackData


class DeliveryCallbackFactory(CallbackData, prefix="delivery"):
    action: str
    delivery_id: int


class DeliveriesCallbackFactory(CallbackData, prefix="deliveries"):
    delivery_type: str
    page: int = 1


class BackCallbackFactory(CallbackData, prefix="back"):
    destination: str
