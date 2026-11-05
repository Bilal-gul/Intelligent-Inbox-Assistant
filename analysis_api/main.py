import os
import json
import httpx
from fastapi import FastAPI, HTTPException, status
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq

from schemas import EmailRequest, EmailResponse

load_dotenv()

app = FastAPI(title="Email Analysis API")

groq_api_key = os.getenv("LLM_API_KEY")
groq_client = Groq(api_key=groq_api_key)

DB_SERVICE_URL = os.getenv("DB_SERVICE_URL")

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

@app.post("/api/v1/emails/analyze", response_model=EmailResponse)
async def analyze_email(request_data: EmailRequest):

    cleaned_body = clean_html(request_data.body_html)

    system_prompt = """
      Sen gelen e-postaları analiz eden uzman bir yapay zeka asistanısın. 
      Görevin, sana verilen e-posta metnini analiz edip SADECE aşağıdaki JSON formatında yanıt vermektir. 

      Yanıtında JSON dışında hiçbir açıklama, selamlama veya ekstra metin bulunmamalıdır.

      Beklenen JSON Formatı:
      {
        "classification": {
          "primary_category": "work | academic | personal | finance | spam | other",
              "tags": ["etiket1", "etiket2"],
          "email_type": "request | announcement | discussion | notification"
        },
        "summary": "E-postanın kısa ve net özeti.",
        "tasks": [
          {
            "title": "Görev başlığı",
            "description": "Görev açıklaması",
            "deadline": "YYYY-MM-DDTHH:MM:SSZ veya null",
            "priority": "low | medium | high",
            "status": "pending"
          }
        ],
        "events": [
          {
            "title": "Etkinlik/Toplantı başlığı",
            "start_at": "YYYY-MM-DDTHH:MM:SSZ veya null",
            "end_at": "YYYY-MM-DDTHH:MM:SSZ veya null",
            "location": "Konum veya null"
          }
        ],
        "evidence": [
          {
            "field_path": "hangi alan olduğu (örn: tasks[0].deadline)",
            "quote": "E-postadan alınan ilgili cümle"
          }
        ]
      }
    """

    user_content = f"""
    Gönderen: {request_data.sender}
    Konu: {request_data.subject}
    Tarih: {request_data.received_at}
    İçerik: {cleaned_body}
    """

    try:

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model="openai/gpt-oss-120b",
            response_format={"type": "json_object"},
            temperature=0.1
        )

        llm_raw_response = chat_completion.choices[0].message.content
        parsed_json = json.loads(llm_raw_response)

        analyzed_data = EmailResponse(
            source_email_id=request_data.source_email_id,
            thread_id=request_data.thread_id,
            sender=request_data.sender,
            subject=request_data.subject,
            received_at=request_data.received_at,
            classification=parsed_json.get("classification"),
            summary=parsed_json.get("summary", ""),
            tasks=parsed_json.get("tasks", []),
            events=parsed_json.get("events", []),
            evidence=parsed_json.get("evidence", []),
            processing_status="success"
        )

        async with httpx.AsyncClient() as http_client:
            try:
                db_response = await http_client.post(
                    DB_SERVICE_URL,
                    json=analyzed_data.model_dump(), 
                    timeout=10.0
                )
                db_response.raise_for_status()
            except httpx.HTTPError as db_err:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Could not connect to the database service/an error occurred: {str(db_err)}"
                ) from db_err

        return analyzed_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during analysis: {str(e)}"
        )
        
