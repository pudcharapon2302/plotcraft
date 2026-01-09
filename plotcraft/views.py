import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.conf.urls.static import static
from django.urls import reverse
import json

import io
from django.template.loader import render_to_string
from django.utils.text import slugify

# Library สำหรับ Export (ต้องติดตั้งก่อน)
from ebooklib import epub
from weasyprint import HTML, CSS
from django.utils.encoding import escape_uri_path

from .models import (
    Novel, Chapter, Character, Location, Item,
    Scene, Timeline, TimelineEvent, Profile, User
)
from .forms import (
    UserForm, RegisterForm, ProfileForm, NovelForm, ChapterForm,
    CharacterForm, LocationForm, ItemForm, SceneForm, TimelineForm, EventForm
)

from .rag_service import rag_service


# ==================== AUTHENTICATION & PROFILE (from myapp) ====================

def landing(request):
    return render(request, 'landing.html')


def home(request):
    max_items = 3
    if request.user.is_authenticated:
        characters = Character.objects.filter(created_by=request.user).order_by('-created_at')[:max_items]
        novels = Novel.objects.filter(author=request.user).order_by('-updated_at')[:max_items]
        locations = Location.objects.filter(created_by=request.user).order_by('-created_at')[:max_items]
    else:
        characters = Character.objects.all().order_by('-created_at')[:max_items]
        novels = Novel.objects.all().order_by('-updated_at')[:max_items]
        locations = Location.objects.all().order_by('-created_at')[:max_items]

    return render(request, 'home.html', {
        'characters': characters,
        'novels': novels,
        'locations': locations,
    })


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect('plotcraft:home')
        else:
            messages.error(request, "Unsuccessful registration. Invalid information.")
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('plotcraft:landing')

def login_view(request):
    return render(request, 'registration/login.html')

@login_required
def profile(request):
    if request.method == 'POST':
        if 'delete_account' in request.POST:
            user = request.user
            logout(request)
            user.delete()
            return redirect('plotcraft:landing')

        u_form = UserForm(request.POST, instance=request.user)
        p_form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'บันทึกข้อมูลสำเร็จ')
            return redirect('plotcraft:profile')
    else:
        u_form = UserForm(instance=request.user)
        p_form = ProfileForm(instance=request.user.profile)

    return render(request, 'profile.html', {'u_form': u_form, 'p_form': p_form})


@login_required
def global_search(request):
    query = request.GET.get('q', '')
    results = {}
    
    if query:
        results['projects'] = Novel.objects.filter(
            Q(title__icontains=query) | Q(synopsis__icontains=query),
            author=request.user
        )

        results['characters'] = Character.objects.filter(
            Q(name__icontains=query) | 
            Q(background__icontains=query) | 
            Q(personality__icontains=query) |
            Q(appearance__icontains=query) |
            Q(alias__icontains=query),
            created_by=request.user
        )

        results['scenes'] = Scene.objects.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query),
            created_by=request.user
        )

        results['timeline_events'] = TimelineEvent.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query),
            timeline__created_by=request.user
        )

        results['locations'] = Location.objects.filter(
            Q(name__icontains=query) |
            Q(history__icontains=query) |
            Q(terrain__icontains=query) |
            Q(climate__icontains=query) |
            Q(ecosystem__icontains=query) |
            Q(myths__icontains=query) |
            Q(culture__icontains=query) |
            Q(politics__icontains=query) |
            Q(economy__icontains=query) |
            Q(language__icontains=query),
            created_by=request.user
        )

        results['items'] = Item.objects.filter(
            Q(name__icontains=query) |
            Q(appearance__icontains=query) |
            Q(history__icontains=query) |
            Q(abilities__icontains=query) |
            Q(limitations__icontains=query),
            created_by=request.user
        )

    return render(request, 'search_results.html', {'query': query, 'results': results})


# ==================== NOVEL & CHAPTER ====================

@login_required
def novel_list(request):
    novels = Novel.objects.filter(author=request.user).order_by('-updated_at')
    return render(request, 'notes/novel_list.html', {'novels': novels})


@login_required
def novel_create(request):
    if request.method == 'POST':
        form = NovelForm(request.POST, request.FILES)
        if form.is_valid():
            novel = form.save(commit=False)
            novel.author = request.user
            novel.save()
            return redirect('plotcraft:novel_detail', pk=novel.id)
    else:
        form = NovelForm()
    return render(request, 'notes/novel_create.html', {'form': form})


@login_required
def novel_edit(request, pk):
    novel = get_object_or_404(Novel, pk=pk, author=request.user)
    if request.method == 'POST':
        form = NovelForm(request.POST, request.FILES, instance=novel)
        if form.is_valid():
            form.save()
            return redirect('plotcraft:novel_detail', pk=novel.id)
    else:
        form = NovelForm(instance=novel)
    return render(request, 'notes/novel_create.html', {'form': form, 'is_edit': True})


@login_required
def novel_detail(request, pk):
    novel = get_object_or_404(Novel, pk=pk, author=request.user)
    chapters = novel.chapters.all().order_by('order')
    return render(request, 'notes/novel_detail.html', {'novel': novel, 'chapters': chapters})


@login_required
def novel_delete(request, pk):
    novel = get_object_or_404(Novel, pk=pk, author=request.user)
    if request.method == 'POST':
        novel.delete()
        return redirect('plotcraft:novel_list')
    return render(request, 'notes/novel_confirm_delete.html', {'novel': novel})


@login_required
def chapter_create(request, novel_id):
    novel = get_object_or_404(Novel, pk=novel_id, author=request.user)
    
    if request.method == 'POST':
        form = ChapterForm(request.POST)
        if form.is_valid():
            chapter = form.save(commit=False)
            chapter.novel = novel
            chapter.save()
            return redirect('plotcraft:chapter_edit', novel_id=novel.id, chapter_id=chapter.id)
    else:
        next_order = novel.chapters.count() + 1
        form = ChapterForm(initial={'order': next_order})
    
    return render(request, 'notes/chapter_create.html', {'form': form, 'novel': novel})


@login_required
def chapter_edit(request, novel_id, chapter_id):
    novel = get_object_or_404(Novel, pk=novel_id, author=request.user)
    chapter = get_object_or_404(Chapter, pk=chapter_id, novel=novel)

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        
        # รับค่า is_draft จาก Form (ส่งมาเป็น String 'true' หรือ 'false')
        is_draft_str = request.POST.get('is_draft') 
        
        chapter.title = title
        chapter.content = content
        
        # ตรวจสอบถ้ามีการส่งสถานะมาให้บันทึกด้วย
        if is_draft_str:
            chapter.is_draft = True if is_draft_str == 'true' else False
            
        chapter.save()
        
        return redirect('plotcraft:novel_detail', pk=novel.id)

    return render(request, 'notes/chapter_write.html', {'novel': novel, 'chapter': chapter})


@login_required
def chapter_delete(request, pk):
    chapter = get_object_or_404(Chapter, pk=pk, novel__author=request.user)
    novel_id = chapter.novel.id
    if request.method == 'POST':
        chapter.delete()
    return redirect('plotcraft:novel_detail', pk=novel_id)

@login_required
def change_chapter_status(request, chapter_id, status):
    # ฟังก์ชันสำหรับเปลี่ยนสถานะ Draft/finish แบบไม่ต้องรีโหลดหน้า
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    # ตรวจสอบสิทธิ์ความเป็นเจ้าของก่อนบันทึก (กันคนอื่นมาแก้)
    # if chapter.novel.author != request.user:
    #    return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if status == 'finish':
        chapter.is_draft = False
    elif status == 'draft':
        chapter.is_draft = True
        
    chapter.save()
    
    # ส่งค่ากลับไปบอกหน้าเว็บว่าทำสำเร็จแล้ว
    return JsonResponse({'success': True, 'is_draft': chapter.is_draft})

@login_required
def chapter_preview(request, pk):
    chapter = get_object_or_404(Chapter, id=pk)
    
    if chapter.novel.author != request.user:
         return HttpResponseForbidden("คุณไม่มีสิทธิ์ดูตัวอย่างตอนนี้")

    # หาตอนที่มี order น้อยกว่าปัจจุบัน (ตอนก่อนหน้า)
    previous_chapter = Chapter.objects.filter(
        novel=chapter.novel, 
        order__lt=chapter.order
    ).order_by('-order').first()
    
    # หาตอนที่มี order มากกว่าปัจจุบัน (ตอนถัดไป)
    next_chapter = Chapter.objects.filter(
        novel=chapter.novel, 
        order__gt=chapter.order
    ).order_by('order').first()

    # ส่งตัวแปรเพิ่มเข้าไปใน template
    return render(request, 'notes/chapter_preview.html', {
        'chapter': chapter,
        'previous_chapter': previous_chapter,
        'next_chapter': next_chapter,
    })



# ==================== WORLDBUILDING (Characters, Locations, Items) ====================

def worldbuilding_overview(request):
    return render(request, "worldbuilding/overview.html")


@login_required
def character_list(request):
    base_characters = Character.objects.filter(created_by=request.user)
    
    project_id = request.GET.get('project')
    if project_id:
        project = get_object_or_404(Novel, id=project_id)
        characters = base_characters.filter(project=project)
    else:
        characters = base_characters.order_by('-created_at')

    return render(request, 'worldbuilding/character_list.html', {
        'characters': characters,
    })


@login_required
def character_create(request):
    if request.method == 'POST':
        form = CharacterForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            character = form.save(commit=False)
            if request.user.is_authenticated:
                character.created_by = request.user
            character.save()
            form.save_m2m()
            return redirect('plotcraft:character_detail', pk=character.id)
    else:
        initial = {}
        project_id = request.GET.get('project')
        if project_id:
            try:
                initial['project'] = Novel.objects.get(id=project_id, author=request.user)
            except Novel.DoesNotExist:
                pass
        form = CharacterForm(request.user, initial=initial)
    return render(request, 'worldbuilding/character_form.html', {'form': form})


@login_required
def character_edit(request, pk):
    character = get_object_or_404(Character, id=pk) 
    
    if character.created_by != request.user:
        messages.error(request, "คุณไม่มีสิทธิ์แก้ไข/ลบตัวละครนี้")
        return redirect('plotcraft:character_detail', pk=pk)

    if request.method == 'POST':
        
        if "character_delete" in request.POST:
            character_name = character.name
            character.delete()
            messages.success(request, f"ลบตัวละคร '{character_name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:character_list')
        
        form = CharacterForm(request.user, request.POST, request.FILES, instance=character)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            form.save_m2m()
            messages.success(request, f"บันทึกตัวละคร '{obj.name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:character_detail', pk=obj.id)
        
    else:
        form = CharacterForm(request.user, instance=character)

    return render(request, 'worldbuilding/character_form.html', {
        'form': form,
        'character': character,
    })


@login_required
def character_detail(request, pk):
    character = get_object_or_404(Character, id=pk)
    return render(request, 'worldbuilding/character_detail.html', {'character': character})


@login_required
def location_create(request):
    if request.method == 'POST':
        form = LocationForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            location = form.save(commit=False)
            location.created_by = request.user
            location.save()
            form.save_m2m()
            messages.success(request, f"สร้างสถานที่ '{location.name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:location_detail', pk=location.id)
    else:
        initial = {}
        project_id = request.GET.get('project')
        if project_id:
            try:
                initial['project'] = Novel.objects.get(id=project_id, author=request.user)
            except Novel.DoesNotExist:
                pass
        form = LocationForm(request.user, initial=initial)
    return render(request, 'worldbuilding/location_form.html', {'form': form})


@login_required
def location_list(request):
    locations = Location.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'worldbuilding/location_list.html', {'locations': locations})


@login_required
def location_detail(request, pk):
    location = get_object_or_404(Location, id=pk)
    return render(request, 'worldbuilding/location_detail.html', {'location': location})


@login_required
def location_edit(request, pk):
    location = get_object_or_404(Location, id=pk)
    
    if location.created_by != request.user:
        messages.error(request, "คุณไม่มีสิทธิ์แก้ไข/ลบสถานที่นี้")
        return redirect('plotcraft:location_detail', pk=pk)

    if request.method == 'POST':
        if "location_delete" in request.POST:
            location_name = location.name
            location.delete()
            messages.success(request, f"ลบสถานที่ '{location_name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:location_list')
        
        form = LocationForm(request.user, request.POST, request.FILES, instance=location)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            form.save_m2m()
            messages.success(request, f"บันทึกสถานที่ '{obj.name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:location_detail', pk=obj.id)
    else:
        form = LocationForm(request.user, instance=location)

    return render(request, 'worldbuilding/location_form.html', {
        'form': form,
        'location': location,
    })


@login_required
def item_create(request):
    if request.method == 'POST':
        form = ItemForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()
            form.save_m2m()
            messages.success(request, f"สร้างไอเท็ม '{item.name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:item_detail', pk=item.id)
    else:
        initial = {}
        project_id = request.GET.get('project')
        if project_id:
            try:
                initial['project'] = Novel.objects.get(id=project_id, author=request.user)
            except Novel.DoesNotExist:
                pass
        form = ItemForm(request.user, initial=initial)
    return render(request, 'worldbuilding/item_form.html', {'form': form})


@login_required
def item_list(request):
    items = Item.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'worldbuilding/item_list.html', {'items': items})


@login_required
def item_detail(request, pk):
    item = get_object_or_404(Item, id=pk)
    return render(request, 'worldbuilding/item_detail.html', {'item': item})


@login_required
def item_edit(request, pk):
    item = get_object_or_404(Item, id=pk)
    
    if item.created_by != request.user:
        messages.error(request, "คุณไม่มีสิทธิ์แก้ไข/ลบไอเท็มนี้")
        return redirect('plotcraft:item_detail', pk=pk)

    if request.method == 'POST':
        if "item_delete" in request.POST:
            item_name = item.name
            item.delete()
            messages.success(request, f"ลบไอเท็ม '{item_name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:item_list')
        
        form = ItemForm(request.user, request.POST, request.FILES, instance=item)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            form.save_m2m()
            messages.success(request, f"บันทึกไอเท็ม '{obj.name}' เรียบร้อยแล้ว")
            return redirect('plotcraft:item_detail', pk=obj.id)
    else:
        form = ItemForm(request.user, instance=item)

    return render(request, 'worldbuilding/item_form.html', {
        'form': form,
        'item': item,
    })


# ==================== SCENES ====================

@login_required
def scene_list(request):
    projects = Novel.objects.filter(author=request.user)
    scenes = Scene.objects.filter(created_by=request.user).order_by('order')
    
    selected_project_id = request.GET.get('project')
    selected_project = None

    if selected_project_id:
        scenes = scenes.filter(project_id=selected_project_id)
        if projects.filter(id=selected_project_id).exists():
            selected_project = projects.get(id=selected_project_id)

    context = {
        'scenes': scenes,
        'projects': projects,
        'selected_project': selected_project,
    }
    return render(request, 'scenes/scene_list.html', context)


@login_required
def scene_create(request):
    if request.method == 'POST':
        form = SceneForm(request.user, request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            form.save_m2m() # สำคัญมากสำหรับ ManyToMany
            
            messages.success(request, f"สร้างฉาก '{obj.title}' เรียบร้อย เริ่มร่างเนื้อหาด้วย AI ได้เลย!")
            
            # ✅ แก้ตรงนี้ 1: สร้างเสร็จ ให้เด้งไปหน้า Edit ของฉากนั้นทันที
            return redirect('plotcraft:scene_edit', pk=obj.pk) 
            
    else:
        # (ส่วน GET เหมือนเดิม)
        initial = {}
        if 'project' in request.GET:
             # แนะนำให้ดึง project_id มาใส่ initial ไว้เลย ถ้าทำได้
             # initial['project'] = request.GET.get('project') 
             pass
        form = SceneForm(request.user, initial=initial)

    return render(request, 'scenes/scene_form.html', {'form': form})


@login_required
def scene_edit(request, pk):
    scene = get_object_or_404(Scene, pk=pk)

    if scene.created_by != request.user:
        messages.error(request, "ไม่มีสิทธิ์แก้ไข")
        return redirect('plotcraft:scene_list')

    if request.method == 'POST':
        # 1. ✅ เก็บ ID นิยายไว้ก่อนลบ (สำคัญ! ต้องทำก่อน delete)
        project_id = scene.project.id if scene.project else None
        
        if "scene_delete" in request.POST:
            scene.delete()
            messages.success(request, "ลบฉากเรียบร้อย")

            # 2. ✅ สร้าง URL แบบ Dynamic (ปลอดภัยกว่า Hardcode)
            target_url = reverse('plotcraft:scene_list')
            if project_id:
                target_url += f"?project={project_id}"
            
            return redirect(target_url)

        # --- ส่วนบันทึกข้อมูล (เหมือนเดิม) ---
        form = SceneForm(request.user, request.POST, instance=scene)
        if form.is_valid():
            form.save()
            messages.success(request, "บันทึกข้อมูลแล้ว กดปุ่ม AI เพื่อร่างเนื้อหาต่อได้เลย")
            return redirect('plotcraft:scene_edit', pk=scene.pk)

    else:
        form = SceneForm(request.user, instance=scene)

    return render(request, 'scenes/scene_form.html', {'form': form, 'scene': scene})


# ==================== TIMELINE ====================

def timeline_list(request):
    if request.user.is_authenticated:
        timelines = Timeline.objects.filter(created_by=request.user).order_by('-updated_at')
    else:
        timelines = Timeline.objects.all().order_by('-updated_at')
    return render(request, 'timeline/timeline_list.html', {'timelines': timelines})


@login_required
def timeline_create(request):
    if request.method == 'POST':
        form = TimelineForm(request.POST, user=request.user) 
        
        if form.is_valid():
            timeline = form.save(commit=False)
            timeline.created_by = request.user
            timeline.save()
            return redirect('plotcraft:timeline_detail', pk=timeline.id)
    else:
        form = TimelineForm(user=request.user)
    
    return render(request, 'timeline/timeline_form.html', {'form': form})


def timeline_detail(request, pk):
    timeline = get_object_or_404(Timeline, id=pk)
    events = timeline.events.all().order_by('order')

    if request.user.is_authenticated:
        event_form = EventForm(user=request.user, timeline=timeline)
    else:
        event_form = EventForm()

    return render(request, 'timeline/timeline_detail.html', {
        'timeline': timeline,
        'events': events,
        'event_form': event_form,
    })


@login_required
def timeline_delete(request, pk):
    timeline = get_object_or_404(Timeline, id=pk)
    if timeline.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden()
    if request.method == 'POST':
        timeline.delete()
        return redirect('plotcraft:timeline_list')
    return render(request, 'timeline/timeline_confirm_delete.html', {'timeline': timeline})


@require_POST
def update_event_order(request):
    try:
        data = json.loads(request.body)
        event_ids = data.get('ids', [])
        for index, event_id in enumerate(event_ids):
            TimelineEvent.objects.filter(
                id=event_id, 
                timeline__created_by=request.user
            ).update(order=index)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error'}, status=400)

    
@login_required
def timeline_event_create(request, pk):
    timeline = get_object_or_404(Timeline, id=pk)
    
    if timeline.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, user=request.user, timeline=timeline)
        
        if form.is_valid():
            ev = form.save(commit=False)
            ev.timeline = timeline
            ev.save()
            form.save_m2m()
            return redirect('plotcraft:timeline_detail', pk=timeline.id)
    else:
        form = EventForm(user=request.user, timeline=timeline)
    
    return render(request, 'timeline/event_form.html', {'form': form, 'timeline': timeline})


@login_required
def timeline_event_update(request, pk):
    event = get_object_or_404(TimelineEvent, id=pk)
    
    if event.timeline.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, user=request.user, instance=event)
        if form.is_valid():
            form.save()
            return redirect('plotcraft:timeline_detail', pk=event.timeline.id)
    else:
        form = EventForm(user=request.user, instance=event)
    
    return render(request, 'timeline/event_form.html', {'form': form, 'event': event})


@login_required
def timeline_event_delete(request, pk):
    event = get_object_or_404(TimelineEvent, id=pk)
    
    if event.timeline.created_by != request.user and not request.user.is_staff:
        return HttpResponseForbidden()
    
    timeline_id = event.timeline.id
    if request.method == 'POST':
        event.delete()
        messages.success(request, "ลบเหตุการณ์เรียบร้อย")
        return redirect('plotcraft:timeline_detail', pk=timeline_id)
    
    return render(request, 'timeline/event_confirm_delete.html', {'event': event})


# ==================== RAG SERVICE INTEGRATION ====================

@csrf_exempt
@login_required
def ai_generate_scene(request, scene_id):
    """ API สำหรับกดปุ่ม 'Generate Draft' """
    if request.method == "POST":
        # 1. ดึงข้อมูล Scene มา (ต้องเป็นเจ้าของเท่านั้น)
        # หมายเหตุ: ใน models.py ของคุณ Scene ไม่ได้ผูกกับ User โดยตรง แต่ผูกผ่าน Project -> Owner
        # ดังนั้นต้องเช็คผ่าน project__owner
        scene = get_object_or_404(Scene, pk=scene_id, project__author=request.user)
        
        # 2. เรียก AI ให้ร่างให้
        draft_content = rag_service.generate_scene_draft(scene)
        
        # 3. ส่งเนื้อหากลับไป
        try:
             draft_content = rag_service.generate_scene_draft(scene)
             return JsonResponse({'draft': draft_content})
        except Exception as e:
             return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
@login_required
def ai_chat_general(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            novel_id = data.get('novel_id')
            
            reply = rag_service.chat_with_editor(
                user_message, 
                novel_id=novel_id, 
                user_id=request.user.id
            )
            
            return JsonResponse({'reply': reply})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)