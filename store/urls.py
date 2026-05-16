from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard_redirect, name='dashboard'),
    path('signup/', views.signup_view, name='signup'),
    path('profile/', views.profile_view, name='profile'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Custom Password Reset via Code
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    
    # Admin Dashboard
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('management/subadmins/', views.manage_subadmins, name='manage_subadmins'),
    path('management/subadmins/add/', views.add_subadmin, name='add_subadmin'),
    path('management/subadmins/edit/<int:user_id>/', views.edit_subadmin, name='edit_subadmin'),
    path('management/subadmins/delete/<int:user_id>/', views.delete_subadmin, name='delete_subadmin'),
    
    # User views
    path('mangas/', views.user_manga_list, name='user_manga_list'),
    path('mangas/<int:manga_id>/', views.manga_detail, name='manga_detail'),
    
    # Admin Manga Management
    path('management/mangas/', views.manage_mangas, name='manage_mangas'),
    path('management/mangas/add/', views.add_manga, name='add_manga'),
    path('management/mangas/edit/<int:manga_id>/', views.edit_manga, name='edit_manga'),
    path('management/mangas/delete/<int:manga_id>/', views.delete_manga, name='delete_manga'),
    path('management/mangas/export/', views.export_mangas_csv, name='export_mangas_csv'),
    path('management/mangas/quick-stock/<int:manga_id>/', views.quick_stock_update, name='quick_stock_update'),
    # Rental views
    path('rent/<int:manga_id>/', views.rent_manga, name='rent_manga'),
    path('rentals/', views.my_rentals, name='my_rentals'),
    path('rentals/return/<int:rental_id>/', views.return_manga, name='return_manga'),
    
    # Admin User Management
    path('management/users/', views.manage_users, name='manage_users'),
    path('management/users/suspend/<int:user_id>/', views.toggle_user_suspension, name='toggle_user_suspension'),
    path('management/users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('management/users/visits/<int:user_id>/', views.view_user_visits, name='view_user_visits'),
    path('management/users/detail/<int:user_id>/', views.user_detail_admin, name='user_detail_admin'),
    
    path('favorites/', views.favorites_list, name='favorites_list'),
    path('favorites/add/<int:manga_id>/', views.add_to_favorites, name='add_to_favorites'),
    path('favorites/remove/<int:manga_id>/', views.remove_from_favorites, name='remove_from_favorites'),
    
    # Cart views
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:manga_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:manga_id>/<str:action>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/remove/<int:manga_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/checkout/', views.checkout_cart, name='checkout_cart'),
    
    path('order/<int:manga_id>/', views.order_manga, name='order_manga'),
    path('compare/', views.compare_mangas, name='compare_mangas'),
]
