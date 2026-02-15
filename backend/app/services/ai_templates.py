
from openai import OpenAI
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models import Run, Video, Template
import json

class SentimentTemplates:
    def __init__(self, db: Session, run_id: str):
        self.db = db
        self.run_id = run_id
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )

    def generate(self):
        """
        Generates 10 reusable title templates based on collected videos.
        """
        # Fetch videos for this run
        videos = self.db.query(Video).filter(Video.run_id == self.run_id).all()
        
        if not videos:
            return

        titles = [v.title for v in videos]
        titles_str = "\n".join([f"- {t}" for t in titles])

        prompt = f"""
        Analyze these high-performing YouTube titles:
        {titles_str}

        Generate 10 reusable title templates based on the winning patterns found in these titles.
        For each template, provide 2 example applications.
        
        Return the result as a raw JSON array of objects with keys: "template_text", "example_1", "example_2".
        Do not include markdown formatting.
        """

        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a YouTube expert. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        content = response.choices[0].message.content
        try:
            templates_data = json.loads(content)
            
            for t in templates_data:
                template = Template(
                    run_id=self.run_id,
                    template_text=t.get("template_text"),
                    example_1=t.get("example_1"),
                    example_2=t.get("example_2")
                )
                self.db.add(template)
            
            self.db.commit()

        except json.JSONDecodeError:
            # Fallback or log error
            pass
