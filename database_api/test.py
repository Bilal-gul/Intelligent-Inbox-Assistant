from models import EmailAnalysis
from crud import save_email_analysis

sample_json = {
    "schema_version": "v1.0",
    "source_email_id": "msg-101202",
    "thread_id": "thread-8899",
    "sender": "prof.ahmet@erciyes.edu.tr",
    "subject": "Yazılım Mühendisliği Proje Sunumu ve Rapor Teslimi",
    "received_at": "2026-10-23T10:00:00Z",
    "classification": {
        "primary_category": "academic",
        "tags": [
            "software engineering",
            "project",
            "presentation",
            "report"
        ],
        "email_type": "announcement"
    },
    "summary": "Software engineering project presentation on 26 Oct at 15:00 in Amfi 2, with report due by 25 Oct 23:59.",
    "tasks": [
        {
            "title": "Prepare architectural report",
            "description": "Prepare the project's architectural report and upload to the system",
            "deadline": "2026-10-25T23:59:00Z",
            "priority": "high",
            "status": "pending"
        }
    ],
    "events": [
        {
            "title": "Software Engineering Project Presentation",
            "start_at": "2026-10-26T15:00:00Z",
            "end_at": None,
            "location": "Amfi 2"
        }
    ],
    "evidence": [
        {
            "field_path": "events[0].start_at",
            "quote": "Yazılım projesi sunumumuz 26 Ekim Pazartesi günü saat 15:00'te Amfi 2'de yapılacaktır."
        },
        {
            "field_path": "events[0].location",
            "quote": "Yazılım projesi sunumumuz 26 Ekim Pazartesi günü saat 15:00'te Amfi 2'de yapılacaktır."
        },
        {
            "field_path": "tasks[0].deadline",
            "quote": "en geç 25 Ekim Pazar saat 23:59'a kadar sisteme yükle."
        }
    ],
    "processing_status": "success"
}

analysis = EmailAnalysis.model_validate(sample_json)

email_id = save_email_analysis(analysis)

print(f"E-posta başarıyla kaydedildi! email_id: {email_id}")