import random
from django.core.management.base import BaseCommand
from shop.models import Category, SubCategory, Product, ProductUnit

class Command(BaseCommand):
    help = 'Generate random products for the database'

    def handle(self, *args, **kwargs):
        # Create some units
        units = ['шт.', 'кг.', 'л.']
        for unit in units:
            ProductUnit.objects.get_or_create(title=unit)

        # Create some categories and subcategories
        categories = ['Электроника', 'Одежда', 'Продукты']
        for category_title in categories:
            category, _ = Category.objects.get_or_create(title=category_title)
            for i in range(3):  # Create 3 subcategories for each category
                subcategory_title = f'{category_title} Подкатегория {i+1}'
                SubCategory.objects.get_or_create(title=subcategory_title, category=category)

        # Create products
        for i in range(50):  # Generate 50 products
            category = random.choice(Category.objects.all())
            subcategories = category.subcategories.all()
            subcategory = random.choice(subcategories) if subcategories else None
            unit = random.choice(ProductUnit.objects.all())
            product_title = f'Товар {i+1} - {random.randint(1000, 9999)}'  # Add random number to make title unique
            price = round(random.uniform(10.0, 1000.0), 2)  # Random price between 10 and 1000

            Product.objects.create(
                title=product_title,
                price=price,
                category=category,
                subcategory=subcategory,
                unit=unit,
                description=f'Описание для {product_title}',
                in_stoplist=random.choice([True, False]),
                is_popular=random.choice([True, False]),
                order=i
            )

        self.stdout.write(self.style.SUCCESS('Successfully generated products')) 