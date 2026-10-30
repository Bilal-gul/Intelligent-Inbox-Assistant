import base64
import json
import requests
import time
import os
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


KLASOR = Path(__file__).resolve().parent
CIKTI_DOSYASI = KLASOR / "hazir_epostalar.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
ANALIZ_API_URL = os.environ.get(
    "ANALIZ_API_URL",
    "http://127.0.0.1:8002/api/v1/emails/analyze"
)

def gmail_baglan():
    kimlik = None
    token_dosyasi = KLASOR / "token.json"

    if token_dosyasi.exists():
        kimlik = Credentials.from_authorized_user_file(
            str(token_dosyasi), SCOPES
        )

    if not kimlik or not kimlik.valid:
        if kimlik and kimlik.expired and kimlik.refresh_token:
            kimlik.refresh(Request())
        else:
            izin_akisi = InstalledAppFlow.from_client_secrets_file(
                str(KLASOR / "credentials.json"),
                SCOPES
            )
            kimlik = izin_akisi.run_local_server(port=0)

        token_dosyasi.write_text(
            kimlik.to_json(),
            encoding="utf-8"
        )

    return build("gmail", "v1", credentials=kimlik)


def kayitlari_oku():
    if not CIKTI_DOSYASI.exists():
        return []

    kayitlar = json.loads(
        CIKTI_DOSYASI.read_text(encoding="utf-8")
    )

    if not isinstance(kayitlar, list):
        raise ValueError("JSON dosyası bir e-posta listesi içermeli.")

    for kayit in kayitlar:
        if (
            not isinstance(kayit, dict)
            or not isinstance(kayit.get("source_email_id"), str)
        ):
            raise ValueError("JSON dosyasında geçersiz kayıt var.")

    return kayitlar


def kayitlari_yaz(kayitlar):
    gecici_dosya = CIKTI_DOSYASI.with_suffix(".tmp")

    gecici_dosya.write_text(
        json.dumps(kayitlar, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    gecici_dosya.replace(CIKTI_DOSYASI)


def epostayi_hazirla(veri):
    kodlu_veri = veri["raw"]
    kodlu_veri += "=" * (-len(kodlu_veri) % 4)

    mesaj = BytesParser(policy=policy.default).parsebytes(
        base64.urlsafe_b64decode(kodlu_veri)
    )

    _, gonderen = parseaddr(str(mesaj.get("From", "")))

    alici_basliklari = [
        str(baslik)
        for alan in ("To", "Cc")
        for baslik in mesaj.get_all(alan, [])
    ]

    alicilar = list(dict.fromkeys(
        adres
        for _, adres in getaddresses(alici_basliklari)
        if adres
    ))

    alinma_zamani = datetime.fromtimestamp(
        int(veri["internalDate"]) / 1000,
        tz=timezone.utc
    ).isoformat()

    html_govde = mesaj.get_body(preferencelist=("html",))

    return {
        "source_email_id": veri["id"],
        "thread_id": veri["threadId"],
        "sender": gonderen,
        "recipients": alicilar,
        "subject": str(mesaj.get("Subject", "")),
        "received_at": alinma_zamani,
        "body_html": (
            html_govde.get_content()
            if html_govde is not None
            else None
        )
    }


def main():
    try:
        kayitlar = kayitlari_oku()
    except (OSError, ValueError) as hata:
        print(f"Kayıt dosyası okunamadı: {hata}")
        print("Mevcut dosyayı korumak için işlem durduruldu.")
        return

    kayitli_idler = {
        kayit["source_email_id"]
        for kayit in kayitlar
    }

    hazir_idler = {
        kayit["source_email_id"]
        for kayit in kayitlar
        if "body_html" in kayit
    }

    try:
        gmail = gmail_baglan()
    except Exception as hata:
        print(f"Gmail bağlantısı kurulamadı: {hata}")
        return

    yeni_sayisi = 0
    guncellenen_sayisi = 0
    hata_sayisi = 0
    sayfa_tokeni = None

    while True:
        try:
            sonuc = gmail.users().messages().list(
                userId="me",
                q="{in:inbox in:spam}",
                includeSpamTrash=True,
                maxResults=100,
                pageToken=sayfa_tokeni
            ).execute(num_retries=3)
        except (HttpError, OSError) as hata:
            print(f"Mesaj listesi alınamadı: {hata}")
            print("Daha önce kaydedilen veriler korunuyor.")
            return

        for mesaj_bilgisi in sonuc.get("messages", []):
            mesaj_id = mesaj_bilgisi["id"]

            if mesaj_id in hazir_idler:
                continue

            try:
                veri = gmail.users().messages().get(
                    userId="me",
                    id=mesaj_id,
                    format="raw"
                ).execute(num_retries=3)

                eposta = epostayi_hazirla(veri)
            except Exception as hata:
                hata_sayisi += 1
                print(f"Mesaj alınamadı ({mesaj_id}): {hata}")
                continue

            zaten_kayitli = mesaj_id in kayitli_idler

            if zaten_kayitli:
                yeni_liste = [
                    eposta if k["source_email_id"] == mesaj_id else k
                    for k in kayitlar
                ]
            else:
                yeni_liste = kayitlar + [eposta]

            try:
                kayitlari_yaz(yeni_liste)
            except OSError as hata:
                print(f"Dosyaya kayıt yapılamadı: {hata}")
                print("İşlem durduruldu.")
                return

            kayitlar = yeni_liste
            kayitli_idler.add(mesaj_id)
            hazir_idler.add(mesaj_id)

            if zaten_kayitli:
                guncellenen_sayisi += 1
            else:
                yeni_sayisi += 1

            print(f"Kaydedildi: {eposta['subject']}")

        sayfa_tokeni = sonuc.get("nextPageToken")

        if not sayfa_tokeni:
            break

    print(f"\nYeni kayıt: {yeni_sayisi}")
    print(f"HTML alanı güncellenen: {guncellenen_sayisi}")
    print(f"Alınamayan mesaj: {hata_sayisi}")
    print(f"Toplam kayıt: {len(kayitlar)}")


def analizleri_gonder():
    durum_dosyasi = KLASOR / "analiz_sonuclari.json"

    try:
        epostalar = kayitlari_oku()

        if durum_dosyasi.exists():
            analizler = json.loads(
                durum_dosyasi.read_text(encoding="utf-8")
            )
            if not isinstance(analizler, dict):
                raise ValueError("Analiz dosyası nesne biçiminde olmalı.")
        else:
            analizler = {}

    except (OSError, ValueError) as hata:
        print(f"Gönderim dosyaları okunamadı: {hata}")
        return

    gonderilen = 0
    atlanan = 0

    with requests.Session() as oturum:
        for eposta in epostalar:
            mesaj_id = eposta["source_email_id"]

            if mesaj_id in analizler:
                atlanan += 1
                continue

            if "body_html" not in eposta:
                print(f"HTML alanı eksik, atlandı: {mesaj_id}")
                continue

            try:
                yanit = oturum.post(
                    ANALIZ_API_URL,
                    json=eposta,
                    timeout=(5, 60),
                    allow_redirects=False
                )

                if not 200 <= yanit.status_code < 300:
                    print(f"API hatası: HTTP {yanit.status_code}")
                    print(yanit.text[:500])
                    print("Gönderim durduruldu; sonraki çalıştırmada denenebilir.")
                    break

                analiz_sonucu = yanit.json()

            except requests.exceptions.Timeout:
                print("API isteği zaman aşımına uğradı.")
                print("Sunucu işlemi tamamlamış olabilir; sonuç alınamadı.")
                print("Bu mesaj sonraki çalıştırmada tekrar gönderilecek.")
                break

            except requests.exceptions.ConnectionError:
                print(f"API'ye bağlanılamadı: {ANALIZ_API_URL}")
                print("Sunucunun açık ve adresin erişilebilir olduğunu kontrol et.")
                break

            except requests.exceptions.RequestException as hata:
                print(f"Gönderim hatası: {hata}")
                break

            except ValueError:
                print("API başarılı durum kodu döndürdü ama yanıt JSON değil.")
                print("Mesaj gönderilmiş olarak işaretlenmedi.")
                break

            yeni_analizler = {
                **analizler,
                mesaj_id: analiz_sonucu
            }

            try:
                gecici_dosya = durum_dosyasi.with_suffix(".tmp")
                gecici_dosya.write_text(
                    json.dumps(
                        yeni_analizler,
                        ensure_ascii=False,
                        indent=2
                    ),
                    encoding="utf-8"
                )
                gecici_dosya.replace(durum_dosyasi)

            except OSError as hata:
                print(f"API yanıtı alındı ama diske kaydedilemedi: {hata}")
                print("Tekrar çalıştırmada bu mesaj yeniden gönderilebilir.")
                break

            analizler = yeni_analizler
            gonderilen += 1
            print(f"Analiz tamamlandı: {eposta['subject']}")

    print(f"\nBu çalıştırmada analiz edilen: {gonderilen}")
    print(f"Daha önce analiz edilen: {atlanan}")


if __name__ == "__main__":
    print("Program başlatıldı. Durdurmak için Ctrl+C.")

    try:
        while True:
            print("\nE-postalar kontrol ediliyor...")

            try:
                main()
                analizleri_gonder()
            except Exception as hata:
                print(f"Kontrol sırasında hata oluştu: {hata}")

            print("Sonraki kontrol 15 saniye sonra.")
            time.sleep(15)

    except KeyboardInterrupt:
        print("\nProgram durduruldu.")