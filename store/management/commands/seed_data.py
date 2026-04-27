from django.core.management.base import BaseCommand
from store.models import Category, Task, Author, Editor, Manga, User
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seeds the database with initial data'

    def handle(self, *args, **kwargs):
        # Create Tasks
        tasks = ['Gestion des Mangas', 'Gestion des Commandes', 'Gestion des Catégories', 'Gestion des Utilisateurs']
        for t_name in tasks:
            Task.objects.get_or_create(name=t_name, description=f"Tâche de {t_name}")

        # Create Categories
        categories = ['Action', 'Adventure', 'Horror', 'Mystery', 'Comedy']
        cat_objs = {}
        for c_name in categories:
            cat, _ = Category.objects.get_or_create(name=c_name)
            cat_objs[c_name] = cat

        # Create Authors
        authors = ['Eiichiro Oda', 'Masashi Kishimoto', 'Hajime Isayama', 'Tsugumi Ohba', 'Akira Toriyama']
        auth_objs = {}
        for a_name in authors:
            auth, _ = Author.objects.get_or_create(name=a_name)
            auth_objs[a_name] = auth

        # Create Editors
        editors = ['Shueisha', 'Kodansha', 'Viz Media']
        edit_objs = {}
        for e_name in editors:
            edit, _ = Editor.objects.get_or_create(name=e_name)
            edit_objs[e_name] = edit

        # Create Mangas
        mangas_data = [
            ('One Piece', 'Eiichiro Oda', 'Shueisha', 'Adventure', 9.99, 10, True),
            ('Naruto', 'Masashi Kishimoto', 'Shueisha', 'Action', 10.99, 5, True),
            ('Attack on Titan', 'Hajime Isayama', 'Kodansha', 'Horror', 11.99, 0, False),
            ('Death Note', 'Tsugumi Ohba', 'Viz Media', 'Mystery', 8.50, 15, False),
            ('Dragon Ball', 'Akira Toriyama', 'Shueisha', 'Action', 9.50, 20, True),
        ]

        for title, auth, edit, cat, price, stock, popular in mangas_data:
            Manga.objects.get_or_create(
                title=title,
                author=auth_objs[auth],
                editor=edit_objs[edit],
                category=cat_objs[cat],
                price=Decimal(price),
                stock=stock,
                is_popular=popular
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded data'))
