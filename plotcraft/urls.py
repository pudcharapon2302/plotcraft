from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'plotcraft'

urlpatterns = [
    # ==================== AUTHENTICATION ====================
    path('', views.landing, name='landing'),
    path('home/', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('quickguide/', auth_views.TemplateView.as_view(template_name='Quickguide.html'), name='quickguide'),
    path('search/', views.global_search, name='global_search'),

    # ==================== NOVELS ====================
    path('notes/', views.novel_list, name='novel_list'),
    path('notes/create/', views.novel_create, name='novel_create'),
    path('notes/<int:pk>/', views.novel_detail, name='novel_detail'),
    path('notes/<int:pk>/edit/', views.novel_edit, name='novel_edit'),
    path('notes/<int:pk>/delete/', views.novel_delete, name='novel_delete'),
    path('notes/<int:novel_id>/chapter/add/', views.chapter_create, name='chapter_create'),
    path('notes/<int:novel_id>/chapter/<int:chapter_id>/write/', views.chapter_edit, name='chapter_edit'),
    path('notes/chapter/<int:pk>/delete/', views.chapter_delete, name='chapter_delete'),
    path('notes/chapter/<int:chapter_id>/status/<str:status>/', views.change_chapter_status, name='change_chapter_status'),
    path('notes/chapter/<int:pk>/preview/', views.chapter_preview, name='chapter_preview'),

    # ==================== WORLDBUILDING ====================
    path('worldbuilding/', views.worldbuilding_overview, name='worldbuilding_overview'),
    
    # Characters
    path('worldbuilding/characters/', views.character_list, name='character_list'),
    path('worldbuilding/characters/create/', views.character_create, name='character_create'),
    path('worldbuilding/characters/<int:pk>/', views.character_detail, name='character_detail'),
    path('worldbuilding/characters/<int:pk>/edit/', views.character_edit, name='character_edit'),
    
    # Locations
    path('worldbuilding/locations/', views.location_list, name='location_list'),
    path('worldbuilding/locations/create/', views.location_create, name='location_create'),
    path('worldbuilding/locations/<int:pk>/', views.location_detail, name='location_detail'),
    path('worldbuilding/locations/<int:pk>/edit/', views.location_edit, name='location_edit'),
    
    # Items
    path('worldbuilding/items/', views.item_list, name='item_list'),
    path('worldbuilding/items/create/', views.item_create, name='item_create'),
    path('worldbuilding/items/<int:pk>/', views.item_detail, name='item_detail'),
    path('worldbuilding/items/<int:pk>/edit/', views.item_edit, name='item_edit'),

    # ==================== SCENES ====================
    path('scenes/', views.scene_list, name='scene_list'),
    path('scenes/create/', views.scene_create, name='scene_create'),
    path('scenes/<int:pk>/edit/', views.scene_edit, name='scene_edit'),

    # ==================== TIMELINE ====================
    path('timeline/', views.timeline_list, name='timeline_list'),
    path('timeline/create/', views.timeline_create, name='timeline_create'),
    path('timeline/<int:pk>/', views.timeline_detail, name='timeline_detail'),
    path('timeline/<int:pk>/event/create/', views.timeline_event_create, name='timeline_event_create'),
    path('timeline/<int:pk>/delete/', views.timeline_delete, name='timeline_delete'),
    path('timeline/event/<int:pk>/update/', views.timeline_event_update, name='timeline_event_update'),
    path('timeline/event/<int:pk>/delete/', views.timeline_event_delete, name='timeline_event_delete'),
    path('timeline/reorder/', views.update_event_order, name='update_event_order'),

    # ==================== RAG-ASSISTED WRITING ====================
    path('api/chat/general/', views.ai_chat_general, name='ai_chat_general'),
    path('api/generate-scene/<int:scene_id>/', views.ai_generate_scene, name='ai_generate_scene'),
]
