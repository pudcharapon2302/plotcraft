from django.apps import AppConfig


class PlotcraftConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plotcraft'

    def ready(self):
        import plotcraft.signals