import datetime

from django.utils.dateformat import DateFormat
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from filer.fields.folder import FilerFolderField
from filer.fields.image import FilerImageField
from easy_thumbnails.files import get_thumbnailer

from .utils import format_amount

#! PRODUCT
class Category(models.Model):
    title = models.CharField(max_length=255, verbose_name="Наименование категории", unique=True)
    order = models.PositiveIntegerField(null=True, blank=True, default=0)

    class Meta:
        ordering = ("order",)
        verbose_name = "категория"
        verbose_name_plural = "категории"

    def __str__(self):
        return self.title


class SubCategory(models.Model):
    title = models.CharField(max_length=255, verbose_name="Наименование категории", unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="subcategories",)
    order = models.PositiveIntegerField(null=True, blank=True, default=0)

    class Meta:
        ordering = ("order",)
        verbose_name = "подкатегория"
        verbose_name_plural = "подкатегории"

    def __str__(self):
        return self.title


class ProductUnit(models.Model):
    title = models.CharField(verbose_name="Наименование", help_text="Укажите единицу измерения товара, например: шт., кг., л. и т.д.", max_length=255)

    class Meta:
        verbose_name = "eдиница измерения"
        verbose_name_plural = "eдиницы измерения"

    def __str__(self):
        return self.title
    

class Product(models.Model):
    title = models.CharField(verbose_name="Наименование", max_length=255, unique=True)
    price = models.DecimalField(verbose_name="Цена", decimal_places=2, max_digits=12)
    cover = FilerImageField(verbose_name='Обложка', null=True, blank=True, on_delete=models.SET_NULL)
    slider = FilerFolderField(on_delete=models.SET_NULL, verbose_name='Галерея', null=True, blank=True)
    category = models.ForeignKey(Category, verbose_name="Категория", on_delete=models.SET_NULL, null=True, blank=True, related_name="products",)
    subcategory = models.ForeignKey(SubCategory, verbose_name="Подкатегория", on_delete=models.SET_NULL, null=True, blank=True, related_name="products",)
    unit = models.ForeignKey(ProductUnit, verbose_name="Единица измерения", on_delete=models.SET_NULL, null=True, blank=True, related_name="products",)
    description = models.TextField(verbose_name="Описание", blank=True, null=True)
    in_stoplist = models.BooleanField(verbose_name="В стоп-листе?", default=False)
    is_popular = models.BooleanField(verbose_name="Популярный товар?", default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order",)
        verbose_name = "товар"
        verbose_name_plural = "товары"

    def __str__(self):
        return self.title

    def get_thumbnail(self):
        image = '-'
        if self.cover:
            image = format_html('<img src="{0}"/>', get_thumbnailer(self.cover)['cover_thumbnail'].url)
        return image
    
    get_thumbnail.allow_tags = True
    get_thumbnail.short_description = 'Обложка'

    @property
    def readable_price(self):
        return format_amount(self.price)


class FavoriteProduct(models.Model):
    user = models.ForeignKey(get_user_model(), related_name="favorites", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_user_product")
        ]
        verbose_name = "Избранный товар"
        verbose_name_plural = "Избранные товары"
    
    def __str__(self):
        return f'{self.user.username} - {self.product.title}'


#! CART/ORDER
class Cart(models.Model):
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name="Корзина",
    )

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины пользователей"

    def __str__(self) -> str:
        return str(self.user.username)

    @property
    def cart_total_sum(self):
        return sum([item.total_sum for item in self.items.all()])
    
    @property
    def total_sum(self):
        return format_amount(sum([item.total_sum for item in self.items.all()]))
    

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items",verbose_name="Корзина",)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар",)
    item_count = models.PositiveIntegerField(default=1, verbose_name="Количество",)

    class Meta:
        verbose_name = "Элемент списка корзины"
        verbose_name_plural = "Элементы списка корзины"

    def __str__(self) -> str:
        return f"{self.product.title} x{self.item_count}"
    
    @property
    def total_sum(self):
        return self.item_count * self.product.price

    @property
    def readable_total_sum(self):
        return format_amount(self.total_sum)


class OrderStatus:
    Created = "created"
    AwaitingPayment = "awaiting_payment"
    AwaitingDelivery = "awaiting_delivery"
    Completed = "completed"
    Canceled = "canceled"


class Order(models.Model):
    STATUSES = [
        (OrderStatus.Created, "Создан"),
        (OrderStatus.AwaitingPayment, "Ожидает оплаты"),
        (OrderStatus.AwaitingDelivery, "Ожидает доставки"),
        (OrderStatus.Completed, "Выполнен"),
        (OrderStatus.Canceled, "Отменен"),
    ]
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="Пользователь",
    )
    status = models.CharField(max_length=256, choices=STATUSES, default=OrderStatus.Created, verbose_name="Статус заказа",)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    address = models.CharField(max_length=255, verbose_name="Адрес", null=True, blank=True)
    phone = models.CharField(max_length=255, verbose_name="Телефон", null=True, blank=True)
    time = models.TimeField(verbose_name="Время доставки", null=True, blank=True)
    date = models.DateField(verbose_name="Дата доставки", null=True, blank=True)
    
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self):
        return f"{self.user.username} - {self.status}"

    def save(self, *args, **kwargs):
        if self.id:
            prev_status = Order.objects.get(id=self.id).status
            if self.status == OrderStatus.Completed and self.status != prev_status:
                if buyer := BuyerProfile.objects.filter(user=self.user).first():
                    if referrer := buyer.referrer:
                        referrer.balance += self.total_sum * referrer.referral_percent
                        referrer.save()
        super().save(*args, **kwargs)

    @property
    def total_sum(self):
        return sum([item.total_sum for item in self.items.all()])
    
    @property
    def readable_total_sum(self):
        return format_amount(self.total_sum)

    @property
    def readable_date(self):
        return DateFormat(self.created_at + datetime.timedelta(hours=3)).format('d.m.Y')

    @property
    def readable_time(self):
        return DateFormat(self.created_at + datetime.timedelta(hours=3)).format('H:i')

    @property
    def readable_delivery_date(self):
        if self.date:
            return DateFormat(self.date).format('d.m.Y')
        return '-'

    @property
    def readable_delivery_time(self):
        if self.time:
            return DateFormat(self.time).format('H:i')
        return '-'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ",)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар",)
    item_count = models.PositiveIntegerField(default=1, verbose_name="Количество",)

    class Meta:
        verbose_name = "Элемент заказа"
        verbose_name_plural = "Элементы заказов"

    def __str__(self) -> str:
        return f"{self.product.title} x {self.item_count}"
    
    @property
    def total_sum(self):
        return self.item_count * self.product.price
    
    @property
    def readable_total_sum(self):
        return format_amount(self.total_sum)


#! BOT DATA
class BuyerProfile(models.Model):
    user = models.ForeignKey(get_user_model(), 
                             on_delete=models.CASCADE, 
                             related_name="telegram_user", 
                             verbose_name="Пользователь",
                             )
    tg_id = models.CharField(max_length=255, verbose_name="ID в Telegram", unique=True)
    username = models.CharField(max_length=255, verbose_name="Имя пользователя в Telegram", null=True, blank=True)
    phone = models.CharField(max_length=255, verbose_name="Телефон", null=True, blank=True)
    address = models.CharField(max_length=255, verbose_name="Адрес", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    referrer = models.ForeignKey("self", 
                                 on_delete=models.SET_NULL, 
                                 null=True, blank=True, 
                                 verbose_name="Реферал", 
                                 related_name="referrals",)
    referral_percent = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="Доля реферальных отчислений", default=0, help_text="Укажите долю реферальных отчислений (0.01=1%)")
    referrals_count = models.IntegerField(verbose_name="Количество рефералов", default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Баланс", default=0)
    thread_id = models.CharField(max_length=255, verbose_name="Топик id", null=True, blank=True)

    class Meta:
        verbose_name = "Профиль покупателя"
        verbose_name_plural = "Профили покупателей"

    def __str__(self):
        return self.user.username


class BaseSettings(models.Model):
    bot_token = models.CharField(max_length=255, verbose_name="Токен бота")
    bot_name = models.CharField(max_length=255, verbose_name="Имя бота")
    referral_percent = models.DecimalField(max_digits=5, decimal_places=3, verbose_name="Доля реферальных отчислений", default=0, help_text="Укажите долю реферальных отчислений (0.01=1%)")
    orders_per_page = models.PositiveIntegerField(verbose_name="Количество заказов на странице", default=5)
    help_chat = models.CharField(max_length=255, verbose_name="Чат поддержки")
    web_app_url = models.CharField(max_length=255, verbose_name="URL веб-приложения")

    class Meta:
        verbose_name = "Настройки магазина"
        verbose_name_plural = "Настройки магазина"

    def __str__(self):
        return "Настройки магазина"
    