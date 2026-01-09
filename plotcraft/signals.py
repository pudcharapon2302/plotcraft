# plotcraft/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Character, Chapter, Scene # Import Scene เพิ่มเผื่ออนาคต
from .rag_service import rag_service

# ==================== CHARACTER (ตัวละคร) ====================
@receiver(post_save, sender=Character)
def update_character_rag(sender, instance, created, **kwargs):
    rag_service.add_character_to_rag(instance)
    print(f"🔄 RAG Updated: Character '{instance.name}'")

@receiver(post_delete, sender=Character)
def delete_character_rag(sender, instance, **kwargs):
    # ✅ แก้จาก pass เป็นคำสั่งลบจริง
    # ID ต้องตรงกับตอน add (ดูใน rag_service.py บรรทัดที่ 57)
    rag_service.delete_data_from_rag(f"char_{instance.id}")
    print(f"🗑️ RAG Deleted: Character '{instance.name}'")


# ==================== CHAPTER (เนื้อหาตอน) ====================
@receiver(post_save, sender=Chapter)
def update_chapter_rag(sender, instance, created, **kwargs):
    if instance.content: 
        rag_service.add_chapter_to_rag(instance)
        print(f"🔄 RAG Updated: Chapter '{instance.title}'")

# ✅ เพิ่มฟังก์ชันลบตอน (ของเดิมไม่มี)
@receiver(post_delete, sender=Chapter)
def delete_chapter_rag(sender, instance, **kwargs):
    rag_service.delete_data_from_rag(f"chap_{instance.id}")
    print(f"🗑️ RAG Deleted: Chapter '{instance.title}'")

# ==================== SCENE (ฉาก) ====================
@receiver(post_save, sender=Scene)
def update_scene_rag(sender, instance, **kwargs):
    """ เมื่อสร้างหรือแก้ฉาก -> ให้จำข้อมูลฉาก (Goal/Conflict) """
    rag_service.add_scene_to_rag(instance) 
    print(f"🔄 RAG Updated: Scene '{instance.title}'")

@receiver(post_delete, sender=Scene)
def delete_scene_rag(sender, instance, **kwargs):
    """ เมื่อลบฉาก -> ให้ลืม """
    rag_service.delete_data_from_rag(f"scene_{instance.id}")
    print(f"🗑️ RAG Deleted: Scene '{instance.title}'")