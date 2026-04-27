from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.http import HttpResponse
import csv
import random
import string
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from .models import User, Manga, Category, Order, Favorite, Task, SubAdminTask, Author, Editor, Rental, SiteVisit
from .forms import SignUpForm, SubAdminForm, MangaForm, BankDetailsForm
from django.contrib import messages

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.password_plain = request.POST.get('password1') # Store plain password from form
            user.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'store/signup.html', {'form': form})

from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_deleted:
                messages.error(request, "Ce compte a été supprimé par l'administration.")
                return redirect('login')
            if user.is_suspended:
                messages.error(request, "Votre compte est suspendu. Contactez un administrateur.")
                return redirect('login')
            
            login(request, user)
            return redirect('dashboard')
        else:
            # Check if user exists but is inactive/deleted/suspended
            username = request.POST.get('username')
            user = User.objects.filter(username=username).first()
            if user:
                if user.is_deleted:
                    messages.error(request, "Ce compte a été supprimé par l'administration.")
                    return redirect('login')
                if user.is_suspended:
                    messages.error(request, "Votre compte est suspendu. Contactez un administrateur.")
                    return redirect('login')
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    else:
        form = AuthenticationForm()
    return render(request, 'store/login.html', {'form': form})

@login_required
def dashboard_redirect(request):
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    elif request.user.is_subadmin:
        # Check if they have specific tasks
        return redirect('admin_dashboard') # For now, subadmins go to a limited admin dashboard
    else:
        return redirect('user_manga_list')

@login_required
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.is_subadmin):
        return redirect('user_manga_list')
    
    # Dates for monthly filtering
    now = timezone.now()
    first_day_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Stats for the dashboard
    stats = {
        'total_mangas': Manga.objects.count(),
        'total_orders': Order.objects.count(),
        'mangas_sold': Order.objects.filter(status='delivered').aggregate(Sum('quantity'))['quantity__sum'] or 0,
        'total_revenue': Order.objects.filter(status='delivered').aggregate(total=Sum(models.F('manga__price') * models.F('quantity')))['total'] or 0,
        'avg_price': Manga.objects.aggregate(Avg('price'))['price__avg'] or 0,
        'avg_order': Order.objects.aggregate(avg=Avg(models.F('manga__price') * models.F('quantity')))['avg'] or 0,
        'active_users': User.objects.filter(is_active=True, is_superuser=False).count(),
        'low_stock': Manga.objects.filter(stock__lt=5).count(),
        'active_rentals': Rental.objects.filter(status='active').count(),
        'monthly_sales': Order.objects.filter(ordered_at__gte=first_day_month, status='delivered').aggregate(Sum('quantity'))['quantity__sum'] or 0,
    }
    
    top_mangas = Manga.objects.order_by('-consultations')[:10]
    top_sales = Manga.objects.order_by('-sales')[:5]
    
    # Sales by category for a chart
    category_sales = Category.objects.annotate(
        total_sales=Sum('manga__sales')
    ).filter(total_sales__gt=0).order_by('-total_sales')
    
    # Active rentals list
    active_rentals_list = Rental.objects.filter(status='active').order_by('due_date')[:5]
    
    return render(request, 'store/admin_dashboard.html', {
        'stats': stats,
        'top_mangas': top_mangas,
        'top_sales': top_sales,
        'category_sales': category_sales,
        'active_rentals_list': active_rentals_list,
    })

@login_required
def manga_detail(request, manga_id):
    manga = get_object_or_404(Manga, id=manga_id)
    manga.consultations += 1
    manga.save()
    
    # Recently Viewed logic
    recently_viewed = request.session.get('recently_viewed', [])
    if manga_id in recently_viewed:
        recently_viewed.remove(manga_id)
    recently_viewed.insert(0, manga_id)
    request.session['recently_viewed'] = recently_viewed[:5] # Keep last 5
    
    return render(request, 'store/manga_detail.html', {'manga': manga})

@login_required
def user_manga_list(request):
    mangas = Manga.objects.all()
    categories = Category.objects.all()
    
    # Search
    search = request.GET.get('search')
    if search:
        mangas = mangas.filter(title__icontains=search)
    
    # Filter by category if provided
    cat_id = request.GET.get('category')
    if cat_id:
        mangas = mangas.filter(category_id=cat_id)
        
    # Recently Viewed
    recently_viewed_ids = request.session.get('recently_viewed', [])
    recently_viewed = Manga.objects.filter(id__in=recently_viewed_ids)
    # Sort to maintain the order from session
    recently_viewed = sorted(recently_viewed, key=lambda m: recently_viewed_ids.index(m.id))

    return render(request, 'store/user_manga_list.html', {
        'mangas': mangas,
        'categories': categories,
        'search': search,
        'recently_viewed': recently_viewed,
    })

# Admin Manga Management
@login_required
def manage_mangas(request):
    if not (request.user.is_superuser or request.user.is_subadmin):
        return redirect('user_manga_list')
    mangas = Manga.objects.all()
    return render(request, 'store/manage_mangas.html', {'mangas': mangas})

@login_required
def add_manga(request):
    if not (request.user.is_superuser or request.user.is_subadmin):
        return redirect('user_manga_list')
    if request.method == 'POST':
        form = MangaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Manga ajouté avec succès.")
            return redirect('manage_mangas')
    else:
        form = MangaForm()
    return render(request, 'store/manga_form.html', {'form': form, 'title': 'Ajouter un Manga'})

@login_required
def edit_manga(request, manga_id):
    if not (request.user.is_superuser or request.user.is_subadmin):
        return redirect('user_manga_list')
    manga = get_object_or_404(Manga, id=manga_id)
    if request.method == 'POST':
        form = MangaForm(request.POST, request.FILES, instance=manga)
        if form.is_valid():
            form.save()
            messages.success(request, "Manga mis à jour.")
            return redirect('manage_mangas')
    else:
        form = MangaForm(instance=manga)
    return render(request, 'store/manga_form.html', {'form': form, 'title': 'Modifier le Manga'})

@login_required
def delete_manga(request, manga_id):
    if not (request.user.is_superuser or request.user.is_subadmin):
        return redirect('user_manga_list')
    manga = get_object_or_404(Manga, id=manga_id)
    manga.delete()
    messages.success(request, "Manga supprimé.")
    return redirect('manage_mangas')

@login_required
def export_mangas_csv(request):
    if not (request.user.is_superuser or request.user.is_subadmin):
        return redirect('user_manga_list')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="mangas_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID', 'Titre', 'Auteur', 'Éditeur', 'Catégorie', 'Prix', 'Stock', 'Ventes'])
    
    mangas = Manga.objects.all().values_list('id', 'title', 'author__name', 'editor__name', 'category__name', 'price', 'stock', 'sales')
    for manga in mangas:
        writer.writerow(manga)
    
    return response

@login_required
def quick_stock_update(request, manga_id):
    if not (request.user.is_superuser or request.user.is_subadmin):
        return redirect('user_manga_list')
    
    manga = get_object_or_404(Manga, id=manga_id)
    new_stock = request.POST.get('stock')
    if new_stock is not None:
        manga.stock = int(new_stock)
        manga.save()
        messages.success(request, f"Stock de {manga.title} mis à jour.")
    return redirect('manage_mangas')

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = BankDetailsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Coordonnées bancaires mises à jour.")
            return redirect('user_manga_list')
    else:
        form = BankDetailsForm(instance=request.user)
    return render(request, 'store/profile.html', {'form': form})

@login_required
def rent_manga(request, manga_id):
    manga = get_object_or_404(Manga, id=manga_id)
    if not request.user.has_bank_details():
        messages.warning(request, "Veuillez renseigner vos coordonnées bancaires avant de louer.")
        return redirect('profile')
    
    if not request.user.can_rent():
        messages.error(request, "Vous ne pouvez plus louer de mangas en raison de fautes ou d'une suspension.")
        return redirect('user_manga_list')
    
    if manga.stock > 0:
        Rental.objects.create(
            user=request.user,
            manga=manga,
            deposit_paid=manga.rental_deposit,
            due_date=timezone.now() + timedelta(days=14)
        )
        manga.stock -= 1
        manga.save()
        messages.success(request, f"Vous avez loué {manga.title}.")
    else:
        messages.error(request, "Stock insuffisant.")
    return redirect('user_manga_list')

@login_required
def return_manga(request, rental_id):
    rental = get_object_or_404(Rental, id=rental_id, user=request.user, status='active')
    status = request.POST.get('status', 'returned')
    
    rental.status = status
    rental.returned_at = timezone.now()
    rental.save()
    
    # Restore stock
    rental.manga.stock += 1
    rental.manga.save()
    
    if status in ['damaged', 'lost']:
        request.user.rental_strikes += 1
        request.user.save()
        messages.warning(request, f"Manga rendu comme {status}. Attention: {request.user.rental_strikes}/3 fautes.")
    else:
        messages.success(request, f"Manga {rental.manga.title} rendu avec succès.")
        
    return redirect('my_rentals')

@login_required
def my_rentals(request):
    rentals = request.user.rentals.all().order_by('-rented_at')
    return render(request, 'store/my_rentals.html', {'rentals': rentals})

# Admin User Management
@login_required
def manage_users(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
    users = User.objects.filter(is_superuser=False, is_deleted=False).order_by('-date_joined')
    return render(request, 'store/manage_users.html', {'users': users})

@login_required
def toggle_user_suspension(request, user_id):
    if not request.user.is_superuser:
        return redirect('dashboard')
    user = get_object_or_404(User, id=user_id)
    user.is_suspended = not user.is_suspended
    user.save()
    status = "suspendu" if user.is_suspended else "réactivé"
    messages.success(request, f"Compte de {user.username} {status}.")
    return redirect('manage_users')

@login_required
def delete_user(request, user_id):
    if not request.user.is_superuser:
        return redirect('dashboard')
    user = get_object_or_404(User, id=user_id)
    username = user.username
    user.is_active = False
    user.is_deleted = True
    user.save()
    messages.success(request, f"Utilisateur {username} marqué comme supprimé.")
    return redirect('manage_users')

@login_required
def view_user_visits(request, user_id):
    if not request.user.is_superuser:
        return redirect('dashboard')
    user = get_object_or_404(User, id=user_id)
    visits = SiteVisit.objects.filter(user=user).order_by('-visited_at')[:100]
    return render(request, 'store/user_visits.html', {'target_user': user, 'visits': visits})

@login_required
def user_detail_admin(request, user_id):
    if not request.user.is_superuser:
        return redirect('dashboard')
    target_user = get_object_or_404(User, id=user_id)
    rentals = target_user.rentals.all().order_by('-rented_at')
    orders = target_user.orders.all().order_by('-ordered_at')
    visits = SiteVisit.objects.filter(user=target_user).order_by('-visited_at')[:50]
    
    return render(request, 'store/user_detail_admin.html', {
        'target_user': target_user,
        'rentals': rentals,
        'orders': orders,
        'visits': visits,
    })

@login_required
def add_to_favorites(request, manga_id):
    manga = get_object_or_404(Manga, id=manga_id)
    Favorite.objects.get_or_create(user=request.user, manga=manga)
    messages.success(request, f"{manga.title} ajouté aux favoris.")
    return redirect('user_manga_list')

@login_required
def remove_from_favorites(request, manga_id):
    manga = get_object_or_404(Manga, id=manga_id)
    Favorite.objects.filter(user=request.user, manga=manga).delete()
    return redirect('favorites_list')

@login_required
def favorites_list(request):
    favorites = Favorite.objects.filter(user=request.user)
    return render(request, 'store/favorites.html', {'favorites': favorites})

@login_required
def order_manga(request, manga_id):
    manga = get_object_or_404(Manga, id=manga_id)
    if not request.user.has_bank_details():
        messages.warning(request, "Veuillez renseigner vos coordonnées bancaires avant d'acheter.")
        return redirect('profile')
        
    if manga.stock > 0:
        Order.objects.create(user=request.user, manga=manga, quantity=1, status='delivered')
        manga.stock -= 1
        manga.sales += 1
        manga.save()
        messages.success(request, f"Achat de {manga.title} réussi.")
    else:
        messages.error(request, "Stock insuffisant.")
    return redirect('user_manga_list')

@login_required
def compare_mangas(request):
    manga_ids = request.GET.getlist('mangas')
    if len(manga_ids) < 2:
        messages.warning(request, "Veuillez sélectionner au moins 2 mangas à comparer.")
        return redirect('user_manga_list')
    
    mangas = Manga.objects.filter(id__in=manga_ids)
    return render(request, 'store/compare.html', {'mangas': mangas})

# Admin Management of Sub-admins
@user_passes_test(lambda u: u.is_superuser)
def manage_subadmins(request):
    subadmins = User.objects.filter(is_subadmin=True)
    return render(request, 'store/manage_subadmins.html', {'subadmins': subadmins})

@user_passes_test(lambda u: u.is_superuser)
def add_subadmin(request):
    if request.method == 'POST':
        form = SubAdminForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Sous-admin ajouté avec succès.")
            return redirect('manage_subadmins')
    else:
        form = SubAdminForm()
    return render(request, 'store/add_subadmin.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def edit_subadmin(request, user_id):
    user = get_object_or_404(User, id=user_id, is_subadmin=True)
    if request.method == 'POST':
        form = SubAdminForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Sous-admin mis à jour.")
            return redirect('manage_subadmins')
    else:
        # Pre-fill tasks
        initial_tasks = [sat.task.id for sat in user.subadmin_tasks.all()]
        form = SubAdminForm(instance=user, initial={'tasks': initial_tasks})
    return render(request, 'store/add_subadmin.html', {'form': form, 'edit': True})

@login_required
def delete_subadmin(request, user_id):
    user = get_object_or_404(User, id=user_id, is_subadmin=True)
    user.delete()
    messages.success(request, "Sous-admin supprimé.")
    return redirect('manage_subadmins')

# Custom Password Reset via Code
def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            code = ''.join(random.choices(string.digits, k=6))
            user.reset_code = code
            user.reset_code_expires = timezone.now() + timedelta(minutes=15)
            user.save()
            # Simulation d'envoi d'email
            messages.success(request, f"Un code de réinitialisation a été généré : {code}")
            return redirect('password_reset_verify')
        except User.DoesNotExist:
            messages.error(request, "Aucun utilisateur trouvé avec cet email.")
    return render(request, 'store/password_reset_request.html')

def password_reset_verify(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        code = request.POST.get('code')
        new_password = request.POST.get('new_password')
        try:
            user = User.objects.get(email=email, reset_code=code)
            if user.reset_code_expires > timezone.now():
                user.set_password(new_password)
                user.password_plain = new_password # Update plain password
                user.reset_code = None
                user.reset_code_expires = None
                user.save()
                messages.success(request, "Mot de passe changé avec succès !")
                return redirect('login')
            else:
                messages.error(request, "Le code a expiré.")
        except User.DoesNotExist:
            messages.error(request, "Email ou code invalide.")
    return render(request, 'store/password_reset_verify.html')
