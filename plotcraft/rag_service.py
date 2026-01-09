# rag_service.py
import os
import chromadb
from django.conf import settings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

class RAGService:
    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        
        # 1. ตั้งค่า Model (เหมือนเดิม)
        print("📥 Loading Embedding Model...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )

        if self.api_key:
            self.llm = GoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=self.api_key,
                temperature=0.7
            )
        else:
            self.llm = None

        # 2. เชื่อมต่อ ChromaDB (เปลี่ยนชื่อ Collection เป็น plotcraft)
        try:
            self.chroma_client = chromadb.HttpClient(
                host=os.environ.get("CHROMA_HOST", "chroma_db"), 
                port=int(os.environ.get("CHROMA_PORT", 8000))
            )
            self.collection = self.chroma_client.get_or_create_collection(name="plotcraft_collection")
            print("✅ RAG Service Initialized for Plotcraft")
        except Exception as e:
            print(f"❌ ChromaDB Error: {e}")
            self.collection = None

    def add_character_to_rag(self, char):
        """ จดจำข้อมูลตัวละคร """
        try:
            # สร้างข้อความสรุปตัวละครจาก Field ใน models.py ของคุณ
            content = f"""
            [ข้อมูลตัวละคร]
            ชื่อ: {char.name}
            นามแฝง: {char.alias}
            บทบาท: {char.role}
            นิสัย: {char.personality}
            ปูมหลัง: {char.background}
            จุดแข็ง: {char.strengths}
            จุดอ่อน: {char.weaknesses}
            ทักษะ: {char.skills}
            """
            
            self.collection.add(
                documents=[content],
                embeddings=[self.embeddings.embed_query(content)],
                metadatas=[{
                    "type": "character",
                    "novel_id": str(char.project.id) if char.project else "unknown",
                    "owner_id": str(char.created_by.id) if char.created_by else "unknown",
                    "source_id": str(char.id)
                }],
                ids=[f"char_{char.id}"]
            )
            print(f"✅ RAG Added Character: {char.name} (Owner: {char.created_by.id})")
        except Exception as e:
            print(f"❌ Error adding character: {e}")

    def add_chapter_to_rag(self, chapter):
        """ จดจำเนื้อหาในแต่ละตอน """
        try:
            # ตัดเนื้อหาถ้ายาวเกินไป (Optional) แต่ Gemini รองรับ Context ยาวได้พอสมควร
            content = f"""
            [เนื้อเรื่อง บทที่ {chapter.order}]
            ชื่อตอน: {chapter.title}
            เนื้อหา: {chapter.content}
            """
            
            self.collection.add(
                documents=[content],
                embeddings=[self.embeddings.embed_query(content)],
                metadatas=[{
                    "type": "content",
                    "novel_id": str(chapter.novel.id),
                    "source_id": str(chapter.id),
                    "owner_id": str(chapter.novel.author.id)
                }],
                ids=[f"chap_{chapter.id}"]
            )
            print(f"✅ Added Chapter: {chapter.title}")
        except Exception as e:
             print(f"❌ Error adding chapter: {e}")

    def chat_with_editor(self, user_query, novel_id=None, user_id=None):
        """ ฟังก์ชันคุยกับพี่บก. (รวมร่าง: คุยเล่น + ตรวจงาน) """
        print(f"💬 Chatting with Editor. Novel ID: {novel_id}, User ID: {user_id}")
        
        context_text = ""
        
        # ค้นหาข้อมูล (ต้องมี User ID เสมอเพื่อความปลอดภัย)
        if user_id: 
            try:
                query_vector = self.embeddings.embed_query(user_query)
                
                # สร้างเงื่อนไขค้นหา (Where Clause)
                where_conditions = []
                
                # 1. ต้องเป็นของ User คนนี้เท่านั้น (สำคัญที่สุด!)
                where_conditions.append({"owner_id": str(user_id)})
                
                # 2. ถ้าระบุ Novel ID ก็กรองเพิ่ม
                if novel_id:
                    where_conditions.append({"novel_id": str(novel_id)})
                
                # รวมเงื่อนไข
                if len(where_conditions) > 1:
                    final_where = {"$and": where_conditions}
                else:
                    final_where = where_conditions[0]

                results = self.collection.query(
                    query_embeddings=[query_vector],
                    n_results=3,
                    where=final_where 
                )
                
                docs = results['documents'][0]
                if docs:
                    context_text = "\n\n".join(docs)
                    print(f"📚 Found {len(docs)} related docs")
                    
            except Exception as e:
                print(f"RAG Error: {e}")

        # 2. สร้าง Prompt เดียว ใช้ด้วยกันทั้งเว็บ
        prompt = f"""
        Role: คุณคือ "พี่บก." (Plotcraft Editor) รุ่นพี่ที่สนิทกับนักเขียน (User) มากๆ
        Personality: เก่ง สุภาพ ขี้เล่นนิดๆ ให้กำลังใจเก่ง และมีความรู้เรื่องนิยายแน่นปึ้ก
        
        บริบทนิยายที่กำลังคุยถึง (Context):
        {context_text if context_text else "ไม่ได้ระบุ หรือคุยเรื่องทั่วไป"}
        
        ข้อความจากน้องนักเขียน: 
        "{user_query}"
        
        กติกาการตอบ:
        1. ❌ ห้ามใช้ Markdown เยอะ (ห้าม #, *, -) เอาให้อ่านง่ายเหมือนแชทไลน์
        2. ✅ ตอบสั้น กระชับ (ไม่เกิน 3-4 ประโยค) เหมือนคุยแชท
        3. ✅ ใช้ภาษาพูดที่เป็นกันเอง (แทนตัวว่า "พี่" แทน User ว่า "เรา" หรือ "น้อง")
        4. ถ้ามี Context นิยาย: ให้ตอบโดยอิงข้อมูลนั้น ช่วยวิเคราะห์หรือเสนอไอเดีย
        5. ถ้าไม่มี Context: ให้ชวนคุยเรื่องเทคนิคการเขียน หรือให้กำลังใจทั่วไป
        
        เริ่มตอบได้:
        """
        
        try:
            if self.llm:
                return self.llm.invoke(prompt)
            return "ระบบพี่ยังไม่พร้อมใช้งานครับ (No API Key)"
        except Exception as e:
            return f"โทษที พี่มึนหัวนิดหน่อย (Error: {str(e)})"
    
    def generate_scene_draft(self, scene):
        """ ฟังก์ชันสำหรับช่วยร่างฉากนิยาย (Scene Drafter) """
        print(f"✍️ Drafting Scene: {scene.title}")
        
        try:
            # 1. เตรียมข้อมูลวัตถุดิบ (Raw Data)
            pov_name = scene.pov_character.name if scene.pov_character else "ไม่ระบุ"
            pov_desc = f"นิสัย: {scene.pov_character.personality}, รูปลักษณ์: {scene.pov_character.appearance}" if scene.pov_character else ""
            
            loc_name = scene.location.name if scene.location else "ไม่ระบุ"
            loc_desc = f"สภาพแวดล้อม: {scene.location.terrain}, บรรยากาศ: {scene.location.climate}" if scene.location else ""
            
            other_chars = ", ".join([c.name for c in scene.characters.all()]) or "ไม่มี"

            # 2. สร้าง Prompt สำหรับนักเขียนเงา
            prompt = f"""
            Role: คุณคือ "Ghostwriter" มืออาชีพ หน้าที่ของคุณคือร่างเนื้อหานิยาย (First Draft) จากโครงเรื่องที่กำหนดให้
            
            🏗️ โครงสร้างฉาก (Scene Structure):
            - ชื่อฉาก: {scene.title}
            - ตัวละครดำเนินเรื่อง (POV): {pov_name} ({pov_desc})
            - สถานที่: {loc_name} ({loc_desc})
            - ตัวละครอื่นๆ ในฉาก: {other_chars}
            
            🎯 เป้าหมายของฉาก (Goal): {scene.goal}
            🚧 อุปสรรค/ความขัดแย้ง (Conflict): {scene.conflict}
            🏁 ผลลัพธ์ของฉาก (Outcome): {scene.outcome}
            
            📝 คำสั่งการเขียน:
            1. เขียนบรรยายในรูปแบบ "นิยาย" (Narrative) มุมมองบุคคลที่ 3 (หรือ 1 ตามความเหมาะสมของ POV)
            2. เริ่มต้นด้วยการบรรยายบรรยากาศสถานที่ (Setting the scene) ให้เห็นภาพ
            3. ใส่บทพูด (Dialogue) และการกระทำ (Action) ที่สะท้อนนิสัยตัวละคร
            4. ดำเนินเรื่องให้เห็น "อุปสรรค" ที่ตัวละครต้องเจอ และจบลงที่ "ผลลัพธ์" ตามที่ระบุ
            5. ไม่ต้องเขียนยาวมาก เอาแค่โครงร่างหลักๆ ประมาณ 300-500 คำ เพื่อให้นักเขียนไปเกลาต่อได้
            6. ใช้ภาษาไทยสละสลวย เหมาะกับการเป็นนิยาย
            
            เริ่มร่างเนื้อหา:
            """
            
            if self.llm:
                return self.llm.invoke(prompt)
            return "ระบบยังไม่พร้อมใช้งาน (No API Key)"
            
        except Exception as e:
            print(f"Draft Error: {e}")
            return f"เกิดข้อผิดพลาดในการร่าง: {str(e)}"
        
    def add_scene_to_rag(self, scene):
        """ จดจำข้อมูลโครงสร้างฉาก (Goal, Conflict, Outcome) """
        try:
            # 1. เตรียมข้อมูลให้ AI อ่านง่าย
            pov = scene.pov_character.name if scene.pov_character else "ไม่ระบุ"
            loc = scene.location.name if scene.location else "ไม่ระบุ"
            chars = ", ".join([c.name for c in scene.characters.all()]) or "-"
            
            content = f"""
            [ข้อมูลฉาก]
            ชื่อฉาก: {scene.title} (ลำดับที่ {scene.order})
            สถานะ: {scene.get_status_display()}
            สถานที่: {loc}
            ตัวละครดำเนินเรื่อง (POV): {pov}
            ตัวละครประกอบ: {chars}
            
            🎯 เป้าหมาย (Goal): {scene.goal}
            🚧 อุปสรรค (Conflict): {scene.conflict}
            🏁 ผลลัพธ์ (Outcome): {scene.outcome}
            
            📝 เนื้อหาบางส่วน:
            {scene.content[:1000] if scene.content else "ยังไม่มีเนื้อหา"}
            """
            
            # 2. บันทึกลง ChromaDB
            self.collection.add(
                documents=[content],
                embeddings=[self.embeddings.embed_query(content)],
                metadatas=[{
                    "type": "scene",
                    "novel_id": str(scene.project.id) if scene.project else "unknown",
                    "owner_id": str(scene.created_by.id) if scene.created_by else "unknown",
                    "source_id": str(scene.id)
                }],
                ids=[f"scene_{scene.id}"]
            )
            print(f"✅ RAG Added Scene: {scene.title}")
            
        except Exception as e:
            print(f"❌ Error adding scene: {e}")
        
    def delete_data_from_rag(self, doc_id):
        """ ฟังก์ชันลบข้อมูลออกจากสมอง AI """
        try:
            self.collection.delete(ids=[doc_id])
            print(f"🗑️ Deleted from RAG: {doc_id}")
        except Exception as e:
            print(f"❌ Error deleting from RAG: {e}")
# สร้าง Instance รอไว้เรียกใช้
rag_service = RAGService()