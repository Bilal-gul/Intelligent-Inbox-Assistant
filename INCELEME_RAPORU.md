# Intelligent Inbox Assistant – Birleştirme Öncesi İnceleme Raporu

**İnceleme kapsamı:** İlk aşamada servisler ve Docker yapılandırmaları statik olarak incelendi. Sonraki isteğinizle raporda belirtilen gerekli kod/Compose düzenlemeleri uygulandı; dışarıdaki servis bağımlılıklarıyla uçtan uca doğrulama Docker Engine’in çalışmaması nedeniyle tamamlanamadı.

## Sonraki düzenleme ve doğrulama durumu

Kullanıcının uygulama isteği üzerine servislerin yapısı korunarak `compose.yaml` güncellendi; analiz yanıtı, DB bağlantı ayarları, Gmail OAuth/data yolları ve düz metin e-posta işleme düzenlendi. Önceki JSON tespiti revize edildi: beklenen sözleşme `analyzed_data` olduğundan endpoint artık bu nesneyi döndürür. Arayüz için mevcut `Dockerfile.web` Compose’a `web` servisi olarak eklendi ve DB API’nin düz kategori alanları UI’nin beklediği `classification` biçimine dönüştürülüyor. Compose yapılandırması, Python sözdizimi kontrolü ve `git diff --check` başarılı. Log incelemesi analiz endpoint’inde Groq istemcisiyle HTTP istemcisinin aynı `client` adını kullanmasından doğan `UnboundLocalError` hatasını gösterdi; istemciler farklı isimlendirildi ve analiz servisi yeniden build edildi. Son uçtan uca doğrulamada dört servis çalışıyor, analiz/DB API’leri healthy, DB listesi 7 kayıt döndürüyor ve web sayfası HTTP 200 ile aynı 7 kaydı içeriyor. Gmail işçisinin analiz durum dosyasında da 7 başarılı sonuç var.

## Kısa değerlendirme

Projede üç ayrı servis mevcut: `gmail_service`, `analysis_api` ve `database_api`. Her servis için ayrı Dockerfile var; ancak kök dizinde Docker Compose dosyası yok. Mevcut haliyle servisleri tek komutla ayağa kaldırıp uçtan uca e-posta işlemek mümkün görünmüyor. Özellikle Gmail kimlik doğrulaması, servis adresleri, analiz yanıtı ve SQL Server bağlantısı düzeltilmeden temel akış çalışmayacaktır.

## Çalışmayı engelleyen kritik noktalar

1. **Compose eklendi; gerçek başlangıç Docker Engine bekliyor.** Kök `compose.yaml`, üç servisin build context’lerini, servis DNS URL’lerini, portlarını, healthcheck’lerini ve Gmail veri volume’unu tanımlar. Compose yapılandırması doğrulandı; Docker Engine çalışmadığından imaj build/başlatma doğrulaması yapılamadı.

2. **Servisler arası URL’ler container ortamına uygun değil.** Gmail servisi varsayılan olarak `http://127.0.0.1:8002/api/v1/emails/analyze` adresine, analiz servisi de `.env` içindeki `DB_SERVICE_URL` değerine POST ediyor. Container içinde `127.0.0.1`, aynı container’ı gösterir; kardeş servisi göstermez. Compose servis DNS adları kullanılmalı. Ayrıca veritabanı API’sinin kayıt endpoint’i `/api/v1/analyses` (`database_api/main.py`), bu nedenle analiz servisindeki POST adresi tam olarak bu yola yönlenmeli. `.env` içindeki adresin tam değeri bu rapora alınmadı.

3. **Analiz yanıtı sözleşmeye göre düzeltildi.** Projenin beklenen JSON sözleşmesinin `analyzed_data` olduğu netleşti. `analysis_api/main.py` artık DB’ye gönderilen doğrulanmış analiz nesnesini (`EmailResponse`) döndürüyor; böylece endpoint’in `response_model` tanımıyla yanıtı eşleşiyor.

4. **Gmail kimlik bilgisi Docker imajına girmiyor.** `gmail_service/.dockerignore` içinde `credentials.json` hariç tutulmuş; `gmail_oku.py:40-42` ise ilk OAuth girişinde bu dosyayı zorunlu olarak açıyor. `token.json` yoksa container içindeki işçi dosya bulunamadığı için Gmail’e bağlanamaz. Kimlik bilgileri build’e gömülmeden runtime’da güvenli biçimde sağlanmalı.

5. **Gmail OAuth akışı etkileşimli; container için hazır değil.** `gmail_oku.py:44` `run_local_server()` ile tarayıcı ve yerel OAuth callback’i bekliyor. Normal Compose servisinde bu etkileşimli akış tamamlanamaz. OAuth yetkilendirmesi container dışında tamamlanıp token’ın kalıcı şekilde sağlanması veya container’a uygun bir OAuth yöntemi belirlenmesi gerekir. `token.json` container içinde oluşturulsa bile volume olmadan yeniden oluşturulan container’da kaybolur.

6. **SQL Server bağlantısı Linux container’da çalışacak şekilde yapılandırılmamış.** `database_api/database.py:3-13` Windows’a özgü `'.\\SQLEXPRESS'` sunucu adı ve `Trusted_Connection=yes` kullanıyor. Veritabanı API imajı Debian tabanlı Linux (`database_api/Dockerfile`); Windows host’taki yerel SQL Express’e bu adla ve Windows entegre kimlik doğrulamasıyla bağlanamaz. Host erişim adresi, SQL Server TCP/IP/port ayarları ve container’ın kullanabileceği kimlik doğrulama yöntemi belirlenmeli. `ODBC Driver 18` imajda kuruluyor; bağlantı dizesinin bu sürücüyle TLS ve kimlik doğrulama ayarları da uyumlu olmalı.

7. **HTML ve düz metin e-posta desteği düzenlendi.** Gmail işçisi şimdi HTML gövdesi yoksa MIME düz metin gövdesini, ikisi de yoksa boş metni gönderir. Analiz isteğinde `body_html` opsiyoneldir.

## Yüksek öncelikli hata ve veri tutarlılığı riskleri

- **DB hatası yanlış HTTP koduna dönüşüyor.** Analiz kodu DB hatasında 502 `HTTPException` fırlatıyor (`analysis_api/main.py:115-119`), fakat bunu çevreleyen `except Exception` bu hatayı da yakalayıp 500’e çeviriyor (`126-130`). Dışarıya gerçek durum kodu yansımıyor.
- **Tekrarlanan analizler çift kayıt oluşturabilir.** Gmail işçisi yalnızca yerel `analiz_sonuclari.json` dosyasında başarı yanıtı kaydedilince mesajı tamamlanmış sayıyor. Analiz/DB kaydı başarılı olup yanıt şema hatası, bağlantı kopması veya dosya yazma hatası yaşanırsa aynı mesaj yeniden gönderilebilir. DB’de `source_email_id` benzersiz kısıtı varsa 409 alınır; yoksa mükerrer kayıt oluşabilir. DB şeması repoda bulunmadığından kısıtın varlığı doğrulanamıyor.
- **API anahtarı eksikse analiz servisi başlangıçta hata verebilir.** `analysis_api/main.py:15-16` anahtarı zorunlu doğrulamadan `Groq` istemcisini modül yüklenirken oluşturuyor. Dockerfile `.env` kopyalamıyor; `.dockerignore` da `.env` dosyasını dışlıyor. Compose/runtime ortamı `LLM_API_KEY` sağlamalı. Yerel `.env` dosyasının kendiliğinden container’a geçeceği varsayılmamalı.
- **Groq çağrısı async endpoint içinde senkron çalışıyor.** `analysis_api/main.py:80` senkron `client.chat.completions.create` çağrısı yapıyor. Bu, yoğunlukta FastAPI event loop’unu bloke edebilir; ilk lokal açılış engeli değil, ancak eşzamanlı işleme kapasitesini etkiler.
- **Analiz servisinde LLM çıktı doğrulaması sınırlı.** Alanlar Pydantic ile kısmen doğrulansa da sınıflandırma, öncelik ve durum değerleri beklenen kümeden çıkabilir. LLM boş yanıt verirse veya beklenmeyen biçim üretirse istek hata verir.

## Gmail servisi ve arayüz hakkında

- `gmail_service/Dockerfile` yalnızca `python gmail_oku.py` başlatıyor. Bu, Django web sunucusu değil; periyodik Gmail okuma ve analiz gönderme işçisidir. Dockerfile’da `EXPOSE`/Django komutu yok.
- Repoda `inbox.views.index` için çağrılan `inbox/index.html` şablonu görünmüyor; `gmail_service/inbox` altında template dosyası bulunmuyor. Dolayısıyla Django arayüzü ayrıca çalıştırılmak istenirse ana sayfa render aşamasında hata verebilir. Mevcut Dockerfile zaten bu arayüzü başlatmıyor.
- Arayüz servisi için `EMAILS_API_URL` varsayılanı `http://127.0.0.1:8000/api/v1/emails` (`gmail_service/inbox/services.py:9-12`). Compose’da bu değişken tanımlanmazsa container kendi içindeki 8000’e erişmeye çalışır.
- `gmail_oku.py` her 15 saniyede bir Gmail’i tarar. `hazir_epostalar.json` ve `analiz_sonuclari.json` container filesystem’inde kalıcı volume’a bağlanmazsa yeniden oluşturma sırasında iş durumu kaybolabilir ve e-postalar yeniden işlenebilir.
- OAuth scope `gmail.readonly`; mevcut akış yalnızca okuma için yetki istiyor.

## Veritabanı ön koşulları

Veritabanını sizin oluşturacağınız bilgisi dikkate alındı; rapor mevcut bağlantı kodunun beklediği şemayı not ediyor. `database_api/crud.py`, aşağıdaki tabloları ve alanları bekliyor: `Emails`, `Tags`, `EmailTags`, `Tasks`, `Events`, `Evidence`. Özellikle `Emails.email_id` eklenen satırın ID’si olarak dönmeli; `created_at` detay sorgusunda bekleniyor. Gerekli kolon isimleri CRUD sorgularında sabit yazılmış. Veritabanı adı `Intelligent_Inbox_Assistant` olarak sabit (`database_api/database.py:4`). Tablo/kolonlar veya SQL türleri farklıysa kayıt/listeleme işlemleri hata verir. Şema/DDL repoda olmadığı için kolon tipleri, indeksler ve `source_email_id` benzersizlik kuralı ayrıca doğrulanamadı.

## Daha düşük öncelikli bakım bulguları

- Kök `README.md` boş; servisleri başlatma, değişkenler, DB ön koşulları ve OAuth kurulumu belgelenmemiş.
- Her servisin Python bağımlılıkları sabit sürümlü; fakat Python sürümleri 3.11 ve 3.12 olarak ayrışıyor. Bu şu an doğrudan hata kanıtı değil, ancak yerel ve container davranışları farklılaşabilir.
- `analysis_api/main.py` içindeki Türkçe sistem prompt’u ve bazı servis mesajları dosya içeriğinde bozuk karakterlerle görünüyor (ör. `E-postalarÄ±`). Model kalitesini ve log okunabilirliğini etkileyebilir; terminal/UTF-8 görüntülemesi de kontrol edilmeli.
- `database_api/main.py` SQL hatalarının çoğunu genel 500 olarak döndürüyor; gerçek hata ayrıntısı loglanmadığından bağlantı/şema teşhisi zorlaşabilir.

## Birleştirmeden önce önerilen sıra

1. Docker Desktop / Docker Engine’i başlatın.
2. `.env.example` dosyasını kök `.env` dosyasına kopyalayıp SQL Server host/port ve SQL kullanıcı bilgilerini girin. SQL Server TCP/IP ve TCP portunun host’tan erişilebilir olması gerekir.
3. İlk Gmail OAuth token’ını host üzerinde oluşturun: `gmail_service` klasöründe `GMAIL_AUTH_ONLY=1` ve `GMAIL_DATA_DIR=../gmail_data` ayarlarıyla `python gmail_oku.py` çalıştırın. `credentials.json` mevcut olmalı ve Google OAuth yapılandırması bu masaüstü akışına izin vermeli.
4. Analiz API anahtarının `analysis_api/.env` içinde tanımlı olduğunu doğrulayın.
5. `docker compose up --build` ile servisleri başlatıp healthcheck’leri bekleyin; ardından DB bağlantısı, analiz API yanıtı ve tek Gmail mesajının uçtan uca işlenmesini doğrulayın.

## Çalışma ağacına dair not

İnceleme sırasında mevcut Git çalışma ağacında `analysis_api` altında yeni/değişmiş dosyalar, `database_api/database.py` değişikliği ve `analysis_api/new.txt` silinmiş olarak görünüyordu. Bunlar bu inceleme kapsamında değiştirilmedi. Rapordaki tespitler mevcut çalışma ağacı içeriğine göredir.
