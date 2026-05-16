from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    is_subadmin = models.BooleanField(default=False)
    rental_strikes = models.PositiveIntegerField(default=0)
    is_suspended = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    # Bank Details
    card_number = models.CharField(max_length=16, blank=True, null=True)
    card_expiry = models.CharField(max_length=5, blank=True, null=True) # MM/YY
    card_cvv = models.CharField(max_length=3, blank=True, null=True)
    
    # Password Reset Code
    reset_code = models.CharField(max_length=6, blank=True, null=True)
    reset_code_expires = models.DateTimeField(blank=True, null=True)
    
    def has_bank_details(self):
        return all([self.card_number, self.card_expiry, self.card_cvv])
    
    def can_rent(self):
        return self.rental_strikes < 3 and not self.is_suspended and self.has_bank_details()

    def __str__(self):
        return self.username

class Task(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

class SubAdminTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subadmin_tasks')
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'task')

class Category(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Author(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Editor(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class Manga(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    editor = models.ForeignKey(Editor, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    rental_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)
    stock = models.IntegerField(default=0)
    image = models.FileField(upload_to='mangas/', blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    is_popular = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    consultations = models.IntegerField(default=0)
    sales = models.IntegerField(default=0)

    def __str__(self):
        return self.title

class Rental(models.Model):
    STATUS_CHOICES = (
        ('active', 'En cours'),
        ('returned', 'Rendu'),
        ('damaged', 'Endommagé'),
        ('lost', 'Perdu'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rentals')
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE)
    deposit_paid = models.DecimalField(max_digits=10, decimal_places=2)
    rented_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"{self.user.username} loue {self.manga.title}"

class SiteVisit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    path = models.CharField(max_length=255)
    visited_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username if self.user else 'Anonyme'} a visité {self.path}"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'manga')

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('shipped', 'Expédié'),
        ('delivered', 'Livré'),
        ('cancelled', 'Annulé'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    manga = models.ForeignKey(Manga, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ordered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
