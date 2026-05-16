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
            user = form.save()
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
    
    period = request.GET.get('period', 'week')
    now = timezone.now()
    
    if period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = "Aujourd'hui"
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_label = "Ce mois"
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        period_label = "Cette année"
    elif period == 'all':
        start_date = None
        period_label = "Depuis le début"
    else: # Default to week
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = "Cette semaine"

    # Base querysets
    orders_qs = Order.objects.all()
    rentals_qs = Rental.objects.all()
    
    if start_date:
        orders_qs = orders_qs.filter(ordered_at__gte=start_date)
        rentals_qs = rentals_qs.filter(rented_at__gte=start_date)

    # Stats for the dashboard
    stats = {
        'total_mangas': Manga.objects.count(),
        'total_orders': orders_qs.count(),
        'mangas_sold': orders_qs.filter(status='delivered').aggregate(Sum('quantity'))['quantity__sum'] or 0,
        'total_revenue': orders_qs.filter(status='delivered').aggregate(total=Sum(models.F('manga__price') * models.F('quantity')))['total'] or 0,
        'avg_price': Manga.objects.aggregate(Avg('price'))['price__avg'] or 0,
        'avg_order': orders_qs.aggregate(avg=Avg(models.F('manga__price') * models.F('quantity')))['avg'] or 0,
        'active_users': User.objects.filter(is_active=True, is_superuser=False).count(),
        'low_stock': Manga.objects.filter(stock__lt=5).count(),
        'active_rentals': rentals_qs.filter(status='active').count(),
    }
    
    top_mangas = Manga.objects.order_by('-consultations')[:10]
    
    # Top sales based on filtered orders
    top_sales_ids = orders_qs.filter(status='delivered').values('manga').annotate(total_sales=Sum('quantity')).order_by('-total_sales')[:5]
    top_sales = []
    for item in top_sales_ids:
        manga = Manga.objects.get(id=item['manga'])
        manga.period_sales = item['total_sales']
        top_sales.append(manga)
    
    # Sales by category for a chart (filtered)
    category_sales = Category.objects.annotate(
        total_sales=Sum('manga__order__quantity', filter=models.Q(manga__order__status='delivered', manga__order__ordered_at__gte=start_date) if start_date else models.Q(manga__order__status='delivered'))
    ).filter(total_sales__gt=0).order_by('-total_sales')
    
    # Trends Data for Chart.js
    trend_labels = []
    trend_data = []
    
    if period == 'day':
        # Last 24 hours
        for i in range(23, -1, -1):
            hour_time = now - timedelta(hours=i)
            label = hour_time.strftime("%H:00")
            count = orders_qs.filter(ordered_at__hour=hour_time.hour, ordered_at__day=hour_time.day).count()
            trend_labels.append(label)
            trend_data.append(count)
    elif period == 'month':
        # Days of current month
        last_day = (now.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        for day in range(1, last_day.day + 1):
            trend_labels.append(str(day))
            count = orders_qs.filter(ordered_at__day=day).count()
            trend_data.append(count)
    elif period == 'year':
        # 12 Months
        month_names = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        for i in range(1, 13):
            trend_labels.append(month_names[i-1])
            count = orders_qs.filter(ordered_at__month=i).count()
            trend_data.append(count)
    elif period == 'all':
        # Last 5 years
        current_year = now.year
        for year in range(current_year - 4, current_year + 1):
            trend_labels.append(str(year))
            count = orders_qs.filter(ordered_at__year=year).count()
            trend_data.append(count)
    else: # week
        # Last 7 days
        days = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
        start_of_week = now - timedelta(days=now.weekday())
        for i in range(7):
            current_day = start_of_week + timedelta(days=i)
            trend_labels.append(days[i])
            count = orders_qs.filter(ordered_at__day=current_day.day, ordered_at__month=current_day.month).count()
            trend_data.append(count)

    # Active rentals list
    active_rentals_list = rentals_qs.filter(status='active').order_by('due_date')[:5]
    
    return render(request, 'store/admin_dashboard.html', {
        'stats': stats,
        'top_mangas': top_mangas,
        'top_sales': top_sales,
        'category_sales': category_sales,
        'active_rentals_list': active_rentals_list,
        'period': period,
        'period_label': period_label,
        'now': now,
        'trend_labels': trend_labels,
        'trend_data': trend_data,
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

    # Recommendations (Popular or Random)
    recommendations = Manga.objects.filter(is_popular=True).exclude(id__in=recently_viewed_ids).order_by('?')[:15]
    if not recommendations:
        recommendations = Manga.objects.exclude(id__in=recently_viewed_ids).order_by('?')[:15]

    return render(request, 'store/user_manga_list.html', {
        'mangas': mangas,
        'categories': categories,
        'search': search,
        'recently_viewed': recently_viewed,
        'recommendations': recommendations,
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
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="mangas_export.csv"'
    response.write('\ufeff') # BOM for Excel
    
    writer = csv.writer(response, delimiter=';')
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
    
    if Rental.objects.filter(user=request.user, manga=manga, status='active').exists():
        messages.warning(request, "Vous avez déjà une location en cours pour ce manga.")
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
def add_to_cart(request, manga_id):
    manga = get_object_or_404(Manga, id=manga_id)
    if manga.stock <= 0:
        messages.error(request, f"Désolé, {manga.title} est en rupture de stock.")
        return redirect('user_manga_list')
    
    cart = request.session.get('cart', {})
    manga_id_str = str(manga_id)
    
    if manga_id_str in cart:
        if cart[manga_id_str] < manga.stock:
            cart[manga_id_str] += 1
            messages.success(request, f"Une autre unité de {manga.title} a été ajoutée au panier.")
        else:
            messages.warning(request, f"Stock maximum atteint pour {manga.title}.")
    else:
        cart[manga_id_str] = 1
        messages.success(request, f"{manga.title} ajouté au panier.")
    
    request.session['cart'] = cart
    return redirect('user_manga_list')

@login_required
def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0
    
    for manga_id, quantity in cart.items():
        manga = get_object_or_404(Manga, id=manga_id)
        subtotal = manga.price * quantity
        total_price += subtotal
        cart_items.append({
            'manga': manga,
            'quantity': quantity,
            'subtotal': subtotal
        })
    
    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price
    })

@login_required
def update_cart_quantity(request, manga_id, action):
    cart = request.session.get('cart', {})
    manga_id_str = str(manga_id)
    manga = get_object_or_404(Manga, id=manga_id)
    
    if manga_id_str in cart:
        if action == 'increment':
            if cart[manga_id_str] < manga.stock:
                cart[manga_id_str] += 1
            else:
                messages.warning(request, f"Stock maximum atteint pour {manga.title}.")
        elif action == 'decrement':
            if cart[manga_id_str] > 1:
                cart[manga_id_str] -= 1
            else:
                del cart[manga_id_str]
                messages.success(request, f"{manga.title} retiré du panier.")
                
        request.session['cart'] = cart
    return redirect('view_cart')

@login_required
def remove_from_cart(request, manga_id):
    cart = request.session.get('cart', {})
    manga_id_str = str(manga_id)
    if manga_id_str in cart:
        del cart[manga_id_str]
        request.session['cart'] = cart
        messages.success(request, "Article retiré du panier.")
    return redirect('view_cart')

@login_required
def checkout_cart(request):
    if not request.user.has_bank_details():
        messages.warning(request, "Veuillez renseigner vos coordonnées bancaires avant de valider votre panier.")
        return redirect('profile')
    
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Votre panier est vide.")
        return redirect('user_manga_list')
    
    processed_mangas = []
    for manga_id, quantity in cart.items():
        manga = get_object_or_404(Manga, id=manga_id)
        if manga.stock < quantity:
            messages.error(request, f"Stock insuffisant pour {manga.title}. Veuillez ajuster votre panier.")
            return redirect('view_cart')
        processed_mangas.append((manga, quantity))
    
    # All stocks are fine, proceed to create orders
    for manga, quantity in processed_mangas:
        Order.objects.create(user=request.user, manga=manga, quantity=quantity, status='delivered')
        manga.stock -= quantity
        manga.sales += quantity
        manga.save()
    
    # Clear cart
    request.session['cart'] = {}
    messages.success(request, "Merci pour votre achat ! Votre commande a été validée.")
    return redirect('user_manga_list')

@login_required
def order_manga(request, manga_id):
    # This function is now superseded by the cart system for general users, 
    # but we can keep it as a 'Quick Buy' if needed, or redirect to add_to_cart.
    return add_to_cart(request, manga_id)

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
