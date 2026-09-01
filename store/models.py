from django.db import models
from django.utils import timezone

# 1. Categories Table
class Category(models.Model):
    class Meta:
        verbose_name_plural = "Categories"
    name = models.CharField(max_length=100)
    image = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

# 2. Products Table
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.IntegerField() # MRP - Original Price
    discount_price = models.IntegerField(null=True, blank=True) # Final price after discount
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    brand = models.CharField(max_length=100, default="VASTRA")
    size = models.CharField(max_length=100, default="S M L XL XXL FreeSize")
    colour = models.CharField(max_length=50, default="Black")
    stock = models.IntegerField(default=100)
    image = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, default='pending')
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def discount_percent(self):
        if self.discount_price and self.price > self.discount_price and self.price > 0:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0

    @property
    def final_price(self):
        return self.discount_price if self.discount_price and self.discount_price < self.price else self.price

    @property
    def original_price(self): # Cart kosam easy ga
        return self.price

    def __str__(self):
        return self.name

# 3. Users Table
class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return self.name

# 4. Orders Table - Checkout Address
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    # product field vaddu Muni - OrderItem lo untundi
    # product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField(default=1) # Total qty for backward compat
    size = models.CharField(max_length=20, default='M')
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    pincode = models.CharField(max_length=10)
    payment_method = models.CharField(max_length=20, default='COD')
    payment_status = models.CharField(max_length=20, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    total_amount = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True) 

    def save(self, *args, **kwargs):
        # FIXED Muni - Delivered/Shipped time overwrite avvakunda
        if self.payment_status == 'Shipped' and self.shipped_at is None:
            self.shipped_at = timezone.now()
        if self.payment_status == 'Delivered' and self.delivered_at is None:
            self.delivered_at = timezone.now()
            if self.shipped_at is None: # Delivered ayithe shipped kuda undali
                self.shipped_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - Rs.{self.total_amount} - {self.transaction_id} - {self.created_at.strftime('%d-%m-%Y %I:%M %p')}"

# 5. ContactMessage
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    mail = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.name} - {self.mail} - {self.created_at.strftime('%d-%m-%Y %H:%M')}"

# 6. OrderItem Table
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    size = models.CharField(max_length=20, default='M')  
    price = models.IntegerField(default=0) # Integer chesa Muni - Decimal kadu

    def __str__(self):
        return f"{self.product.name} - {self.size} x {self.quantity} - Rs.{self.price}"


# 7. REVIEW MODEL
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True)
    rating = models.IntegerField(choices=[(i, i) for i in range(1,6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} - {self.rating}"

# 8. RETURN MODEL
class ReturnRequest(models.Model):
    STATUS_CHOICES = [('Requested','Requested'),
                      ('Approved','Approved'),
                      ('Picked', 'Picked Up - Courier Assigned'),
                      ('Returned', 'Returned to Warehouse'),
                      ('Refunded', 'Refunded'),
                      ('Rejected','Rejected'),
                    ]
    order_group_id = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Requested,choices=STATUS_CHOICES')
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order_group_id} - {self.status}"    

# Wishlist Model

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # Oka product okasare

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"